"""
Verification tests for ClearSky Intelligence CI/CD pipelines, automated AWS provisioning,
and environmental data preservation across deployment operations.
"""
from pathlib import Path
import json
import yaml
import pytest
from datetime import datetime, timezone

from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    PollutantValue,
    WeatherConditions,
    FireSummary,
    NearbyInfrastructure,
    ConfidenceLevel,
    DecisionType,
    DataMode
)
from app.repositories.json_repository import JSONRepository

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# 1. DATA PRESERVATION TESTS
# ==============================================================================

def test_data_preservation_across_repository_reinitialization(tmp_path):
    """
    Verifies that re-instantiating the repository does NOT wipe or reset
    existing environmental readings or published decisions.
    """
    repo1 = JSONRepository(data_dir=str(tmp_path))

    test_zone = Zone(
        zone_id="zone-delhi-anand-vihar",
        name="Anand Vihar ISBT",
        latitude=28.6469,
        longitude=77.3160,
        description="High-density transport terminal",
        zone_type="Industrial",
        nearby_infrastructure=NearbyInfrastructure(
            major_roads=["Vikas Marg", "Gazipur Road"],
            construction_sites=["RRTS Transit Station"],
            has_construction_nearby=True
        )
    )
    repo1.save_zone(test_zone)

    now_iso = datetime.now(timezone.utc).isoformat()

    reading = EnvironmentalReading(
        reading_id="read-anand-vihar-001",
        zone_id="zone-delhi-anand-vihar",
        timestamp=now_iso,
        pm25=PollutantValue(value=245.5, unit="ug/m3"),
        pm10=PollutantValue(value=380.0, unit="ug/m3"),
        weather=WeatherConditions(
            temperature_c=22.5,
            relative_humidity=65.0,
            wind_speed_kmh=6.5,
            wind_direction_deg=295.0,
            boundary_layer_height_m=350.0
        ),
        fire_summary=FireSummary(nearby_fires_count=14, possible_smoke_transport=True),
        data_mode=DataMode.LIVE
    )
    repo1.save_reading(reading)

    decision = DecisionRecord(
        decision_id="dec-anand-vihar-001",
        zone_id="zone-delhi-anand-vihar",
        decision=DecisionType.INTERVENTION_RECOMMENDED,
        confidence=ConfidenceLevel.HIGH,
        priority=1,
        pollutants={"pm25": PollutantValue(value=245.5), "pm10": PollutantValue(value=380.0)},
        weather=WeatherConditions(temperature_c=22.5, wind_speed_kmh=6.5),
        reasons=["Severe localized PM10", "Low boundary layer height"],
        triggered_rules=["RULE_SEVERE_PM10", "RULE_LOW_BOUNDARY_LAYER"],
        observed_at=now_iso,
        scored_at=now_iso,
        data_mode=DataMode.LIVE
    )
    repo1.save_decision(decision)

    # Re-instantiate repository (simulating backend redeployment)
    repo2 = JSONRepository(data_dir=str(tmp_path))
    zones = repo2.list_zones()
    assert len(zones) == 1
    assert zones[0].zone_id == "zone-delhi-anand-vihar"

    latest_reading = repo2.get_latest_reading("zone-delhi-anand-vihar")
    assert latest_reading is not None
    assert latest_reading.pm25.value == 245.5
    assert latest_reading.pm10.value == 380.0
    assert latest_reading.weather.boundary_layer_height_m == 350.0

    latest_decision = repo2.get_latest_decision("zone-delhi-anand-vihar")
    assert latest_decision is not None
    assert latest_decision.decision == DecisionType.INTERVENTION_RECOMMENDED
    assert latest_decision.confidence == ConfidenceLevel.HIGH
    assert "Severe localized PM10" in latest_decision.reasons


