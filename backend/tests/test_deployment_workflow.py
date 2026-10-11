"""
Tests for Deployment Workflow Semantics, OIDC Configuration, and EB Readiness.
Validates that .github/workflows/deploy.yml adheres to strict deployment guarantees:
- Fails when AWS credentials/secrets are missing in DEPLOY mode.
- Supports explicit PREPARATION_ONLY mode without falsely claiming deployment.
- Enforces strict job dependencies (CI -> Infrastructure -> Application -> Smoke).
- Disallows continue-on-error hiding of deployment failures.
- Verifies OIDC trust policy targeting repo:Ishaan-Chaturved1/clearsky-intelligence:ref:refs/heads/main.
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
        "pre-deploy-check",
        "deploy-infrastructure",
        "deploy-application",
        "post-deploy-verify"
    ]
    for j in expected_jobs:
        assert j in jobs, f"Job {j} missing from deploy.yml"

    # Verify dependency chain
    assert jobs["deploy-infrastructure"]["needs"] == "pre-deploy-check"
    assert jobs["deploy-application"]["needs"] == ["pre-deploy-check", "deploy-infrastructure"]
    assert jobs["post-deploy-verify"]["needs"] == ["deploy-infrastructure", "deploy-application"]


def test_deploy_workflow_no_continue_on_error(deploy_workflow_content):
    data, text = deploy_workflow_content
    assert "continue-on-error: true" not in text.lower(), (
        "Deployment workflow must not use continue-on-error to hide failures."
    )


def test_deploy_workflow_explicit_preparation_only_mode(deploy_workflow_content):
    data, text = deploy_workflow_content
    on_clause = data.get("on") or data.get(True) or {}
    inputs = on_clause.get("workflow_dispatch", {}).get("inputs", {})
    assert "deployment_mode" in inputs
    options = inputs["deployment_mode"].get("options", [])
    assert "DEPLOY" in options
    assert "PREPARATION_ONLY" in options

    # Verify preparation-only labeling in script text
    assert "PREPARATION_ONLY" in text
    assert "PREPARATION ONLY" in text


def test_deploy_workflow_fails_on_missing_credentials(deploy_workflow_content):
    data, text = deploy_workflow_content
    # Check that pre-deploy-check exits with code 1 if ROLE_ARN is missing in DEPLOY mode
    pre_deploy_steps = data["jobs"]["pre-deploy-check"]["steps"]
    eval_step = next(s for s in pre_deploy_steps if s.get("id") == "eval-mode")
    run_script = eval_step["run"]

    assert "exit 1" in run_script
    assert "AWS_DEPLOY_ROLE_ARN" in run_script


def test_deploy_workflow_eb_fails_on_missing_config(deploy_workflow_content):
    data, text = deploy_workflow_content
    eb_steps = data["jobs"]["deploy-application"]["steps"]
    validate_step = next(s for s in eb_steps if "Validate Elastic Beanstalk Prerequisites" in s.get("name", ""))
    run_script = validate_step["run"]

    assert "EB_APP_NAME" in run_script
    assert "EB_ENV_NAME" in run_script
    assert "S3_DEPLOY_BUCKET" in run_script
    assert "exit 1" in run_script


def test_deploy_workflow_smoke_tests_fails_on_missing_target(deploy_workflow_content):
    data, text = deploy_workflow_content
    smoke_steps = data["jobs"]["post-deploy-verify"]["steps"]
    run_smoke_step = next(s for s in smoke_steps if "Run Smoke Tests" in s.get("name", ""))
    run_script = run_smoke_step["run"]

    assert "exit 1" in run_script
    assert "TARGET_URL" in run_script
    assert "scripts/smoke_test.py" in run_script


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
