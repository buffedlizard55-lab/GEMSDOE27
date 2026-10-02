#!/usr/bin/env bash
# Restore the owner-provided competition-data bridge without DrivenData credentials.
# Hash equality verifies this bridge's identity against data/manifest.json, NOT independent organiser provenance.
# Never touches drivendata.org.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" "${ROOT}/scripts/restore_data.py" "$@"

CACHE_DIR="${GEMS_DATA_DIR:-${ROOT}/data_cache}"
mkdir -p "${ROOT}/data"
for f in "${CACHE_DIR}"/*; do
  base="$(basename "${f}")"
  if [ "${base}" = "manifest.json" ] || [ "${base}" = "parts" ]; then
    continue
  fi
  ln -sfn "${f}" "${ROOT}/data/${base}"
done
echo "Competition data restored in ${CACHE_DIR} and linked into ${ROOT}/data/ (git-ignored)."
