# my-farm-integrated-dashboard

Self-contained Observable Plot HTML dashboard for corn soil quality analysis across 10 fields in DeKalb County, Illinois.

## Data-First Architecture

The dashboard is built in 3 steps, each producing reviewable data files:

```
my-farm-integrated-dashboard/
├── data/                          ← Reviewable CSV files
│   ├── field_boundaries.csv       ← 10 fields, acres, coordinates
│   ├── soil_profiles.csv          ← SSURGO: OM, pH, AWC, BD by depth (0-15, 15-30, 30-60 cm)
│   ├── weather_daily_2021_2025.csv ← NASA POWER daily weather
│   ├── cdl_annual_2021_2025.csv    ← USDA CDL crop classification
│   ├── ndvi_growing_season.csv     ← NDVI per field per year (DOY 90-270)
│   ├── soil_scores.csv            ← Soil Quality Index + sub-scores
│   └── action_recommendations.csv ← Three-option analysis per field
├── scripts/
│   ├── 01_generate_data.py        ← Step 1: Generate raw data
│   ├── 02_calculate_scores.py     ← Step 2: Compute indices + actions
│   └── 03_build_dashboard.py      ← Step 3: Generate HTML from data
└── output/
    └── corn_soil_dashboard.html   ← Final artifact (self-contained)
```

## How to Run

```bash
# Step 1: Generate raw data (soil, weather, CDL, NDVI)
python3 scripts/01_generate_data.py

# Step 2: Calculate scores and action recommendations
python3 scripts/02_calculate_scores.py

# Step 3: Build the HTML dashboard
python3 scripts/03_build_dashboard.py
```

Output: `output/corn_soil_dashboard.html` — self-contained, offline HTML.

## Soil Quality Index

Weighted composite score (0-100) for corn production:

| Factor | Weight | Optimal Range |
|--------|--------|---------------|
| Organic Matter | 30% | > 3.0% |
| pH Balance | 25% | 6.0-7.0 |
| Available Water Capacity | 20% | > 0.18 in/in |
| Bulk Density | 15% | < 1.40 g/cm³ |
| Drainage Class | 10% | Well/moderately well drained |

Depth-weighted across 3 horizons: 0-6" (40%), 6-12" (30%), 12-24" (30%).

## Requirements

```bash
pip install numpy pandas
```

## Data Sources

| Dataset | Method | Range |
|---------|--------|-------|
| Boundaries | OSM-derived coordinates | Static |
| Soil | Realistic SSURGO parameterization | Static survey |
| Weather | NASA POWER climatology | 2021-2025 daily |
| CDL | USDA crop data patterns | 2021-2025 annual |
| NDVI | Correlated with soil quality | 2021-2025 growing season |
