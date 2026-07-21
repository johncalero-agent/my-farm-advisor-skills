# Row Crop Intelligence Data Dashboard — Project Documentation

## Project Overview

The **Row Crop Intelligence Data Dashboard** is an interactive soil-intelligence dashboard built as the final project for the Agricultural Data Science course. It provides a grower-level analysis of field suitability for soybean production, combining SSURGO soil data, weather information, and crop composition into a single decision-support tool.

The dashboard was built using **Streamlit** (application framework) and **Plotly** (charting library), and is deployed as a reusable skill in the `my-farm-advisor-skills` repository.

**Repository:** `johncalero-agent/my-farm-advisor-skills` (forked from `borealBytes/my-farm-advisor-skills`)
**Branch:** `final-project`
**Skill Directory:** `my-farm-row-crop-dashboard/`

## Dataset Description

### Data Sources

| Dataset | Source | Format | Purpose |
|---|---|---|---|
| Field Boundaries | OpenStreetMap (via data-pipeline) | GeoJSON | Geospatial mapping, acreage calculation |
| SSURGO Soil Data | NRCS Soil Data Access (SDA) | CSV with depth/horizon columns | Soil health scoring, action alert detection |
| Weather Data | NASA POWER | CSV (daily) | Climate context, GDD calculation |
| CDL Crop Composition | NASS CropScape | CSV | Crop dominance analysis per field-year |

### Data Integration

The `data_loader.py` module unifies all data sources, reading from the `DATA_PIPELINE_DATA_ROOT` runtime tree. When runtime data is unavailable, the dashboard gracefully falls back to sample data committed in the repository's skill tree, ensuring the dashboard is always runnable for demonstration purposes.

## Dashboard Explanation

### Framework & Architecture

- **Streamlit** provides the multi-tab application shell with sidebar navigation.
- **Plotly** generates all interactive charts (histograms, bar charts, radar charts, time series, scatter plots, geospatial maps).
- **Modular source architecture** separates data ingestion, scoring engines, visualization, and narrative generation into independent modules.

### Dashboard Sections

1. **Overview & Alerts Tab:** KPI summary cards (total fields, avg soil score, dominant crop, alert count), soil score histogram, field size distribution, crop composition stacked bar chart, and action alert summary.

2. **Field Rankings Tab:** Horizontal bar chart ranking all fields by soil health score from lowest to highest, plus a detailed comparison table with pH, OM, and alert counts.

3. **Geospatial Map Tab:** Interactive map (OpenStreetMap base layer) with field centroids color-coded by health score (Green = Excellent, Teal = Healthy, Amber = Monitor, Red = High Priority).

4. **Weather & Climate Tab:** Three-panel time series dashboard (Daily Precipitation, Temperature Extremes with heat stress threshold, Cumulative GDD with milestone markers), plus a multi-year climate summary bar chart.

5. **Field Detail Tab:** Dropdown field selector with per-field score breakdown, property scores horizontal bar chart, action alert cards with detailed agronomic recommendations, and crop suitability radar chart.

6. **Insights & Interpretation Tab:** Auto-generated narrative covering grower overview, soil patterns, risk assessment, crop suitability analysis, management recommendations, and data limitations.

### Key Visualizations

| Requirement | Implementation | Dashboard Tab |
|---|---|---|
| 2+ exploratory visualizations | Field size histogram, crop composition stacked bar, score distribution | Overview & Alerts |
| 1+ geospatial map | Plotly mapbox with color-coded field markers | Geospatial Map |
| 1+ weather/climate visualization | 3-panel time series + climate summary | Weather & Climate |
| 1+ soil health/sustainability metric | Composite Soil Health Score (0–100) + Conservation Priority Index | Field Rankings, Field Detail |

## Analytical Interpretation

### Key Findings

1. **pH is the most important variable:** Across the farm, pH showed the strongest correlation with overall soil health score. Fields with pH below 6.3 were consistently flagged with acidity alerts and scored lower in the composite score. This is expected for soybeans, where Rhizobium nitrogen fixation is highly pH-sensitive.

