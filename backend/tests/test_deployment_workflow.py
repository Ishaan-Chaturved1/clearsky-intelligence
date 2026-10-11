"""
Tests for Deployment Workflow Semantics, OIDC Configuration, and EB Readiness.
Validates that .github/workflows/deploy.yml adheres to a clean test-then-deploy pipeline:
- Enforces test suite execution before deployment (deploy needs test).
- Fails when AWS credentials/secrets are missing before deployment.
- Disallows continue-on-error hiding of deployment failures.
- Verifies OIDC trust policy targeting repo:Ishaan-Chaturved1/clearsky-intelligence:ref:refs/heads/main.
- Verifies Elastic Beanstalk entrypoint and configuration.
"""
import json
from pathlib import Path
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def deploy_workflow_content():
    deploy_yml = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
    assert deploy_yml.exists(), "deploy.yml must exist"
    with open(deploy_yml, "r", encoding="utf-8") as f:
        return yaml.safe_load(f), deploy_yml.read_text(encoding="utf-8")


def test_deploy_workflow_structure_and_jobs(deploy_workflow_content):
    data, text = deploy_workflow_content
    jobs = data.get("jobs", {})

    expected_jobs = [
        "test",
        "deploy"
    ]
    for j in expected_jobs:
        assert j in jobs, f"Job {j} missing from deploy.yml"

    # Verify dependency chain: deployment strictly requires tests to pass
    assert jobs["deploy"]["needs"] == "test"


def test_deploy_workflow_no_continue_on_error(deploy_workflow_content):
    data, text = deploy_workflow_content
    assert "continue-on-error: true" not in text.lower(), (
        "Deployment workflow must not use continue-on-error to hide failures."
    )


def test_deploy_workflow_fails_on_missing_credentials(deploy_workflow_content):
    data, text = deploy_workflow_content
    deploy_steps = data["jobs"]["deploy"]["steps"]
    validate_step = next(s for s in deploy_steps if "Validate Deployment Prerequisites" in s.get("name", ""))
    run_script = validate_step["run"]

    assert "exit 1" in run_script
    assert "ROLE_ARN" in run_script
    assert "EB_APP_NAME" in run_script
    assert "EB_ENV_NAME" in run_script
    assert "S3_DEPLOY_BUCKET" in run_script


def test_oidc_role_trust_policy_targets_main_branch():
    trust_policy_path = REPO_ROOT / "infrastructure" / "github-oidc-trust-policy.json"
    assert trust_policy_path.exists()

    with open(trust_policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)

    stmt = policy["Statement"][0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Action"] == "sts:AssumeRoleWithWebIdentity"
    cond = stmt["Condition"]
    assert cond["StringEquals"]["token.actions.githubusercontent.com:aud"] == "sts.amazonaws.com"
    assert cond["StringLike"]["token.actions.githubusercontent.com:sub"] == "repo:Ishaan-Chaturved1/clearsky-intelligence:ref:refs/heads/main"


def test_eb_entrypoint_and_config():
    procfile = REPO_ROOT / "Procfile"
    assert procfile.exists()
    assert "application:application" in procfile.read_text(encoding="utf-8")

    eb_config = REPO_ROOT / ".ebextensions" / "01_app.config"
    assert eb_config.exists()
    content = eb_config.read_text(encoding="utf-8")
    assert "HealthCheckPath: \"/api/health\"" in content
    assert "MatcherHTTPCode: \"200\"" in content
    assert "clearsky-zones-production" in content
