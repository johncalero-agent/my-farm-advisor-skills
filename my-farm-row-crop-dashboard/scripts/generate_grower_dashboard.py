#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Row Crop Intelligence Dashboard — Grower-level soil health analysis.

Usage:
    streamlit run generate_grower_dashboard.py

Or as a module:
    python generate_grower_dashboard.py --grower-slug il-dekalb-grower

This skill generates a comprehensive soil-intelligence dashboard for all
fields belonging to a grower, with soybean-specific soil health scoring,
action alerts with detailed agronomic recommendations, crop suitability
comparison, weather context, and geospatial visualization.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
sys.path.insert(0, str(_PARENT / "src"))

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import pandas as pd
import plotly.graph_objects as go

from data_loader import build_grower_dataset, load_soil_data, load_field_boundaries, discover_fields
from soil_scoring import score_field_soil, score_all_fields
from action_alerts import evaluate_field, generate_action_summary, get_alert_color_map
from crop_suitability import evaluate_crop_suitability
from viz_kpi import render_kpi_cards, render_score_distribution, render_field_rankings
from viz_exploratory import render_field_size_distribution, render_crop_composition, render_crop_radar
from viz_geospatial import render_field_map
from viz_weather import render_weather_dashboard, render_climate_context
from viz_soil import (
    render_action_alert_cards, render_soil_score_breakdown,
    render_soil_health_ranking_table, render_alert_summary_chart,
)
from narrative_engine import generate_grower_narrative


PAGE_CONFIG = {
    "page_title": "Row Crop Intelligence Dashboard",
    "page_icon": "🌾",
    "layout": "wide",
}


def _render_header(dataset: dict, soil_scores: pd.DataFrame,
                   action_summary: dict):
    cards = render_kpi_cards(dataset, soil_scores, action_summary)
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""<div style="background:#f8fafc;border-radius:10px;padding:16px;text-align:center;
                border-top:4px solid {card['color']};">
                <span style="font-size:24px;">{card['icon']}</span>
                <h3 style="margin:6px 0;color:#0f172a;font-size:22px;">{card['value']}</h3>
                <p style="margin:0;color:#334155;font-size:12px;font-weight:bold;">{card['title']}</p>
                <p style="margin:2px 0 0 0;color:#64748b;font-size:11px;">{card['subtitle']}</p>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_field_detail(soil_scores: pd.DataFrame, soil_df: pd.DataFrame,
                         dataset: dict, suitability_results: list[dict]) -> None:
    st.subheader("Field Detail View")
    field_ids = soil_scores["field_id"].tolist()
    selected_field = st.selectbox("Select a field to analyze:", field_ids)

    if not selected_field:
        return

    score_row = soil_scores[soil_scores["field_id"] == selected_field].iloc[0]
    field_score = score_row.to_dict()
    alerts = evaluate_field(field_score)
    suit_result = next((r for r in suitability_results if r["field_id"] == selected_field), None)

    score = field_score.get("overall_score", 50)
    status = field_score.get("status", "unknown").replace("_", " ").title()
    status_color = {
        "Excellent": "#10B981", "Healthy": "#0D9488",
        "Monitor": "#F59E0B", "High Priority": "#DC2626",
    }.get(status, "#94a3b8")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            f"""<div style="background:#f8fafc;border-radius:10px;padding:20px;">
            <h3 style="margin:0;color:#0f172a;">{selected_field}</h3>
            <span style="font-size:48px;font-weight:bold;color:{status_color};">{score:.0f}</span>
            <span style="font-size:14px;color:{status_color};">/100 — {status}</span>
            <p style="margin-top:8px;color:#334155;">Dominant Soil: <b>{field_score.get('dominant_soil', 'Unknown')}</b><br>
            {field_score.get('dominant_muname', '')}</p>
            <p style="color:#64748b;font-size:13px;">
            pH: {field_score.get('avg_ph', 'N/A')} | OM: {field_score.get('avg_om', 'N/A')}%<br>
            Clay: {field_score.get('avg_clay', 'N/A')}% | Sand: {field_score.get('avg_sand', 'N/A')}%<br>
            Drainage: {field_score.get('drainage_raw', 'N/A')}<br>
            BD: {field_score.get('avg_bulk_density', 'N/A')} g/cm³</p>
            </div>""",
            unsafe_allow_html=True,
        )

        if suit_result:
            st.markdown(
                f"""<div style="background:#f0fdf4;border-radius:8px;padding:12px;margin-top:8px;
                border-left:4px solid #10B981;">
                <b>Crop Suitability</b><br>
                Best crop: <b>{suit_result['best_crop']}</b> ({suit_result['best_score']:.0f}/100)<br>
                Runner-up: {suit_result['runner_up']} ({suit_result['runner_up_score']:.0f}/100)
                </div>""",
                unsafe_allow_html=True,
            )

    with col2:
        fig = render_soil_score_breakdown(field_score)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Action Alerts & Recommendations")
    alert_html = render_action_alert_cards(field_score, alerts)
    st.markdown(alert_html, unsafe_allow_html=True)

    if suit_result:
        st.markdown("---")
        st.subheader("Crop Suitability Comparison")
        fig_radar = render_crop_radar(field_score, suit_result)
        if fig_radar.data:
            st.plotly_chart(fig_radar, use_container_width=True)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Row Crop Intelligence Dashboard for a grower"
    )
    parser.add_argument("--grower-slug", default="il-dekalb-grower",
                       help="Grower slug to analyze")
    parser.add_argument("--farm-slug", default="dekalb-demo-farm",
                       help="Farm slug to analyze")
    parser.add_argument("--no-streamlit", action="store_true",
                       help="Generate data only, skip Streamlit UI")
    args = parser.parse_args()

    if HAS_STREAMLIT and not args.no_streamlit:
        st.set_page_config(**PAGE_CONFIG)
        _run_streamlit_dashboard(args)
    else:
        _run_cli_dashboard(args)


