#!/usr/bin/env python3
"""
generate_report.py — One-time HTML report from EDA outputs.

Usage:
    export DATA_PIPELINE_DATA_ROOT=/path/to/runtime
    python scripts/generate_report.py
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", ""))
if not DATA_ROOT.exists():
    print("ERROR: DATA_PIPELINE_DATA_ROOT is not set or does not exist")
    sys.exit(1)

OUTPUT_DIR = DATA_ROOT / "data-pipeline" / "eda" / "eda-assignment-2" / "output"
REPORT_PATH = OUTPUT_DIR / "eda_report.html"


def img_to_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def read_csv_summary(path: Path) -> str:
    lines = path.read_text().strip().split("\n")
    if not lines:
        return "<p>No data</p>"
    header = lines[0].split(",")
    rows = [line.split(",") for line in lines[1:]]
    html = '<table><thead><tr>' + ''.join(f'<th>{h}</th>' for h in header) + '</tr></thead><tbody>'
    for row in rows:
        html += '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>'
    html += '</tbody></table>'
    return html


def main():
    imgs = {
        "field_boundaries": [
            ("Area Histogram", "area_histogram.png",
             "Distribution of field areas across all three growers. IL and NE have larger, more variable fields; IA is more uniform."),
            ("Area Boxplot", "area_boxplot.png",
             "Boxplot comparing field area distributions. IL median ~800ac, IA median ~690ac, NE median ~770ac."),
            ("Boundary Map", "boundary_map.png",
             "All 30 field boundaries in Albers projection, colored by grower. Three distinct counties: DeKalb IL, Story IA, Phelps NE."),
        ],
        "weather": [
            ("Annual Precipitation", "annual_precip.png",
             "Annual precipitation by grower and year. NE receives ~300mm less rain than IL. 2022 drought visible in NE (392mm)."),
            ("Annual Growing Degree Days", "annual_gdd.png",
             "Annual GDD (base 10°C). NE has ~24% more heat than IL — the inverse of the precipitation gradient."),
            ("Precipitation vs GDD", "precip_gdd_correlation.png",
             "Scatter plot of precip vs GDD by grower-year. IL clusters wet/cool, NE clusters dry/hot. The fundamental climate tradeoff."),
            ("Weather Centroid Map", "weather_centroid_map.png",
             "Field centroids colored by grower. The spatial separation of the three counties matches their climate differences."),
        ],
        "cdl": [
            ("Crop Composition", "crop_composition_stacked.png",
             "Crop composition by grower (mean across 5 years). NE is corn-dominant, IA leans soy, IL is balanced."),
            ("Corn Years Histogram", "corn_years_histogram.png",
             "Number of years each field was in corn (out of 5). NE has more fields with 3-5 corn years (irrigation)."),
            ("Corn/Soy Ratio Trend", "corn_soy_ratio.png",
             "Combined corn+soy percentage of total CDL area over time. All three growers consistently >75% corn+soy."),
            ("Dominant Crop Map", "dominant_crop_map.png",
             "Fields colored by dominant 2025 CDL crop. Corn (yellow) vs soy (green) spatial distribution across the three counties."),
        ],
    }

    tables = {
        "Area Comparison": "area_comparison.csv",
        "Precip/GDD Correlation": "precip_gdd_correlation.csv",
        "Corn/Soy Ratio": "corn_soy_ratio.csv",
    }

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Assignment 2 — Field-Level EDA Report</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #fafafa; color: #333; }
h1 { color: #1a5276; border-bottom: 3px solid #1a5276; padding-bottom: 8px; }
h2 { color: #2e86c1; margin-top: 40px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { color: #555; margin-top: 30px; }
.section { margin-bottom: 40px; }
.plot-row { display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }
.plot-card { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 15px; flex: 1 1 420px; }
.plot-card img { width: 100%; height: auto; border-radius: 4px; }
.plot-card .caption { margin-top: 8px; font-size: 13px; color: #666; line-height: 1.5; }
.plot-card .title { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #2c3e50; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #2e86c1; color: white; }
tr:nth-child(even) { background: #f2f2f2; }
.meta { font-family: monospace; font-size: 12px; color: #888; margin-bottom: 30px; }
</style>
</head>
<body>
<h1>Assignment 2 — Field-Level Exploratory Data Analysis</h1>
<div class="meta">
<p><strong>Growers:</strong> IL: il-dekalb-grower (DeKalb) | IA: iowa-grower (Story) | NE: nebraska-grower (Phelps)</p>
<p><strong>Data:</strong> Real OSM field boundaries, NASA POWER weather (2021-2025), USDA CDL cropland (2021-2025)</p>
<p><strong>Generated:</strong> Static Python outputs from eda-assignment-2 subskill</p>
</div>
""")

    # Summary table
    html_parts.append("<h2>Summary</h2><div class='section'>")
    html_parts.append("<p>Three Corn Belt growers with 10 fields each. Field boundaries sourced from OpenStreetMap/Overpass. "
                      "Weather data from NASA POWER via Zarr grid. CDL crop type data from USDA NASS. "
                      "The east-west climate gradient (IL → IA → NE) drives differences in field scale, crop choice, and irrigation adoption.</p>")
    html_parts.append('<table><thead><tr><th>Grower</th><th>County</th><th>Fields</th><th>State FIPS</th><th>Avg Field (ac)</th><th>Total (ac)</th><th>Avg Precip (mm)</th><th>Avg GDD</th><th>Dominant 2025 Crop</th></tr></thead><tbody>')
    html_parts.append('<tr><td>IL</td><td>DeKalb</td><td>10</td><td>17</td><td>836</td><td>8,356</td><td>846</td><td>1,800</td><td>Corn</td></tr>')
    html_parts.append('<tr><td>IA</td><td>Story</td><td>10</td><td>19</td><td>693</td><td>6,934</td><td>813</td><td>2,139</td><td>Corn</td></tr>')
    html_parts.append('<tr><td>NE</td><td>Phelps</td><td>10</td><td>31</td><td>774</td><td>7,742</td><td>565</td><td>2,241</td><td>Corn</td></tr>')
    html_parts.append('</tbody></table></div>')

    # Data Sources
    html_parts.append("""
<h2>Data Sources</h2>
<div class='section'>
<table>
  <tr><th>Dataset</th><th>Source</th><th>Spatial Resolution</th><th>Temporal Coverage</th></tr>
  <tr><td>Field boundaries</td><td>OpenStreetMap / Overpass API</td><td>Individual field polygons</td><td>Static (current OSM snapshot)</td></tr>
  <tr><td>Weather</td><td>NASA POWER (Zarr grid)</td><td>~0.5&deg; (~50 km)</td><td>Daily, 2021–2025</td></tr>
  <tr><td>CDL cropland</td><td>USDA NASS Cropland Data Layer</td><td>30 m</td><td>Annual, 2021–2025</td></tr>
</table>
</div>

<h2>Analysis Levels</h2>
<div class='section'>
<p>This EDA compares data at three levels:</p>
<ul>
  <li><strong>Within a field:</strong> Weather variables (precipitation, GDD) across 5 years for individual fields. Visible in the annual bar charts and precip/GDD scatter.</li>
  <li><strong>Across fields within a grower:</strong> Field size distributions, corn year frequency, and crop diversity within each grower's 10 fields. Visible in the histogram, boxplot, and corn years chart.</li>
  <li><strong>Across growers:</strong> IL vs IA vs NE comparisons of climate, field scale, and crop composition. All grouped charts and the geospatial maps address this level.</li>
</ul>
<p><strong>Note:</strong> Soil analysis was not required for this assignment and was not included. The EDA focuses exclusively on field boundaries, weather, and CDL/cropland data layers.</p>
</div>
""")

    # Categories
    for section_id, section_title in [
        ("field_boundaries", "Field Boundaries"),
        ("weather", "Weather"),
        ("cdl", "CDL / Cropland Data"),
    ]:
        html_parts.append(f"<h2>{section_title}</h2><div class='section'>")
        items = imgs[section_id]
        for i in range(0, len(items), 2):
            html_parts.append("<div class='plot-row'>")
            for _, filename, caption in items[i:i+2]:
                path = OUTPUT_DIR / filename
                if path.exists():
                    b64 = img_to_b64(path)
                    html_parts.append(f"<div class='plot-card'>")
                    html_parts.append(f"<img src='data:image/png;base64,{b64}' alt='{filename}'>")
                    html_parts.append(f"<div class='caption'>{caption}</div>")
                    html_parts.append(f"</div>")
            html_parts.append("</div>")
        html_parts.append("</div>")

    # Tables
    html_parts.append("<h2>Comparison Tables</h2><div class='section'>")
    for title, filename in tables.items():
        path = OUTPUT_DIR / filename
        if path.exists():
            html_parts.append(f"<h3>{title}</h3>")
            html_parts.append(read_csv_summary(path))
    html_parts.append("</div>")

    html_parts.append("""
<h2>Key Findings</h2>
<div class='section'>
<ol>
  <li><strong>Scale varies by state:</strong> IL and NE fields average 770-840 ac; IA fields average 690 ac. The difference reflects farm structure and land ownership patterns.</li>
  <li><strong>Climate gradient drives strategy:</strong> NE receives 33% less rain than IL but has 24% more GDD. This inverse relationship creates the conditions that make irrigation profitable.</li>
  <li><strong>Irrigation enables continuous corn:</strong> NE has more fields with 3-5 years of corn (out of 5) because irrigation buffers drought risk. IA and IL rotate corn-soy more frequently.</li>
  <li><strong>2022 drought signal:</strong> Nebraska's 2022 precipitation (392mm) was 31% below its 5-year mean. No corresponding yield penalty appears in CDL — consistent with irrigation adoption.</li>
  <li><strong>Corn+soy dominance:</strong> All three growers devote 75-99% of CDL-classified area to corn and soybeans. The Corn Belt label is well-earned.</li>
</ol>
</div>

<h2>Limitations</h2>
<div class='section'>
<ol>
  <li><strong>Small sample:</strong> 10 fields per state from one county each. Results may not generalize to entire states or other counties within the same state.</li>
  <li><strong>Short time window:</strong> 5 years of weather and CDL data is insufficient for firm climate trend conclusions. Apparent patterns (e.g., NE drought year) should be interpreted as observations, not long-term shifts.</li>
  <li><strong>Modeled weather:</strong> NASA POWER is a global reanalysis grid (~0.5&deg; resolution). Local precipitation and temperature extremes may be smoothed compared to on-site station data.</li>
  <li><strong>Provisional 2025 CDL:</strong> The current-year Cropland Data Layer is preliminary and may be revised by USDA in subsequent releases.</li>
  <li><strong>OSM boundary quality:</strong> OpenStreetMap farmland polygons are crowd-sourced and may contain omissions, misclassifications, or aggregated field groupings.</li>
  <li><strong>Single county per state:</strong> One county cannot capture within-state diversity, such as northern versus southern Illinois climate or eastern versus western Nebraska rainfall gradients.</li>
  <li><strong>Soil excluded:</strong> Soil properties influence both crop choice and drought response but were excluded per the assignment scope.</li>
  <li><strong>Satellite imagery not included:</strong> Raw Sentinel-2 and Landsat scenes were not downloaded due to credential requirements, so NDVI-based vegetation health analysis was not possible.</li>
</ol>
</div>

<p><em>Report generated by eda-assignment-2 subskill. All outputs under
<code>DATA_PIPELINE_DATA_ROOT/data-pipeline/eda/eda-assignment-2/output/</code>.</em></p>
</body>
</html>""")

    REPORT_PATH.write_text("\n".join(html_parts))
    print(f"Report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
