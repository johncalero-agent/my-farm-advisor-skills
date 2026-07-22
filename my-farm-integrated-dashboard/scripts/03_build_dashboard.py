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
    # Serialize all data as JSON for embedding
    scores_json = json.dumps(scores.to_dict("records"))
    actions_json = json.dumps(actions.to_dict("records"))
    soil_json = json.dumps(_serialize_soil(soil))

    # Build weather JSON (compact)
    weather_records = []
    for _, row in weather.iterrows():
        weather_records.append({
            "date": str(row["date"]),
            "year": int(row["year"]),
            "doy": int(row["doy"]),
            "T2M": float(row["T2M"]),
            "T2M_MAX": float(row["T2M_MAX"]),
            "T2M_MIN": float(row["T2M_MIN"]),
            "PRECTOTCORR": float(row["PRECTOTCORR"]),
        })
    weather_json = json.dumps(weather_records)

    # Build NDVI JSON (grouped by field_id -> year -> values)
    ndvi_grouped = {}
    for (fid, yr), grp in ndvi.groupby(["field_id", "year"]):
        if fid not in ndvi_grouped:
            ndvi_grouped[fid] = {}
        ndvi_grouped[fid][int(yr)] = [float(v) for v in grp.sort_values("doy")["ndvi"].tolist()]
    ndvi_json = json.dumps(ndvi_grouped)

    # ── Narrative ──
    n_good = int((scores["score"] >= 80).sum())
    n_crit = int((scores["score"] < 55).sum())
    avg_score = int(round(scores["score"].mean()))
    best = scores.iloc[0]
    worst = scores.iloc[-1]
    n_fields = len(fields)
    total_ac = int(fields["acres"].sum())

    narrative = (
        f"<strong>{n_crit} {'field needs' if n_crit == 1 else 'fields need'} immediate action"
        f" — {n_good} {'field is' if n_good == 1 else 'fields are'} ready for corn.</strong> "
        f"Average Soil Quality Index across {n_fields} fields: <strong>{avg_score}/100</strong>. "
        f"Best: {best['field_id']} ({best['name']}, {int(best['score'])}). "
        f"Worst: {worst['field_id']} ({worst['name']}, {int(worst['score'])}). "
        f"Select any field below to see detailed soil profiles, NDVI trends, and action options "
        f"including crop-switching alternatives with honest payback periods."
    )

    # ── Priority List ──
    criticals = scores[scores["score"] < 55]
    if len(criticals) == 0:
        priority_html = '<h2>NEEDS ATTENTION</h2><p style="color:#10B981;font-size:12px">✅ No critical fields — all fields performing well.</p>'
    else:
        items = []
        for _, s in criticals.head(3).iterrows():
            act = actions[actions["field_id"] == s["field_id"]].iloc[0]
            items.append(
                f'<div class="priority-item">'
                f'<span class="field-name" style="cursor:pointer;color:#EF4444" '
                f'onclick="selectField(\'{s["field_id"]}\')">🔴 {s["field_id"]}</span> '
                f'({s["name"]}, {int(s["score"])})<br>'
                f'<span style="color:#64748b">{_first_detail(act["fix_details"])}</span>'
                f'</div>'
            )
        priority_html = (
            f'<h2>NEEDS ATTENTION ({len(criticals)} field{"s" if len(criticals) != 1 else ""})</h2>'
            + "".join(items)
        )

    # ── Field Options ──
    field_options = "".join(
        f'<option value="{s["field_id"]}"{" selected" if i == 0 else ""}>'
        f'{s["field_id"]} — {s["name"]} (Score: {int(s["score"])})</option>'
        for i, (_, s) in enumerate(scores.iterrows())
    )

    default_fid = scores.iloc[0]["field_id"]

    # ── Build HTML ──
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corn Soil Dashboard — DeKalb, IL</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.4; font-size: 13px; }}
.dashboard {{ max-width: 1400px; margin: 0 auto; padding: 12px 16px; height: 100vh; display: flex; flex-direction: column; }}
.header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; }}
.header-left h1 {{ font-size: 20px; color: #166534; margin-bottom: 2px; }}
.header-left .subtitle {{ font-size: 12px; color: #64748b; }}
.narrative {{ font-size: 13px; color: #334155; max-width: 800px; padding: 6px 10px; background: #f0fdf4; border-left: 3px solid #10B981; border-radius: 4px; margin-bottom: 8px; }}
.content {{ display: grid; grid-template-columns: 1fr 280px; gap: 10px; flex: 1; min-height: 0; }}
.left-panel {{ display: flex; flex-direction: column; gap: 8px; min-height: 0; }}
.rankings {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.rankings h2 {{ font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 8px; }}
.rank-row {{ display: flex; align-items: center; gap: 8px; padding: 3px 0; cursor: pointer; border-radius: 4px; transition: background 0.15s; }}
.rank-row:hover {{ background: #f1f5f9; }}
.rank-row.selected {{ background: #dbeafe; }}
.rank-bar-bg {{ flex: 1; height: 18px; background: #f1f5f9; border-radius: 3px; position: relative; overflow: hidden; }}
.rank-bar-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
.rank-label {{ font-weight: 600; font-size: 12px; width: 24px; }}
.rank-score {{ font-size: 12px; font-weight: 700; width: 28px; text-align: right; }}
.rank-ndvi {{ font-size: 10px; color: #64748b; width: 90px; }}
.rank-flag {{ font-size: 10px; width: 100px; }}
.rank-sub {{ display: flex; gap: 2px; align-items: center; font-size: 9px; color: #94a3b8; }}
.rank-sub-bar {{ width: 3px; border-radius: 1px; }}
.right-panel {{ display: flex; flex-direction: column; gap: 8px; }}
.priority {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.priority h2 {{ font-size: 14px; font-weight: 600; color: #EF4444; margin-bottom: 8px; }}
.priority-item {{ padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12px; }}
.priority-item:last-child {{ border-bottom: none; }}
.priority-item .field-name {{ font-weight: 600; }}
.detail {{ background: white; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); flex: 1; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }}
.detail-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
.detail-header h2 {{ font-size: 14px; font-weight: 600; }}
.detail-header select {{ font-size: 12px; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; background: white; }}
.detail-grid {{ display: grid; grid-template-columns: 1.8fr 1fr; gap: 10px; margin-bottom: 8px; }}
.map-panel {{ aspect-ratio: 1.2; border: 1px solid #e2e8f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; background: #f8fafc; flex-direction: column; gap: 6px; }}
.profile-panel {{ display: flex; flex-direction: column; gap: 3px; font-size: 11px; }}
.profile-panel h3 {{ font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }}
.profile-row {{ display: grid; grid-template-columns: 44px 1fr 36px 28px; gap: 3px; align-items: center; padding: 1px 0; }}
.profile-bar-bg {{ background: #f1f5f9; border-radius: 2px; height: 12px; position: relative; overflow: hidden; }}
.profile-bar-fill {{ height: 100%; border-radius: 2px; }}
.profile-status {{ font-size: 10px; font-weight: 600; text-align: center; padding: 1px 3px; border-radius: 3px; }}
.status-ok {{ background: #dcfce7; color: #166534; }}
.status-warn {{ background: #fef9c3; color: #854d0e; }}
.status-bad {{ background: #fee2e2; color: #991b1b; }}
.ndvi-alert {{ padding: 6px 10px; border-radius: 4px; font-size: 11px; margin-bottom: 8px; }}
.ndvi-alert.danger {{ background: #fef2f2; border-left: 3px solid #EF4444; }}
.ndvi-alert.ok {{ background: #f0fdf4; border-left: 3px solid #10B981; }}
.ndvi-alert.warn {{ background: #fffbeb; border-left: 3px solid #F59E0B; }}
.options {{ display: flex; flex-direction: column; gap: 6px; }}
.option-card {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; }}
.option-card h4 {{ font-size: 12px; margin-bottom: 4px; }}
.option-card ul {{ list-style: none; font-size: 11px; color: #475569; }}
.option-card ul li {{ padding: 1px 0; }}
.option-card ul li::before {{ content: "├── "; color: #94a3b8; }}
.rec {{ font-size: 11px; padding: 6px 10px; background: #eff6ff; border-radius: 4px; border-left: 3px solid #3b82f6; margin-top: 6px; }}
.weather {{ background: white; border-radius: 8px; padding: 8px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: flex; align-items: center; gap: 16px; }}
.weather h2 {{ font-size: 13px; font-weight: 600; white-space: nowrap; }}
.weather select {{ font-size: 12px; padding: 3px 6px; border: 1px solid #d1d5db; border-radius: 4px; background: white; }}
.weather-chart {{ flex: 1; height: 50px; }}
.weather-metric {{ font-size: 11px; text-align: center; flex: 1; }}
.weather-metric .value {{ font-weight: 700; font-size: 14px; }}
.weather-metric .label {{ color: #64748b; font-size: 10px; }}
</style>
</head>
<body>
<div class="dashboard">
  <div class="header">
    <div class="header-left">
      <h1>🌽 Corn Soil Dashboard</h1>
      <div class="subtitle">DeKalb County, IL · {n_fields} fields · {total_ac:,} acres · Soil Quality Index (0–100)</div>
    </div>
  </div>

  <div class="narrative">{narrative}</div>

  <div class="content">
    <div class="left-panel">
      <div class="rankings">
        <h2>FIELD RANKINGS (best → worst)</h2>
        <div id="rankings-container"></div>
      </div>

      <div class="detail" id="detail-section">
        <div class="detail-header">
          <h2 id="detail-title">FIELD DETAIL</h2>
          <select id="field-selector">{field_options}</select>
        </div>
        <div id="detail-content">Select a field above to see details.</div>
      </div>
    </div>

    <div class="right-panel">
      <div class="priority" id="priority-section">
        {priority_html}
      </div>
    </div>
  </div>

  <div class="weather">
    <h2>WEATHER</h2>
    <select id="year-selector">
      <option value="2025" selected>2025</option>
      <option value="2024">2024</option>
      <option value="2023">2023</option>
      <option value="2022">2022</option>
      <option value="2021">2021</option>
    </select>
    <div id="weather-panel" class="weather-chart"></div>
  </div>
</div>

<script type="module">
import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

const SCORES = {scores_json};
const WEATHER = {weather_json};
const NDVI = {ndvi_json};
const ACTIONS = {actions_json};
const SOIL = {soil_json};

let selectedField = "{default_fid}";
let selectedYear = 2025;

// ── Rankings ──
function renderRankings() {{
  const container = document.getElementById("rankings-container");
  const rows = SCORES.map(s => {{
    const pct = s.score;
    const ndviData = NDVI[s.field_id]?.[selectedYear] || [];
    const ndviMean = ndviData.length ? (ndviData.reduce((a,b) => a+b,0) / ndviData.length).toFixed(3) : null;
    let color = pct >= 80 ? '#10B981' : pct >= 55 ? '#F59E0B' : '#EF4444';
    let tierIcon = pct >= 80 ? '🟢' : pct >= 65 ? '🟡' : pct >= 55 ? '🟠' : '🔴';

    let flag = "";
    if (!ndviMean) flag = "";
    else if (pct < 55 && parseFloat(ndviMean) < 0.65) flag = "⚠️ Soil+NDVI low";
    else if (pct >= 80 && parseFloat(ndviMean) >= 0.72) flag = "✅";
    else if (pct >= 80) flag = "⚠️ NDVI low";

    const sel = s.field_id === selectedField ? " selected" : "";
    const topPct = s.topsoil_score || 0;
    const subPct = s.subsoil_score || 0;

    return `<div class="rank-row${{sel}}" onclick="selectField('${{s.field_id}}')">
      <span class="rank-label">${{s.field_id}}</span>
      <div class="rank-bar-bg">
        <div class="rank-bar-fill" style="width:${{pct}}%;background:${{color}}"></div>
      </div>
      <span class="rank-score" style="color:${{color}}">${{pct}}</span>
      <span class="rank-ndvi" data-fid="${{s.field_id}}">—</span>
      <span class="rank-flag">${{flag}}</span>
      <span class="rank-sub" title="Topsoil / Subsoil score">
        T:<span class="rank-sub-bar" style="background:${{topPct >= 65 ? '#10B981' : '#EF4444'}};height:${{Math.max(2, topPct/10)}}px"></span>
        S:<span class="rank-sub-bar" style="background:${{subPct >= 50 ? '#10B981' : '#EF4444'}};height:${{Math.max(2, subPct/10)}}px"></span>
      </span>
    </div>`;
  }}).join('');
  container.innerHTML = rows;

  // Render NDVI sparklines
  container.querySelectorAll('.rank-ndvi').forEach(el => {{
    const fid = el.dataset.fid;
    const ndviData = NDVI[fid]?.[selectedYear] || [];
    if (ndviData.length) {{
      const svg = sparklineSVG(ndviData, 85, 14);
      el.innerHTML = '';
      el.appendChild(svg);
    }} else {{
      el.textContent = 'no data';
    }}
  }});
}}

function sparklineSVG(vals, w, h) {{
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", w); svg.setAttribute("height", h);
  svg.setAttribute("viewBox", `0 0 ${{vals.length - 1}} 1`);
  svg.style.overflow = "visible";
  const pts = vals.map((v, i) => `${{i}},${{1 - v}}`).join(' ');
  const pl = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  pl.setAttribute("points", pts); pl.setAttribute("fill", "none");
  pl.setAttribute("stroke", "#6366f1"); pl.setAttribute("stroke-width", "0.06");
  pl.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(pl);
  return svg;
}}

// ── Field selector ──
window.selectField = function(fid) {{
  selectedField = fid;
  document.getElementById("field-selector").value = fid;
  renderRankings();
  renderDetail();
}};
document.getElementById("field-selector").addEventListener("change", (e) => {{
  window.selectField(e.target.value);
}});

// ── Detail Section ──
function fieldMapSvg(fid, score, acres, name) {{
  const cx = 160, cy = 140;
  const size = 80 + (acres - 620) * 0.05;
  const color = score >= 80 ? '#10B981' : score >= 55 ? '#F59E0B' : '#EF4444';
  const opacity = 0.35 + score * 0.006;
  const pts = [
    [cx - size*0.6, cy - size*0.5], [cx + size*0.5, cy - size*0.55],
    [cx + size*0.7, cy], [cx + size*0.4, cy + size*0.5],
    [cx - size*0.3, cy + size*0.6], [cx - size*0.7, cy + size*0.1]
  ];
  const d = pts.map((p,i) => `${{i===0?'M':'L'}} ${{p[0]}} ${{p[1]}}`).join(' ')+' Z';
  return `<svg width="320" height="280" viewBox="0 0 320 280">
    <rect width="320" height="280" fill="#f8fafc"/>
    <path d="${{d}}" fill="${{color}}" fill-opacity="${{opacity}}" stroke="${{color}}" stroke-width="2"/>
    <text x="160" y="20" text-anchor="middle" font-size="9" fill="#94a3b8">${{name}} — ${{acres}} acres</text>
    <text x="160" y="${{cy - 15}}" text-anchor="middle" font-size="11" font-weight="700" fill="${{color}}">Soil Quality: ${{score}}/100</text>
    <text x="160" y="${{cy + 5}}" text-anchor="middle" font-size="9" fill="#94a3b8">Corn suitability ${{score >= 80 ? 'Excellent' : score >= 55 ? 'Needs attention' : 'Critical'}}</text>
  </svg>`;
}}

function renderDetail() {{
  const field = SCORES.find(s => s.field_id === selectedField);
  if (!field) return;
  const action = ACTIONS.find(a => a.field_id === selectedField) || {{}};
  const soilData = SOIL[field.field_id];
  const ndviData = NDVI[field.field_id]?.[selectedYear] || [];
  const ndviMean = ndviData.length ? (ndviData.reduce((a,b) => a+b,0) / ndviData.length).toFixed(3) : null;
  const isGood = field.score >= 80;
  const ndviLow = ndviMean && parseFloat(ndviMean) < 0.65;

  const mapSvg = fieldMapSvg(field.field_id, field.score, field.acres, field.name);

  // Soil profile
  let profileHtml = '';
  if (soilData && soilData.layers) {{
    const depthLabels = ['0-6"', '6-12"', '12-24"'];
    soilData.layers.forEach((l, i) => {{
      const omPct = Math.min(100, Math.round(l.om_r / 5.0 * 100));
      const phPct = Math.min(100, Math.round(l.ph1to1h2o_r / 8.0 * 100));
      const awcPct = Math.min(100, Math.round(l.awc_r / 0.25 * 100));
      const omS = l.om_r >= 3.0 ? 'ok' : l.om_r >= 2.0 ? 'warn' : 'bad';
      const phS = (l.ph1to1h2o_r >= 6.0 && l.ph1to1h2o_r <= 7.0) ? 'ok' : (l.ph1to1h2o_r >= 5.5) ? 'warn' : 'bad';
      const awcS = l.awc_r >= 0.15 ? 'ok' : l.awc_r >= 0.10 ? 'warn' : 'bad';
      profileHtml += `
        <div style="font-size:10px;font-weight:600;color:#94a3b8;margin-top:3px">${{depthLabels[i]}}</div>
        <div class="profile-row"><span>OM</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{omPct}}%;background:#${{omS==='ok'?'10B981':omS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.om_r}}%</span><span class="profile-status status-${{omS}}">${{omS==='ok'?'✓':omS==='warn'?'~':'✗'}}</span></div>
        <div class="profile-row"><span>pH</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{phPct}}%;background:#${{phS==='ok'?'10B981':phS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.ph1to1h2o_r}}</span><span class="profile-status status-${{phS}}">${{phS==='ok'?'✓':phS==='warn'?'~':'✗'}}</span></div>
        <div class="profile-row"><span>AWC</span><div class="profile-bar-bg"><div class="profile-bar-fill" style="width:${{awcPct}}%;background:#${{awcS==='ok'?'10B981':awcS==='warn'?'F59E0B':'EF4444'}}"></div></div><span>${{l.awc_r}}</span><span class="profile-status status-${{awcS}}">${{awcS==='ok'?'✓':awcS==='warn'?'~':'✗'}}</span></div>`;
    }});
    profileHtml += '<div style="font-size:9px;color:#94a3b8;margin-top:3px">✓ corn optimal ~ borderline ✗ outside range</div>';
  }}

  // NDVI alert
  let ndviAlertHtml = '';
  if (ndviBothLow(isGood, ndviMean)) {{
    ndviAlertHtml = `<div class="ndvi-alert danger">⚠️ <strong>Soil score (${{field.score}}) AND NDVI (${{ndviMean}}) are both low.</strong> Soil limitations are likely reducing plant vigor. Consider remediation or crop switching.</div>`;
  }} else if (isGood && ndviMean && parseFloat(ndviMean) >= 0.72) {{
    ndviAlertHtml = '<div class="ndvi-alert ok">✅ Soil and NDVI both look good — field is performing as expected.</div>';
  }} else if (isGood && ndviLow) {{
    ndviAlertHtml = `<div class="ndvi-alert warn">⚠️ Soil score is good but NDVI is lower than expected (${{ndviMean}}). May indicate management or weather factors, not soil problems.</div>`;
  }}

  // Options
  let optionsHtml = '';
  if (isGood) {{
    optionsHtml = `<div class="option-card" style="border-left:3px solid #10B981">
      <h4 style="color:#166534">✅ No Action Needed</h4>
      <ul>
        <li>Soil Quality Index: ${{field.score}}/100 — all depths within optimal range</li>
        <li>Estimated corn yield: ${{Math.round(action.base_yield_corn_bu_ac || 180)}} bu/acre</li>
        <li>Revenue: ~$${{Math.round(action.revenue_current_per_ac || 990)}}/acre</li>
        <li>Maintain current practices — annual soil testing recommended</li>
      </ul>
    </div>`;
  }} else {{
    optionsHtml = `<div class="option-card" style="border-left:3px solid #10B981">
      <h4 style="color:#166534">OPTION 1: FIX FOR CORN (Recommended long-term)</h4>
      <ul>
        ${{(action.fix_details || '').split(' | ').filter(d => d && d.indexOf(':') === -1).map(d => '<li>'+d+'</li>').join('')}}
        <li><strong>Cost:</strong> $${{action.fix_cost_per_ac || 0}}/acre</li>
        <li><strong>Yield:</strong> ${{action.base_yield_corn_bu_ac || 0}} → ${{action.fixed_yield_corn_bu_ac || 0}} bu/acre</li>
        <li><strong>Revenue after fix:</strong> ~$${{action.revenue_fixed_per_ac || 0}}/acre</li>
        <li><strong>Payback:</strong> ${{(action.payback_years || 0).toFixed(1)}} years</li>
      </ul>
    </div>
    <div class="option-card" style="border-left:3px solid #F59E0B">
      <h4 style="color:#92400E">OPTION 2: SWITCH TO SOYBEANS (Lower risk)</h4>
      <ul>
        <li>Cost: $0 (saves nitrogen fertilizer for corn)</li>
        <li>Expected yield: ${{action.soy_yield_bu_ac || 0}} bu/acre</li>
        <li>Revenue: ~$${{action.revenue_soy_per_ac || 0}}/acre</li>
        <li>Soybeans tolerate marginal/poorly-drained soils better than corn</li>
      </ul>
    </div>
    <div class="option-card" style="border-left:3px solid #94a3b8">
      <h4 style="color:#475569">OPTION 3: DO NOTHING</h4>
      <ul>
        <li>Cost: $0</li>
        <li>Current revenue: ~$${{action.revenue_current_per_ac || 0}}/acre</li>
        <li>Risk: Yield may decline as soil degrades further</li>
      </ul>
    </div>`;
  }}

  let recHtml = '';
  if (!isGood) {{
    const pb = (action.payback_years || 0);
    const fc = (action.fix_cost_per_ac || 0);
    const rs = Math.round(action.revenue_soy_per_ac || 0);
    let msg;
    if (pb <= 3.0) {{
      msg = 'Fix for corn now — invest $' + fc + '/acre, breaks even in ' + pb.toFixed(1) + ' years.';
    }} else {{
      msg = 'Consider switching to soybeans — lower revenue (~$' + rs + '/ac) but zero upfront cost and less risk on marginal soil.';
    }}
    recHtml = '<div class="rec"><strong>Recommendation:</strong> ' + msg + '</div>';
  }}

  document.getElementById("detail-title").textContent = `FIELD DETAIL: ${{field.field_id}} — ${{field.name}}`;
  document.getElementById("detail-content").innerHTML = `
    <div class="detail-grid">
      <div class="map-panel">${{mapSvg}}</div>
      <div class="profile-panel">
        <h3>Soil Profile by Depth</h3>
        ${{profileHtml}}
      </div>
    </div>
    ${{ndviAlertHtml}}
    <div class="options">${{optionsHtml}}</div>
    ${{recHtml}}
  `;
}}

function ndviBothLow(isGood, ndviMean) {{
  return !isGood && ndviMean && parseFloat(ndviMean) < 0.65;
}}

// ── Weather ──
function renderWeather() {{
  const panel = document.getElementById("weather-panel");
  const yearData = WEATHER.filter(d => d.year === selectedYear);
  if (yearData.length === 0) {{ panel.innerHTML = '<span style="color:#94a3b8;font-size:11px">No data for '+selectedYear+'</span>'; return; }}

  const months = [1,2,3,4,5,6,7,8,9,10,11,12];
  const mRain = months.map(m => yearData.filter(d => new Date(d.date).getMonth()+1 === m).reduce((s,d) => s+(d.PRECTOTCORR||0), 0));
  const annualRain = mRain.reduce((a,b) => a+b, 0);
  const mTemp = months.map(m => {{
    const days = yearData.filter(d => new Date(d.date).getMonth()+1 === m);
    return days.length ? days.reduce((s,d) => s+(d.T2M||0),0)/days.length : 0;
  }});
  const annualTemp = mTemp.reduce((a,b) => a+b, 0)/12;

  const growDays = yearData.filter(d => {{
    const m = new Date(d.date).getMonth()+1;
    return m >= 4 && m <= 9;
  }});
  const annualGdd = Math.round(growDays.reduce((s,d) => s + Math.max(0,((d.T2M_MAX||70)+(d.T2M_MIN||50))/2-50), 0));

  // Anomaly check
  const allGrow = WEATHER.filter(d => {{
    const m = new Date(d.date).getMonth()+1;
    return d.year >= 2021 && d.year <= 2025 && m >= 4 && m <= 9;
  }});
  const avgRain = Math.round(allGrow.reduce((s,d) => s+(d.PRECTOTCORR||0),0) / 5);
  const thisRain = yearData.filter(d => {{ const m=new Date(d.date).getMonth()+1; return m>=4 && m<=9; }}).reduce((s,d) => s+(d.PRECTOTCORR||0), 0);
  const rainPct = avgRain > 0 ? Math.round(thisRain/avgRain*100) : 100;
  const anomalyLabel = rainPct > 130 ? '⚠️ Wet' : rainPct < 70 ? '⚠️ Dry' : '✅ Normal';
  const anomalyColor = rainPct > 130 ? '#EF4444' : rainPct < 70 ? '#F59E0B' : '#10B981';
  const soilReliable = rainPct <= 150 && rainPct >= 60;

  panel.innerHTML = `
    <div style="display:flex;gap:12px;align-items:flex-start;justify-content:space-between">
      <div class="weather-metric">
        <div class="value">${{annualRain.toFixed(1)}}″</div>
        <div class="label">Rainfall</div>
        ${{miniChartSVG(mRain, Math.max(...mRain, 1), 120, 30)}}
      </div>
      <div class="weather-metric">
        <div class="value">${{annualTemp.toFixed(1)}}°F</div>
        <div class="label">Avg Temp</div>
        ${{miniChartSVG(mTemp, Math.max(...mTemp, 1), 120, 30)}}
      </div>
      <div class="weather-metric">
        <div class="value">${{annualGdd}}</div>
        <div class="label">GDD (Base 50°F)</div>
        <div style="font-size:9px;color:#64748b">Apr–Sep cumulative</div>
      </div>
      <div class="weather-metric">
        <div class="value" style="color:${{anomalyColor}}">${{anomalyLabel}}</div>
        <div class="label">${{rainPct}}% of avg rain</div>
        <div style="font-size:9px;color:#94a3b8">Soil readings ${{soilReliable ? 'reliable' : 'may be affected'}}</div>
      </div>
    </div>
  `;
}}

function miniChartSVG(vals, maxVal, w, h) {{
  if (vals.length === 0) return '';
  const svg = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 ${{vals.length-1}} ${{maxVal}}" style="overflow:visible">
    <polyline fill="none" stroke="#3b82f6" stroke-width="0.15" vector-effect="non-scaling-stroke"
      points="${{vals.map((v,i)=>`${{i}},${{maxVal-v}}`).join(' ')}}"/>
    <circle cx="${{vals.length-1}}" cy="${{maxVal-vals[vals.length-1]}}" r="0.3" fill="#3b82f6"/>
  </svg>`;
  return svg;
}}

// ── Year selector ──
document.getElementById("year-selector").addEventListener("change", (e) => {{
  selectedYear = parseInt(e.target.value);
  renderWeather();
  renderRankings();
  renderDetail();
}});

// ── Init ──
renderRankings();
renderDetail();
renderWeather();
</script>
</body>
</html>"""

    return html


def _first_detail(details: str) -> str:
    if not details:
        return "Soil quality below threshold"
    parts = details.split(" | ")
    return parts[0] if parts else details[:80]


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
