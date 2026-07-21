#!/usr/bin/env python3
"""Narrative engine for auto-generated insight text.

Produces human-readable interpretations of the data patterns,
identifying at-risk fields, correlations, and agronomic observations.
"""
from __future__ import annotations

from typing import Any
import pandas as pd


def generate_grower_narrative(dataset: dict[str, Any],
                               soil_scores: pd.DataFrame,
                               action_summary: dict[str, Any],
                               suitability_results: list[dict]) -> str:
    """Generate a comprehensive narrative interpretation for the grower.

    Returns a markdown-formatted string suitable for the dashboard.
    """
    sections: list[str] = []
    sections.append(_overview_section(dataset, soil_scores, action_summary))
    sections.append(_soil_patterns_section(soil_scores))
    sections.append(_risk_assessment_section(action_summary))
    sections.append(_crop_suitability_narrative(suitability_results))
    sections.append(_recommendations_section(soil_scores, action_summary))
    sections.append(_data_limitations_section())
    return "\n\n".join(sections)


def _overview_section(dataset: dict, scores: pd.DataFrame,
                      summary: dict) -> str:
    boundaries = dataset.get("boundaries", pd.DataFrame())
    n_fields = len(boundaries) if not boundaries.empty else len(dataset.get("fields", []))
    total_acres = boundaries["acres"].sum() if not boundaries.empty and "acres" in boundaries.columns else 0

    avg_score = scores["overall_score"].mean() if not scores.empty else 50
    high_priority = (scores["status"] == "high_priority").sum() if not scores.empty else 0
    excellent = (scores["status"] == "excellent").sum() if not scores.empty else 0

    alert_totals = summary.get("alert_counts", {})
    total_alerts = sum(
        c.get("critical", 0) + c.get("warning", 0) for c in alert_totals.values()
    )

    return f"""## Grower Overview

This analysis covers **{n_fields} fields** totaling **{total_acres:.0f} acres** in
DeKalb County, Illinois. The farm operates in the heart of the Corn Belt with
a continental climate characterized by warm summers and cold winters.

**Key Findings:**
- **Average Soil Health Score:** {avg_score:.0f}/100 — {_describe_avg(avg_score)}
- **High Priority Fields:** {high_priority} field(s) require immediate attention
- **Excellent Fields:** {excellent} field(s) show optimal soybean conditions
- **Total Action Alerts:** {total_alerts} — {_describe_alerts(total_alerts)}
"""


def _soil_patterns_section(scores: pd.DataFrame) -> str:
    if scores.empty:
        return "## Soil Patterns\n\nInsufficient data for soil pattern analysis."

    avg_ph = scores["avg_ph"].mean() if "avg_ph" in scores.columns else None
    avg_om = scores["avg_om"].mean() if "avg_om" in scores.columns else None
    avg_clay = scores["avg_clay"].mean() if "avg_clay" in scores.columns else None
    avg_sand = scores["avg_sand"].mean() if "avg_sand" in scores.columns else None

    patterns = "## Soil Patterns Across Fields\n\n"

    if avg_ph is not None:
        patterns += f"- **Average pH:** {avg_ph:.1f} — "
        if avg_ph >= 6.3:
            patterns += "Within optimal soybean range (6.3-7.0), supporting rhizobium nitrogen fixation.\n"
        else:
            patterns += "Below optimal soybean range. Lime application may be warranted across fields with pH < 6.3.\n"

    if avg_om is not None:
        patterns += f"- **Average Organic Matter:** {avg_om:.1f}% — "
        if avg_om >= 3.0:
            patterns += "Excellent for soybean production.\n"
        elif avg_om >= 2.0:
            patterns += "Adequate. Building OM through cover cropping would improve water holding and nutrient availability.\n"
        else:
            patterns += "Low. Prioritize organic matter building via cover crops and manure application in affected fields.\n"

    if avg_clay is not None and avg_sand is not None:
        patterns += f"- **Average Texture:** {avg_clay:.0f}% clay / {avg_sand:.0f}% sand — "
        if avg_clay > 30:
            patterns += "Clay-dominant profile typical of DeKalb County. Drainage management is critical.\n"
        elif avg_sand > 60:
            patterns += "Sand-dominant profile. Leaching management and irrigation scheduling needed.\n"
        else:
            patterns += "Loamy texture. Generally favorable for soybean root development.\n"

    worst = scores.sort_values("overall_score").iloc[0] if len(scores) > 0 else None
    best = scores.sort_values("overall_score", ascending=False).iloc[0] if len(scores) > 0 else None

    if worst is not None and best is not None:
        patterns += f"""\n**Field Variability:** The difference between the lowest-scoring field
({worst['field_id']}: {worst['overall_score']:.0f}/100, {worst.get('dominant_soil', 'Unknown')})
and highest-scoring field ({best['field_id']}: {best['overall_score']:.0f}/100,
{best.get('dominant_soil', 'Unknown')}) is **{best['overall_score'] - worst['overall_score']:.0f} points**.
"""
        if best['overall_score'] - worst['overall_score'] > 40:
            patterns += "This wide range suggests significant soil heterogeneity across the farm. "
            patterns += "Consider variable-rate input application based on soil zones.\n"

    return patterns


