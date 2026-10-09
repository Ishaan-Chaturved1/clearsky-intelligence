import os
from pathlib import Path
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")
load_dotenv()

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
    
    # Storage
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "sqlite")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "data" / "clearsky.db"))
    
    # Timeouts & Limits
    API_TIMEOUT_SECONDS: float = float(os.getenv("API_TIMEOUT_SECONDS", "10.0"))
    CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "30"))
    STALE_THRESHOLD_HOURS: float = float(os.getenv("STALE_THRESHOLD_HOURS", "3.0"))
    
    # External APIs
    OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
    OPENAQ_BASE_URL: str = os.getenv("OPENAQ_BASE_URL", "https://api.openaq.org/v3")
    
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
