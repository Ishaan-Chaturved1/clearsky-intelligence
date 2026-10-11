"""
Data-Source Health and Verification Service for ClearSky Intelligence.
Provides rigorous live operational checking and stored dataset auditing across
all registered environmental data sources.
"""
import os
import re
import time
import math
import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.config import settings
from app.services.data_source_registry import (
    DataSourceMetadata,
    DataSourceRegistry,
    data_source_registry,
    DataCategory,
    ProviderType
)
from app.data_sources.cpcb_client import CPCBClient
from app.data_sources.openaq_client import OpenAQClient
from app.data_sources.open_meteo_client import OpenMeteoClient
from app.data_sources.firms_client import FirmsClient
from app.data_sources.overpass_client import OverpassClient
from app.services.geocoding_service import GeocodingService
from app.repositories import get_repository
from app.repositories.s3_repository import S3DataLakeRepository
from app.data_sources.base import global_cache


class VerificationStatus(str, Enum):
    """
    Standard 10-state health and verification status enumeration.
    """
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    EMPTY = "EMPTY"
    MISCONFIGURED = "MISCONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"
    NOT_CHECKED = "NOT_CHECKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceVerificationResult(BaseModel):
    """
    Structured, fully validated verification outcome for a single environmental data source.
    """
    source_id: str
    source_name: str
    status: VerificationStatus
    checked_at: datetime
    last_attempt_at: datetime
    last_successful_fetch_at: Optional[datetime] = None
    latest_observation_at: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    http_status: Optional[int] = None
    records_received: int = 0
    records_valid: int = 0
    records_rejected: int = 0
    expected_fields: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    missing_value_counts: Dict[str, int] = Field(default_factory=dict)
    unique_station_count: Optional[int] = None
    geographic_coverage: Optional[str] = None
    temporal_coverage: Optional[str] = None
    cache_age_seconds: Optional[float] = None
    freshness_threshold_seconds: int = 7200
    data_quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    retry_count: int = 0
    provenance: str = "UNKNOWN"
    verification_method: str = "LIVE_OPERATIONAL_CHECK"
    limitations: List[str] = Field(default_factory=list)


class DataHealthSummary(BaseModel):
    """
    Aggregated health assessment covering all registered sources.
    """
    total_registered_sources: int
    total_checked: int
    healthy_count: int
    degraded_count: int
    stale_count: int
    empty_count: int
    misconfigured_count: int
    unavailable_count: int
    rate_limited_count: int
    error_count: int
    not_checked_count: int
    datasets_with_missing_required_fields: int
    datasets_with_insufficient_coverage: int
    most_recent_successful_fetch: Optional[datetime] = None
    overall_status: VerificationStatus
    recommended_actions: List[str] = Field(default_factory=list)
    verification_mode: str  # LIVE_OPERATIONAL_CHECK or STORED_DATASET_AUDIT
    results: List[SourceVerificationResult] = Field(default_factory=list)

    @property
    def total_registered(self) -> int:
        return self.total_registered_sources

    @property
    def checked_count(self) -> int:
        return self.total_checked

    @property
    def sources(self) -> List[SourceVerificationResult]:
        return self.results