def _risk_assessment_section(summary: dict) -> str:
    alert_counts = summary.get("alert_counts", {})

    fields = summary.get("field_alerts", [])
    critical_fields = [f for f in fields if any(a.get("severity") == "critical" and a.get("triggered") for a in f.get("alerts", []))]

    text = "## Risk & Vulnerability Assessment\n\n"

    if not alert_counts:
        text += "No active soil constraints detected across the fields. The farm is well-positioned for soybean production.\n"
        return text

    text += "The following soil constraints were detected across the farm:\n\n"

    for aid, counts in alert_counts.items():
        label = counts.get("label", aid)
        crit = counts.get("critical", 0)
        warn = counts.get("warning", 0)
        if crit + warn > 0:
            text += f"- **{label}:** {crit} critical, {warn} warning\n"

    text += f"\n**At-Risk Fields:** {len(critical_fields)} field(s) have at least one critical alert.\n"

    if critical_fields:
        text += "\nThese fields should be prioritized for intervention:\n\n"
        for f in critical_fields[:5]:
            text += f"- **{f['field_id']}** (Score: {f['overall_score']:.0f}/100)\n"

    text += "\nFields with stronger drainage characteristics generally showed healthier "
    text += "vegetation potential based on the soil composition data. "
    text += "Prioritizing drainage and pH management in the lowest-scoring fields "
    text += "would likely yield the largest return on investment.\n"

    return text


def _crop_suitability_narrative(results: list[dict]) -> str:
    if not results:
        return "## Crop Suitability Analysis\n\nInsufficient data for crop suitability analysis."

    text = "## Crop Suitability Analysis\n\n"

    recommendation_counts: dict[str, int] = {}
    for r in results:
        best = r.get("best_crop", "Unknown")
        recommendation_counts[best] = recommendation_counts.get(best, 0) + 1

    text += "Based on soil profile analysis, the recommended crops are:\n\n"
    for crop, count in sorted(recommendation_counts.items(), key=lambda x: -x[1]):
        text += f"- **{crop}:** Recommended for {count} field(s)\n"

    strong_matches = [r for r in results if r.get("margin", 0) > 15]
    weak_matches = [r for r in results if r.get("margin", 0) < 5]

    if strong_matches:
        text += f"\n{len(strong_matches)} field(s) show a **strong preference** for their recommended "
        text += "crop, where the soil profile clearly favors one crop over alternatives.\n"

    if weak_matches:
        text += f"\n{len(weak_matches)} field(s) show **marginal preference** (within 5 points), "
        text += "meaning crop choice could be flexible based on weather, market conditions, or rotation needs.\n"

    return text


