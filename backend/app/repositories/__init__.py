from app.core.config import settings
from app.repositories.base import BaseRepository
from app.repositories.local_repository import SQLiteRepository
from app.repositories.json_repository import JSONRepository
from app.repositories.dynamodb_repository import DynamoDBRepository


def get_repository() -> BaseRepository:
    """
    Repository factory supporting:
      - 'dynamodb': AWS DynamoDB (with JSON fallback)
      - 'json': Local JSON files + AWS S3 sync
      - 'sqlite': Local SQLite database
    """
    backend = settings.STORAGE_BACKEND.lower().strip()
    if backend == "dynamodb":
        return DynamoDBRepository(region_name=settings.AWS_REGION)
    elif backend == "json":
        return JSONRepository(data_dir=settings.JSON_STORAGE_DIR)
    else:
        return SQLiteRepository(settings.SQLITE_DB_PATH)


__all__ = [
    "BaseRepository",
    "SQLiteRepository",
    "JSONRepository",
    "DynamoDBRepository",
    "get_repository"
]
