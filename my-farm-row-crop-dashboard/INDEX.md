# my-farm-row-crop-dashboard — Index

## Entry points

| File | Purpose |
|------|---------|
| [`SKILL.md`](./SKILL.md) | Compact routing — when to invoke this skill |
| [`README.md`](./README.md) | Workflow overview, quick-start, and run instructions |
| [`AGENTS.md`](./AGENTS.md) | Local rules for agents editing or running this skill |
| [`PROVENANCE.md`](./PROVENANCE.md) | Source record and import notes |
| [`SOIL_HEALTH_SCORE.md`](./SOIL_HEALTH_SCORE.md) | Formula and methodology for the soybean soil health score |
| [`ACTION_ALERT_GUIDE.md`](./ACTION_ALERT_GUIDE.md) | Alert trigger conditions and detailed recommendations |

## Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/generate_grower_dashboard.py`](./scripts/generate_grower_dashboard.py) | Main dashboard generator — Streamlit app or CLI mode |

## Source modules

| Module | Purpose |
|--------|---------|
| [`src/data_loader.py`](./src/data_loader.py) | Unified data ingestion from runtime tree with fallback |
| [`src/soil_scoring.py`](./src/soil_scoring.py) | Soybean-specific composite soil health score engine |
| [`src/action_alerts.py`](./src/action_alerts.py) | Problem detection and detailed agronomic recommendations |
| [`src/crop_suitability.py`](./src/crop_suitability.py) | Crop comparison engine (Soybeans vs. Corn vs. Wheat) |
| [`src/viz_kpi.py`](./src/viz_kpi.py) | KPI cards, score distribution, and field rankings |
| [`src/viz_exploratory.py`](./src/viz_exploratory.py) | Field size, crop composition, depth profiles, radar charts |
| [`src/viz_geospatial.py`](./src/viz_geospatial.py) | Interactive field boundary map |
| [`src/viz_weather.py`](./src/viz_weather.py) | Weather time series and climate context |
| [`src/viz_soil.py`](./src/viz_soil.py) | Action alert cards, soil breakdowns, alert summary |
| [`src/narrative_engine.py`](./src/narrative_engine.py) | Auto-generated insight text |

## Examples

| Example | Description |
|---------|-------------|
| [`examples/`](./examples/) | Generated dashboard screenshots for submitted field-years |
