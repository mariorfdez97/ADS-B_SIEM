#!/usr/bin/env bash
# Script de arranque rápido: servidor HTTP para aircraft.json, backend Co-ATC y simulador BCN.
# Muestra logs en vivo y guarda PIDs para poder detenerlos con detener_lab.sh

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CO_ATC_DIR="$BASE_DIR/co-atc-main"
LOG_DIR="$BASE_DIR/logs"
PIDS_FILE="$LOG_DIR/pids.env"
CO_ATC_BIN="$CO_ATC_DIR/bin/co-atc"
CO_ATC_CONFIG="$CO_ATC_DIR/configs/config.toml"
CO_ATC_BUILD_LOG="$LOG_DIR/co_atc_build.log"
EXPORTER_SCRIPT="$BASE_DIR/co_atc_exporter.py"

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

kill_residuals() {
  # Mata procesos residuales si quedaron huérfanos en ejecuciones previas sin pids.env
  for pattern in "python3 -m http.server 9000" "bin/co-atc" "go run ./cmd/server" "simulador_bcn.py" "tmp/go-build" "/exe/server" "tail -n 20 -f"; do
    pids=$(pgrep -f "$pattern" || true)
    if [ -n "$pids" ]; then
      echo "[INFO] Matando procesos residuales: $pattern -> $pids"
      kill $pids 2>/dev/null || true
    fi
  done
}

# ----------------------- Menu interactivo -----------------------------------
echo "================ MENÚ DE ARRANQUE ================"
read -r -p "Factor de tiempo (default 1.0): " INPUT_FACTOR
SIM_FACTOR_TIEMPO="${INPUT_FACTOR:-${SIM_FACTOR_TIEMPO:-1.0}}"

read -r -p "Incluir anomalías? [s/N]: " INPUT_ANOM
INCLUIR_ANOMALIAS="no"
if [[ "${INPUT_ANOM,,}" == "s" || "${INPUT_ANOM,,}" == "y" ]]; then
  INCLUIR_ANOMALIAS="si"
fi

read -r -p "Resetear bases co-atc (RESET_COATC_DB=1)? [s/N]: " INPUT_RESET
RESET_COATC_DB="${INPUT_RESET:-}"
if [[ "${INPUT_RESET,,}" == "s" || "${INPUT_RESET,,}" == "y" ]]; then
  RESET_COATC_DB="1"
else
  RESET_COATC_DB="0"
fi

read -r -p "Forzar build de co-atc (go build)? [s/N]: " INPUT_BUILD
FORCE_BUILD="${INPUT_BUILD:-}"
if [[ "${INPUT_BUILD,,}" == "s" || "${INPUT_BUILD,,}" == "y" ]]; then
  FORCE_BUILD="1"
else
  FORCE_BUILD="0"
fi
echo "=================================================="
echo "[INFO] Configuración seleccionada:"
echo "  - factor-tiempo: ${SIM_FACTOR_TIEMPO}"
echo "  - anomalías: ${INCLUIR_ANOMALIAS}"
echo "  - reset DB: ${RESET_COATC_DB}"
echo "  - force build: ${FORCE_BUILD}"
echo "--------------------------------------------------"

mkdir -p "$LOG_DIR"

# Detener instancias anteriores si existen
if [[ -f "$PIDS_FILE" ]]; then
  echo "[INFO] Encontrado $PIDS_FILE, intentando detener procesos previos..."
  bash "$BASE_DIR/detener_lab.sh" || true
fi

rm -f "$PIDS_FILE"
kill_residuals

# Reset opcional de estado de Co-ATC (reinicia planes y bases diarias)
# Si quieres forzar limpieza, exporta RESET_COATC_DB=1 antes de lanzar el script.
if [[ "${RESET_COATC_DB:-0}" == "1" ]]; then
  echo "[INFO] Limpiando bases SQLite de Co-ATC (co-atc-*.db) para reiniciar vuelos..."
  rm -f "$CO_ATC_DIR"/data/co-atc-*.db "$CO_ATC_DIR"/data/co-atc-*.db-shm "$CO_ATC_DIR"/data/co-atc-*.db-wal || true
else
  echo "[INFO] Manteniendo bases SQLite existentes (no se borran co-atc-*.db)"
fi

