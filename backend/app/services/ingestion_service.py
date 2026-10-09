import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    PollutantValue,
    WeatherConditions,
    FireSummary,
    DataMode
)
from app.repositories.base import BaseRepository
from app.data_sources.openaq_client import OpenAQClient
from app.data_sources.open_meteo_client import OpenMeteoClient
from app.data_sources.firms_client import FirmsClient
from app.data_sources.overpass_client import OverpassClient
from app.services.estimation_service import EstimationService
from app.services.decision_engine import DecisionEngine
from app.services.alerting_service import AlertingService
from app.core.logging import logger

class IngestionService:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        self.openaq = OpenAQClient()
        self.open_meteo = OpenMeteoClient()
        self.firms = FirmsClient()
        self.overpass = OverpassClient()
        self.estimation = EstimationService()
        self.decision_engine = DecisionEngine()
        self.alerting = AlertingService(repository)

    async def ingest_and_score_zone(
        self,
        zone: Zone,
        force_demo: bool = False
    ) -> DecisionRecord:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat().replace("+00:00", "Z")

        source_status: Dict[str, str] = {
            "openaq": "unavailable",
            "open_meteo_weather": "unavailable",
            "open_meteo_aq": "unavailable",
            "nasa_firms": "unavailable",
            "osm_overpass": "available"
        }

        # If force_demo is false, attempt live queries
        weather_cond = WeatherConditions()
        pm25_val = None
        pm10_val = None
        fire_summary = FireSummary()
        data_mode = DataMode.DEMO

        if not force_demo:
            try:
                # Concurrent retrieval
                w_task = self.open_meteo.get_weather(zone.latitude, zone.longitude)
                aq_task = self.open_meteo.get_air_quality(zone.latitude, zone.longitude)
                w_res, aq_res = await asyncio.gather(w_task, aq_task, return_exceptions=True)

                if isinstance(w_res, Exception):
                    source_status["open_meteo_weather"] = f"error: {str(w_res)[:40]}"
                elif w_res.is_success and w_res.data:
                    source_status["open_meteo_weather"] = "available"
                    weather_cond = WeatherConditions(**{
                        k: v for k, v in w_res.data.items() if k in WeatherConditions.model_fields
                    })
                    data_mode = DataMode.LIVE

                modeled_pm25 = None
                modeled_pm10 = None
                if isinstance(aq_res, Exception):
                    source_status["open_meteo_aq"] = f"error: {str(aq_res)[:40]}"
                elif aq_res.is_success and aq_res.data:
                    source_status["open_meteo_aq"] = "available"
                    modeled_pm25 = aq_res.data.get("pm25")
                    modeled_pm10 = aq_res.data.get("pm10")
                    data_mode = DataMode.LIVE

                # Ground stations via OpenAQ
                st_res = await self.openaq.get_nearby_station_measurements(zone.latitude, zone.longitude)
                stations = []
                if st_res.is_success:
                    source_status["openaq"] = "available"
                    stations = st_res.data or []
                else:
                    source_status["openaq"] = st_res.error_message or "offline"

                # Check active fires via NASA FIRMS
                f_res = await self.firms.check_nearby_fires(
                    zone.latitude,
                    zone.longitude,
                    wind_direction_deg=weather_cond.wind_direction_deg
                )
                if f_res.is_success:
                    source_status["nasa_firms"] = "available"
                    fire_summary = FireSummary(**f_res.data)
                else:
                    source_status["nasa_firms"] = f_res.error_message or "offline"

                # Estimate pollutants
                pm25_pollutant, _ = self.estimation.estimate_pollutant("pm25", zone.latitude, zone.longitude, stations, modeled_pm25)
                pm10_pollutant, _ = self.estimation.estimate_pollutant("pm10", zone.latitude, zone.longitude, stations, modeled_pm10)

            except Exception as e:
                logger.warning(f"Error during live ingestion for zone {zone.zone_id}: {e}")
                data_mode = DataMode.DEMO
                pm25_pollutant = PollutantValue(value=None, data_type="unavailable")
                pm10_pollutant = PollutantValue(value=None, data_type="unavailable")
        else:
            pm25_pollutant = PollutantValue(value=None, data_type="unavailable")
            pm10_pollutant = PollutantValue(value=None, data_type="unavailable")

        # If data is completely unavailable or we are in DEMO mode and no live data arrived, use previous reading if exists
        if pm25_pollutant.value is None or pm10_pollutant.value is None:
            prev_reading = self.repository.get_latest_reading(zone.zone_id)
            if prev_reading:
                reading = prev_reading
                reading.timestamp = now_iso
            else:
                # Default baseline fallback reading
                reading = EnvironmentalReading(
                    reading_id=f"RD-{zone.zone_id}-{now_iso}",
                    zone_id=zone.zone_id,
                    timestamp=now_iso,
                    pm25=PollutantValue(value=55.0, data_type="modeled"),
                    pm10=PollutantValue(value=140.0, data_type="modeled"),
                    pm_ratio=2.55,
                    weather=WeatherConditions(
                        temperature_c=28.5,
                        relative_humidity=52.0,
                        wind_speed_kmh=8.5,
                        wind_direction_deg=280.0,
                        boundary_layer_height_m=420.0
                    ),
                    fire_summary=FireSummary(),
                    data_mode=DataMode.DEMO,
                    is_stale=False
                )
        else:
            ratio = None
            if pm25_pollutant.value and pm25_pollutant.value > 0.1 and pm10_pollutant.value:
                ratio = round(pm10_pollutant.value / pm25_pollutant.value, 2)
            reading = EnvironmentalReading(
                reading_id=f"RD-{zone.zone_id}-{now_iso}",
                zone_id=zone.zone_id,
                timestamp=now_iso,
                pm25=pm25_pollutant,
                pm10=pm10_pollutant,
                pm_ratio=ratio,
                weather=weather_cond,
                fire_summary=fire_summary,
                data_mode=data_mode,
                is_stale=False
            )

        # Save reading
        self.repository.save_reading(reading)

        # Evaluate decision
        prev_decision = self.repository.get_latest_decision(zone.zone_id)
        decision = self.decision_engine.evaluate(
            zone=zone,
            reading=reading,
            scored_at=now_iso,
            source_status=source_status
        )
        self.repository.save_decision(decision)

        # Check for alert trigger
        self.alerting.check_and_emit(zone, decision, prev_decision)

        return decision

    async def run_full_cycle(self, force_demo: bool = False) -> List[DecisionRecord]:
        zones = self.repository.list_zones()
        decisions = []
        for zone in zones:
            d = await self.ingest_and_score_zone(zone, force_demo=force_demo)
            decisions.append(d)
        return decisions
