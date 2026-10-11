"""
CPCB & data.gov.in Real-Time Ambient Air Quality and Industrial Monitoring Adapter.
Adheres to honest data retrieval, credential verification, and unit normalization.
"""
import os
import time
from typing import Dict, Any, Optional, List
import httpx
from pydantic import BaseModel, Field

from app.data_sources.base import SourceFetchResult, global_cache
from app.core.logging import logger

DATA_GOV_RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
DATA_GOV_BASE_URL = f"https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}"


class CPCBStationReading(BaseModel):
    station_name: str
    city: str
    state: str
    pollutant: str
    concentration: Optional[float]
    unit: str = "ug/m3"
    timestamp: str
    provenance: str = "CPCB_DATA_GOV_IN"
    quality_flag: str = "VALIDATED"


class CPCBClient:
    """
    Client for accessing Central Pollution Control Board (CPCB) real-time ambient
    air quality data published via India's Open Government Data platform (data.gov.in).
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 12.0):
        self.api_key = (
            api_key
            or os.getenv("CPCB_DATA_GOV_API_KEY")
            or os.getenv("DATA_GOV_IN_API_KEY")
            or ""
        )
        self.timeout = timeout
        self.cache_ttl = 900  # 15 minutes TTL for official telemetry

    def is_available(self) -> bool:
        """Returns True if a valid data.gov.in API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def get_realtime_station_measurements(
        self,
        city: Optional[str] = "Delhi",
        state: Optional[str] = "Delhi",
        station: Optional[str] = None,
        limit: int = 100
    ) -> SourceFetchResult:
        """
        Fetches official CPCB station observations from data.gov.in.
        Returns SourceFetchResult with honest success/failure/credential indicators.
        """
        if not self.is_available():
            return SourceFetchResult(
                source_name="CPCB_DATA_GOV_IN",
                is_success=False,
                error_message="MISSING_CREDENTIALS: CPCB/data.gov.in API key not configured.",
                data=[],
                fetched_at=time.time()
            )

        cache_key = f"cpcb_live_{state}_{city}_{station}_{limit}".lower()
        cached = global_cache.get(cache_key)
        if cached is not None:
            return SourceFetchResult(
                source_name="CPCB_DATA_GOV_IN",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "offset": 0,
            "limit": limit
        }
        if city:
            params["filters[city]"] = city
        if state:
            params["filters[state]"] = state
        if station:
            params["filters[station]"] = station

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(DATA_GOV_BASE_URL, params=params)

                if resp.status_code == 401 or resp.status_code == 403:
                    return SourceFetchResult(
                        source_name="CPCB_DATA_GOV_IN",
                        is_success=False,
                        error_message="AUTHENTICATION_FAILED: Invalid data.gov.in API key.",
                        data=[],
                        fetched_at=time.time()
                    )
                if resp.status_code == 429:
                    return SourceFetchResult(
                        source_name="CPCB_DATA_GOV_IN",
                        is_success=False,
                        error_message="RATE_LIMITED: data.gov.in rate limit exceeded.",
                        data=[],
                        fetched_at=time.time()
                    )
                if resp.status_code != 200:
                    return SourceFetchResult(
                        source_name="CPCB_DATA_GOV_IN",
                        is_success=False,
                        error_message=f"HTTP_ERROR_{resp.status_code}: {resp.text[:100]}",
                        data=[],
                        fetched_at=time.time()
                    )

                body = resp.json()
                records = body.get("records", [])
                parsed_readings: List[Dict[str, Any]] = []

                for r in records:
                    pollutant_raw = str(r.get("pollutant_id", "")).strip().upper()
                    # Normalize pollutant label
                    if pollutant_raw in ("PM2.5", "PM25"):
                        pollutant = "pm25"
                    elif pollutant_raw in ("PM10",):
                        pollutant = "pm10"
                    elif pollutant_raw in ("NO2", "SO2", "CO", "OZONE", "O3", "NH3"):
                        pollutant = pollutant_raw.lower()
                    else:
                        pollutant = pollutant_raw.lower()

                    # Value extraction (prefers avg, then min/max)
                    val = None
                    for key in ("pollutant_avg", "pollutant_min", "pollutant_max"):
                        raw_v = r.get(key)
                        if raw_v not in (None, "", "NA", "N/A"):
                            try:
                                v_float = float(raw_v)
                                if v_float >= 0:
                                    val = v_float
                                    break
                            except (ValueError, TypeError):
                                pass

                    parsed_readings.append({
                        "station_name": r.get("station", "Unknown Station"),
                        "city": r.get("city", city or "Unknown"),
                        "state": r.get("state", state or "Unknown"),
                        "pollutant": pollutant,
                        "concentration": val,
                        "unit": "ug/m3",
                        "timestamp": r.get("last_update", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                        "provenance": "CPCB_DATA_GOV_IN",
                        "latitude": r.get("latitude"),
                        "longitude": r.get("longitude")
                    })

                global_cache.set(cache_key, parsed_readings, ttl_seconds=self.cache_ttl)
                return SourceFetchResult(
                    source_name="CPCB_DATA_GOV_IN",
                    is_success=True,
                    data=parsed_readings,
                    fetched_at=time.time()
                )

        except httpx.TimeoutException:
            return SourceFetchResult(
                source_name="CPCB_DATA_GOV_IN",
                is_success=False,
                error_message="TIMEOUT: Request to data.gov.in timed out.",
                data=[],
                fetched_at=time.time()
            )
        except Exception as exc:
            logger.error(f"Unexpected error in CPCBClient: {exc}")
            return SourceFetchResult(
                source_name="CPCB_DATA_GOV_IN",
                is_success=False,
                error_message=f"UNEXPECTED_ERROR: {str(exc)[:100]}",
                data=[],
                fetched_at=time.time()
            )

    def get_industrial_emission_status(self) -> Dict[str, Any]:
        """
        Explains official CPCB OCEMS (Online Continuous Emission Monitoring Systems)
        access requirements for industrial point sources.
        """
        return {
            "system_name": "CPCB_OCEMS",
            "access_type": "RESTRICTED_REGULATORY_INTRANET",
            "is_public_api": False,
            "regulatory_framework": "Environment (Protection) Act, 1986 / CPCB Directions for 17 Highly Polluting Categories",
            "data_availability": "Requires authorized industrial CPCB portal credentials (cpcb.nic.in); no public anonymous REST endpoint exists.",
            "status": "ACCESS_RESTRICTED",
            "recommendation": "Integrate via licensed industrial client API tokens or authorized state pollution control board (SPCB) data agreements in Stage 5+."
        }
