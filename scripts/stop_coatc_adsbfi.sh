#!/usr/bin/env bash
# Detiene los procesos iniciados por scripts/run_coatc_adsbfi.sh

set -euo pipefail

PIDS=()
echo "[INFO] Buscando procesos conocidos (fetch_adsbfi.py, http.server 9000, co-atc)..."

for pattern in "tools/adsb/fetch_adsbfi.py" "python3 -m http.server 9000" "bin/co-atc -config"; do
  found=$(pgrep -f "$pattern" || true)
  if [[ -n "$found" ]]; then
    PIDS+=($found)
  fi
done

if [[ ${#PIDS[@]} -eq 0 ]]; then
  echo "[WARN] No se encontraron procesos a detener."
  exit 0
fi

echo "[INFO] Matando PIDs: ${PIDS[*]}"
kill "${PIDS[@]}" 2>/dev/null || true
echo "[INFO] Finalizado."

