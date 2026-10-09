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
    Applies configurable thresholds with strict 3-layer rule precedence:
      Layer 1: Safety & Reliability Gates (Data freshness, rain, smoke, humidity, wind)
      Layer 2: Dust-Suppression Suitability (Coarse PM10 dominance vs combustion soot)
      Layer 3: Intervention Optimization & Logistics (Targeting, operating windows, alternatives)
    """
    def __init__(
        self,
        dust_ratio_threshold: float = 2.0,
        elevated_pm10_threshold: float = 120.0,
        severe_pm10_threshold: float = 250.0,
        high_humidity_threshold: float = 80.0,
        high_wind_speed_threshold_kmh: float = 20.0,
        precipitation_threshold_mmh: float = 0.1,
        min_surface_drying_time_min: int = 12,
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
        self.precipitation_threshold_mmh = precipitation_threshold_mmh
        self.min_surface_drying_time_min = min_surface_drying_time_min
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
        triggered_rules: List[str] = []
        conditions_to_change: List[str] = []
        source_status = source_status or {}

        # ------------------------------------------------------------------
        # LAYER 1: SAFETY & RELIABILITY GATES (Precedence 1)
        # ------------------------------------------------------------------

        # Gate 1.1: Missing or Stale Data Check
        if reading.is_stale:
            warnings.append("Environmental measurements exceed the maximum freshness age (>3h).")
            triggered_rules.append("GATE-STALE-DATA")
            conditions_to_change.append("Receive refreshed telemetry from monitoring stations or numerical weather models within 60 minutes.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        pm25_val = reading.pm25.value
        pm10_val = reading.pm10.value

        # Gate 1.2: Incomplete pollutant observation
        if pm25_val is None or pm10_val is None:
            warnings.append("Incomplete pollutant observation; one or both PM readings are missing.")
            triggered_rules.append("GATE-INCOMPLETE-DATA")
            conditions_to_change.append("Restore dual PM10 and PM2.5 monitoring stream to enable particulate speciation heuristic.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Gate 1.3: Negative sensor values (calibration anomaly)
        if pm25_val < 0 or pm10_val < 0:
            warnings.append("Negative sensor values detected, indicating calibration anomaly.")
            triggered_rules.append("GATE-SENSOR-ANOMALY")
            conditions_to_change.append("Sensor zero-point recalibration by station operator.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Safeguard division by zero or near-zero PM2.5
        if pm25_val <= 0.1:
            ratio = None
            warnings.append("PM2.5 value is near zero; ratio calculation skipped to avoid division error.")
        else:
            ratio = round(pm10_val / pm25_val, 2)

        # Gate 1.4: Physical contradiction (PM10 must physically enclose PM2.5)
        if pm10_val < (pm25_val * 0.85):
            warnings.append("Contradictory observations: PM10 is reported significantly lower than PM2.5.")
            triggered_rules.append("GATE-CONTRADICTION")
            conditions_to_change.append("Cross-check optical particle counter versus beta-attenuation monitor alignment.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Assess Confidence level
        confidence = ConfidenceLevel.MEDIUM
        if reading.pm25.data_type == "observed" and reading.pm10.data_type == "observed":
            confidence = ConfidenceLevel.HIGH
        elif reading.pm25.data_type == "unavailable" or reading.pm10.data_type == "unavailable":
            confidence = ConfidenceLevel.LOW

        w = reading.weather
        rh = w.relative_humidity
        ws = w.wind_speed_kmh
        blh = w.boundary_layer_height_m
        precip = w.precipitation_mmh or 0.0

        # Gate 1.5: Active Precipitation / Wet Road Gate
        if precip >= self.precipitation_threshold_mmh:
            reasons.append(f"Active precipitation detected ({precip} mm/h). Natural atmospheric wet-deposition and road dampening are actively suppressing coarse dust. Municipal spraying is redundant and creates hazardous slippery roadway conditions.")
            warnings.append("Natural precipitation already suppresses mechanical dust resuspension.")
            triggered_rules.append("GATE-ACTIVE-PRECIPITATION")
            conditions_to_change.append(f"Cease rainfall (< {self.precipitation_threshold_mmh} mm/h) and allow road surface to dry.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Gate 1.6: Possible Smoke Transport / Biomass Fire Gate
        fire = reading.fire_summary
        if fire.possible_smoke_transport or (fire.nearby_fires_count > 0 and fire.closest_fire_distance_km and fire.closest_fire_distance_km <= 20.0):
            reasons.append(f"Nearby active fire detections ({fire.nearby_fires_count} thermal anomalies within {fire.closest_fire_distance_km}km) indicate possible biomass/agricultural smoke transport.")
            warnings.append("Water mist spraying does not effectively mitigate combustion-derived smoke aerosols.")
            triggered_rules.append("GATE-SMOKE-BIOMASS")
            conditions_to_change.append("Shift in regional wind trajectory or cessation of active upwind thermal anomalies.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Gate 1.7: High Relative Humidity Gate (Risk of artificial fog and poor evaporation)
        if rh is not None and rh >= self.high_humidity_threshold:
            reasons.append(f"High relative humidity ({rh}%) makes dust-suppression mist spraying ineffective and risks localized fogging.")
            warnings.append("High ambient humidity impedes droplet evaporation and exacerbates stagnant particulate accumulation.")
            triggered_rules.append("GATE-HIGH-HUMIDITY")
            conditions_to_change.append(f"Relative humidity falling below {self.high_humidity_threshold}% (typically during peak daylight afternoon).")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Gate 1.8: High Ambient Wind Speed (Droplet drift away from corridor)
        if ws is not None and ws >= self.high_wind_speed_threshold_kmh:
            reasons.append(f"High ambient wind speed ({ws} km/h) causes spray droplet drift and reduces localized particulate capture efficiency.")
            warnings.append("Mist droplets carried away before reaching breathing zone or road surface.")
            triggered_rules.append("GATE-HIGH-WIND")
            conditions_to_change.append(f"Wind speed subsiding below {self.high_wind_speed_threshold_kmh} km/h.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # ------------------------------------------------------------------
        # LAYER 2: DUST-SUPPRESSION SUITABILITY EVALUATION
        # ------------------------------------------------------------------

        # Boundary Layer Inversion Context Check
        if blh is not None and blh <= self.low_blh_threshold_m and ws is not None and ws <= self.low_wind_accumulation_kmh:
            warnings.append(f"Boundary-layer inversion detected ({blh}m) with stagnant winds ({ws} km/h), favoring regional pollution accumulation.")
            triggered_rules.append("ADVISORY-INVERSION-TRAPPING")

        # Barometric Pressure Supporting Context
        if w.surface_pressure_hpa is not None:
            p_desc = f"Surface pressure is {w.surface_pressure_hpa:.1f} hPa ({w.pressure_tendency}"
            if w.pressure_trend_3h_hpa is not None:
                p_desc += f", 3h delta: {w.pressure_trend_3h_hpa:+.1f} hPa"
            p_desc += "). Atmospheric pressure is evaluated as supporting synoptic evidence, not a standalone spraying trigger."
            reasons.append(p_desc)

        # Construction infrastructure proximity
        has_construction = zone.nearby_infrastructure.has_construction_nearby
        construction_dist = zone.nearby_infrastructure.construction_distance_meters
        is_construction_adjacent = has_construction and (construction_dist is not None and construction_dist <= self.construction_proximity_threshold_m)

        # Particulate dominance heuristics
        is_dust_dominated = (ratio is not None and ratio >= self.dust_ratio_threshold)
        is_pm10_elevated = (pm10_val >= self.elevated_pm10_threshold)

        # Combustion / Fine Soot check
        if not is_dust_dominated and not is_pm10_elevated:
            reasons.append(f"Pollutant levels do not demonstrate coarse dust elevation (PM10 = {pm10_val} µg/m³ is below {self.elevated_pm10_threshold} µg/m³ and PM10/PM2.5 ratio = {ratio} < {self.dust_ratio_threshold}).")
            triggered_rules.append("EVAL-LOW-COARSE-DUST")
            conditions_to_change.append(f"PM10 concentration exceeding {self.elevated_pm10_threshold} µg/m³ with PM10/PM2.5 ratio >= {self.dust_ratio_threshold}.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        if not is_dust_dominated and pm25_val > 100.0:
            reasons.append(f"Elevated PM2.5 ({pm25_val} µg/m³) is dominated by fine combustion aerosols (PM10/PM2.5 ratio {ratio} < {self.dust_ratio_threshold}). Anti-smog water spraying is not indicated for vehicular/soot pollution.")
            warnings.append("Water spraying cannot scrub fine sub-micron combustion soot; source reduction and traffic control required.")
            triggered_rules.append("EVAL-COMBUSTION-DOMINANT")
            conditions_to_change.append("Transition to coarse mechanical/construction dust dominance with ratio >= 2.0.")
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
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # ------------------------------------------------------------------
        # LAYER 3: INTERVENTION OPTIMIZATION & LOGISTICS
        # ------------------------------------------------------------------

        if is_dust_dominated and is_pm10_elevated:
            reasons.append(f"PM10 is elevated ({pm10_val} µg/m³) with high PM10/PM2.5 ratio ({ratio}), indicating potential coarse fugitive dust dominance.")
            triggered_rules.append("OPT-COARSE-DUST-DOMINANCE")

            # Check surface drying feasibility:
            drying_time = w.estimated_surface_drying_time_min
            if drying_time is not None and drying_time < self.min_surface_drying_time_min:
                reasons.append(f"Severe evaporation conditions (drying time ~{drying_time} min < {self.min_surface_drying_time_min} min threshold) suggest applied water will dissipate too rapidly to justify mobile tanker expenditure.")
                warnings.append("Recommend deploying chemical dust suppressants or mechanical vacuum sweepers instead of pure water mist.")
                triggered_rules.append("OPT-RAPID-DRYING-ALTERNATIVE")
                conditions_to_change.append("Lower temperature window (early morning/evening) with surface drying persistence >15 min.")
                return DecisionRecord(
                    decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                    zone_id=zone.zone_id,
                    decision=DecisionType.ALTERNATIVE_DUST_CONTROL_SUGGESTED,
                    priority=2,
                    confidence=confidence,
                    pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                    weather=reading.weather,
                    reasons=reasons,
                    warnings=warnings,
                    triggered_rules=triggered_rules,
                    conditions_to_change=conditions_to_change,
                    source_status=source_status,
                    data_mode=reading.data_mode,
                    observed_at=reading.timestamp,
                    scored_at=scored_at,
                    station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
                )

            # Base priority calculation (1 to 5)
            priority = 2
            if pm10_val >= self.severe_pm10_threshold:
                priority += 1
                reasons.append(f"Severe PM10 concentration (>= {self.severe_pm10_threshold} µg/m³).")
                triggered_rules.append("OPT-SEVERE-PM10")

            if ratio >= 2.5:
                priority += 1
                reasons.append(f"High dust-dominance index (PM10/PM2.5 ratio {ratio} >= 2.5).")
                triggered_rules.append("OPT-HIGH-RATIO")

            if is_construction_adjacent:
                priority += 1
                reasons.append(f"Identified nearby construction site within {construction_dist}m contributes to localized fugitive road/earth dust.")
                warnings.append("Recommend contractor environmental compliance review and perimeter wetting.")
                triggered_rules.append("OPT-CONSTRUCTION-ADJACENT")

            priority = min(max(priority, 1), 5)

            # Decision: Targeted vs General
            if is_construction_adjacent:
                decision = DecisionType.TARGETED_INTERVENTION_RECOMMENDED
                conditions_to_change.append("Contractor stabilization of unpaved excavation piles and perimeter dust netting compliance.")
            else:
                decision = DecisionType.INTERVENTION_RECOMMENDED
                conditions_to_change.append(f"PM10 falling below {self.elevated_pm10_threshold} µg/m³ or rain onset.")

            return DecisionRecord(
                decision_id=f"DEC-{zone.zone_id}-{scored_at.replace(':', '').replace('-', '')[:15]}",
                zone_id=zone.zone_id,
                decision=decision,
                priority=priority,
                confidence=confidence,
                pollutants={"pm25": reading.pm25, "pm10": reading.pm10},
                weather=reading.weather,
                reasons=reasons,
                warnings=warnings,
                triggered_rules=triggered_rules,
                conditions_to_change=conditions_to_change,
                source_status=source_status,
                data_mode=reading.data_mode,
                observed_at=reading.timestamp,
                scored_at=scored_at,
                station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
            )

        # Fallback advisory
        triggered_rules.append("EVAL-UNCERTAIN-EVIDENCE")
        conditions_to_change.append("Clearer particulate ratio trend (>2.0) or confirmed local construction/traffic hotspot.")
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
            triggered_rules=triggered_rules,
            conditions_to_change=conditions_to_change,
            source_status=source_status,
            data_mode=reading.data_mode,
            observed_at=reading.timestamp,
            scored_at=scored_at,
            station_distance_km=reading.pm10.station_distance_km or reading.pm25.station_distance_km
        )
