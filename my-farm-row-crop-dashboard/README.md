# my-farm-row-crop-dashboard

A reusable skill that generates a **grower-level Row Crop Intelligence Dashboard** — an interactive Streamlit application that combines soil health scoring, action alerts with detailed agronomic recommendations, crop suitability comparison, weather context, and geospatial visualization.

## What It Does

This skill answers the core question: **which fields are best suited for soybean production, which need intervention, and what specific actions should be taken to improve underperforming areas?**

Rather than a static report, it builds an interactive dashboard experience with six focused tabs:

1. **Overview & Alerts** — KPI summary cards, score distribution, field-size analysis, alert summary
2. **Field Rankings** — Horizontal bar chart ranking all fields by soil health score
3. **Geospatial Map** — Interactive map with fields color-coded by health score
4. **Weather & Climate** — Multi-panel time series (precipitation, temperature, GDD) with crop-year selector
5. **Field Detail** — Per-field deep dive with score breakdown, action alerts, and crop suitability comparison
6. **Insights & Interpretation** — Auto-generated narrative with risk assessment and management recommendations

## Data Inputs

All inputs come from the approved `data-pipeline` runtime area, with automatic fallback to sample data:

| Input | Runtime Path | Fallback Source |
|---|---|---|
| Field boundaries | `growers/<g>/farms/<f>/boundary/field_boundaries.geojson` | `examples/real_10_fields_illinois.geojson` |
| Daily weather | `growers/<g>/farms/<f>/fields/<field>/weather/daily_weather.csv` | `examples/sample_weather_2fields_2020_2024.csv` |
| CDL composition | `growers/<g>/farms/<f>/derived/tables/<farm>_cdl_*_full_composition.csv` | `examples/sample_cdl_2_fields.csv` |
| SSURGO soil | `growers/<g>/farms/<f>/fields/<field>/soil/` | `examples/soil_data_10_fields.csv` |

> Soil data must include depth/horizon information (`hzdept_r`, `hzdepb_r`) for the depth-weighted root zone analysis (0–60 cm).

## Dashboard Features

### Soybean Soil Health Score (0–100)

A composite score computed from five depth-weighted soil properties:
- **Organic Matter (30%)** — Water holding, nutrient availability
- **pH Balance (25%)** — Rhizobium nitrogen fixation sensitivity
- **Available Water Capacity (20%)** — Drought resilience
- **Bulk Density (15%)** — Compaction indicator
- **Drainage Class (10%)** — Waterlogging risk assessment

Full formula documentation in [`SOIL_HEALTH_SCORE.md`](./SOIL_HEALTH_SCORE.md).

### Action Alerts (5 Types, Zero Overlap Colors)

Each alert has a unique, non-overlapping color for clear identification:

| Alert | Color | Hex |
|---|---|---|
| Nitrogen Leaching Risk | Deep Purple | `#7C3AED` |
| Compaction Stress | Dark Brown | `#92400E` |
| Acidity Lockup | Bright Amber | `#F59E0B` |
| Drought Susceptibility | Sandy Desert | `#D97706` |
| Waterlogging Risk | Deep Cyan | `#0891B2` |

Each alert includes detailed, multi-step agronomic recommendations specific to soybeans.

### Crop Suitability Comparison

Compares each field's soil profile against optimal requirements for Soybeans, Corn, and Winter Wheat, recommending the best crop based on soil characteristics.

## How to Run

### Prerequisites

```bash
pip install streamlit plotly pandas numpy geopandas
```

### Quick Start (with Streamlit)

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime

streamlit run scripts/generate_grower_dashboard.py
```

### CLI Mode (generate scores without UI)

```bash
python scripts/generate_grower_dashboard.py \
    --grower-slug il-dekalb-grower \
    --farm-slug dekalb-demo-farm \
    --no-streamlit
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--grower-slug` | `il-dekalb-grower` | Grower identifier |
| `--farm-slug` | `dekalb-demo-farm` | Farm identifier |
| `--no-streamlit` | `False` | Run CLI mode instead of Streamlit |

## Where to Find Runtime Data

The dashboard reads from `DATA_PIPELINE_DATA_ROOT`, which should point to the `data-pipeline` runtime tree set up by the `install.sh` script:

```
my-farm-advisor-runtime/
└── data-pipeline/
    ├── growers/
    │   └── <grower-slug>/
    │       └── farms/
    │           └── <farm-slug>/
    │               ├── boundary/
    │               │   └── field_boundaries.geojson
    │               ├── derived/
    │               │   └── tables/
    │               │       └── <farm>_cdl_<start>_<end>_full_composition.csv
    │               └── fields/
    │                   └── <field-slug>/
    │                       ├── boundary/
    │                       ├── weather/
    │                       └── soil/
    └── shared/
        └── cdl/
```

If the runtime tree is not available, the dashboard automatically falls back to sample data committed in the `my-farm-advisor` skill tree.

## Dependencies

- Python 3.9+
- streamlit >= 1.28
- plotly >= 5.17
- pandas >= 2.0
- numpy >= 1.24
- geopandas >= 0.13 (optional, for geospatial features)

## Example Output

The dashboard generates an interactive Streamlit web application. Example outputs can be viewed by running the dashboard locally. Screenshots are saved to `examples/` when the CLI mode is used.

## Assignment Summary

### Skill or workflow name
**`my-farm-row-crop-dashboard`** — Generate a grower-level Row Crop Intelligence Dashboard focused on soil health analysis for soybean production.

### Input files used
Field boundaries (GeoJSON), daily weather (CSV), CDL crop composition (CSV), SSURGO soil data with depth/horizon information (CSV).

### Soil health metrics calculated
Soybean-specific composite score (0–100) with five depth-weighted properties (OM, pH, AWC, Bulk Density, Drainage), Conservation Priority Index, action alert detection (5 types), crop suitability comparison (3 crops).

### Generated output paths
Interactive Streamlit application. CLI mode writes scores to stdout.

### How to rerun
```bash
streamlit run scripts/generate_grower_dashboard.py
```

### Known data limitations
- SSURGO data represents map unit averages; field-scale variability may be higher
- Scores are calibrated for soybeans; different crops use different optimal ranges
- Weather data integration is context-only and does not modify the soil score
- Action alerts are based on soil properties alone; yield history and management history would provide additional context
- All recommendations are agronomic guidance; consult a certified agronomist before implementing