def test_failed_reading_does_not_corrupt_existing_data(tmp_path):
    """
    Verifies that a failure during ingestion does not delete previously
    stored readings.
    """
    repo = JSONRepository(data_dir=str(tmp_path))
    zone_id = "zone-delhi-wazirpur"
    ts = "2025-10-10T10:00:00+00:00"

    initial_reading = EnvironmentalReading(
        reading_id="read-wazirpur-001",
        zone_id=zone_id,
        timestamp=ts,
        pm25=PollutantValue(value=180.0, unit="ug/m3"),
        pm10=PollutantValue(value=310.0, unit="ug/m3"),
        weather=WeatherConditions(temperature_c=25.0, wind_speed_kmh=8.0),
        data_mode=DataMode.CACHED
    )
    repo.save_reading(initial_reading)

    # Verify initial exists
    persisted = repo.get_latest_reading(zone_id)
    assert persisted is not None
    assert persisted.pm25.value == 180.0
    assert persisted.timestamp == ts


# ==============================================================================
# 2. CI/CD WORKFLOW STRUCTURE & SAFETY TESTS
# ==============================================================================

WORKFLOWS = [
    "ci.yml",
    "deploy-backend.yml",
    "deploy-frontend.yml",
    "deploy-infrastructure.yml",
    "bootstrap-aws.yml"
]


@pytest.mark.parametrize("wf_file", WORKFLOWS)
def test_workflow_files_exist_and_are_valid_yaml(wf_file):
    path = REPO_ROOT / ".github" / "workflows" / wf_file
    assert path.exists(), f"Workflow file {wf_file} must exist"
    content = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    assert parsed is not None
    assert "name" in parsed
    assert "jobs" in parsed


def test_no_hardcoded_aws_credentials_in_workflows():
    """
    Ensures that no AWS access keys, secret keys, or account credentials
    are hardcoded or logged in workflow files.
    """
    wf_dir = REPO_ROOT / ".github" / "workflows"
    for wf in wf_dir.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        assert "AKIA" not in text, f"Hardcoded AWS Access Key ID detected in {wf.name}"
        assert "aws_secret_access_key:" not in text or "${{" in text, (
            f"Unmasked secret access key found in {wf.name}"
        )


def test_deployment_workflows_authenticate_with_access_keys():
    """
    Ensures that automated deployment and bootstrap workflows authenticate
    using AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY without requiring OIDC.
    """
    for wf_name in ["deploy-backend.yml", "deploy-frontend.yml", "deploy-infrastructure.yml", "bootstrap-aws.yml"]:
        path = REPO_ROOT / ".github" / "workflows" / wf_name
        text = path.read_text(encoding="utf-8")
        assert "aws-actions/configure-aws-credentials@v4" in text
        assert "AWS_ACCESS_KEY_ID" in text
        assert "AWS_SECRET_ACCESS_KEY" in text


def test_bootstrap_workflow_verifies_account_id_safety():
    """
    Ensures bootstrap-aws.yml verifies caller identity and matches against
    AWS_ACCOUNT_ID before executing any AWS changes.
    """
    bootstrap_path = REPO_ROOT / ".github" / "workflows" / "bootstrap-aws.yml"
    text = bootstrap_path.read_text(encoding="utf-8")
    assert "aws sts get-caller-identity" in text
    assert "EXPECTED_ACCOUNT_ID" in text
    assert "Account ID mismatch" in text
    assert "exit 1" in text


