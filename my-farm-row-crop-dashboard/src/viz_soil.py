#!/usr/bin/env python3
"""Soil health and sustainability visualization module.

Renders action alert cards, soil health score breakdowns,
depth profiles, and conservation priority indicators.
"""
from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.graph_objects as go


def render_action_alert_cards(field_score: dict, alerts: list[dict]) -> str:
    """Render action alert cards as HTML for Streamlit.

    Returns HTML string with styled alert cards.
    """
    triggered = [a for a in alerts if a.get("triggered")]
    if not triggered:
        return (
            '<div style="padding:20px;background:#f0fdf4;border-radius:8px;'
            'border-left:6px solid #10B981;">'
            '<p style="font-size:16px;color:#065f46;margin:0;"><b>&#x2705; '
            'No Action Alerts</b></p>'
            '<p style="font-size:14px;color:#047857;margin:4px 0 0 0;">'
            f'This field ({field_score.get("field_id", "")}) has healthy soil '
            f'conditions for soybean production. Soil score: '
            f'{field_score.get("overall_score", "N/A"):.0f}/100. '
            'Continue current management practices.</p></div>'
        )

    html_parts = []
    for alert in triggered:
        sev = alert["severity"]
        sev_label = "&#x26A0; CRITICAL" if sev == "critical" else "&#x26A0; WARNING"
        sev_bg = "rgba(127,29,29,0.06)" if sev == "critical" else "rgba(180,83,9,0.06)"
        sev_border = "#991B1B" if sev == "critical" else alert["color"]

        rec = alert.get("recommendation", "").replace("\n", "<br>")
        rec_formatted = rec.replace("**", "<b>").replace("</b><br><b>", "</b><br><b>")

        if sev == "critical":
            rec_formatted = rec_formatted.replace("<br><b>", "<br><br><b>").replace("</b><br>", "</b><br><br>")

        card = (
            f'<div style="margin-bottom:16px;background:{sev_bg};border-radius:8px;'
            f'border-left:6px solid {sev_border};padding:16px;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<span style="font-size:20px;">{alert["icon"]}</span>'
            f'<span style="font-size:16px;font-weight:bold;color:{alert["color"]};">'
            f'{alert["label"]}</span>'
            f'<span style="font-size:12px;padding:3px 8px;border-radius:12px;'
            f'background:{sev_border}20;color:{sev_border};font-weight:bold;">'
            f'{sev_label}</span></div>'
            f'<div style="font-size:13px;color:#334155;line-height:1.6;">'
            f'{rec_formatted}</div></div>'
        )
        html_parts.append(card)

    return "".join(html_parts)


def render_soil_score_breakdown(field_score: dict) -> go.Figure:
    """Render a horizontal bar chart of soil property scores."""
    prop_scores = field_score.get("property_scores", {})
    if not prop_scores:
        return go.Figure()

    labels_map = {
        "om_r": "Organic Matter",
        "ph1to1h2o_r": "pH Balance",
        "awc_r": "Available Water Capacity",
        "dbthirdbar_r": "Bulk Density",
        "drainage_score": "Drainage",
    }

    labels = []
    scores = []
    weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    colors = ["#10B981", "#0D9488", "#F59E0B", "#D97706", "#0891B2"]

    for prop, label in labels_map.items():
        if prop in prop_scores:
            labels.append(label)
            scores.append(prop_scores[prop])

    bar_colors = []
    for s in scores:
        if s > 75:
            bar_colors.append("#10B981")
        elif s > 50:
            bar_colors.append("#F59E0B")
        else:
            bar_colors.append("#DC2626")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=scores,
        y=labels,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{s:.0f}" for s in scores],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}/100<extra></extra>",
    ))

    fig.add_vline(x=75, line_dash="dash", line_color="#10B981", line_width=1, opacity=0.5)
    fig.add_vline(x=50, line_dash="dash", line_color="#F59E0B", line_width=1, opacity=0.5)

    fig.update_layout(
        title=f"Property Score Breakdown — {field_score.get('field_id', 'Field')} "
              f"(Overall: {field_score.get('overall_score', 0):.0f}/100)",
        xaxis=dict(title="Score (0-100)", range=[0, 105]),
        template="plotly_white",
        height=280,
    )
    return fig


