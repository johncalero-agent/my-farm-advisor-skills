# my-farm-row-crop-dashboard — Provenance

## Source

This skill was created as the final project for the Agricultural Data Science course.

- **Author:** John Calero
- **Created:** July 2026
- **Repository:** `johncalero-agent/my-farm-advisor-skills` (forked from `borealBytes/my-farm-advisor-skills`)
- **Branch:** `final-project`

## Import Notes

This skill builds on work from previous assignments:
- **Assignment 1:** Data pipeline infrastructure, SSURGO soil workflows, field boundaries, CDL, weather ingestion
- **Assignment 2:** Multi-grower EDA, statistical visualization patterns, cross-data comparisons
- **Assignment 3:** Field-season dashboard, NDVI extraction, weather metrics (GDD, precip, temp), event detection, Plotly HTML generation

## Technical Architecture

The dashboard uses Streamlit as the application framework and Plotly for all charting. The modular source structure separates concerns:
- `data_loader.py`: Data ingestion and fallback logic
- `soil_scoring.py`: Scoring engine with depth-weighted zone analysis
- `action_alerts.py`: Rule-based alert detection with severity levels
- `crop_suitability.py`: Multi-crop comparison engine
- `viz_*.py`: Visualization modules for each dashboard section
- `narrative_engine.py`: Automated interpretation text generation

## Data Flow

```
Runtime Tree (DATA_PIPELINE_DATA_ROOT)
        OR
Sample Data (my-farm-advisor skill tree)
        │
        ▼
  data_loader.py  ──  Unified DataFrame
        │
        ├── soil_scoring.py     ──  Field health scores
        │       └── action_alerts.py  ──  Alert detection
        │       └── crop_suitability.py ──  Crop comparison
        │
        ├── viz_kpi.py           ──  KPI cards, distributions
        ├── viz_exploratory.py   ──  Field size, crop composition
        ├── viz_geospatial.py    ──  Field map
        ├── viz_weather.py       ──  Weather time series
        ├── viz_soil.py          ──  Alert cards, rankings
        └── narrative_engine.py  ──  Interpretation text
                │
                ▼
    generate_grower_dashboard.py (Streamlit App)
```

## Dependencies

- Python 3.9+
- streamlit, plotly, pandas, numpy
- geopandas (optional, for geospatial features)
- All data comes from the NRCS SSURGO database via Soil Data Access (SDA)

## Validation

The dashboard was tested with synthetic sample data simulating a 10-field grower in DeKalb County, Illinois, with realistic SSURGO soil profiles including depth/horizon information.
