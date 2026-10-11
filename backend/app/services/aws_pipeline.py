"""
AWS-Native Data Pipeline Services for ClearSky Intelligence.
Orchestrates: EventBridge -> Ingestion Lambda -> SQS (+DLQ) -> Processing Lambda -> DynamoDB & S3 Data Lake.
Includes idempotency keys, schema versioning, partial batch failure handling, and provenance tracking.
"""
import os
import json
import time
import hashlib
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    PollutantValue,
    WeatherConditions,
    FireSummary,
    DataMode
)
from app.data_sources.open_meteo_client import OpenMeteoClient
from app.data_sources.openaq_client import OpenAQClient
from app.data_sources.firms_client import FirmsClient
from app.data_sources.cpcb_client import CPCBClient
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.repositories.s3_repository import S3DataLakeRepository
from app.services.decision_engine import DecisionEngine
from app.services.estimation_service import EstimationService
from app.investigation.event_detector import PollutionEventDetector
from app.core.telemetry import telemetry, generate_correlation_id
from app.core.logging import logger

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


class IngestionMessage(BaseModel):
    """
    Standard versioned SQS message envelope for queued environmental telemetry.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    idempotency_key: str
    zone_id: str
    provider: str
    data_mode: str = "LIVE"
    payload: Dict[str, Any]
    s3_raw_uri: Optional[str] = None
    correlation_id: str = Field(default_factory=generate_correlation_id)


class IngestionPipelineService:
    """
    Ingestion orchestrator triggered by EventBridge cron or manual invocation.
    Fetches raw environmental telemetry, archives to S3 Data Lake, and enqueues to SQS.
    """

    def __init__(
        self,
        sqs_queue_url: Optional[str] = None,
        s3_repo: Optional[S3DataLakeRepository] = None,
        region_name: Optional[str] = None
    ):
        self.sqs_queue_url = sqs_queue_url or os.getenv("SQS_INGESTION_QUEUE_URL") or ""
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.s3_repo = s3_repo or S3DataLakeRepository()
        self.open_meteo = OpenMeteoClient()
        self.openaq = OpenAQClient()
        self.firms = FirmsClient()
        self.cpcb = CPCBClient()
        self.sqs_client = None
        self._init_sqs()

    def _init_sqs(self) -> None:
        if self.sqs_queue_url and boto3 is not None:
            try:
                session = boto3.Session(region_name=self.region_name)
                self.sqs_client = session.client("sqs")
            except Exception as exc:
                logger.debug(f"SQS client initialization skipped ({exc})")

    @staticmethod
    def compute_idempotency_key(zone_id: str, provider: str, obs_time: str) -> str:
        """Computes deterministic hash to identify duplicate observations."""
        raw = f"{zone_id}:{provider.upper()}:{obs_time}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def ingest_zone_telemetry(self, zone: Zone) -> List[IngestionMessage]:
        """
        Polls configured external providers for a zone and creates SQS ingestion messages.
        """
        start_time = time.time()
        correlation_id = generate_correlation_id()
        now_iso = datetime.now(timezone.utc).isoformat()
        messages: List[IngestionMessage] = []

        # 1. Weather & Open-Meteo Air Quality
        try:
            w_res, aq_res = await asyncio.gather(
                self.open_meteo.get_weather(zone.latitude, zone.longitude),
                self.open_meteo.get_air_quality(zone.latitude, zone.longitude),
                return_exceptions=True
            )
            if not isinstance(w_res, Exception) and w_res.is_success and w_res.data:
                idem_key = self.compute_idempotency_key(zone.zone_id, "OPEN_METEO_WEATHER", now_iso)
                raw_uri = self.s3_repo.put_raw_telemetry(
                    provider="OPEN_METEO_WEATHER",
                    record_id=f"{zone.zone_id}_{idem_key[:12]}",
                    data=w_res.data
                )
                msg = IngestionMessage(
                    idempotency_key=idem_key,
                    zone_id=zone.zone_id,
                    provider="OPEN_METEO_WEATHER",
                    payload=w_res.data,
                    s3_raw_uri=raw_uri,
                    correlation_id=correlation_id
                )
                messages.append(msg)
                telemetry.emit_ingestion_metrics("OPEN_METEO", 1, True, (time.time() - start_time) * 1000)
            else:
                telemetry.emit_ingestion_metrics("OPEN_METEO", 0, False, (time.time() - start_time) * 1000)
        except Exception as exc:
            logger.warning(f"Error fetching Open-Meteo for {zone.zone_id}: {exc}")

        # 2. OpenAQ Station Telemetry
        try:
            st_res = await self.openaq.get_nearby_station_measurements(zone.latitude, zone.longitude)
            if st_res.is_success and st_res.data:
                idem_key = self.compute_idempotency_key(zone.zone_id, "OPENAQ", now_iso)
                raw_uri = self.s3_repo.put_raw_telemetry(
                    provider="OPENAQ",
                    record_id=f"{zone.zone_id}_{idem_key[:12]}",
                    data={"stations": st_res.data}
                )
                msg = IngestionMessage(
                    idempotency_key=idem_key,
                    zone_id=zone.zone_id,
                    provider="OPENAQ",
                    payload={"stations": st_res.data},
                    s3_raw_uri=raw_uri,
                    correlation_id=correlation_id
                )
                messages.append(msg)
                telemetry.emit_ingestion_metrics("OPENAQ", len(st_res.data), True, (time.time() - start_time) * 1000)
        except Exception as exc:
            logger.warning(f"Error fetching OpenAQ for {zone.zone_id}: {exc}")

        # 3. NASA FIRMS VIIRS Active Fire Anomalies
        try:
            f_res = await self.firms.check_nearby_fires(zone.latitude, zone.longitude)
            if f_res.is_success and f_res.data:
                idem_key = self.compute_idempotency_key(zone.zone_id, "NASA_FIRMS", now_iso)
                raw_uri = self.s3_repo.put_raw_telemetry(
                    provider="NASA_FIRMS",
                    record_id=f"{zone.zone_id}_{idem_key[:12]}",
                    data=f_res.data
                )
                msg = IngestionMessage(
                    idempotency_key=idem_key,
                    zone_id=zone.zone_id,
                    provider="NASA_FIRMS",
                    payload=f_res.data,
                    s3_raw_uri=raw_uri,
                    correlation_id=correlation_id
                )
                messages.append(msg)
                telemetry.emit_ingestion_metrics("NASA_FIRMS", f_res.data.get("nearby_fires_count", 0), True, (time.time() - start_time) * 1000)
        except Exception as exc:
            logger.warning(f"Error fetching NASA FIRMS for {zone.zone_id}: {exc}")

        # 4. CPCB data.gov.in Station Telemetry (if available)
        try:
            cpcb_res = await self.cpcb.get_realtime_station_measurements(city=zone.name, limit=50)
            if cpcb_res.is_success and cpcb_res.data:
                idem_key = self.compute_idempotency_key(zone.zone_id, "CPCB_DATA_GOV_IN", now_iso)
                raw_uri = self.s3_repo.put_raw_telemetry(
                    provider="CPCB_DATA_GOV_IN",
                    record_id=f"{zone.zone_id}_{idem_key[:12]}",
                    data={"records": cpcb_res.data}
                )
                msg = IngestionMessage(
                    idempotency_key=idem_key,
                    zone_id=zone.zone_id,
                    provider="CPCB_DATA_GOV_IN",
                    payload={"records": cpcb_res.data},
                    s3_raw_uri=raw_uri,
                    correlation_id=correlation_id
                )
                messages.append(msg)
                telemetry.emit_ingestion_metrics("CPCB", len(cpcb_res.data), True, (time.time() - start_time) * 1000)
        except Exception as exc:
            logger.warning(f"Error fetching CPCB for {zone.zone_id}: {exc}")

        return messages

    def send_messages_to_sqs(self, messages: List[IngestionMessage]) -> Tuple[int, int]:
        """
        Sends messages to SQS queue. Returns (success_count, failure_count).
        """
        if not messages:
            return (0, 0)

        success = 0
        failure = 0

        for msg in messages:
            body = msg.model_dump_json()
            if self.sqs_client and self.sqs_queue_url:
                try:
                    self.sqs_client.send_message(
                        QueueUrl=self.sqs_queue_url,
                        MessageBody=body,
                        MessageAttributes={
                            "SchemaVersion": {"DataType": "String", "StringValue": msg.schema_version},
                            "Provider": {"DataType": "String", "StringValue": msg.provider},
                            "ZoneId": {"DataType": "String", "StringValue": msg.zone_id},
                            "CorrelationId": {"DataType": "String", "StringValue": msg.correlation_id}
                        }
                    )
                    success += 1
                except Exception as exc:
                    logger.error(f"Failed sending SQS message for {msg.zone_id} ({exc})")
                    failure += 1
            else:
                # Local logging if SQS unconfigured
                logger.debug(f"[LOCAL SQS ENQUEUE] {msg.provider} -> {msg.zone_id} ({msg.idempotency_key[:8]})")
                success += 1

        return (success, failure)


class ProcessingPipelineService:
    """
    Processing worker triggered by SQS events.
    Validates message schema, enforces idempotency, evaluates decisions & events,
    and updates DynamoDB and S3 data lake.
    """

    def __init__(
        self,
        repository: Optional[DynamoDBRepository] = None,
        s3_repo: Optional[S3DataLakeRepository] = None
    ):
        self.repository = repository or DynamoDBRepository()
        self.s3_repo = s3_repo or S3DataLakeRepository()
        self.decision_engine = DecisionEngine()
        self.event_detector = PollutionEventDetector()
        self.processed_idempotency_keys = set()

    def process_sqs_batch(self, sqs_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes an SQS batch of records.
        Returns AWS Lambda partial batch failure format:
        {'batchItemFailures': [{'itemIdentifier': 'msg-id'}]}
        """
        start_time = time.time()
        batch_item_failures = []
        processed_count = 0

        for rec in sqs_records:
            msg_id = rec.get("messageId", str(uuid.uuid4()))
            raw_body = rec.get("body", "{}")

            try:
                data = json.loads(raw_body)
                msg = IngestionMessage(**data)

                # Schema version guard
                if msg.schema_version != "1.0":
                    logger.error(f"Unsupported message schema version: {msg.schema_version}")
                    # Non-retryable error, do not add to batchItemFailures to avoid endless poison pills
                    continue

                # Idempotency guard: skip duplicates
                if msg.idempotency_key in self.processed_idempotency_keys:
                    logger.info(f"Duplicate message skipped via idempotency key: {msg.idempotency_key[:12]}")
                    processed_count += 1
                    continue

                self.process_single_message(msg)
                self.processed_idempotency_keys.add(msg.idempotency_key)
                processed_count += 1

            except Exception as exc:
                logger.error(f"Processing error for SQS message {msg_id}: {exc}")
                # Mark as failed for SQS retry / DLQ redrive
                batch_item_failures.append({"itemIdentifier": msg_id})

        duration_ms = (time.time() - start_time) * 1000
        telemetry.emit_processing_metrics(processed_count, len(batch_item_failures), duration_ms)

        return {
            "batchItemFailures": batch_item_failures,
            "processed_count": processed_count,
            "failed_count": len(batch_item_failures)
        }

    def process_single_message(self, msg: IngestionMessage) -> None:
        """
        Processes a single validated ingestion message.
        """
        zone = self.repository.get_zone(msg.zone_id)
        if not zone:
            logger.warning(f"Zone {msg.zone_id} not found in repository. Skipping evaluation.")
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        reading_id = f"RD-{msg.zone_id}-{now_iso}"

        # Build environmental reading from message payload
        weather = WeatherConditions()
        pm25_val = None
        pm10_val = None
        fire_summary = FireSummary()

        if msg.provider == "OPEN_METEO_WEATHER":
            weather = WeatherConditions(**{
                k: v for k, v in msg.payload.items() if k in WeatherConditions.model_fields
            })
        elif msg.provider == "NASA_FIRMS":
            fire_summary = FireSummary(**msg.payload)

        # Assemble reading
        reading = EnvironmentalReading(
            reading_id=reading_id,
            zone_id=msg.zone_id,
            timestamp=now_iso,
            pm25=PollutantValue(value=pm25_val, data_type="observed" if pm25_val else "unavailable"),
            pm10=PollutantValue(value=pm10_val, data_type="observed" if pm10_val else "unavailable"),
            pm_ratio=None,
            weather=weather,
            fire_summary=fire_summary,
            data_mode=DataMode.LIVE,
            is_stale=False
        )

        # Save to DynamoDB
        self.repository.save_reading(reading)

        # Archive to S3 Data Lake
        self.s3_repo.put_processed_reading(
            zone_id=msg.zone_id,
            reading_id=reading_id,
            data=reading.model_dump()
        )

        # Evaluate decision
        decision = self.decision_engine.evaluate(
            zone=zone,
            reading=reading,
            scored_at=now_iso,
            source_status={msg.provider.lower(): "available"}
        )
        self.repository.save_decision(decision)
