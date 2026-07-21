#!/usr/bin/env python3
"""Action alert engine for soybean soil intelligence.

Detects specific agronomic problem patterns from soil data and generates
detailed, actionable recommendations for each field. Each alert has a
unique color (no overlap) for clear visual identification.

Alert types and their unique colors:
    Purple (#7C3AED)  — Nitrogen Leaching Risk
    Brown  (#92400E)  — Compaction Stress
    Amber  (#F59E0B)  — Acidity Lockup
    Sandy  (#D97706)  — Drought Susceptibility
    Cyan   (#0891B2)  — Waterlogging Risk
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def _safe_val(props: dict, key: str, default: float = 0.0) -> float:
    val = props.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_ps(props: dict, key: str, default: float = 0.0) -> float:
    ps = props.get("property_scores")
    if not isinstance(ps, dict):
        return default
    val = ps.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


_ALERT_DEFINITIONS = {
    "nitrogen_leaching": {
        "id": "nitrogen_leaching",
        "label": "Nitrogen Leaching Risk",
        "color": "#7C3AED",
        "color_name": "Deep Purple",
        "icon": "⬇",
        "trigger": lambda props: (
            _safe_val(props, "avg_sand", 0) > 65
            and _safe_val(props, "avg_om", 10) < 2.0
        ),
        "severity_rules": [
            (lambda p: _safe_val(p, "avg_sand", 0) > 75 and _safe_val(p, "avg_om", 10) < 1.5, "critical"),
            (lambda p: _safe_val(p, "avg_sand", 0) > 65 and _safe_val(p, "avg_om", 10) < 2.0, "warning"),
        ],
        "recommendation": """Sandy soil texture with low organic matter creates high nitrogen leaching potential in this zone. Nitrogen applied in soluble forms moves rapidly below the soybean root zone before uptake can occur.

**Detailed Recommendations:**
1. **Nitrogen Management:** Apply 15-20% additional nitrogen as a split application — 50% at planting, 50% at R1 (beginning bloom). This ensures N is available when demand peaks during pod fill (R3-R5).
2. **Stabilizer Use:** Incorporate a nitrification inhibitor (e.g., nitrapyrin/N-Serve at 0.5 lb a.i./acre) to slow conversion of ammonium to leachable nitrate. Apply with the pre-plant N portion.
3. **Organic Amendments:** Apply 2-3 tons/acre of composted manure or cover crop residue in the fall prior to soybeans. Target increasing OM by 0.5-1.0% over 3 years.
4. **Cover Crops:** Plant cereal rye at 40-60 lb/acre after corn harvest to scavenge residual N and build OM. Terminate 10-14 days before soybean planting.
5. **Tissue Testing:** Monitor leaf N at R3 (early pod). Tissue N below 4.0% indicates deficiency requiring supplemental N application.

**Expected Impact:** Reducing leaching could improve soybean yield by 3-7 bu/acre in the affected zone.
**Implementation Window:** Fall cover crop establishment + spring split application.""",
    },
    "compaction_stress": {
        "id": "compaction_stress",
        "label": "Compaction Stress",
        "color": "#92400E",
        "color_name": "Dark Brown",
        "icon": "🏋",
        "trigger": lambda props: (
            _safe_val(props, "avg_bulk_density", 1.2) > 1.55
            and _safe_val(props, "avg_clay", 0) > 30
        ),
        "severity_rules": [
            (lambda p: _safe_val(p, "avg_bulk_density", 1.2) > 1.65 and _safe_val(p, "avg_clay", 0) > 35, "critical"),
            (lambda p: _safe_val(p, "avg_bulk_density", 1.2) > 1.55 and _safe_val(p, "avg_clay", 0) > 30, "warning"),
        ],
        "recommendation": """Elevated bulk density combined with high clay content indicates subsoil compaction. Compacted layers restrict soybean taproot development and limit nodulation depth, reducing nitrogen fixation capacity.

