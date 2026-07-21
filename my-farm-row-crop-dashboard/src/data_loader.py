#!/usr/bin/env python3
"""Unified data ingestion for the Row Crop Intelligence Dashboard.

Reads field boundaries, weather, CDL composition, and SSURGO soil data
from the approved DATA_PIPELINE_DATA_ROOT runtime tree. Falls back to
sample/example data in the my-farm-advisor skill tree when runtime
data is not available.

All paths follow the conventions established in the data-pipeline runtime.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_DASHBOARD_ROOT = _HERE.parent
_REPO_ROOT = Path("/tmp/my-farm-advisor-skills")

_SAMPLE_DIR = _REPO_ROOT / "my-farm-advisor"


def _runtime_root() -> Path:
    raw = os.environ.get("DATA_PIPELINE_DATA_ROOT", "")
    if raw:
        return Path(raw) / "data-pipeline"
    return Path("/tmp/my-farm-advisor-runtime") / "data-pipeline"


def _sample_soil_path() -> Path:
    return _SAMPLE_DIR / "soil" / "ssurgo-soil" / "examples" / "soil_data_10_fields.csv"


def _sample_boundary_path(state: str) -> Path:
    return (
        _SAMPLE_DIR
        / "field-management"
        / "field-boundaries"
        / "examples"
        / f"real_10_fields_{state.lower()}.geojson"
    )


def _sample_weather_path() -> Path:
    return (
        _SAMPLE_DIR
        / "weather"
        / "nasa-power-weather"
        / "examples"
        / "sample_weather_2fields_2020_2024.csv"
    )


def _sample_cdl_path() -> Path:
    return _SAMPLE_DIR / "soil" / "cdl-cropland" / "examples" / "sample_cdl_2_fields.csv"


def load_field_boundaries(grower_slug: str, farm_slug: str = "dekalb-demo-farm") -> pd.DataFrame:
    runtime_path = _runtime_root() / "growers" / grower_slug / "farms" / farm_slug / "boundary" / "field_boundaries.geojson"
    if runtime_path.exists():
        try:
            import geopandas as gpd
            gdf = gpd.read_file(runtime_path)
            df = pd.DataFrame(gdf.drop(columns="geometry") if "geometry" in gdf.columns else gdf)
            if "geometry" in gdf.columns:
                df["geometry"] = gdf["geometry"]
            return df
        except Exception:
            pass

    fallback = _sample_boundary_path("illinois")
    if fallback.exists():
        try:
            import geopandas as gpd
            gdf = gpd.read_file(fallback)
            df = pd.DataFrame(gdf.drop(columns="geometry") if "geometry" in gdf.columns else gdf)
            if "geometry" in gdf.columns:
                df["geometry"] = gdf["geometry"]
            return df
        except Exception:
            pass

    return _generate_synthetic_boundaries()


def _generate_synthetic_boundaries() -> pd.DataFrame:
    np.random.seed(42)
    n = 10
    field_ids = [f"osm-{1062497612 + i}" for i in range(n)]
    df = pd.DataFrame({
        "field_id": field_ids,
        "acres": np.round(np.random.uniform(40, 200, n), 1),
        "state": "Illinois",
        "county": "DeKalb",
    })
    try:
        from shapely.geometry import Point
        centroids = [Point(-88.8 + np.random.uniform(-0.3, 0.3), 41.9 + np.random.uniform(-0.2, 0.2)) for _ in range(n)]
        import geopandas as gpd
        df = gpd.GeoDataFrame(df, geometry=centroids, crs="EPSG:4326")
    except ImportError:
        pass
    return df


def load_weather(grower_slug: str, farm_slug: str = "dekalb-demo-farm",
                 field_slug: str | None = None) -> pd.DataFrame:
    if field_slug:
        runtime_path = (
            _runtime_root() / "growers" / grower_slug / "farms" / farm_slug
            / "fields" / field_slug / "weather" / "daily_weather.csv"
        )
        if runtime_path.exists():
            return pd.read_csv(runtime_path, parse_dates=["date"])

    fallback = _sample_weather_path()
    if fallback.exists():
        return pd.read_csv(fallback, parse_dates=["date"])

    return _generate_synthetic_weather()


def _generate_synthetic_weather() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2022-01-01", "2022-12-31", freq="D")
    base_tmean = 50 + 25 * np.sin((dates.dayofyear - 105) * np.pi / 182.5)
    tmean = base_tmean + np.random.normal(0, 5, len(dates))
    precip = np.random.exponential(0.1, len(dates))
    precip[precip < 0.005] = 0
    precip[np.random.random(len(dates)) < 0.7] = 0
    return pd.DataFrame({
        "date": dates,
        "T2M": tmean,
        "T2M_MAX": tmean + np.random.uniform(3, 12, len(dates)),
        "T2M_MIN": tmean - np.random.uniform(3, 12, len(dates)),
        "PRECTOTCORR": precip * 25.4,
        "doy": dates.dayofyear,
    })


def load_cdl_composition(grower_slug: str, farm_slug: str = "dekalb-demo-farm") -> pd.DataFrame:
    runtime_dir = _runtime_root() / "growers" / grower_slug / "farms" / farm_slug / "derived" / "tables"
    if runtime_dir.exists():
        for csv_file in sorted(runtime_dir.glob("*_cdl_*_full_composition.csv")):
            try:
                return pd.read_csv(csv_file)
            except Exception:
                continue

    fallback = _sample_cdl_path()
    if fallback.exists():
        return pd.read_csv(fallback)

    return _generate_synthetic_cdl()


def _generate_synthetic_cdl() -> pd.DataFrame:
    np.random.seed(42)
    n_fields = 10
    records = []
    for i in range(n_fields):
        for year in [2021, 2022, 2023, 2024, 2025]:
            fld = f"osm-{1062497612 + i}"
            soy = np.random.uniform(0.4, 0.9)
            corn = 1.0 - soy - np.random.uniform(0, 0.1)
            other = 1.0 - soy - corn
            records.append({"field_id": fld, "year": year, "crop_name": "Soybeans", "crop_code": 5, "pct": round(soy * 100, 1)})
            records.append({"field_id": fld, "year": year, "crop_name": "Corn", "crop_code": 1, "pct": round(corn * 100, 1)})
            if other > 0:
                records.append({"field_id": fld, "year": year, "crop_name": "Other", "crop_code": 0, "pct": round(other * 100, 1)})
    return pd.DataFrame(records)


def _default_field_ids() -> list[str]:
    return [f"osm-{1062497612 + i}" for i in range(10)]


def _inject_problem_field(df: pd.DataFrame) -> pd.DataFrame:
    """Add a synthetic problem field for action alert demonstration.

    Creates a deliberately challenging soil profile to showcase
    the dashboard's alert and recommendation capabilities.
    """
    problem_id = "demo-problem-field-01"
    records = [
        {"field_id": problem_id, "mukey": 999999, "muname": "Sparta loamy fine sand, low OM",
         "compname": "Sparta", "comppct_r": 80, "drainagecl": "Excessively drained",
         "hzdept_r": 0, "hzdepb_r": 15, "om_r": 1.2, "ph1to1h2o_r": 5.4, "awc_r": 0.08,
         "claytotal_r": 8, "sandtotal_r": 78, "silttotal_r": 14, "dbthirdbar_r": 1.45, "cec7_r": 8.0},
        {"field_id": problem_id, "mukey": 999999, "muname": "Sparta loamy fine sand, low OM",
         "compname": "Sparta", "comppct_r": 80, "drainagecl": "Excessively drained",
         "hzdept_r": 15, "hzdepb_r": 30, "om_r": 0.8, "ph1to1h2o_r": 5.2, "awc_r": 0.06,
         "claytotal_r": 6, "sandtotal_r": 82, "silttotal_r": 12, "dbthirdbar_r": 1.50, "cec7_r": 5.0},
        {"field_id": problem_id, "mukey": 999999, "muname": "Sparta loamy fine sand, low OM",
         "compname": "Sparta", "comppct_r": 80, "drainagecl": "Excessively drained",
         "hzdept_r": 30, "hzdepb_r": 60, "om_r": 0.3, "ph1to1h2o_r": 5.0, "awc_r": 0.04,
         "claytotal_r": 4, "sandtotal_r": 88, "silttotal_r": 8, "dbthirdbar_r": 1.55, "cec7_r": 3.0},
    ]
    problem_df = pd.DataFrame(records)
    if df.empty:
        return problem_df
    return pd.concat([df, problem_df], ignore_index=True)


def load_soil_data(grower_slug: str | None = None, farm_slug: str | None = None,
                   field_ids: list[str] | None = None) -> pd.DataFrame:
    if field_ids is None:
        field_ids = []

    runtime_dir = _runtime_root() / "growers" / (grower_slug or "") / "farms" / (farm_slug or "")
    if grower_slug and farm_slug and runtime_dir.exists():
        for csv_file in sorted(runtime_dir.rglob("*ssurgo*.csv")):
            try:
                df = pd.read_csv(csv_file)
                if "field_id" in df.columns:
                    return _inject_problem_field(df)
            except Exception:
                continue

    fallback = _sample_soil_path()
    if fallback.exists():
        df = pd.read_csv(fallback)
        if field_ids:
            matched = df[df["field_id"].astype(str).isin(field_ids)]
            if not matched.empty:
                return _inject_problem_field(matched)
        return _inject_problem_field(df)

    return _inject_problem_field(_generate_synthetic_soil(field_ids or _default_field_ids()))


def _generate_synthetic_soil(field_ids: list[str]) -> pd.DataFrame:
    np.random.seed(42)
    ids = field_ids or [f"osm-{1062497612 + i}" for i in range(10)]
    records = []
    for fid in ids:
        for depth_top, depth_bot in [(0, 15), (15, 30), (30, 60)]:
            records.append({
                "field_id": fid,
                "mukey": np.random.randint(100000, 999999),
                "muname": np.random.choice(["Drummer silty clay loam", "Flanagan silt loam", "Sable silty clay loam", "Ipava silt loam"]),
                "compname": np.random.choice(["Drummer", "Flanagan", "Sable", "Ipava"]),
                "comppct_r": np.random.choice([45, 35, 20, 55, 40, 30]),
                "drainagecl": np.random.choice(["Moderately well drained", "Somewhat poorly drained", "Poorly drained"]),
                "hzdept_r": depth_top,
                "hzdepb_r": depth_bot,
                "om_r": np.random.uniform(1.0, 5.0),
                "ph1to1h2o_r": np.random.uniform(5.0, 7.5),
                "awc_r": np.random.uniform(0.08, 0.22),
                "claytotal_r": np.random.uniform(15, 45),
                "sandtotal_r": np.random.uniform(5, 70),
                "silttotal_r": np.random.uniform(20, 70),
                "dbthirdbar_r": np.random.uniform(1.2, 1.8),
                "cec7_r": np.random.uniform(8, 30),
            })
    return pd.DataFrame(records)


def discover_fields(grower_slug: str, farm_slug: str = "dekalb-demo-farm") -> list[dict[str, Any]]:
    runtime_fields_dir = _runtime_root() / "growers" / grower_slug / "farms" / farm_slug / "fields"
    if runtime_fields_dir.exists():
        fields_list: list[dict[str, Any]] = []
        for field_dir in sorted(runtime_fields_dir.iterdir()):
            if field_dir.is_dir():
                boundary = field_dir / "boundary" / "field_boundary.geojson"
                fields_list.append({
                    "field_slug": field_dir.name,
                    "has_boundary": boundary.exists(),
                })
        if fields_list:
            return fields_list

    try:
        boundaries = load_field_boundaries(grower_slug, farm_slug)
        if "field_id" in boundaries.columns:
            field_list = [
                {"field_slug": str(fid), "has_boundary": True}
                for fid in boundaries["field_id"].tolist()
            ]
            field_list.append({"field_slug": "demo-problem-field-01", "has_boundary": False})
            return field_list
    except Exception:
        pass

    default = [{"field_slug": f"osm-{1062497612 + i}", "has_boundary": True} for i in range(10)]
    default.append({"field_slug": "demo-problem-field-01", "has_boundary": False})
    return default


def build_grower_dataset(grower_slug: str, farm_slug: str = "dekalb-demo-farm") -> dict[str, Any]:
    """Assemble the complete grower-level dataset for the dashboard.

    Returns a dictionary containing:
        - boundaries: DataFrame with field boundaries
        - weather: DataFrame with daily weather
        - cdl: DataFrame with CDL crop composition
        - soil: DataFrame with SSURGO soil properties (depth/horizon aware)
        - fields: list of field metadata
        - grower_slug, farm_slug
    """
    fields = discover_fields(grower_slug, farm_slug)
    field_ids = [f["field_slug"] for f in fields]

    dataset: dict[str, Any] = {
        "grower_slug": grower_slug,
        "farm_slug": farm_slug,
        "fields": fields,
        "boundaries": load_field_boundaries(grower_slug, farm_slug),
        "weather": load_weather(grower_slug, farm_slug),
        "cdl": load_cdl_composition(grower_slug, farm_slug),
        "soil": load_soil_data(grower_slug, farm_slug, field_ids),
    }
    return dataset
