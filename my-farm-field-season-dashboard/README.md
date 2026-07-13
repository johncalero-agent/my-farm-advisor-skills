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

> See `examples/osm-1062497612_2022_dashboard.png` and `examples/osm-1062497612_2022_dashboard.html` for the example outputs.

## Assignment summary

### Skill or workflow name

**`my-farm-field-season-dashboard`** — Generate aligned field-season mini-dashboards for one field-year.

### Input files used

All inputs come from the approved `data-pipeline` runtime area:

| Input | Runtime path |
|-------|--------------|
| Daily weather | `growers/<g>/farms/<f>/fields/<field>/weather/daily_weather.csv` |
| Sentinel NDVI | `growers/<g>/farms/<f>/fields/<field>/satellite/sentinel/manifest.json` |
| CDL composition | `growers/<g>/farms/<f>/derived/tables/<farm>_cdl_*_full_composition.csv` |
| CDL raster | `shared/cdl/rasters/CDL_<year>_<fips>.tif` |
| Field boundary | `growers/<g>/farms/<f>/fields/<field>/boundary/field_boundary.geojson` |

### Weather metrics calculated

| Metric | Formula | Units |
|--------|---------|-------|
| Precipitation | `PRECTOTCORR / 25.4` | inches |
| Temperature | `T * 9/5 + 32` | °F |
| GDD (daily) | `max(0, min((Tmax+Tmin)/2, 86) - 50)` | °F·day |
| Cumulative GDD | Sum from planting window (default DOY 90) | °F·day |

### Generated output paths

```
growers/<g>/farms/<f>/fields/<field>/derived/reports/<field>_<year>_season_dashboard.png
growers/<g>/farms/<f>/fields/<field>/derived/reports/<field>_<year>_season_dashboard.html
```

### How to rerun

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime

python scripts/generate_field_season_dashboard.py \
  --grower-slug il-dekalb-grower \
  --farm-slug dekalb-demo-farm \
  --field-slug osm-1062497612 \
  --year 2022 \
  --state-fips 17
```

### Known data limitations

- **5-year reference stats** require historical weather and NDVI for the same field; if missing, the reference comparison degrades gracefully to a plain data summary
- **CDL crop masking** accuracy depends on dominant crop percentage; fields with <50% dominant crop may produce unreliable NDVI means
- **Sentinel scene availability** varies by year and cloud cover; some years may have sparse NDVI coverage
- **GDD accumulation** uses a fixed planting window (DOY 90) rather than actual planting date, which may misalign with true crop development
- **Weather data** is from the NASA POWER reanalysis; it may not match on-station observations exactly
