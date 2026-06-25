#!/usr/bin/env python3
"""Fetch real OSM field boundaries for IL, IA, NE and save as GeoJSON.

Usage:
    python scripts/fetch_real_boundaries.py

Output:
    field-management/field-boundaries/examples/real_10_fields_*.geojson
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

import requests
from shapely.geometry import Polygon

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BATCH_DELAY = 3.0
RATE_LIMIT_DELAY = 15.0

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
EXAMPLES_DIR = REPO_ROOT / "my-farm-advisor" / "field-management" / "field-boundaries" / "examples"


def query_bbox(south: float, west: float, north: float, east: float) -> list[dict]:
    query = (
        f'[out:json][timeout:120];'
        f'(way["landuse"="farmland"]({south},{west},{north},{east}););'
        f'out geom;'
    )
    for attempt in range(3):
        try:
            r = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=180,
                headers={"User-Agent": "MyFarmAdvisor/1.0"},
            )
            if r.status_code == 200:
                return r.json().get("elements", [])
            if r.status_code == 429:
                print(f"  Rate limited (429), waiting {RATE_LIMIT_DELAY}s...")
                time.sleep(RATE_LIMIT_DELAY * (attempt + 1))
                continue
            print(f"  HTTP {r.status_code}, retrying...")
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            print(f"  Error: {e}, retrying...")
            time.sleep(5 * (attempt + 1))
    return []


def osm_element_to_feature(element: dict, state_fips: str) -> dict | None:
    if element.get("type") != "way":
        return None
    geom = element.get("geometry", [])
    if len(geom) < 4:
        return None
    ring = [(p["lon"], p["lat"]) for p in geom]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    try:
        polygon = Polygon(ring)
        if not polygon.is_valid or polygon.is_empty or polygon.area == 0:
            return None
    except Exception:
        return None

    field_id = f"osm-{element['id']}"
    area_acres = polygon.area * (111320 ** 2) * abs(math.cos(math.radians(polygon.centroid.y))) / 4046.86
    if area_acres < 25:
        return None
    tags = element.get("tags", {})

    return {
        "type": "Feature",
        "properties": {
            "field_id": field_id,
            "state_fips": state_fips,
            "region": "corn_belt",
            "crop_name": str(tags.get("crop") or tags.get("landuse", "farmland")),
            "source": "OpenStreetMap/Overpass",
            "area_acres": round(area_acres, 2),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    }


def fetch_fields(
    bboxes: list[tuple[float, float, float, float]],
    state_fips: str,
    label: str,
    target: int = 10,
) -> list[dict]:
    seen_ids: set[int] = set()
    features: list[dict] = []

    for i, (s, w, n, e) in enumerate(bboxes):
        print(f"  Querying {label} bbox {i+1}/{len(bboxes)}...")
        elements = query_bbox(s, w, n, e)
        for el in elements:
            if el["id"] in seen_ids:
                continue
            seen_ids.add(el["id"])
            feat = osm_element_to_feature(el, state_fips)
            if feat:
                features.append(feat)
        print(f"    Found {len(elements)} elements, {len(features)} valid fields so far")
        if len(features) >= target * 3:
            print(f"    Collected enough candidates, stopping early")
            break
        time.sleep(BATCH_DELAY)

    if len(features) < target:
        print(f"  WARNING: Only found {len(features)} fields, need {target}")
        return features

    # Sample deterministically: pick largest fields, then random to reach target
    features.sort(key=lambda f: f["properties"]["area_acres"], reverse=True)
    top = features[:target]
    random.seed(42)
    if len(features) > target:
        top = features[:max(target - 2, 6)]
        remaining = [f for f in features if f not in top]
        extra = random.sample(remaining, min(target - len(top), len(remaining)))
        top.extend(extra)
    top.sort(key=lambda f: f["properties"]["field_id"])
    return top


def main():
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Fetching real OSM field boundaries")
    print("=" * 60)
    print()

    # ── Illinois – DeKalb county ──
    il_bboxes = [
        (41.80, -88.90, 41.95, -88.70),
        (41.95, -88.80, 42.10, -88.60),
        (41.70, -88.95, 41.85, -88.75),
        (41.85, -88.70, 42.00, -88.50),
        (41.60, -89.00, 41.80, -88.80),
    ]
    print("Fetching Illinois fields (DeKalb county)...")
    il_fields = fetch_fields(il_bboxes, "17", "IL")
    print(f"  Illinois: {len(il_fields)} fields selected")

    # ── Iowa – Story county ──
    ia_bboxes = [
        (41.85, -93.70, 42.05, -93.40),
        (41.95, -93.50, 42.15, -93.25),
        (41.80, -93.55, 42.00, -93.30),
        (42.00, -93.45, 42.20, -93.20),
        (41.90, -93.65, 42.10, -93.40),
    ]
    print("Fetching Iowa fields (Story county)...")
    ia_fields = fetch_fields(ia_bboxes, "19", "IA")
    print(f"  Iowa: {len(ia_fields)} fields selected")

    # ── Nebraska – Phelps county ──
    ne_bboxes = [
        (40.40, -99.55, 40.60, -99.30),
        (40.30, -99.50, 40.50, -99.25),
        (40.55, -99.40, 40.70, -99.15),
        (40.35, -99.65, 40.50, -99.40),
        (40.50, -99.65, 40.65, -99.40),
    ]
    print("Fetching Nebraska fields (Phelps county)...")
    ne_fields = fetch_fields(ne_bboxes, "31", "NE")
    print(f"  Nebraska: {len(ne_fields)} fields selected")

    # ── Write GeoJSON files ──
    if il_fields:
        path = EXAMPLES_DIR / "real_10_fields_illinois.geojson"
        with open(path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": il_fields}, f, indent=2)
        print(f"\nWritten: {path}")
    else:
        print("\nWARNING: No Illinois fields fetched — keeping existing file")

    if ia_fields:
        path = EXAMPLES_DIR / "real_10_fields_iowa.geojson"
        with open(path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": ia_fields}, f, indent=2)
        print(f"Written: {path}")
    else:
        print("WARNING: No Iowa fields fetched — keeping existing file")

    if ne_fields:
        path = EXAMPLES_DIR / "real_10_fields_nebraska.geojson"
        with open(path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": ne_fields}, f, indent=2)
        print(f"Written: {path}")
    else:
        print("WARNING: No Nebraska fields fetched — keeping existing file")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
