# Soybean Soil Health Score — Formula & Methodology

This document explains how the Soil Health Score is calculated for each field in the Row Crop Intelligence Dashboard. It is designed to be transparent and understandable to growers, agronomists, and other stakeholders.

## Purpose

The Soil Health Score provides a single, easy-to-interpret number (0–100) that reflects how well a field's soil profile supports soybean production. The score integrates five key soil properties, weighted by their relative importance to soybean growth, and accounts for how those properties change with depth in the root zone.

## Score Interpretation

| Score Range | Status | What It Means |
|---|---|---|
| **80–100** | Excellent | Optimal conditions for soybeans. Soil properties are within ideal ranges. Continue current management practices. |
| **60–79** | Healthy | Good conditions with minor limitations. Targeted improvements (e.g., pH adjustment in a small area) could push this field into excellent range. |
| **40–59** | Monitor | Moderate limitations exist. One or more soil properties deviate from optimal ranges. Address specific alerts to improve. |
| **Below 40** | High Priority | Significant soil constraints that will likely limit soybean yield. Multiple interventions recommended. |

## The Five Properties (Soybean-Specific Weights)

Each property's weight reflects its relative importance to soybean health:

| Property | Weight | Optimal Range (Soybeans) | Why It Matters |
|---|---|---|---|
| **Organic Matter (OM)** | 30% | ≥ 3.0% | Critical for water holding, nutrient availability, and soil biology. Soybeans benefit from higher OM for phosphorus availability and microbial activity supporting nitrogen fixation. |
| **pH Balance** | 25% | 6.3–7.0 | The most important single factor for soybeans. Rhizobium bacteria responsible for nitrogen fixation are pH-sensitive; their activity declines sharply below pH 6.3. Phosphorus, molybdenum, and boron availability also peak in this range. |
| **Available Water Capacity (AWC)** | 20% | ≥ 0.15 cm/cm | Determines how much plant-available water the soil can hold. Critical during R3–R5 pod fill when soybeans require 0.25–0.30 inches of water per day. |
| **Bulk Density** | 15% | ≤ 1.45 g/cm³ | Indicator of compaction. Soybean taproots need uncompacted soil for deep rooting and nodulation. Bulk density above 1.55 g/cm³ restricts root penetration. |
| **Drainage Class** | 10% | Well drained – Moderately well drained | Soybeans are sensitive to waterlogging. Saturated conditions beyond 24–48 hours reduce oxygen to roots and rhizobia, limiting nitrogen fixation. |

## Depth-Weighted Calculation

The score incorporates soil properties from **three depth zones** in the full root zone (0–60 cm), with weights reflecting the relative importance of each zone to annual soybean growth:

| Depth Zone | Range | Weight | Rationale |
|---|---|---|---|
| **Topsoil** | 0–15 cm | 40% | The most biologically active zone. Contains the majority of organic matter and nutrients. Where most soybean lateral roots and early nodulation occur. |
| **Upper Root Zone** | 15–30 cm | 35% | Important for water and nutrient uptake during vegetative growth. Soybean taproot reaches this zone by V4–V6. |
| **Lower Root Zone** | 30–60 cm | 25% | Provides deeper water access during reproductive stages. Important for drought resilience during pod fill. |

### How Depth Weighting Works

For each depth zone and each soil property, the dashboard:

1. Identifies all SSURGO soil horizons that overlap with the zone.
2. Computes a component-percentage-weighted average of the property value within that zone.
3. Scores the property value against the optimal range (0–100 scale).
4. Multiplies the zone score by the zone weight (40% / 35% / 25%).
5. Sums across all three zones to get the property's overall score.

Example: If OM is 4.5% in topsoil (score 100), 3.2% in upper root (score 100), but 1.8% in lower root (score 60):

`OM Score = (100 × 0.40) + (100 × 0.35) + (60 × 0.25) = 90`

## Overall Score Calculation

```
Overall Score = (OM Score × 0.30)
              + (pH Score × 0.25)
              + (AWC Score × 0.20)
              + (Bulk Density Score × 0.15)
              + (Drainage Score × 0.10)
```

## Scoring Functions (How Individual Properties Are Scored)

### Higher-Better Properties (OM, AWC)
Properties where higher values are beneficial:
- If value ≥ optimal minimum → Score = 100
- If value ≤ critical low → Score = 0
- Otherwise → Linear interpolation between critical low and optimal minimum

### Lower-Better Properties (Bulk Density)
Properties where lower values are beneficial:
- If value ≤ optimal maximum → Score = 100
- If value ≥ critical high → Score = 0
- Otherwise → Linear interpolation between optimal maximum and critical high

### Near-Optimal Properties (pH)
Properties with a target range:
- If optimal_min ≤ value ≤ optimal_max → Score = 100
- If value is below optimal_min → Linear decline to critical_low (0)
- If value is above optimal_max → Linear decline to critical_high (0)

### Drainage Class Scoring
Drainage is scored categorically based on SSURGO drainage classifications:

| Drainage Class | Score |
|---|---|
| Well drained | 100 |
| Moderately well drained | 80 |
| Somewhat excessively drained | 55 |
| Somewhat poorly drained | 45 |
| Excessively drained | 40 |
| Poorly drained | 20 |
| Very poorly drained | 10 |

## Conservation Priority Index

Fields with an overall score below 40 are flagged as **High Conservation Priority**, meaning the soil limitations are severe enough that significant intervention (drainage, liming, organic amendments) is recommended before expecting optimal soybean yields. These fields may also be candidates for alternative crops better suited to their soil profile.

## Data Sources

- **Soil properties:** USDA NRCS Soil Data Access (SDA) — SSURGO database
- **Horizon data:** `chorizon` table, including `hzdept_r` (horizon top depth) and `hzdepb_r` (horizon bottom depth)
- **Component data:** `component` table, including `comppct_r` (component percentage)

## Limitations

- SSURGO data represents map unit averages at 1:12,000 to 1:24,000 scale. Actual field variability may exceed what is captured.
- The scoring is calibrated for soybeans (Glycine max). Different crops use different optimal ranges.
- Weather factors (precipitation, temperature, GDD) are not included in the soil score itself but are presented separately in the dashboard's weather section.
- This score reflects soil **potential** — actual yields depend on management, weather, pests, and other factors.
