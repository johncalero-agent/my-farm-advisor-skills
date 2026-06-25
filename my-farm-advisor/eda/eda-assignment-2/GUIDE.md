---
name: eda-assignment-2
version: 1.0.0
author: Boreal Bytes
tags: [eda, assignment, field-boundaries, weather, cdl, cropland, comparison]
---

# Workflow: eda-assignment-2

Field-level EDA comparing three Corn Belt growers (Illinois, Iowa, Nebraska). Produces 12 static outputs: statistical visualizations, comparison tables, and geospatial maps across field boundaries, weather, and CDL/cropland data.

## When to Use This Workflow

- Compare field size distributions across states
- Examine the east-west precipitation and GDD gradient
- Analyze crop composition and rotation differences
- Understand how irrigation changes cropping decisions

## Prerequisites

```bash
pip install pandas geopandas matplotlib seaborn numpy
```

Requires `DATA_PIPELINE_DATA_ROOT` pointing to completed runtime data (see `my-farm-advisor/data-pipeline/README.md`).

## Quick Start

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/runtime
python scripts/run_eda.py
```

Output directory: `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/eda/eda-assignment-2/output/`

## Common Tasks

### Task 1: Field boundary area analysis

**What:** Histogram and boxplot of field areas by grower.

**When to use:** First step — understand scale differences before interpreting weather or CDL.

### Task 2: Climate gradient comparison

**What:** Grouped bar charts of annual precipitation and GDD by grower.

**When to use:** Establish the east-west climate gradient that drives different farming systems.

### Task 3: Crop composition analysis

**What:** Stacked bar chart and corn-years histogram comparing crop mixes.

**When to use:** See how irrigation and climate shape crop choice.

### Task 4: Cross-data comparison

**What:** Precip vs GDD scatter plot and corn/soy ratio comparison.

**When to use:** Find correlations and tradeoffs between climate and crop management.

### Task 5: Geospatial context maps

**What:** Maps of field boundaries, weather centroids, and dominant crops.

**When to use:** Visualize the spatial patterns behind the statistics.

## Complete Example

See `scripts/run_eda.py` — the single orchestrator that reads grower data from the runtime tree and writes all 12 outputs.

## Best Practices

- Run the full pipeline (`setup-assignment-2.sh`) before running EDA
- Review output PNGs in order: boundaries → CDL → weather
- Use the CSVs for custom analysis beyond the standard plots
