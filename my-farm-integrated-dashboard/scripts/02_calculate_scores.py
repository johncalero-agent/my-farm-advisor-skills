#!/usr/bin/env python3
"""Step 2: Calculate Soil Quality Index and action recommendations.

Reads:
  data/field_boundaries.csv
  data/soil_profiles.csv

Outputs:
  data/soil_scores.csv         — Per-field Soil Quality Index (0-100) with detailed breakdown
  data/action_recommendations.csv — Three-option analysis per field (fix / switch / do nothing)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PRICE_CORN = 5.50
PRICE_SOY = 13.00


def load_data():
    fields = pd.read_csv(DATA_DIR / "field_boundaries.csv")
    soil = pd.read_csv(DATA_DIR / "soil_profiles.csv")
    return fields, soil


def _layer_subscore(layer):
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


def calculate_scores(fields, soil):
    """Calculate Soil Quality Index (0-100) per field.

    Weights: OM 30%, pH 25%, AWC 20%, Bulk Density 15%, Drainage 10%
    Depth weights: 0-15cm 40%, 15-30cm 30%, 30-60cm 30%
    """
    weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    depth_weights = [0.40, 0.30, 0.30]
    results = []

    for _, field in fields.iterrows():
        fid = field["field_id"]
        layers_df = soil[soil["field_id"] == fid].sort_values("hzdept_r")
        layers = layers_df.to_dict("records")
        drainage = layers[0]["drainagecl"]

        om_scores = [min(1.0, l["om_r"] / 3.0) for l in layers]
        om = sum(s * w for s, w in zip(om_scores, depth_weights))

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
        ph_raw = sum(s * w for s, w in zip(ph_scores, depth_weights))

        awc_scores = [min(1.0, l["awc_r"] / 0.18) for l in layers]
        awc_raw = sum(s * w for s, w in zip(awc_scores, depth_weights))

        bd_scores = [max(0.0, min(1.0, (1.70 - l["dbthirdbar_r"]) / 0.40)) for l in layers]
        bd_raw = sum(s * w for s, w in zip(bd_scores, depth_weights))

        drainage_map = {"Well drained": 1.0, "Moderately well drained": 0.85,
                        "Somewhat poorly drained": 0.55, "Poorly drained": 0.25,
                        "Excessively drained": 0.5}
        dr_score = drainage_map.get(drainage, 0.5)

        raw = sum(s * w for s, w in zip([om, ph_raw, awc_raw, bd_raw, dr_score], weights))
        score = round(raw * 100)

        if score >= 80:
            tier = "excellent"
        elif score >= 65:
            tier = "good"
        elif score >= 55:
            tier = "watch"
        else:
            tier = "critical"

        topsoil_score = round(_layer_subscore(layers[0]) * 100)
        subsoil_score = round(_layer_subscore(layers[2]) * 100)

        results.append({
            "field_id": fid,
            "name": field["name"],
            "acres": field["acres"],
            "lat": field["lat"],
            "lon": field["lon"],
            "score": score,
            "raw_score": round(raw, 4),
            "tier": tier,
            "topsoil_score": topsoil_score,
            "subsoil_score": subsoil_score,
            "om_score": round(om, 4),
            "ph_score": round(ph_raw, 4),
            "awc_score": round(awc_raw, 4),
            "bd_score": round(bd_raw, 4),
            "drainage_score": round(dr_score, 4),
            "drainagecl": drainage,
            "muname": layers[0]["muname"],
        })

    return pd.DataFrame(results).sort_values("score", ascending=False)


def generate_actions(scores_df):
    """Generate three-option analysis per field."""
    rows = []
    for _, s in scores_df.iterrows():
        fid = s["field_id"]
        score = s["score"]
        drainage = s["drainagecl"]

        base_yield_corn = 170 + (score - 65) * 0.6
        base_yield_corn = max(100, min(195, base_yield_corn))
        fixed_yield_corn = base_yield_corn + (25 if score < 65 else 5)

        revenue_current = base_yield_corn * PRICE_CORN
        revenue_fixed = fixed_yield_corn * PRICE_CORN
        annual_gain = (fixed_yield_corn - base_yield_corn) * PRICE_CORN

        soy_yield = max(35, min(62, 60 - max(0, (65 - score) * 0.25)))
        revenue_soy = soy_yield * PRICE_SOY

        fix_cost = 0
        fix_details = []
        if score < 80:
            fix_details.append(f"Soil Quality: {score}/100 ({s['tier'].capitalize()})")
            fix_details.append(f"Drainage: {drainage}")
            if score < 65:
                fix_cost += 50
                fix_details.append("Apply ag lime to raise subsoil pH")
            if score < 55:
                fix_cost += 30
                fix_details.append("Plant cover crop to build organic matter")
                fix_cost += 40
                fix_details.append("Deep tillage or strip-till to reduce compaction")
            if drainage in ("Poorly drained", "Somewhat poorly drained"):
                fix_cost += 80
                fix_details.append("Install surface/mole drains")

        payback = round(fix_cost / max(annual_gain, 1), 1) if fix_cost > 0 else 0

        rows.append({
            "field_id": fid,
            "score": score,
            "tier": s["tier"],
            "base_yield_corn_bu_ac": round(base_yield_corn),
            "fixed_yield_corn_bu_ac": round(fixed_yield_corn),
            "revenue_current_per_ac": round(revenue_current),
            "revenue_fixed_per_ac": round(revenue_fixed),
            "soy_yield_bu_ac": round(soy_yield),
            "revenue_soy_per_ac": round(revenue_soy),
            "fix_cost_per_ac": fix_cost,
            "payback_years": payback,
            "fix_details": " | ".join(fix_details) if fix_details else "No action needed",
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("Step 2: Calculating Scores and Actions")
    print("=" * 60)

    print("\nLoading raw data...")
    fields, soil = load_data()

    print(f"  Fields: {len(fields)}")
    print(f"  Soil horizons: {len(soil)}")

    print("\nCalculating Soil Quality Index...")
    scores = calculate_scores(fields, soil)
    scores.to_csv(DATA_DIR / "soil_scores.csv", index=False)

    n_good = (scores["score"] >= 80).sum()
    n_critical = (scores["score"] < 55).sum()
    print(f"  Scores saved: {len(scores)} fields")
    for _, s in scores.iterrows():
        print(f"    {s['field_id']} ({s['name']}): {s['score']} — {s['tier']}")

    print(f"\n  Distribution: {n_good} excellent, "
          f"{(scores['score'] >= 65).sum() - n_good - (scores['score'] >= 55).sum() + 1} good, "
          f"{((scores['score'] >= 55) & (scores['score'] < 65)).sum()} watch, "
          f"{n_critical} critical")

    print("\nGenerating action recommendations...")
    actions = generate_actions(scores)
    actions.to_csv(DATA_DIR / "action_recommendations.csv", index=False)
    print(f"  Actions saved: {len(actions)} fields")

    for _, a in actions.iterrows():
        print(f"    {a['field_id']}: Fix ${a['fix_cost_per_ac']}/ac, "
              f"payback {a['payback_years']}yr | "
              f"Soy ${a['revenue_soy_per_ac']}/ac | "
              f"Corn ${a['revenue_current_per_ac']}/ac")

    print("\n✅ Scores and actions saved to data/")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