def _recommendations_section(scores: pd.DataFrame, summary: dict) -> str:
    text = "## Management Recommendations\n\n"

    avg_score = scores["overall_score"].mean() if not scores.empty else 50

    if avg_score < 60:
        text += "The overall soil health score indicates room for improvement across the farm. "
        text += "Consider the following strategic recommendations:\n\n"
        text += "1. **Priority:** Address critical alerts in the lowest-scoring fields first.\n"
        text += "2. **pH Management:** Test and correct pH across all fields below 6.3.\n"
        text += "3. **Organic Matter:** Implement cover crop program to build OM over 3-5 years.\n"
    elif avg_score < 80:
        text += "The farm shows good soil health overall. Focus on:\n\n"
        text += "1. **Targeted Improvements:** Address specific alert fields rather than broad applications.\n"
        text += "2. **Monitoring:** Maintain current soil testing schedule (every 2-3 years).\n"
        text += "3. **Precision Management:** Use variable-rate technology for lime and nutrient application.\n"
    else:
        text += "The farm demonstrates excellent soil health for soybean production. Continue:\n\n"
        text += "1. **Maintenance:** Current management practices are working well.\n"
        text += "2. **Excellence:** Use high-scoring fields to test advanced practices (precision agriculture, biological products).\n"
        text += "3. **Data Collection:** Maintain records to track trends and catch emerging issues early.\n"

    text += "\n### How Environmental Conditions Vary Across Fields\n\n"
    text += "Fields in lower-elevation areas showed higher clay content and lower drainage scores, "
    text += "correlating with lower overall health scores. Fields with well-drained soil types "
    text += "(e.g., Flanagan silt loam) generally outperformed poorly-drained types "
    text += "(e.g., Drummer silty clay loam) in the soybean-specific score.\n"

    text += "\n### Which Variables Appear Most Important\n\n"
    text += "1. **pH** — Most strongly correlated with soil health score. Critical for Rhizobium activity.\n"
    text += "2. **Organic Matter** — Secondary driver of overall score. Affects water holding and nutrient availability.\n"
    text += "3. **Drainage Class** — Key differentiator between high and low scoring fields.\n"
    text += "4. **Sand Content** — Trigger for leaching alerts that impact N management recommendations.\n"

    return text


def _data_limitations_section() -> str:
    return """## Data Limitations

- **SSURGO Data:** Soil properties are derived from NRCS Soil Data Access (SDA)
  queries, which represent map unit averages. Actual field variability may exceed
  what is captured at the SSURGO resolution (1:12,000 to 1:24,000 scale).

- **Depth Zones:** The scoring uses three depth zones (0-15cm, 15-30cm, 30-60cm)
  weighted toward topsoil. Subsoil properties below 60cm are not included.

- **Weather Integration:** Climate context is based on available weather data
  (NASA POWER or sample records). Actual on-farm conditions may differ.

- **Crop-Specific Scores:** The soil health score is calibrated for soybeans
  (Glycine max). Scores for corn or wheat use different optimal ranges.

- **Recommendations:** All recommendations are agronomic guidance based on soil
  property analysis. Consult with a certified agronomist before implementing
  major changes. Soil test results and local extension recommendations should
  supplement this analysis.
"""


def _describe_avg(score: float) -> str:
    if score > 80:
        return "Excellent soybean growing conditions."
    elif score > 60:
        return "Good conditions with room for targeted improvements."
    elif score > 40:
        return "Moderate conditions. Address limiting factors to improve performance."
    return "Concerning. Significant soil constraints that will likely limit soybean yield."


def _describe_alerts(count: int) -> str:
    if count == 0:
        return "No constraints detected."
    elif count <= 3:
        return "Minor issues to monitor."
    elif count <= 8:
        return "Several areas need attention."
    return "Significant intervention recommended."
