import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union


def normalize_timestamp(
    ts: Union[datetime, str, int, float],
    source_name: Optional[str] = None
) -> datetime:
    """
    Normalizes any input timestamp to a timezone-aware UTC datetime.
    
    Rules:
    - Timezone-aware datetimes are converted to UTC.
    - Naive datetimes are assumed to represent UTC (documented assumption for standard telemetry).
    - ISO-8601 strings (e.g., '2026-10-11T09:30:00Z', '2026-10-11T15:00:00+05:30') are parsed and converted to UTC.
    - Unix epoch timestamps (seconds as int/float) are converted to UTC.
    
    Raises:
        ValueError: If the timestamp is malformed, unparseable, or out of realistic range.
    """
    if ts is None:
        raise ValueError("Timestamp cannot be None")

    if isinstance(ts, (int, float)):
        if math.isnan(ts) or math.isinf(ts):
            raise ValueError("Numeric timestamp cannot be NaN or infinite")
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as err:
            raise ValueError(f"Invalid numeric epoch timestamp {ts}: {err}") from err

    if isinstance(ts, str):
        cleaned = ts.strip()
        if not cleaned:
            raise ValueError("Timestamp string cannot be empty")
        # Handle trailing Z
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError as err:
            raise ValueError(f"Malformed ISO-8601 timestamp string '{ts}': {err}") from err
        if dt.tzinfo is None:
            # Naive timestamp in string: assume UTC as per system standard
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            # Naive datetime: assume UTC
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    raise ValueError(f"Unsupported timestamp type {type(ts)}")


def validate_coordinates(
    lat: Optional[float],
    lon: Optional[float],
    allow_none: bool = True
) -> Tuple[Optional[float], Optional[float]]:
    """
    Validates geographic latitude and longitude.
    
    Coordinates are optional for gridded, administrative, or regional datasets.
    If provided, both must be valid finite numbers within WGS84 bounds.
    """
    if lat is None and lon is None:
        if allow_none:
            return None, None
        raise ValueError("Coordinates are required for this entity")

    if (lat is None) != (lon is None):
        raise ValueError("Latitude and longitude must both be provided, or both be None")

    if math.isnan(lat) or math.isinf(lat):
        raise ValueError("Latitude cannot be NaN or infinite")
    if math.isnan(lon) or math.isinf(lon):
        raise ValueError("Longitude cannot be NaN or infinite")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is out of bounds [-90.0, 90.0]")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} is out of bounds [-180.0, 180.0]")

    return float(lat), float(lon)


def validate_numeric_measurement(
    value: Optional[float],
    name: str,
    allow_negative: bool = False,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None
) -> Optional[float]:
    """
    Validates a physical environmental measurement.
    Rejects NaN, infinite numbers, or values outside physical plausibility limits.
    """
    if value is None:
        return None

    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Measurement '{name}' cannot be NaN or infinite")

    if not allow_negative and value < 0:
        raise ValueError(f"Measurement '{name}' cannot be negative ({value})")

    if min_val is not None and value < min_val:
        raise ValueError(f"Measurement '{name}' value {value} is below physical minimum {min_val}")

    if max_val is not None and value > max_val:
        raise ValueError(f"Measurement '{name}' value {value} exceeds physical maximum {max_val}")

    return float(value)


def evaluate_freshness(
    observation_time: Union[datetime, str],
    max_age_seconds: float,
    reference_time: Optional[datetime] = None
) -> Tuple[bool, float]:
    """
    Evaluates whether an observation satisfies a dataset-specific freshness threshold.
    
    Returns:
        (is_fresh: bool, age_seconds: float)
    """
    obs_utc = normalize_timestamp(observation_time)
    ref_utc = normalize_timestamp(reference_time) if reference_time is not None else datetime.now(timezone.utc)

    age_seconds = (ref_utc - obs_utc).total_seconds()

    # Reject future timestamps beyond 300s clock skew
    if age_seconds < -300.0:
        raise ValueError(f"Observation timestamp {obs_utc.isoformat()} is in the future relative to {ref_utc.isoformat()}")

    is_fresh = 0.0 <= age_seconds <= max_age_seconds
    return is_fresh, max(0.0, age_seconds)


def convert_pollutant_concentration(
    value: float,
    from_unit: str,
    to_unit: str,
    pollutant: str,
    temperature_c: Optional[float] = None,
    pressure_hpa: Optional[float] = None
) -> float:
    """
    Converts pollutant concentration units with strict scientific guardrails.
    
    Supported mass conversions:
    - mg/m3 <-> ug/m3 (factor 1000)
    
    Volumetric (ppm/ppb) conversions to mass (ug/m3) require explicit ambient
    temperature and surface pressure to apply the ideal gas law.
    Attempting gas conversion without meteorological conditions raises ValueError.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Concentration value cannot be NaN or infinite")
    if value < 0:
        raise ValueError("Concentration cannot be negative")

    from_u = from_unit.strip().lower()
    to_u = to_unit.strip().lower()

    if from_u == to_u:
        return float(value)

    # Mass to Mass
    if from_u == "mg/m3" and to_u in ("ug/m3", "µg/m3"):
        return float(value * 1000.0)
    if from_u in ("ug/m3", "µg/m3") and to_u == "mg/m3":
        return float(value / 1000.0)

    # Volumetric to Mass checks
    if from_u in ("ppm", "ppb") or to_u in ("ppm", "ppb"):
        if temperature_c is None or pressure_hpa is None:
            raise ValueError(
                f"Conversion between volumetric ({from_unit}) and mass concentration ({to_unit}) "
                f"for {pollutant} requires ambient temperature and pressure for ideal gas law calculation."
            )
        # Molecular weights for common air quality gases
        mw_table = {
            "NO2": 46.0055,
            "SO2": 64.066,
            "CO": 28.01,
            "O3": 47.9982,
        }
        poll_key = pollutant.upper().replace(".", "")
        if poll_key not in mw_table:
            raise ValueError(f"Molecular weight not available for gas {pollutant}")

        mw = mw_table[poll_key]
        temp_k = temperature_c + 273.15
        p_atm = pressure_hpa / 1013.25
        # Ideal gas constant R = 0.082057 L·atm/(mol·K)
        # 1 ppm = (MW * 1000 / V_m) ug/m3 where V_m = R * T / P (liters per mole)
        vm = (0.082057 * temp_k) / p_atm

        if from_u == "ppm" and to_u in ("ug/m3", "µg/m3"):
            return float(value * (mw * 1000.0) / vm)
        if from_u == "ppb" and to_u in ("ug/m3", "µg/m3"):
            return float((value / 1000.0) * (mw * 1000.0) / vm)
        if from_u in ("ug/m3", "µg/m3") and to_u == "ppm":
            return float(value * vm / (mw * 1000.0))
        if from_u in ("ug/m3", "µg/m3") and to_u == "ppb":
            return float((value * vm / (mw * 1000.0)) * 1000.0)

    raise ValueError(f"Unsupported unit conversion from '{from_unit}' to '{to_unit}' for {pollutant}")
