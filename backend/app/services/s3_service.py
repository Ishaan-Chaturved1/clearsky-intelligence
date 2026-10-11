import json
import os
from typing import Optional, Any, Dict
from app.core.logging import logger
from app.core.config import settings

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception


class S3Service:
    """
    AWS S3 service for persisting JSON documents, daily briefs,
    and citizen evidence photos/voice notes.
    """
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region_name = region_name or settings.AWS_REGION
        self.s3_client = None
        self._is_available = False
        self._init_client()

    def _init_client(self):
        if not self.bucket_name:
            return
        if boto3 is None:
            logger.warning("boto3 not installed; S3 integration disabled.")
            return

        try:
            self.s3_client = boto3.client("s3", region_name=self.region_name)
            self._is_available = True
            logger.info(f"S3 client connected for bucket '{self.bucket_name}'")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"S3 client credentials unavailable: {e}")
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available and bool(self.bucket_name)

    def get_json(self, key: str) -> Optional[Any]:
        """Fetch and parse a JSON document from S3."""
        if not self.is_available:
            return None
        try:
            resp = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = resp["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                logger.warning(f"S3 get_json error for {key}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to read JSON from s3://{self.bucket_name}/{key}: {e}")
            return None

    def put_json(self, key: str, data: Any) -> bool:
        """Serialize and upload a JSON document to S3."""
        if not self.is_available:
            return False
        try:
            payload = json.dumps(data, indent=2, default=str).encode("utf-8")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=payload,
                ContentType="application/json"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to write JSON to s3://{self.bucket_name}/{key}: {e}")
            return False

    def upload_file_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload raw binary data and return its public/authenticated S3 URL."""
        if not self.is_available:
            return None
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{key}"
        except Exception as e:
            logger.warning(f"Failed to upload media to s3://{self.bucket_name}/{key}: {e}")
            return None
