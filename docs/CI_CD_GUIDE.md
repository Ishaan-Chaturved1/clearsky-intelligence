# ClearSky Intelligence CI/CD Guide

## Overview

ClearSky Intelligence utilizes a decoupled, deadline-ready GitHub Actions CI/CD architecture designed for reliability, fast automated feedback, and explicit separation between continuous integration testing and AWS deployment.

---

## 1. Workflows Architecture

| Workflow | File | Triggers | Required Permissions | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **ClearSky Intelligence CI** | [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml) | `push` to `main`, `pull_request` to `main` | `contents: read` | Automated validation of application code (backend tests & frontend build) without cloud credentials. |
| **Continuous Deployment** | [`.github/workflows/deploy.yml`](file:///.github/workflows/deploy.yml) | `workflow_dispatch` (Manual intentional trigger) | Top: `contents: read`<br>Deploy jobs: `id-token: write` | Packaging and deployment to AWS via OIDC authentication, followed by smoke verification. |

---

## 2. Workflow Validation Scope

### A. CI Workflow (`ci.yml`)
Runs two parallel, zero-cloud-credential jobs:
1. **`backend-test`**:
   - Sets up Python 3.11 with pip caching.
   - Installs production backend dependencies (`requirements.txt`).
   - Runs full pytest suite (145 tests covering spatial IDW, Stage 5 evidence enrichment, Indian AQI sub-index calculations, and deployment configurations).
   - Any test failure causes an immediate CI failure.
2. **`frontend-build`**:
   - Sets up Node.js 20 with npm caching.
   - Installs dependencies reproducibly (`npm ci`).
   - Executes TypeScript typechecking and Vite production compilation (`tsc && vite build`).
   - Any compiler or bundle error fails the job.

### B. CD Workflow (`deploy.yml`)
Structured into four sequential and gated stages:
1. **`pre-deploy-check`**:
   - Evaluates selected execution mode (`DEPLOY` vs `PREPARATION_ONLY`).
   - In `DEPLOY` mode: asserts presence of `AWS_DEPLOY_ROLE_ARN`. Fails immediately if credentials are missing.
   - In `PREPARATION_ONLY` mode: emits an explicit warning in `$GITHUB_STEP_SUMMARY` stating no live AWS deployment was attempted or claimed.
   - Re-verifies backend tests and compiles frontend distribution.
   - Packages `clearsky-deploy.zip` and uploads deployment bundle artifact.
2. **`deploy-infrastructure`** (Gated on `DEPLOY` mode):
   - Authenticates via GitHub Actions OIDC (`aws-actions/configure-aws-credentials@v4`).
   - Builds and deploys AWS SAM serverless stack (`infrastructure/template.yaml`).
   - Exports `serverless_api_url` and `data_lake_bucket`.
3. **`deploy-application`** (Gated on `DEPLOY` mode):
   - Asserts Elastic Beanstalk configuration (`EB_APP_NAME`, `EB_ENV_NAME`, `S3_DEPLOY_BUCKET`).
   - Deploys version bundle to S3 and initiates Elastic Beanstalk update.
   - Polls until environment update is complete and asserts Health is not `Red`.
4. **`post-deploy-verify`** (Gated on `DEPLOY` mode):
   - Resolves target URL and executes live deployment verification via `scripts/smoke_test.py`.
   - Any endpoint failure or stack trace leak fails verification.

---

## 3. GitHub Secrets & Variables

### Required for Deployment (`DEPLOY` mode)
- `AWS_DEPLOY_ROLE_ARN`: AWS IAM Role ARN for OIDC authentication.
- `AWS_REGION`: Target AWS region (defaults to `us-east-1` if omitted).
- `EB_APP_NAME`: Elastic Beanstalk application name.
- `EB_ENV_NAME`: Elastic Beanstalk environment name.
- `S3_DEPLOY_BUCKET`: Target S3 bucket for Elastic Beanstalk deployment bundles.

### Optional Provider API Keys (Passed to CloudFormation parameters)
- `OPENAQ_API_KEY`: OpenAQ v3 API key.
- `NASA_FIRMS_MAP_KEY`: NASA FIRMS VIIRS active fire map key.
- `DATA_GOV_IN_API_KEY`: CPCB / data.gov.in API key.

*Note: No static, long-lived AWS Access Key IDs or Secret Access Keys are accepted or used in this pipeline.*

---

## 4. AWS OIDC Authentication

GitHub Actions authenticates to AWS using OpenID Connect (OIDC) tokens, eliminating static secrets:

1. GitHub issues a short-lived OIDC JSON Web Token (JWT) signed by `token.actions.githubusercontent.com`.
2. Action requests temporary STS credentials assuming the role specified by `AWS_DEPLOY_ROLE_ARN`.
3. The IAM Role's trust policy enforces strict subject claims:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:Ishaan-Chaturved1/clearsky-intelligence:ref:refs/heads/main"
           }
         }
       }
     ]
   }
   ```
4. Only jobs originating from `Ishaan-Chaturved1/clearsky-intelligence` on branch `main` are authorized.

---

## 5. Distinguishing CI Success from Deployment Success

- **CI Success**: Indicates code compiles, tests pass, and frontend bundles cleanly. CI status does **not** indicate that code is running in AWS.
- **Deployment Success**: Confirmed only when all 4 deployment jobs succeed, ending with `post-deploy-verify` exiting code 0 against a live HTTP URL.
- **Preparation Mode**: When run with `deployment_mode=PREPARATION_ONLY`, artifacts are verified and packaged without deploying. The step summary explicitly documents this to prevent false-green deployment claims.

---

## 6. Troubleshooting & Known Blockers

### A. Missing `AWS_DEPLOY_ROLE_ARN`
- **Symptom**: `pre-deploy-check` fails with `Missing AWS Secret: AWS_DEPLOY_ROLE_ARN secret is missing in GitHub Repository Secrets.`
- **Remedy**: Configure `AWS_DEPLOY_ROLE_ARN` in GitHub Repository Settings -> Secrets and variables -> Actions, or trigger `workflow_dispatch` with `deployment_mode=PREPARATION_ONLY`.

### B. AWS Account Access Restrictions
- If AWS account access is unavailable due to institutional account ownership or missing sandbox permissions, CI remains 100% functional.
- The repository can be fully developed and evaluated locally (`pytest` + `npm run build`) without requiring an active AWS subscription.
