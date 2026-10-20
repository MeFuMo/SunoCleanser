#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v conda >/dev/null 2>&1; then
  for candidate in \
    "${HOME}/miniconda3/etc/profile.d/conda.sh" \
    "${HOME}/anaconda3/etc/profile.d/conda.sh" \
    "/opt/conda/etc/profile.d/conda.sh"
  do
    if [[ -f "${candidate}" ]]; then
      # shellcheck source=/dev/null
      source "${candidate}"
      break
    fi
  done
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "Error: conda no encontrado. Instala Miniconda y: conda env create -f environment.yml" >&2
  exit 1
fi

exec conda run -n sunocleanser --no-capture-output python -m src.gui "$@"
