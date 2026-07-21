#!/usr/bin/env python3
"""Soybean-specific soil health scoring engine.

Computes a composite Soil Health Score (0-100) for soybean production
using depth-weighted SSURGO soil properties across the full root zone
(0-60 cm).

The score adapts weights and optimal thresholds specifically for
soybeans (Glycine max), accounting for:
- Rhizobium nitrogen fixation sensitivity to pH
- Root nodulation depth requirements
- Pod-fill moisture sensitivity
- Higher pH optimal range vs. corn

Score Interpretation:
    >80: Excellent — optimal for soybeans
    60-80: Healthy — minor adjustments recommended
    40-60: Monitor — address specific limitations
    <40: High Priority — significant intervention needed
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MATURE_ROOT_ZONE_CM = 60

_DEPTH_ZONES = [
    {"name": "topsoil", "top_cm": 0, "bottom_cm": 15, "weight": 0.40},
    {"name": "upper_root", "top_cm": 15, "bottom_cm": 30, "weight": 0.35},
    {"name": "lower_root", "top_cm": 30, "bottom_cm": 60, "weight": 0.25},
]

_SOYBEAN_SCORING = {
    "om_r": {
        "weight": 0.30,
        "label": "Organic Matter",
        "unit": "%",
        "optimal_min": 3.0,
        "optimal_max": 6.0,
        "critical_low": 1.5,
        "direction": "higher_better",
    },
    "ph1to1h2o_r": {
        "weight": 0.25,
        "label": "pH Balance",
        "unit": "pH",
        "optimal_min": 6.3,
        "optimal_max": 7.0,
        "critical_low": 5.5,
        "critical_high": 7.5,
        "direction": "near_optimal",
    },
    "awc_r": {
        "weight": 0.20,
        "label": "Available Water Capacity",
        "unit": "cm/cm",
        "optimal_min": 0.15,
        "optimal_max": 0.25,
        "critical_low": 0.10,
        "direction": "higher_better",
    },
    "dbthirdbar_r": {
        "weight": 0.15,
        "label": "Bulk Density",
        "unit": "g/cm³",
        "optimal_min": 1.10,
        "optimal_max": 1.45,
        "critical_high": 1.60,
        "direction": "lower_better",
    },
    "drainage_score": {
        "weight": 0.10,
        "label": "Drainage Suitability",
        "unit": "score",
        "optimal_min": 60,
        "optimal_max": 100,
        "critical_low": 30,
        "direction": "higher_better",
    },
}

_DRAINAGE_CLASS_SCORES = {
    "Excessively drained": 40,
    "Somewhat excessively drained": 55,
    "Well drained": 100,
    "Moderately well drained": 80,
    "Somewhat poorly drained": 45,
    "Poorly drained": 20,
    "Very poorly drained": 10,
    "unknown": 40,
    None: 40,
}


def _score_higher_better(value: float, optimal_min: float, critical_low: float) -> float:
    if value >= optimal_min:
        return 100.0
    if value <= critical_low:
        return 0.0
    return ((value - critical_low) / (optimal_min - critical_low)) * 100.0


def _score_lower_better(value: float, optimal_max: float, critical_high: float) -> float:
    if value <= optimal_max:
        return 100.0
    if value >= critical_high:
        return 0.0
    return ((critical_high - value) / (critical_high - optimal_max)) * 100.0


def _score_near_optimal(value: float, opt_min: float, opt_max: float,
                        crit_low: float, crit_high: float) -> float:
    if opt_min <= value <= opt_max:
        return 100.0
    if value < opt_min:
        if value <= crit_low:
            return 0.0
        return ((value - crit_low) / (opt_min - crit_low)) * 100.0
    if value >= crit_high:
        return 0.0
    return ((crit_high - value) / (crit_high - opt_max)) * 100.0


def _depth_zone_weights(sub_df: pd.DataFrame, top: float, bottom: float) -> float:
    if sub_df.empty:
        return 0.0
    contrib = 0.0
    for _, row in sub_df.iterrows():
        hz_top = float(row.get("hzdept_r", 0))
        hz_bot = float(row.get("hzdepb_r", 0))
        overlap = max(0.0, min(bottom, hz_bot) - max(top, hz_top))
        if overlap > 0:
            comppct = float(row.get("comppct_r", 100))
            contrib += overlap * comppct
    return contrib


def _score_property(sub_df: pd.DataFrame, prop: str, config: dict) -> float:
    if sub_df.empty or prop not in sub_df.columns:
        return 0.0

    valid = sub_df[sub_df[prop].notna()].copy()
    if valid.empty:
        return 0.0

    total_wt = valid["comppct_r"].astype(float).sum() if "comppct_r" in valid.columns else len(valid)
    if total_wt == 0:
        return 0.0

    weighted_val = (valid[prop].astype(float) * valid["comppct_r"].astype(float)).sum() / total_wt

    direction = config["direction"]
    if direction == "higher_better":
        return _score_higher_better(weighted_val, config["optimal_min"], config["critical_low"])
    elif direction == "lower_better":
        return _score_lower_better(weighted_val, config["optimal_max"], config["critical_high"])
    elif direction == "near_optimal":
        return _score_near_optimal(
            weighted_val, config["optimal_min"], config["optimal_max"],
            config["critical_low"], config["critical_high"]
        )
    return 50.0


def score_field_soil(soil_df: pd.DataFrame, field_id: str) -> dict:
    """Compute the soybean-specific soil health score for one field.

    Args:
        soil_df: Full SSURGO DataFrame with columns: field_id, hzdept_r,
                 hzdepb_r, comppct_r, om_r, ph1to1h2o_r, awc_r,
                 dbthirdbar_r, drainagecl, claytotal_r, sandtotal_r, silttotal_r.
        field_id: Field identifier to score.

    Returns:
        Dictionary with overall_score, property_scores, depth_breakdown,
        soil_taxonomy summary, and per-zone property values.
    """
    field_data = soil_df[soil_df["field_id"].astype(str) == str(field_id)].copy()
    if field_data.empty:
        return {
            "field_id": field_id,
            "overall_score": 50,
            "status": "insufficient_data",
            "property_scores": {},
            "depth_profile": [],
            "dominant_soil": "Unknown",
            "dominant_drainage": "Unknown",
        }

    for col in ["hzdept_r", "hzdepb_r", "comppct_r"]:
        if col in field_data.columns:
            field_data[col] = pd.to_numeric(field_data[col], errors="coerce")
    for col in ["om_r", "ph1to1h2o_r", "awc_r", "dbthirdbar_r"]:
        if col in field_data.columns:
            field_data[col] = pd.to_numeric(field_data[col], errors="coerce")

    dominant = field_data.loc[field_data["comppct_r"].idxmax()] if not field_data.empty else None
    dominant_soil = str(dominant.get("compname", "Unknown")) if dominant is not None else "Unknown"
    dominant_drainage = str(dominant.get("drainagecl", "Unknown")) if dominant is not None else "Unknown"
    dominant_muname = str(dominant.get("muname", "")) if dominant is not None else ""

    drainage_raw = str(dominant.get("drainagecl", "Unknown")) if dominant is not None else "Unknown"
    drainage_score = _DRAINAGE_CLASS_SCORES.get(drainage_raw, 40)

    property_scores: dict[str, float] = {}
    depth_profile: list[dict] = []

    for dz in _DEPTH_ZONES:
        zone_mask = (
            (field_data["hzdept_r"] < dz["bottom_cm"])
            & (field_data["hzdepb_r"] > dz["top_cm"])
        )
        zone_data = field_data[zone_mask]

        zone_props: dict[str, Any] = {
            "zone": dz["name"],
            "depth_cm": f"{dz['top_cm']}-{dz['bottom_cm']}",
            "weight": dz["weight"],
        }

        for prop, config in _SOYBEAN_SCORING.items():
            if prop == "drainage_score":
                raw_val = drainage_score
            elif prop in zone_data.columns:
                valid = zone_data[zone_data[prop].notna()]
                if not valid.empty:
                    raw_val = (valid[prop].astype(float) * valid["comppct_r"].astype(float)).sum() / valid["comppct_r"].astype(float).sum()
                else:
                    raw_val = None
            else:
                raw_val = None

            zone_props[prop] = raw_val

        depth_profile.append(zone_props)

    for prop, config in _SOYBEAN_SCORING.items():
        if prop == "drainage_score":
            score = drainage_score
        else:
            zone_scores = []
            zone_weights_sum = 0.0
            for dz in _DEPTH_ZONES:
                zone_mask = (
                    (field_data["hzdept_r"] < dz["bottom_cm"])
                    & (field_data["hzdepb_r"] > dz["top_cm"])
                )
                zone_data = field_data[zone_mask]
                if not zone_data.empty and prop in zone_data.columns:
                    s = _score_property(zone_data, prop, config)
                    zone_scores.append(s * dz["weight"])
                    zone_weights_sum += dz["weight"]
            score = sum(zone_scores) / zone_weights_sum if zone_weights_sum > 0 else 50.0

        property_scores[prop] = round(score, 1)

    overall = sum(
        property_scores.get(prop, 50) * config["weight"]
        for prop, config in _SOYBEAN_SCORING.items()
    )
    overall = round(overall, 1)

    if overall > 80:
        status = "excellent"
    elif overall > 60:
        status = "healthy"
    elif overall > 40:
        status = "monitor"
    else:
        status = "high_priority"

    avg_om = _safe_avg(field_data, "om_r")
    avg_ph = _safe_avg(field_data, "ph1to1h2o_r")
    avg_clay = _safe_avg(field_data, "claytotal_r")
    avg_sand = _safe_avg(field_data, "sandtotal_r")
    avg_bd = _safe_avg(field_data, "dbthirdbar_r")

    return {
        "field_id": field_id,
        "overall_score": overall,
        "status": status,
        "property_scores": property_scores,
        "depth_profile": depth_profile,
        "dominant_soil": dominant_soil,
        "dominant_muname": dominant_muname,
        "dominant_drainage": dominant_drainage,
        "drainage_raw": drainage_raw,
        "avg_om": round(avg_om, 2) if avg_om else None,
        "avg_ph": round(avg_ph, 2) if avg_ph else None,
        "avg_clay": round(avg_clay, 1) if avg_clay else None,
        "avg_sand": round(avg_sand, 1) if avg_sand else None,
        "avg_bulk_density": round(avg_bd, 2) if avg_bd else None,
    }


def score_all_fields(soil_df: pd.DataFrame) -> pd.DataFrame:
    """Score all fields in a soil DataFrame."""
    field_ids = soil_df["field_id"].astype(str).unique()
    results = []
    for fid in field_ids:
        result = score_field_soil(soil_df, fid)
        results.append(result)
    return pd.DataFrame(results)


def _safe_avg(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns:
        return None
    valid = df[col].dropna()
    if valid.empty:
        return None
    if "comppct_r" in df.columns:
        valid_idx = valid.index
        weights = df.loc[valid_idx, "comppct_r"].astype(float)
        return float((valid.astype(float) * weights).sum() / weights.sum())
    return float(valid.mean())
