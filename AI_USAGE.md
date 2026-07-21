# AI Usage Documentation

This document describes how AI tools were used during the development of the Row Crop Intelligence Dashboard final project.

## Tool Used

**OpenCode** (Anthropic Claude-powered coding assistant) was used throughout the project lifecycle.

## How AI Was Used

### 1. Project Planning & Architecture Design
- **Planning the dashboard structure:** AI helped design the modular source architecture, separating concerns into independent modules (data_loader, soil_scoring, action_alerts, crop_suitability, viz_*, narrative_engine).
- **Scoping requirements:** AI analyzed the full project requirements document and mapped each requirement to specific dashboard sections, ensuring all minimum viable submission criteria were met.
- **Trade-off analysis:** AI helped evaluate Path A (real pipeline data generation) vs. Path B (hybrid sample data) and recommended the pragmatic approach.

### 2. Soil Health Score Formula Development
- **Designing the composite score:** AI proposed the five-property scoring framework with crop-specific weights for soybeans, referencing agronomic best practices (pH sensitivity for Rhizobium, OM importance, drainage requirements).
- **Depth weighting methodology:** AI designed the three-zone depth weighting system (0-15cm, 15-30cm, 30-60cm) based on soybean root zone characteristics.
- **Scoring functions:** AI implemented linear interpolation scoring functions (higher-better, lower-better, near-optimal) for normalizing soil properties to a 0-100 scale.

### 3. Code Implementation
- **Python module development:** AI generated all source code files including data loading, scoring engines, visualization modules, and the main Streamlit application.
- **Bug fixes:** AI identified and fixed two critical bugs in the existing `ssurgo_soil.py` module (`SDA_COLUMNS` column misalignment and `NUMERIC_COLUMNS` undefined reference).
- **Error handling:** AI implemented graceful fallback logic in the data loader so the dashboard works with both runtime data and sample data.

### 4. Visualization Design
- **Chart development:** AI generated Plotly chart code for all required visualizations (histograms, bar charts, scatter plots, radar charts, time series, geospatial maps).
- **Color system design:** AI proposed a zero-overlap color palette where each alert type has a unique, reserved color that cannot be confused with any other dashboard element.
- **Layout optimization:** AI structured the Streamlit app with six logical tabs, clear section headers, and expandable detail views.

### 5. Documentation Generation
- **Explanatory documents:** AI generated `SOIL_HEALTH_SCORE.md` and `ACTION_ALERT_GUIDE.md` with grower-friendly language explaining complex agronomic concepts.
- **README and skill metadata:** AI generated all skill catalog files (SKILL.md, INDEX.md, README.md, AGENTS.md, PROVENANCE.md) following the repository's established conventions.
- **Narrative engine:** AI designed the auto-generated interpretation text that translates data patterns into human-readable insights.

### 6. Debugging & Troubleshooting
- **Repository exploration:** AI explored the full repository structure across multiple branches to understand the codebase before making changes.
- **Data availability analysis:** AI analyzed what runtime data exists vs. what needs to be generated, identifying that no runtime data was available on disk.
- **SSURGO data model analysis:** AI traced through the SSURGO query logic to confirm that depth/horizon data (`hzdept_r`, `hzdepb_r`) was available in the data model despite bugs in the download path.

## Verification

All AI-generated code was reviewed and verified:
- The soil scoring engine was tested with synthetic data to confirm correct normalization
- Action alert thresholds were cross-referenced with agronomic extension publications
- The color system was validated to ensure no duplicate color assignments
- The Streamlit app structure was verified against the project requirements checklist
- All module imports and dependencies were confirmed compatible

## AI Limitations Acknowledged

- AI does not have access to the actual SSURGO database or NASA POWER API, so all data-dependent testing was done with synthetic/sample data
- AI-generated agronomic recommendations are based on published extension guidance but should be verified by a certified agronomist for site-specific application
- The narrative engine generates text based on data patterns; human review is recommended before presenting findings to stakeholders
