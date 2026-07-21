#!/usr/bin/env python3
"""Weather and climate visualization module.

Renders temperature, precipitation, and GDD time series
with event detection annotations.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_weather_dashboard(weather_df: pd.DataFrame, year: int | None = None) -> go.Figure:
    """Render a 3-panel weather dashboard: Precipitation, Temperature, GDD.

    Args:
        weather_df: DataFrame with columns: date, T2M, T2M_MAX, T2M_MIN,
                    PRECTOTCORR, doy. Temperatures in Fahrenheit,
                    precipitation in inches.
        year: Optional year to filter. If None, uses all data.

    Returns:
        Plotly figure with 3 aligned subplots.
    """
    if weather_df is None or weather_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No weather data available", showarrow=False,
                          x=0.5, y=0.5, font=dict(size=16, color="#64748b"))
        fig.update_layout(template="plotly_white", height=400)
        return fig

    df = weather_df.copy()
    if "year" not in df.columns and "date" in df.columns:
        df["year"] = pd.to_datetime(df["date"]).dt.year

    if year is not None and "year" in df.columns:
        df = df[df["year"] == year]

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No weather data for {year}", showarrow=False,
                          x=0.5, y=0.5, font=dict(size=16, color="#64748b"))
        fig.update_layout(template="plotly_white", height=400)
        return fig

    if "doy" not in df.columns and "date" in df.columns:
        df["doy"] = pd.to_datetime(df["date"]).dt.dayofyear

    precip_in = "PRECTOTCORR_in" if "PRECTOTCORR_in" in df.columns else "PRECTOTCORR"
    temp_max_col = "T2M_MAX" if "T2M_MAX" in df.columns else "T2M_MAX"
    temp_min_col = "T2M_MIN" if "T2M_MIN" in df.columns else "T2M_MIN"
    temp_mean_col = "T2M" if "T2M" in df.columns else "T2M"

    has_temp = temp_max_col in df.columns and temp_min_col in df.columns
    has_precip = precip_in in df.columns

    df = df.sort_values("doy")

    df["gdd"] = _compute_gdd(df)
    df["cum_gdd"] = df["gdd"].cumsum()
    df["precip_roll7"] = df[precip_in].rolling(7, min_periods=1).mean()

    heat_days = int((df[temp_max_col] > 95).sum()) if has_temp else 0
    season_precip = float(df[precip_in].sum()) if has_precip else 0
    season_gdd = float(df["cum_gdd"].iloc[-1]) if not df.empty else 0

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("Daily Precipitation", "Temperature Extremes", "Cumulative Growing Degree Days"),
        row_heights=[1, 1, 1],
    )

    if has_precip:
        fig.add_trace(go.Bar(
            x=df["doy"], y=df[precip_in],
            name="Daily Precip",
            marker_color="#475569", opacity=0.6,
            hovertemplate="DOY %{x}<br>%{y:.2f} in<extra></extra>",
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df["doy"], y=df["precip_roll7"],
            name="7-day Avg",
            line=dict(color="#0F766E", width=2),
            hovertemplate="DOY %{x}<br>7d avg: %{y:.2f} in<extra></extra>",
        ), row=1, col=1)

    if has_temp:
        fig.add_trace(go.Scatter(
            x=df["doy"], y=df[temp_max_col],
            mode="lines", name="Tmax", line=dict(color="#FCA5A5", width=0.5),
            showlegend=False, hovertemplate="DOY %{x}<br>Max: %{y:.1f}°F<extra></extra>",
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=df["doy"], y=df[temp_min_col],
            mode="lines", name="Tmin fill", line=dict(color="#FCA5A5", width=0.5),
            fill="tonexty", fillcolor="rgba(252,165,165,0.35)",
            showlegend=False, hovertemplate="DOY %{x}<br>Min: %{y:.1f}°F<extra></extra>",
        ), row=2, col=1)

        if temp_mean_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["doy"], y=df[temp_mean_col],
                mode="lines", name="Tmean",
                line=dict(color="#DC2626", width=1.5),
                hovertemplate="DOY %{x}<br>Mean: %{y:.1f}°F<extra></extra>",
            ), row=2, col=1)

        fig.add_hline(
            y=95, line=dict(color="#D97706", dash="dash", width=1),
            annotation_text="Heat Stress Threshold (95°F)", annotation_position="right",
            row=2, col=1,
        )

    fig.add_trace(go.Scatter(
        x=df["doy"], y=df["cum_gdd"],
        mode="lines", name="Cumulative GDD",
        line=dict(color="#7C3AED", width=2.5),
        hovertemplate="DOY %{x}<br>GDD: %{y:.0f}<extra></extra>",
    ), row=3, col=1)

    for m in [1000, 2000, 3000]:
        crossing = df[df["cum_gdd"] >= m]
        if not crossing.empty:
            fig.add_hline(y=m, line=dict(color="#A78BFA", dash="dot", width=0.8), row=3, col=1)

    fig.update_layout(
        title=f"Weather Summary — Precip: {season_precip:.1f} in | Heat Days (>95°F): {heat_days} | GDD: {season_gdd:.0f}",
        template="plotly_white",
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(title_text="Day of Year", row=3, col=1)
    fig.update_yaxes(title_text="Inches", row=1, col=1)
    fig.update_yaxes(title_text="°F", row=2, col=1)
    fig.update_yaxes(title_text="°F·day", row=3, col=1)

    return fig


def render_climate_context(weather_df: pd.DataFrame) -> go.Figure:
    """Annual precipitation and GDD summary bar chart."""
    if weather_df is None or weather_df.empty:
        return go.Figure()

    df = weather_df.copy()
    if "year" not in df.columns and "date" in df.columns:
        df["year"] = pd.to_datetime(df["date"]).dt.year

    if "year" not in df.columns:
        return go.Figure()

    precip_col = "PRECTOTCORR_in" if "PRECTOTCORR_in" in df.columns else "PRECTOTCORR"

    yearly = df.groupby("year").agg(
        annual_precip_in=(precip_col, "sum"),
        mean_temp_f=("T2M", "mean"),
        days_above_95=("T2M_MAX", lambda x: (x > 95).sum()),
    ).reset_index()

    yearly["cum_gdd"] = df.groupby("year").apply(
        lambda g: _compute_gdd(g).sum() if not g.empty else 0
    ).values

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=yearly["year"], y=yearly["annual_precip_in"],
        name="Annual Precipitation (in)",
        marker_color="#475569", opacity=0.7,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=yearly["year"], y=yearly["cum_gdd"],
        name="Cumulative GDD",
        mode="lines+markers",
        line=dict(color="#7C3AED", width=3),
        marker=dict(size=8),
    ), secondary_y=True)

    fig.update_layout(
        title="Annual Climate Summary",
        template="plotly_white",
        height=350,
    )
    fig.update_yaxes(title_text="Precipitation (in)", secondary_y=False)
    fig.update_yaxes(title_text="GDD (°F·day)", secondary_y=True)
    fig.update_xaxes(title_text="Year")

    return fig


def _compute_gdd(df: pd.DataFrame, base: float = 50.0, cap: float = 86.0) -> pd.Series:
    tmin_col = "T2M_MIN" if "T2M_MIN" in df.columns else "T2M_MIN"
    tmax_col = "T2M_MAX" if "T2M_MAX" in df.columns else "T2M_MAX"

    if tmin_col not in df.columns or tmax_col not in df.columns:
        return pd.Series([0.0] * len(df), index=df.index)

    tmin = df[tmin_col].clip(lower=base, upper=cap)
    tmax = df[tmax_col].clip(lower=base, upper=cap)
    tmean = (tmin + tmax) / 2.0
    return (tmean - base).clip(lower=0.0)
