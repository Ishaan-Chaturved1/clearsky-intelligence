# ClearSky Intelligence — Scientific Methodology & Atmospheric Intervention Rules

**Document Version:** 2.0-Production  
**Domain:** Environmental Atmospheric Physics & Urban Fugitive Dust Suppression  
**System:** ClearSky Intelligence Decision Support Platform (Delhi NCR 12-Sector Grid)  

---

## 1. Executive Scientific Premise

Urban particulate matter in South Asian megacities comprises two distinct aerosol regimes with fundamentally different mechanical behaviors:

1. **Fine Accumulation Mode Particles ($\text{PM}_{2.5}$, Aerodynamic Diameter $\le 2.5\ \mu\text{m}$):**
   - **Primary Origins:** Secondary aerosol formation, high-temperature combustion (vehicular tailpipes, coal-fired power stations, industrial emissions, brick kilns, agricultural stubble burning).
   - **Atmospheric Physics:** Fine particles remain suspended for days, disperse regionally over synoptic scales, and have relaxation times measured in milliseconds.
   - **Physical Droplet Interaction:** Municipal mist cannons emit droplets between $30\ \mu\text{m}$ and $100\ \mu\text{m}$. Due to aerodynamic slipstream divergence around falling droplets, fine submicron particles follow the gas streamlines around the droplet and escape inertial impaction. Brownian diffusion is negligible for $1\text{--}2.5\ \mu\text{m}$ particles.
   - **Conclusion:** **Water spraying cannot wash, scrub, or mitigate fine $\text{PM}_{2.5}$, combustion soot, or wildfire/crop-burning smoke.** Recommending water spraying merely because ambient $\text{PM}_{2.5}$ or overall AQI is high is scientifically invalid and wastes municipal water.

2. **Coarse Settleable Particulate Matter ($\text{PM}_{10-2.5}$, Aerodynamic Diameter $2.5\ \mu\text{m} \text{ to } 10\ \mu\text{m}$):**
   - **Primary Origins:** Mechanical grinding, unpaved road shoulders, tire-pavement shear, construction excavation, demolition debris, and mineral soil resuspension.
   - **Physical Droplet Interaction:** Coarse particles carry sufficient inertia to cross fluid streamlines and collide with falling mist droplets (inertial impaction). Furthermore, applying moisture to ground surfaces binds surface fines, preventing wind and vehicular shear resuspension.
   - **Operational Objective:** ClearSky Intelligence targets **only coarse fugitive dust events** where mechanical ground wetting or localized misting provides plausible physical suppression.

---

## 2. Ingested Data Sources & Normalization

All environmental inputs adhere to strict ingestion, unit normalization, and validation rules:

| Domain | Provider | Ingested Metrics | Native Units | Normalized Units | Validation / Quality Checks |
|---|---|---|---|---|---|
| **Ground Air Quality** | OpenAQ v3 / CPCB / DPCC | $\text{PM}_{10}$, $\text{PM}_{2.5}$, $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{O}_3$ | $\mu\text{g/m}^3$ | $\mu\text{g/m}^3$ | Stale check ($>3\text{h}$), physical contradiction check ($\text{PM}_{10} < \text{PM}_{2.5}$ rejected), station distance $<25\text{ km}$ |
| **Meteorology & Forecast** | Open-Meteo API | Temperature ($2\text{m}$), Relative Humidity, Wind Speed ($10\text{m}$), Wind Direction, Surface Pressure, Hourly Forecast ($24\text{h}$) | ${}^\circ\text{C}$, $\%$, $\text{km/h}$, ${}^\circ$, $\text{hPa}$, $\text{mm/h}$ | Native SI | Sensor bounds, missing delta detection, WMO pressure tendency calculation |
| **Thermal Anomalies** | NASA FIRMS VIIRS (SNPP / NOAA-20) | Active Fire Points, Fire Radiative Power (FRP), Confidence | Lat/Lon, $\text{MW}$ | Decimal Degrees | Trajectory alignment within $50\text{ km}$ upwind sector |
| **Urban Geometry** | OpenStreetMap (Overpass API) | Road network, lane classification, civil construction points | Lat/Lon, OSM tags | Length ($\text{km}$), Width ($\text{m}$), Area ($\text{m}^2$) | Proximity buffer ($\le 500\text{ m}$), candidate corridor filtering |

