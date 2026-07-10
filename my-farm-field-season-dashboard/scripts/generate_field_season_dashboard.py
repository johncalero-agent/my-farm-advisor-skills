#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportArgumentType=false, reportCallIssue=false, reportGeneralTypeIssues=false
"""Generate an aligned field-season mini-dashboard for one field-year.

Usage:
    python generate_field_season_dashboard.py \
        --data-root /path/to/data-pipeline/runtime \
        --grower-slug <grower> \
        --farm-slug <farm> \
        --field-slug <field> \
        --year <year> \
        [--gdd-base 50] \
        [--gdd-cap 86] \
        [--heat-stress-threshold 95] \
        [--planting-doy 90] \
        [--output-path <path>]

Outputs a single PNG with four aligned panels:
  1. Sentinel NDVI (CDL crop-masked mean)
  2. Daily precipitation
  3. Temperature extremes (min/max band + mean)
  4. Cumulative GDD

Annotations and heuristic captions compare the selected year to a 5-year
field reference when historical data is available.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject
from rasterio.mask import mask

matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_ROOT = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", "/tmp/my-farm-advisor-runtime"))
_RUNTIME_BASE = _DATA_ROOT / "data-pipeline"
_GROWERS_ROOT = _RUNTIME_BASE / "growers"
_SHARED_ROOT = _RUNTIME_BASE / "shared"


def _field_dir(grower: str, farm: str, field: str) -> Path:
    return _GROWERS_ROOT / grower / "farms" / farm / "fields" / field


def _field_weather_path(grower: str, farm: str, field: str) -> Path:
    return _field_dir(grower, farm, field) / "weather" / "daily_weather.csv"


def _field_boundary_path(grower: str, farm: str, field: str) -> Path:
    return _field_dir(grower, farm, field) / "boundary" / "field_boundary.geojson"


def _field_satellite_dir(grower: str, farm: str, field: str) -> Path:
    return _field_dir(grower, farm, field) / "satellite"


def _field_reports_dir(grower: str, farm: str, field: str) -> Path:
    return _field_dir(grower, farm, field) / "derived" / "reports"


def _farm_dir(grower: str, farm: str) -> Path:
    return _GROWERS_ROOT / grower / "farms" / farm


def _farm_tables_dir(grower: str, farm: str) -> Path:
    return _farm_dir(grower, farm) / "derived" / "tables"


def _normalized_farm_prefix(farm_slug: str) -> str:
    normalized = farm_slug.strip().replace("-", "_")
    if normalized == "iowa_demo_farm":
        return "iowa"
    if normalized.endswith("_farm"):
        normalized = normalized[: -len("_farm")]
    return normalized


def _farm_cdl_full_composition_path(grower: str, farm: str, start: int, end: int) -> Path:
    prefix = _normalized_farm_prefix(farm)
    return _farm_tables_dir(grower, farm) / f"{prefix}_cdl_{start}_{end}_full_composition.csv"


def _farm_cdl_preferred_full_composition_path(grower: str, farm: str) -> Path:
    for start, end in ((2021, 2025), (2020, 2024), (2021, 2024)):
        candidate = _farm_cdl_full_composition_path(grower, farm, start, end)
        if candidate.exists():
            return candidate
    return _farm_cdl_full_composition_path(grower, farm, 2021, 2025)


def _shared_cdl_conus_raster_path(year: int) -> Path:
    return _SHARED_ROOT / "cdl" / "rasters" / f"CDL_{year}_CONUS.tif"


def _shared_cdl_state_raster_path(year: int, state_fips: str) -> Path:
    return _SHARED_ROOT / "cdl" / "rasters" / f"CDL_{year}_{state_fips.zfill(2)}.tif"


def _resolve_cdl_raster(year: int, state_fips: str = "19") -> Path | None:
    state_path = _shared_cdl_state_raster_path(year, state_fips)
    if state_path.exists():
        return state_path
    conus_path = _shared_cdl_conus_raster_path(year)
    if conus_path.exists():
        return conus_path
    return None


# ---------------------------------------------------------------------------
# CDL helpers
# ---------------------------------------------------------------------------
_CDL_CODES = {
    0: "No Data",
    1: "Corn",
    5: "Soybeans",
    24: "Winter Wheat",
    28: "Alfalfa",
    36: "Forest",
    38: "Grassland",
    43: "Open Water",
    61: "Fallow/Idle",
    63: "Other",
    176: "Grass/Pasture",
}


def _dominant_crop_for_field_year(cdl_path: Path, field_id: str, year: int) -> tuple[str, int]:
    """Return (crop_name, crop_code) for the dominant crop of field_id in year."""
    df = pd.read_csv(cdl_path)
    if df.empty:
        return ("Unknown", 0)
    mask_field = df["field_id"].astype(str) == str(field_id)
    mask_year = df["year"].astype(int) == int(year)
    subset = df.loc[mask_field & mask_year].copy()
    if subset.empty:
        return ("Unknown", 0)
    subset = subset.sort_values("pct", ascending=False)
    top = subset.iloc[0]
    crop_name = str(top.get("crop_name", "Unknown"))
    crop_code = int(top.get("crop_code", 0))
    return (crop_name, crop_code)


# ---------------------------------------------------------------------------
# Sentinel NDVI extraction
# ---------------------------------------------------------------------------
def _collect_sentinel_scenes(field_slug: str, grower: str, farm: str, year: int) -> list[dict[str, Any]]:
    manifest_path = _field_satellite_dir(grower, farm, field_slug) / "sentinel" / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes: list[dict[str, Any]] = []
    for entry in manifest.get("years", []):
        if entry.get("year") != year:
            continue
        for scene in entry.get("scenes", []):
            ndvi_tif = scene.get("ndvi_tif")
            if not ndvi_tif:
                continue
            ndvi_path = _RUNTIME_BASE / str(ndvi_tif)
            if ndvi_path.exists():
                scenes.append({
                    "scene_date": scene["scene_date"],
                    "ndvi_path": ndvi_path,
                    "cloud_cover": scene.get("cloud_cover", 999.0),
                })
    return scenes


def _read_resampled_like(source_path: Path, reference_path: Path, resampling: Resampling) -> np.ndarray:
    with rasterio.open(reference_path) as ref_src, rasterio.open(source_path) as src:
        destination = np.full((ref_src.height, ref_src.width), np.nan, dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_src.transform,
            dst_crs=ref_src.crs,
            resampling=resampling,
        )
    return destination


def _masked_ndvi_mean(ndvi_path: Path, boundary_path: Path, cdl_raster: Path, crop_code: int) -> float | None:
    """Compute CDL-masked mean NDVI for a single scene."""
    boundary = gpd.read_file(boundary_path)
    with rasterio.open(ndvi_path) as src:
        boundary_proj = boundary.to_crs(src.crs)
        ndvi_array = src.read(1).astype("float32")
        field_mask = rasterio.features.geometry_mask(
            boundary_proj.geometry,
            transform=src.transform,
            invert=True,
            out_shape=(src.height, src.width),
        )

    cdl_array = _read_resampled_like(cdl_raster, ndvi_path, resampling=Resampling.nearest)
    valid_mask = (
        field_mask
        & np.isfinite(ndvi_array)
        & np.isfinite(cdl_array)
        & (np.rint(cdl_array).astype("int32") == crop_code)
    )
    values = ndvi_array[valid_mask]
    if values.size == 0:
        return None
    return float(np.nanmean(values))


# ---------------------------------------------------------------------------
# Weather metrics
# ---------------------------------------------------------------------------
def _c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def _load_weather(weather_path: Path, year: int) -> pd.DataFrame:
    df = pd.read_csv(weather_path, parse_dates=["date"])
    df["year"] = df["date"].dt.year
    df = df[df["year"] == year].copy()
    # Convert temperatures from Celsius to Fahrenheit
    for col in ["T2M", "T2M_MAX", "T2M_MIN"]:
        if col in df.columns:
            df[col] = df[col].apply(_c_to_f)
    # Convert precipitation from mm to inches
    if "PRECTOTCORR" in df.columns:
        df["PRECTOTCORR_in"] = df["PRECTOTCORR"] / 25.4
    df["doy"] = df["date"].dt.dayofyear
    return df


def _compute_gdd_series(df: pd.DataFrame, base: float = 50.0, cap: float = 86.0) -> pd.Series:
    tmin = df["T2M_MIN"].clip(lower=base, upper=cap)
    tmax = df["T2M_MAX"].clip(lower=base, upper=cap)
    tmean = (tmin + tmax) / 2.0
    gdd = (tmean - base).clip(lower=0.0)
    return gdd


# ---------------------------------------------------------------------------
# 5-year reference stats
# ---------------------------------------------------------------------------
def _build_reference_stats(
    grower: str, farm: str, field: str, target_year: int, crop_code: int, args: argparse.Namespace
) -> dict[str, Any] | None:
    """Build 5-year reference stats from historical daily_weather and NDVI scenes."""
    ref_years = [y for y in range(target_year - 5, target_year) if y != target_year]
    if not ref_years:
        return None

    weather_path = _field_weather_path(grower, farm, field)
    if not weather_path.exists():
        return None

    weather_frames: list[pd.DataFrame] = []
    for y in ref_years:
        wf = _load_weather(weather_path, y)
        if not wf.empty:
            weather_frames.append(wf)
    if not weather_frames:
        return None

    all_weather = pd.concat(weather_frames, ignore_index=True)

    # Reference GDD
    all_weather["gdd"] = _compute_gdd_series(all_weather, base=args.gdd_base, cap=args.gdd_cap)
    gdd_by_doy = all_weather.groupby("doy")["gdd"].mean().cumsum()

    # Reference precip
    precip_by_doy = all_weather.groupby("doy")["PRECTOTCORR_in"].mean()
    season_precip = all_weather.groupby(all_weather["date"].dt.year)["PRECTOTCORR_in"].sum()

    # Reference heat stress
    heat_by_year = all_weather.groupby(all_weather["date"].dt.year).apply(
        lambda g: int((g["T2M_MAX"] > args.heat_stress_threshold).sum())
    )

    # Reference NDVI peak DOY
    peak_doys: list[int] = []
    for y in ref_years:
        scenes = _collect_sentinel_scenes(field, grower, farm, y)
        cdl_raster = _resolve_cdl_raster(y)
        if not scenes or cdl_raster is None:
            continue
        boundary_path = _field_boundary_path(grower, farm, field)
        rows = []
        for s in scenes:
            mean_ndvi = _masked_ndvi_mean(s["ndvi_path"], boundary_path, cdl_raster, crop_code)
            if mean_ndvi is not None:
                doy = pd.Timestamp(s["scene_date"]).dayofyear
                rows.append({"doy": doy, "mean_ndvi": mean_ndvi})
        if rows:
            df_ndvi = pd.DataFrame(rows)
            peak_doy = int(df_ndvi.loc[df_ndvi["mean_ndvi"].idxmax(), "doy"])
            peak_doys.append(peak_doy)

    return {
        "avg_peak_ndvi_doy": int(np.mean(peak_doys)) if peak_doys else None,
        "avg_season_precip_in": float(season_precip.mean()) if not season_precip.empty else None,
        "avg_heat_stress_days": float(heat_by_year.mean()) if not heat_by_year.empty else None,
        "avg_final_gdd": float(gdd_by_doy.iloc[-1]) if not gdd_by_doy.empty else None,
        "gdd_by_doy": gdd_by_doy,
        "precip_by_doy": precip_by_doy,
    }


# ---------------------------------------------------------------------------
# Dashboard rendering
# ---------------------------------------------------------------------------
def _smooth_loess(x: np.ndarray, y: np.ndarray, frac: float = 0.3) -> np.ndarray:
    try:
        import statsmodels.api as sm
        lowess = sm.nonparametric.lowess(y, x, frac=frac)
        return lowess[:, 1]
    except Exception:
        # Fallback to simple rolling mean
        s = pd.Series(y, index=x).sort_index()
        return s.rolling(window=3, min_periods=1, center=True).mean().values


def _render_dashboard(
    scenes_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    ref_stats: dict[str, Any] | None,
    crop_name: str,
    field_slug: str,
    year: int,
    args: argparse.Namespace,
) -> plt.Figure:
    fig = plt.figure(figsize=(14, 16))
    fig.patch.set_facecolor("#fafaf9")
    gs = fig.add_gridspec(5, 1, height_ratios=[0.12, 1.0, 1.0, 1.0, 1.0], hspace=0.22)

    # Title / stats box
    title_ax = fig.add_subplot(gs[0, 0])
    title_ax.axis("off")

    # Compute current-year metrics
    weather_df["gdd"] = _compute_gdd_series(weather_df, base=args.gdd_base, cap=args.gdd_cap)
    weather_df["cum_gdd"] = weather_df["gdd"].cumsum()
    season_precip = float(weather_df["PRECTOTCORR_in"].sum())
    heat_days = int((weather_df["T2M_MAX"] > args.heat_stress_threshold).sum())
    final_gdd = float(weather_df["cum_gdd"].iloc[-1])

    peak_ndvi = None
    peak_doy = None
    if not scenes_df.empty:
        peak_idx = scenes_df["mean_ndvi"].idxmax()
        peak_ndvi = float(scenes_df.loc[peak_idx, "mean_ndvi"])
        peak_doy = int(scenes_df.loc[peak_idx, "doy"])

    # Build caption lines
    lines = [f"{year} Season — {crop_name}  |  Field: {field_slug}"]
    stats_line = f"Peak NDVI: {peak_ndvi:.3f} on DOY {peak_doy}" if peak_ndvi else "Peak NDVI: N/A"
    stats_line += f"  |  Precip: {season_precip:.1f} in"
    stats_line += f"  |  Heat stress days (>{args.heat_stress_threshold}°F): {heat_days}"
    stats_line += f"  |  Final GDD: {final_gdd:.0f} °F·day"
    lines.append(stats_line)

    # Heuristic callouts vs 5-year reference
    callouts: list[str] = []
    if ref_stats:
        if peak_doy and ref_stats.get("avg_peak_ndvi_doy"):
            delta = peak_doy - ref_stats["avg_peak_ndvi_doy"]
            if abs(delta) > 7:
                direction = "later" if delta > 0 else "earlier"
                callouts.append(
                    f"• Peak NDVI arrived ~{abs(delta)} days {direction} than the 5-yr avg (DOY {ref_stats['avg_peak_ndvi_doy']})."
                )
        if ref_stats.get("avg_season_precip_in"):
            ratio = season_precip / ref_stats["avg_season_precip_in"]
            if ratio < 0.8:
                callouts.append(f"• Drier-than-average season ({ratio:.0%} of 5-yr avg).")
            elif ratio > 1.2:
                callouts.append(f"• Wetter-than-average season ({ratio:.0%} of 5-yr avg).")
        if ref_stats.get("avg_heat_stress_days"):
            delta_heat = heat_days - ref_stats["avg_heat_stress_days"]
            if delta_heat > 3:
                callouts.append(f"• Above-normal heat stress (+{delta_heat:.0f} days vs. 5-yr avg).")
        if ref_stats.get("avg_final_gdd"):
            ratio_gdd = final_gdd / ref_stats["avg_final_gdd"]
            if ratio_gdd < 0.9:
                callouts.append(f"• Cool season: final GDD {ratio_gdd:.0%} of 5-yr avg.")
            elif ratio_gdd > 1.1:
                callouts.append(f"• Warm season: final GDD {ratio_gdd:.0%} of 5-yr avg.")
    else:
        callouts.append("• 5-year reference data unavailable for comparison.")

    lines.append("  ".join(callouts) if callouts else "")

    title_ax.text(
        0.5, 0.95, lines[0], transform=title_ax.transAxes,
        fontsize=16, fontweight="bold", color="#0f172a", ha="center", va="top",
    )
    title_ax.text(
        0.5, 0.55, lines[1], transform=title_ax.transAxes,
        fontsize=10.5, color="#334155", ha="center", va="top",
    )
    if len(lines) > 2 and lines[2]:
        title_ax.text(
            0.5, 0.18, lines[2], transform=title_ax.transAxes,
            fontsize=9.5, color="#475569", ha="center", va="top", wrap=True,
        )

    # Panel 1: NDVI
    ax_ndvi = fig.add_subplot(gs[1, 0])
    ax_ndvi.set_facecolor("#ffffff")
    ax_ndvi.grid(True, alpha=0.25)
    ax_ndvi.set_ylabel("NDVI", fontsize=11)
    ax_ndvi.set_title("Sentinel NDVI (CDL-masked mean)", fontsize=12, fontweight="bold", loc="left")
    ax_ndvi.tick_params(axis="both", labelsize=9)
    ax_ndvi.set_xlim(args.planting_doy, 320)
    ax_ndvi.set_ylim(-0.1, 1.0)

    if not scenes_df.empty:
        ax_ndvi.scatter(
            scenes_df["doy"], scenes_df["mean_ndvi"],
            color="#0f766e", s=55, zorder=3, edgecolors="white", linewidths=0.8,
        )
        if len(scenes_df) >= 3:
            smooth_y = _smooth_loess(scenes_df["doy"].values, scenes_df["mean_ndvi"].values)
            ax_ndvi.plot(scenes_df["doy"], smooth_y, color="#0f766e", linewidth=2.0, alpha=0.7, zorder=2)
        if peak_doy:
            ax_ndvi.axvline(x=peak_doy, color="#ea580c", linestyle="--", alpha=0.6, zorder=1)
            ax_ndvi.text(
                peak_doy + 2, 0.92, f"Peak\nDOY {peak_doy}",
                fontsize=8, color="#ea580c", va="top",
            )
    else:
        ax_ndvi.text(0.5, 0.5, "No Sentinel NDVI scenes available", ha="center", va="center",
                     transform=ax_ndvi.transAxes, color="#64748b", fontsize=10)

    # Panel 2: Precipitation
    ax_precip = fig.add_subplot(gs[2, 0])
    ax_precip.set_facecolor("#ffffff")
    ax_precip.grid(True, alpha=0.25)
    ax_precip.set_ylabel("Precipitation (in)", fontsize=11)
    ax_precip.set_title("Daily Precipitation", fontsize=12, fontweight="bold", loc="left")
    ax_precip.tick_params(axis="both", labelsize=9)
    ax_precip.set_xlim(args.planting_doy, 320)
    ax_precip.set_ylim(0, max(weather_df["PRECTOTCORR_in"].max() * 1.2, 0.5))

    if not weather_df.empty:
        ax_precip.bar(weather_df["doy"], weather_df["PRECTOTCORR_in"], color="#2563eb", alpha=0.6, width=0.8)
        roll7 = weather_df.set_index("doy")["PRECTOTCORR_in"].rolling(7, min_periods=1).mean().reindex(range(60, 321), fill_value=0)
        ax_precip.plot(roll7.index, roll7.values, color="#1e40af", linewidth=1.5, alpha=0.8)
    else:
        ax_precip.text(0.5, 0.5, "No weather data", ha="center", va="center",
                       transform=ax_precip.transAxes, color="#64748b", fontsize=10)

    # Panel 3: Temperature
    ax_temp = fig.add_subplot(gs[3, 0])
    ax_temp.set_facecolor("#ffffff")
    ax_temp.grid(True, alpha=0.25)
    ax_temp.set_ylabel("Temperature (°F)", fontsize=11)
    ax_temp.set_title("Temperature Extremes", fontsize=12, fontweight="bold", loc="left")
    ax_temp.tick_params(axis="both", labelsize=9)
    ax_temp.set_xlim(args.planting_doy, 320)

    if not weather_df.empty:
        tmin = weather_df.set_index("doy")["T2M_MIN"].reindex(range(60, 321))
        tmax = weather_df.set_index("doy")["T2M_MAX"].reindex(range(60, 321))
        tmean = weather_df.set_index("doy")["T2M"].reindex(range(60, 321))
        doy_range = tmin.index.values
        ax_temp.fill_between(doy_range, tmin.values, tmax.values, color="#fca5a5", alpha=0.35, label="Min–Max")
        ax_temp.plot(doy_range, tmean.values, color="#dc2626", linewidth=1.2, label="Mean")
        ax_temp.axhline(y=args.heat_stress_threshold, color="#ea580c", linestyle="--", alpha=0.5, linewidth=1.0)
        ax_temp.set_ylim(tmin.min() * 0.95, tmax.max() * 1.05)
        ax_temp.legend(loc="upper left", fontsize=8)
    else:
        ax_temp.text(0.5, 0.5, "No weather data", ha="center", va="center",
                     transform=ax_temp.transAxes, color="#64748b", fontsize=10)

    # Panel 4: Cumulative GDD
    ax_gdd = fig.add_subplot(gs[4, 0])
    ax_gdd.set_facecolor("#ffffff")
    ax_gdd.grid(True, alpha=0.25)
    ax_gdd.set_xlabel("Day of Year", fontsize=11)
    ax_gdd.set_ylabel("Cumulative GDD (°F·day)", fontsize=11)
    ax_gdd.set_title(f"Cumulative GDD (base {args.gdd_base}°F, cap {args.gdd_cap}°F)",
                     fontsize=12, fontweight="bold", loc="left")
    ax_gdd.tick_params(axis="both", labelsize=9)
    ax_gdd.set_xlim(args.planting_doy, 320)

    if not weather_df.empty:
        gdd_series = weather_df.set_index("doy")["cum_gdd"].reindex(range(60, 321))
        ax_gdd.plot(gdd_series.index, gdd_series.values, color="#7c3aed", linewidth=2.0, label=f"{year}")
        if ref_stats and ref_stats.get("gdd_by_doy") is not None:
            ref_gdd = ref_stats["gdd_by_doy"].reindex(range(60, 321), fill_value=0)
            ax_gdd.plot(ref_gdd.index, ref_gdd.values, color="#a78bfa", linewidth=1.5,
                        linestyle="--", label="5-yr avg", alpha=0.8)
        ax_gdd.legend(loc="upper left", fontsize=8)
        ax_gdd.set_ylim(0, max(gdd_series.max() * 1.1, 500))
    else:
        ax_gdd.text(0.5, 0.5, "No weather data", ha="center", va="center",
                    transform=ax_gdd.transAxes, color="#64748b", fontsize=10)

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("DATA_PIPELINE_DATA_ROOT"),
                        help="Runtime data root (defaults to DATA_PIPELINE_DATA_ROOT env var)")
    parser.add_argument("--grower-slug", required=True)
    parser.add_argument("--farm-slug", required=True)
    parser.add_argument("--field-slug", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--gdd-base", type=float, default=50.0)
    parser.add_argument("--gdd-cap", type=float, default=86.0)
    parser.add_argument("--heat-stress-threshold", type=float, default=95.0)
    parser.add_argument("--planting-doy", type=int, default=90,
                        help="Day-of-year to start growing-season axis (default 90 = Mar 31)")
    parser.add_argument("--output-path", default=None,
                        help="Override output PNG path")
    parser.add_argument("--state-fips", default="19",
                        help="State FIPS for CDL raster lookup (default 19 = Iowa)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global _DATA_ROOT, _RUNTIME_BASE, _GROWERS_ROOT, _SHARED_ROOT
    if args.data_root:
        _DATA_ROOT = Path(args.data_root)
        _RUNTIME_BASE = _DATA_ROOT / "data-pipeline"
        _GROWERS_ROOT = _RUNTIME_BASE / "growers"
        _SHARED_ROOT = _RUNTIME_BASE / "shared"

    grower, farm, field = args.grower_slug, args.farm_slug, args.field_slug
    year = args.year

    # --- Load inputs ---
    weather_path = _field_weather_path(grower, farm, field)
    boundary_path = _field_boundary_path(grower, farm, field)
    cdl_comp_path = _farm_cdl_preferred_full_composition_path(grower, farm)

    if not weather_path.exists():
        print(f"ERROR: Weather file not found: {weather_path}")
        sys.exit(1)
    if not boundary_path.exists():
        print(f"ERROR: Boundary file not found: {boundary_path}")
        sys.exit(1)
    if not cdl_comp_path.exists():
        print(f"ERROR: CDL composition file not found: {cdl_comp_path}")
        sys.exit(1)

    # Identify dominant crop
    # Need field_id from boundary
    boundary_gdf = gpd.read_file(boundary_path)
    field_id = str(boundary_gdf.iloc[0].get("field_id", field))
    crop_name, crop_code = _dominant_crop_for_field_year(cdl_comp_path, field_id, year)
    print(f"Field {field} ({field_id}) | {year} | Dominant crop: {crop_name} (code {crop_code})")

    # Load weather
    weather_df = _load_weather(weather_path, year)
    print(f"Loaded {len(weather_df)} daily weather records for {year}")

    # Collect Sentinel scenes
    scenes = _collect_sentinel_scenes(field, grower, farm, year)
    print(f"Found {len(scenes)} Sentinel scenes for {year}")

    # Compute CDL-masked NDVI means
    cdl_raster = _resolve_cdl_raster(year, args.state_fips)
    scene_rows: list[dict[str, Any]] = []
    if cdl_raster and cdl_raster.exists() and crop_code > 0:
        for s in scenes:
            mean_ndvi = _masked_ndvi_mean(s["ndvi_path"], boundary_path, cdl_raster, crop_code)
            if mean_ndvi is not None:
                doy = pd.Timestamp(s["scene_date"]).dayofyear
                scene_rows.append({
                    "scene_date": s["scene_date"],
                    "doy": doy,
                    "mean_ndvi": mean_ndvi,
                    "cloud_cover": s["cloud_cover"],
                })
                print(f"  DOY {doy}: NDVI {mean_ndvi:.3f}")
    else:
        print(f"  WARNING: CDL raster unavailable or crop code is zero; skipping NDVI masking")
        # Fallback: unmasked mean
        for s in scenes:
            with rasterio.open(s["ndvi_path"]) as src:
                boundary_proj = gpd.read_file(boundary_path).to_crs(src.crs)
                clipped, _ = mask(src, boundary_proj.geometry, crop=True, filled=False)
            array = np.ma.filled(clipped[0], np.nan).astype(float)
            valid = array[np.isfinite(array)]
            if valid.size > 0:
                doy = pd.Timestamp(s["scene_date"]).dayofyear
                scene_rows.append({
                    "scene_date": s["scene_date"],
                    "doy": doy,
                    "mean_ndvi": float(np.nanmean(valid)),
                    "cloud_cover": s["cloud_cover"],
                })

    scenes_df = pd.DataFrame(scene_rows)

    # Build 5-year reference
    print("Building 5-year reference stats...")
    ref_stats = _build_reference_stats(grower, farm, field, year, crop_code, args)
    if ref_stats:
        print(f"  Avg peak NDVI DOY: {ref_stats.get('avg_peak_ndvi_doy')}")
        print(f"  Avg season precip: {ref_stats.get('avg_season_precip_in'):.1f} in")
        print(f"  Avg heat stress days: {ref_stats.get('avg_heat_stress_days'):.1f}")
        print(f"  Avg final GDD: {ref_stats.get('avg_final_gdd'):.0f}")

    # Render
    fig = _render_dashboard(scenes_df, weather_df, ref_stats, crop_name, field, year, args)

    if args.output_path:
        output_path = Path(args.output_path)
    else:
        output_path = _field_reports_dir(grower, farm, field) / f"{field}_{year}_season_dashboard.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"\nDashboard saved: {output_path}")


if __name__ == "__main__":
    main()