**Detailed Recommendations:**
1. **Mechanical Remediation:** Execute deep tillage with ripper shanks set to 16-18" depth in the fall following soybean harvest, when soil moisture is below field capacity. Shatter the compacted layer and leave surface residue intact.
2. **Biological Remediation:** Plant deep-taproot cover crops such as tillage radish (8-10 lb/acre) or cereal rye (40-60 lb/acre) immediately after corn harvest. Radish taproots will penetrate 12-18" into compacted layers.
3. **Traffic Management:** Designate controlled traffic lanes and avoid field operations when soil moisture exceeds 70% of field capacity. A single pass at high moisture can re-compact loosened soil.
4. **Rotation Strategy:** Consider including a full-season cover crop fallow every 3-4 years in the affected zone to allow biological decompaction.
5. **Yield Impact:** Compacted zones typically show 15-25% yield reduction vs. uncompacted areas. Monitor with yield maps to verify response.

**Expected Impact:** Breaking compaction can increase effective rooting depth from 12" to 24"+, improving drought resilience and nitrogen fixation.
**Implementation Window:** Fall tillage + cover crop establishment.""",
    },
    "acidity_lockup": {
        "id": "acidity_lockup",
        "label": "Acidity Lockup",
        "color": "#F59E0B",
        "color_name": "Bright Amber",
        "icon": "⚠",
        "trigger": lambda props: _safe_val(props, "avg_ph", 7.0) < 6.3,
        "severity_rules": [
            (lambda p: _safe_val(p, "avg_ph", 7.0) < 5.8, "critical"),
            (lambda p: _safe_val(p, "avg_ph", 7.0) < 6.3, "warning"),
        ],
        "recommendation": """Soil pH is below the optimal range for soybean production. Rhizobium bacteria responsible for nitrogen fixation are pH-sensitive and their activity declines significantly below pH 6.3. Additionally, phosphorus and molybdenum availability are reduced in acidic conditions.

**Detailed Recommendations:**
1. **Liming Rate:** Apply 2.0-2.5 tons/acre of agricultural limestone (ENV 90%) based on buffer pH. Higher rates (up to 3.0 tons/acre) may be needed if pH is below 5.8. Use dolomitic lime if magnesium is also low.
2. **Application Timing:** Apply lime in the fall prior to the soybean rotation, ideally 6-12 months before planting. Incorporate to 6" depth for faster reaction. Surface-applied no-till lime takes 12-18 months to correct subsoil pH.
3. **Split Application:** If rates exceed 2.5 tons/acre, split into two applications 6 months apart to avoid over-liming the surface layer.
4. **Inoculation:** When pH is marginal (6.0-6.3), use a fresh peat-based Bradyrhizobium japonicum inoculant at 2x the standard rate. This ensures adequate nodulation even with reduced native rhizobia populations.
5. **Monitoring:** Retest soil pH at 0-6" and 6-12" depths after 12 months. Target pH 6.5 at both depths. Subsoil pH below 5.5 may require deep lime incorporation.

**Expected Impact:** Correcting pH to 6.5 can improve phosphorus availability by 30-40% and increase nitrogen fixation, yielding 3-5 bu/acre improvement.
**Implementation Window:** Fall lime application, spring retesting.""",
    },
    "drought_susceptibility": {
        "id": "drought_susceptibility",
        "label": "Drought Susceptibility",
        "color": "#D97706",
        "color_name": "Sandy Desert",
        "icon": "🏜",
        "trigger": lambda props: (
            _safe_val(props, "avg_sand", 0) > 60
            or _safe_ps(props, "awc_r", 100) < 35
        ),
        "severity_rules": [
            (lambda p: _safe_val(p, "avg_sand", 0) > 70 and _safe_ps(p, "awc_r", 100) < 25, "critical"),
            (lambda p: _safe_val(p, "avg_sand", 0) > 60 or _safe_ps(p, "awc_r", 100) < 35, "warning"),
        ],
        "recommendation": """Coarse soil texture with low available water capacity creates drought susceptibility, particularly during the critical R3-R5 (pod fill) stage when soybeans require 0.25-0.30 inches of water per day. Moisture stress during this window directly reduces pod retention and seed size.

