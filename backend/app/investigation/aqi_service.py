from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CpcbAqiResult(BaseModel):
    """
    Detailed output of Indian National Air Quality Index (CPCB) computation.
    """
    aqi: Optional[int] = Field(default=None, description="Overall Composite CPCB AQI (maximum sub-index)")
    category: Optional[str] = Field(default=None, description="CPCB Air Quality band: Good, Satisfactory, Moderate, Poor, Very Poor, Severe")
    dominant_pollutant: Optional[str] = Field(default=None, description="Pollutant with highest sub-index (e.g. PM10, PM2.5)")
    sub_indices: Dict[str, Optional[int]] = Field(default_factory=dict, description="Calculated sub-index per pollutant")
    warnings: List[str] = Field(default_factory=list, description="Data availability or boundary warnings")
    minimum_pollutants_met: bool = Field(default=False, description="True if at least one valid critical particulate measurement is present")


# Official CPCB Breakpoints: (C_low, C_high, I_low, I_high)
PM10_BREAKPOINTS = [
    (0.0, 50.0, 0, 50),
    (51.0, 100.0, 51, 100),
    (101.0, 250.0, 101, 200),
    (251.0, 350.0, 201, 300),
    (351.0, 430.0, 301, 400),
    (431.0, 500.0, 401, 500),
]

PM25_BREAKPOINTS = [
    (0.0, 30.0, 0, 50),
    (31.0, 60.0, 51, 100),
    (61.0, 90.0, 101, 200),
    (91.0, 120.0, 201, 300),
    (121.0, 250.0, 301, 400),
    (251.0, 380.0, 401, 500),
]


def calculate_sub_index(conc: Optional[float], breakpoints: list) -> Optional[int]:
    """
    Calculates piecewise linear sub-index for a concentration against CPCB breakpoints.
    Extrapolates linearly beyond the severe threshold up to 500.
    Returns None for invalid, negative, or missing concentrations.
    """
    if conc is None or conc < 0:
        return None

    import math
    if math.isnan(conc) or math.isinf(conc):
        return None

    for (c_low, c_high, i_low, i_high) in breakpoints:
        if c_low <= conc <= c_high:
            return int(round(((i_high - i_low) / (c_high - c_low)) * (conc - c_low) + i_low))

    # Extrapolate beyond severe threshold
    if conc > breakpoints[-1][1]:
        c_low, c_high, i_low, i_high = breakpoints[-1]
        return min(500, int(round(i_high + (conc - c_high) * 0.5)))

    return None


def get_cpcb_category(aqi: Optional[int]) -> Optional[str]:
    """
    Maps composite CPCB AQI value to official Indian AQI health category.
    """
    if aqi is None:
        return None
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


def calculate_indian_aqi(pm10: Optional[float], pm25: Optional[float]) -> Optional[int]:
    """
    Backward-compatible CPCB AQI computation.
    Preserves the exact signature, behavior, and output of the original endpoints.py implementation.
    """
    if (pm10 is None or pm10 < 0) and (pm25 is None or pm25 < 0):
        return None

    sub_pm10 = calculate_sub_index(pm10, PM10_BREAKPOINTS)
    sub_pm25 = calculate_sub_index(pm25, PM25_BREAKPOINTS)
    sub_indices = [s for s in (sub_pm10, sub_pm25) if s is not None]

    if not sub_indices:
        return None
    return max(sub_indices)


def calculate_cpcb_aqi_details(
    pm10: Optional[float] = None,
    pm25: Optional[float] = None,
    no2: Optional[float] = None,
    so2: Optional[float] = None
) -> CpcbAqiResult:
    """
    Detailed CPCB AQI calculation returning structured sub-indices, category,
    dominant pollutant, and data completeness warnings.
    """
    warnings: List[str] = []
    sub_indices: Dict[str, Optional[int]] = {}

    sub_pm10 = calculate_sub_index(pm10, PM10_BREAKPOINTS)
    sub_pm25 = calculate_sub_index(pm25, PM25_BREAKPOINTS)

    sub_indices["PM10"] = sub_pm10
    sub_indices["PM2.5"] = sub_pm25

    if pm10 is None or pm10 < 0:
        warnings.append("PM10 measurement is missing or invalid.")
    if pm25 is None or pm25 < 0:
        warnings.append("PM2.5 measurement is missing or invalid.")

    valid_subs = {k: v for k, v in sub_indices.items() if v is not None}

    if not valid_subs:
        return CpcbAqiResult(
            aqi=None,
            category=None,
            dominant_pollutant=None,
            sub_indices=sub_indices,
            warnings=warnings,
            minimum_pollutants_met=False
        )

    # Determine maximum sub-index and dominant pollutant
    dominant_poll = max(valid_subs, key=lambda k: valid_subs[k])
    max_aqi = valid_subs[dominant_poll]
    cat = get_cpcb_category(max_aqi)

    return CpcbAqiResult(
        aqi=max_aqi,
        category=cat,
        dominant_pollutant=dominant_poll,
        sub_indices=sub_indices,
        warnings=warnings,
        minimum_pollutants_met=True
    )
