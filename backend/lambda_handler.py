import asyncio
import json
from app.main import app
from app.core.logging import logger
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.services.ingestion_service import IngestionService

# Try importing Mangum for ASGI Lambda adapter
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    def handler(event, context):
        logger.warning("Mangum is not installed. To run on AWS Lambda, install mangum package.")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Mangum ASGI adapter missing"})
        }

def ingestion_handler(event, context):
    """
    AWS Lambda entrypoint triggered by EventBridge cron schedule every 30 minutes.
    """
    logger.info("Executing scheduled ingestion and scoring pipeline via EventBridge trigger")
    repo = DynamoDBRepository()
    ingestion = IngestionService(repo)
    
    loop = asyncio.get_event_loop()
    decisions = loop.run_until_complete(ingestion.run_full_cycle())
    
    logger.info(f"Scheduled cycle completed. Scored {len(decisions)} zones.")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Successfully ingested and scored {len(decisions)} zones.",
            "scored_zones_count": len(decisions)
        })
    }