def _run_cli_dashboard(args):
    print("=" * 70)
    print("  Row Crop Intelligence Dashboard")
    print(f"  Grower: {args.grower_slug}  |  Farm: {args.farm_slug}")
    print("=" * 70)

    print("\nLoading data...")
    dataset = build_grower_dataset(args.grower_slug, args.farm_slug)
    soil_df = dataset["soil"]

    print(f"  Fields: {len(dataset['fields'])}")
    print(f"  Soil records: {len(soil_df)}")

    print("\nComputing soil health scores...")
    soil_scores = score_all_fields(soil_df)
    action_summary = generate_action_summary(soil_scores.to_dict("records") if not soil_scores.empty else [{}])

    suitability_results = []
    for _, row in soil_scores.iterrows():
        result = evaluate_crop_suitability(row.to_dict())
        suitability_results.append(result)

    print(f"\n  Avg Score: {soil_scores['overall_score'].mean():.0f}/100" if not soil_scores.empty else "  No scores")
    print(f"  Total Alerts: {sum(c.get('critical',0)+c.get('warning',0) for c in action_summary.get('alert_counts',{}).values())}")

    print("\n  Top 5 Field Scores:")
    for _, row in soil_scores.sort_values("overall_score", ascending=False).head(5).iterrows():
        print(f"    {row['field_id']}: {row['overall_score']:.0f}/100 ({row['status']})")

    print("\nDashboard data generation complete. Run with Streamlit for full UI.")
    print("  pip install streamlit")
    print(f"  streamlit run {__file__}")