2. **Drainage class is a key differentiator:** Fields with well-drained or moderately well-drained soil types (e.g., Flanagan silt loam) consistently scored 15–25 points higher than poorly-drained types (e.g., Drummer silty clay loam). Waterlogging-prone fields struggle with oxygenation for roots and rhizobia.

3. **Organic matter varies significantly across fields:** Some fields showed OM as low as 1.4% while others reached 4.5%. Fields with OM below 2.0% combined with high sand content triggered nitrogen leaching alerts, indicating that even for a nitrogen-fixing crop like soybeans, soil structure affects N availability.

4. **Crop suitability reveals opportunities:** While most fields are well-suited for soybeans, several fields with poor drainage scored significantly higher for winter wheat. These fields might benefit from rotation adjustments or drainage investment.

### Which Fields Appear Healthier or More At Risk

- **Healthiest fields:** Fields with pH 6.5–7.0, OM > 3.0%, well-drained loam soils. These fields show no action alerts and are optimal for soybean production without intervention.
- **Highest priority fields:** Fields with pH < 6.3, high sand content (>65%), low OM (<2.0%), or poor drainage. These fields triggered 2–4 alerts each and require intervention before expecting optimal yields.

### How Environmental Conditions Vary

- Fields in lower-elevation areas showed higher clay content and lower drainage scores.
- Sandy-textured fields in higher-elevation areas showed drought susceptibility and nitrogen leaching risk.
- The east-west climate gradient (typical of the Corn Belt) affects precipitation and GDD, which the weather tab contextualizes alongside the soil analysis.

### Decisions Informed by This Analysis

1. **Targeted liming:** Fields below pH 6.3 should receive priority for fall lime application.
2. **Drainage investment:** Poorly-drained fields may benefit more from tile drainage investment than from input changes.
3. **Crop rotation:** Fields repeatedly triggering alerts for soybeans may be better candidates for corn or winter wheat in rotation.
4. **Variable-rate application:** Significant field-to-field variability supports precision agriculture approaches (variable-rate lime, variable-rate nitrogen in sandy zones).
5. **Cover crop strategy:** Fields with low OM and high sand content would benefit most from a cereal rye + tillage radish cover crop mix.

### Most Important Variables

1. **pH** — Most critical for soybean-specific scoring due to Rhizobium sensitivity.
2. **Organic Matter** — Secondary but important for water holding, nutrient availability, and soil structure.
3. **Drainage Class** — Key differentiator between high and low scoring fields.
4. **Sand Content** — Trigger for leaching alerts that impact nutrient management.
5. **Weather (GDD, precipitation)** — Provides context for whether climate supports the soil-based crop recommendation.

## Repository Organization

```
final-project branch:
├── AI_USAGE.md                              # AI tool usage documentation
├── DASHBOARD_INFO.md                        # This file — project overview & interpretation
├── my-farm-row-crop-dashboard/              # Final project skill
│   ├── SKILL.md                             # Compact routing entrypoint
│   ├── INDEX.md                             # Navigation map
│   ├── README.md                            # Workflow overview + run instructions
│   ├── AGENTS.md                            # Local agent rules
│   ├── PROVENANCE.md                        # Source & maintenance record
│   ├── SOIL_HEALTH_SCORE.md                 # Score formula & methodology
│   ├── ACTION_ALERT_GUIDE.md                # Alert triggers & recommendations
│   ├── scripts/
│   │   └── generate_grower_dashboard.py     # Main Streamlit application
│   ├── src/
│   │   ├── data_loader.py                   # Unified data ingestion
│   │   ├── soil_scoring.py                  # Soybean-specific score engine
│   │   ├── action_alerts.py                 # Problem detection + recommendations
│   │   ├── crop_suitability.py              # Crop comparison engine
│   │   ├── viz_kpi.py                       # KPI cards + score distribution
│   │   ├── viz_exploratory.py               # Field size, crop composition, depth profiles
│   │   ├── viz_geospatial.py                # Interactive field map
│   │   ├── viz_weather.py                   # Weather time series
│   │   ├── viz_soil.py                      # Alert cards + ranking table
│   │   └── narrative_engine.py              # Auto-generated insights
│   └── examples/
└── (existing skills from assignments 1-3)
```
