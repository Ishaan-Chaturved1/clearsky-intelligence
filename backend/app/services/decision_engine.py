import math
from typing import List, Dict, Optional, Tuple, Any
from app.models.domain import (
    DecisionType,
    ConfidenceLevel,
    DataMode,
    DecisionRecord,
    EnvironmentalReading,
    Zone,
    NearbyInfrastructure
)
from app.core.logging import logger

class DecisionEngine:
    """
    Deterministic, transparent, rule-based environmental decision engine.
    Applies configurable thresholds with strict rule precedence.
    """
    def __init__(
        self,
        dust_ratio_threshold: float = 2.0,
        elevated_pm10_threshold: float = 120.0,
        severe_pm10_threshold: float = 250.0,
        high_humidity_threshold: float = 80.0,
        high_wind_speed_threshold_kmh: float = 20.0,
        low_blh_threshold_m: float = 300.0,
        low_wind_accumulation_kmh: float = 5.0,
        construction_proximity_threshold_m: int = 300,
        fire_proximity_threshold_km: float = 50.0
    ):
        self.dust_ratio_threshold = dust_ratio_threshold
        self.elevated_pm10_threshold = elevated_pm10_threshold
        self.severe_pm10_threshold = severe_pm10_threshold
        self.high_humidity_threshold = high_humidity_threshold
        self.high_wind_speed_threshold_kmh = high_wind_speed_threshold_kmh
        self.low_blh_threshold_m = low_blh_threshold_m
        self.low_wind_accumulation_kmh = low_wind_accumulation_kmh
        self.construction_proximity_threshold_m = construction_proximity_threshold_m
        self.fire_proximity_threshold_km = fire_proximity_threshold_km

    def evaluate(
        self,
        zone: Zone,
        reading: EnvironmentalReading,
        scored_at: str,
        source_status: Optional[Dict[str, str]] = None
    ) -> DecisionRecord:
        reasons: List[str] = []
        warnings: List[str] = []
        source_status = source_status or {}

        # 1. Missing or Stale Data Check (Precedence 1)
        if reading.is_stale:
            warnings.append("Environmental measurements exceed the maximum freshness age (>3h).")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.ADVISORY_ONLY,
                priority=None,
                confidence=ConfidenceLevel.LOW,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=["Readings are stale; reliable operational intervention cannot be supported."],
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        pm25_val = reading.pm25.value
        pm10_val = reading.pm10.value

        if pm25_val is None or pm10_val is None:
            warnings.append("Incomplete pollutant observation; one or both PM readings are missing.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.ADVISORY_ONLY,
                priority=None,
                confidence=ConfidenceLevel.LOW,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=["Insufficient pollutant data to determine dust-dominance."],
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # 2. Check for Contradictory / Invalid pollutant readings
        if pm25_val < 0 or pm10_val < 0:
            warnings.append("Negative sensor values detected, indicating calibration anomaly.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.ADVISORY_ONLY,
                priority=None,
                confidence=ConfidenceLevel.LOW,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=["Sensor reading anomaly detected."],
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Safeguard division by zero or near zero
        if pm25_val <= 0.1:
            ratio = None
            warnings.append("PM2.5 value is near zero; ratio calculation skipped to avoid division error.")
        else:
            ratio = round(pm10_val / pm25_val, 2)

        # PM10 must be physically >= PM2.5 in standard ambient conditions (PM2.5 is a fraction of PM10)
        if pm10_val < (pm25_val * 0.85):
            warnings.append("Contradictory observations: PM10 is reported significantly lower than PM2.5.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.ADVISORY_ONLY,
                priority=None,
                confidence=ConfidenceLevel.LOW,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=["Measurement contradiction between PM10 and PM2.5 sensors."],
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Assess Confidence
        confidence = ConfidenceLevel.MEDIUM
        if reading.pm25.data_type == "observed" and reading.pm10.data_type == "observed":
            confidence = ConfidenceLevel.HIGH
        elif reading.pm25.data_type == "unavailable" or reading.pm10.data_type == "unavailable":
            confidence = ConfidenceLevel.LOW

        # Weather factors
        w = reading.weather
        rh = w.relative_humidity
        ws = w.wind_speed_kmh
        blh = w.boundary_layer_height_m

        # Rule 5 check: Low BLH + low wind (Inversion / accumulation)
        if blh is not None and blh <= self.low_blh_threshold_m and ws is not None and ws <= self.low_wind_accumulation_kmh:
            warnings.append(f"Boundary-layer inversion detected ({blh}m) with stagnant winds ({ws} km/h), favoring regional pollution accumulation.")

        # Rule 2: Possible Smoke Influence (Precedence 2)
        fire = reading.fire_summary
        if fire.possible_smoke_transport or (fire.nearby_fires_count > 0 and fire.closest_fire_distance_km and fire.closest_fire_distance_km <= 20.0):
            reasons.append(f"Nearby active fire detections ({fire.nearby_fires_count} anomalies within {fire.closest_fire_distance_km}km) indicate possible biomass/agricultural smoke transport.")
            warnings.append("Water mist spraying does not effectively mitigate combustion-derived smoke aerosols.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_NOT_RECOMMENDED,
                priority=None,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Rule 3: High Humidity (Precedence 3)
        if rh is not None and rh >= self.high_humidity_threshold:
            reasons.append(f"High relative humidity ({rh}%) makes dust-suppression mist spraying ineffective and risks localized fogging.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_NOT_RECOMMENDED,
                priority=None,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Rule 4: High Wind (Precedence 4)
        if ws is not None and ws >= self.high_wind_speed_threshold_kmh:
            reasons.append(f"High ambient wind speed ({ws} km/h) causes spray droplet drift and reduces localized particulate capture efficiency.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_NOT_RECOMMENDED,
                priority=None,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Rule 6: Construction dust source check
        has_construction = zone.nearby_infrastructure.has_construction_nearby
        construction_dist = zone.nearby_infrastructure.construction_distance_meters
        is_construction_adjacent = has_construction and (construction_dist is not None and construction_dist <= self.construction_proximity_threshold_m)

        # Rule 1: Potential Dust Dominance
        is_dust_dominated = (ratio is not None and ratio >= self.dust_ratio_threshold)
        is_pm10_elevated = (pm10_val >= self.elevated_pm10_threshold)

        # Combustion / Fine Soot Check (High PM2.5 without dust ratio)
        if not is_dust_dominated and not is_pm10_elevated:
            reasons.append("Pollutant levels do not demonstrate coarse dust elevation (PM10 is below threshold and PM10/PM2.5 ratio < 2.0).")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_NOT_RECOMMENDED,
                priority=None,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        if not is_dust_dominated and pm25_val > 100.0:
            reasons.append("Elevated PM2.5 is dominated by fine combustion aerosols (PM10/PM2.5 ratio < 2.0). Anti-smog water spraying is not indicated for vehicular/soot pollution.")
            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_NOT_RECOMMENDED,
                priority=None,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # INTERVENTION RECOMMENDED when evidence supports coarse dust dominance & suitable weather
        if is_dust_dominated and is_pm10_elevated:
            reasons.append(f"PM10 is elevated ({pm10_val} µg/m³) with high PM10/PM2.5 ratio ({ratio}), indicating potential coarse fugitive dust dominance.")
            
            # Base priority calculation (1 to 5)
            priority = 2
            if pm10_val >= self.severe_pm10_threshold:
                priority += 1
                reasons.append(f"Severe PM10 concentration (>= {self.severe_pm10_threshold} µg/m³).")
            if ratio >= 2.5:
                priority += 1
                reasons.append(f"High dust-dominance index (PM10/PM2.5 ratio {ratio} >= 2.5).")
            if is_construction_adjacent:
                priority += 1
                reasons.append(f"Identified nearby construction site within {construction_dist}m contributes to localized fugitive road/earth dust.")
                warnings.append("Recommend contractor environmental compliance review and perimeter wetting.")

            priority = min(max(priority, 1), 5)

            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=DecisionType.INTERVENTION_RECOMMENDED,
                priority=priority,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at
            )

        # Fallback advisory
        return DecisionRecord(
            decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
            zone_id=zone.zone_id,
            decision=DecisionType.ADVISORY_ONLY,
            priority=None,
            confidence=ConfidenceLevel.LOW,
            pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
            weather=reading.weather,
            reasons=["Evidence does not decisively support either intervention or explicit cessation."],
            warnings=warnings,
            source_status=source_status,
            data_mode=reading.data_mode,
            observed_at=reading.timestamp,
            scored_at=scored_at
        )
