# ClearSky Intelligence — Scientific Methodology & Decision Rules

**Version:** 1.2-Deterministic  
**Authors:** Quantified Minds (Ishaan Chaturvedi & Ankit Kumar Tiwari)  

---

## 1. Core Premise: Targeted Particulate Mitigation

In many urban corridors across South Asia, municipal authorities deploy anti-smog water cannons and road misting trucks based solely on high Air Quality Index (AQI) readings. However, fine particulate matter ($\text{PM}_{2.5}$, aerodynamic diameter $\le 2.5\ \mu\text{m}$) originates predominantly from combustion sources (vehicular exhaust, biomass burning, coal-fired thermal generation, industrial stacks) and cannot be captured or washed from the ambient air by water droplet misting.

Water spray mist cannons are mechanically effective only against **coarse, settleable fugitive dust** ($\text{PM}_{10-2.5}$, aerodynamic diameter $2.5\ \mu\text{m} \text{ to } 10\ \mu\text{m}$) caused by unpaved roads, construction excavation, and mechanical shearing.

**ClearSky Intelligence replaces indiscriminate spraying with evidence-aware decision support:**
1. Determining whether the particulate signature indicates coarse dust dominance.
2. Confirming that ambient weather does not cause droplet drift or artificial fogging.
3. Ensuring sufficient fresh observational evidence exists before deployment.
4. Comparing decisions against fixed-schedule baselines to audit water conservation.

---

## 2. Decision Rules & Scientific Rationale

### Rule 1: Coarse Dust Dominance Indicator
- **Threshold:** $\text{PM}_{10}/\text{PM}_{2.5} \ge 2.0$ with $\text{PM}_{10} \ge 120\ \mu\text{g/m}^3$.
- **Rationale:** Ambient dust events exhibit significant coarse mass relative to fine combustion soot. A high ratio supports a mechanical dust hypothesis.
- **Scientific Limitation:** A high ratio is an empirical indicator, not definitive chemical speciation.

### Rule 2: Active Smoke / Fire Exclusion
- **Threshold:** Thermal anomaly detected by NASA FIRMS within $50\text{ km}$ with an upwind smoke transport trajectory.
- **Rationale:** Water mist cannot mitigate combustion aerosols from agricultural stubble or waste burning.
- **Precedence:** Discourages intervention even if total AQI is severe.

### Rule 3: High Humidity Suppression
- **Threshold:** Ambient Relative Humidity $\ge 80\%$.
- **Rationale:** In near-saturated air, water mist droplets fail to evaporate and cause localized fogging, ground puddle formation, and road hazards with minimal dust-capture benefit.

### Rule 4: High Ambient Wind Dispersion Exclusion
- **Threshold:** 10-meter wind speed $\ge 20\text{ km/h}$.
- **Rationale:** Elevated horizontal winds drift droplet plumes away from targeted dust sources before inertial impaction can occur.

### Rule 5: Atmospheric Inversion Advisory
- **Threshold:** Boundary Layer Height (BLH) $\le 300\text{ m}$ combined with wind speed $\le 5\text{ km/h}$.
- **Rationale:** Shallow planetary boundary layers trap surface emissions in a localized stagnant inversion layer. Elevates candidate priority but does not alone trigger spraying.

### Rule 6: Nearby Construction Dust Hotspot
- **Threshold:** Active civil/construction site mapped within $300\text{ m}$ in OpenStreetMap along with elevated $\text{PM}_{10}$.
- **Rationale:** Proximity to earthmoving or unpaved shoulders provides localized fugitive dust. Increases intervention priority ($+1$) and prompts contractor perimeter compliance reviews.

---

## 3. Water-Efficiency Analytical Formulas

Comparative water efficiency evaluates avoidable water deployment against fixed daily municipal runs:

1. **Baseline Scheduled Operations ($B_{\text{ops}}$):**
   $$B_{\text{ops}} = N_{\text{zones}} \times R_{\text{baseline}} \times D_{\text{days}}$$
   *(Default: $R_{\text{baseline}} = 3.0\text{ runs/zone/day}$)*

2. **Recommended Targeted Operations ($T_{\text{ops}}$):**
   $$T_{\text{ops}} = \sum_{i=1}^{M} \mathbb{I}(\text{Decision}_i = \text{INTERVENTION\_RECOMMENDED})$$

3. **Avoided Operations ($A_{\text{ops}}$):**
   $$A_{\text{ops}} = \max(0, B_{\text{ops}} - T_{\text{ops}})$$

4. **Estimated Water Saved ($W_{\text{saved}}$ in Liters):**
   $$W_{\text{saved}} = A_{\text{ops}} \times V_{\text{run}}$$
   *(Default: $V_{\text{run}} = 5,000\text{ Liters per run}$)*

5. **Operational Reduction Percentage:**
   $$P_{\text{reduction}} = 100 \times \frac{B_{\text{ops}} - T_{\text{ops}}}{B_{\text{ops}}} \quad (\text{safe against zero baseline})$$

---

## 4. Ethical AI & Scientific Boundaries

- **No Medical Claims:** The platform does not claim anti-smog guns eliminate health hazards or reduce ambient $\text{PM}_{2.5}$ exposure.
- **Model vs Observation:** All estimates derived from CAMS/Open-Meteo models are explicitly tagged as `modeled`, never reported as physical ground station readings.
- **Data Absence Transparency:** Missing sensors produce `ADVISORY_ONLY`. The platform never fabricates live measurements.