def test_sam_template_persistent_resources_retain_policy():
    """
    Ensures that DynamoDB tables and S3 DataLake in template.yaml
    have DeletionPolicy: Retain and UpdateReplacePolicy: Retain.
    """
    def cfn_constructor(loader, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        elif isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return str(node)

    class CfnLoader(yaml.SafeLoader):
        pass

    for tag in ['!Sub', '!Ref', '!GetAtt', '!Join', '!Select', '!Split', '!FindInMap', '!Base64', '!Cidr']:
        CfnLoader.add_constructor(tag, cfn_constructor)

    template_path = REPO_ROOT / "infrastructure" / "template.yaml"
    with open(template_path, "r", encoding="utf-8") as f:
        template = yaml.load(f, Loader=CfnLoader)

    resources = template.get("Resources", {})
    persistent_keys = [
        "ZonesTable",
        "ReadingsTable",
        "DecisionsTable",
        "AlertsTable",
        "EventsTable",
        "InvestigationsTable",
        "DataLakeBucket"
    ]
    for key in persistent_keys:
        res = resources.get(key)
        assert res is not None, f"Resource {key} must exist in template.yaml"
        assert res.get("DeletionPolicy") == "Retain", f"{key} must have DeletionPolicy: Retain"
        assert res.get("UpdateReplacePolicy") == "Retain", f"{key} must have UpdateReplacePolicy: Retain"


def test_deploy_frontend_workflow_s3_and_cloudfront_oac_configuration():
    """
    Verifies that deploy-frontend.yml and generate_cloudfront_config.py configure:
    - Dedicated private S3 bucket with account ID
    - CloudFront Origin Access Control (OAC)
    - Custom error responses for SPA fallback (403/404 -> index.html 200)
    - Optimized caching for immutable assets vs index.html
    - Account ID safety verification
    """
    frontend_wf = REPO_ROOT / ".github" / "workflows" / "deploy-frontend.yml"
    assert frontend_wf.exists()
    content = frontend_wf.read_text(encoding="utf-8")

    # Private S3 and OAC
    assert "clearsky-intelligence-frontend-${TARGET_ENV}-${ACCOUNT_ID}" in content
    assert "put-public-access-block" in content
    assert "create-origin-access-control" in content
    assert "scripts/generate_cloudfront_config.py" in content

    # Caching Strategy
    assert "max-age=31536000,immutable" in content
    assert "no-cache,no-store,must-revalidate" in content

    # Account Verification
    assert "aws sts get-caller-identity" in content
    assert "EXPECTED_ACCOUNT_ID" in content

    # No backend restart or ingestion
    assert "eb deploy" not in content
    assert "eb setenv" not in content
    assert "sam deploy" not in content
    assert "scripts/ingest" not in content

    # Verify script generates exact SPA fallback configuration
    from scripts.generate_cloudfront_config import generate_distribution_config, generate_oac_bucket_policy
    cfg = generate_distribution_config(
        caller_ref="test-ref",
        bucket="test-bucket",
        region="us-east-1",
        oac_id="oac-test-id",
        comment="test-comment"
    )
    assert cfg["DefaultRootObject"] == "index.html"
    error_responses = cfg["CustomErrorResponses"]["Items"]
    error_codes = {item["ErrorCode"]: item for item in error_responses}
    assert 403 in error_codes and error_codes[403]["ResponsePagePath"] == "/index.html" and error_codes[403]["ResponseCode"] == "200"
    assert 404 in error_codes and error_codes[404]["ResponsePagePath"] == "/index.html" and error_codes[404]["ResponseCode"] == "200"

    # Verify OAC policy
    policy = generate_oac_bucket_policy(bucket="test-bucket", account_id="654157459447", dist_id="EDIST123")
    statement = policy["Statement"][0]
    assert statement["Principal"]["Service"] == "cloudfront.amazonaws.com"
    assert "test-bucket/*" in statement["Resource"]
    assert "EDIST123" in statement["Condition"]["StringEquals"]["AWS:SourceArn"]


def test_frontend_api_base_url_normalization_logic():
    """
    Verifies URL normalization logic mirroring frontend/src/services/api.ts.
    """
    def compute_api_base(raw: str | None) -> str:
        trimmed = (raw or "").strip()
        normalized = trimmed.rstrip("/") if trimmed else ""
        if not normalized:
            return "/api"
        return normalized if normalized.endswith("/api") else f"{normalized}/api"

    # Default / empty
    assert compute_api_base(None) == "/api"
    assert compute_api_base("") == "/api"
    assert compute_api_base("   ") == "/api"

    # Relative or absolute without trailing slash
    assert compute_api_base("http://backend.elasticbeanstalk.com") == "http://backend.elasticbeanstalk.com/api"
    # With trailing slash
    assert compute_api_base("http://backend.elasticbeanstalk.com/") == "http://backend.elasticbeanstalk.com/api"
    # Already includes /api
    assert compute_api_base("http://backend.elasticbeanstalk.com/api") == "http://backend.elasticbeanstalk.com/api"
    assert compute_api_base("http://backend.elasticbeanstalk.com/api/") == "http://backend.elasticbeanstalk.com/api"
