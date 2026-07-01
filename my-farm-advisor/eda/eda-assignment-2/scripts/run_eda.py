#!/usr/bin/env python3
"""
run_eda.py — Assignment 2 field-level EDA orchestrator.

Reads grower runtime data (boundaries, weather, CDL) and produces
12 static outputs: statistical visualizations, comparison tables,
and geospatial maps across three categories.

Usage:
    export DATA_PIPELINE_DATA_ROOT=/path/to/runtime
    python scripts/run_eda.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="Set2")

DATA_ROOT = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", ""))
if not DATA_ROOT.exists():
    print("ERROR: DATA_PIPELINE_DATA_ROOT is not set or does not exist")
    sys.exit(1)

GROWERS_ROOT = DATA_ROOT / "data-pipeline" / "growers"
OUTPUT_DIR = DATA_ROOT / "data-pipeline" / "eda" / "eda-assignment-2" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GROWER_CONFIG = [
    ("il-dekalb-grower", "dekalb-demo-farm", "IL", "DeKalb, IL"),
    ("iowa-grower", "iowa-grower-iowa", "IA", "Story, IA"),
    ("nebraska-grower", "nebraska-farm", "NE", "Phelps, NE"),
]
GROWER_COLORS = {"IL": "#4e79a7", "IA": "#f28e2b", "NE": "#e15759"}
GROWER_LABELS = {abbr: label for _, _, abbr, label in GROWER_CONFIG}


def load_boundaries() -> dict[str, gpd.GeoDataFrame]:
    result = {}
    for slug, farm, abbr, _ in GROWER_CONFIG:
        path = GROWERS_ROOT / slug / "farms" / farm / "boundary" / "field_boundaries.geojson"
        gdf = gpd.read_file(path)
        gdf["grower"] = abbr
        result[abbr] = gdf
    return result


def load_weather() -> dict[str, pd.DataFrame]:
    result = {}
    for slug, farm, abbr, _ in GROWER_CONFIG:
        tables_dir = GROWERS_ROOT / slug / "farms" / farm / "derived" / "tables"
        wt = list(tables_dir.glob("*weather*.csv"))
        if wt:
            df = pd.read_csv(wt[0], parse_dates=["date"])
            df["grower"] = abbr
            df["year"] = df["date"].dt.year
            df["gdd"] = ((df["T2M_MAX"] + df["T2M_MIN"]) / 2 - 10).clip(lower=0)
            result[abbr] = df
    return result


def load_cdl() -> dict[str, pd.DataFrame]:
    result = {}
    for slug, farm, abbr, _ in GROWER_CONFIG:
        tables_dir = GROWERS_ROOT / slug / "farms" / farm / "derived" / "tables"
        fc = list(tables_dir.glob("*full_composition*"))
        if fc:
            df = pd.read_csv(fc[0])
            df["grower"] = abbr
            result[abbr] = df
    return result


def load_rotation() -> dict[str, pd.DataFrame]:
    result = {}
    for slug, farm, abbr, _ in GROWER_CONFIG:
        tables_dir = GROWERS_ROOT / slug / "farms" / farm / "derived" / "tables"
        rt = list(tables_dir.glob("*rotation*"))
        if rt:
            df = pd.read_csv(rt[0])
            df["grower"] = abbr
            result[abbr] = df
    return result


# ── Field Boundary Outputs ──

def plot_area_histogram(boundaries: dict[str, gpd.GeoDataFrame]) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    for abbr, c in GROWER_COLORS.items():
        data = boundaries[abbr]["area_acres"]
        ax.hist(data, bins=8, alpha=0.6, color=c, label=GROWER_LABELS[abbr], edgecolor="white")
    ax.set_xlabel("Field area (acres)")
    ax.set_ylabel("Number of fields")
    ax.set_title("Field Area Distribution by Grower")
    ax.legend()
    path = str(OUTPUT_DIR / "area_histogram.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_area_boxplot(boundaries: dict[str, gpd.GeoDataFrame]) -> str:
    combined = pd.concat(boundaries.values(), ignore_index=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    order = ["IL", "IA", "NE"]
    data = [boundaries[abbr]["area_acres"] for abbr in order]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5)
    ax.set_xticklabels([GROWER_LABELS[abbr] for abbr in order])
    for patch, abbr in zip(bp["boxes"], order):
        patch.set_facecolor(GROWER_COLORS[abbr])
        patch.set_alpha(0.6)
    for whisker in bp["whiskers"]:
        whisker.set_color("gray")
    for cap in bp["caps"]:
        cap.set_color("gray")
    for median in bp["medians"]:
        median.set_color("black")
    ax.set_ylabel("Field area (acres)")
    ax.set_title("Field Area Comparison Across Growers")
    path = str(OUTPUT_DIR / "area_boxplot.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def save_area_comparison(boundaries: dict[str, gpd.GeoDataFrame]) -> str:
    rows = []
    for abbr, gdf in boundaries.items():
        a = gdf["area_acres"]
        rows.append({
            "grower": abbr, "count": len(a), "min_ac": round(a.min(), 1),
            "max_ac": round(a.max(), 1), "mean_ac": round(a.mean(), 1),
            "cv_pct": round(a.std() / a.mean() * 100, 1),
            "total_ac": round(a.sum(), 1),
        })
    df = pd.DataFrame(rows)
    path = str(OUTPUT_DIR / "area_comparison.csv")
    df.to_csv(path, index=False)
    print(f"  Saved: {path}")
    return path


def plot_boundary_map(boundaries: dict[str, gpd.GeoDataFrame]) -> str:
    combined = pd.concat(boundaries.values(), ignore_index=True)
    combined = combined.to_crs("EPSG:5070")
    fig, ax = plt.subplots(figsize=(12, 6))
    for abbr, c in GROWER_COLORS.items():
        subset = combined[combined["grower"] == abbr]
        subset.plot(ax=ax, color=c, edgecolor="black", linewidth=0.3,
                     alpha=0.7, label=GROWER_LABELS[abbr])
    ax.set_title("Field Boundaries by Grower")
    ax.set_xlabel("Easting (m, EPSG:5070)")
    ax.set_ylabel("Northing (m, EPSG:5070)")
    ax.legend()
    ax.axis("equal")
    path = str(OUTPUT_DIR / "boundary_map.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_individual_boundary_maps(boundaries: dict[str, gpd.GeoDataFrame]) -> list[str]:
    paths = []
    for abbr in ["IL", "IA", "NE"]:
        gdf = boundaries[abbr].to_crs("EPSG:5070")
        fig, ax = plt.subplots(figsize=(8, 6))
        gdf.plot(ax=ax, color=GROWER_COLORS[abbr], edgecolor="black",
                  linewidth=0.5, alpha=0.8)
        # Add field labels
        for _, row in gdf.iterrows():
            cent = row.geometry.centroid
            label = row["field_id"].replace("osm-", "").replace("IL_FIELD_", "F")
            ax.annotate(label, (cent.x, cent.y), fontsize=5, ha="center", va="center")
        ax.set_title(f"Field Boundaries — {GROWER_LABELS[abbr]}")
        ax.set_xlabel("Easting (m, EPSG:5070)")
        ax.set_ylabel("Northing (m, EPSG:5070)")
        ax.axis("equal")
        path = str(OUTPUT_DIR / f"boundary_map_{abbr.lower()}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {path}")
        paths.append(path)
    return paths


# ── Weather Outputs ──

def plot_annual_precip(weather: dict[str, pd.DataFrame]) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(5)
    width = 0.25
    years = sorted(weather["IL"]["year"].unique())
    for i, abbr in enumerate(["IL", "IA", "NE"]):
        grouped = weather[abbr].groupby("year")["PRECTOTCORR"].sum() / weather[abbr]["field_id"].nunique()
        vals = [grouped.get(y, 0) for y in years]
        ax.bar(x + i * width, vals, width, color=GROWER_COLORS[abbr],
               alpha=0.8, label=GROWER_LABELS[abbr])
    ax.set_xticks(x + width)
    ax.set_xticklabels(years)
    ax.set_ylabel("Annual precipitation (mm)")
    ax.set_title("Annual Precipitation by Grower")
    ax.legend()
    path = str(OUTPUT_DIR / "annual_precip.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_annual_gdd(weather: dict[str, pd.DataFrame]) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(5)
    width = 0.25
    years = sorted(weather["IL"]["year"].unique())
    for i, abbr in enumerate(["IL", "IA", "NE"]):
        grouped = weather[abbr].groupby("year")["gdd"].sum() / weather[abbr]["field_id"].nunique()
        vals = [grouped.get(y, 0) for y in years]
        ax.bar(x + i * width, vals, width, color=GROWER_COLORS[abbr],
               alpha=0.8, label=GROWER_LABELS[abbr])
    ax.set_xticks(x + width)
    ax.set_xticklabels(years)
    ax.set_ylabel("Annual GDD (base 10°C)")
    ax.set_title("Annual Growing Degree Days by Grower")
    ax.legend()
    path = str(OUTPUT_DIR / "annual_gdd.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def save_precip_gdd_correlation(weather: dict[str, pd.DataFrame]) -> str:
    rows = []
    for abbr in ["IL", "IA", "NE"]:
        grouped = weather[abbr].groupby("year").agg(
            precip=("PRECTOTCORR", lambda x: x.sum() / weather[abbr]["field_id"].nunique()),
            gdd=("gdd", lambda x: x.sum() / weather[abbr]["field_id"].nunique()),
        )
        for year, row in grouped.iterrows():
            rows.append({"grower": abbr, "year": int(year),
                         "precip_mm": round(row["precip"], 1),
                         "gdd": round(row["gdd"], 1)})
    df = pd.DataFrame(rows)
    path_csv = str(OUTPUT_DIR / "precip_gdd_correlation.csv")
    df.to_csv(path_csv, index=False)

    fig, ax = plt.subplots(figsize=(8, 6))
    for abbr in ["IL", "IA", "NE"]:
        subset = df[df["grower"] == abbr]
        ax.scatter(subset["precip_mm"], subset["gdd"], c=GROWER_COLORS[abbr],
                   s=80, alpha=0.8, label=GROWER_LABELS[abbr], edgecolors="black", linewidth=0.5)
        for _, row in subset.iterrows():
            ax.annotate(str(int(row["year"])), (row["precip_mm"], row["gdd"]),
                        fontsize=7, ha="center", va="bottom", xytext=(0, 4),
                        textcoords="offset points")
    ax.set_xlabel("Annual precipitation (mm)")
    ax.set_ylabel("Annual GDD (base 10°C)")
    ax.set_title("Precipitation vs GDD by Grower-Year")
    ax.legend()
    path_png = str(OUTPUT_DIR / "precip_gdd_correlation.png")
    fig.savefig(path_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path_png}")
    return path_csv


def plot_weather_centroid_map(boundaries: dict[str, gpd.GeoDataFrame],
                               weather: dict[str, pd.DataFrame]) -> str:
    points = []
    for abbr, gdf in boundaries.items():
        gdf_proj = gdf.to_crs("EPSG:5070")
        total_precip = weather[abbr].groupby("field_id")["PRECTOTCORR"].sum()
        for _, row in gdf_proj.iterrows():
            cent = row.geometry.centroid
            precip_val = total_precip.get(row["field_id"], 0)
            points.append({"grower": abbr, "field_id": row["field_id"],
                           "geometry": cent, "total_precip_mm": precip_val})
    gdf_pts = gpd.GeoDataFrame(points, crs="EPSG:5070")

    fig, ax = plt.subplots(figsize=(10, 6))
    for abbr in ["IL", "IA", "NE"]:
        subset = gdf_pts[gdf_pts["grower"] == abbr]
        subset.plot(ax=ax, color=GROWER_COLORS[abbr], markersize=40,
                     alpha=0.7, label=GROWER_LABELS[abbr], edgecolors="black", linewidth=0.5)
    ax.set_title("Field Centroids by Grower (Total Precip 2021-2025)")
    ax.set_xlabel("Easting (m, EPSG:5070)")
    ax.set_ylabel("Northing (m, EPSG:5070)")
    ax.legend()
    path = str(OUTPUT_DIR / "weather_centroid_map.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ── CDL Outputs ──

def plot_crop_composition(cdl: dict[str, pd.DataFrame]) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(3)
    width = 0.6
    all_crops = sorted({c for abbr in ["IL", "IA", "NE"] for c in cdl[abbr]["crop_name"].unique()})
    bottom = np.zeros(3)
    colors = plt.cm.Set2(np.linspace(0, 1, len(all_crops)))
    crop_data = {abbr: cdl[abbr].groupby("crop_name")["pct"].mean() for abbr in ["IL", "IA", "NE"]}
    for idx, crop in enumerate(all_crops):
        vals = [crop_data[abbr].get(crop, 0) for abbr in ["IL", "IA", "NE"]]
        ax.bar(x, vals, width, bottom=bottom, color=colors[idx], edgecolor="white", label=crop)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([GROWER_LABELS[abbr] for abbr in ["IL", "IA", "NE"]])
    ax.set_ylabel("Mean crop percentage")
    ax.set_title("Crop Composition by Grower (avg across years)")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    path = str(OUTPUT_DIR / "crop_composition_stacked.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def plot_corn_years_histogram(cdl: dict[str, pd.DataFrame]) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    for abbr, c in GROWER_COLORS.items():
        dominant = cdl[abbr].loc[cdl[abbr].groupby(["field_id", "year"])["pct"].idxmax()]
        by_field = dominant[dominant["crop_name"] == "Corn"].groupby("field_id").size()
        ax.hist(by_field, bins=range(1, 7), alpha=0.6, color=c,
                label=GROWER_LABELS[abbr], edgecolor="white", align="left")
    ax.set_xlabel("Number of years in corn (out of 5)")
    ax.set_ylabel("Number of fields")
    ax.set_title("Corn Years Distribution by Grower")
    ax.set_xticks(range(1, 6))
    ax.legend()
    path = str(OUTPUT_DIR / "corn_years_histogram.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def save_corn_soy_ratio(cdl: dict[str, pd.DataFrame]) -> str:
    rows = []
    for abbr in ["IL", "IA", "NE"]:
        for year in sorted(cdl[abbr]["year"].unique()):
            subset = cdl[abbr][cdl[abbr]["year"] == year]
            corn = subset[subset["crop_name"] == "Corn"]["pct"].sum()
            soy = subset[subset["crop_name"] == "Soybeans"]["pct"].sum()
            rows.append({
                "grower": abbr, "year": int(year),
                "corn_pct": round(corn, 1), "soy_pct": round(soy, 1),
                "corn_soy_total_pct": round(corn + soy, 1),
            })
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, 6))
    for abbr, c in GROWER_COLORS.items():
        subset = df[df["grower"] == abbr]
        ax.plot(subset["year"], subset["corn_soy_total_pct"], "o-",
                color=c, linewidth=2, markersize=8, label=GROWER_LABELS[abbr])
    ax.set_xlabel("Year")
    ax.set_ylabel("Corn + Soybean % of total CDL area")
    ax.set_title("Corn/Soy Dominance by Grower Over Time")
    ax.set_xticks(sorted(df["year"].unique()))
    ax.legend()
    path_png = str(OUTPUT_DIR / "corn_soy_ratio.png")
    fig.savefig(path_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path_png}")
    path_csv = str(OUTPUT_DIR / "corn_soy_ratio.csv")
    df.to_csv(path_csv, index=False)
    print(f"  Saved: {path_csv}")
    return path_csv


def plot_dominant_crop_map(boundaries: dict[str, gpd.GeoDataFrame],
                            cdl: dict[str, pd.DataFrame]) -> str:
    combined = pd.concat(boundaries.values(), ignore_index=True)
    combined = combined.to_crs("EPSG:5070")
    dominant = []
    for abbr in ["IL", "IA", "NE"]:
        cdl_2025 = cdl[abbr][cdl[abbr]["year"] == 2025]
        top = cdl_2025.loc[cdl_2025.groupby("field_id")["pct"].idxmax()]
        dominant.append(top)
    dominant_all = pd.concat(dominant, ignore_index=True)
    merged = combined.merge(dominant_all[["field_id", "crop_name"]].rename(
        columns={"crop_name": "dominant_crop"}), on="field_id", how="left")
    merged["dominant_crop"] = merged["dominant_crop"].fillna("Unknown")
    crop_colors = {"Corn": "#f4c542", "Soybeans": "#6db33f", "Alfalfa": "#9acd32",
                   "Winter Wheat": "#d4a76a", "Grass/Pasture": "#90ee90",
                   "Forest": "#2d5a27", "Fallow/Idle": "#cd853f", "Unknown": "#cccccc"}
    fig, ax = plt.subplots(figsize=(12, 6))
    for crop, color in crop_colors.items():
        subset = merged[merged["dominant_crop"] == crop]
        if not subset.empty:
            subset.plot(ax=ax, color=color, edgecolor="black", linewidth=0.3,
                        alpha=0.8, label=crop)
    ax.set_title("Dominant 2025 Crop by Field")
    ax.axis("equal")
    ax.legend(loc="lower right", fontsize=8)
    path = str(OUTPUT_DIR / "dominant_crop_map.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ── Main ──

def main():
    print("=" * 60)
    print("EDA: Assignment 2 Field-Level Analysis")
    print("=" * 60)
    print()

    print("Loading data...")
    boundaries = load_boundaries()
    weather = load_weather()
    cdl = load_cdl()
    print(f"  Boundaries: {', '.join(f'{k}: {len(v)} fields' for k, v in boundaries.items())}")
    print(f"  Weather:    {', '.join(f'{k}: {len(v)} rows' for k, v in weather.items())}")
    print(f"  CDL:        {', '.join(f'{k}: {len(v)} rows' for k, v in cdl.items())}")
    print()

    print("Field boundary outputs:")
    plot_area_histogram(boundaries)
    plot_area_boxplot(boundaries)
    save_area_comparison(boundaries)
    plot_boundary_map(boundaries)
    plot_individual_boundary_maps(boundaries)
    print()

    print("Weather outputs:")
    plot_annual_precip(weather)
    plot_annual_gdd(weather)
    save_precip_gdd_correlation(weather)
    plot_weather_centroid_map(boundaries, weather)
    print()

    print("CDL/cropland outputs:")
    plot_crop_composition(cdl)
    plot_corn_years_histogram(cdl)
    save_corn_soy_ratio(cdl)
    plot_dominant_crop_map(boundaries, cdl)
    print()

    print(f"All outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