# Compilación opcional de Co-ATC (se fuerza con FORCE_BUILD=1)
if [[ ! -x "$CO_ATC_BIN" || "${FORCE_BUILD:-0}" == "1" ]]; then
  echo "[INFO] Compilando Co-ATC (go build)..."
  mkdir -p "$(dirname "$CO_ATC_BIN")"
  (
    cd "$CO_ATC_DIR"
    GOCACHE="$CO_ATC_DIR/.gocache" go build -o "$CO_ATC_BIN" ./cmd/server
  ) >>"$CO_ATC_BUILD_LOG" 2>&1 || { echo "[ERROR] Falló go build, revisa $CO_ATC_BUILD_LOG"; exit 1; }
  echo "[INFO] Build completado. Binario en $CO_ATC_BIN (log en $CO_ATC_BUILD_LOG)"
else
  echo "[INFO] Usando binario existente: $CO_ATC_BIN"
fi

# Arranque del feed estático
echo "[INFO] Iniciando servidor estático para aircraft.json en 9000..."
(
  cd "$CO_ATC_DIR/data"
  exec python3 -m http.server 9000 --bind 127.0.0.1 >>"$LOG_DIR/feed_http.log" 2>&1
) &
echo "FEED_PID=$!" >>"$PIDS_FILE"

# Esperar a que el feed HTTP responda para evitar errores en Co-ATC
echo "[INFO] Esperando a que el feed HTTP responda en 9000..."
wait_for_port "127.0.0.1" 9000 10

# Arranque de Co-ATC
echo "[INFO] Iniciando Co-ATC (binario, config=$CO_ATC_CONFIG)..."
(
  cd "$CO_ATC_DIR"
  exec "$CO_ATC_BIN" -config "$CO_ATC_CONFIG" >>"$LOG_DIR/co_atc.log" 2>&1
) &
echo "CO_ATC_PID=$!" >>"$PIDS_FILE"

echo "[INFO] Esperando a que Co-ATC escuche en 8000..."
wait_for_port "127.0.0.1" 8000 30

SIM_FACTOR_TIEMPO="${SIM_FACTOR_TIEMPO:-1.0}"
EXTRA_ARGS=()
if [[ "$INCLUIR_ANOMALIAS" == "si" ]]; then
  EXTRA_ARGS+=(--incluir-anomalias)
fi

# Arranque del simulador
echo "[INFO] Iniciando simulador BCN (factor-tiempo=${SIM_FACTOR_TIEMPO}; añade --incluir-anomalias si procede)..."
(
  cd "$BASE_DIR"
  exec python3 simulador_bcn.py --factor-tiempo "$SIM_FACTOR_TIEMPO" "${EXTRA_ARGS[@]}" >>"$LOG_DIR/simulador.log" 2>&1
) &
echo "SIM_PID=$!" >>"$PIDS_FILE"

# Exportador de telemetría hacia logs/adsb_events.log para Filebeat/Logstash
if [[ -f "$EXPORTER_SCRIPT" ]]; then
  echo "[INFO] Iniciando exportador Co-ATC -> logs/adsb_events.log ..."
  (
    cd "$BASE_DIR"
    exec python3 "$EXPORTER_SCRIPT" --url http://127.0.0.1:8000/api/v1/aircraft --output "$LOG_DIR/adsb_events.log" --interval 1.0 >>"$LOG_DIR/exporter.log" 2>&1
  ) &
  echo "EXPORTER_PID=$!" >>"$PIDS_FILE"
else
  echo "[WARN] No se encontró $EXPORTER_SCRIPT; no se exportarán eventos ADS-B a logs/adsb_events.log"
fi

# Lanzar un tail unificado en segundo plano
echo "[INFO] Mostrando logs en vivo (Ctrl+C para salir y detener procesos)..."
tail -n 20 -f "$LOG_DIR/feed_http.log" "$LOG_DIR/co_atc.log" "$LOG_DIR/simulador.log" &
echo "TAIL_PID=$!" >>"$PIDS_FILE"

# Capturar Ctrl+C para cerrar todo limpiamente
trap 'echo "[INFO] Ctrl+C detectado. Deteniendo procesos..."; bash "$BASE_DIR/detener_lab.sh"; exit 0' INT TERM

wait
