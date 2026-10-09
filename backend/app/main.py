import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, BASE_DIR

# Ensure project root is in sys.path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.logging import logger
from app.api.endpoints import router as api_router
from app.repositories.local_repository import SQLiteRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # Auto-seed SQLite database if empty
    if settings.STORAGE_BACKEND == "sqlite":
        repo = SQLiteRepository(settings.SQLITE_DB_PATH)
        existing_zones = repo.list_zones()
        if not existing_zones:
            logger.info("Database is empty. Automatically executing seed script...")
            from scripts.seed_demo_data import seed_database
            seed_database(settings.SQLITE_DB_PATH)
            logger.info("Automatic demo seeding finished.")
            
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
