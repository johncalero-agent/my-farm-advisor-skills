# my-farm-row-crop-dashboard — Agent Operating Rules

## Scope

This skill generates a grower-level Row Crop Intelligence Dashboard focused on soil health analysis for soybean production. It reads data from the approved `DATA_PIPELINE_DATA_ROOT` runtime tree and falls back to sample data in the my-farm-advisor skill tree when runtime data is not available.

## When to invoke this skill

Load this skill's `AGENTS.md` when the request involves:
- Generating or running the row crop dashboard
- Modifying soil health scoring logic
- Updating action alert thresholds or recommendations
- Changing visualization output formats
- Adding new data sources to the dashboard

## Runtime environment

- The dashboard expects `DATA_PIPELINE_DATA_ROOT` to point to the runtime data root.
- If the environment variable is not set, the dashboard uses sample data from:
  - `my-farm-advisor/soil/ssurgo-soil/examples/`
  - `my-farm-advisor/field-management/field-boundaries/examples/`
  - `my-farm-advisor/weather/nasa-power-weather/examples/`
  - `my-farm-advisor/soil/cdl-cropland/examples/`

## Dependencies

```
streamlit>=1.28
plotly>=5.17
pandas>=2.0
numpy>=1.24
geopandas>=0.13
```

Install with:
```bash
pip install streamlit plotly pandas numpy geopandas
```

## File change rules

- All dashboard source code lives under `my-farm-row-crop-dashboard/`
- Generated outputs (screenshots, exports) go to `examples/` or the runtime reports path
- Do not commit large data files to the repository
- `SOIL_HEALTH_SCORE.md` must be updated whenever scoring logic changes
- `ACTION_ALERT_GUIDE.md` must be updated whenever alert thresholds change
- Run the dashboard with streamlit to verify changes before committing:
  ```bash
  streamlit run scripts/generate_grower_dashboard.py
  ```

## Color system rules

- Alert colors are **reserved for alerts only**. Never reuse alert colors for charts, maps, or KPIs.
- Alert color map (zero overlap):
  - Purple `#7C3AED` — Nitrogen Leaching Risk
  - Brown `#92400E` — Compaction Stress
  - Amber `#F59E0B` — Acidity Lockup
  - Sandy `#D97706` — Drought Susceptibility
  - Cyan `#0891B2` — Waterlogging Risk
- Score status colors: Green `#10B981` (Excellent), Teal `#0D9488` (Healthy), Amber `#F59E0B` (Monitor), Red `#DC2626` (High Priority)
- Chart colors use slate `#475569`, teal `#0F766E`, and lavender `#A78BFA`

## Data path conventions

The dashboard reads from standardized runtime paths:
- Weather: `growers/<g>/farms/<f>/fields/<field>/weather/daily_weather.csv`
- Boundaries: `growers/<g>/farms/<f>/fields/<field>/boundary/field_boundary.geojson`
- CDL: `growers/<g>/farms/<f>/derived/tables/<farm>_cdl_*_full_composition.csv`
- Soil: SSURGO CSV in field soil directory or sample fallback
- Satellite: `growers/<g>/farms/<f>/fields/<field>/satellite/sentinel/manifest.json`

## Testing

Before committing changes, verify:
1. Streamlit launches: `streamlit run scripts/generate_grower_dashboard.py`
2. All 6 tabs render without errors
3. Soil scores compute correctly for at least 10 fields
4. Action alerts trigger based on configured thresholds
5. Geospatial map renders field markers
6. Weather charts render when data is available
7. Crop suitability comparison produces results for all 3 crops
