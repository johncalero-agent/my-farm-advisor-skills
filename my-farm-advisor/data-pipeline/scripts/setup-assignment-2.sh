#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
REPO_ROOT="$(cd "${SKILL_DIR}/../.." && pwd -P)"

die() {
  echo "[setup-assignment-2] $*" >&2
  exit 2
}

log() {
  echo "[setup-assignment-2] $*" >&2
}

if [[ -z "${DATA_PIPELINE_DATA_ROOT:-}" ]]; then
  die "DATA_PIPELINE_DATA_ROOT is required. Run install.sh first, then export DATA_PIPELINE_DATA_ROOT=<path>"
fi

RESOLVED_ROOT="$(cd "${DATA_PIPELINE_DATA_ROOT}" 2>/dev/null && pwd -P || die "DATA_PIPELINE_DATA_ROOT does not exist: ${DATA_PIPELINE_DATA_ROOT}")"
RUNTIME_SRC="${RESOLVED_ROOT}/data-pipeline/src"
RUNTIME_VENV="${DATA_PIPELINE_VENV_DIR:-${RESOLVED_ROOT}/data-pipeline/.venv}"

[[ -d "${RUNTIME_SRC}" ]] || die "Runtime source not found at ${RUNTIME_SRC}. Run install.sh first."
[[ -x "${RUNTIME_VENV}/bin/python" ]] || die "Runtime venv not found at ${RUNTIME_VENV}. Run install.sh first."

PYTHON="${RUNTIME_VENV}/bin/python"
EXAMPLES_DIR="${REPO_ROOT}/my-farm-advisor/field-management/field-boundaries/examples"

generate_inventory_csv() {
  local geojson="$1"
  local csv="$2"
  mkdir -p "$(dirname "$csv")"
  "${PYTHON}" -c "
import csv, json
with open('${geojson}') as f:
    fc = json.load(f)
with open('${csv}', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['field_id', 'field_slug'])
    for feat in fc['features']:
        fid = feat['properties']['field_id']
        slug = fid.lower().replace('_', '-')
        w.writerow([fid, slug])
"
  log "  Inventory CSV: ${csv}"
}

run_ingest() {
  local grower_slug="$1"
  local farm_slug="$2"
  local farm_name="$3"
  local geojson="$4"
  local inventory_csv="$5"

  local ingest_dir="${RUNTIME_SRC}/scripts/ingest"
  local growers_dir="${RESOLVED_ROOT}/data-pipeline/growers"
  local canonical_boundary="${growers_dir}/${grower_slug}/farms/${farm_slug}/boundary/field_boundaries.geojson"

  mkdir -p "$(dirname "${canonical_boundary}")"
  cp "${geojson}" "${canonical_boundary}"

  log "  Generating inventory CSV..."
  generate_inventory_csv "${geojson}" "${inventory_csv}"

  export AG_GROWER_SLUG="${grower_slug}"
  export AG_FARM_SLUG="${farm_slug}"
  export AG_FARM_NAME="${farm_name}"
  export AG_BOUNDARIES="${canonical_boundary}"
  export AG_INVENTORY_CSV="${inventory_csv}"
  export AG_WEATHER_BACKEND="zarr"
  export AG_WEATHER_START_YEAR="2021"
  export AG_WEATHER_END_YEAR="2025"
  export AG_WEATHER_TIME_STANDARD="lst"
  export AG_FORCE="1"
  export DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}"

  log "  Step 1: Field boundaries..."
  "${PYTHON}" "${ingest_dir}/download_fields.py"

  log "  Step 2: Weather data..."
  "${PYTHON}" "${ingest_dir}/download_weather.py"

  log "  Step 3: CDL/cropland data..."
  "${PYTHON}" "${ingest_dir}/download_cdl.py" || log "  Warning: CDL step completed with issues"
}

log "=========================================="
log "Assignment 2: Creating growers with 10 fields each"
log "=========================================="
log ""