def _run_streamlit_dashboard(args):
    st.title("🌾 Row Crop Intelligence Dashboard")
    st.caption(f"Grower: **{args.grower_slug}**  |  Farm: **{args.farm_slug}**  |  Crop Focus: Soybeans")

    with st.spinner("Loading grower data..."):
        dataset = build_grower_dataset(args.grower_slug, args.farm_slug)
        soil_df = dataset["soil"]

    if soil_df.empty:
        st.warning("No soil data found. Using synthetic sample data for demonstration.")
        field_ids = [f["field_slug"] for f in dataset["fields"]]
        from data_loader import load_soil_data
        soil_df = load_soil_data(None, None, field_ids)

    with st.spinner("Computing soil health scores..."):
        soil_scores = score_all_fields(soil_df)
        score_dicts = soil_scores.to_dict("records") if not soil_scores.empty else [{}]
        action_summary = generate_action_summary(score_dicts)

        suitability_results = []
        if not soil_scores.empty:
            for _, row in soil_scores.iterrows():
                result = evaluate_crop_suitability(row.to_dict())
                suitability_results.append(result)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview & Alerts",
        "Field Rankings",
        "Geospatial Map",
        "Weather & Climate",
        "Field Detail",
        "Insights & Interpretation",
    ])

    with tab1:
        st.subheader("Grower Summary")
        _render_header(dataset, soil_scores, action_summary)

        st.markdown("---")
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("Exploratory: Field Size Distribution")
            boundaries = dataset.get("boundaries", pd.DataFrame())
            fig = render_field_size_distribution(boundaries)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Crop Composition")
            cdl = dataset.get("cdl", pd.DataFrame())
            fig = render_crop_composition(cdl)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("Soil Health Score Distribution")
            fig = render_score_distribution(soil_scores)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Action Alert Summary")
            fig = render_alert_summary_chart(action_summary)
            st.plotly_chart(fig, use_container_width=True)

            prioritized = action_summary.get("prioritized_actions", [])
            if prioritized:
                st.markdown("**Prioritized Action List:**")
                for action in prioritized[:5]:
                    alert_colors = get_alert_color_map()
                    c = alert_colors.get(action["alert_id"], {}).get("color", "#94a3b8")
                    st.markdown(
                        f"""<div style="border-left:4px solid {c};padding:6px 12px;
                        margin-bottom:6px;background:#f8fafc;border-radius:4px;">
                        <b>{action['field_id']}</b>: {action['alert_label']}</div>""",
                        unsafe_allow_html=True,
                    )

    with tab2:
        st.subheader("Field Soil Health Rankings")
        fig = render_field_rankings(soil_scores)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Field Comparison Table")
        fig = render_soil_health_ranking_table(soil_scores, action_summary)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("Geospatial Field Map")
        st.caption("Fields colored by soil health score. Green = Excellent, Red = High Priority.")
        boundaries = dataset.get("boundaries", pd.DataFrame())
        fig = render_field_map(boundaries, soil_scores)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Weather & Climate Context")
        weather = dataset.get("weather", pd.DataFrame())

        year_options = sorted(weather["year"].unique()) if not weather.empty and "year" in weather.columns else [2022]
        if not weather.empty and "year" not in weather.columns and "date" in weather.columns:
            weather["year"] = pd.to_datetime(weather["date"]).dt.year
            year_options = sorted(weather["year"].unique())

        selected_year = st.selectbox("Select growing season:", year_options, index=min(2, len(year_options)-1))
        st.caption(f"Showing weather patterns for {selected_year}")

        fig = render_weather_dashboard(weather, selected_year)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Multi-Year Climate Context")
        fig = render_climate_context(weather)
        st.plotly_chart(fig, use_container_width=True)

    with tab5:
        _render_field_detail(soil_scores, soil_df, dataset, suitability_results)

    with tab6:
        st.subheader("Analytical Interpretation")

        narrative = generate_grower_narrative(
            dataset, soil_scores, action_summary, suitability_results
        )

        sections = narrative.split("\n\n## ")
        for i, section in enumerate(sections):
            if i == 0:
                st.markdown(section)
            else:
                st.markdown(f"## {section}")
            if i < len(sections) - 1:
                st.markdown("---")

    st.markdown("---")
    st.caption(
        "Row Crop Intelligence Dashboard — Generated by my-farm-row-crop-dashboard skill. "
        "Soil data sourced from NRCS SSURGO via Soil Data Access (SDA). "
        "Recommendations are agronomic guidance based on soil property analysis. "
        "Consult a certified agronomist before implementing changes."
    )


if __name__ == "__main__":
    main()
