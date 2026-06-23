#!/usr/bin/env python3
"""Generate headlands rings for field boundaries.

Headlands are the border strips around a field that are left unplanted or
used for turning farm machinery. This script:

1. Reads field boundary GeoJSON
2. Reprojects to appropriate UTM zone for accurate metric calculations
3. Calculates full boundary area (m² + acres)
4. Creates a negative buffer (default -21m) to define the inner planted area
5. Differences: full_boundary - inner_buffer = headlands_ring
6. Calculates headlands ring area (m² + acres)
7. Converts headlands ring back to EPSG:4326
8. Writes GeoPackage outputs

Usage:
    python generate_headlands_rings.py --grower-slug iowa-grower --farm-slug iowa-grower-iowa
    python generate_headlands_rings.py --all
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

# Try to find runtime_paths from the active data-pipeline runtime
# Fall back to checkout path for development
_DATA_PIPELINE_LIB = Path("/home/coder/my-farm-advisor-runtime/data-pipeline/src/scripts/lib")
if not (_DATA_PIPELINE_LIB / "runtime_paths.py").exists():
    _DATA_PIPELINE_LIB = Path(__file__).resolve().parents[3] / "data-pipeline" / "src" / "scripts" / "lib"

sys.path.insert(0, str(_DATA_PIPELINE_LIB))
from runtime_paths import resolve_runtime_paths  # noqa: E402

_RUNTIME_PATHS = resolve_runtime_paths()
_REPO = _RUNTIME_PATHS.runtime_base
_GROWERS_ROOT = _REPO / "growers"

# Constants
_SQ_M_TO_ACRES = 4046.8564224  # 1 acre = 4046.8564224 m²
_DEFAULT_BUFFER_M = -21.0


def _determine_utm_epsg(lon: float, lat: float) -> int:
    """Determine UTM EPSG code from WGS84 coordinates."""
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return epsg


def _calculate_area_acres(area_m2: float) -> float:
    """Convert square meters to acres."""
    return area_m2 / _SQ_M_TO_ACRES


def _add_area_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add area_m2 and area_acres columns to a GeoDataFrame."""
    gdf = gdf.copy()
    gdf["area_m2"] = gdf.geometry.area
    gdf["area_acres"] = gdf["area_m2"].apply(_calculate_area_acres)
    return gdf


def _discover_growers() -> list[dict[str, str]]:
    """Discover all growers and farms."""
    results = []
    for grower_dir in sorted(_GROWERS_ROOT.glob("*")):
        if not grower_dir.is_dir():
            continue
        g_slug = grower_dir.name
        farms_dir = grower_dir / "farms"
        if not farms_dir.exists():
            continue
        for farm_dir in sorted(farms_dir.glob("*")):
            if not farm_dir.is_dir():
                continue
            f_slug = farm_dir.name
            farm_name = f_slug.replace("-", " ").title()
            results.append({
                "grower_slug": g_slug,
                "farm_slug": f_slug,
                "farm_name": farm_name,
            })
    return results