def render_soil_health_ranking_table(soil_scores: pd.DataFrame,
                                      action_summary: dict[str, Any]) -> go.Figure:
    """Render a styled table of fields ranked by soil health score."""
    if soil_scores.empty:
        return go.Figure()

    df = soil_scores.sort_values("overall_score", ascending=True).copy()

    field_alerts_map = {}
    for fa in action_summary.get("field_alerts", []):
        field_alerts_map[fa["field_id"]] = fa.get("alert_count", 0)

    table_data: dict[str, list] = {
        "Field": [],
        "Score": [],
        "Status": [],
        "Alerts": [],
        "Dominant Soil": [],
        "pH": [],
        "OM (%)": [],
    }

    for _, row in df.iterrows():
        fid = str(row.get("field_id", ""))
        table_data["Field"].append(fid)
        table_data["Score"].append(f"{row['overall_score']:.0f}")
        table_data["Status"].append(row.get("status", "unknown").replace("_", " ").title())
        table_data["Alerts"].append(str(field_alerts_map.get(fid, 0)))
        table_data["Dominant Soil"].append(str(row.get("dominant_soil", ""))[:25])
        table_data["pH"].append(f"{row.get('avg_ph', 0):.1f}" if row.get("avg_ph") else "N/A")
        table_data["OM (%)"].append(f"{row.get('avg_om', 0):.1f}" if row.get("avg_om") else "N/A")

    status_colors = {
        "Excellent": "#10B981", "Healthy": "#0D9488",
        "Monitor": "#F59E0B", "High Priority": "#DC2626",
    }

    fill_colors = []
    for s in table_data["Status"]:
        fill_colors.append(status_colors.get(s, "#94a3b8"))

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(table_data.keys()),
            fill_color="#1e293b",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=list(table_data.values()),
            fill_color=[fill_colors] * len(table_data),
            font=dict(size=11),
            align="left",
            height=30,
        ),
    )])

    fig.update_layout(
        title="Field Soil Health Rankings",
        template="plotly_white",
        height=max(300, len(df) * 35 + 60),
    )
    return fig


def render_alert_summary_chart(action_summary: dict[str, Any]) -> go.Figure:
    """Render a summary bar chart of alert types across all fields."""
    alert_counts = action_summary.get("alert_counts", {})
    if not alert_counts:
        return go.Figure()

    alert_ids = []
    labels = []
    critical_counts = []
    warning_counts = []
    colors = []
    name_to_color = {
        "Nitrogen Leaching Risk": "#7C3AED",
        "Compaction Stress": "#92400E",
        "Acidity Lockup": "#F59E0B",
        "Drought Susceptibility": "#D97706",
        "Waterlogging Risk": "#0891B2",
    }

    for aid, counts in alert_counts.items():
        alert_ids.append(aid)
        labels.append(counts.get("label", aid))
        critical_counts.append(counts.get("critical", 0))
        warning_counts.append(counts.get("warning", 0))
        colors.append(name_to_color.get(counts.get("label", ""), "#94a3b8"))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Critical",
        x=labels, y=critical_counts,
        marker_color=["#DC2626"] * len(labels),
        hovertemplate="%{x}<br>Critical: %{y}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Warning",
        x=labels, y=warning_counts,
        marker_color=colors,
        hovertemplate="%{x}<br>Warning: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title="Action Alerts by Type",
        barmode="stack",
        xaxis_title="Alert Type",
        yaxis_title="Number of Fields",
        template="plotly_white",
        height=350,
    )
    return fig
