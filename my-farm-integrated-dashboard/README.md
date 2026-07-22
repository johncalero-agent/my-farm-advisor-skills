# my-farm-integrated-dashboard

Self-contained Observable Plot HTML dashboard for corn soil quality analysis across 10 fields in DeKalb County, Illinois.

## Features

- **Soil Quality Index (0-100)** — composite score from organic matter, pH, AWC, bulk density, and drainage class
- **Field Rankings** — best-to-worst bar chart with inline NDVI sparklines
- **Geospatial Map** — single-field map with dropdown selector
- **Soil Profile Gallery** — OM, pH, AWC by depth (0-6", 6-12", 12-24") with corn optimal range indicators
- **Weather Small Multiples** — 5-year rainfall, temperature, GDD, and climate anomaly data
- **Action Recommendations** — three-option analysis per field: fix for corn, switch to soybeans, or do nothing
- **NDVI Correlation Alerts** — flags fields where soil quality AND NDVI are both low
- **Year Dropdown** (2021-2025) — updates weather context, validates soil readings

## How to Run

```bash
python3 scripts/generate_dashboard.py
```

Output: `output/corn_soil_dashboard.html` — self-contained, works offline in any modern browser.

## Requirements

```bash
pip install numpy pandas
```

## Data Sources

| Dataset | Source | Time Range |
|---------|--------|------------|
| Soil profiles | Generated from realistic SSURGO parameters | Static |
| Weather | Generated from NASA POWER climatology | 2021-2025 daily |
| CDL | Generated, filtered for corn-dominant fields | 2021-2025 |
| NDVI | Generated, correlated with soil quality | 2021-2025 growing season |
| Field boundaries | OSM-derived, 10 fields ≥ 400 acres | Static |