def generate_headlands_for_farm(
    grower_slug: str,
    farm_slug: str,
    farm_name: str | None = None,
    buffer_m: float = _DEFAULT_BUFFER_M,
) -> tuple[Path, Path] | None:
    """Generate headlands rings for a single farm.

    Returns:
        Tuple of (headlands_4326_gpkg_path, headlands_utm_gpkg_path)
    """
    boundary_path = _REPO / "growers" / grower_slug / "farms" / farm_slug / "boundary" / "field_boundaries.geojson"
    if not boundary_path.exists():
        print(f"  SKIP {grower_slug}/{farm_slug}: boundary not found")
        return None

    # Read original GeoDataFrame in EPSG:4326
    original_gdf = gpd.read_file(boundary_path)
    if original_gdf.empty:
        print(f"  SKIP {grower_slug}/{farm_slug}: no features")
        return None

    print(f"\n  Processing {grower_slug}/{farm_slug}...")
    print(f"    Fields: {len(original_gdf)}")

    # Determine UTM zone from centroid
    centroid = original_gdf.geometry.union_all().centroid
    utm_epsg = _determine_utm_epsg(centroid.x, centroid.y)
    print(f"    UTM Zone: EPSG:{utm_epsg}")

    # Reproject to UTM working GeoDataFrame
    utm_gdf = original_gdf.to_crs(epsg=utm_epsg)
    print(f"    Reprojected to UTM (EPSG:{utm_epsg})")

    # Calculate full boundary area in UTM
    utm_gdf = _add_area_columns(utm_gdf)
    total_area_ac = utm_gdf["area_acres"].sum()
    print(f"    Full boundary area: {total_area_ac:.2f} acres")

    # Create negative buffer (inner polygon)
    inner_gdf = utm_gdf.copy()
    inner_gdf.geometry = inner_gdf.geometry.buffer(buffer_m)

    # Remove any empty geometries from buffer (fields too small for buffer)
    inner_gdf = inner_gdf[~inner_gdf.geometry.is_empty]
    inner_gdf = inner_gdf[inner_gdf.geometry.area > 0]

    if len(inner_gdf) < len(utm_gdf):
        skipped = len(utm_gdf) - len(inner_gdf)
        print(f"    WARNING: {skipped} field(s) too small for {abs(buffer_m)}m buffer, skipped")

    # Difference: full boundary - inner buffer = headlands ring
    headlands_utm = utm_gdf.copy()
    headlands_utm.geometry = headlands_utm.geometry.difference(
        inner_gdf.geometry.union_all()
    )

    # Remove empty headlands (entire field became buffer)
    headlands_utm = headlands_utm[~headlands_utm.geometry.is_empty]
    headlands_utm = headlands_utm[headlands_utm.geometry.area > 0.1]  # tiny slivers

    if len(headlands_utm) == 0:
        print(f"    WARNING: No headlands rings generated (all fields too small)")
        return None

    # Calculate headlands ring area
    headlands_utm = _add_area_columns(headlands_utm)
    headlands_area_ac = headlands_utm["area_acres"].sum()
    print(f"    Headlands ring area: {headlands_area_ac:.2f} acres")
    print(f"    Headlands % of total: {100 * headlands_area_ac / total_area_ac:.1f}%")

    # Convert headlands ring back to EPSG:4326
    headlands_4326 = headlands_utm.to_crs(epsg=4326)
    print(f"    Converted headlands back to EPSG:4326")

    # Output directory
    out_dir = _REPO / "growers" / grower_slug / "farms" / farm_slug / "derived" / "headlands"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write GeoPackage 1: Headlands in EPSG:4326
    gpkg_4326 = out_dir / f"{farm_slug}_headlands_4326.gpkg"
    headlands_4326.to_file(gpkg_4326, driver="GPKG")
    print(f"    Wrote: {gpkg_4326.name}")

    # Write GeoPackage 2: Headlands in UTM (with full boundary and inner buffer for reference)
    gpkg_utm = out_dir / f"{farm_slug}_headlands_utm.gpkg"

    # Prepare layers
    utm_gdf_out = utm_gdf.copy()
    utm_gdf_out["geometry_type"] = "full_boundary"

    inner_gdf_out = inner_gdf.copy()
    inner_gdf_out["geometry_type"] = "inner_buffer"
    inner_gdf_out = _add_area_columns(inner_gdf_out)

    headlands_utm_out = headlands_utm.copy()
    headlands_utm_out["geometry_type"] = "headlands_ring"

    # Combine for multi-layer GPKG
    combined = gpd.GeoDataFrame(
        pd.concat([utm_gdf_out, inner_gdf_out, headlands_utm_out], ignore_index=True),
        crs=utm_gdf.crs,
    )
    combined.to_file(gpkg_utm, driver="GPKG", layer="headlands_analysis")
    print(f"    Wrote: {gpkg_utm.name} (3 layers: boundary, buffer, headlands)")

    return gpkg_4326, gpkg_utm


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate headlands rings for field boundaries")
    parser.add_argument("--grower-slug", default=None, help="Target grower slug")
    parser.add_argument("--farm-slug", default=None, help="Target farm slug")
    parser.add_argument("--all", action="store_true", help="Process all discovered farms")
    parser.add_argument(
        "--buffer-m",
        type=float,
        default=_DEFAULT_BUFFER_M,
        help=f"Buffer distance in meters (default: {_DEFAULT_BUFFER_M})",
    )
    args = parser.parse_args()

    if args.all:
        farms = _discover_growers()
        if not farms:
            print("No farms discovered")
            sys.exit(1)
        print(f"Processing {len(farms)} farm(s)...")
        for item in farms:
            generate_headlands_for_farm(
                item["grower_slug"],
                item["farm_slug"],
                item["farm_name"],
                buffer_m=args.buffer_m,
            )
        print("\nDone.")
        return

    if not args.grower_slug:
        parser.error("Provide --grower-slug or use --all")

    if args.farm_slug:
        generate_headlands_for_farm(
            args.grower_slug,
            args.farm_slug,
            buffer_m=args.buffer_m,
        )
    else:
        farms = _discover_growers()
        matches = [f for f in farms if f["grower_slug"] == args.grower_slug]
        if not matches:
            print(f"No farms found for grower '{args.grower_slug}'")
            sys.exit(1)
        for item in matches:
            generate_headlands_for_farm(
                item["grower_slug"],
                item["farm_slug"],
                item["farm_name"],
                buffer_m=args.buffer_m,
            )


if __name__ == "__main__":
    # Need pandas for concat
    import pandas as pd

    main()
