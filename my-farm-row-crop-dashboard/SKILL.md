---
name: my-farm-row-crop-dashboard
description: |
  Generate a grower-level Row Crop Intelligence Dashboard combining
  soil health scoring, action alerts with detailed agronomic recommendations,
  crop suitability comparison, weather context, and geospatial visualization
  into an interactive Streamlit application.
---

# my-farm-row-crop-dashboard

Use this skill when the request is about generating a comprehensive,
soil-intelligence-focused dashboard for all fields belonging to a grower.

## When to invoke

- A user asks for a "row crop dashboard," "soil health dashboard,"
  "field intelligence report," or "grower-level analysis"
- A user wants soil-based action alerts with agronomic recommendations
- A user needs to compare crop suitability across multiple fields
- A user wants to identify which fields need intervention for soybean production

## Start here

1. Read [`README.md`](./README.md) for the workflow overview and run instructions.
2. Ensure runtime data is available at `DATA_PIPELINE_DATA_ROOT` or use the
   built-in sample data fallback.
3. Run `scripts/generate_grower_dashboard.py` or launch with Streamlit:
   ```bash
   streamlit run scripts/generate_grower_dashboard.py
   ```

## Inputs

- Field boundaries (GeoJSON)
- Daily weather data (CSV)
- CDL crop composition (CSV)
- SSURGO soil data with depth/horizon information (CSV)

## Output

An interactive Streamlit dashboard with six tabs:
1. **Overview & Alerts** — KPI cards, score distribution, alert summary
2. **Field Rankings** — Ranked bar chart and comparison table
3. **Geospatial Map** — Color-coded field map
4. **Weather & Climate** — Multi-panel time series with GDD
5. **Field Detail** — Per-field deep dive with action alerts
6. **Insights & Interpretation** — Auto-generated narrative

## Key features

- Soybean-specific composite Soil Health Score (0–100) with depth weighting
- Five unique action alerts with detailed agronomic recommendations
- Crop suitability comparison (Soybeans vs. Corn vs. Winter Wheat)
- Action alert color system with zero overlap for clear identification
- Geospatial map with fields colored by health score
- Full root zone analysis (0–60 cm) with three depth zones
