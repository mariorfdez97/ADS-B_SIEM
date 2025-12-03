#!/usr/bin/env bash
# Detiene los procesos lanzados por lanzar_lab.sh usando los PIDs guardados.

set -euo pipefail

LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"
PIDS_FILE="$LOG_DIR/pids.env"

if [ -f "$PIDS_FILE" ]; then
  source "$PIDS_FILE"

  for pid_var in FEED_PID CO_ATC_PID SIM_PID TAIL_PID; do
    pid="${!pid_var:-}"
    if [ -n "$pid" ]; then
      if kill -0 "$pid" 2>/dev/null; then
        echo "[INFO] Matando $pid_var=$pid"
        kill "$pid" 2>/dev/null || echo "[WARN] No se pudo matar $pid_var (pid=$pid)"
      else
        echo "[WARN] $pid_var=$pid no está en ejecución."
      fi
    else
      echo "[WARN] Variable $pid_var vacía o no definida en $PIDS_FILE"
    fi
  done

  rm -f "$PIDS_FILE"
else
  echo "[WARN] No se encontró $PIDS_FILE. Se intentará matar procesos por patrón.";
  # Limpieza basada en patrones si no hay fichero de PIDs
  for pattern in "python3 -m http.server 9000" "bin/co-atc" "go run ./cmd/server" "simulador_bcn.py" "tail -n 20 -f" "tmp/go-build" "/exe/server"; do
    pids=$(pgrep -f "$pattern" || true)
    if [ -n "$pids" ]; then
      echo "[INFO] Matando procesos que coinciden con: $pattern -> $pids"
      kill $pids 2>/dev/null || true
    fi
  done
fi
