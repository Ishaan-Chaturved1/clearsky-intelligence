#!/usr/bin/env python3
"""
Post-Deployment Smoke Test & Health Verification Suite for ClearSky Intelligence.
Runs against local or remote deployments (AWS Elastic Beanstalk / API Gateway).
Uses Python standard library (urllib.request) so it has zero external dependencies.
Exits with code 0 on full verification pass, code 1 on failure.
"""
import sys
import os
import argparse
import time
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List

TEST_TIMEOUT = 15.0


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


class SmokeTestResponse:
    def __init__(self, status_code: int, body_bytes: bytes):
        self.status_code = status_code
        self.content = body_bytes
        self.text = body_bytes.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


def http_get(url: str, timeout: float = TEST_TIMEOUT) -> SmokeTestResponse:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ClearSky-SmokeTest/1.0", "Accept": "*/*"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return SmokeTestResponse(resp.status, resp.read())
    except urllib.error.HTTPError as exc:
        return SmokeTestResponse(exc.code, exc.read())


def run_smoke_tests(base_url: str) -> bool:
    base_url = base_url.rstrip("/")
    log(f"Starting deployment smoke tests against target: {base_url}")
    failures: List[str] = []

    endpoints = [
        # (Path, Expected Status, Description, Validator fn)
        (
            "/api/health",
            200,
            "Application Health Check",
            lambda r: r.json().get("status") in ("healthy", "ok")
        ),
        (
            "/api/overview",
            200,
            "System Overview Metrics",
            lambda r: "total_monitored_zones" in r.json() and "data_mode" in r.json()
        ),
        (
            "/api/zones",
            200,
            "Monitored Zones Listing",
            lambda r: isinstance(r.json(), list) and len(r.json()) > 0
        ),
        (
            "/api/stations",
            200,
            "Monitoring Stations Catalog",
            lambda r: isinstance(r.json(), list)
        ),
        (
            "/api/sources/status",
            200,
            "Environmental Data Sources Health",
            lambda r: "sources" in r.json() or "coverage" in r.json()
        ),
        (
            "/api/methodology",
            200,
            "Scientific Decision Rules & Documentation",
            lambda r: "rules" in r.json() or "methodology" in r.json() or "version" in r.json()
        ),
        (
            "/api/investigation/local-sources?latitude=28.6469&longitude=77.3160&radius_km=5",
            200,
            "Stage 3 Local Source Investigation API",
            lambda r: "candidates" in r.json() and "status" in r.json()
        ),
        (
            "/api/investigation/transport?latitude=28.6469&longitude=77.3160&lookback_hours=6",
            200,
            "Stage 3 Backward Atmospheric Transport API",
            lambda r: "trajectory_points" in r.json() and "limitations" in r.json()
        ),
        (
            "/docs",
            200,
            "OpenAPI / Swagger UI Documentation",
            lambda r: "swagger" in r.text.lower() or "openapi" in r.text.lower()
        ),
    ]

    for path, expected_status, description, validator in endpoints:
        url = f"{base_url}{path}"
        try:
            resp = http_get(url)
            if resp.status_code != expected_status:
                failures.append(f"FAIL: {description} ({path}) -> HTTP {resp.status_code} (expected {expected_status})")
                log(f"  ❌ {description} (HTTP {resp.status_code})")
                continue

            if validator and not validator(resp):
                failures.append(f"FAIL: {description} ({path}) -> JSON payload validation failed")
                log(f"  ❌ {description} (Validation failed)")
                continue

            log(f"  ✅ {description} (HTTP {resp.status_code})")
        except Exception as exc:
            failures.append(f"ERROR: {description} ({path}) -> Connection failed: {exc}")
            log(f"  ❌ {description} (Connection error: {exc})")

    # Security check: 404 should never expose stack traces or secrets
    try:
        err_resp = http_get(f"{base_url}/api/unmapped-endpoint-probe-999")
        if err_resp.status_code != 404:
            failures.append(f"SECURITY: Unmapped endpoint probe returned HTTP {err_resp.status_code} instead of 404")
        elif "traceback" in err_resp.text.lower() or ("line " in err_resp.text.lower() and "file " in err_resp.text.lower()):
            failures.append("SECURITY: 404 response leaked internal stack trace")
        else:
            log("  ✅ Security Error Boundary (No stack trace leakage)")
    except Exception as exc:
        failures.append(f"ERROR: Security error boundary probe failed: {exc}")

    print("\n" + "=" * 60)
    if not failures:
        log("🎉 ALL DEPLOYMENT SMOKE TESTS PASSED CLEANLY!")
        print("=" * 60 + "\n")
        return True
    else:
        log(f"💥 {len(failures)} SMOKE TEST(S) FAILED:")
        for f in failures:
            print(f"  • {f}")
        print("=" * 60 + "\n")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClearSky Deployment Smoke Tests")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEPLOYMENT_BASE_URL", "http://127.0.0.1:8000"),
        help="Target base URL of deployment to test"
    )
    args = parser.parse_args()

    success = run_smoke_tests(args.base_url)
    sys.exit(0 if success else 1)