def sanitize_message(msg: str) -> str:
    """Removes API keys, map keys, and sensitive tokens from error/warning strings."""
    if not msg:
        return ""
    # Mask potential hex or alphanumeric tokens of length > 16
    cleaned = re.sub(r'([?&]api[_-]?key=)[^&\s]+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    cleaned = re.sub(r'(MAP_KEY=)[^&\s]+', r'\1[REDACTED]', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'([A-Fa-f0-9]{24,})', '[REDACTED_TOKEN]', cleaned)
    return cleaned


class DataHealthService:
    """
    Core data health and verification service supporting Live Operational Checks
    and Stored Dataset Audits.
    """

    def __init__(self, registry: Optional[DataSourceRegistry] = None):
        self.registry = registry or data_source_registry
        self.cpcb_client = CPCBClient()
        self.openaq_client = OpenAQClient()
        self.open_meteo_client = OpenMeteoClient()
        self.firms_client = FirmsClient()
        self.overpass_client = OverpassClient()
        self.geocoding_service = GeocodingService()
        self._last_verification_cache: Dict[str, SourceVerificationResult] = {}

    def get_registered_sources(self) -> List[DataSourceMetadata]:
        return self.registry.list_sources()

    def get_source_metadata(self, source_id: str) -> Optional[DataSourceMetadata]:
        return self.registry.get_source(source_id)

    async def check_source(self, source_id: str) -> SourceVerificationResult:
        """
        Executes a live operational check for a specific registered source.
        """
        source = self.registry.get_source(source_id)
        if not source:
            raise ValueError(f"Unknown data source ID: '{source_id}'")

        now_utc = datetime.now(timezone.utc)
        result = await self._run_live_check(source, now_utc)
        self._last_verification_cache[source_id] = result
        return result

    async def check_all_sources(self) -> DataHealthSummary:
        """
        Mode 1: Executes concurrent, bounded live operational checks across all registered sources.
        """
        sources = self.registry.list_sources()
        now_utc = datetime.now(timezone.utc)

        # Run checks with bounded concurrency
        semaphore = asyncio.Semaphore(5)

        async def _bounded_check(src: DataSourceMetadata) -> SourceVerificationResult:
            async with semaphore:
                try:
                    return await self._run_live_check(src, now_utc)
                except Exception as ex:
                    logger.error(f"Unexpected error verifying source {src.source_id}: {ex}")
                    return SourceVerificationResult(
                        source_id=src.source_id,
                        source_name=src.source_name,
                        status=VerificationStatus.ERROR,
                        checked_at=now_utc,
                        last_attempt_at=now_utc,
                        expected_fields=src.supported_fields,
                        freshness_threshold_seconds=src.freshness_threshold_seconds,
                        errors=[sanitize_message(str(ex))],
                        verification_method="LIVE_OPERATIONAL_CHECK",
                        limitations=src.limitations
                    )

        tasks = [_bounded_check(s) for s in sources]
        results = await asyncio.gather(*tasks)

        for res in results:
            self._last_verification_cache[res.source_id] = res

        return self._build_summary(results, "LIVE_OPERATIONAL_CHECK")

    async def audit_stored_datasets(self) -> DataHealthSummary:
        """
        Mode 2: Stored Dataset Audit.
        Inspects existing persisted records, SQLite tables, JSON configurations,
        and local/S3 partitions without requiring live provider requests.
        """
        sources = self.registry.list_sources()
        now_utc = datetime.now(timezone.utc)
        results: List[SourceVerificationResult] = []

        for src in sources:
            try:
                res = await self._run_stored_audit(src, now_utc)
                results.append(res)
            except Exception as ex:
                logger.error(f"Error auditing stored dataset for {src.source_id}: {ex}")
                results.append(
                    SourceVerificationResult(
                        source_id=src.source_id,
                        source_name=src.source_name,
                        status=VerificationStatus.ERROR,
                        checked_at=now_utc,
                        last_attempt_at=now_utc,
                        expected_fields=src.supported_fields,
                        freshness_threshold_seconds=src.freshness_threshold_seconds,
                        errors=[sanitize_message(str(ex))],
                        verification_method="STORED_DATASET_AUDIT",
                        limitations=src.limitations
                    )
                )

        return self._build_summary(results, "STORED_DATASET_AUDIT")

    def get_cached_status(self) -> DataHealthSummary:
        """
        Returns the most recent verification outcome or marks un-checked sources as NOT_CHECKED.
        """
        sources = self.registry.list_sources()
        now_utc = datetime.now(timezone.utc)
        results: List[SourceVerificationResult] = []

        for src in sources:
            if src.source_id in self._last_verification_cache:
                results.append(self._last_verification_cache[src.source_id])
            else:
                results.append(
                    SourceVerificationResult(
                        source_id=src.source_id,
                        source_name=src.source_name,
                        status=VerificationStatus.NOT_CHECKED,
                        checked_at=now_utc,
                        last_attempt_at=now_utc,
                        expected_fields=src.supported_fields,
                        freshness_threshold_seconds=src.freshness_threshold_seconds,
                        warnings=["Source has not yet been audited or verified during this session."],
                        verification_method="UNCHECKED",
                        limitations=src.limitations
                    )
                )

        return self._build_summary(results, "CACHED_STATUS")

    # =========================================================================
    # LIVE CHECK IMPLEMENTATION
    # =========================================================================

    async def _run_live_check(self, src: DataSourceMetadata, now_utc: datetime) -> SourceVerificationResult:
        start_time = time.time()
        res_fields = src.supported_fields
        t_sec = src.freshness_threshold_seconds

        # Check required configuration
        missing_configs = [cfg for cfg in src.required_config if not os.getenv(cfg)]
        if missing_configs:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.MISCONFIGURED,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                expected_fields=res_fields,
                missing_fields=[],
                freshness_threshold_seconds=t_sec,
                errors=[f"Missing required configuration: {', '.join(missing_configs)}"],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="CONFIGURATION"
            )

        # Dispatch per source adapter
        if src.source_id == "cpcb_in":
            return await self._verify_cpcb(src, now_utc, start_time)
        elif src.source_id == "openaq_v3":
            return await self._verify_openaq(src, now_utc, start_time)
        elif src.source_id == "open_meteo_weather":
            return await self._verify_open_meteo_weather(src, now_utc, start_time)
        elif src.source_id == "open_meteo_air_quality":
            return await self._verify_open_meteo_air_quality(src, now_utc, start_time)
        elif src.source_id == "nasa_firms_viirs":
            return await self._verify_firms(src, now_utc, start_time)
        elif src.source_id == "osm_overpass":
            return await self._verify_overpass(src, now_utc, start_time)
        elif src.source_id == "nominatim_geocoding":
            return await self._verify_nominatim(src, now_utc, start_time)
        elif src.source_id == "local_station_db":
            return await self._verify_local_db(src, now_utc, start_time)
        elif src.source_id == "s3_data_lake":
            return await self._verify_s3_data_lake(src, now_utc, start_time)
        else:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.NOT_APPLICABLE,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                expected_fields=res_fields,
                freshness_threshold_seconds=t_sec,
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations
            )

    async def _verify_cpcb(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        if not self.cpcb_client.is_available():
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.MISCONFIGURED,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=["CPCB_DATA_GOV_API_KEY environment variable is not configured."],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GROUND_MEASUREMENT"
            )

        fetch_res = await self.cpcb_client.get_realtime_station_measurements(city="Delhi", state="Delhi", limit=5)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "401" in err or "403" in err or "CREDENTIALS" in err:
                status = VerificationStatus.MISCONFIGURED
                http_code = 401 if "401" in err else 403
            elif "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429
            elif "TIMEOUT" in err or "Timeout" in err:
                status = VerificationStatus.UNAVAILABLE
            elif "500" in err or "502" in err or "503" in err:
                status = VerificationStatus.UNAVAILABLE
                http_code = 500

            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GROUND_MEASUREMENT"
            )

        data = fetch_res.data or []
        records_rec = len(data)
        if records_rec == 0:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.EMPTY,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                last_successful_fetch_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=200,
                records_received=0,
                records_valid=0,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                warnings=["Provider contacted successfully, but returned zero records for query parameters."],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GROUND_MEASUREMENT"
            )

        valid_count = 0
        rejected_count = 0
        latest_obs_dt: Optional[datetime] = None
        unique_stations = set()

        for rec in data:
            station = getattr(rec, "station_name", None) or rec.get("station_name")
            conc = getattr(rec, "concentration", None) if hasattr(rec, "concentration") else rec.get("concentration")
            ts = getattr(rec, "timestamp", None) or rec.get("timestamp")

            if station:
                unique_stations.add(station)

            # Validation: finite, non-negative
            if conc is not None and not (math.isnan(conc) or math.isinf(conc)) and conc >= 0:
                valid_count += 1
            else:
                rejected_count += 1

            if ts:
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if latest_obs_dt is None or dt > latest_obs_dt:
                        latest_obs_dt = dt
                except Exception:
                    pass

        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        # Freshness check
        if latest_obs_dt:
            age = (now_utc - latest_obs_dt).total_seconds()
            if age > src.freshness_threshold_seconds:
                status = VerificationStatus.STALE
                warnings.append(f"Observation timestamp is {age / 3600:.1f} hours old (threshold is {src.freshness_threshold_seconds / 3600:.1f}h).")

        if rejected_count > 0 and status == VerificationStatus.HEALTHY:
            status = VerificationStatus.DEGRADED
            warnings.append(f"{rejected_count} records rejected due to missing, invalid, or negative concentration values.")

        quality_score = round((valid_count / records_rec) * 100.0, 1) if records_rec > 0 else 0.0

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            latest_observation_at=latest_obs_dt,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=records_rec,
            records_valid=valid_count,
            records_rejected=rejected_count,
            expected_fields=src.supported_fields,
            unique_station_count=len(unique_stations),
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=quality_score,
            warnings=warnings,
            provenance="GROUND_MEASUREMENT",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_openaq(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        # Bounded query around Central Delhi (28.6139, 77.2090)
        fetch_res = await self.openaq_client.get_nearby_station_measurements(28.6139, 77.2090, radius_km=15.0)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "401" in err or "403" in err or "not configured" in err:
                status = VerificationStatus.MISCONFIGURED
                http_code = 401 if "401" in err else (403 if "403" in err else None)
            elif "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429

            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GROUND_MEASUREMENT"
            )

        data = fetch_res.data or []
        records_rec = len(data)
        if records_rec == 0:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.EMPTY,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                last_successful_fetch_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=200,
                records_received=0,
                records_valid=0,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                warnings=["Valid 200 response returned 0 stations within 15 km radius."],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GROUND_MEASUREMENT"
            )

        valid_count = 0
        rejected_count = 0
        latest_obs_dt: Optional[datetime] = None
        unique_stations = set()

        for st in data:
            st_id = st.get("station_id") or st.get("name")
            if st_id:
                unique_stations.add(st_id)
            lat = st.get("latitude")
            lon = st.get("longitude")
            pm25 = st.get("pm25")
            pm10 = st.get("pm10")
            ts = st.get("observed_at") or st.get("timestamp")

            # Check validity
            is_valid = True
            if lat is not None and lon is not None:
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    is_valid = False
            if pm25 is not None and (math.isnan(pm25) or math.isinf(pm25) or pm25 < 0):
                is_valid = False
            if pm10 is not None and (math.isnan(pm10) or math.isinf(pm10) or pm10 < 0):
                is_valid = False

            if is_valid:
                valid_count += 1
            else:
                rejected_count += 1

            if ts:
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if latest_obs_dt is None or dt > latest_obs_dt:
                        latest_obs_dt = dt
                except Exception:
                    pass

        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        if latest_obs_dt:
            age = (now_utc - latest_obs_dt).total_seconds()
            if age > src.freshness_threshold_seconds:
                status = VerificationStatus.STALE
                warnings.append(f"Observations are {age / 3600:.1f} hours old (> {src.freshness_threshold_seconds / 3600:.1f}h threshold).")

        if rejected_count > 0 and status == VerificationStatus.HEALTHY:
            status = VerificationStatus.DEGRADED
            warnings.append(f"{rejected_count} station records rejected due to invalid coordinates or measurements.")

        quality_score = round((valid_count / records_rec) * 100.0, 1) if records_rec > 0 else 0.0

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            latest_observation_at=latest_obs_dt,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=records_rec,
            records_valid=valid_count,
            records_rejected=rejected_count,
            expected_fields=src.supported_fields,
            unique_station_count=len(unique_stations),
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=quality_score,
            warnings=warnings,
            provenance="GROUND_MEASUREMENT",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_open_meteo_weather(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        fetch_res = await self.open_meteo_client.get_weather(28.6139, 77.2090)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429
            elif "500" in err or "502" in err or "503" in err:
                http_code = 500

            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="MODELED"
            )

        data = fetch_res.data or {}
        missing_fields = [f for f in src.supported_fields if f not in data or data[f] is None]
        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        if missing_fields:
            status = VerificationStatus.DEGRADED
            warnings.append(f"Missing atmospheric fields: {', '.join(missing_fields)}")

        raw_ts = data.get("raw_timestamp")
        latest_obs_dt: Optional[datetime] = None
        if raw_ts:
            try:
                latest_obs_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                if latest_obs_dt.tzinfo is None:
                    latest_obs_dt = latest_obs_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        if latest_obs_dt:
            age = (now_utc - latest_obs_dt).total_seconds()
            if age > src.freshness_threshold_seconds:
                status = VerificationStatus.STALE
                warnings.append(f"Model forecast timestamp is {age / 3600:.1f} hours old.")

        records_valid = len(src.supported_fields) - len(missing_fields)
        quality_score = round((records_valid / len(src.supported_fields)) * 100.0, 1)

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            latest_observation_at=latest_obs_dt,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=1,
            records_valid=1 if not missing_fields else 0,
            records_rejected=0 if not missing_fields else 1,
            expected_fields=src.supported_fields,
            missing_fields=missing_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=quality_score,
            warnings=warnings,
            provenance="MODELED",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_open_meteo_air_quality(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        fetch_res = await self.open_meteo_client.get_air_quality(28.6139, 77.2090)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="MODELED"
            )

        data = fetch_res.data or {}
        missing_fields = [f for f in src.supported_fields if f not in data or data[f] is None]
        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        if missing_fields:
            status = VerificationStatus.DEGRADED
            warnings.append(f"Missing pollutant modeled fields: {', '.join(missing_fields)}")

        raw_ts = data.get("raw_timestamp")
        latest_obs_dt: Optional[datetime] = None
        if raw_ts:
            try:
                latest_obs_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                if latest_obs_dt.tzinfo is None:
                    latest_obs_dt = latest_obs_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        if latest_obs_dt:
            age = (now_utc - latest_obs_dt).total_seconds()
            if age > src.freshness_threshold_seconds:
                status = VerificationStatus.STALE
                warnings.append(f"Chemical reanalysis timestamp is {age / 3600:.1f} hours old.")

        records_valid = len(src.supported_fields) - len(missing_fields)
        quality_score = round((records_valid / len(src.supported_fields)) * 100.0, 1)

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            latest_observation_at=latest_obs_dt,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=1,
            records_valid=1 if not missing_fields else 0,
            records_rejected=0 if not missing_fields else 1,
            expected_fields=src.supported_fields,
            missing_fields=missing_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=quality_score,
            warnings=warnings,
            provenance="MODELED",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_firms(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        if not self.firms_client.is_available():
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.MISCONFIGURED,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=["NASA_FIRMS_MAP_KEY environment variable is not configured."],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="SATELLITE_DERIVED"
            )

        fetch_res = await self.firms_client.check_nearby_fires(28.6139, 77.2090, radius_km=50.0)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "401" in err or "403" in err or "not configured" in err:
                status = VerificationStatus.MISCONFIGURED
                http_code = 401 if "401" in err else 403
            elif "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429

            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="SATELLITE_DERIVED"
            )

        data = fetch_res.data or {}
        fires = data.get("details", [])
        total_fires = data.get("nearby_fires_count", 0)

        if total_fires == 0:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.EMPTY,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                last_successful_fetch_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=200,
                records_received=0,
                records_valid=0,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                warnings=["Zero active thermal fire anomalies detected in query domain."],
                provenance="SATELLITE_DERIVED",
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations
            )

        valid_count = 0
        rejected_count = 0
        for f in fires:
            flat = f.get("latitude") if isinstance(f, dict) else getattr(f, "latitude", None)
            flon = f.get("longitude") if isinstance(f, dict) else getattr(f, "longitude", None)
            if flat is not None and flon is not None:
                if not (-90.0 <= flat <= 90.0 and -180.0 <= flon <= 180.0):
                    rejected_count += 1
                else:
                    valid_count += 1
            else:
                valid_count += 1

        status = VerificationStatus.HEALTHY
        warnings: List[str] = []
        if rejected_count > 0:
            status = VerificationStatus.DEGRADED
            warnings.append(f"{rejected_count} fire detection records rejected due to invalid coordinates.")

        quality_score = round((valid_count / total_fires) * 100.0, 1) if total_fires > 0 else 0.0

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=total_fires,
            records_valid=valid_count,
            records_rejected=rejected_count,
            expected_fields=src.supported_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=quality_score,
            warnings=warnings,
            provenance="SATELLITE_DERIVED",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_overpass(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        fetch_res = await self.overpass_client.get_nearby_infrastructure(28.6139, 77.2090, radius_meters=350)
        elapsed_ms = (time.time() - start_time) * 1000

        if not fetch_res.is_success:
            err = fetch_res.error_message or "Unknown failure"
            status = VerificationStatus.UNAVAILABLE
            http_code = None
            if "429" in err:
                status = VerificationStatus.RATE_LIMITED
                http_code = 429
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=http_code,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=[sanitize_message(err)],
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations,
                provenance="GEOSPATIAL_VECTOR_FEATURES"
            )

        data = fetch_res.data or {}
        elements_count = data.get("nearby_construction_count", 0) + data.get("major_roads_count", 0)
        status = VerificationStatus.HEALTHY if elements_count > 0 else VerificationStatus.EMPTY

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=elements_count,
            records_valid=elements_count,
            expected_fields=src.supported_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=100.0,
            provenance="GEOSPATIAL_VECTOR_FEATURES",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_nominatim(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        places = await self.geocoding_service.search_places("Connaught Place")
        elapsed_ms = (time.time() - start_time) * 1000

        records_rec = len(places)
        if records_rec == 0:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.EMPTY,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                last_successful_fetch_at=now_utc,
                response_time_ms=elapsed_ms,
                http_status=200,
                records_received=0,
                records_valid=0,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                warnings=["Zero places resolved for test anchor."],
                provenance="GEOCODING_LOOKUP",
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations
            )

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=VerificationStatus.HEALTHY,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            response_time_ms=elapsed_ms,
            http_status=200,
            records_received=records_rec,
            records_valid=records_rec,
            expected_fields=src.supported_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=100.0,
            provenance="GEOCODING_LOOKUP",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_local_db(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        repo = get_repository()
        zones = repo.list_zones()
        elapsed_ms = (time.time() - start_time) * 1000

        records_rec = len(zones)
        if records_rec == 0:
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=VerificationStatus.EMPTY,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                response_time_ms=elapsed_ms,
                records_received=0,
                records_valid=0,
                expected_fields=src.supported_fields,
                freshness_threshold_seconds=src.freshness_threshold_seconds,
                errors=["Local database contains zero monitored zones."],
                provenance="PERSISTENT_STORE",
                verification_method="LIVE_OPERATIONAL_CHECK",
                limitations=src.limitations
            )

        valid_count = 0
        latest_reading_dt: Optional[datetime] = None

        for z in zones:
            if z.latitude and z.longitude:
                valid_count += 1
            latest_r = repo.get_latest_reading(z.zone_id)
            if latest_r and latest_r.timestamp:
                try:
                    dt = datetime.fromisoformat(str(latest_r.timestamp).replace("Z", "+00:00"))
                    if latest_reading_dt is None or dt > latest_reading_dt:
                        latest_reading_dt = dt
                except Exception:
                    pass

        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        if latest_reading_dt:
            age = (now_utc - latest_reading_dt).total_seconds()
            if age > src.freshness_threshold_seconds:
                status = VerificationStatus.STALE
                warnings.append(f"Latest zone reading is {age / 3600:.1f} hours old (> {src.freshness_threshold_seconds / 3600:.1f}h threshold).")

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            latest_observation_at=latest_reading_dt,
            response_time_ms=elapsed_ms,
            records_received=records_rec,
            records_valid=valid_count,
            expected_fields=src.supported_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=round((valid_count / records_rec) * 100.0, 1) if records_rec > 0 else 0.0,
            warnings=warnings,
            provenance="PERSISTENT_STORE",
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    async def _verify_s3_data_lake(self, src: DataSourceMetadata, now_utc: datetime, start_time: float) -> SourceVerificationResult:
        lake = S3DataLakeRepository()
        elapsed_ms = (time.time() - start_time) * 1000

        # Check availability
        is_cloud = lake._is_available
        prov = "S3_OBJECT_STORE" if is_cloud else "LOCAL_FILESYSTEM_FALLBACK"
        status = VerificationStatus.HEALTHY
        warnings: List[str] = []

        if not is_cloud:
            warnings.append("S3_DATA_LAKE_BUCKET not configured or boto3 absent; operating with local data/s3_lake/ directory.")

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=now_utc,
            response_time_ms=elapsed_ms,
            records_received=1,
            records_valid=1,
            expected_fields=src.supported_fields,
            freshness_threshold_seconds=src.freshness_threshold_seconds,
            data_quality_score=100.0,
            warnings=warnings,
            provenance=prov,
            verification_method="LIVE_OPERATIONAL_CHECK",
            limitations=src.limitations
        )

    # =========================================================================
    # STORED DATASET AUDIT IMPLEMENTATION (OFFLINE MODE)
    # =========================================================================

    async def _run_stored_audit(self, src: DataSourceMetadata, now_utc: datetime) -> SourceVerificationResult:
        """
        Audits stored state without making outbound network requests.
        """
        t_sec = src.freshness_threshold_seconds
        res_fields = src.supported_fields

        if src.source_id == "local_station_db":
            return await self._verify_local_db(src, now_utc, time.time())

        elif src.source_id == "s3_data_lake":
            lake = S3DataLakeRepository()
            local_dir = lake.local_dir
            record_count = 0
            if local_dir.exists():
                for _ in local_dir.rglob("*.json"):
                    record_count += 1
            status = VerificationStatus.HEALTHY if record_count > 0 else VerificationStatus.EMPTY
            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                records_received=record_count,
                records_valid=record_count,
                expected_fields=res_fields,
                freshness_threshold_seconds=t_sec,
                provenance="LOCAL_FILESYSTEM_PARTITIONS",
                verification_method="STORED_DATASET_AUDIT",
                limitations=src.limitations
            )

        # For external API sources: inspect memory cache or local persistence
        # Check if cache entries exist
        matching_keys = [k for k in global_cache._cache.keys() if src.source_id.split("_")[0] in k.lower()]
        if not matching_keys:
            # Check if required configuration is present
            missing_configs = [cfg for cfg in src.required_config if not os.getenv(cfg)]
            status = VerificationStatus.MISCONFIGURED if missing_configs else VerificationStatus.EMPTY
            warn = ["No stored or cached records found for this source."]
            if missing_configs:
                warn.append(f"Missing required configuration: {', '.join(missing_configs)}")

            return SourceVerificationResult(
                source_id=src.source_id,
                source_name=src.source_name,
                status=status,
                checked_at=now_utc,
                last_attempt_at=now_utc,
                expected_fields=res_fields,
                records_received=0,
                records_valid=0,
                freshness_threshold_seconds=t_sec,
                warnings=warn,
                provenance="STORED_CACHE",
                verification_method="STORED_DATASET_AUDIT",
                limitations=src.limitations
            )

        # Analyze latest cached entry
        latest_entry = max([global_cache._cache[k] for k in matching_keys], key=lambda x: x["timestamp"])
        cache_age = time.time() - latest_entry["timestamp"]
        cached_dt = datetime.fromtimestamp(latest_entry["timestamp"], tz=timezone.utc)

        status = VerificationStatus.HEALTHY
        warnings = []
        if cache_age > t_sec:
            status = VerificationStatus.STALE
            warnings.append(f"Stored cached data is {cache_age / 3600:.1f} hours old (> {t_sec / 3600:.1f}h threshold).")

        return SourceVerificationResult(
            source_id=src.source_id,
            source_name=src.source_name,
            status=status,
            checked_at=now_utc,
            last_attempt_at=now_utc,
            last_successful_fetch_at=cached_dt,
            cache_age_seconds=round(cache_age, 1),
            records_received=len(matching_keys),
            records_valid=len(matching_keys),
            expected_fields=res_fields,
            freshness_threshold_seconds=t_sec,
            warnings=warnings,
            provenance="STORED_CACHE",
            verification_method="STORED_DATASET_AUDIT",
            limitations=src.limitations
        )

    # =========================================================================
    # SUMMARY BUILDER
    # =========================================================================

    def _build_summary(self, results: List[SourceVerificationResult], mode: str) -> DataHealthSummary:
        total_registered = len(self.registry.list_sources())
        total_checked = len(results)

        counts = {s: 0 for s in VerificationStatus}
        for r in results:
            counts[r.status] += 1

        missing_fields_count = sum(1 for r in results if r.missing_fields)
        insufficient_coverage_count = sum(
            1 for r in results if r.status in (VerificationStatus.EMPTY, VerificationStatus.DEGRADED)
        )

        successful_fetches = [r.last_successful_fetch_at for r in results if r.last_successful_fetch_at is not None]
        most_recent_fetch = max(successful_fetches) if successful_fetches else None

        # Deterministic overall status
        actions: List[str] = []
        if counts[VerificationStatus.ERROR] > 0 or counts[VerificationStatus.UNAVAILABLE] > 0:
            # Check if any required source is down
            req_failed = any(
                r for r in results
                if self.registry.get_source(r.source_id)
                and self.registry.get_source(r.source_id).is_required
                and r.status in (VerificationStatus.UNAVAILABLE, VerificationStatus.ERROR, VerificationStatus.MISCONFIGURED)
            )
            overall = VerificationStatus.DEGRADED if not req_failed else VerificationStatus.UNAVAILABLE
            actions.append("Inspect provider endpoint reachability, credentials, and network DNS resolution.")
        elif counts[VerificationStatus.DEGRADED] > 0 or counts[VerificationStatus.STALE] > 0:
            overall = VerificationStatus.DEGRADED
            actions.append("Re-poll upstream telemetry sources; refresh stale caches.")
        elif counts[VerificationStatus.NOT_CHECKED] == total_checked:
            overall = VerificationStatus.NOT_CHECKED
            actions.append("Trigger an initial live operational check or stored dataset audit.")
        else:
            overall = VerificationStatus.HEALTHY
            actions.append("All operational checks verified. Environmental ingestion running nominally.")

        if counts[VerificationStatus.MISCONFIGURED] > 0:
            actions.append("Configure missing environment keys (e.g. CPCB_DATA_GOV_API_KEY, NASA_FIRMS_MAP_KEY).")

        return DataHealthSummary(
            total_registered_sources=total_registered,
            total_checked=total_checked,
            healthy_count=counts[VerificationStatus.HEALTHY],
            degraded_count=counts[VerificationStatus.DEGRADED],
            stale_count=counts[VerificationStatus.STALE],
            empty_count=counts[VerificationStatus.EMPTY],
            misconfigured_count=counts[VerificationStatus.MISCONFIGURED],
            unavailable_count=counts[VerificationStatus.UNAVAILABLE],
            rate_limited_count=counts[VerificationStatus.RATE_LIMITED],
            error_count=counts[VerificationStatus.ERROR],
            not_checked_count=counts[VerificationStatus.NOT_CHECKED],
            datasets_with_missing_required_fields=missing_fields_count,
            datasets_with_insufficient_coverage=insufficient_coverage_count,
            most_recent_successful_fetch=most_recent_fetch,
            overall_status=overall,
            recommended_actions=actions,
            verification_mode=mode,
            results=results
        )


# Global service instance
data_health_service = DataHealthService()
