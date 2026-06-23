---
skill_name: headlands-ring-generator
category: field-management
---

# Headlands Ring Generator

Generate metric-accurate headlands rings from field boundary GeoJSON.

## When to invoke

- User asks about headlands, buffer strips, or field border calculations
- User needs to calculate unplanted border areas for machinery turning
- User has field boundaries in EPSG:4326 but needs metric-accurate areas
- User wants to exclude headlands from variable-rate application zones

## Where to start

1. Read `README.md` for usage and outputs
2. Run `scripts/generate_headlands_rings.py` against existing field boundaries
3. Outputs appear under `growers/<grower>/farms/<farm>/derived/headlands/`

## Inputs

- Field boundary GeoJSON from data-pipeline output (`boundary/field_boundaries.geojson`)
- Buffer distance in meters (default: -21)

## Outputs

- `{farm}_headlands_4326.gpkg` — Headlands ring, EPSG:4326, web-ready
- `{farm}_headlands_utm.gpkg` — Multi-layer analysis in UTM (boundary, buffer, headlands)

## Key features

- Auto-detects UTM zone from field centroid
- Calculates accurate areas in m² and acres
- Negative buffer operation (configurable width)
- Filters out fields too small for buffer
- Handles multi-polygon fields
