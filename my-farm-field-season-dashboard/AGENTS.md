# Local Instructions — my-farm-field-season-dashboard

## Purpose

This skill generates aligned field-season mini-dashboards that combine Sentinel
NDVI, daily weather, and CDL crop-year data for one field and one growing
season per image.

## Safe edit scope

Edits should stay inside `my-farm-field-season-dashboard/` unless the user
explicitly asks for repo-wide work. Do not edit sibling skill trees from here.

## Read nearby docs first

1. [`README.md`](./README.md) — workflow overview and example command
2. [`SKILL.md`](./SKILL.md) — routing entrypoint
3. [`../AGENTS.md`](../AGENTS.md) — root asset and validation policy

## Runtime contract

- This skill reads **only** from the `data-pipeline` runtime tree under
  `DATA_PIPELINE_DATA_ROOT`. It does not create its own data roots.
- Required paths:
  - `growers/<grower>/farms/<farm>/fields/<field>/weather/daily_weather.csv`
  - `growers/<grower>/farms/<farm>/fields/<field>/satellite/sentinel/manifest.json`
  - `growers/<grower>/farms/<farm>/derived/tables/<farm>_cdl_*_full_composition.csv`
  - `shared/cdl/rasters/CDL_<year>_CONUS.tif` (or state variant)
  - `growers/<grower>/farms/<farm>/fields/<field>/boundary/field_boundary.geojson`
- Output path:
  - `growers/<grower>/farms/<farm>/fields/<field>/derived/reports/<field>_<year>_season_dashboard.png`
- Example artifacts may be committed to `examples/` for assignment submission.

## Local validation

Run the root validator after structural changes:

```bash
cd ..
./scripts/validate.sh
```

## Dependency notes

This skill uses standard scientific Python packages:
- `geopandas`, `rasterio`, `matplotlib`, `numpy`, `pandas`, `rasterstats`

It does not import from `superior-byte-works-skills` or vendor external skills.
