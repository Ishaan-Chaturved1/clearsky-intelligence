import math
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import global_cache
from app.investigation.normalization import normalize_timestamp, validate_coordinates


class TrajectoryPoint(BaseModel):
    """
    Discrete location along an estimated backward transport path.
    """
    step_hours_back: float = Field(..., description="Hours prior to the reference event time")
    timestamp: datetime = Field(..., description="Estimated arrival time of the air parcel at this coordinate")
    latitude: float
    longitude: float
    wind_speed_kmh: float
    wind_direction_deg: float
    boundary_layer_height_m: Optional[float] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    is_forecast: bool = Field(default=False, description="True if based on predictive forecast rather than historical reanalysis")


class TransportAssessment(BaseModel):
    """
    Comprehensive atmospheric transport and upwind trajectory estimation.
    """
    status: str = Field(default="COMPLETED", description="COMPLETED, PARTIAL, INSUFFICIENT_DATA, PROVIDER_ERROR")
    method_name: str = "Kinematic Backward Wind Advection v1.0"
    start_latitude: float
    start_longitude: float
    event_timestamp: datetime
    lookback_hours: int
    trajectory_points: List[TrajectoryPoint] = Field(default_factory=list)
    total_path_length_km: float = 0.0
    net_displacement_km: float = 0.0
    dominant_upwind_bearing_deg: Optional[float] = None
    dominant_upwind_compass: Optional[str] = None
    average_transport_speed_kmh: Optional[float] = None
    min_boundary_layer_height_m: Optional[float] = None
    data_completeness_pct: float = 100.0
    is_forecast_derived: bool = False
    data_source_mode: str = "LIVE"
    uncertainty_description: str
    limitations: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> Tuple[float, float]:
    """
    Computes latitude and longitude reached after travelling a specified distance
    along a compass bearing from a starting point (Spherical Earth forward geodesic).
    """
    r = 6371.0
    d_div_r = distance_km / r
    brng_r = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)

    dest_lat_r = math.asin(
        math.sin(lat_r) * math.cos(d_div_r) +
        math.cos(lat_r) * math.sin(d_div_r) * math.cos(brng_r)
    )
    dest_lon_r = lon_r + math.atan2(
        math.sin(brng_r) * math.sin(d_div_r) * math.cos(lat_r),
        math.cos(d_div_r) - math.sin(lat_r) * math.sin(dest_lat_r)
    )

    dest_lat = math.degrees(dest_lat_r)
    dest_lon = (math.degrees(dest_lon_r) + 540.0) % 360.0 - 180.0
    return round(dest_lat, 5), round(dest_lon, 5)


