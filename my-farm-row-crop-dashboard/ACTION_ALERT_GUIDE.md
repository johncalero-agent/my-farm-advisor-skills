# Action Alert Guide — How Alerts Are Triggered & Resolved

This document explains each action alert type in the Row Crop Intelligence Dashboard: what triggers it, what severity level means, and the detailed agronomic recommendations provided.

## Alert Color System

Each alert has a **unique, non-overlapping color** so there is never confusion about which problem is being highlighted:

| Alert | Color | Hex Code | Visual |
|---|---|---|---|
| Nitrogen Leaching Risk | Deep Purple | `#7C3AED` | 🟣 |
| Compaction Stress | Dark Brown | `#92400E` | 🟤 |
| Acidity Lockup | Bright Amber | `#F59E0B` | 🟡 |
| Drought Susceptibility | Sandy Desert | `#D97706` | 🟠 |
| Waterlogging Risk | Deep Cyan | `#0891B2` | 🔵 |

These colors are **reserved exclusively for alert identification**. No chart, map element, or other dashboard component will use these same colors.

## Severity Levels

| Level | Meaning |
|---|---|
| **Critical** | The soil constraint is severe and will significantly impact soybean yield if not addressed. Immediate intervention recommended. |
| **Warning** | The constraint is present but moderate. Monitor and plan for intervention in the next 1–2 growing seasons. |
| **None** | No constraint detected. The soil property is within acceptable range for soybeans. |

---

## Alert #1: Nitrogen Leaching Risk 🟣

### Trigger Conditions
- Sand content > 65%
- AND Organic matter < 2.0%

### Critical Threshold
- Sand > 75% AND OM < 1.5%

### Why It Matters for Soybeans
Sandy soils with low organic matter have very low cation exchange capacity (CEC), meaning nitrogen applied in soluble forms (nitrate) moves rapidly through the soil profile. While soybeans fix their own nitrogen, they still require 40–60 lbs N/acre for early growth before nodulation is established, and the crop removes approximately 3.5–4.0 lbs N per bushel of yield. In leaching-prone soils, residual N from previous crops or applied starter N may be lost before roots can access it.

### Recommendation
1. Apply 15–20% additional nitrogen as split application (50% at planting, 50% at R1).
2. Incorporate a nitrification inhibitor (e.g., nitrapyrin/N-Serve at 0.5 lb a.i./acre).
3. Apply 2–3 tons/acre composted manure in fall to build organic matter.
4. Plant cereal rye cover crop at 40–60 lb/acre after corn harvest.
5. Monitor leaf N at R3; tissue N below 4.0% indicates deficiency.

---

## Alert #2: Compaction Stress 🟤

### Trigger Conditions
- Bulk density > 1.55 g/cm³
- AND Clay content > 30%

### Critical Threshold
- Bulk density > 1.65 g/cm³ AND Clay > 35%

### Why It Matters for Soybeans
Compacted soil layers restrict soybean taproot development and limit nodulation depth. Soybean roots need to penetrate to at least 18–24 inches for optimal water and nutrient access. Compaction reduces pore space, limiting oxygen to roots and rhizobia, which directly reduces nitrogen fixation capacity.

### Recommendation
1. Deep tillage with ripper shanks set to 16–18" depth in fall after harvest.
2. Plant deep-taproot cover crops (tillage radish at 8–10 lb/acre, cereal rye at 40–60 lb/acre).
3. Designate controlled traffic lanes; avoid field operations above 70% field capacity moisture.
4. Consider full-season cover crop fallow every 3–4 years in affected zones.
5. Monitor with yield maps to verify response.

---

## Alert #3: Acidity Lockup 🟡

### Trigger Conditions
- pH < 6.3

### Critical Threshold
- pH < 5.8

### Why It Matters for Soybeans
This is the single most important alert for soybeans. Rhizobium japonicum bacteria are highly pH-sensitive—their activity declines significantly below pH 6.3. Additionally, phosphorus availability (critical for nodulation energy) decreases in acidic soils, and aluminum toxicity can occur below pH 5.5. Molybdenum, essential for nitrogenase enzyme function, also becomes less available.

### Recommendation
1. Apply 2.0–2.5 tons/acre agricultural lime (ENV 90%) based on buffer pH.
2. Apply lime in fall, 6–12 months before soybean planting, incorporated to 6" depth.
3. For rates > 2.5 tons/acre, split into two applications 6 months apart.
4. Use fresh peat-based Bradyrhizobium inoculant at 2× standard rate when pH is 6.0–6.3.
5. Retest soil pH at 0–6" and 6–12" depths after 12 months.

---

## Alert #4: Drought Susceptibility 🟠

### Trigger Conditions
- Sand content > 60%
- OR AWC property score < 35/100

### Critical Threshold
- Sand > 70% AND AWC score < 25/100

### Why It Matters for Soybeans
Soybeans are most sensitive to drought during R3–R5 (pod development and seed fill), requiring 0.25–0.30 inches of water per day during this period. Coarse-textured soils with low water-holding capacity cannot buffer against even short dry periods during this critical window, leading to flower abortion, reduced pod set, and smaller seed size.

### Recommendation
1. Schedule irrigation at 50% depletion in upper 24" of soil profile; use soil moisture sensors.
2. Increase seeding rate by 10–15% (140,000–160,000 seeds/acre) in affected zones.
3. Maintain minimum 30% surface residue cover to reduce evaporation.
4. Build organic matter through compost (3–4 tons/acre) or high-biomass cover crops.
5. Select drought-tolerant soybean varieties with determinate growth habit.

---

## Alert #5: Waterlogging Risk 🔵

### Trigger Conditions
- Drainage class is "Poorly drained," "Very poorly drained," or "Somewhat poorly drained"
- AND Clay content > 35%

### Critical Threshold
- Drainage class is "Very poorly drained" or "Poorly drained" AND Clay > 40%

### Why It Matters for Soybeans
Saturated soils reduce oxygen availability to roots and rhizobia. Soybeans can tolerate only 24–48 hours of saturated conditions before significant damage occurs. Each day of saturation beyond 48 hours causes approximately 1–2% yield loss. Waterlogged conditions also increase the risk of root rot diseases (Phytophthora, Pythium) and reduce nodulation.

### Recommendation
1. Install subsurface tile drainage at 50–60 foot spacing and 3.5–4.0 foot depth.
2. Install shallow surface drains or grade to achieve minimum 0.5% slope.
3. Convert to 30" raised beds (6–8" height) where tile is not feasible.
4. If drainage cannot be improved, consider transitioning zone to winter wheat (more water-tolerant).
5. Delay planting in poorly-drained zones by 7–10 days relative to well-drained areas.
