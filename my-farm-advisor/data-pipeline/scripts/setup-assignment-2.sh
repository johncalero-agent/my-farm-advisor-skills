#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

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
BOOTSTRAP="${RUNTIME_SRC}/scripts/ingest/bootstrap_farm_from_county.py"
DASHBOARD="${RUNTIME_SRC}/scripts/farm_dashboard.py"
GROWERS_DIR="${RESOLVED_ROOT}/data-pipeline/growers"

count_fields() {
  local grower_slug="$1"
  local farm_slug="$2"
  local inventory="${GROWERS_DIR}/${grower_slug}/farms/${farm_slug}/manifests/field-inventory.csv"
  if [[ -f "${inventory}" ]]; then
    tail -n +2 "${inventory}" | wc -l
  else
    echo 0
  fi
}

TARGET_FIELD_COUNT=10

log "=========================================="
log "Assignment 2: Expanding growers to ${TARGET_FIELD_COUNT} fields each"
log "=========================================="
log ""

# ──────────────────────────────────────────────
# Step 1: Expand Illinois grower
# ──────────────────────────────────────────────
IL_SLUG="il-dekalb-grower"
IL_FARM="dekalb-demo-farm"
IL_EXISTING=$(count_fields "${IL_SLUG}" "${IL_FARM}")
IL_NEED=$((TARGET_FIELD_COUNT - IL_EXISTING))

log "Illinois: ${IL_SLUG}/${IL_FARM} has ${IL_EXISTING} field(s), needs ${IL_NEED} more"

if [[ ${IL_NEED} -gt 0 ]]; then
  log "  Running bootstrap for DeKalb county, IL (${IL_NEED} fields, append mode)..."
  DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}" \
    "${PYTHON}" "${BOOTSTRAP}" \
    --state-fips 17 \
    --county-name DeKalb \
    --count "${IL_NEED}" \
    --seed 42 \
    --grower-slug "${IL_SLUG}" \
    --farm-slug "${IL_FARM}" \
    --farm-name "DeKalb Demo Farm" \
    --append
  log "  Illinois grower expanded."
else
  log "  Illinois grower already has ${TARGET_FIELD_COUNT} or more fields; skipping."
fi
log ""

# ──────────────────────────────────────────────
# Step 2: Expand Iowa grower
# ──────────────────────────────────────────────
IA_SLUG="iowa-grower"
IA_FARM="iowa-grower-iowa"
IA_EXISTING=$(count_fields "${IA_SLUG}" "${IA_FARM}")
IA_NEED=$((TARGET_FIELD_COUNT - IA_EXISTING))

log "Iowa: ${IA_SLUG}/${IA_FARM} has ${IA_EXISTING} field(s), needs ${IA_NEED} more"

if [[ ${IA_NEED} -gt 0 ]]; then
  log "  Running bootstrap for Story county, IA (${IA_NEED} fields, append mode)..."
  DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}" \
    "${PYTHON}" "${BOOTSTRAP}" \
    --state-fips 19 \
    --county-name Story \
    --count "${IA_NEED}" \
    --seed 43 \
    --grower-slug "${IA_SLUG}" \
    --farm-slug "${IA_FARM}" \
    --farm-name "Iowa Farm" \
    --append
  log "  Iowa grower expanded."
else
  log "  Iowa grower already has ${TARGET_FIELD_COUNT} or more fields; skipping."
fi
log ""

# ──────────────────────────────────────────────
# Step 3: Add Nebraska grower
# ──────────────────────────────────────────────
NE_SLUG="nebraska-grower"
NE_FARM="nebraska-farm"
NE_EXISTING=$(count_fields "${NE_SLUG}" "${NE_FARM}")
NE_NEED=$((TARGET_FIELD_COUNT - NE_EXISTING))

log "Nebraska: ${NE_SLUG}/${NE_FARM} has ${NE_EXISTING} field(s), needs ${NE_NEED} more"

if [[ ${NE_NEED} -eq ${TARGET_FIELD_COUNT} ]]; then
  log "  Creating new Nebraska grower via farm_dashboard.py..."
  DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}" \
    "${PYTHON}" "${DASHBOARD}" create \
    --state Nebraska \
    --field-count "${TARGET_FIELD_COUNT}" \
    --seed 44 \
    --grower-slug "${NE_SLUG}" \
    --farm-slug "${NE_FARM}" \
    --farm-name "Nebraska Farm"
  log "  Nebraska grower created."
elif [[ ${NE_NEED} -gt 0 ]]; then
  log "  Expanding Nebraska grower via bootstrap (${NE_NEED} fields, append mode)..."
  DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}" \
    "${PYTHON}" "${BOOTSTRAP}" \
    --state-fips 31 \
    --county-name Lancaster \
    --count "${NE_NEED}" \
    --seed 44 \
    --grower-slug "${NE_SLUG}" \
    --farm-slug "${NE_FARM}" \
    --farm-name "Nebraska Farm" \
    --append
  log "  Nebraska grower expanded."
else
  log "  Nebraska grower already has ${TARGET_FIELD_COUNT} or more fields; skipping."
fi
log ""

# ──────────────────────────────────────────────
# Step 4: Refresh all farms (run pipeline)
# ──────────────────────────────────────────────
log "Refreshing all farms (running full pipeline with --force)..."
DATA_PIPELINE_DATA_ROOT="${RESOLVED_ROOT}" \
  "${PYTHON}" "${DASHBOARD}" refresh --scope all --force
log ""

log "=========================================="
log "Assignment 2 setup complete!"
log ""
log "Grower summary:"
log "  ${IL_SLUG}/${IL_FARM} -> $(count_fields "${IL_SLUG}" "${IL_FARM}") fields (Illinois)"
log "  ${IA_SLUG}/${IA_FARM} -> $(count_fields "${IA_SLUG}" "${IA_FARM}") fields (Iowa)"
log "  ${NE_SLUG}/${NE_FARM} -> $(count_fields "${NE_SLUG}" "${NE_FARM}") fields (Nebraska)"
log "=========================================="