### 2.1 Indian National CPCB AQI Calculation
Where an AQI value is calculated or displayed, ClearSky utilizes the documented **CPCB 8-Sub-Index Breakpoint Standard** rather than generic or US EPA scales:

$$I_p = I_{lo} + \frac{I_{hi} - I_{lo}}{B_{hi} - B_{lo}} (C_p - B_{lo})$$

$$\text{AQI} = \max(I_{\text{PM10}}, I_{\text{PM2.5}})$$

---

## 3. Atmospheric Feature Engineering

### 3.1 Barometric Pressure Trend & Weather Pattern Analysis
Surface pressure ($P_{\text{surface}}$ in $\text{hPa}$) provides critical synoptic context regarding air mass stagnation and frontal transitions. ClearSky computes pressure changes across configurable intervals ($3\text{h}$, $6\text{h}$, and $12\text{h}$):

$$\Delta P_{3h} = P(t) - P(t - 3\text{h})$$

- **WMO Pressure Tendencies:**
  - $\Delta P_{3h} > +1.5\text{ hPa}$: **RISING** (Building anticyclone or cold surface high; associated with clear skies, nocturnal radiation cooling, and strong ground-level thermal inversions).
  - $\Delta P_{3h} < -1.5\text{ hPa}$: **FALLING** (Approaching trough, western disturbance, or active frontal passage; indicates destabilizing atmosphere, increasing gustiness, or impending precipitation).
  - $|\Delta P_{3h}| \le 1.5\text{ hPa}$: **STEADY** (Persistent synoptic stagnation).

**Scientific Guardrail:** Atmospheric pressure is strictly supporting evidence. ClearSky never triggers or suppresses water spraying based on barometric pressure alone.

### 3.2 Dalton Aerodynamic Evaporation & Road Surface Drying Time
Applying water to a road surface is only justifiable if the resulting surface dampness persists long enough to suppress dust resuspension. The platform estimates the hourly surface evaporation rate ($E_{\text{rate}}$ in $\text{mm/h}$) using an aerodynamic Dalton formulation:

$$e_s(T) = 6.112 \times \exp\left(\frac{17.67 \times T}{T + 243.5}\right) \quad [\text{Saturation Vapor Pressure, hPa}]$$

$$e_a(T, \text{RH}) = e_s(T) \times \frac{\text{RH}}{100} \quad [\text{Actual Vapor Pressure, hPa}]$$

$$E_{\text{rate}} = \max\left(0.05, (0.089 + 0.0782 \cdot u) \times (e_s - e_a)\right) \quad [\text{mm/h}]$$

Where $u$ is the $10\text{m}$ wind speed in $\text{m/s}$. Given an operational water application layer $D_{\text{water}} = 0.4\text{ mm}$ ($0.4\text{ L/m}^2$), the estimated surface drying time is:

$$t_{\text{drying}} = \min\left(180, \frac{0.4}{E_{\text{rate}}} \times 60\right) \quad [\text{minutes}]$$

- If $t_{\text{drying}} < 12\text{ minutes}$ (e.g., during summer afternoons with $T > 40^\circ\text{C}$ and low humidity), spraying water is ineffective because the road dries almost instantly, wasting water. In this condition, ClearSky recommends `ALTERNATIVE_DUST_CONTROL_SUGGESTED` (chemical dust suppressants, gravel blankets, or vacuum sweeping).

### 3.3 Wind Drift and Mist Dispersion
Municipal mist cannons discharge droplets at high velocity. If ambient horizontal wind speed exceeds $20\text{ km/h}$ ($5.5\text{ m/s}$):
- Mist plumes are deflected laterally away from target roadbeds.
- Droplets drift into pedestrian footpaths, storefronts, and cross-traffic, causing visibility hazards without capturing targeted road dust.

---

## 4. Deterministic 3-Layer Decision Engine

Decisions follow a strict hierarchical precedence structure:

```
[Layer 1: Safety & Reliability Gates]
       │ (Any gate violated?)
       ├── YES ──> Suppress Intervention (DISCOURAGED or ADVISORY_ONLY)
       └── NO
            │
[Layer 2: Particulate Speciation & Dust Dominance]
       │ (Is PM10 elevated & ratio >= 2.0?)
       ├── NO  ──> INTERVENTION_DISCOURAGED (Combustion soot / fine aerosols)
       └── YES
            │
[Layer 3: Intervention Optimization & Targeting]
       │ (Evaluate Drying Time, Construction Hotspots & Priority)
       ├── Drying < 12 min ──> ALTERNATIVE_DUST_CONTROL_SUGGESTED
       ├── Construction Proximity ──> TARGETED_INTERVENTION_RECOMMENDED
       └── Standard Coarse Dust ──> INTERVENTION_RECOMMENDED
```

### Complete Decision Rules Summary

| Rule ID | Name | Trigger Condition | Decision Impact | Scientific & Operational Rationale |
|---|---|---|---|---|
| **RULE-01** | Data Freshness & Sensor Integrity | Reading age $>3\text{h}$, missing critical values, or $\text{PM}_{10} < \text{PM}_{2.5}$ | `ADVISORY_ONLY` | Prevents operational deployment based on stale, unverified, or unphysical sensor signals. |
| **RULE-02** | Active Rain Preclusion | Precipitation $\ge 0.1\text{ mm/h}$ or recent rain | `INTERVENTION_DISCOURAGED` | Natural wet deposition already suppresses dust; mechanical spraying adds road slip hazards and wastes water. |
| **RULE-03** | Upwind Biomass Fire Smoke Exclusion | Active fire within $50\text{ km}$ aligned with wind vector $\pm 45^\circ$ | `INTERVENTION_DISCOURAGED` | Elevated PM is driven by submicron combustion soot that water mist cannons cannot physically scrub. |
| **RULE-04** | High Humidity Fog & Moisture Risk | Ambient Relative Humidity $\ge 80\%$ | `INTERVENTION_DISCOURAGED` | In near-saturated air, water droplets fail to evaporate, exacerbating dense artificial fog, road pooling, and traffic hazards. |
| **RULE-05** | High Wind Drift & Traffic Hazard | Wind Speed $\ge 20\text{ km/h}$ ($5.5\text{ m/s}$) | `INTERVENTION_DISCOURAGED` | Droplet plumes drift off-target; excessive drift reduces impaction efficiency and endangers pedestrian/traffic safety. |
| **RULE-06** | Coarse Dust Dominance Threshold | $\text{PM}_{10} \ge 120\ \mu\text{g/m}^3$ and $\text{PM}_{10}/\text{PM}_{2.5} \ge 2.0$ | `INTERVENTION_RECOMMENDED` | Mechanical dust signature confirmed. Water droplets achieve physical impaction with coarse particles. |
| **RULE-07** | Combustion Soot Dominance Exclusion | $\text{PM}_{2.5} > 100\ \mu\text{g/m}^3$ and $\text{PM}_{10}/\text{PM}_{2.5} < 2.0$ | `INTERVENTION_DISCOURAGED` | High total pollution is dominated by fine vehicular or combustion exhaust; misting will not remediate fine fraction. |
| **RULE-08** | Construction Proximity Spatial Escalation | Active construction/demolition site within $500\text{ m}$ of sector corridor | `TARGETED_INTERVENTION_RECOMMENDED` | Localized fugitive dust hotspot. Priority escalated ($+1$); perimeter dust mitigation and targeted corridor wetting recommended. |
| **RULE-09** | Extreme Evaporative Drying Preclusion | Surface drying time $<12\text{ min}$ under high heat/wind | `ALTERNATIVE_DUST_CONTROL_SUGGESTED` | Water applied evaporates too rapidly to justify consumption. Chemical dust suppressants, hygroscopic salts, or vacuum sweepers recommended. |

---

## 5. Spatial Intelligence & Road Segment Targeting

### 5.1 Inverse Distance Weighting (IDW) Interpolation
Sector centroids without dedicated collocated monitoring stations estimate ambient concentrations using inverse distance weighting of nearby stations within $R_{\max} = 25\text{ km}$:

$$\hat{C}_z = \frac{\sum_{i=1}^K w_i C_i}{\sum_{i=1}^K w_i}, \quad w_i = \frac{1}{d(z, s_i)^p} \quad (p = 2)$$

Where $d(z, s_i)$ is computed via the great-circle Haversine formula.

### 5.2 Precision Corridor Water Demand Formula
Candidate road segments are extracted from OpenStreetMap and ranked by surface area, traffic index, and construction adjacency:

$$\text{Surface Area } (A_s) = L_{\text{segment}} \times W_{\text{lane}} \quad [\text{m}^2]$$

$$\text{Water Required } (V_w) = A_s \times \text{Application Rate } (0.4\text{ L/m}^2) \quad [\text{Liters}]$$

$$\text{Tanker Trips} = \left\lceil \frac{V_w}{C_{\text{tanker}}} \right\rceil \quad (C_{\text{tanker}} = 5,000\text{ L default})$$

$$\text{Operating Expenditure (INR)} = \frac{V_w}{1000} \times \text{Cost}_{\text{water}} + \text{Trips} \times \text{Cost}_{\text{trip}}$$

---

## 6. Forecast-Based Intervention Planning

Operating windows are evaluated across hourly forecast horizons ($12\text{--}24\text{h}$) to rank the **Best Time to Spray**:

$$\text{Suitability Score } (S) = \max\left(0, 100 - P_{\text{rain}} - P_{\text{wind}} - P_{\text{humidity}} - P_{\text{heat}}\right)$$

- **Penalties:**
  - $P_{\text{rain}} = 100$ if precipitation $> 0.1\text{ mm/h}$.
  - $P_{\text{wind}} = 40 \times \max(0, \text{wind} - 12) / 8$.
  - $P_{\text{humidity}} = 50 \times \max(0, \text{RH} - 75) / 15$.
  - $P_{\text{heat}} = 30$ if $T > 38^\circ\text{C}$ and $\text{RH} < 25\%$.

Windows are categorized into `OPTIMAL` ($S \ge 75$), `MODERATE` ($50 \le S < 75$), `POOR` ($25 \le S < 50$), and `PROHIBITED` ($S < 25$).

---

## 7. Predictive Effectiveness Framework

ClearSky implements a transparent framework for measuring empirical post-intervention outcomes ($\Delta \text{PM}_{10}$ relative to nearby untreated control sectors).

### Scientific Commitment Against Artificial Predictions
- **No Synthetic Machine Learning Labels:** The platform explicitly **refuses to invent synthetic reductions or fabricate trained neural network coefficients** in the absence of verified municipal telemetry.
- **Empirical Calibration Status:** Until longitudinal intervention logs are recorded with collocated sensor pairs, the predictive model is marked as `CALIBRATING`. Decisions are driven by transparent physical and meteorological rules.

---

## 8. Multi-Scenario Water Audit & Conservation Analytics

The audit module compares four distinct municipal operating strategies:

1. **Fixed Scheduled Spraying (Status Quo):** Fixed runs ($3\text{ runs/zone/day}$) deployed regardless of weather, dust composition, or rain.
2. **Naive AQI-Threshold Spraying:** Deploys whenever total AQI exceeds 200, spraying into combustion smoke and rain.
3. **ClearSky Targeted Intelligence:** Deploys strictly when coarse dust dominates, wind $<20\text{ km/h}$, $\text{RH} < 80\%$, and drying time $\ge 12\text{ min}$.
4. **Alternative Dust Control:** Deploys chemical dust suppressants, surface crusting agents, and mechanical vacuum sweepers on persistent hot corridors.

Audit metrics are exportable to CSV with full formula and parameter transparency.

---

## 9. Environmental Ethics & Non-Potable Water Notice

- **Non-Potable Water Requirement:** Municipal anti-smog spraying must **never use treated municipal potable water**. Operations must use secondary treated sewage effluent (STP treated non-potable water).
- **Source Control Precedence:** Water spraying is a temporary, localized palliative measure. It is **not a substitute for root-cause emission controls** (enforcing construction dust barriers, paving road shoulders, vehicle emission standards, and industrial stack controls).
