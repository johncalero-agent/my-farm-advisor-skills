#!/usr/bin/env python3
"""Generate a lightweight, self-contained interactive HTML web map for a grower/farm.

Usage (single farm):
    python generate_grower_web_map.py --grower-slug iowa-grower --farm-slug iowa-grower-iowa

Usage (all farms):
    python generate_grower_web_map.py --all

Output:
    growers/<grower>/farms/<farm>/derived/reports/<farm>_grower_web_map.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd

_LOCAL_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LOCAL_LIB))

from runtime_paths import resolve_runtime_paths  # noqa: E402

_RUNTIME_PATHS = resolve_runtime_paths()
_REPO = _RUNTIME_PATHS.runtime_base
_GROWERS_ROOT = _REPO / "growers"

# Distinct field colors (Tableau10)
_FIELD_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]


def _discover_growers() -> list[dict[str, str]]:
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


def _extract_first_coords(geometry: dict) -> tuple[float, float]:
    try:
        coords = geometry.get("coordinates", [])
        if geometry.get("type") == "Polygon":
            ring = coords[0]
            lon, lat = ring[0]
            return (lat, lon)
        elif geometry.get("type") == "MultiPolygon":
            ring = coords[0][0]
            lon, lat = ring[0]
            return (lat, lon)
    except Exception:
        pass
    return (40.0, -95.0)


def _generate_html(
    geojson_data: dict,
    *,
    grower_slug: str,
    farm_slug: str,
    farm_name: str,
) -> str:
    features = geojson_data.get("features", [])
    field_count = len(features)

    fields_meta = []
    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = _extract_first_coords(geom)
        fields_meta.append({
            "index": idx,
            "field_id": props.get("field_id", f"field-{idx}"),
            "crop_name": props.get("crop_name", ""),
            "area_acres": round(float(props.get("area_acres", 0)), 2),
            "county_name": props.get("county_name", ""),
            "state_fips": props.get("state_fips", ""),
            "lat": coords[0],
            "lon": coords[1],
            "color": _FIELD_COLORS[idx % len(_FIELD_COLORS)],
        })

    fields_meta_json = json.dumps(fields_meta)
    geojson_json = json.dumps(geojson_data)

    if fields_meta:
        center_lat = sum(f["lat"] for f in fields_meta) / len(fields_meta)
        center_lon = sum(f["lon"] for f in fields_meta) / len(fields_meta)
    else:
        center_lat, center_lon = 40.0, -95.0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{farm_name} — Grower Web Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow: hidden; }}
  #container {{ display: flex; height: 100vh; width: 100vw; }}
  #sidebar {{
    width: 300px;
    background: #ffffff;
    border-right: 1px solid #ddd;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  #sidebar header {{
    padding: 16px;
    background: #1B5E20;
    color: white;
  }}
  #sidebar header h1 {{ font-size: 1.1rem; margin-bottom: 4px; }}
  #sidebar header p {{ font-size: 0.8rem; opacity: 0.9; margin: 0; }}
  #field-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }}
  .field-item {{
    display: flex;
    align-items: center;
    padding: 10px 8px;
    margin-bottom: 6px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
    border: 1px solid transparent;
  }}
  .field-item:hover {{ background: #E8F5E9; border-color: #A5D6A7; }}
  .field-color {{
    width: 14px; height: 14px; border-radius: 3px;
    margin-right: 10px; flex-shrink: 0;
    border: 1px solid rgba(0,0,0,0.2);
  }}
  .field-info {{ flex: 1; min-width: 0; }}
  .field-info .name {{
    font-weight: 600; font-size: 0.9rem;
    color: #1a1a1a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .field-info .meta {{
    font-size: 0.75rem; color: #666; margin-top: 2px;
  }}
  .fit-all-btn {{
    margin: 12px;
    padding: 10px;
    background: #2E7D32;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    text-align: center;
  }}
  .fit-all-btn:hover {{ background: #1B5E20; }}
  #map {{ flex: 1; position: relative; }}
  .leaflet-popup-content-wrapper {{
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }}
  .leaflet-popup-content {{
    margin: 12px 16px;
    line-height: 1.5;
    font-size: 0.9rem;
  }}
  .popup-row {{ display: flex; justify-content: space-between; gap: 12px; }}
  .popup-label {{ color: #666; font-size: 0.8rem; }}
  .popup-value {{ font-weight: 500; color: #1a1a1a; }}
  @media (max-width: 768px) {{
    #sidebar {{ width: 220px; }}
  }}
</style>
</head>
<body>
<div id="container">
  <div id="sidebar">
    <header>
      <h1>{farm_name}</h1>
      <p>Grower: {grower_slug} &middot; {field_count} field{'s' if field_count != 1 else ''}</p>
    </header>
    <button class="fit-all-btn" onclick="fitAllFields()">Fit All Fields</button>
    <div id="field-list"></div>
  </div>
  <div id="map"></div>
</div>

<script>
  var fieldMeta = {fields_meta_json};
  var geojsonData = {geojson_json};

  var map = L.map('map', {{ zoomControl: true }}).setView([{center_lat}, {center_lon}], 12);

  var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }});

  var imagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    attribution: 'Tiles &copy; Esri',
    maxZoom: 18
  }});

  osm.addTo(map);
  L.control.layers({{ 'OpenStreetMap': osm, 'Satellite': imagery }}).addTo(map);

  var layers = [];
  var geoLayer = L.geoJSON(geojsonData, {{
    style: function(feature) {{
      var idx = geojsonData.features.indexOf(feature);
      var color = fieldMeta[idx] ? fieldMeta[idx].color : '#4E79A7';
      return {{
        color: color,
        weight: 2.5,
        opacity: 0.9,
        fillColor: color,
        fillOpacity: 0.35
      }};
    }},
    onEachFeature: function(feature, layer) {{
      var idx = geojsonData.features.indexOf(feature);
      var meta = fieldMeta[idx] || {{}};
      var popupHtml = '<div style="min-width:180px;">' +
        '<div style="font-weight:700;font-size:1rem;margin-bottom:8px;color:#1B5E20;">' + (meta.field_id || 'Field') + '</div>' +
        '<div class="popup-row"><span class="popup-label">Grower</span><span class="popup-value">{grower_slug}</span></div>' +
        '<div class="popup-row"><span class="popup-label">Farm</span><span class="popup-value">{farm_name}</span></div>' +
        '<div class="popup-row"><span class="popup-label">Area</span><span class="popup-value">' + (meta.area_acres || 'N/A') + ' ac</span></div>' +
        '<div class="popup-row"><span class="popup-label">County</span><span class="popup-value">' + (meta.county_name || 'N/A') + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">State FIPS</span><span class="popup-value">' + (meta.state_fips || 'N/A') + '</span></div>' +
        '<div class="popup-row"><span class="popup-label">Crop</span><span class="popup-value">' + (meta.crop_name || 'N/A') + '</span></div>' +
        '</div>';
      layer.bindPopup(popupHtml);
      layers.push(layer);
    }}
  }}).addTo(map);

  var listEl = document.getElementById('field-list');
  fieldMeta.forEach(function(meta, idx) {{
    var item = document.createElement('div');
    item.className = 'field-item';
    item.innerHTML = '<div class="field-color" style="background:' + meta.color + '"></div>' +
      '<div class="field-info">' +
        '<div class="name">' + meta.field_id + '</div>' +
        '<div class="meta">' + meta.area_acres + ' ac &middot; ' + (meta.county_name || 'Unknown') + '</div>' +
      '</div>';
    item.onclick = function() {{
      var layer = layers[idx];
      if (layer) {{
        map.fitBounds(layer.getBounds().pad(0.3), {{ maxZoom: 16, animate: true, duration: 0.5 }});
        layer.openPopup();
      }}
    }};
    listEl.appendChild(item);
  }});

  function fitAllFields() {{
    if (geoLayer.getBounds().isValid()) {{
      map.fitBounds(geoLayer.getBounds().pad(0.1), {{ animate: true, duration: 0.5 }});
    }}
  }}

  fitAllFields();
</script>
</body>
</html>"""
    return html


