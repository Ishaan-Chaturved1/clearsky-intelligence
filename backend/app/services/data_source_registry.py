"""
Centralized Data-Source Registry for ClearSky Intelligence.
Registers all verified environmental data sources, provider adapters, schema expectations,
freshness thresholds, and reliability policies.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DataCategory(str, Enum):
    AIR_QUALITY = "AIR_QUALITY"
    WEATHER = "WEATHER"
    SATELLITE_FIRE = "SATELLITE_FIRE"
    GEOSPATIAL = "GEOSPATIAL"
    GEOCODING = "GEOCODING"
    PERSISTENT_STORE = "PERSISTENT_STORE"
    DATA_LAKE = "DATA_LAKE"


class ProviderType(str, Enum):
    API_REST = "API_REST"
    API_CSV = "API_CSV"
    OVERPASS_QL = "OVERPASS_QL"
    SQLITE_DATABASE = "SQLITE_DATABASE"
    S3_OBJECT_STORE = "S3_OBJECT_STORE"


class RetryPolicy(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=5)
    backoff_factor: float = Field(default=1.5, ge=1.0)
    retry_status_codes: List[int] = Field(default_factory=lambda: [500, 502, 503, 504])


class DataSourceMetadata(BaseModel):
    source_id: str
    source_name: str
    data_category: DataCategory
    provider_type: ProviderType
    description: str
    required_config: List[str] = Field(default_factory=list)
    optional_config: List[str] = Field(default_factory=list)
    geographical_coverage: str
    supported_fields: List[str]
    expected_update_frequency_seconds: int = 1800  # Default 30 min
    freshness_threshold_seconds: int = 7200  # Default 2 hours
    request_timeout_seconds: float = 10.0
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    rate_limit_behavior: str
    cache_ttl_seconds: int = 1800
    data_validation_requirements: Dict[str, Any] = Field(default_factory=dict)
    is_required: bool = False
    is_verifiable: bool = True
    limitations: List[str] = Field(default_factory=list)


class DataSourceRegistry:
    """
    Singleton registry holding all verified environmental data source definitions.
    """

    def __init__(self):
        self._sources: Dict[str, DataSourceMetadata] = {}
        self._register_default_sources()

    def register(self, source: DataSourceMetadata) -> None:
        self._sources[source.source_id] = source

    def get_source(self, source_id: str) -> Optional[DataSourceMetadata]:
        return self._sources.get(source_id)

    def list_sources(self) -> List[DataSourceMetadata]:
        return list(self._sources.values())

    def get_all_sources(self) -> List[DataSourceMetadata]:
        return list(self._sources.values())

    @classmethod
    def get_default_registry(cls) -> "DataSourceRegistry":
        return data_source_registry

    @classmethod
    def get_source_by_id(cls, source_id: str) -> Optional[DataSourceMetadata]:
        return data_source_registry.get_source(source_id)

    def get_sources_by_category(self, category: DataCategory) -> List[DataSourceMetadata]:
        return [s for s in self._sources.values() if s.data_category == category]

    def _register_default_sources(self) -> None:
        # 1. CPCB / data.gov.in (Official Indian Air Quality)
        self.register(
            DataSourceMetadata(
                source_id="cpcb_in",
                source_name="CPCB Ambient Air Quality (data.gov.in)",
                data_category=DataCategory.AIR_QUALITY,
                provider_type=ProviderType.API_REST,
                description="Official Indian Central Pollution Control Board continuous ambient monitoring stations published via data.gov.in.",
                required_config=["CPCB_DATA_GOV_API_KEY"],
                optional_config=["DATA_GOV_IN_API_KEY"],
                geographical_coverage="Delhi NCT and National India",
                supported_fields=["station_name", "city", "pollutant", "concentration", "unit", "timestamp"],
                expected_update_frequency_seconds=900,  # 15 minutes
                freshness_threshold_seconds=14400,  # 4 hours
                request_timeout_seconds=12.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5),
                rate_limit_behavior="Standard data.gov.in quota (10,000 requests/day per key)",
                cache_ttl_seconds=900,
                data_validation_requirements={
                    "require_finite_concentration": True,
                    "require_non_negative": True,
                    "valid_units": ["ug/m3", "mg/m3", "ppb", "ppm"]
                },
                is_required=False,  # Optional: graceful fallback when key unconfigured
                is_verifiable=True,
                limitations=[
                    "Requires valid data.gov.in API key.",
                    "Telemetry updates depend on governmental ingestion pipeline frequency.",
                    "Some regional stations may experience periodic transmission outages."
                ]
            )
        )

        # 2. OpenAQ v3 (Global Ground Station Telemetry)
        self.register(
            DataSourceMetadata(
                source_id="openaq_v3",
                source_name="OpenAQ Ground Stations v3",
                data_category=DataCategory.AIR_QUALITY,
                provider_type=ProviderType.API_REST,
                description="Global open-data platform aggregating regulatory ground sensor telemetry including DPCC/CPCB stations.",
                required_config=[],
                optional_config=["OPENAQ_API_KEY"],
                geographical_coverage="Delhi NCR & Worldwide",
                supported_fields=["station_id", "station_name", "latitude", "longitude", "pm25", "pm10", "timestamp"],
                expected_update_frequency_seconds=3600,  # 1 hour
                freshness_threshold_seconds=14400,  # 4 hours
                request_timeout_seconds=10.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5),
                rate_limit_behavior="Free tier rates (subject to HTTP 429 when overloaded without key)",
                cache_ttl_seconds=1800,
                data_validation_requirements={
                    "require_finite_concentration": True,
                    "require_non_negative": True,
                    "require_valid_coordinates": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Without OPENAQ_API_KEY, requests are throttled or may fail under heavy traffic.",
                    "Coordinates must resolve within valid bounding box."
                ]
            )
        )

        # 3. Open-Meteo Weather Forecast (Atmospheric Physics)
        self.register(
            DataSourceMetadata(
                source_id="open_meteo_weather",
                source_name="Open-Meteo Atmospheric Forecast",
                data_category=DataCategory.WEATHER,
                provider_type=ProviderType.API_REST,
                description="High-resolution atmospheric modeling providing temperature, humidity, wind vectors, pressure, and boundary layer height.",
                required_config=[],
                optional_config=[],
                geographical_coverage="Global gridded (1 km - 11 km resolution)",
                supported_fields=[
                    "temperature_c", "relative_humidity", "surface_pressure_hpa",
                    "wind_speed_kmh", "wind_direction_deg", "precipitation_mmh",
                    "boundary_layer_height_m", "evaporation_rate_mmh"
                ],
                expected_update_frequency_seconds=3600,
                freshness_threshold_seconds=10800,  # 3 hours
                request_timeout_seconds=8.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5),
                rate_limit_behavior="10,000 calls/day free tier without authentication",
                cache_ttl_seconds=1800,
                data_validation_requirements={
                    "require_finite_numeric": True,
                    "humidity_range": [0.0, 100.0],
                    "wind_direction_range": [0.0, 360.0]
                },
                is_required=True,  # Core requirement for dispersion & mist-cannon rules
                is_verifiable=True,
                limitations=[
                    "Numerical weather prediction (NWP) model output, not direct physical in-situ anemometer measurement."
                ]
            )
        )

        # 4. Open-Meteo Air Quality (Chemical Transport Model)
        self.register(
            DataSourceMetadata(
                source_id="open_meteo_air_quality",
                source_name="Open-Meteo Air Quality Model",
                data_category=DataCategory.AIR_QUALITY,
                provider_type=ProviderType.API_REST,
                description="Global chemical reanalysis and aerosol forecast (CAMS/SILAM/Copernicus model derivative) for PM2.5, PM10, and dust.",
                required_config=[],
                optional_config=[],
                geographical_coverage="Global gridded (~10 km resolution)",
                supported_fields=["pm10", "pm25", "dust", "raw_timestamp"],
                expected_update_frequency_seconds=3600,
                freshness_threshold_seconds=14400,
                request_timeout_seconds=8.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5),
                rate_limit_behavior="10,000 calls/day free tier",
                cache_ttl_seconds=1800,
                data_validation_requirements={
                    "require_finite_numeric": True,
                    "require_non_negative": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Modeled reanalysis estimates, not direct regulatory ground sensors."
                ]
            )
        )

        # 5. NASA FIRMS VIIRS Active Fire Detections (Satellite Radiometry)
        self.register(
            DataSourceMetadata(
                source_id="nasa_firms_viirs",
                source_name="NASA FIRMS VIIRS Active Fire Telemetry",
                data_category=DataCategory.SATELLITE_FIRE,
                provider_type=ProviderType.API_CSV,
                description="Suomi NPP & NOAA-20 375m thermal anomaly detections for identifying regional agricultural stubble burning and industrial flares.",
                required_config=["NASA_FIRMS_MAP_KEY"],
                optional_config=[],
                geographical_coverage="India & South Asia regional sector",
                supported_fields=[
                    "latitude", "longitude", "bright_ti4", "scan", "track",
                    "acq_date", "acq_time", "satellite", "confidence", "frp"
                ],
                expected_update_frequency_seconds=10800,  # 3 hours (satellite orbit pass)
                freshness_threshold_seconds=86400,  # 24 hours
                request_timeout_seconds=15.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=2.0),
                rate_limit_behavior="Requires MAP_KEY; bounded rate limits per key",
                cache_ttl_seconds=1800,
                data_validation_requirements={
                    "require_valid_coordinates": True,
                    "require_finite_frp": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Requires NASA_FIRMS_MAP_KEY to access live telemetry.",
                    "Cloud cover, heavy smog, or low thermal intensity may obstruct satellite detection.",
                    "Satellite observations occur during specific overpass windows, not continuous 24/7 sampling."
                ]
            )
        )

        # 6. OpenStreetMap Overpass (Infrastructure & Vector Features)
        self.register(
            DataSourceMetadata(
                source_id="osm_overpass",
                source_name="OpenStreetMap Overpass Infrastructure",
                data_category=DataCategory.GEOSPATIAL,
                provider_type=ProviderType.OVERPASS_QL,
                description="OpenStreetMap Overpass QL query engine identifying proximate construction sites, industrial zones, and arterial highways.",
                required_config=[],
                optional_config=[],
                geographical_coverage="Global vector geometries (Delhi NCR query domain)",
                supported_fields=["id", "tags", "type", "lat", "lon"],
                expected_update_frequency_seconds=86400,  # 24 hours
                freshness_threshold_seconds=604800,  # 7 days
                request_timeout_seconds=12.0,
                retry_policy=RetryPolicy(max_retries=1, backoff_factor=2.0),
                rate_limit_behavior="Public community interpreter rate-limited; heavily cached (24h TTL)",
                cache_ttl_seconds=86400,
                data_validation_requirements={
                    "require_valid_geojson_or_elements": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Community server may experience high load timeouts (>8s).",
                    "Cached responses are utilized to respect OpenStreetMap community resources."
                ]
            )
        )

        # 7. OpenStreetMap Nominatim (Geocoding & Reverse Geocoding)
        self.register(
            DataSourceMetadata(
                source_id="nominatim_geocoding",
                source_name="OpenStreetMap Nominatim Geocoder",
                data_category=DataCategory.GEOCODING,
                provider_type=ProviderType.API_REST,
                description="Forward and reverse geocoding resolving addresses, neighborhoods, and coordinates across Delhi NCR.",
                required_config=[],
                optional_config=[],
                geographical_coverage="Delhi NCR & Global",
                supported_fields=["place_id", "display_name", "lat", "lon", "type"],
                expected_update_frequency_seconds=86400,
                freshness_threshold_seconds=604800,
                request_timeout_seconds=8.0,
                retry_policy=RetryPolicy(max_retries=1, backoff_factor=1.5),
                rate_limit_behavior="Strict 1 request/sec policy per OSM usage guidelines; uses local fallback anchors",
                cache_ttl_seconds=86400,
                data_validation_requirements={
                    "require_valid_coordinates": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Usage policy restricts bulk automated queries.",
                    "Local Delhi NCR anchor database is utilized for fast resolution and resilience."
                ]
            )
        )

        # 8. Local Monitored Zones & Persistent Database
        self.register(
            DataSourceMetadata(
                source_id="local_station_db",
                source_name="ClearSky Local Monitored Zones (SQLite)",
                data_category=DataCategory.PERSISTENT_STORE,
                provider_type=ProviderType.SQLITE_DATABASE,
                description="Primary operational storage holding the 12 monitored Delhi NCR sectors, decision audits, and telemetry time-series.",
                required_config=[],
                optional_config=["SQLITE_DB_PATH"],
                geographical_coverage="12 Monitored Sectors across Delhi NCR",
                supported_fields=["zone_id", "name", "latitude", "longitude", "zone_type", "nearby_infrastructure"],
                expected_update_frequency_seconds=1800,
                freshness_threshold_seconds=14400,
                request_timeout_seconds=2.0,
                retry_policy=RetryPolicy(max_retries=0, backoff_factor=1.0),
                rate_limit_behavior="Local disk I/O, no network rate limit",
                cache_ttl_seconds=0,
                data_validation_requirements={
                    "minimum_zones": 12,
                    "require_valid_coordinates": True
                },
                is_required=True,
                is_verifiable=True,
                limitations=[
                    "Local SQLite file on application filesystem or persistent volume."
                ]
            )
        )

        # 9. AWS S3 Data Lake Archive
        self.register(
            DataSourceMetadata(
                source_id="s3_data_lake",
                source_name="AWS S3 Data Lake Partition Archive",
                data_category=DataCategory.DATA_LAKE,
                provider_type=ProviderType.S3_OBJECT_STORE,
                description="S3 archival store partitioning raw and normalized environmental records by year/month/day/provider for AWS Glue and Athena.",
                required_config=[],
                optional_config=["S3_DATA_LAKE_BUCKET", "AWS_REGION"],
                geographical_coverage="Cloud Object Storage (AWS S3 or data/s3_lake fallback)",
                supported_fields=["raw_records", "processed_records", "investigations"],
                expected_update_frequency_seconds=1800,
                freshness_threshold_seconds=86400,
                request_timeout_seconds=5.0,
                retry_policy=RetryPolicy(max_retries=2, backoff_factor=1.5),
                rate_limit_behavior="Standard AWS S3 TPS (3,500 PUT/s, 5,500 GET/s)",
                cache_ttl_seconds=0,
                data_validation_requirements={
                    "require_json_content": True
                },
                is_required=False,
                is_verifiable=True,
                limitations=[
                    "Falls back to local data/s3_lake/ directory if S3_DATA_LAKE_BUCKET is not configured."
                ]
            )
        )


# Global registry singleton
data_source_registry = DataSourceRegistry()