**Detailed Recommendations:**
1. **Irrigation Scheduling:** If irrigation is available, schedule at 50% depletion in the upper 24" of soil profile. Use soil moisture sensors (Watermark or similar) at 6" and 18" depths to trigger irrigation. Apply 0.75-1.0 inch per event during R3-R5.
2. **Planting Population:** Increase seeding rate by 10-15% (to 140,000-160,000 seeds/acre) in the affected zone to compensate for lower individual plant productivity under moisture stress.
3. **Residue Management:** Maintain minimum 30% surface residue cover to reduce evaporation. Avoid fall tillage that incorporates all residue. Strip-till or no-till is preferred in this zone.
4. **Organic Matter Building:** Apply 3-4 tons/acre composted manure or plant a high-biomass cover crop (sorghum-sudangrass at 30-40 lb/acre) to increase water-holding capacity. Each 1% increase in OM adds 0.5-0.8" of plant-available water in the top 12".
5. **Drought-Tolerant Varieties:** Select soybean varieties rated for drought tolerance with a determinate growth habit and deep taproot characteristics. Consult local university variety trial data.

**Expected Impact:** Improved water management in drought-prone zones can stabilize yields at 85-90% of field average, reducing loss from the typical 25-40% reduction.
**Implementation Window:** Pre-season irrigation planning + spring variety selection.""",
    },
    "waterlogging_risk": {
        "id": "waterlogging_risk",
        "label": "Waterlogging Risk",
        "color": "#0891B2",
        "color_name": "Deep Cyan",
        "icon": "💧",
        "trigger": lambda props: (
            str(props.get("drainage_raw", "")).lower() in (
                "poorly drained", "very poorly drained", "somewhat poorly drained"
            )
            and _safe_val(props, "avg_clay", 0) > 35
        ),
        "severity_rules": [
            (lambda p: str(p.get("drainage_raw", "")).lower() in ("very poorly drained", "poorly drained") and _safe_val(p, "avg_clay", 0) > 40, "critical"),
            (lambda p: str(p.get("drainage_raw", "")).lower() in ("somewhat poorly drained", "poorly drained") and _safe_val(p, "avg_clay", 0) > 35, "warning"),
        ],
        "recommendation": """Poor drainage combined with high clay content creates waterlogged conditions that are detrimental to soybean root health. Saturated soils reduce oxygen availability to roots and rhizobia, limiting nitrogen fixation. Soybeans can tolerate only 24-48 hours of saturated conditions before significant damage occurs.

**Detailed Recommendations:**
1. **Tile Drainage Installation:** Install subsurface tile drainage at 50-60 foot spacing and 3.5-4.0 foot depth in the affected zone. This is the most effective and permanent solution for heavy clay soils. Calculate cost at approximately $800-1,200/acre with a 7-10 year ROI from yield improvement.
2. **Surface Drainage:** For fields where tile is not feasible, install shallow surface drains or grade to achieve minimum 0.5% slope to move surface water. Use berms or waterways to direct flow.
3. **Raised Bed System:** Convert to 30" raised beds (6-8" height) for the affected zones. This elevates the soybean root zone above the saturated layer and improves aeration.
4. **Crop Rotation Adjustment:** If drainage cannot be improved, consider transitioning the affected zone to a more water-tolerant crop such as winter wheat which can tolerate wet conditions during early growth stages.
5. **Planting Date:** Delay planting in poorly-drained zones by 7-10 days relative to well-drained areas to allow for drier soil conditions.
6. **Yield Impact:** Waterlogged zones typically produce only 40-60% of the field average yield. Each day of saturation above 48 hours causes approximately 1-2% yield loss.

