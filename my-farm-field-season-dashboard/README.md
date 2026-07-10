# my-farm-field-season-dashboard

A reusable skill that produces an aligned field-season mini-dashboard for one
selected field and one growing season. The dashboard combines Sentinel NDVI,
daily weather, and CDL crop-year information into a single image with a shared
time axis, plot annotations, and heuristic captions.

## What it does

This skill answers a focused question: **what seasonal weather and vegetation
patterns show up for this field-year, and how can an advisor quickly read that
story from the plot?**

Rather than a broad report across every field, it builds a small, repeatable
workflow that:

1. Reads `daily_weather.csv` for the selected field-year
2. Pulls Sentinel NDVI scenes and masks them to the dominant CDL crop
3. Calculates precipitation, temperature extremes, and cumulative GDD
4. Generates one aligned dashboard PNG with annotations and callouts

## Dashboard panels

| Panel | Content |
|-------|---------|
| **NDVI** | Sentinel scenes, CDL crop-masked mean, with LOESS smoothing and peak annotation |
| **Precipitation** | Daily bars (inches) + 7-day rolling average |
| **Temperature** | Min/max fill-between band + mean line (°F) |
| **Cumulative GDD** | Line chart with optional 5-year average overlay (base 50°F, cap 86°F) |

## Data inputs

All inputs come from the approved `data-pipeline` runtime area:

| Input | Runtime path |
|-------|--------------|
| Daily weather | `growers/<g>/farms/<f>/fields/<field>/weather/daily_weather.csv` |
| Sentinel NDVI | `growers/<g>/farms/<f>/fields/<field>/satellite/sentinel/manifest.json` |
| CDL composition | `growers/<g>/farms/<f>/derived/tables/<farm>_cdl_*_full_composition.csv` |
| CDL raster | `shared/cdl/rasters/CDL_<year>_CONUS.tif` (or state variant) |
| Field boundary | `growers/<g>/farms/<f>/fields/<field>/boundary/field_boundary.geojson` |

## Requirements

- Python 3.10+
- `geopandas`, `rasterio`, `matplotlib`, `numpy`, `pandas`, `rasterstats`
- A populated `data-pipeline` runtime with farm data (see data-pipeline README)

## Quick start

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime

cd my-farm-field-season-dashboard
python scripts/generate_field_season_dashboard.py \
  --grower-slug il-dekalb-grower \
  --farm-slug dekalb-demo-farm \
  --field-slug osm-1062497612 \
  --year 2022 \
  --state-fips 17
```

The dashboard PNG is written to:
```
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower>/farms/<farm>/fields/<field>/derived/reports/<field>_<year>_season_dashboard.png
```

## Example field-year

The example below was generated for:

- **Field:** `osm-1062497612`
- **Year:** **2022**
- **Crop:** **Soybeans** (72.4% dominant from CDL tables for that field-year)
- **Location:** DeKalb County, Illinois (state FIPS 17)
- **Grower:** `il-dekalb-grower`
- **Farm:** `dekalb-demo-farm`

### Why this field-year?

| Criterion | Assessment |
|-----------|------------|
| CDL crop clarity | Soybeans at 72.4% — clean dominant crop |
| Weather completeness | 365 daily records (standard year, no leap-year bias) |
| Sentinel NDVI coverage | 9 scenes: Mar–Nov (best coverage of any year) |
| 5-year reference | 2021, 2023, 2024, 2025 available for comparison |
| Data cleanliness | No gaps, no errors in pipeline outputs |

### Dashboard highlights

- **Peak NDVI:** 0.604 on DOY 243 (late August — typical for soybeans)
- **Season precipitation:** 28.7 inches
- **Heat stress days:** 0.0 days (>/95°F)
- **Final cumulative GDD:** 3,693 °F·day

> See `examples/osm-1062497612_2022_dashboard.png` for the example output.

## How to rerun

The script is fully parameterized. Change `--field-slug`, `--year`, and
`--state-fips` to target any field-year in the runtime data tree.

Optional overrides:
```bash
python scripts/generate_field_season_dashboard.py \
  --grower-slug <grower> \
  --farm-slug <farm> \
  --field-slug <field> \
  --year <year> \
  --gdd-base 50 \
  --gdd-cap 86 \
  --heat-stress-threshold 95 \
  --planting-doy 90 \
  --output-path /custom/path/output.png
```

## Annotations and callouts

The dashboard includes a title block with:

- Peak NDVI value and day-of-year
- Total growing-season precipitation
- Heat-stress day count (days > 95°F)
- Final cumulative GDD

When 5 years of historical data are available for the same field, heuristic
captions are generated automatically:

- "Peak NDVI arrived ~X days later than the 5-yr avg"
- "Drier-than-average season (Y% of 5-yr avg)"
- "Above-normal heat stress (+Z days vs. 5-yr avg)"
- "Cool season: final GDD W% of 5-yr avg"

If reference data is missing, the callout degrades gracefully to a plain
data summary.

## Skill layout

```
my-farm-field-season-dashboard/
├── SKILL.md              # Routing entrypoint
├── README.md             # This file
├── INDEX.md              # Agent navigation
├── AGENTS.md             # Local operating rules
├── PROVENANCE.md         # Source record
├── scripts/
│   └── generate_field_season_dashboard.py
└── examples/
    └── osm-1062497612_2022_dashboard.png
```
