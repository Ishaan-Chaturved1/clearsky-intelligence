import math
from typing import List, Dict, Optional, Tuple, Any
from app.models.domain import PollutantValue, ConfidenceLevel
from app.core.logging import logger

class EstimationService:
    def __init__(
        self,
        max_station_distance_km: float = 25.0,
        min_stations_for_idw: int = 2,
        idw_power: float = 2.0
    ):
        self.max_station_distance_km = max_station_distance_km
        self.min_stations_for_idw = min_stations_for_idw
        self.idw_power = idw_power

    def haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lam = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def estimate_pollutant(
        self,
        pollutant_name: str,  # 'pm25' or 'pm10'
        zone_lat: float,
        zone_lon: float,
        stations: List[Dict[str, Any]],
        modeled_value: Optional[float] = None
    ) -> Tuple[PollutantValue, Dict[str, Any]]:
        """
        Estimates pollutant value using:
        1. Single nearest station if within 5km
        2. IDW interpolation if >= 2 valid stations within max_distance
        3. Nearest station within max_distance if only 1 station available
        4. Modeled value fallback if no ground stations available
        5. Unavailable fallback if neither exists
        """
        valid_stations = []
        for st in stations:
            val = st.get(pollutant_name)
            if val is not None and isinstance(val, (int, float)) and val >= 0:
                dist = st.get("distance_km")
                if dist is None:
                    dist = self.haversine_km(zone_lat, zone_lon, st["latitude"], st["longitude"])
                if dist <= self.max_station_distance_km:
                    valid_stations.append((st, dist, float(val)))

        metadata: Dict[str, Any] = {
            "pollutant": pollutant_name,
            "valid_stations_count": len(valid_stations),
            "method": "unavailable"
        }

        # Case 1: Ground stations available
        if valid_stations:
            # Sort by distance
            valid_stations.sort(key=lambda x: x[1])
            closest_st, closest_dist, closest_val = valid_stations[0]

            # If very close (< 5km) or only 1 station, use closest
            if closest_dist < 5.0 or len(valid_stations) < self.min_stations_for_idw:
                metadata["method"] = "nearest_station_observation"
                metadata["station_id"] = closest_st.get("station_id")
                metadata["distance_km"] = closest_dist
                return PollutantValue(
                    value=round(closest_val, 1),
                    unit="ug/m3",
                    data_type="observed",
                    station_id=closest_st.get("station_id"),
                    station_distance_km=round(closest_dist, 2)
                ), metadata

            # Inverse Distance Weighting (IDW)
            total_weight = 0.0
            weighted_sum = 0.0
            for st_obj, dist, val in valid_stations:
                dist = max(dist, 0.1)  # avoid division by zero
                w = 1.0 / (dist ** self.idw_power)
                total_weight += w
                weighted_sum += w * val

            idw_val = weighted_sum / total_weight if total_weight > 0 else closest_val
            metadata["method"] = "inverse_distance_weighted_interpolation"
            metadata["interpolated_from_stations"] = len(valid_stations)
            metadata["closest_station_distance_km"] = closest_dist

            return PollutantValue(
                value=round(idw_val, 1),
                unit="ug/m3",
                data_type="interpolated",
                station_id=f"IDW_{len(valid_stations)}_stations",
                station_distance_km=round(closest_dist, 2)
            ), metadata

        # Case 2: No ground stations, fallback to modeled estimate
        if modeled_value is not None and isinstance(modeled_value, (int, float)) and modeled_value >= 0:
            metadata["method"] = "numerical_atmospheric_model"
            return PollutantValue(
                value=round(modeled_value, 1),
                unit="ug/m3",
                data_type="modeled",
                station_id=None,
                station_distance_km=None
            ), metadata

        # Case 3: Unavailable
        metadata["method"] = "data_unavailable"
        return PollutantValue(
            value=None,
            unit="ug/m3",
            data_type="unavailable",
            station_id=None,
            station_distance_km=None
        ), metadata

    def assess_confidence(
        self,
        pm25_type: str,
        pm10_type: str,
        weather_available: bool,
        fire_checked: bool,
        is_stale: bool,
        has_sufficient_pollutants: bool
    ) -> ConfidenceLevel:
        if is_stale or not has_sufficient_pollutants:
            return ConfidenceLevel.LOW

        # Both observed/interpolated + weather + fire
        if pm25_type in ("observed", "interpolated") and pm10_type in ("observed", "interpolated") and weather_available and fire_checked:
            return ConfidenceLevel.HIGH

        # Modeled or partial coverage
        if (pm25_type == "modeled" or pm10_type == "modeled") and weather_available:
            return ConfidenceLevel.MEDIUM

        return ConfidenceLevel.LOW