def generate_for_farm(
    grower_slug: str,
    farm_slug: str,
    farm_name: str | None = None,
) -> Path | None:
    boundary_path = _REPO / "growers" / grower_slug / "farms" / farm_slug / "boundary" / "field_boundaries.geojson"
    if not boundary_path.exists():
        print(f"  SKIP {grower_slug}/{farm_slug}: boundary not found at {boundary_path}")
        return None

    try:
        gdf = gpd.read_file(boundary_path)
    except Exception as exc:
        print(f"  ERROR {grower_slug}/{farm_slug}: could not read boundary GeoJSON: {exc}")
        return None

    if gdf.empty:
        print(f"  SKIP {grower_slug}/{farm_slug}: no features in boundary file")
        return None

    geojson_data = json.loads(gdf.to_json())
    resolved_name = farm_name or farm_slug.replace("-", " ").title()

    html = _generate_html(
        geojson_data,
        grower_slug=grower_slug,
        farm_slug=farm_slug,
        farm_name=resolved_name,
    )

    out_dir = _REPO / "growers" / grower_slug / "farms" / farm_slug / "derived" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{farm_slug}_grower_web_map.html"
    out_path.write_text(html, encoding="utf-8")

    size_kb = len(html) / 1024
    print(f"  OK  {grower_slug}/{farm_slug} -> {out_path.relative_to(_REPO)} ({size_kb:.1f} KB)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grower-level interactive web maps")
    parser.add_argument("--grower-slug", default=None, help="Target grower slug")
    parser.add_argument("--farm-slug", default=None, help="Target farm slug (optional)")
    parser.add_argument("--all", action="store_true", help="Generate maps for all discovered farms")
    args = parser.parse_args()

    if args.all:
        farms = _discover_growers()
        if not farms:
            print("No farms discovered under growers/")
            sys.exit(1)
        print(f"Generating web maps for {len(farms)} farm(s)...")
        for item in farms:
            generate_for_farm(item["grower_slug"], item["farm_slug"], item["farm_name"])
        print("Done.")
        return

    if not args.grower_slug:
        parser.error("Provide --grower-slug or use --all")

    if args.farm_slug:
        generate_for_farm(args.grower_slug, args.farm_slug)
    else:
        farms = _discover_growers()
        matches = [f for f in farms if f["grower_slug"] == args.grower_slug]
        if not matches:
            print(f"No farms found for grower '{args.grower_slug}'")
            sys.exit(1)
        for item in matches:
            generate_for_farm(item["grower_slug"], item["farm_slug"], item["farm_name"])


if __name__ == "__main__":
    main()
