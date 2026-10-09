import math
from typing import List, Dict, Optional, Any
from app.models.domain import Zone, CandidateRoadSegment
from app.core.logging import logger

class SpatialService:
    """
    Geospatial analysis engine for candidate road corridors across Delhi NCR sectors.
    Computes road surface geometry, dust accumulation vulnerability, water volume demands,
    and priority rankings based on proximity to mapped construction and traffic classifications.
    """
    def __init__(
        self,
        standard_application_rate_liters_per_m2: float = 0.4,
        standard_tanker_capacity_liters: float = 5000.0,
        tanker_cost_per_trip_inr: float = 1200.0
    ):
        self.app_rate = standard_application_rate_liters_per_m2
        self.tanker_capacity = standard_tanker_capacity_liters
        self.cost_per_trip = tanker_cost_per_trip_inr

        # Standard width estimations by road classification (meters)
        self.width_map = {
            "motorway": 24.0,
            "trunk": 18.0,
            "primary": 14.0,
            "secondary": 10.0,
            "tertiary": 7.0
        }

    def get_candidate_road_segments(
        self,
        zone: Zone,
        current_pm10: Optional[float] = None
    ) -> List[CandidateRoadSegment]:
        """
        Derives prioritized road segments for the sector based on nearby infrastructure,
        classification, surface area, and construction proximity.
        """
        segments: List[CandidateRoadSegment] = []
        major_roads = zone.nearby_infrastructure.major_roads or [f"{zone.name} Main Corridor"]
        has_construction = zone.nearby_infrastructure.has_construction_nearby
        const_dist = zone.nearby_infrastructure.construction_distance_meters

        for idx, road_name in enumerate(major_roads):
            # Classify road hierarchy
            if any(term in road_name.lower() for term in ["ring road", "gt road", "national", "expressway"]):
                classification = "trunk"
                length_km = 2.4
                traffic = "HIGH"
            elif any(term in road_name.lower() for term in ["marg", "avenue", "flyover", "extension"]):
                classification = "primary"
                length_km = 1.6
                traffic = "HIGH" if idx == 0 else "MEDIUM"
            else:
                classification = "secondary"
                length_km = 1.0
                traffic = "MEDIUM"

            width_m = self.width_map.get(classification, 14.0)
            area_m2 = round(length_km * 1000.0 * width_m, 1)

            # Application rate = 0.4 Liters / m² standard municipal dust wetting
            water_liters = round(area_m2 * self.app_rate, 0)
            trips = max(1, math.ceil(water_liters / self.tanker_capacity))
            cost_inr = round(trips * self.cost_per_trip, 0)

            # Calculate priority score (1 to 5)
            # Construction adjacency on first segment
            is_const_adj = has_construction and (idx == 0 or (const_dist is not None and const_dist <= 300))
            score = 3
            if is_const_adj:
                score += 1
            if classification in ("trunk", "primary"):
                score += 1
            if current_pm10 and current_pm10 >= 250.0:
                score += 1
            score = min(max(score, 1), 5)

            # Determine recommended action
            if is_const_adj and score >= 4:
                action = "TARGETED_CORRIDOR_MISTING"
            elif score >= 3:
                action = "MECHANICAL_SWEEPING_AND_WETTING"
            else:
                action = "ADVISORY_MONITORING"

            segments.append(
                CandidateRoadSegment(
                    segment_id=f"SEG-{zone.zone_id}-{idx+1:02d}",
                    zone_id=zone.zone_id,
                    road_name=road_name,
                    road_classification=classification,
                    length_km=length_km,
                    estimated_width_m=width_m,
                    surface_area_m2=area_m2,
                    traffic_index=traffic,
                    construction_adjacent=is_const_adj,
                    construction_distance_m=const_dist if is_const_adj else None,
                    water_required_liters=water_liters,
                    tanker_trips_required=trips,
                    priority_score=score,
                    recommended_action=action,
                    estimated_cost_inr=cost_inr
                )
            )

        # Sort descending by priority score and required water
        return sorted(segments, key=lambda s: (s.priority_score, s.water_required_liters), reverse=True)
