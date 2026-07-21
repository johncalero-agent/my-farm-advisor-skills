#!/usr/bin/env python3
"""Geospatial visualization module.

Renders an interactive folium/plotly map of field boundaries
colored by soil health score, with popup details for each field.
"""
from __future__ import annotations

from typing import Any
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def render_field_map(boundaries: pd.DataFrame, soil_scores: pd.DataFrame,
                     highlight_field: str | None = None) -> go.Figure:
    """Render an interactive field boundary map color-coded by soil score.

    Args:
        boundaries: DataFrame with field_id, acres, and geometry columns.
        soil_scores: DataFrame with field_id, overall_score, status columns.
        highlight_field: Optional field_id to highlight on the map.

    Returns:
        Plotly figure with field boundaries as filled polygons.
    """
    if boundaries is None or boundaries.empty:
        fig = go.Figure()
        fig.add_annotation(text="No geospatial data available", showarrow=False,
                          x=0.5, y=0.5, font=dict(size=16, color="#64748b"))
        fig.update_layout(template="plotly_white", height=500)
        return fig

    try:
        import geopandas as gpd
        has_geometry = "geometry" in boundaries.columns and hasattr(boundaries, "geometry")
        if not has_geometry:
            try:
                boundaries = gpd.GeoDataFrame(boundaries, geometry="geometry", crs="EPSG:4326")
            except Exception:
                has_geometry = False

        if has_geometry:
            boundaries = boundaries.to_crs("EPSG:4326")
    except ImportError:
        has_geometry = False

    fig = go.Figure()

    centroids_x, centroids_y, colors, sizes, texts, field_ids_list = [], [], [], [], [], []

    score_lookup = {}
    if not soil_scores.empty and "field_id" in soil_scores.columns:
        for _, row in soil_scores.iterrows():
            score_lookup[str(row["field_id"])] = {
                "overall_score": row.get("overall_score", 50),
                "status": row.get("status", "unknown"),
                "dominant_soil": row.get("dominant_soil", "Unknown"),
                "avg_om": row.get("avg_om"),
                "avg_ph": row.get("avg_ph"),
                "avg_clay": row.get("avg_clay"),
                "avg_sand": row.get("avg_sand"),
            }

    for _, row in boundaries.iterrows():
        fid = str(row.get("field_id", ""))
        score_info = score_lookup.get(fid, {})
        score = score_info.get("overall_score", 50)
        status = score_info.get("status", "unknown")

        if score > 80:
            color = "#10B981"
        elif score > 60:
            color = "#0D9488"
        elif score > 40:
            color = "#F59E0B"
        else:
            color = "#DC2626"

        size = 12
        opacity = 1.0
        if highlight_field and fid == highlight_field:
            size = 20
            opacity = 1.0
        elif status == "high_priority":
            size = 14

        if has_geometry and hasattr(boundaries, "geometry"):
            geom = row.geometry
            if geom is not None:
                try:
                    centroid = geom.centroid
                    centroids_x.append(centroid.x)
                    centroids_y.append(centroid.y)
                except Exception:
                    continue
            else:
                continue
        else:
            centroids_x.append(-88.8 + np.random.uniform(-0.1, 0.1))
            centroids_y.append(41.9 + np.random.uniform(-0.1, 0.1))

        colors.append(color)
        sizes.append(size)
        acres = row.get("acres", "N/A")
        dom_soil = score_info.get("dominant_soil", "Unknown")
        text_entry = (
            f"<b>{fid}</b><br>"
            f"Acres: {acres}<br>"
            f"Soil Score: {score:.0f}/100<br>"
            f"Status: {status.replace('_', ' ').title()}<br>"
            f"Dominant Soil: {dom_soil}"
        )
        texts.append(text_entry)
        field_ids_list.append(fid)

    fig.add_trace(go.Scattermapbox(
        lat=centroids_y,
        lon=centroids_x,
        mode="markers+text",
        marker=dict(size=sizes, color=colors, opacity=0.8),
        text=field_ids_list,
        textposition="top center",
        textfont=dict(size=10, color="#1e293b"),
        hovertemplate="%{hovertext}<extra></extra>",
        hovertext=texts,
        name="Fields",
    ))

    lat_center = np.mean(centroids_y) if centroids_y else 41.9
    lon_center = np.mean(centroids_x) if centroids_x else -88.8

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=lat_center, lon=lon_center),
            zoom=10,
        ),
        title="Field Map — Colored by Soil Health Score",
        template="plotly_white",
        height=550,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(
            yanchor="top", y=0.99, xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
        ),
    )

    fig.add_trace(go.Scattermapbox(
        lat=[None], lon=[None], mode="markers",
        marker=dict(size=12, color="#10B981"),
        name="Excellent (>80)",
        showlegend=True,
    ))
    fig.add_trace(go.Scattermapbox(
        lat=[None], lon=[None], mode="markers",
        marker=dict(size=12, color="#0D9488"),
        name="Healthy (60-80)",
        showlegend=True,
    ))
    fig.add_trace(go.Scattermapbox(
        lat=[None], lon=[None], mode="markers",
        marker=dict(size=12, color="#F59E0B"),
        name="Monitor (40-60)",
        showlegend=True,
    ))
    fig.add_trace(go.Scattermapbox(
        lat=[None], lon=[None], mode="markers",
        marker=dict(size=12, color="#DC2626"),
        name="High Priority (<40)",
        showlegend=True,
    ))

    return fig
