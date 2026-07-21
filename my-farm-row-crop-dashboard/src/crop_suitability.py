#!/usr/bin/env python3
"""Crop suitability comparison engine.

Evaluates each field's soil profile against optimal requirements for
Soybeans, Corn, and Winter Wheat, then recommends the best crop based
on how well the soil profile matches each crop's needs.

Comparison Dimensions:
    - pH requirement
    - Organic matter tolerance
    - Drainage preference
    - Water availability requirement
    - Bulk density sensitivity
"""
from __future__ import annotations

from typing import Any
import pandas as pd


_CROP_REQUIREMENTS = {
    "Soybeans": {
        "ph": {"opt_min": 6.3, "opt_max": 7.0, "weight": 0.30},
        "om": {"opt_min": 2.5, "opt_max": 6.0, "weight": 0.25},
        "drainage": {"preferred": ["Well drained", "Moderately well drained"],
                     "tolerated": ["Somewhat poorly drained"], "weight": 0.15},
        "awc": {"opt_min": 0.12, "opt_max": 0.25, "weight": 0.20},
        "bulk_density": {"opt_max": 1.55, "weight": 0.10},
    },
    "Corn": {
        "ph": {"opt_min": 6.0, "opt_max": 6.8, "weight": 0.20},
        "om": {"opt_min": 2.5, "opt_max": 6.0, "weight": 0.25},
        "drainage": {"preferred": ["Well drained", "Moderately well drained"],
                     "tolerated": [], "weight": 0.20},
        "awc": {"opt_min": 0.15, "opt_max": 0.25, "weight": 0.25},
        "bulk_density": {"opt_max": 1.60, "weight": 0.10},
    },
    "Winter Wheat": {
        "ph": {"opt_min": 6.0, "opt_max": 7.0, "weight": 0.15},
        "om": {"opt_min": 1.5, "opt_max": 5.0, "weight": 0.15},
        "drainage": {"preferred": ["Well drained", "Moderately well drained", "Somewhat poorly drained"],
                     "tolerated": ["Poorly drained"], "weight": 0.25},
        "awc": {"opt_min": 0.08, "opt_max": 0.20, "weight": 0.20},
        "bulk_density": {"opt_max": 1.65, "weight": 0.25},
    },
}


def _ph_score(ph: float | None, req: dict) -> float:
    if ph is None:
        return 50.0
    if req["opt_min"] <= ph <= req["opt_max"]:
        return 100.0
    if ph < req["opt_min"]:
        return max(0, ((ph - (req["opt_min"] - 1.5)) / 1.5) * 100.0)
    return max(0, (((req["opt_max"] + 1.5) - ph) / 1.5) * 100.0)


def _om_score(om: float | None, req: dict) -> float:
    if om is None:
        return 50.0
    if om >= req["opt_min"]:
        return 100.0
    return max(0, (om / req["opt_min"]) * 100.0)


def _drainage_score(drainage: str | None, req: dict) -> float:
    if drainage is None:
        return 50.0
    d = str(drainage)
    if d in req["preferred"]:
        return 100.0
    if d in req.get("tolerated", []):
        return 60.0
    return 20.0


def _awc_score(awc: float | None, req: dict) -> float:
    if awc is None:
        return 50.0
    if awc >= req["opt_min"]:
        return min(100.0, 50.0 + (awc / req["opt_min"]) * 50.0)
    return max(0, (awc / req["opt_min"]) * 100.0)


def _bd_score(bd: float | None, req: dict) -> float:
    if bd is None:
        return 50.0
    if bd <= req["opt_max"]:
        return 100.0
    return max(0, ((1.80 - bd) / (1.80 - req["opt_max"])) * 100.0)


def evaluate_crop_suitability(field_score: dict) -> dict[str, Any]:
    """Evaluate how well a field's soil supports each crop.

    Args:
        field_score: Dictionary from soil_scoring.score_field_soil()

    Returns:
        Dictionary with per-crop scores, best crop recommendation,
        and reasoning.
    """
    ph = field_score.get("avg_ph")
    om = field_score.get("avg_om")
    drainage = field_score.get("drainage_raw")
    awc = _safe_awc(field_score)
    bd = field_score.get("avg_bulk_density")

    crop_scores: dict[str, float] = {}
    crop_details: dict[str, dict] = {}

    for crop, req in _CROP_REQUIREMENTS.items():
        scores = {
            "ph": _ph_score(ph, req["ph"]),
            "om": _om_score(om, req["om"]),
            "drainage": _drainage_score(drainage, req["drainage"]),
            "awc": _awc_score(awc, req["awc"]),
            "bulk_density": _bd_score(bd, req["bulk_density"]),
        }

        weighted = sum(
            scores[key] * req[key]["weight"]
            for key in req
        )
        crop_scores[crop] = round(weighted, 1)
        crop_details[crop] = {
            "overall_score": round(weighted, 1),
            "dimension_scores": {k: round(v, 1) for k, v in scores.items()},
        }

    best_crop = max(crop_scores, key=crop_scores.get)
    best_score = crop_scores[best_crop]
    runner_up = sorted(crop_scores.items(), key=lambda x: -x[1])[1]

    reasons: list[str] = []
    if best_crop == "Soybeans":
        if ph is not None and 6.3 <= ph <= 7.0:
            reasons.append(f"pH ({ph:.1f}) in optimal soybean range for nitrogen fixation.")
        if drainage is not None and str(drainage) in ["Well drained", "Moderately well drained"]:
            reasons.append(f"{drainage} conditions support healthy nodulation.")
    elif best_crop == "Corn":
        if ph is not None and 6.0 <= ph < 6.3:
            reasons.append(f"pH ({ph:.1f}) favors corn over soybeans.")
        if awc is not None and awc >= 0.15:
            reasons.append(f"High water availability ({awc:.3f}) supports corn yield potential.")
    elif best_crop == "Winter Wheat":
        if drainage is not None and "poorly" in str(drainage).lower():
            reasons.append(f"Poor drainage tolerated better by wheat.")
        if om is not None and om < 2.0:
            reasons.append(f"Lower organic matter sufficient for wheat.")

    return {
        "field_id": field_score["field_id"],
        "crop_scores": crop_scores,
        "crop_details": crop_details,
        "best_crop": best_crop,
        "best_score": best_score,
        "runner_up": runner_up[0],
        "runner_up_score": runner_up[1],
        "margin": round(best_score - runner_up[1], 1),
        "reasons": reasons,
        "decision": (
            f"Based on soil characteristics (pH {ph:.1f}, OM {om:.1f}%, "
            f"{drainage}), {best_crop} is the recommended crop for this field."
            if ph is not None and om is not None and drainage is not None
            else f"Based on available soil data, {best_crop} is the recommended crop."
        ),
    }


def _safe_awc(field_score: dict) -> float | None:
    depth_profile = field_score.get("depth_profile", [])
    if not depth_profile:
        return None
    awc_vals = []
    for zone in depth_profile:
        val = zone.get("awc_r")
        if val is not None:
            awc_vals.append(float(val))
    return sum(awc_vals) / len(awc_vals) if awc_vals else None
