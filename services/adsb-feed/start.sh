#!/usr/bin/env sh
set -eu

LAT="${LAT:-41.2971}"
LON="${LON:-2.0785}"
DIST="${DIST:-80}"
INTERVAL="${INTERVAL:-2}"
OUT="${OUT:-/data/aircraft.json}"
ANOMALY_LOG="${ANOMALY_LOG:-/data/adsb_feed_anomalies.log}"

echo "[INFO] adsb-feed: escribiendo ${OUT} (lat=${LAT} lon=${LON} dist=${DIST} interval=${INTERVAL}s)"
echo "[INFO] adsb-feed: anomalias ANOMALY_ENABLED=${ANOMALY_ENABLED:-false} ANOMALY_RATE=${ANOMALY_RATE:-0.0} ANOMALY_MAX_PER_WRITE=${ANOMALY_MAX_PER_WRITE:-0} ANOMALY_COOLDOWN_CYCLES=${ANOMALY_COOLDOWN_CYCLES:-0} ANOMALY_RSSI_DISTANCE_RATE=${ANOMALY_RSSI_DISTANCE_RATE:-0.0} ANOMALY_RSSI_DISTANCE_MAX_PER_WRITE=${ANOMALY_RSSI_DISTANCE_MAX_PER_WRITE:-0} ANOMALY_TYPES=${ANOMALY_TYPES:-} ANOMALY_LOG=${ANOMALY_LOG}"

python /app/feed.py &

touch "$OUT"
cd /data
echo "[INFO] adsb-feed: sirviendo /data en 0.0.0.0:9000"
exec python -m http.server 9000 --bind 0.0.0.0
