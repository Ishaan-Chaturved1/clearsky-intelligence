import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend and project root directories are in sys.path
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
_project_root = _backend_dir.parent
for _p in (_backend_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, BASE_DIR
from app.core.logging import logger
from app.api.endpoints import router as api_router
from app.api.investigation_endpoints import router as investigation_router
from app.api.data_health_endpoints import router as data_health_router
from app.repositories.local_repository import SQLiteRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    from app.repositories import get_repository
    repo = get_repository()
    existing_zones = repo.list_zones()
    if not existing_zones:
        logger.info(f"Storage backend '{settings.STORAGE_BACKEND}' is empty. Initializing zones from data/zones.json...")
        if settings.STORAGE_BACKEND == "sqlite":
            from scripts.seed_demo_data import seed_database
            seed_database(settings.SQLITE_DB_PATH)
        else:
            import json
            from app.models.domain import Zone, NearbyInfrastructure
            zones_json_path = BASE_DIR / "data" / "zones.json"
            if zones_json_path.exists():
                with open(zones_json_path, "r", encoding="utf-8") as f:
                    for zd in json.load(f):
                        repo.save_zone(Zone(
                            zone_id=zd["zone_id"],
                            name=zd["name"],
                            latitude=zd["latitude"],
                            longitude=zd["longitude"],
                            description=zd.get("description", ""),
                            zone_type=zd.get("zone_type", "Urban"),
                            nearby_infrastructure=NearbyInfrastructure(**zd.get("nearby_infrastructure", {}))
                        ))
        logger.info("Zones initialization finished.")
            
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Smart Urban Air Intelligence — Transparent environmental decision engine and water-efficiency analytics.",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(investigation_router, prefix="/api")
app.include_router(data_health_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "project": settings.PROJECT_NAME,
        "descriptor": settings.PROJECT_DESCRIPTOR,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "team": "Quantified Minds (Ishaan Chaturvedi, Ankit Kumar Tiwari)",
        "docs_url": "/docs",
        "api_health": "/api/health"
    }
