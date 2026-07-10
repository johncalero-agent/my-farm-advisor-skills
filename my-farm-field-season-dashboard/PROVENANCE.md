# Provenance — my-farm-field-season-dashboard

## Origin

This skill was created as Assignment 3 for the My Farm Advisor skill catalog.
It is a new, standalone top-level skill that consumes outputs from the existing
`data-pipeline` subskill without modifying it.

## Source conventions

- Data inputs follow the canonical `data-pipeline` runtime path conventions
  documented in `my-farm-advisor/data-pipeline/README.md` and
  `my-farm-advisor/data-pipeline/src/scripts/lib/paths.py`.
- CDL crop codes and names follow the mapping in
  `my-farm-advisor/soil/cdl-cropland/src/cdl_reporting.py`.
- Dashboard styling (colors, fonts, DPI) aligns with existing pipeline reporting
  scripts (e.g., `generate_ndvi_cards.py`).

## Dependencies

- Python 3.10+
- `geopandas`, `rasterio`, `matplotlib`, `numpy`, `pandas`, `rasterstats`
- Optional: `statsmodels` (for LOESS smoothing; falls back to rolling mean)

## Maintenance

- Created: 2026-07-10
- Branch: `assignment-3`
- Fork: `johncalero-agent/my-farm-advisor-skills`
