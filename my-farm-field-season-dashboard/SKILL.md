---
name: my-farm-field-season-dashboard
description: |
  Generate aligned field-season mini-dashboards that combine Sentinel NDVI,
  daily weather, and CDL crop-year information for one selected field and
  one growing season.
---

# my-farm-field-season-dashboard

Use this skill when the request is about producing a focused, repeatable
field-year storyline image for a single field and growing season.

## When to invoke

- A user asks for a "field season dashboard" or "field-year storyline"
- A user wants to see NDVI, weather, and GDD together for one field-year
- A user needs a quick seasonal summary image for agronomic review

## Start here

1. Read [`README.md`](./README.md) for the workflow overview and example command.
2. Run `scripts/generate_field_season_dashboard.py` with the required arguments.
3. The script reads only from `data-pipeline` runtime paths (weather, Sentinel NDVI, CDL).

## Inputs

- `daily_weather.csv` — per-field daily weather from NASA POWER
- Sentinel `manifest.json` + scene `ndvi_tif` files
- CDL composition tables + shared CDL rasters
- Field boundary GeoJSON

## Output

A single PNG dashboard with four aligned panels (shared time axis):

1. Sentinel NDVI (CDL crop-masked mean)
2. Daily precipitation
3. Temperature extremes (min/max band + mean, °F)
4. Cumulative GDD (base 50°F, cap 86°F)

Plus plot annotations and heuristic captions vs. a 5-year field reference.
