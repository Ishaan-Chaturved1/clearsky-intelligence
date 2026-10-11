import os
import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(override=True)

def _load_aws_secrets_manager():
    """
    Safely retrieves application secrets from AWS Secrets Manager if configured.
    Checks SECRETS_MANAGER_SECRET_NAME or default 'clearsky/production/api-keys'.
    Falls back gracefully without raising errors when Secrets Manager is absent or offline.
    """
    secret_name = os.getenv("SECRETS_MANAGER_SECRET_NAME")
    if not secret_name:
        return
    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            secrets = json.loads(response["SecretString"])
            for key, val in secrets.items():
                if key and val and key not in os.environ:
                    os.environ[key] = str(val)
    except Exception:
        # Non-blocking fallback to existing environment variables
        pass

_load_aws_secrets_manager()

class Settings(BaseModel):
    PROJECT_NAME: str = "ClearSky Intelligence"
    PROJECT_DESCRIPTOR: str = "Smart Urban Air Intelligence"
    TAGLINE: str = "Smarter environmental decisions. Cleaner, more sustainable cities."
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    CORS_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,*").split(",") if origin.strip()
    ]
    
    # Storage: "sqlite", "json", or "dynamodb"
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "sqlite")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "data" / "clearsky.db"))
    JSON_STORAGE_DIR: str = os.getenv("JSON_STORAGE_DIR", str(BASE_DIR / "data"))
    
    # AWS S3 & DynamoDB Configuration
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_REGION: str = os.getenv("S3_REGION", os.getenv("AWS_REGION", "us-east-1"))
    DYNAMODB_ENDPOINT_URL: Optional[str] = os.getenv("DYNAMODB_ENDPOINT_URL", None)
    DYNAMODB_ZONES_TABLE: str = os.getenv("DYNAMODB_ZONES_TABLE", "clearsky-zones")
    DYNAMODB_READINGS_TABLE: str = os.getenv("DYNAMODB_READINGS_TABLE", "clearsky-readings")
    DYNAMODB_DECISIONS_TABLE: str = os.getenv("DYNAMODB_DECISIONS_TABLE", "clearsky-decisions")
    DYNAMODB_ALERTS_TABLE: str = os.getenv("DYNAMODB_ALERTS_TABLE", "clearsky-alerts")
    DYNAMODB_REPORTS_TABLE: str = os.getenv("DYNAMODB_REPORTS_TABLE", "clearsky-citizen-reports")
    DYNAMODB_REWARDS_TABLE: str = os.getenv("DYNAMODB_REWARDS_TABLE", "clearsky-rewards")
    DYNAMODB_REDEMPTIONS_TABLE: str = os.getenv("DYNAMODB_REDEMPTIONS_TABLE", "clearsky-redemptions")
    DYNAMODB_EVENTS_TABLE: str = os.getenv("DYNAMODB_EVENTS_TABLE", "clearsky-events")
    DYNAMODB_INVESTIGATIONS_TABLE: str = os.getenv("DYNAMODB_INVESTIGATIONS_TABLE", "clearsky-investigations")
    SECRETS_MANAGER_SECRET_NAME: str = os.getenv("SECRETS_MANAGER_SECRET_NAME", "")
    
    # Timeouts & Limits
    API_TIMEOUT_SECONDS: float = float(os.getenv("API_TIMEOUT_SECONDS", "10.0"))
    CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "30"))
    STALE_THRESHOLD_HOURS: float = float(os.getenv("STALE_THRESHOLD_HOURS", "3.0"))
    
    # External APIs
    OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
    OPENAQ_BASE_URL: str = os.getenv("OPENAQ_BASE_URL", "https://api.openaq.org/v3")
    CPCB_DATA_GOV_API_KEY: str = os.getenv("CPCB_DATA_GOV_API_KEY", os.getenv("DATA_GOV_IN_API_KEY", ""))
    
    OPEN_METEO_FORECAST_URL: str = os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
    OPEN_METEO_AIR_QUALITY_URL: str = os.getenv("OPEN_METEO_AIR_QUALITY_URL", "https://air-quality-api.open-meteo.com/v1/air-quality")
    
    NASA_FIRMS_MAP_KEY: str = os.getenv("NASA_FIRMS_MAP_KEY", "")
    NASA_FIRMS_BASE_URL: str = os.getenv("NASA_FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/country/csv")
    
    OVERPASS_API_URL: str = os.getenv("OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")
    
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "clearsky-dev-admin-secret-2025")
    
    # Baseline Water Assumptions
    DEFAULT_BASELINE_INTERVENTIONS_PER_ZONE_PER_DAY: float = float(os.getenv("DEFAULT_BASELINE_INTERVENTIONS_PER_ZONE_PER_DAY", "3.0"))
    DEFAULT_ASSUMED_LITERS_PER_INTERVENTION: float = float(os.getenv("DEFAULT_ASSUMED_LITERS_PER_INTERVENTION", "5000.0"))
    
    # AI Summary
    ENABLE_AI_BRIEF: bool = os.getenv("ENABLE_AI_BRIEF", "false").lower() in ("true", "1", "yes")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

settings = Settings()
