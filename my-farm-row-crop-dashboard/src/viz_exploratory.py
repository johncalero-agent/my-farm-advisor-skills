#!/usr/bin/env python3
"""Exploratory visualization module.

Generates field-level exploratory charts: field size distribution,
crop composition analysis, and NDVI/property comparisons.
"""
from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def render_field_size_distribution(boundaries: pd.DataFrame) -> go.Figure:
    """Histogram and boxplot of field sizes in acres."""
    if boundaries is None or boundaries.empty:
        return go.Figure()

    acres = boundaries["acres"].dropna().astype(float) if "acres" in boundaries.columns else pd.Series(dtype=float)
    if acres.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=acres,
        nbinsx=15,
        name="Field Size Distribution",
        marker_color="#475569",
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.75,
        hovertemplate="Size: %{x:.0f} acres<br>Fields: %{y}<extra></extra>",
    ))

    mean_val = acres.mean()
    median_val = acres.median()
    fig.add_vline(x=mean_val, line_dash="dash", line_color="#DC2626", line_width=2,
                  annotation_text=f"Mean: {mean_val:.0f} ac", annotation_position="top")
    fig.add_vline(x=median_val, line_dash="dot", line_color="#16A34A", line_width=2,
                  annotation_text=f"Median: {median_val:.0f} ac", annotation_position="bottom")

    fig.update_layout(
        title="Field Size Distribution",
        xaxis_title="Field Size (acres)",
        yaxis_title="Number of Fields",
        template="plotly_white",
        height=350,
    )
    return fig


def render_crop_composition(cdl: pd.DataFrame) -> go.Figure:
    """Stacked bar chart showing crop composition across fields."""
    if cdl is None or cdl.empty:
        return go.Figure()

    if "crop_name" not in cdl.columns or "field_id" not in cdl.columns:
        return go.Figure()

    fields = sorted(cdl["field_id"].unique())[:15]
    field_data = cdl[cdl["field_id"].isin(fields)]

    crops = sorted(field_data["crop_name"].unique())

    fig = go.Figure()
    for crop in crops:
        crop_data = field_data[field_data["crop_name"] == crop]
        fig.add_trace(go.Bar(
            name=crop,
            x=crop_data["field_id"],
            y=crop_data["pct"],
            text=[f"{p:.0f}%" for p in crop_data["pct"]],
            textposition="inside",
            textfont_size=9,
            hovertemplate=f"{crop}<br>%{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title="Crop Composition by Field",
        xaxis_title="Field",
        yaxis_title="Percentage of Field Area",
        template="plotly_white",
        height=400,
    )
    return fig


def render_soil_depth_profile(field_score: dict) -> go.Figure:
    """Horizontal bar chart showing soil properties by depth zone."""
    depth_profile = field_score.get("depth_profile", [])
    if not depth_profile:
        return go.Figure()

    properties = ["om_r", "ph1to1h2o_r", "awc_r", "dbthirdbar_r"]
    labels = ["Organic Matter (%)", "pH", "AWC (cm/cm)", "Bulk Density (g/cm³)"]
    optimal_ranges = [
        (3.0, 6.0),
        (6.3, 7.0),
        (0.15, 0.25),
        (1.10, 1.45),
    ]

    zones = [z["zone"].replace("_", " ").title() for z in depth_profile]
    depths = [z["depth_cm"] for z in depth_profile]

    fig = go.Figure()

    for i, (prop, label, (opt_min, opt_max)) in enumerate(zip(properties, labels, optimal_ranges)):
        values = []
        for z in depth_profile:
            val = z.get(prop)
            values.append(val if val is not None else 0)

        fig.add_trace(go.Bar(
            name=label,
            x=depths,
            y=values,
            text=[f"{v:.2f}" if v is not None else "N/A" for v in values],
            textposition="auto",
            hovertemplate=f"{label}<br>Depth: %{{x}}<br>Value: %{{y:.3f}}<extra></extra>",
        ))

    fig.update_layout(
        title=f"Soil Depth Profile — {field_score.get('field_id', 'Field')}",
        xaxis_title="Depth Zone",
        yaxis_title="Value",
        template="plotly_white",
        height=400,
        barmode="group",
    )
    return fig


def render_crop_radar(field_score: dict, suitability: dict) -> go.Figure:
    """Radar chart comparing crop suitability scores."""
    if not suitability or "crop_details" not in suitability:
        return go.Figure()

    crops = list(suitability["crop_details"].keys())
    dimensions = ["ph", "om", "drainage", "awc", "bulk_density"]
    dim_labels = ["pH", "Organic Matter", "Drainage", "Water Capacity", "Bulk Density"]

    fig = go.Figure()
    colors = ["#0F766E", "#7C3AED", "#D97706"]

    for i, (crop, color) in enumerate(zip(crops, colors)):
        detail = suitability["crop_details"][crop]
        values = [detail["dimension_scores"].get(d, 50) for d in dimensions]
        values.append(values[0])

        display_dims = dim_labels + [dim_labels[0]]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=display_dims,
            name=crop,
            fill="toself",
            line_color=color,
            opacity=0.4,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100], ticksuffix="%")),
        title=f"Crop Suitability — {field_score.get('field_id', 'Field')}",
        template="plotly_white",
        height=400,
    )
    return fig