**Expected Impact:** Effective drainage can recover 60-80% of the yield gap in affected zones.
**Implementation Window:** Tile installation in dry soil conditions (fall preferred); raised bed preparation in fall/spring.""",
    },
}


def evaluate_field(field_score: dict) -> list[dict[str, Any]]:
    """Evaluate a scored field for active action alerts.

    Args:
        field_score: Dictionary from soil_scoring.score_field_soil()

    Returns:
        List of alert dictionaries, each with: id, label, color, icon,
        severity (critical/warning/none), triggered (bool), and recommendation.
    """
    alerts: list[dict[str, Any]] = []

    for alert_def in _ALERT_DEFINITIONS.values():
        props = {
            "avg_om": field_score.get("avg_om"),
            "avg_ph": field_score.get("avg_ph"),
            "avg_clay": field_score.get("avg_clay"),
            "avg_sand": field_score.get("avg_sand"),
            "avg_bulk_density": field_score.get("avg_bulk_density"),
            "drainage_raw": field_score.get("drainage_raw"),
            "property_scores": field_score.get("property_scores", {}),
        }

        triggered = alert_def["trigger"](props)
        severity = "none"
        if triggered:
            for rule, sev in alert_def["severity_rules"]:
                if rule(props):
                    severity = sev
                    break

        alerts.append({
            "id": alert_def["id"],
            "label": alert_def["label"],
            "color": alert_def["color"],
            "color_name": alert_def["color_name"],
            "icon": alert_def["icon"],
            "severity": severity,
            "triggered": triggered,
            "recommendation": alert_def["recommendation"] if triggered else "",
        })

    return alerts


def generate_action_summary(field_scores: list[dict]) -> dict[str, Any]:
    """Generate a grower-level action summary across all fields.

    Returns a dictionary with total alert counts by type and severity,
    a prioritized action list, and field-level alert details.
    """
    summary: dict[str, Any] = {
        "total_fields": len(field_scores),
        "field_alerts": [],
        "alert_counts": {},
        "prioritized_actions": [],
    }

    alert_totals: dict[str, dict[str, int]] = {}

    for fs in field_scores:
        field_alerts = evaluate_field(fs)
        triggered = [a for a in field_alerts if a["triggered"]]
        summary["field_alerts"].append({
            "field_id": fs["field_id"],
            "overall_score": fs["overall_score"],
            "status": fs["status"],
            "alerts": triggered,
            "alert_count": len(triggered),
        })

        for alert in triggered:
            if alert["id"] not in alert_totals:
                alert_totals[alert["id"]] = {"critical": 0, "warning": 0, "label": alert["label"]}
            alert_totals[alert["id"]][alert["severity"]] += 1

    summary["alert_counts"] = alert_totals

    prioritized = []
    for fid_info in summary["field_alerts"]:
        for alert in fid_info["alerts"]:
            if alert["severity"] == "critical":
                prioritized.append({
                    "priority": 1,
                    "field_id": fid_info["field_id"],
                    "alert_id": alert["id"],
                    "alert_label": alert["label"],
                    "recommendation_summary": alert["recommendation"].split("\n\n")[0][:200] + "...",
                })

    for fid_info in summary["field_alerts"]:
        for alert in fid_info["alerts"]:
            if alert["severity"] == "warning":
                prioritized.append({
                    "priority": 2,
                    "field_id": fid_info["field_id"],
                    "alert_id": alert["id"],
                    "alert_label": alert["label"],
                    "recommendation_summary": alert["recommendation"].split("\n\n")[0][:200] + "...",
                })

    prioritized.sort(key=lambda x: (x["priority"], x["field_id"]))
    summary["prioritized_actions"] = prioritized[:10]

    return summary


def get_alert_color_map() -> dict[str, dict[str, str]]:
    """Return the alert color map for dashboard rendering."""
    return {
        a["id"]: {"color": a["color"], "color_name": a["color_name"], "label": a["label"], "icon": a["icon"]}
        for a in _ALERT_DEFINITIONS.values()
    }
