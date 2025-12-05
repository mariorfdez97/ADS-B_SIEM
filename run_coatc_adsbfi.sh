#!/usr/bin/env bash
# Arranca Co-ATC usando el feed de adsb.fi, en primer plano y con logs en vivo.
# - Compila Co-ATC si no existe binario.
# - Inicia servidor HTTP local (puerto 9000) para servir aircraft.json.
# - Ejecuta fetch_adsbfi.py cada 1 s (LEBL, 80 NM) para poblar aircraft.json.
# - Arranca Co-ATC con configs/config.toml.
# - Ctrl+C detiene todos los procesos.

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CO_ATC_DIR="$BASE_DIR/co-atc-main"
CONFIG="$CO_ATC_DIR/configs/config.toml"
CO_ATC_BIN="$CO_ATC_DIR/bin/co-atc"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

wait_for_port() {
  local host="$1" port="$2" timeout="$3" start
  start=$(date +%s)
  while true; do
    if curl -sf "http://${host}:${port}/" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      echo "[ERROR] Timeout esperando ${host}:${port}" >&2
      return 1
    fi
    sleep 1
  done
}

# Compilar Co-ATC si no hay binario
if [[ ! -x "$CO_ATC_BIN" ]]; then
  echo "[INFO] (build) Binario no encontrado, compilando Co-ATC..."
  (cd "$CO_ATC_DIR" && GOCACHE="$CO_ATC_DIR/.gocache" go build -o "$CO_ATC_BIN" ./cmd/server) \
    >>"$LOG_DIR/co_atc_build.log" 2>&1
  echo "[INFO] (build) Completado -> $CO_ATC_BIN (log: logs/co_atc_build.log)"
fi

# Asegura aircraft.json inicial
touch "$CO_ATC_DIR/data/aircraft.json"

# Servidor estático para aircraft.json (foreground logs)
echo "[INFO] (http) Servidor estático 9000 para aircraft.json..."
(cd "$CO_ATC_DIR/data" && python3 -m http.server 9000 --bind 127.0.0.1 >>"$LOG_DIR/feed_http.log" 2>&1) &
FEED_PID=$!
echo "[INFO] (http) PID=$FEED_PID log=logs/feed_http_serverEstático.log"

wait_for_port "127.0.0.1" 9000 10

# Fetch adsb.fi -> aircraft.json (intervalo 1 s)
echo "[INFO] (fetch) adsb.fi LEBL lat=41.2971 lon=2.0785 dist=80 NM intervalo=1s..."
(cd "$BASE_DIR" && python3 fetch_adsbfi.py --lat 41.2971 --lon 2.0785 --dist 80 --interval 1 >>"$LOG_DIR/adsbfi_fetch.log" 2>&1) &
FETCH_PID=$!
echo "[INFO] (fetch) PID=$FETCH_PID log=logs/adsbfi_fetch.log"

# Arranque de Co-ATC
echo "[INFO] (coatc) Lanzando Co-ATC..."
(cd "$CO_ATC_DIR" && "$CO_ATC_BIN" -config "$CONFIG" >>"$LOG_DIR/co_atc.log" 2>&1) &
CO_ATC_PID=$!
echo "[INFO] (coatc) PID=$CO_ATC_PID log=logs/co_atc.log"

wait_for_port "127.0.0.1" 8000 30
echo "[INFO] (ready) Co-ATC en http://127.0.0.1:8000  | feed:9000 | fetch adsb.fi activo"
echo "[INFO] Ctrl+C para detener todo."

trap 'echo "[INFO] Deteniendo..."; kill $CO_ATC_PID $FETCH_PID $FEED_PID 2>/dev/null; exit 0' INT

# Cola logs en vivo (mínimos) para consola
tail -n 5 -f "$LOG_DIR/adsbfi_fetch.log" "$LOG_DIR/co_atc.log"
