#!/usr/bin/env python3
"""Step 3: Build self-contained Observable Plot HTML dashboard from data files.

Reads all data files from data/ and generates:
  output/corn_soil_dashboard.html

The output is a single downloadable HTML file that works offline in any modern browser.
Observable Plot is loaded from CDN for chart rendering.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_data():
    fields = pd.read_csv(DATA_DIR / "field_boundaries.csv")
    soil = pd.read_csv(DATA_DIR / "soil_profiles.csv")
    weather = pd.read_csv(DATA_DIR / "weather_daily_2021_2025.csv")
    ndvi = pd.read_csv(DATA_DIR / "ndvi_growing_season.csv")
    scores = pd.read_csv(DATA_DIR / "soil_scores.csv")
    actions = pd.read_csv(DATA_DIR / "action_recommendations.csv")
    return fields, soil, weather, ndvi, scores, actions


def _serialize_soil(soil):
    # Group soil rows by field_id into nested structure for template
    grouped = {}
    for fid, grp in soil.groupby("field_id"):
        layers = []
        for _, row in grp.sort_values("hzdept_r").iterrows():
            layers.append({
                "hzdept_r": int(row["hzdept_r"]),
                "hzdepb_r": int(row["hzdepb_r"]),
                "om_r": float(row["om_r"]),
                "ph1to1h2o_r": float(row["ph1to1h2o_r"]),
                "awc_r": float(row["awc_r"]),
                "dbthirdbar_r": float(row["dbthirdbar_r"]),
                "claytotal_r": float(row["claytotal_r"]),
                "sandtotal_r": float(row["sandtotal_r"]),
                "silttotal_r": float(row["silttotal_r"]),
            })
        grouped[fid] = {
            "layers": layers,
            "drainagecl": str(grp.iloc[0]["drainagecl"]),
            "muname": str(grp.iloc[0]["muname"]),
        }
    return grouped


def build_html(fields, soil, weather, ndvi, scores, actions):
    """Assemble the full HTML dashboard page."""
    scores_json = json.dumps(scores.to_dict("records"))
    actions_json = json.dumps(actions.to_dict("records"))
    soil_json = json.dumps(_serialize_soil(soil))

    weather_records = []
    for _, row in weather.iterrows():
        weather_records.append({
            "date": str(row["date"]), "year": int(row["year"]), "doy": int(row["doy"]),
            "T2M": float(row["T2M"]), "T2M_MAX": float(row["T2M_MAX"]),
            "T2M_MIN": float(row["T2M_MIN"]), "PRECTOTCORR": float(row["PRECTOTCORR"]),
        })
    weather_json = json.dumps(weather_records)

    ndvi_grouped = {}
    for (fid, yr), grp in ndvi.groupby(["field_id", "year"]):
        if fid not in ndvi_grouped:
            ndvi_grouped[fid] = {}
        ndvi_grouped[fid][int(yr)] = [float(v) for v in grp.sort_values("doy")["ndvi"].tolist()]
    ndvi_json = json.dumps(ndvi_grouped)

    n_crit = int((scores["score"] < 55).sum())
    n_good = int((scores["score"] >= 80).sum())
    n_fields = len(fields)
    total_ac = int(fields["acres"].sum())
    worst = scores.iloc[-1]

    narrative = (
        f"{n_crit} {'field needs' if n_crit == 1 else 'fields need'} action — "
        f"{n_good} {'field is' if n_good == 1 else 'fields are'} ready for corn."
    )

    field_options = "".join(
        f'<option value="{s["field_id"]}"{" selected" if i == 0 else ""}>'
        f'{s["field_id"]} — {s["name"]} (Score: {int(s["score"])} '
        f'{"🟢" if s["score"] >= 80 else "🟡" if s["score"] >= 65 else "🟠" if s["score"] >= 55 else "🔴"})</option>'
        for i, (_, s) in enumerate(scores.iterrows())
    )

    default_fid = scores.iloc[0]["field_id"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corn Soil Dashboard — DeKalb, IL</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.4; font-size: 13px; }}
.dashboard {{ max-width: 1500px; margin: 0 auto; padding: 10px 14px; height: 100vh; display: flex; flex-direction: column; }}
.header {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }}
.header h1 {{ font-size: 18px; color: #166534; white-space: nowrap; }}
.header .summary {{ font-size: 12px; color: #475569; font-weight: 600; }}
.header .meta {{ font-size: 11px; color: #94a3b8; white-space: nowrap; }}
.field-picker {{ display: flex; align-items: center; gap: 8px; padding: 8px 0 6px; }}
.field-picker label {{ font-size: 12px; font-weight: 600; color: #334155; white-space: nowrap; }}
.field-picker select {{ font-size: 13px; padding: 5px 10px; border: 1px solid #d1d5db; border-radius: 6px; background: white; font-weight: 600; min-width: 300px; }}
.field-picker .nav-btn {{ padding: 4px 10px; border: 1px solid #d1d5db; background: white; border-radius: 4px; cursor: pointer; font-size: 12px; }}
.field-picker .nav-btn:hover {{ background: #f1f5f9; }}
.detail-grid {{ display: grid; grid-template-columns: 2.5fr 1fr; gap: 12px; flex: 1; min-height: 0; }}
.map-section {{ background: white; border-radius: 8px; padding: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: flex; flex-direction: column; min-height: 0; }}
.map-container {{ flex: 1; position: relative; }}
.right-side {{ display: flex; flex-direction: column; gap: 8px; min-height: 0; }}
.profile-panel {{ background: white; border-radius: 8px; padding: 8px 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); font-size: 11px; }}
.profile-panel h3 {{ font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }}
.profile-row {{ display: grid; grid-template-columns: 36px 1fr 32px 24px; gap: 2px; align-items: center; padding: 1px 0; }}
.profile-bar-bg {{ background: #f1f5f9; border-radius: 2px; height: 10px; overflow: hidden; }}
.profile-bar-fill {{ height: 100%; border-radius: 2px; }}
.profile-status {{ font-size: 9px; font-weight: 600; text-align: center; padding: 1px 2px; border-radius: 2px; }}
.status-ok {{ background: #dcfce7; color: #166534; }}
.status-warn {{ background: #fef9c3; color: #854d0e; }}
.status-bad {{ background: #fee2e2; color: #991b1b; }}
.ndvi-line {{ display: flex; align-items: center; gap: 4px; font-size: 10px; padding: 2px 0; }}
.field-aside {{ display: flex; flex-direction: column; gap: 6px; flex: 1; min-height: 0; }}
.options {{ display: flex; flex-direction: column; gap: 5px; overflow-y: auto; flex: 1; }}
.option-card {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 8px; font-size: 11px; }}
.option-card h4 {{ font-size: 11px; margin-bottom: 3px; }}
.option-card ul {{ list-style: none; color: #475569; }}
.option-card ul li {{ padding: 1px 0; }}
.option-card ul li::before {{ content: "├── "; color: #94a3b8; }}
.rec {{ font-size: 10px; padding: 4px 8px; background: #eff6ff; border-radius: 4px; border-left: 3px solid #3b82f6; }}
.bottom-section {{ display: flex; flex-direction: column; gap: 6px; }}
.rankings-bar {{ background: white; border-radius: 6px; padding: 6px 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); overflow: hidden; }}
.rankings-bar summary {{ font-size: 12px; font-weight: 600; color: #334155; cursor: pointer; padding: 2px 0; }}
.rankings-bar summary::marker {{ font-size: 10px; }}
.ranks-inner {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px 12px; padding-top: 6px; }}
.rank-compact {{ display: flex; align-items: center; gap: 4px; padding: 2px 4px; cursor: pointer; border-radius: 4px; font-size: 11px; }}
.rank-compact:hover {{ background: #f1f5f9; }}
.rank-compact .rname {{ font-weight: 600; min-width: 22px; }}
.rank-compact .rbar {{ flex: 1; height: 10px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }}
.rank-compact .rfill {{ height: 100%; border-radius: 2px; }}
.rank-compact .rscore {{ font-weight: 700; font-size: 10px; min-width: 22px; text-align: right; }}
.rank-compact .rndvi {{ width: 55px; height: 10px; }}
.weather-section {{ background: white; border-radius: 8px; padding: 8px 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.weather-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
.weather-header h3 {{ font-size: 13px; font-weight: 600; color: #334155; }}
.weather-header select {{ font-size: 12px; padding: 3px 8px; border: 1px solid #d1d5db; border-radius: 4px; background: white; }}
.weather-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
.weather-table th {{ text-align: left; font-weight: 600; color: #64748b; padding: 3px 6px; border-bottom: 1px solid #e2e8f0; font-size: 10px; }}
.weather-table td {{ padding: 3px 6px; border-bottom: 1px solid #f1f5f9; }}
.weather-table tr.total {{ font-weight: 700; border-top: 2px solid #e2e8f0; }}
.weather-table .evt {{ color: #EF4444; font-weight: 600; }}
.weather-table .evt-none {{ color: #94a3b8; }}
.weather-annual {{ display: flex; gap: 16px; padding-top: 6px; font-size: 11px; color: #475569; border-top: 1px solid #e2e8f0; margin-top: 4px; }}
.weather-annual strong {{ color: #1e293b; }}
</style>
</head>
<body>
<div class="dashboard">
  <div class="header">
    <div style="display:flex;align-items:baseline;gap:12px">
      <h1>🌽 Corn Soil Dashboard</h1>
      <span class="summary">{narrative}</span>
    </div>
    <div class="meta">DeKalb County, IL · {n_fields} fields · {total_ac:,} acres · Soil Quality Index (0-100)</div>
  </div>

  <div class="field-picker">
    <label>FIELD:</label>
    <select id="field-selector">{field_options}</select>
    <button class="nav-btn" onclick="navField(-1)">◀ Prev</button>
    <button class="nav-btn" onclick="navField(1)">Next ▶</button>
  </div>

  <div class="detail-grid">
    <div class="map-section">
      <div class="map-container" id="map-container"></div>
    </div>
    <div class="right-side">
      <div class="profile-panel" id="profile-panel">
        <h3>Soil Profile by Depth</h3>
        <div id="profile-content"></div>
      </div>
      <div class="field-aside">
        <div id="ndvi-alert"></div>
        <div class="options" id="options-panel"></div>
        <div id="rec-section"></div>
      </div>
    </div>
  </div>

  <div class="bottom-section">
    <details class="rankings-bar" open>
      <summary>ALL FIELDS (best → worst)</summary>
      <div class="ranks-inner" id="ranks-grid"></div>
    </details>
    <div class="weather-section" id="weather-section">
      <div class="weather-header">
        <h3>WEATHER TABLE</h3>
        <select id="year-selector">
          <option value="2025" selected>2025</option><option value="2024">2024</option>
          <option value="2023">2023</option><option value="2022">2022</option><option value="2021">2021</option>
        </select>
      </div>
      <div id="weather-table"></div>
    </div>
  </div>
</div>

<script type="module">
import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

const SCORES = {scores_json};
const WEATHER = {weather_json};
const NDVI = {ndvi_json};
const ACTIONS = {actions_json};
const SOIL = {soil_json};
const MM_TO_IN = 1.0 / 25.4;

let selectedField = "{default_fid}";
let selectedYear = 2025;

// ── Rankings Grid ──
function renderRankings() {{
  const grid = document.getElementById("ranks-grid");
  const rows = SCORES.map(s => {{
    const pct = s.score;
    const color = pct >= 80 ? '#10B981' : pct >= 55 ? '#F59E0B' : '#EF4444';
    const ndviData = NDVI[s.field_id]?.[selectedYear] || [];
    const sel = s.field_id === selectedField ? ' style="outline:2px solid #3b82f6;outline-offset:1px"' : '';
    return `<div class="rank-compact"${{sel}} onclick="selectField('${{s.field_id}}')">
      <span class="rname">${{s.field_id}}</span>
      <div class="rbar"><div class="rfill" style="width:${{pct}}%;background:${{color}}"></div></div>
      <span class="rscore" style="color:${{color}}">${{pct}}</span>
      <span class="rndvi" data-fid="${{s.field_id}}"></span>
    </div>`;
  }}).join('');
  grid.innerHTML = rows;
  grid.querySelectorAll('.rndvi').forEach(el => {{
    const fid = el.dataset.fid;
    const ndviData = NDVI[fid]?.[selectedYear] || [];
    if (ndviData.length) {{
      const svg = sparkSmall(ndviData, 55, 10);
      el.innerHTML = ''; el.appendChild(svg);
    }}
  }});
}}

function sparkSmall(vals, w, h) {{
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", w); svg.setAttribute("height", h);
  svg.setAttribute("viewBox", `0 0 ${{vals.length-1}} 1`);
  svg.style.overflow = "visible";
  const pts = vals.map((v,i) => `${{i}},${{1-v}}`).join(' ');
  const pl = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  pl.setAttribute("points", pts); pl.setAttribute("fill", "none");
  pl.setAttribute("stroke", "#818cf8"); pl.setAttribute("stroke-width", "0.08");
  pl.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(pl);
  return svg;
}}

// ── Map ──
function renderMap() {{
  const field = SCORES.find(s => s.field_id === selectedField);
  if (!field) return;
  const score = field.score;
  const acres = field.acres;
  const name = field.name;
  const color = score >= 80 ? '#10B981' : score >= 55 ? '#F59E0B' : '#EF4444';
  const opacity = 0.4 + score * 0.005;
  const w = 600, h = 340, cx = w/2, cy = h/2, sz = 90 + (acres - 620) * 0.06;

  // Simple 6-point polygon
  const pts = [[cx-sz*0.55,cy-sz*0.45],[cx+sz*0.45,cy-sz*0.5],[cx+sz*0.65,cy],[cx+sz*0.35,cy+sz*0.48],[cx-sz*0.28,cy+sz*0.55],[cx-sz*0.65,cy+sz*0.08]];
  const d = pts.map((p,i)=>`${{i===0?'M':'L'}} ${{p[0].toFixed(0)}} ${{p[1].toFixed(0)}}`).join(' ')+' Z';

  // Grid lines
  let grid = '';
  for (let x = 0; x <= w; x += 100) grid += `<line x1="${{x}}" y1="0" x2="${{x}}" y2="${{h}}" stroke="#e2e8f0" stroke-width="0.5"/>`;
  for (let y = 0; y <= h; y += 100) grid += `<line x1="0" y1="${{y}}" x2="${{w}}" y2="${{y}}" stroke="#e2e8f0" stroke-width="0.5"/>`;

  // Scale bar
  const scaleX = w - 90, scaleY = h - 30;

  const svg = document.getElementById("map-container");
  svg.innerHTML = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 ${{w}} ${{h}}" style="width:100%;height:100%">
    <rect width="${{w}}" height="${{h}}" fill="#dcfce7"/>
    ${{grid}}
    <path d="${{d}}" fill="${{color}}" fill-opacity="${{opacity}}" stroke="${{color}}" stroke-width="2.5"/>
    <text x="${{cx}}" y="${{cy-25}}" text-anchor="middle" font-size="10" fill="#475569" font-weight="600">${{name}}</text>
    <text x="${{cx}}" y="${{cy-8}}" text-anchor="middle" font-size="9" fill="#64748b">${{acres}} acres · Soil Quality: ${{score}}/100</text>
    <text x="${{cx}}" y="${{cy+8}}" text-anchor="middle" font-size="9" fill="${{color}}" font-weight="600">${{score>=80?'🟢 Excellent':score>=65?'🟡 Good':score>=55?'🟠 Needs attention':'🔴 Critical'}}</text>
    <line x1="${{scaleX}}" y1="${{scaleY}}" x2="${{scaleX-60}}" y2="${{scaleY}}" stroke="#94a3b8" stroke-width="1.5"/>
    <line x1="${{scaleX}}" y1="${{scaleY-4}}" x2="${{scaleX}}" y2="${{scaleY+4}}" stroke="#94a3b8" stroke-width="1"/>
    <line x1="${{scaleX-60}}" y1="${{scaleY-4}}" x2="${{scaleX-60}}" y2="${{scaleY+4}}" stroke="#94a3b8" stroke-width="1"/>
    <text x="${{scaleX-30}}" y="${{scaleY-5}}" text-anchor="middle" font-size="7" fill="#94a3b8">~1,000 ft</text>
    <text x="15" y="18" font-size="8" fill="#94a3b8">N</text>
    <polygon points="15,14 12,20 18,20" fill="#94a3b8"/>
  </svg>`;
}}

// ── Field Navigation ──
window.navField = function(dir) {{
  const idx = SCORES.findIndex(s => s.field_id === selectedField);
  const nextIdx = (idx + dir + SCORES.length) % SCORES.length;
  window.selectField(SCORES[nextIdx].field_id);
}};

// ── Selector ──
window.selectField = function(fid) {{
  selectedField = fid;
  document.getElementById("field-selector").value = fid;
  renderMap(); renderProfile(); renderOptions(); renderRankings();
}};
document.getElementById("field-selector").addEventListener("change", (e) => window.selectField(e.target.value));

// ── Profile ──
function renderProfile() {{
  const field = SCORES.find(s => s.field_id === selectedField);
  if (!field) return;
  const soilData = SOIL[field.field_id];
  if (!soilData || !soilData.layers) return;
  const dl = ['0–6"', '6–12"', '12–24"'];
  let h = '';
  soilData.layers.forEach((l, i) => {{
    const omS = l.om_r >= 3.0 ? 'ok' : l.om_r >= 2.0 ? 'warn' : 'bad';
    const phS = (l.ph1to1h2o_r >= 6.0 && l.ph1to1h2o_r <= 7.0) ? 'ok' : (l.ph1to1h2o_r >= 5.5) ? 'warn' : 'bad';
    const awcS = l.awc_r >= 0.15 ? 'ok' : l.awc_r >= 0.10 ? 'warn' : 'bad';
    const omPct = Math.min(100, Math.round(l.om_r / 5.0 * 100));
    const phPct = Math.min(100, Math.round(l.ph1to1h2o_r / 8.0 * 100));
    const awcPct = Math.min(100, Math.round(l.awc_r / 0.25 * 100));
    h += `<div style="font-size:9px;font-weight:600;color:#94a3b8;margin-top:3px">${{dl[i]}}</div>`;
    h += `<div class="profile-row"><span>OM</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{omPct}}%;background:#${{omS==='ok'?'10B981':omS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.om_r}}%</span><span class="profile-status status-${{omS}}">${{omS==='ok'?'+':omS==='warn'?'~':'−'}}</span></div>`;
    h += `<div class="profile-row"><span>pH</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{phPct}}%;background:#${{phS==='ok'?'10B981':phS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.ph1to1h2o_r}}</span><span class="profile-status status-${{phS}}">${{phS==='ok'?'+':phS==='warn'?'~':'−'}}</span></div>`;
    h += `<div class="profile-row"><span>AWC</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{awcPct}}%;background:#${{awcS==='ok'?'10B981':awcS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.awc_r}}</span><span class="profile-status status-${{awcS}}">${{awcS==='ok'?'+':awcS==='warn'?'~':'−'}}</span></div>`;
  }});
  h += '<div style="font-size:8px;color:#94a3b8;margin-top:3px">+ optimal ~ borderline − needs fix</div>';
  document.getElementById("profile-content").innerHTML = h;
}}

// ── NDVI Alert ──
function getNdviAlert(field, ndviMean, isGood) {{
  if (!ndviMean) return '';
  if (!isGood && parseFloat(ndviMean) < 0.65)
    return '<div style="padding:4px 6px;background:#fef2f2;border-left:3px solid #EF4444;border-radius:4px;font-size:10px;margin-bottom:4px">⚠️ Soil score AND NDVI both low — soil likely limiting plant vigor</div>';
  if (isGood && parseFloat(ndviMean) >= 0.72)
    return '<div style="padding:4px 6px;background:#f0fdf4;border-left:3px solid #10B981;border-radius:4px;font-size:10px;margin-bottom:4px">✅ Soil and NDVI both in good range</div>';
  if (isGood)
    return '<div style="padding:4px 6px;background:#fffbeb;border-left:3px solid #F59E0B;border-radius:4px;font-size:10px;margin-bottom:4px">⚠️ Good soil but low NDVI — check weather or management</div>';
  return '';
}}

// ── Options ──
function renderOptions() {{
  const field = SCORES.find(s => s.field_id === selectedField);
  if (!field) return;
  const action = ACTIONS.find(a => a.field_id === selectedField) || {{}};
  const ndviData = NDVI[field.field_id]?.[selectedYear] || [];
  const ndviMean = ndviData.length ? (ndviData.reduce((a,b) => a+b,0) / ndviData.length).toFixed(3) : null;
  const isGood = field.score >= 80;

  document.getElementById("ndvi-alert").innerHTML = getNdviAlert(field, ndviMean, isGood);

  let html = '';
  if (isGood) {{
    html = `<div class="option-card" style="border-left:3px solid #10B981">
      <h4 style="color:#166534">✅ No Action Needed</h4>
      <ul>
        <li>Estimated corn yield: ${{Math.round(action.base_yield_corn_bu_ac || 180)}} bu/acre</li>
        <li>Revenue: ~$${{Math.round(action.revenue_current_per_ac || 990)}}/acre</li>
        <li>Maintain current practices</li>
      </ul>
    </div>`;
  }} else {{
    html = `<div class="option-card" style="border-left:3px solid #10B981">
      <h4 style="color:#166534">OPTION 1: FIX FOR CORN</h4>
      <ul>
        <li>Cost: $${{action.fix_cost_per_ac || 0}}/acre</li>
        <li>Yield: ${{action.base_yield_corn_bu_ac || 0}} → ${{action.fixed_yield_corn_bu_ac || 0}} bu/acre</li>
        <li>Revenue after fix: ~$${{action.revenue_fixed_per_ac || 0}}/acre</li>
        <li>Payback: ${{(action.payback_years || 0).toFixed(1)}} years</li>
      </ul>
    </div>
    <div class="option-card" style="border-left:3px solid #F59E0B">
      <h4 style="color:#92400E">OPTION 2: SWITCH TO SOYBEANS</h4>
      <ul>
        <li>Cost: $0</li>
        <li>Expected yield: ${{action.soy_yield_bu_ac || 0}} bu/acre</li>
        <li>Revenue: ~$${{action.revenue_soy_per_ac || 0}}/acre</li>
      </ul>
    </div>
    <div class="option-card" style="border-left:3px solid #94a3b8">
      <h4 style="color:#475569">OPTION 3: DO NOTHING</h4>
      <ul>
        <li>Current revenue: ~$${{action.revenue_current_per_ac || 0}}/acre</li>
        <li>Risk: Soil may continue to degrade</li>
      </ul>
    </div>`;
  }}
  document.getElementById("options-panel").innerHTML = html;

  // Recommendation
  if (!isGood) {{
    const pb = (action.payback_years || 0);
    const fc = (action.fix_cost_per_ac || 0);
    const rs = Math.round(action.revenue_soy_per_ac || 0);
    let msg = pb <= 3.0
      ? 'Fix for corn now — invest $'+fc+'/acre, breaks even in '+pb.toFixed(1)+' years.'
      : 'Consider switching to soybeans — lower revenue (~$'+rs+'/ac) but zero upfront cost and less risk.';
    document.getElementById("rec-section").innerHTML = '<div class="rec"><strong>Recommendation:</strong> '+msg+'</div>';
  }} else {{
    document.getElementById("rec-section").innerHTML = '';
  }}
}}

// ── Weather Table ──
function renderWeather() {{
  const tbl = document.getElementById("weather-table");
  const yearData = WEATHER.filter(d => d.year === selectedYear);
  if (yearData.length === 0) {{ tbl.innerHTML = 'No data'; return; }}
  const months = [1,2,3,4,5,6,7,8,9,10,11,12];
  const mNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  // Monthly aggregates
  const mRainIn = months.map(m => {{
    const d = yearData.filter(r => new Date(r.date).getMonth()+1 === m);
    return +(d.reduce((s,r) => s + (r.PRECTOTCORR||0), 0) * MM_TO_IN).toFixed(1);
  }});
  const mTemp = months.map(m => {{
    const d = yearData.filter(r => new Date(r.date).getMonth()+1 === m);
    return d.length ? Math.round(d.reduce((s,r) => s+(r.T2M||0),0)/d.length) : 0;
  }});

  // 5-yr averages for anomaly
  const allYears = WEATHER.filter(r => r.year >= 2021 && r.year <= 2025);
  const mAvgRain = months.map(m => {{
    const five = allYears.filter(r => {{ const mo = new Date(r.date).getMonth()+1; return mo === m && r.year !== selectedYear; }});
    const total = five.reduce((s,r) => s + (r.PRECTOTCORR||0), 0);
    return +(total * MM_TO_IN / 4).toFixed(1);
  }});

  const mGdd = months.map(m => {{
    const d = yearData.filter(r => new Date(r.date).getMonth()+1 === m);
    return Math.round(d.reduce((s,r) => s + Math.max(0, ((r.T2M_MAX||70)+(r.T2M_MIN||50))/2-50), 0));
  }});

  // Events
  const mEvents = months.map(m => {{
    const d = yearData.filter(r => new Date(r.date).getMonth()+1 === m);
    const rain = d.reduce((s,r) => s + (r.PRECTOTCORR||0), 0) * MM_TO_IN;
    const avgR = mAvgRain[m-1];
    const maxTemp = Math.max(...d.map(r => r.T2M_MAX||0));
    if (rain > avgR * 1.5) return 'Heavy rain';
    if (maxTemp > 95 && m >= 5 && m <= 9) return 'Heat stress';
    if (rain < avgR * 0.4 && m >= 4 && m <= 9) return 'Dry month';
    return '';
  }});

  // Status
  const mStatus = months.map(m => {{
    const rain = mRainIn[m-1];
    const avgR = mAvgRain[m-1];
    if (m < 3 || m > 10) return '—';
    if (rain > avgR * 1.4) return 'Wet';
    if (rain < avgR * 0.5) return 'Dry';
    return 'Good';
  }});

  const totalRain = +mRainIn.reduce((a,b) => a+b, 0).toFixed(1);
  const avgTemp = Math.round(mTemp.reduce((a,b) => a+b, 0)/12);
  const totalGdd = mGdd.reduce((a,b) => a+b, 0);
  const growSeasonRain = mRainIn.slice(3, 9).reduce((a,b) => a+b, 0);
  const avgGrowRain = mAvgRain.slice(3, 9).reduce((a,b) => a+b, 0);
  const rainPct = avgGrowRain > 0 ? Math.round(growSeasonRain/avgGrowRain*100) : 100;
  const anomalyLabel = rainPct > 130 ? '⚠️ Wet year' : rainPct < 70 ? '⚠️ Dry year' : '✅ Normal';
  const anomalyColor = rainPct > 130 ? '#EF4444' : rainPct < 70 ? '#F59E0B' : '#10B981';
  const nEvents = mEvents.filter(e => e).length;
  const soilReliable = rainPct <= 150 && rainPct >= 60;

  let rows = `<tr><th>Month</th><th>Rain</th><th>Temp</th><th>GDD</th><th>Extreme Weather</th><th>Status</th></tr>`;
  for (let i = 0; i < 12; i++) {{
    const evtClass = mEvents[i] ? 'evt' : 'evt-none';
    rows += `<tr><td>${{mNames[i]}}</td><td>${{mRainIn[i]}}″</td><td>${{mTemp[i]}}°F</td><td>${{mGdd[i]}}</td><td class="${{evtClass}}">${{mEvents[i] || '—'}}</td><td>${{mStatus[i]}}</td></tr>`;
  }}
  rows += `<tr class="total"><td><strong>TOTAL</strong></td><td><strong>${{totalRain}}″</strong></td><td><strong>${{avgTemp}}°F</strong></td><td><strong>${{totalGdd}}</strong></td><td><strong>${{nEvents}} event${{nEvents!==1?'s':''}}</strong></td><td><strong>${{anomalyLabel}}</strong></td></tr>`;

  const anomalyPanel = `<div class="weather-annual">
    <span>Annual: <strong>${{totalRain}}″ rain</strong> · <strong>${{avgTemp}}°F avg</strong> · <strong>${{totalGdd}} GDD</strong></span>
    <span style="color:${{anomalyColor}};font-weight:600">${{anomalyLabel}} (${{rainPct}}% of 5-yr growing-season avg)</span>
    <span style="color:#94a3b8">Soil readings ${{soilReliable ? '✅ reliable' : '⚠️ may be affected by weather'}}</span>
  </div>`;

  tbl.innerHTML = `<table class="weather-table">${{rows}}</table>${{anomalyPanel}}`;
}}

// ── Year selector ──
document.getElementById("year-selector").addEventListener("change", (e) => {{
  selectedYear = parseInt(e.target.value);
  renderWeather();
  renderRankings();
}});

// ── Init ──
renderMap();
renderProfile();
renderOptions();
renderRankings();
renderWeather();
</script>
</body>
</html>"""

    return html


def main():
    print("=" * 60)
    print("Step 3: Building HTML Dashboard")
    print("=" * 60)

    print("\nLoading data files...")
    fields, soil, weather, ndvi, scores, actions = load_all_data()
    print(f"  {len(fields)} fields, {len(soil)} soil layers, {len(weather)} weather records")
    print(f"  {len(ndvi)} NDVI obs, {len(scores)} scores, {len(actions)} actions")

    print("\nBuilding HTML...")
    html = build_html(fields, soil, weather, ndvi, scores, actions)

    output_path = OUTPUT_DIR / "corn_soil_dashboard.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard saved to: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")

    n_good = (scores["score"] >= 80).sum()
    n_crit = (scores["score"] < 55).sum()
    print(f"   Fields: {n_good} excellent/good, 2 watch, {n_crit} critical")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
