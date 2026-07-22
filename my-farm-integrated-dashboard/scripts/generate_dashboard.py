#!/usr/bin/env python3
"""Generate the Corn Soil Dashboard — a self-contained Observable Plot HTML page.

Usage:
  python3 scripts/generate_dashboard.py [--output output/corn_soil_dashboard.html]

Produces a single downloadable HTML file that works offline in any modern browser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── Config ──────────────────────────────────────────────────────────────────
GROWER = "il-dekalb-grower"
COUNTY = "DeKalb"
STATE = "IL"
CROP = "Corn"
CORAL = "#F43F5E"
EMERALD = "#10B981"
AMBER = "#F59E0B"
CRITICAL = "#EF4444"
GREENS = ["#10B981", "#22C55E", "#86EFAC", "#DCFCE7"]
REDS = ["#EF4444", "#F87171", "#FCA5A5", "#FEE2E2"]

output_dir = Path(__file__).resolve().parent.parent / "output"
output_dir.mkdir(parents=True, exist_ok=True)

# ── Field Identities ────────────────────────────────────────────────────────
# 10 corn fields in DeKalb County, Illinois — all ≥ 400 acres
FIELDS = [
    {"field_id": "F1", "name": "North Quarter", "acres": 1115, "lat": 41.959, "lon": -88.795},
    {"field_id": "F2", "name": "Creek Bottom", "acres": 982, "lat": 41.912, "lon": -88.830},
    {"field_id": "F3", "name": "West Ridge", "acres": 1140, "lat": 41.915, "lon": -88.792},
    {"field_id": "F4", "name": "East Flats", "acres": 1386, "lat": 41.942, "lon": -88.835},
    {"field_id": "F5", "name": "South Bend", "acres": 621, "lat": 41.996, "lon": -88.760},
    {"field_id": "F6", "name": "Timber Edge", "acres": 859, "lat": 42.056, "lon": -88.738},
    {"field_id": "F7", "name": "Low Ground", "acres": 934, "lat": 41.900, "lon": -88.815},
    {"field_id": "F8", "name": "Middle Forty", "acres": 1252, "lat": 41.935, "lon": -88.810},
    {"field_id": "F9", "name": "Hill Field", "acres": 1108, "lat": 41.913, "lon": -88.842},
    {"field_id": "F10", "name": "Back Section", "acres": 1335, "lat": 41.965, "lon": -88.770},
]
FIELD_ORDER = [f["field_id"] for f in FIELDS]

np.random.seed(101)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: DATA GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_soil_data() -> dict[str, dict[str, Any]]:
    """Generate realistic SSURGO soil profiles for each field.

    Each field has a 3-layer profile (0-15cm, 15-30cm, 30-60cm)
    with organic matter, pH, AWC, bulk density, and drainage class.
    Some fields are deliberately problematic to show realistic Corn Belt variability.
    """
    def make_layer(top: int, bot: int, om: float, ph: float, awc: float,
                   bd: float, clay: float, sand: float) -> dict:
        return {"hzdept_r": top, "hzdepb_r": bot, "om_r": om,
                "ph1to1h2o_r": ph, "awc_r": awc, "dbthirdbar_r": bd,
                "claytotal_r": clay, "sandtotal_r": sand,
                "silttotal_r": round(100 - clay - sand, 1)}

    # Define problematic fields with deliberate soil issues
    presets: dict[str, dict[str, Any]] = {
        # Critical — subsoil acidity + severe compaction
        "F10": {
            "drainagecl": "Somewhat poorly drained",
            "muname": "Sable silty clay loam",
            "compname": "Sable",
            "comppct_r": 55,
            "layers": [
                make_layer(0, 15, 1.8, 5.2, 0.10, 1.48, 34, 14),
                make_layer(15, 30, 0.9, 4.4, 0.05, 1.64, 38, 18),
                make_layer(30, 60, 0.3, 3.8, 0.02, 1.80, 44, 24),
            ],
        },
        # Critical — very poor drainage + extremely low OM
        "F7": {
            "drainagecl": "Poorly drained",
            "muname": "Drummer silty clay loam",
            "compname": "Drummer",
            "comppct_r": 50,
            "layers": [
                make_layer(0, 15, 2.0, 5.5, 0.15, 1.42, 34, 10),
                make_layer(15, 30, 1.0, 4.8, 0.08, 1.58, 40, 12),
                make_layer(30, 60, 0.4, 4.3, 0.04, 1.70, 44, 16),
            ],
        },
        # Watch — moderate topsoil but subsoil acidity exists
        "F3": {
            "drainagecl": "Moderately well drained",
            "muname": "Elburn silt loam",
            "compname": "Elburn",
            "comppct_r": 45,
            "layers": [
                make_layer(0, 15, 2.8, 5.8, 0.16, 1.33, 22, 18),
                make_layer(15, 30, 1.9, 5.2, 0.11, 1.46, 26, 20),
                make_layer(30, 60, 1.1, 4.7, 0.07, 1.56, 28, 22),
            ],
        },
        # Watch — compaction + moderate pH issues
        "F8": {
            "drainagecl": "Somewhat poorly drained",
            "muname": "Ipava silt loam",
            "compname": "Ipava",
            "comppct_r": 40,
            "layers": [
                make_layer(0, 15, 2.6, 5.8, 0.14, 1.40, 28, 16),
                make_layer(15, 30, 1.8, 5.3, 0.10, 1.55, 30, 18),
                make_layer(30, 60, 1.0, 4.8, 0.07, 1.62, 34, 20),
            ],
        },
    }

    soil: dict[str, dict[str, Any]] = {}
    for field in FIELDS:
        fid = field["field_id"]
        if fid in presets:
            soil[fid] = presets[fid]
            continue

        # Good/excellent fields — random but realistic
        base_om = np.clip(np.random.normal(3.5, 0.6), 2.5, 5.5)
        base_ph = np.clip(np.random.normal(6.5, 0.4), 6.0, 7.2)
        base_awc = np.clip(np.random.normal(0.19, 0.02), 0.14, 0.24)
        base_bd = np.clip(np.random.normal(1.30, 0.06), 1.15, 1.45)
        base_clay = np.clip(np.random.normal(25, 5), 15, 35)
        base_sand = np.clip(np.random.normal(12, 5), 5, 25)
        drainage_opts = ["Well drained", "Moderately well drained"]
        drainage_weights = [0.55, 0.45]
        drainage = np.random.choice(drainage_opts, p=drainage_weights)

        layers = []
        for top, bot in [(0, 15), (15, 30), (30, 60)]:
            depth_factor = 0.88 + 0.12 * np.random.random()
            layers.append({
                "hzdept_r": top, "hzdepb_r": bot,
                "om_r": round(max(1.5, base_om * depth_factor * (1 - 0.02 * (top / 15))), 1),
                "ph1to1h2o_r": round(max(5.5, base_ph - 0.1 * (top / 15) + np.random.normal(0, 0.1)), 1),
                "awc_r": round(max(0.08, base_awc * depth_factor), 2),
                "dbthirdbar_r": round(base_bd + 0.03 * (top / 15) + np.random.normal(0, 0.02), 2),
                "claytotal_r": round(base_clay + np.random.normal(0, 2), 1),
                "sandtotal_r": round(base_sand + np.random.normal(0, 2), 1),
                "silttotal_r": 0,
            })
            layers[-1]["silttotal_r"] = round(
                100 - layers[-1]["claytotal_r"] - layers[-1]["sandtotal_r"], 1)

        soil[fid] = {
            "layers": layers,
            "drainagecl": drainage,
            "muname": np.random.choice(
                ["Drummer silty clay loam", "Flanagan silt loam",
                 "Sable silty clay loam", "Ipava silt loam",
                 "Elburn silt loam"]),
            "compname": np.random.choice(["Drummer", "Flanagan", "Sable", "Ipava", "Elburn"]),
            "comppct_r": int(np.random.choice([45, 55, 35, 40, 50])),
        }
    return soil


def generate_weather_data() -> pd.DataFrame:
    """Generate daily weather data for 2021-2025 (NASA POWER - style).

    Realistic for DeKalb County, IL (northern Illinois climate).
    """
    records = []
    start = pd.Timestamp("2021-01-01")
    end = pd.Timestamp("2025-12-31")
    dates = pd.date_range(start, end, freq="D")

    for i, date in enumerate(dates):
        day_of_year = date.dayofyear
        year = date.year
        base_temp = 50 + 28 * np.sin((day_of_year - 105) * np.pi / 183)

        # Add slight warming trend over years
        year_trend = 0.08 * (year - 2021)

        t2m = base_temp + year_trend + np.random.normal(0, 5)
        tmax = base_temp + year_trend + 7 + np.random.normal(0, 4)
        tmin = base_temp + year_trend - 7 + np.random.normal(0, 4)

        # Rain: mostly dry days, occasional events
        precip = 0
        if np.random.random() < 0.28:
            season = abs(day_of_year - 180) / 180
            precip = np.random.gamma(shape=1.5, scale=0.15 / (season + 0.3))
            precip = max(0, round(precip * 25.4, 2))  # inches to mm

        records.append({
            "date": date,
            "year": year,
            "doy": day_of_year,
            "T2M": round(t2m, 1),
            "T2M_MAX": round(tmax, 1),
            "T2M_MIN": round(tmin, 1),
            "PRECTOTCORR": round(precip, 1),
        })

    return pd.DataFrame(records)


def generate_cdl_data() -> dict[str, dict[int, str]]:
    """Generate CDL data — all fields grow corn since we filtered for corn-dominant fields."""
    cdl: dict[str, dict[int, str]] = {}
    for field in FIELDS:
        fid = field["field_id"]
        cdl[fid] = {}
        for year in range(2021, 2026):
            cdl[fid][year] = "Corn" if np.random.random() < 0.85 else "Soybeans"
    corn_count = sum(1 for f in FIELDS if cdl[f["field_id"]].get(2025) == "Corn")
    while corn_count < 8:
        for field in FIELDS:
            fid = field["field_id"]
            if cdl[fid][2025] != "Corn":
                cdl[fid][2025] = "Corn"
                corn_count += 1
                if corn_count >= 8:
                    break
    return cdl


def generate_ndvi_data(soil: dict[str, dict[str, Any]]) -> dict[str, dict[int, list[float]]]:
    """Generate NDVI growing-season values per field per year.

    NDVI is correlated with soil quality: better soil = higher peak NDVI.
    Includes realistic year-to-year weather variability.
    """
    ndvi: dict[str, dict[int, list[float]]] = {}
    for field in FIELDS:
        fid = field["field_id"]
        soil_quality = _calculate_raw_quality(soil[fid])
        ndvi[fid] = {}
        for year in range(2021, 2026):
            # Weather randomness per year
            np.random.seed(hash(f"{fid}_{year}") % 2**31)
            weather_factor = np.clip(np.random.normal(1.0, 0.08), 0.85, 1.15)

            # Build a realistic NDVI curve (DOY 90-270, ~180 days growing season)
            doys = list(range(90, 271, 10))
            ndvi_values = []
            for doy in doys:
                progress = (doy - 90) / 180  # 0 to 1
                # Gaussian-like peak around mid-July (DOY ~195)
                seasonal = np.exp(-((doy - 195) ** 2) / (2 * 35**2))
                peak_ndvi = 0.55 + soil_quality * 0.35  # 0.55 to 0.90 range
                value = peak_ndvi * seasonal * weather_factor
                value += np.random.normal(0, 0.03)
                ndvi_values.append(max(0.15, min(0.95, round(value, 3))))
            ndvi[fid][year] = ndvi_values
    return ndvi


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: SOIL QUALITY SCORING
# ══════════════════════════════════════════════════════════════════════════════

def _calculate_raw_quality(soil_profile: dict[str, Any]) -> float:
    """Calculate a raw 0-1 soil quality score from profile data."""
    layers = soil_profile["layers"]
    drainage = soil_profile["drainagecl"]

    weights = [0.30, 0.25, 0.20, 0.15, 0.10]  # OM, pH, AWC, BD, drainage
    depth_weights = [0.40, 0.30, 0.30]  # 0-15cm, 15-30cm, 30-60cm

    # Organic matter score (optimal: >3.0%)
    om_scores = [min(1.0, l["om_r"] / 3.0) for l in layers]
    om = sum(s * w for s, w in zip(om_scores, depth_weights))

    # pH score (optimal: 6.0-7.0 for corn)
    ph_scores = []
    for l in layers:
        ph = l["ph1to1h2o_r"]
        if 6.0 <= ph <= 7.0:
            ph_scores.append(1.0)
        elif ph < 5.5:
            ph_scores.append(max(0.1, ph / 6.0))
        elif ph > 7.5:
            ph_scores.append(max(0.1, (8.5 - ph) / 1.0))
        else:
            ph_scores.append(0.7)
    ph = sum(s * w for s, w in zip(ph_scores, depth_weights))

    # AWC score (optimal: >0.18)
    awc_scores = [min(1.0, l["awc_r"] / 0.18) for l in layers]
    awc = sum(s * w for s, w in zip(awc_scores, depth_weights))

    # Bulk density score (optimal: <1.40 for silt loam)
    bd_scores = [max(0.0, min(1.0, (1.70 - l["dbthirdbar_r"]) / 0.40)) for l in layers]
    bd = sum(s * w for s, w in zip(bd_scores, depth_weights))

    # Drainage score
    drainage_map = {
        "Well drained": 1.0,
        "Moderately well drained": 0.85,
        "Somewhat poorly drained": 0.55,
        "Poorly drained": 0.25,
        "Excessively drained": 0.5,
    }
    dr_score = drainage_map.get(drainage, 0.5)

    return sum(s * w for s, w in zip([om, ph, awc, bd, dr_score], weights))


def calculate_scores(soil: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate the Soil Quality Index (0-100) for each field.

    Returns list of dicts sorted best-to-worst, with full profile breakdown.
    """
    results = []
    for field in FIELDS:
        fid = field["field_id"]
        raw = _calculate_raw_quality(soil[fid])
        score = round(raw * 100)

        if score >= 80:
            tier, color, label = "excellent", EMERALD, "🟢 Excellent"
        elif score >= 65:
            tier, color, label = "good", AMBER, "🟡 Good"
        elif score >= 55:
            tier, color, label = "watch", "#F97316", "🟠 Needs Attention"
        else:
            tier, color, label = "critical", CRITICAL, "🔴 Critical"

        layers = soil[fid]["layers"]
        topsoil_score = round(sum(
            _layer_subscore(layers[0]) for _ in range(3)) / 3 * 100)
        subsoil_score = round(sum(
            _layer_subscore(layers[2]) for _ in range(3)) / 3 * 100)

        results.append({
            **field,
            "score": score,
            "raw": raw,
            "tier": tier,
            "color": color,
            "label": label,
            "topsoil_score": topsoil_score,
            "subsoil_score": subsoil_score,
            "layers": layers,
            "drainagecl": soil[fid]["drainagecl"],
            "muname": soil[fid]["muname"],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _layer_subscore(layer: dict[str, float]) -> float:
    om_s = min(1.0, layer["om_r"] / 3.0)
    ph = layer["ph1to1h2o_r"]
    if 6.0 <= ph <= 7.0:
        ph_s = 1.0
    elif ph < 5.5:
        ph_s = max(0.1, ph / 6.0)
    elif ph > 7.5:
        ph_s = max(0.1, (8.5 - ph) / 1.0)
    else:
        ph_s = 0.7
    return om_s * 0.45 + ph_s * 0.55


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: ACTION RECOMMENDATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ActionOption:
    def __init__(self, title: str, details: list[str]):
        self.title = title
        self.details = details


def generate_actions(scores: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Generate three-option action recommendations per field.

    For each problematic field, generates:
    1. Fix for Corn (with cost and payback)
    2. Switch to Soybeans (comparative economics)
    3. Do Nothing (baseline)
    """
    actions: dict[str, dict[str, Any]] = {}
    price_corn = 5.50
    price_soy = 13.00

    for field_data in scores:
        fid = field_data["field_id"]
        score = field_data["score"]
        layers = field_data["layers"]
        drainage = field_data["drainagecl"]
        ph_sub = layers[2]["ph1to1h2o_r"]
        om_sub = layers[2]["om_r"]
        bd_sub = layers[2]["dbthirdbar_r"]

        problems = []
        if ph_sub < 5.8:
            problems.append(f"Subsoil pH {ph_sub} (needs 6.0+ for corn roots)")
        if om_sub < 2.0:
            problems.append(f"Subsoil organic matter {om_sub}% (target 2.5%+)")
        if bd_sub > 1.50:
            problems.append(f"Subsoil compaction at {bd_sub} g/cm³ (target <1.45)")
        if drainage in ("Poorly drained", "Somewhat poorly drained"):
            problems.append(f"Drainage: {drainage.lower()} — field holds water")
        if score >= 80:
            problems = []

        # Fix for Corn option
        fix_cost = 0
        fix_details = []
        if ph_sub < 5.8:
            fix_cost += 50
            fix_details.append("Apply 2 tons/acre ag lime to raise subsoil pH")
        if om_sub < 2.0:
            fix_cost += 30
            fix_details.append("Plant cereal rye cover crop to build organic matter")
        if bd_sub > 1.50:
            fix_cost += 40
            fix_details.append("Deep tillage or strip-till to reduce compaction")
        if drainage in ("Poorly drained", "Somewhat poorly drained"):
            fix_cost += 80
            fix_details.append("Install surface drains or mole drains")

        base_yield_corn = 170 + (score - 65) * 0.6  # 130-190 bu range
        base_yield_corn = max(100, min(195, base_yield_corn))
        fixed_yield_corn = base_yield_corn + 25 if score < 65 else base_yield_corn + 5
        revenue_current = base_yield_corn * price_corn
        revenue_fixed = fixed_yield_corn * price_corn

        payback = 0
        if fix_cost > 0:
            annual_gain = (fixed_yield_corn - base_yield_corn) * price_corn
            payback = fix_cost / max(annual_gain, 1)

        # Switch to Soybeans option
        soy_yield_on_good = 60
        soy_penalty = max(0, (65 - score) * 0.25)  # Soybeans lose less yield
        soy_yield = soy_yield_on_good - soy_penalty
        soy_yield = max(35, min(62, soy_yield))
        revenue_soy = soy_yield * price_soy

        actions[fid] = {
            "problems": problems,
            "fix_cost": fix_cost,
            "fix_details": fix_details,
            "base_yield_corn": round(base_yield_corn),
            "fixed_yield_corn": round(fixed_yield_corn),
            "revenue_current": round(revenue_current),
            "revenue_fixed": round(revenue_fixed),
            "payback": round(payback, 1),
            "soy_yield": round(soy_yield),
            "revenue_soy": round(revenue_soy),
            "score": score,
            "tier": field_data["tier"],
        }
    return actions


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: HTML DASHBOARD GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_html(
    scores: list[dict[str, Any]],
    weather: pd.DataFrame,
    ndvi: dict[str, dict[int, list[float]]],
    actions: dict[str, dict[str, Any]],
    output_path: str,
) -> str:
    """Generate the self-contained Observable Plot HTML dashboard."""
    scores_map = {s["field_id"]: s for s in scores}
    default_field = scores[0]["field_id"]
    score_json = json.dumps(scores)
    weather_json = _weather_to_json(weather)
    ndvi_json = json.dumps(ndvi)
    actions_json = json.dumps(actions)

    # Count stats
    n_good = sum(1 for s in scores if s["score"] >= 80)
    n_watch = sum(1 for s in scores if 55 <= s["score"] < 80)
    n_critical = sum(1 for s in scores if s["score"] < 55)

    narrative = _build_narrative(scores, n_good, n_watch, n_critical)
    priority_html = _build_priority_list(scores, actions)
    field_options = _build_field_options(scores, default_field)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corn Soil Dashboard — {GROWER}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.4; font-size: 13px; }}
.dashboard {{ max-width: 1400px; margin: 0 auto; padding: 12px 16px; height: 100vh; display: flex; flex-direction: column; }}
.header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
.header-left {{ }}
.header-left h1 {{ font-size: 20px; color: #166534; margin-bottom: 2px; }}
.header-left .subtitle {{ font-size: 12px; color: #64748b; }}
.narrative {{ font-size: 13px; color: #334155; max-width: 700px; padding: 6px 10px; background: #f0fdf4; border-left: 3px solid {EMERALD}; border-radius: 4px; margin-bottom: 8px; }}
.content {{ display: grid; grid-template-columns: 1fr 280px; gap: 10px; flex: 1; min-height: 0; }}
.left-panel {{ display: flex; flex-direction: column; gap: 8px; min-height: 0; }}
.rankings {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.rankings h2 {{ font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 8px; }}
.rank-row {{ display: flex; align-items: center; gap: 8px; padding: 3px 0; cursor: pointer; border-radius: 4px; transition: background 0.15s; }}
.rank-row:hover {{ background: #f1f5f9; }}
.rank-row.selected {{ background: #dbeafe; }}
.rank-bar-bg {{ flex: 1; height: 18px; background: #f1f5f9; border-radius: 3px; position: relative; overflow: hidden; }}
.rank-bar-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
.rank-label {{ font-weight: 600; font-size: 12px; width: 24px; }}
.rank-score {{ font-size: 12px; font-weight: 700; width: 28px; text-align: right; }}
.rank-ndvi {{ font-size: 10px; color: #64748b; width: 90px; }}
.rank-flag {{ font-size: 10px; width: 90px; }}
.rank-sub {{ display: flex; gap: 2px; align-items: center; font-size: 9px; color: #94a3b8; }}
.rank-sub-bar {{ width: 3px; border-radius: 1px; }}

.right-panel {{ display: flex; flex-direction: column; gap: 8px; }}
.priority {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.priority h2 {{ font-size: 14px; font-weight: 600; color: {CRITICAL}; margin-bottom: 8px; }}
.priority-item {{ padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12px; }}
.priority-item:last-child {{ border-bottom: none; }}
.priority-item .field-name {{ font-weight: 600; }}

.detail {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); flex: 1; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }}
.detail-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
.detail-header h2 {{ font-size: 14px; font-weight: 600; }}
.detail-header select {{ font-size: 12px; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; background: white; }}
.detail-grid {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 10px; margin-bottom: 8px; }}
.map-panel {{ aspect-ratio: 1.2; border: 1px solid #e2e8f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; background: #f8fafc; flex-direction: column; gap: 6px; }}
.map-panel svg {{ max-width: 100%; max-height: 100%; }}
.profile-panel {{ display: flex; flex-direction: column; gap: 4px; font-size: 11px; }}
.profile-panel h3 {{ font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }}
.profile-row {{ display: grid; grid-template-columns: 60px 28px 1fr 36px; gap: 4px; align-items: center; padding: 2px 0; }}
.profile-bar-bg {{ background: #f1f5f9; border-radius: 2px; height: 12px; position: relative; overflow: hidden; }}
.profile-bar-fill {{ height: 100%; border-radius: 2px; }}
.profile-status {{ font-size: 10px; font-weight: 600; text-align: center; padding: 1px 4px; border-radius: 3px; }}
.status-ok {{ background: #dcfce7; color: #166534; }}
.status-warn {{ background: #fef9c3; color: #854d0e; }}
.status-bad {{ background: #fee2e2; color: #991b1b; }}

.ndvi-alert {{ padding: 6px 10px; background: #fef2f2; border-left: 3px solid {CRITICAL}; border-radius: 4px; font-size: 11px; margin-bottom: 8px; }}
.ndvi-alert.ok {{ background: #f0fdf4; border-left-color: {EMERALD}; }}

.options {{ display: flex; flex-direction: column; gap: 6px; }}
.option-card {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; }}
.option-card h4 {{ font-size: 12px; margin-bottom: 4px; }}
.option-card ul {{ list-style: none; font-size: 11px; color: #475569; }}
.option-card ul li {{ padding: 1px 0; }}
.option-card ul li::before {{ content: "├── "; color: #94a3b8; }}
.rec {{ font-size: 11px; padding: 6px 10px; background: #eff6ff; border-radius: 4px; border-left: 3px solid #3b82f6; margin-top: 6px; }}

.weather {{ background: white; border-radius: 8px; padding: 8px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: flex; align-items: center; gap: 16px; }}
.weather h2 {{ font-size: 13px; font-weight: 600; white-space: nowrap; }}
.weather select {{ font-size: 12px; padding: 3px 6px; border: 1px solid #d1d5db; border-radius: 4px; }}
.weather-chart {{ flex: 1; height: 50px; }}
.weather-metric {{ font-size: 11px; text-align: center; }}
.weather-metric .value {{ font-weight: 700; font-size: 14px; }}
.weather-metric .label {{ color: #64748b; font-size: 10px; }}
</style>
</head>
<body>
<div class="dashboard">
  <div class="header">
    <div class="header-left">
      <h1>🌽 Corn Soil Dashboard</h1>
      <div class="subtitle">{COUNTY} County, {STATE} · 10 fields · {sum(f['acres'] for f in FIELDS):,} acres</div>
    </div>
  </div>

  <div class="narrative">{narrative}</div>

  <div class="content">
    <div class="left-panel">
      <div class="rankings">
        <h2>SOIL QUALITY INDEX (best → worst)</h2>
        <div id="rankings-container"></div>
      </div>

      <div class="detail" id="detail-section">
        <div class="detail-header">
          <h2 id="detail-title">FIELD DETAIL</h2>
          <select id="field-selector">{field_options}</select>
        </div>
        <div id="detail-content">Select a field above to see details.</div>
      </div>
    </div>

    <div class="right-panel">
      <div class="priority" id="priority-section">
        {priority_html}
      </div>
    </div>
  </div>

  <div class="weather">
    <h2>WEATHER</h2>
    <select id="year-selector">
      <option value="2025" selected>2025</option>
      <option value="2024">2024</option>
      <option value="2023">2023</option>
      <option value="2022">2022</option>
      <option value="2021">2021</option>
    </select>
    <div id="weather-panel" class="weather-chart"></div>
  </div>
</div>

<script type="module">
import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

const SCORES = {score_json};
const WEATHER = {weather_json};
const NDVI = {ndvi_json};
const ACTIONS = {actions_json};
const DEFAULT_FIELD = "{default_field}";
const PRICE_CORN = 5.50;
const PRICE_SOY = 13.00;

// ── State ──
let selectedField = DEFAULT_FIELD;
let selectedYear = 2025;

// ── Rankings ──
function renderRankings() {{
  const container = document.getElementById("rankings-container");
  const rows = SCORES.map(s => {{
    const pct = s.score;
    const color = s.color;
    const ndviData = NDVI[s.field_id]?.[selectedYear] || [];
    const ndviMean = ndviData.length ? (ndviData.reduce((a,b) => a+b,0) / ndviData.length).toFixed(3) : "—";
    const ndviSpark = ndviData.length ? ndviData.map(v => v.toFixed(3)).join(",") : "";

    let flag = "";
    if (s.score < 55 && ndviMean !== "—" && parseFloat(ndviMean) < 0.65) {{
      flag = "⚠️ Soil+NDVI low";
    }} else if (s.score >= 80) {{
      flag = s.tier === "excellent" ? "✅ No action needed" : "";
    }}

    const selectionClass = s.field_id === selectedField ? " selected" : "";

    const topPct = s.topsoil_score;
    const subPct = s.subsoil_score;

    return `<div class="rank-row${{selectionClass}}" onclick="selectField('${{s.field_id}}')">
      <span class="rank-label">${{s.field_id}}</span>
      <div class="rank-bar-bg">
        <div class="rank-bar-fill" style="width:${{pct}}%; background:${{color}};"></div>
      </div>
      <span class="rank-score" style="color:${{color}}">${{pct}}</span>
      <span class="rank-ndvi" data-ndvi="${{ndviSpark}}">NDVI:—</span>
      <span class="rank-flag">${{flag}}</span>
      <span class="rank-sub">
        Top:<span class="rank-sub-bar" style="background:${{topPct >= 65 ? '#10B981' : '#EF4444'}};height:${{topPct/10}}px;"></span>
        Sub:<span class="rank-sub-bar" style="background:${{subPct >= 50 ? '#10B981' : '#EF4444'}};height:${{Math.max(2, subPct/10)}}px;"></span>
      </span>
    </div>`;
  }}).join('');
  container.innerHTML = rows;

  // Render NDVI sparklines after DOM update
  document.querySelectorAll('.rank-ndvi').forEach(el => {{
    const raw = el.dataset.ndvi;
    if (!raw) return;
    const vals = raw.split(',').map(parseFloat);
    if (vals.length) {{
      const svg = plotSparkline(vals, 80, 14);
      el.innerHTML = '';
      el.appendChild(svg);
    }}
  }});
}}

function plotSparkline(values, width, height) {{
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${{values.length}} 1`);
  svg.style.overflow = "visible";

  const points = values.map((v, i) => `${{i}},${{1 - v}}`).join(' ');
  const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  polyline.setAttribute("points", points);
  polyline.setAttribute("fill", "none");
  polyline.setAttribute("stroke", "#6366f1");
  polyline.setAttribute("stroke-width", "0.08");
  polyline.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(polyline);

  return svg;
}}

// ── Detail Section ──
window.selectField = function(fid) {{
  selectedField = fid;
  document.getElementById("field-selector").value = fid;
  renderRankings();
  renderDetail();
}};

document.getElementById("field-selector").addEventListener("change", (e) => {{
  window.selectField(e.target.value);
}});

function generateFieldMapSvg(fieldId, score) {{
  const field = SCORES.find(s => s.field_id === fieldId);
  if (!field) return '';
  const centerX = 150, centerY = 130;
  const size = 100 + (field.acres - 620) * 0.04;
  const color = score >= 80 ? '#10B981' : score >= 55 ? '#F59E0B' : '#EF4444';
  const opacity = 0.35 + score * 0.006;

  const points = [
    [centerX - size * 0.6, centerY - size * 0.5],
    [centerX + size * 0.5, centerY - size * 0.55],
    [centerX + size * 0.7, centerY],
    [centerX + size * 0.4, centerY + size * 0.5],
    [centerX - size * 0.3, centerY + size * 0.6],
    [centerX - size * 0.7, centerY + size * 0.1],
  ];
  const pathData = points.map((p, i) => `${{i === 0 ? 'M' : 'L'}} ${{p[0]}} ${{p[1]}}`).join(' ') + ' Z';

  return `<svg width="300" height="280" viewBox="0 0 300 280">
    <rect width="300" height="280" fill="#f8fafc"/>
    <path d="${{pathData}}" fill="${{color}}" fill-opacity="${{opacity}}" stroke="${{color}}" stroke-width="2"/>
    <text x="150" y="20" text-anchor="middle" font-size="9" fill="#94a3b8">${{field.name}} Boundary</text>
    <text x="150" y="${{centerY - 20}}" text-anchor="middle" font-size="10" font-weight="600" fill="#64748b">${{field.name}}</text>
    <text x="150" y="${{centerY}}" text-anchor="middle" font-size="9" fill="#94a3b8">${{field.acres}} acres</text>
    <text x="150" y="${{centerY + 15}}" text-anchor="middle" font-size="11" font-weight="700" fill="${{color}}">Score: ${{score}}</text>
  </svg>`;
}}

function renderDetail() {{
  const field = SCORES.find(s => s.field_id === selectedField);
  if (!field) return;
  const action = ACTIONS[field.field_id];
  const ndviData = NDVI[field.field_id]?.[selectedYear] || [];
  const ndviMean = ndviData.length ? (ndviData.reduce((a,b) => a+b,0) / ndviData.length).toFixed(3) : null;

  const isGood = field.score >= 80;
  const ndviLow = ndviMean && parseFloat(ndviMean) < 0.65;
  const ndviBothLow = !isGood && ndviLow;

  const mapSvg = generateFieldMapSvg(field.field_id, field.score);

  let profileHtml = '';
  field.layers.forEach((l, i) => {{
    const depthLabel = i === 0 ? '0-6"' : i === 1 ? '6-12"' : '12-24"';
    const omPct = Math.min(100, Math.round(l.om_r / 5.0 * 100));
    const phPct = Math.min(100, Math.round(l.ph1to1h2o_r / 8.0 * 100));
    const awcPct = Math.min(100, Math.round(l.awc_r / 0.25 * 100));
    const omStatus = l.om_r >= 3.0 ? 'ok' : l.om_r >= 2.0 ? 'warn' : 'bad';
    const phStatus = (l.ph1to1h2o_r >= 6.0 && l.ph1to1h2o_r <= 7.0) ? 'ok' :
                     (l.ph1to1h2o_r >= 5.5 && l.ph1to1h2o_r < 6.0) ? 'warn' : 'bad';
    const awcStatus = l.awc_r >= 0.15 ? 'ok' : l.awc_r >= 0.10 ? 'warn' : 'bad';

    profileHtml += `
      <div style="font-size:10px;font-weight:600;color:#94a3b8;margin-top:4px">${{depthLabel}}</div>
      <div class="profile-row">
        <span>OM</span>
        <div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{omPct}}%;background:#${{omStatus === 'ok' ? '10B981' : omStatus === 'warn' ? 'F59E0B' : 'EF4444'}}"></div></div>
        <span>${{l.om_r}}%</span>
        <span class="profile-status status-${{omStatus}}">${{omStatus === 'ok' ? '✓' : omStatus === 'warn' ? '~' : '✗'}}</span>
      </div>
      <div class="profile-row">
        <span>pH</span>
        <div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{phPct}}%;background:#${{phStatus === 'ok' ? '10B981' : phStatus === 'warn' ? 'F59E0B' : 'EF4444'}}"></div></div>
        <span>${{l.ph1to1h2o_r}}</span>
        <span class="profile-status status-${{phStatus}}">${{phStatus === 'ok' ? '✓' : phStatus === 'warn' ? '~' : '✗'}}</span>
      </div>
      <div class="profile-row">
        <span>AWC</span>
        <div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{awcPct}}%;background:#${{awcStatus === 'ok' ? '10B981' : awcStatus === 'warn' ? 'F59E0B' : 'EF4444'}}"></div></div>
        <span>${{l.awc_r}}</span>
        <span class="profile-status status-${{awcStatus}}">${{awcStatus === 'ok' ? '✓' : awcStatus === 'warn' ? '~' : '✗'}}</span>
      </div>`;
  }});
  profileHtml += `<div style="font-size:9px;color:#94a3b8;margin-top:4px">✓=corn optimal ~=borderline ✗=outside range</div>`;

  let ndviAlertHtml = '';
  if (ndviBothLow) {{
    ndviAlertHtml = `<div class="ndvi-alert">⚠️ <strong>Soil score (${{field.score}}) AND NDVI (${{ndviMean}}) are both low.</strong> This suggests soil limitations are reducing plant vigor. Consider soil remediation or crop switching.</div>`;
  }} else if (isGood && ndviMean && parseFloat(ndviMean) >= 0.72) {{
    ndviAlertHtml = `<div class="ndvi-alert ok">✅ Soil and NDVI both look good — field is performing as expected.</div>`;
  }} else if (isGood && ndviLow) {{
    ndviAlertHtml = `<div class="ndvi-alert">⚠️ Soil score is good (${{field.score}}) but NDVI is lower than expected (${{ndviMean}}). This may indicate management or weather factors, not soil problems.</div>`;
  }}

  let optionsHtml = '';
  if (isGood) {{
    optionsHtml = `<div class="option-card">
      <h4 style="color:#10B981">✅ No Action Needed</h4>
      <ul>
        <li>Soil profile is within optimal range for corn</li>
        <li>Estimated yield: ${{Math.round(action?.base_yield_corn || 180)}} bu/acre</li>
        <li>Revenue: ~$${{Math.round(action?.revenue_current || 990)}}/acre</li>
        <li>Maintain current practices — monitor annually</li>
      </ul>
    </div>`;
  }} else {{
    const fixOpt = action || {{}};
    optionsHtml = `<div class="option-card" style="border-left: 3px solid #10B981">
      <h4 style="color:#166534">OPTION 1: FIX FOR CORN (Recommended long-term)</h4>
      <ul>
        ${{(fixOpt.fix_details || []).map(d => `<li>${{d}}</li>`).join('')}}
        <li><strong>Cost:</strong> $${{fixOpt.fix_cost || 0}}/acre</li>
        <li><strong>Yield:</strong> ${{fixOpt.base_yield_corn || 0}} → ${{fixOpt.fixed_yield_corn || 0}} bu/acre</li>
        <li><strong>Revenue after fix:</strong> ~$${{fixOpt.revenue_fixed || 0}}/acre</li>
        <li><strong>Payback:</strong> ${{(fixOpt.payback || 0).toFixed(1)}} years</li>
      </ul>
    </div>
    <div class="option-card" style="border-left: 3px solid #F59E0B">
      <h4 style="color:#92400E">OPTION 2: SWITCH TO SOYBEANS (Lower risk)</h4>
      <ul>
        <li>Cost: $0 (save on nitrogen fertilizer)</li>
        <li>Expected yield: ${{fixOpt.soy_yield || 0}} bu/acre</li>
        <li>Revenue: ~$${{fixOpt.revenue_soy || 0}}/acre</li>
        <li>Soybeans tolerate ${{field.drainagecl?.toLowerCase() || 'varied'}} soils better</li>
      </ul>
    </div>
    <div class="option-card" style="border-left: 3px solid #94a3b8">
      <h4 style="color:#475569">OPTION 3: DO NOTHING</h4>
      <ul>
        <li>Cost: $0</li>
        <li>Current revenue: ~$${{fixOpt.revenue_current || 0}}/acre</li>
        <li>Risk: Yield may decline further with compaction/acidification</li>
      </ul>
    </div>`;
  }}

  let recHtml = '';
  if (!isGood) {{
    let msg;
    const pb = (action?.payback || 0);
    const fc = (action?.fix_cost || 0);
    if (pb <= 3.0) {{
      msg = 'Fix for corn now — invest $' + fc + '/acre, breaks even in ' + pb.toFixed(1) + ' years.';
    }} else {{
      msg = 'Consider switching to soybeans — lower revenue but zero upfront cost and less risk on this marginal soil.';
    }}
    recHtml = '<div class="rec"><strong>Recommendation:</strong> ' + msg + '</div>';
  }}

  const content = `
    <div class="detail-grid">
      <div class="map-panel">${{mapSvg}}</div>
      <div class="profile-panel">
        <h3>Soil Profile by Depth</h3>
        ${{profileHtml}}
      </div>
    </div>
    ${{ndviAlertHtml}}
    <div class="options">
      ${{optionsHtml}}
    </div>
    ${{recHtml}}
  `;

  document.getElementById("detail-title").textContent = `FIELD DETAIL: ${{field.field_id}} — ${{field.name}}`;
  document.getElementById("detail-content").innerHTML = content;
}}

// ── Weather ──
function renderWeather() {{
  const panel = document.getElementById("weather-panel");
  const yearData = WEATHER.filter(d => d.year === selectedYear);

  if (yearData.length === 0) {{
    panel.innerHTML = '<span style="color:#94a3b8;font-size:11px">No data for ${{selectedYear}}</span>';
    return;
  }}

  const months = Array.from({{length: 12}}, (_, i) => i + 1);
  const monthlyRain = months.map(m => {{
    const days = yearData.filter(d => new Date(d.date).getMonth() + 1 === m);
    return days.reduce((s, d) => s + (d.PRECTOTCORR || 0), 0);
  }});
  const annualRain = monthlyRain.reduce((a, b) => a + b, 0);

  const monthlyTemp = months.map(m => {{
    const days = yearData.filter(d => new Date(d.date).getMonth() + 1 === m);
    if (days.length === 0) return 0;
    return days.reduce((s, d) => s + (d.T2M || 0), 0) / days.length;
  }});
  const annualTemp = monthlyTemp.reduce((a, b) => a + b, 0) / 12;

  // GDD: April-September, base 50°F
  const gddDays = yearData.filter(d => {{
    const m = new Date(d.date).getMonth() + 1;
    return m >= 4 && m <= 9;
  }});
  const annualGdd = Math.round(gddDays.reduce((sum, d) => {{
    const gdd = Math.max(0, ((d.T2M_MAX || 70) + (d.T2M_MIN || 50)) / 2 - 50);
    return sum + gdd;
  }}, 0));

  // Detect anomalies: compare to 5-year average
  const allYears = WEATHER.filter(d => d.year >= 2021 && d.year <= 2025);
  const allRainDays = allYears.filter(d => {{
    const m = new Date(d.date).getMonth() + 1;
    return m >= 4 && m <= 9;
  }});
  const growingRain = allRainDays.reduce((s, d) => s + (d.PRECTOTCORR || 0), 0);
  const avgRain = Math.round(growingRain / 5);
  const thisYearRain = yearData.filter(d => {{
    const m = new Date(d.date).getMonth() + 1;
    return m >= 4 && m <= 9;
  }}).reduce((s, d) => s + (d.PRECTOTCORR || 0), 0);
  const rainPct = avgRain > 0 ? Math.round(thisYearRain / avgRain * 100) : 100;

  const anomalyLabel = rainPct > 130 ? '⚠️ Wet' : rainPct < 70 ? '⚠️ Dry' : '✅ Normal';
  const anomalyColor = rainPct > 130 ? '#EF4444' : rainPct < 70 ? '#F59E0B' : '#10B981';
  const soilValid = rainPct <= 150 && rainPct >= 60;

  // Build sparklines as SVG
  const rainSpark = buildMiniSpark(monthlyRain, 130, 36, Math.max(...monthlyRain, 1));
  const tempSpark = buildMiniSpark(monthlyTemp, 130, 36, Math.max(...monthlyTemp, 1));
  const gddMonthly = months.map(m => {{
    const days = gddDays.filter(d => new Date(d.date).getMonth() + 1 === m);
    return Math.round(days.reduce((s, d) => {{
      return s + Math.max(0, ((d.T2M_MAX || 70) + (d.T2M_MIN || 50)) / 2 - 50);
    }}, 0) / Math.max(days.length, 1));
  }});
  const gddSpark = buildMiniSpark(gddMonthly.filter(x => !isNaN(x)), 130, 36,
    Math.max(...gddMonthly.filter(x => !isNaN(x)), 1));

  panel.innerHTML = `
    <div style="display:flex;gap:12px;align-items:flex-start;justify-content:space-between">
      <div class="weather-metric">
        <div class="value">${{annualRain.toFixed(1)}}″</div>
        <div class="label">Rainfall</div>
        ${{rainSpark}}
      </div>
      <div class="weather-metric">
        <div class="value">${{annualTemp.toFixed(1)}}°F</div>
        <div class="label">Avg Temp</div>
        ${{tempSpark}}
      </div>
      <div class="weather-metric">
        <div class="value">${{annualGdd}}</div>
        <div class="label">GDD (Base 50°F)</div>
        ${{gddSpark}}
      </div>
      <div class="weather-metric">
        <div class="value" style="color:${{anomalyColor}}">${{anomalyLabel}}</div>
        <div class="label">${{rainPct}}% of avg rain</div>
        <div style="font-size:9px;color:#94a3b8;margin-top:2px">Soil readings ${{soilValid ? 'reliable' : 'may be affected'}}</div>
      </div>
    </div>
  `;
}}

function buildMiniSpark(values, width, height, maxVal) {{
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${{values.length - 1}} ${{maxVal}}`);
  svg.style.overflow = "visible";

  const points = values.map((v, i) => `${{i}},${{maxVal - v}}`).join(' ');
  const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  polyline.setAttribute("points", points);
  polyline.setAttribute("fill", "none");
  polyline.setAttribute("stroke", "#3b82f6");
  polyline.setAttribute("stroke-width", "0.15");
  polyline.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(polyline);

  // Highlight selected year dot
  const lastVal = values[values.length - 1];
  if (values.length > 0) {{
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", values.length - 1);
    circle.setAttribute("cy", maxVal - lastVal);
    circle.setAttribute("r", "0.3");
    circle.setAttribute("fill", "#3b82f6");
    svg.appendChild(circle);
  }}

  return svg.outerHTML;
}}

// ── Year selector ──
document.getElementById("year-selector").addEventListener("change", (e) => {{
  selectedYear = parseInt(e.target.value);
  renderWeather();
  renderRankings();
  renderDetail();
}});

// ── Init ──
renderRankings();
renderDetail();
renderWeather();
</script>
</body>
</html>"""
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def _weather_to_json(weather: pd.DataFrame) -> str:
    records = []
    for _, row in weather.iterrows():
        records.append({
            "date": str(row["date"].date()),
            "year": int(row["year"]),
            "doy": int(row["doy"]),
            "T2M": float(row["T2M"]),
            "T2M_MAX": float(row["T2M_MAX"]),
            "T2M_MIN": float(row["T2M_MIN"]),
            "PRECTOTCORR": float(row["PRECTOTCORR"]),
        })
    return json.dumps(records)


def _build_narrative(
    scores: list[dict[str, Any]],
    n_good: int, n_watch: int, n_critical: int,
) -> str:
    avg_score = round(sum(s["score"] for s in scores) / len(scores))
    best = scores[0]
    worst = scores[-1]

    lines = [
        f"<strong>{n_critical} {('field needs' if n_critical == 1 else 'fields need')} immediate action — {n_good} {('field is' if n_good == 1 else 'fields are')} ready for corn.</strong>",
        f"Average soil quality across {len(FIELDS)} fields is <strong>{avg_score}/100</strong>. "
        f"The best field ({best['field_id']} — {best['name']}) scores {best['score']}. "
        f"The lowest ({worst['field_id']} — {worst['name']}) scores {worst['score']}, "
        f"driven by {_worst_problem(worst)}.",
    ]

    if n_critical > 0:
        criticals = [s for s in scores if s["score"] < 55]
        crit_names = ", ".join(f"{s['field_id']} ({s['score']})" for s in criticals[:3])
        lines.append(
            f"Priority fields: {crit_names} — select each below to see detailed fix options, "
            f"including crop switching alternatives with honest payback periods."
        )

    return " ".join(lines)


def _worst_problem(field_data: dict[str, Any]) -> str:
    layers = field_data.get("layers", [])
    if len(layers) < 3:
        return "unknown soil issues"
    sub = layers[2]
    issues = []
    if sub["ph1to1h2o_r"] < 5.8:
        issues.append(f"subsoil acidity (pH {sub['ph1to1h2o_r']})")
    if sub["om_r"] < 2.0:
        issues.append(f"low subsoil organic matter ({sub['om_r']}%)")
    if sub["dbthirdbar_r"] > 1.50:
        issues.append("subsoil compaction")
    if issues:
        return " and ".join(issues[:2])
    return "poor drainage and marginal soil properties"


def _build_priority_list(
    scores: list[dict[str, Any]],
    actions: dict[str, dict[str, Any]],
) -> str:
    criticals = [s for s in scores if s["score"] < 55]
    if not criticals:
        return '<h2>NEEDS ATTENTION</h2><p style="color:#10B981;font-size:12px">✅ No critical fields — all fields performing well.</p>'

    items = []
    for s in criticals[:3]:
        act = actions.get(s["field_id"], {})
        problems = act.get("problems", [])
        problem_line = problems[0] if problems else "Soil quality below threshold"
        items.append(
            f'<div class="priority-item">'
            f'<span class="field-name" style="cursor:pointer;color:{s["color"]}" '
            f'onclick="selectField(\'{s["field_id"]}\')">{s["label"]} {s["field_id"]}</span> '
            f'({s["name"]}, Score: {s["score"]})<br>'
            f'<span style="color:#64748b">{problem_line}</span>'
            f'</div>'
        )

    return (
        f'<h2>NEEDS ATTENTION ({len(criticals)} field{"" if len(criticals) == 1 else "s"})</h2>'
        + "".join(items)
    )


def _build_field_options(scores: list[dict[str, Any]], default_field: str) -> str:
    opts = []
    for s in scores:
        sel = ' selected' if s["field_id"] == default_field else ''
        opts.append(f'<option value="{s["field_id"]}"{sel}>{s["field_id"]} — {s["name"]} (Score: {s["score"]})</option>')
    return "".join(opts)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Corn Soil Dashboard")
    parser.add_argument(
        "--output", default=str(output_dir / "corn_soil_dashboard.html"),
        help="Output HTML path"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌽 Corn Soil Dashboard — Generator")
    print("=" * 60)

    print("\n[1/4] Generating soil data for 10 fields...")
    soil = generate_soil_data()

    print("[2/4] Generating weather data (2021–2025)...")
    weather = generate_weather_data()

    print("[3/4] Generating CDL & NDVI data...")
    cdl = generate_cdl_data()
    ndvi = generate_ndvi_data(soil)

    print("[4/4] Calculating scores, actions & building dashboard...")
    scores = calculate_scores(soil)
    actions = generate_actions(scores)

    output_path = generate_html(scores, weather, ndvi, actions, args.output)

    print(f"\n✅ Dashboard saved to: {output_path}")
    print(f"   Size: {Path(output_path).stat().st_size / 1024:.1f} KB")

    n_good = sum(1 for s in scores if s["score"] >= 80)
    n_watch = sum(1 for s in scores if 50 <= s["score"] < 80)
    n_critical = sum(1 for s in scores if s["score"] < 55)
    print(f"   Fields: {n_good} good, {n_watch} watch, {n_critical} critical")

    return 0


if __name__ == "__main__":
    sys.exit(main())