class AtmosphericTransportService:
    """
    Estimates backward transport trajectories using wind observations and reanalysis data.
    
    METEOROLOGICAL PRINCIPLE:
    Wind direction theta (0-360) is the direction FROM which the wind blows.
    To trace an air parcel BACKWARD in time (finding where it came from):
    Displacement vector = bearing theta at speed v for duration dt.
    
    SCIENTIFIC LIMITATIONS:
    This service is a kinematic 2D wind trajectory approximation.
    It does NOT model 3D turbulent dispersion, vertical wind shear, or chemical transformation.
    Trajectory alignment is a necessary condition for regional transport, but does NOT prove causation.
    """

    def __init__(self):
        self.forecast_url = settings.OPEN_METEO_FORECAST_URL
        self.timeout = settings.API_TIMEOUT_SECONDS

    async def estimate_backward_trajectory(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reference_time: Optional[datetime] = None,
        event_time: Optional[datetime] = None,
        lookback_hours: int = 12
    ) -> TransportAssessment:
        actual_lat = lat if lat is not None else latitude
        actual_lon = lon if lon is not None else longitude
        actual_time = reference_time if reference_time is not None else event_time
        if actual_lat is None or actual_lon is None:
            raise ValueError("Coordinates must be provided")
        return await self.calculate_backward_trajectory(
            latitude=actual_lat,
            longitude=actual_lon,
            lookback_hours=lookback_hours,
            event_time=actual_time
        )

    async def calculate_backward_trajectory(
        self,
        latitude: float,
        longitude: float,
        lookback_hours: int = 12,
        event_time: Optional[datetime] = None
    ) -> TransportAssessment:
        """
        Calculates an hourly backward trajectory path over the specified lookback duration.
        """
        valid_lat, valid_lon = validate_coordinates(latitude, longitude, allow_none=False)
        target_time = normalize_timestamp(event_time) if event_time else datetime.now(timezone.utc)
        lookback = max(1, min(48, lookback_hours))

        cache_key = f"transport_traj_{round(valid_lat, 2)}_{round(valid_lon, 2)}_{lookback}_{target_time.strftime('%Y%m%d%H')}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return TransportAssessment(**cached)

        # Query Open-Meteo with past_hours to retrieve historical wind profiles
        params = {
            "latitude": valid_lat,
            "longitude": valid_lon,
            "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation,boundary_layer_height",
            "past_hours": max(24, lookback + 6),
            "forecast_days": 2,
            "timezone": "UTC"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.forecast_url, params=params)
                if resp.status_code != 200:
                    return self._build_error_assessment(
                        valid_lat, valid_lon, target_time, lookback,
                        f"Open-Meteo returned HTTP {resp.status_code}"
                    )

                raw = resp.json()
                hourly = raw.get("hourly", {})
                times_raw = hourly.get("time", [])
                ws_raw = hourly.get("wind_speed_10m", [])
                wd_raw = hourly.get("wind_direction_10m", [])
                blh_raw = hourly.get("boundary_layer_height", [])
                temp_raw = hourly.get("temperature_2m", [])
                precip_raw = hourly.get("precipitation", [])

                if not times_raw or not ws_raw or not wd_raw:
                    return self._build_error_assessment(
                        valid_lat, valid_lon, target_time, lookback,
                        "Open-Meteo response lacked hourly wind variables"
                    )

                # Parse times into UTC datetimes
                dt_list = [normalize_timestamp(t) for t in times_raw]

                # Find closest index to target event_time
                closest_idx = min(range(len(dt_list)), key=lambda i: abs((dt_list[i] - target_time).total_seconds()))
                
                # Check if available data covers lookback period
                trajectory_pts: List[TrajectoryPoint] = []
                current_lat = valid_lat
                current_lon = valid_lon
                total_distance = 0.0
                blh_values: List[float] = []
                speeds: List[float] = []
                any_forecast = False
                valid_steps = 0

                # Initial step 0: Event point
                curr_dt = dt_list[closest_idx]
                curr_ws = ws_raw[closest_idx]
                curr_wd = wd_raw[closest_idx]
                curr_blh = blh_raw[closest_idx] if closest_idx < len(blh_raw) else None
                curr_temp = temp_raw[closest_idx] if closest_idx < len(temp_raw) else None
                curr_precip = precip_raw[closest_idx] if closest_idx < len(precip_raw) else None

                if curr_ws is None or curr_wd is None:
                    return self._build_error_assessment(
                        valid_lat, valid_lon, target_time, lookback,
                        "Wind speed or wind direction is missing at reference event time.",
                        status="INSUFFICIENT_DATA"
                    )

                is_fc = curr_dt > datetime.now(timezone.utc)
                if is_fc:
                    any_forecast = True

                trajectory_pts.append(TrajectoryPoint(
                    step_hours_back=0.0,
                    timestamp=curr_dt,
                    latitude=current_lat,
                    longitude=current_lon,
                    wind_speed_kmh=round(curr_ws, 1),
                    wind_direction_deg=round(curr_wd, 1),
                    boundary_layer_height_m=round(curr_blh, 1) if curr_blh is not None else None,
                    temperature_c=round(curr_temp, 1) if curr_temp is not None else None,
                    precipitation_mm=round(curr_precip, 2) if curr_precip is not None else None,
                    is_forecast=is_fc
                ))
                if curr_blh is not None:
                    blh_values.append(curr_blh)
                speeds.append(curr_ws)
                valid_steps += 1

                # Backward time integration
                for step in range(1, lookback + 1):
                    target_idx = closest_idx - step
                    if target_idx < 0:
                        # Ran out of historical hours in payload
                        break

                    step_dt = dt_list[target_idx]
                    step_ws = ws_raw[target_idx]
                    step_wd = wd_raw[target_idx]
                    step_blh = blh_raw[target_idx] if target_idx < len(blh_raw) else None
                    step_temp = temp_raw[target_idx] if target_idx < len(temp_raw) else None
                    step_precip = precip_raw[target_idx] if target_idx < len(precip_raw) else None
                    step_fc = step_dt > datetime.now(timezone.utc)
                    if step_fc:
                        any_forecast = True

                    if step_ws is None or step_wd is None:
                        # Missing wind observation: stop integration rather than inventing
                        break

                    # Step backward along wind direction theta (where wind came FROM)
                    # For 1 hour interval: distance = speed (km/h) * 1.0 h
                    step_dist_km = max(0.5, step_ws * 1.0)
                    next_lat, next_lon = destination_point(current_lat, current_lon, step_wd, step_dist_km)
                    total_distance += step_dist_km

                    current_lat = next_lat
                    current_lon = next_lon
                    valid_steps += 1
                    speeds.append(step_ws)
                    if step_blh is not None:
                        blh_values.append(step_blh)

                    trajectory_pts.append(TrajectoryPoint(
                        step_hours_back=float(step),
                        timestamp=step_dt,
                        latitude=current_lat,
                        longitude=current_lon,
                        wind_speed_kmh=round(step_ws, 1),
                        wind_direction_deg=round(step_wd, 1),
                        boundary_layer_height_m=round(step_blh, 1) if step_blh is not None else None,
                        temperature_c=round(step_temp, 1) if step_temp is not None else None,
                        precipitation_mm=round(step_precip, 2) if step_precip is not None else None,
                        is_forecast=step_fc
                    ))

                if len(trajectory_pts) < 2:
                    return self._build_error_assessment(
                        valid_lat, valid_lon, target_time, lookback,
                        "Insufficient continuous wind observations to reconstruct backward trajectory",
                        status="INSUFFICIENT_DATA"
                    )

                # Net displacement from origin to furthest backward point
                origin_pt = trajectory_pts[-1]
                net_disp = self._haversine_distance_km(valid_lat, valid_lon, origin_pt.latitude, origin_pt.longitude)
                net_bearing = self._calculate_bearing_deg(valid_lat, valid_lon, origin_pt.latitude, origin_pt.longitude)
                net_compass = self._bearing_to_compass(net_bearing)

                completeness = round((valid_steps / (lookback + 1)) * 100.0, 1)
                status = "COMPLETED" if valid_steps >= lookback + 1 else "PARTIAL"

                assessment = TransportAssessment(
                    status=status,
                    method_name="Kinematic Backward Wind Advection v1.0",
                    start_latitude=valid_lat,
                    start_longitude=valid_lon,
                    event_timestamp=target_time,
                    lookback_hours=lookback,
                    trajectory_points=trajectory_pts,
                    total_path_length_km=round(total_distance, 1),
                    net_displacement_km=round(net_disp, 1),
                    dominant_upwind_bearing_deg=round(net_bearing, 1),
                    dominant_upwind_compass=net_compass,
                    average_transport_speed_kmh=round(sum(speeds) / len(speeds), 1) if speeds else None,
                    min_boundary_layer_height_m=round(min(blh_values), 1) if blh_values else None,
                    data_completeness_pct=completeness,
                    is_forecast_derived=any_forecast,
                    data_source_mode="LIVE",
                    uncertainty_description=(
                        "Kinematic single-point advection assumes horizontal wind field homogeneity. "
                        "Uncertainty expands with increasing lookback time (+/- 15-25% spatial variance per 12 hours)."
                    ),
                    limitations=[
                        "This model is a kinematic wind advection estimate, NOT a full atmospheric dispersion model (e.g. HYSPLIT or AERMOD).",
                        "Does not simulate vertical wind shear, terrain friction, or convective turbulence.",
                        "Does not simulate atmospheric chemical oxidation or dry deposition rates.",
                        "Transport consistency indicates plausible atmospheric transit, but does not prove causation."
                    ]
                )

                # Cache assessment for 30 minutes
                global_cache.set(cache_key, assessment.model_dump(), ttl_seconds=1800)
                return assessment

        except Exception as exc:
            logger.warning(f"Error computing atmospheric transport: {exc}")
            return self._build_error_assessment(
                valid_lat, valid_lon, target_time, lookback, str(exc)
            )

    def _build_error_assessment(
        self,
        lat: float,
        lon: float,
        target_time: datetime,
        lookback: int,
        error_msg: str,
        status: str = "PROVIDER_ERROR"
    ) -> TransportAssessment:
        return TransportAssessment(
            status=status,
            start_latitude=lat,
            start_longitude=lon,
            event_timestamp=target_time,
            lookback_hours=lookback,
            trajectory_points=[],
            data_completeness_pct=0.0,
            is_forecast_derived=False,
            data_source_mode="UNAVAILABLE",
            error_message=error_msg,
            uncertainty_description="Atmospheric transport could not be calculated due to missing observations or provider error.",
            limitations=[
                "This model is a kinematic wind advection estimate, NOT a full atmospheric dispersion model.",
                "Does not simulate vertical wind shear, terrain friction, or convective turbulence.",
                "Does not simulate atmospheric chemical oxidation or dry deposition rates.",
                "Transport consistency indicates plausible atmospheric transit, but does NOT prove causation."
            ]
        )

    @staticmethod
    def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def _calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        diff_lon = math.radians(lon2 - lon1)
        x = math.sin(diff_lon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(diff_lon)
        initial_bearing = math.atan2(x, y)
        return (math.degrees(initial_bearing) + 360.0) % 360.0

    @staticmethod
    def _bearing_to_compass(bearing: float) -> str:
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((bearing + 22.5) // 45.0) % 8
        return dirs[idx]
