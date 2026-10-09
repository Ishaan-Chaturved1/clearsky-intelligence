import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from app.models.domain import ForecastWindow
from app.core.logging import logger

class ForecastService:
    """
    Evaluates upcoming hourly meteorological windows (1 to 24 hours ahead)
    to rank the most suitable operating windows for dust-suppression water misting.
    Combines temperature, relative humidity, wind speed, surface pressure,
    and precipitation to generate transparent suitability scores and safety alerts.
    """
    def __init__(
        self,
        optimal_rh_min: float = 35.0,
        optimal_rh_max: float = 72.0,
        prohibitive_rh: float = 80.0,
        optimal_wind_min: float = 4.0,
        optimal_wind_max: float = 14.0,
        prohibitive_wind: float = 20.0,
        rain_threshold_mmh: float = 0.1
    ):
        self.optimal_rh_min = optimal_rh_min
        self.optimal_rh_max = optimal_rh_max
        self.prohibitive_rh = prohibitive_rh
        self.optimal_wind_min = optimal_wind_min
        self.optimal_wind_max = optimal_wind_max
        self.prohibitive_wind = prohibitive_wind
        self.rain_threshold_mmh = rain_threshold_mmh

    def evaluate_hourly_windows(
        self,
        raw_hourly: Optional[Dict[str, Any]],
        zone_id: str,
        limit_hours: int = 12
    ) -> List[ForecastWindow]:
        """
        Parses hourly arrays from Open-Meteo or synthetic baseline and ranks suitability.
        """
        windows: List[ForecastWindow] = []
        if not raw_hourly or "time" not in raw_hourly:
            # Fallback realistic 12-hour forecast based on diurnal cycles
            now = datetime.now(timezone.utc)
            base_temp = 28.0
            base_rh = 55.0
            base_ws = 9.0
            for h in range(1, limit_hours + 1):
                window_dt = now + timedelta(hours=h)
                # Diurnal simulation: cooler/higher RH at night, warmer/lower RH mid-day
                hour_of_day = window_dt.hour
                temp = round(base_temp + 5.0 * math.sin((hour_of_day - 9) * math.pi / 12), 1)
                rh = round(max(30.0, min(85.0, base_rh - 20.0 * math.sin((hour_of_day - 9) * math.pi / 12))), 1)
                ws = round(max(3.0, base_ws + 3.0 * math.cos((hour_of_day - 14) * math.pi / 12)), 1)
                precip = 0.0
                pressure = round(1013.2 - 1.5 * math.sin((hour_of_day - 12) * math.pi / 12), 1)

                win = self._score_single_window(
                    window_id=f"WIN-{zone_id}-{window_dt.strftime('%Y%m%d%H')}",
                    dt=window_dt,
                    temp=temp,
                    rh=rh,
                    ws=ws,
                    precip=precip,
                    pressure=pressure
                )
                windows.append(win)
            return sorted(windows, key=lambda w: w.suitability_score, reverse=True)

        times = raw_hourly.get("time", [])
        temps = raw_hourly.get("temperature_2m", [])
        rhs = raw_hourly.get("relative_humidity_2m", [])
        winds = raw_hourly.get("wind_speed_10m", [])
        precips = raw_hourly.get("precipitation", [])
        pressures = raw_hourly.get("surface_pressure", [])

        now_iso = datetime.now(timezone.utc).isoformat()[:13]
        start_idx = 0
        for i, t in enumerate(times):
            if t[:13] >= now_iso:
                start_idx = i
                break

        count = 0
        for i in range(start_idx, min(len(times), start_idx + limit_hours)):
            t_str = times[i]
            temp = temps[i] if i < len(temps) and temps[i] is not None else 28.0
            rh = rhs[i] if i < len(rhs) and rhs[i] is not None else 50.0
            ws = winds[i] if i < len(winds) and winds[i] is not None else 8.0
            precip = precips[i] if i < len(precips) and precips[i] is not None else 0.0
            pressure = pressures[i] if i < len(pressures) and pressures[i] is not None else 1012.0

            try:
                dt = datetime.fromisoformat(t_str)
            except Exception:
                dt = datetime.now(timezone.utc) + timedelta(hours=count)

            win = self._score_single_window(
                window_id=f"WIN-{zone_id}-{dt.strftime('%Y%m%d%H')}",
                dt=dt,
                temp=float(temp),
                rh=float(rh),
                ws=float(ws),
                precip=float(precip),
                pressure=float(pressure)
            )
            windows.append(win)
            count += 1

        # Return windows sorted by descending suitability score
        return sorted(windows, key=lambda w: w.suitability_score, reverse=True)

    def _score_single_window(
        self,
        window_id: str,
        dt: datetime,
        temp: float,
        rh: float,
        ws: float,
        precip: float,
        pressure: Optional[float]
    ) -> ForecastWindow:
        score = 100
        safety_concerns: List[str] = []
        rationales: List[str] = []

        # 1. Rain check (Strict disqualification)
        if precip >= self.rain_threshold_mmh:
            score = 10
            safety_concerns.append(f"Forecast precipitation ({precip:.1f} mm/h) provides natural suppression; spraying causes runoff.")
            rationales.append("Rainfall eliminates need for municipal intervention.")
            label = "PROHIBITED"
            return ForecastWindow(
                window_id=window_id,
                start_time=dt.isoformat(),
                end_time=(dt + timedelta(hours=1)).isoformat(),
                hour_label=dt.strftime("%I:%M %p"),
                suitability_score=score,
                suitability_label=label,
                forecast_temp_c=round(temp, 1),
                forecast_rh_percent=round(rh, 1),
                forecast_wind_kmh=round(ws, 1),
                forecast_precipitation_mmh=round(precip, 1),
                forecast_pressure_hpa=round(pressure, 1) if pressure else None,
                rationale="; ".join(rationales),
                safety_concerns=safety_concerns
            )

        # 2. Humidity penalty
        if rh >= self.prohibitive_rh:
            penalty = int((rh - self.prohibitive_rh) * 4) + 30
            score -= penalty
            safety_concerns.append(f"Excessive humidity ({rh:.0f}% >= {self.prohibitive_rh:.0f}%): risk of fog and roadway puddling.")
        elif rh > self.optimal_rh_max:
            score -= int((rh - self.optimal_rh_max) * 1.5)
        elif rh < self.optimal_rh_min:
            score -= 10
            rationales.append("Dry air accelerates droplet evaporation.")
        else:
            rationales.append("Optimal relative humidity for droplet deposition.")

        # 3. Wind speed penalty
        if ws >= self.prohibitive_wind:
            score -= 45
            safety_concerns.append(f"High wind speed ({ws:.1f} km/h >= {self.prohibitive_wind:.0f} km/h): mist will drift away from roadway.")
        elif ws > self.optimal_wind_max:
            score -= int((ws - self.optimal_wind_max) * 3)
            rationales.append("Moderate wind drift expected.")
        elif ws < self.optimal_wind_min:
            score -= 5
            rationales.append("Stagnant winds; localized mist concentration.")
        else:
            rationales.append("Ideal gentle dispersion breeze (4-14 km/h).")

        # 4. Temperature & evaporation feasibility
        if temp >= 38.0:
            score -= 15
            safety_concerns.append("Extreme heat will evaporate applied moisture in <12 minutes.")
        elif temp <= 5.0:
            score -= 20
            safety_concerns.append("Cold temperatures with high humidity risk condensation fogging.")
        else:
            rationales.append(f"Moderate thermal conditions ({temp:.1f}°C).")

        # Ensure score bounds
        score = max(5, min(98, score))

        # Determine label
        if score >= 80:
            label = "OPTIMAL"
        elif score >= 60:
            label = "MODERATE"
        elif score >= 35:
            label = "POOR"
        else:
            label = "PROHIBITED"

        return ForecastWindow(
            window_id=window_id,
            start_time=dt.isoformat(),
            end_time=(dt + timedelta(hours=1)).isoformat(),
            hour_label=dt.strftime("%I:%M %p"),
            suitability_score=score,
            suitability_label=label,
            forecast_temp_c=round(temp, 1),
            forecast_rh_percent=round(rh, 1),
            forecast_wind_kmh=round(ws, 1),
            forecast_precipitation_mmh=round(precip, 1),
            forecast_pressure_hpa=round(pressure, 1) if pressure else None,
            rationale="; ".join(rationales) or "Meteorological conditions evaluated.",
            safety_concerns=safety_concerns
        )
