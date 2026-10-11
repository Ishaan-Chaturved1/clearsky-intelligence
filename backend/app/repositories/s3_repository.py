"""
S3 Data Lake and Historical Storage Repository for ClearSky Intelligence.
Stores raw environmental telemetry, normalized observations, and investigation reports
with Hive-style date partitioning (year=YYYY/month=MM/day=DD) suitable for AWS Glue and Athena.
"""
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.logging import logger
from app.core.config import settings

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


class S3DataLakeRepository:
    """
    Manages archival writes and reads to the AWS S3 Data Lake bucket.
    Partitioning:
      - Raw: raw/year=YYYY/month=MM/day=DD/provider={provider}/{id}.json
      - Processed: processed/year=YYYY/month=MM/day=DD/zone={zone}/{id}.json
      - Investigations: investigations/year=YYYY/month=MM/day=DD/{id}.json
    Falls back gracefully to data/s3_lake/ when S3 is unconfigured.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        local_fallback_dir: str = "data/s3_lake"
    ):
        self.bucket_name = bucket_name or os.getenv("S3_DATA_LAKE_BUCKET") or ""
        self.region_name = region_name or settings.AWS_REGION
        self.local_dir = Path(local_fallback_dir)
        self.s3_client = None
        self._is_available = False
        self._init_client()

    def _init_client(self) -> None:
        strict_storage = os.getenv("STRICT_AWS_STORAGE", "false").lower() == "true"
        if not self.bucket_name or boto3 is None:
            if strict_storage:
                raise RuntimeError(f"S3 Data Lake bucket '{self.bucket_name}' or boto3 unavailable in strict production mode.")
            self._is_available = False
            return
        try:
            session = boto3.Session(region_name=self.region_name)
            self.s3_client = session.client("s3")
            # Probe bucket existence with HeadBucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self._is_available = True
            logger.info(f"S3 Data Lake client connected to bucket: {self.bucket_name}")
        except Exception as exc:
            if strict_storage:
                logger.error(f"FATAL: S3 Data Lake bucket '{self.bucket_name}' head check failed in strict production mode ({exc}). Ephemeral fallback disallowed.")
                raise RuntimeError(f"S3 Data Lake bucket '{self.bucket_name}' head check failed: {exc}") from exc
            logger.debug(f"S3 bucket {self.bucket_name} head check failed ({exc}). Using local fallback.")
            self._is_available = False

    def is_available(self) -> bool:
        """Returns True if the live S3 bucket is accessible."""
        return self._is_available

    def _get_date_partitions(self, dt: Optional[datetime] = None) -> str:
        """Returns Hive-style date partition prefix: year=YYYY/month=MM/day=DD"""
        d = dt or datetime.now(timezone.utc)
        return f"year={d.strftime('%Y')}/month={d.strftime('%m')}/day={d.strftime('%d')}"

    def put_raw_telemetry(
        self,
        provider: str,
        record_id: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Stores raw provider payload in raw/ partition.
        Returns the S3 URI or local fallback URI.
        """
        date_part = self._get_date_partitions(timestamp)
        s3_key = f"raw/{date_part}/provider={provider.lower()}/{record_id}.json"
        strict_storage = os.getenv("STRICT_AWS_STORAGE", "false").lower() == "true"
        content = json.dumps(data, indent=2, default=str)

        if self._is_available and self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                    ServerSideEncryption="AES256"
                )
                return f"s3://{self.bucket_name}/{s3_key}"
            except Exception as exc:
                if strict_storage:
                    logger.error(f"FATAL: Failed writing raw telemetry to S3 in strict production mode: {exc}")
                    raise RuntimeError(f"S3 write failed in strict production mode: {exc}") from exc
                logger.warning(f"Failed writing raw telemetry to S3 ({exc}). Falling back to local disk.")

        if strict_storage:
            raise RuntimeError("Cannot write raw telemetry to S3: S3 Data Lake is unavailable in strict production mode.")

        # Local fallback
        dest = self.local_dir / s3_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return str(dest)

    def put_processed_reading(
        self,
        zone_id: str,
        reading_id: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Stores normalized reading in processed/ partition.
        Returns the S3 URI or local fallback URI.
        """
        strict_storage = os.getenv("STRICT_AWS_STORAGE", "false").lower() == "true"
        date_part = self._get_date_partitions(timestamp)
        s3_key = f"processed/{date_part}/zone={zone_id}/{reading_id}.json"
        content = json.dumps(data, indent=2, default=str)

        if self._is_available and self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                    ServerSideEncryption="AES256"
                )
                return f"s3://{self.bucket_name}/{s3_key}"
            except Exception as exc:
                if strict_storage:
                    logger.error(f"FATAL: Failed writing processed reading to S3 in strict production mode: {exc}")
                    raise RuntimeError(f"S3 write failed in strict production mode: {exc}") from exc
                logger.warning(f"Failed writing processed reading to S3 ({exc}). Falling back to local disk.")

        if strict_storage:
            raise RuntimeError("Cannot write processed reading to S3: S3 Data Lake is unavailable in strict production mode.")

        dest = self.local_dir / s3_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return str(dest)

    def put_investigation_dossier(
        self,
        investigation_id: str,
        dossier_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Stores completed investigation dossier in investigations/ partition.
        """
        strict_storage = os.getenv("STRICT_AWS_STORAGE", "false").lower() == "true"
        date_part = self._get_date_partitions(timestamp)
        s3_key = f"investigations/{date_part}/{investigation_id}.json"
        content = json.dumps(dossier_data, indent=2, default=str)

        if self._is_available and self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                    ServerSideEncryption="AES256"
                )
                return f"s3://{self.bucket_name}/{s3_key}"
            except Exception as exc:
                if strict_storage:
                    logger.error(f"FATAL: Failed writing investigation to S3 in strict production mode: {exc}")
                    raise RuntimeError(f"S3 write failed in strict production mode: {exc}") from exc
                logger.warning(f"Failed writing investigation to S3 ({exc}). Falling back to local disk.")

        if strict_storage:
            raise RuntimeError("Cannot write investigation to S3: S3 Data Lake is unavailable in strict production mode.")

        dest = self.local_dir / s3_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return str(dest)

    def get_object_content(self, s3_key: str) -> Optional[str]:
        """
        Reads content of an object by S3 key or local fallback path.
        """
        if self._is_available and self.s3_client:
            try:
                resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return resp["Body"].read().decode("utf-8")
            except Exception as exc:
                logger.warning(f"Failed reading object from S3 ({exc}): {s3_key}")

        local_path = self.local_dir / s3_key
        if local_path.exists():
            return local_path.read_text(encoding="utf-8")
        return None