# ──────────────────────────────────────────────
# Step 1: Illinois grower (already seeded, verify only)
# ──────────────────────────────────────────────
IL_SLUG="il-dekalb-grower"
IL_FARM="dekalb-demo-farm"
IL_INVENTORY="${RESOLVED_ROOT}/data-pipeline/growers/${IL_SLUG}/farms/${IL_FARM}/manifests/field-inventory.csv"
IL_COUNT=0
[[ -f "${IL_INVENTORY}" ]] && IL_COUNT=$(tail -n +2 "${IL_INVENTORY}" | wc -l)
log "Illinois: ${IL_SLUG}/${IL_FARM} has ${IL_COUNT} field(s)"
if [[ "${IL_COUNT}" -lt 10 ]]; then
  log "  Processing Illinois grower..."
  run_ingest "${IL_SLUG}" "${IL_FARM}" "DeKalb Demo Farm" \
    "${EXAMPLES_DIR}/real_10_fields_illinois.geojson" "${IL_INVENTORY}"
fi
log ""

# ──────────────────────────────────────────────
# Step 2: Iowa grower
# ──────────────────────────────────────────────
IA_SLUG="iowa-grower"
IA_FARM="iowa-grower-iowa"
IA_INVENTORY="${RESOLVED_ROOT}/data-pipeline/growers/${IA_SLUG}/farms/${IA_FARM}/manifests/field-inventory.csv"
IA_COUNT=0
[[ -f "${IA_INVENTORY}" ]] && IA_COUNT=$(tail -n +2 "${IA_INVENTORY}" | wc -l)
log "Iowa: ${IA_SLUG}/${IA_FARM} has ${IA_COUNT} field(s)"
if [[ "${IA_COUNT}" -lt 10 ]]; then
  log "  Processing Iowa grower..."
  run_ingest "${IA_SLUG}" "${IA_FARM}" "Iowa Farm" \
    "${EXAMPLES_DIR}/real_10_fields_iowa.geojson" "${IA_INVENTORY}"
fi
log ""

# ──────────────────────────────────────────────
# Step 3: Nebraska grower
# ──────────────────────────────────────────────
NE_SLUG="nebraska-grower"
NE_FARM="nebraska-farm"
NE_INVENTORY="${RESOLVED_ROOT}/data-pipeline/growers/${NE_SLUG}/farms/${NE_FARM}/manifests/field-inventory.csv"
NE_COUNT=0
[[ -f "${NE_INVENTORY}" ]] && NE_COUNT=$(tail -n +2 "${NE_INVENTORY}" | wc -l)
log "Nebraska: ${NE_SLUG}/${NE_FARM} has ${NE_COUNT} field(s)"
if [[ "${NE_COUNT}" -lt 10 ]]; then
  log "  Processing Nebraska grower..."
  run_ingest "${NE_SLUG}" "${NE_FARM}" "Nebraska Farm" \
    "${EXAMPLES_DIR}/real_10_fields_nebraska.geojson" "${NE_INVENTORY}"
fi
log ""

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
count_fields() {
  local slug="$1"
  local farm="$2"
  local inv="${RESOLVED_ROOT}/data-pipeline/growers/${slug}/farms/${farm}/manifests/field-inventory.csv"
  if [[ -f "${inv}" ]]; then
    tail -n +2 "${inv}" | wc -l
  else
    echo 0
  fi
}

log "=========================================="
log "Assignment 2 setup complete!"
log ""
log "Grower summary:"
log "  ${IL_SLUG}/${IL_FARM} -> $(count_fields "${IL_SLUG}" "${IL_FARM}") fields (Illinois)"
log "  ${IA_SLUG}/${IA_FARM} -> $(count_fields "${IA_SLUG}" "${IA_FARM}") fields (Iowa)"
log "  ${NE_SLUG}/${NE_FARM} -> $(count_fields "${NE_SLUG}" "${NE_FARM}") fields (Nebraska)"
log ""
log "Outputs for EDA:"
log "  Boundaries: growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson"
log "  Per-field:  growers/<grower>/farms/<farm>/fields/<field>/boundary/field_boundary.geojson"
log "  Weather:    growers/<grower>/farms/<farm>/fields/<field>/weather/daily_weather.csv"
log "  CDL:        growers/<grower>/farms/<farm>/derived/tables/<farm>_<year>_cdl.csv"
log "=========================================="
