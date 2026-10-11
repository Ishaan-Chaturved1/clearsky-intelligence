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
    Polls providers, archives raw payloads to S3, and sends versioned messages to SQS.
    """
    logger.info("Executing scheduled ingestion pipeline via EventBridge trigger")
    repo = DynamoDBRepository()
    zones = repo.list_zones()
    
    from app.services.aws_pipeline import IngestionPipelineService
    pipeline = IngestionPipelineService()
    
    loop = asyncio.get_event_loop()
    all_messages = []
    for zone in zones:
        msgs = loop.run_until_complete(pipeline.ingest_zone_telemetry(zone))
        all_messages.extend(msgs)
        
    success, failure = pipeline.send_messages_to_sqs(all_messages)
    logger.info(f"Ingestion cycle completed. Enqueued {success} messages (failed: {failure}).")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Successfully ingested telemetry for {len(zones)} zones.",
            "enqueued_messages": success,
            "failed_messages": failure
        })
    }


def sqs_processing_handler(event, context):
    """
    AWS Lambda entrypoint triggered by SQS ingestion queue.
    Processes telemetry batches, enforces idempotency, evaluates decisions & events,
    and returns batchItemFailures for partial batch failure reporting.
    """
    records = event.get("Records", [])
    logger.info(f"Processing SQS batch containing {len(records)} records")
    
    from app.services.aws_pipeline import ProcessingPipelineService
    processor = ProcessingPipelineService()
    
    result = processor.process_sqs_batch(records)
    logger.info(f"Batch processed. Success: {result['processed_count']}, Failures: {result['failed_count']}")
    
    # Standard AWS Lambda SQS partial batch response format
    return {
        "batchItemFailures": result["batchItemFailures"]
    }
