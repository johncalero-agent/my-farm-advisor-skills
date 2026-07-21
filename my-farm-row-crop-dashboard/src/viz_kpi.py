#!/usr/bin/env python3
"""KPI summary visualization module.

Renders grower-level summary cards and key performance indicators
for the Row Crop Intelligence Dashboard.
"""
from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.graph_objects as go


def render_kpi_cards(dataset: dict[str, Any], soil_scores: pd.DataFrame,
                     action_summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate KPI cards for the dashboard header.

    Returns list of card dictionaries with title, value, subtitle, and color.
    """
    cards = []

    boundaries = dataset.get("boundaries", pd.DataFrame())
    n_fields = len(boundaries) if not boundaries.empty else len(dataset.get("fields", []))
    total_acres = _safe_sum(boundaries, "acres")

    cards.append({
        "title": "Total Fields",
        "value": str(n_fields),
        "subtitle": f"{total_acres:.0f} total acres" if total_acres else "",
        "color": "#475569",
        "icon": "🌾",
    })

    if not soil_scores.empty:
        avg_score = soil_scores["overall_score"].mean()
        exc_count = (soil_scores["status"] == "excellent").sum()
        monitor_count = (soil_scores["status"].isin(["monitor", "high_priority"])).sum()

        cards.append({
            "title": "Avg Soil Health Score",
            "value": f"{avg_score:.0f}/100",
            "subtitle": f"{exc_count} excellent · {monitor_count} need attention",
            "color": "#10B981" if avg_score >= 60 else "#F59E0B" if avg_score >= 40 else "#DC2626",
            "icon": "🩺",
        })

    cdl = dataset.get("cdl", pd.DataFrame())
    if not cdl.empty and "crop_name" in cdl.columns and "pct" in cdl.columns:
        latest_year = cdl["year"].max()
        latest = cdl[cdl["year"] == latest_year]
        dominant_counts = latest.groupby("crop_name")["field_id"].nunique()
        top_crop = dominant_counts.idxmax() if not dominant_counts.empty else "Unknown"
        top_pct = latest[latest["crop_name"] == top_crop]["pct"].mean() if not dominant_counts.empty else 0
        cards.append({
            "title": f"Dominant Crop ({latest_year})",
            "value": str(top_crop),
            "subtitle": f"Avg {top_pct:.0f}% coverage across fields",
            "color": "#0F766E",
            "icon": "🌱",
        })

    alert_counts = action_summary.get("alert_counts", {})
    total_alerts = sum(
        counts.get("critical", 0) + counts.get("warning", 0)
        for counts in alert_counts.values()
    )
    critical_count = sum(counts.get("critical", 0) for counts in alert_counts.values())

    cards.append({
        "title": "Action Alerts",
        "value": str(total_alerts),
        "subtitle": f"{critical_count} critical · {total_alerts - critical_count} warning",
        "color": "#DC2626" if critical_count > 0 else "#F59E0B" if total_alerts > 0 else "#10B981",
        "icon": "🚨",
    })

    return cards


def render_score_distribution(soil_scores: pd.DataFrame) -> go.Figure:
    """Render a histogram of soil health scores across fields."""
    if soil_scores.empty:
        return go.Figure()

    scores = soil_scores["overall_score"].dropna()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=scores,
        nbinsx=20,
        marker_color="#0F766E",
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.8,
        hovertemplate="Score: %{x}<br>Fields: %{y}<extra></extra>",
    ))

    fig.add_vline(x=80, line_dash="dash", line_color="#10B981", line_width=2,
                  annotation_text="Excellent", annotation_position="top")
    fig.add_vline(x=60, line_dash="dash", line_color="#0D9488", line_width=2,
                  annotation_text="Healthy", annotation_position="top")
    fig.add_vline(x=40, line_dash="dash", line_color="#F59E0B", line_width=2,
                  annotation_text="Monitor", annotation_position="top")

    fig.update_layout(
        title="Soil Health Score Distribution",
        xaxis_title="Soil Health Score (0-100)",
        yaxis_title="Number of Fields",
        template="plotly_white",
        bargap=0.05,
        height=350,
    )
    return fig


def render_field_rankings(soil_scores: pd.DataFrame) -> go.Figure:
    """Render a horizontal bar chart of field rankings."""
    if soil_scores.empty:
        return go.Figure()

    df = soil_scores.sort_values("overall_score", ascending=True)

    colors = []
    for _, row in df.iterrows():
        if row["overall_score"] > 80:
            colors.append("#10B981")
        elif row["overall_score"] > 60:
            colors.append("#0D9488")
        elif row["overall_score"] > 40:
            colors.append("#F59E0B")
        else:
            colors.append("#DC2626")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["overall_score"],
        y=df["field_id"],
        orientation="h",
        marker_color=colors,
        text=[f"{s:.0f}" for s in df["overall_score"]],
        textposition="outside",
        hovertemplate="Field: %{y}<br>Score: %{x:.1f}<extra></extra>",
    ))

    fig.update_layout(
        title="Field Soil Health Rankings",
        xaxis_title="Soil Health Score",
        template="plotly_white",
        height=max(300, len(df) * 30),
        margin=dict(l=10, r=40, t=40, b=20),
    )
    return fig


def _safe_sum(df: pd.DataFrame, col: str) -> float | None:
    if df is None or df.empty or col not in df.columns:
        return None
    return float(df[col].astype(float).sum())
