"""
Telemetry, CloudWatch Metrics, and SNS Operational Alerting for ClearSky Intelligence.
Maintains operational visibility across ingestion, SQS processing, and storage.
"""
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from app.core.logging import logger
from app.core.config import settings

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


class CloudWatchTelemetry:
    """
    Publishes custom metrics to Amazon CloudWatch under namespace 'ClearSky/Pipeline'.
    Gracefully degrades to local structured logging when AWS credentials or boto3 are absent.
    """

    def __init__(self, namespace: str = "ClearSky/Pipeline", region_name: Optional[str] = None):
        self.namespace = namespace
        self.region_name = region_name or settings.AWS_REGION
        self.cloudwatch = None
        self.sns = None
        self.sns_topic_arn = os.getenv("SNS_ALERT_TOPIC_ARN") or ""
        self._init_clients()

    def _init_clients(self) -> None:
        if boto3 is None:
            return
        try:
            session = boto3.Session(region_name=self.region_name)
            self.cloudwatch = session.client("cloudwatch")
            if self.sns_topic_arn:
                self.sns = session.client("sns")
        except Exception as exc:
            logger.debug(f"CloudWatch/SNS client initialization skipped: {exc}")

    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Emits a single metric datum to CloudWatch.
        """
        dims = [{"Name": k, "Value": v} for k, v in (dimensions or {}).items()]
        # Add environment dimension by default
        dims.append({"Name": "Environment", "Value": settings.ENVIRONMENT})

        if not self.cloudwatch:
            logger.debug(f"[METRIC LOG] {self.namespace} -> {metric_name}: {value} {unit} {dims}")
            return False

        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Value": float(value),
                        "Unit": unit,
                        "Timestamp": time.time(),
                        "Dimensions": dims
                    }
                ]
            )
            return True
        except Exception as exc:
            logger.debug(f"Failed to publish metric {metric_name} to CloudWatch: {exc}")
            return False

    def emit_ingestion_metrics(
        self,
        provider: str,
        observations_count: int,
        is_success: bool,
        duration_ms: float
    ) -> None:
        """Helper to emit standard ingestion metrics."""
        dims = {"Provider": provider}
        self.put_metric("IngestedObservationsCount", observations_count, "Count", dims)
        self.put_metric("IngestionDurationMs", duration_ms, "Milliseconds", dims)
        if not is_success:
            self.put_metric("IngestionFailures", 1, "Count", dims)

    def emit_processing_metrics(
        self,
        processed_count: int,
        failed_count: int,
        duration_ms: float
    ) -> None:
        """Helper to emit standard SQS processing metrics."""
        self.put_metric("ProcessedMessagesCount", processed_count, "Count")
        self.put_metric("ProcessingDurationMs", duration_ms, "Milliseconds")
        if failed_count > 0:
            self.put_metric("ProcessingFailures", failed_count, "Count")

    def emit_dead_letter_metric(self, dead_letter_count: int) -> None:
        """Helper to emit dead-letter message metric."""
        self.put_metric("DeadLetterMessages", dead_letter_count, "Count")

    def publish_operational_alert(self, subject: str, message: str) -> bool:
        """
        Publishes operational notification to SNS Topic (e.g., DLQ alerts, pipeline downtime).
        """
        if not self.sns or not self.sns_topic_arn:
            logger.warning(f"[OPERATIONAL ALERT] {subject}: {message}")
            return False

        try:
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=f"[ClearSky Alert] {subject[:90]}",
                Message=message
            )
            logger.info(f"Published operational alert to SNS: {subject}")
            return True
        except Exception as exc:
            logger.error(f"Failed to publish operational alert to SNS: {exc}")
            return False


def generate_correlation_id() -> str:
    """Generates a UUID-based correlation ID for request and message tracing."""
    return f"csky-{uuid.uuid4().hex[:12]}"


# Global singleton telemetry instance
telemetry = CloudWatchTelemetry()
