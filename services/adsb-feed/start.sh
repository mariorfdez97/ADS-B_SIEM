#!/usr/bin/env sh
set -eu

LAT="${LAT:-41.2971}"
LON="${LON:-2.0785}"
DIST="${DIST:-80}"
INTERVAL="${INTERVAL:-1}"
OUT="${OUT:-/data/aircraft.json}"

echo "[INFO] adsb-feed: escribiendo ${OUT} (lat=${LAT} lon=${LON} dist=${DIST} interval=${INTERVAL}s)"

python - <<'PY' &
import json
import os
import time
from pathlib import Path

import requests

lat = float(os.environ.get("LAT", "41.2971"))
lon = float(os.environ.get("LON", "2.0785"))
dist = float(os.environ.get("DIST", "80"))
interval = float(os.environ.get("INTERVAL", "1"))
out_path = Path(os.environ.get("OUT", "/data/aircraft.json"))
out_path.parent.mkdir(parents=True, exist_ok=True)


def safe_alt(value):
    if value is None:
        return 0.0
    if isinstance(value, str):
        if value.lower() == "ground":
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
    return float(value)


def map_aircraft(ac):
    alt_baro = safe_alt(ac.get("alt_baro"))
    alt_geom = safe_alt(ac.get("alt_geom", ac.get("alt_baro")))
    gs = ac.get("gs") or ac.get("tas") or ac.get("ias")
    heading = ac.get("true_heading") or ac.get("track") or ac.get("mag_heading")
    baro_rate = ac.get("baro_rate") or ac.get("geom_rate")
    return {
        "hex": (ac.get("hex") or "").upper(),
        "type": ac.get("type"),
        "flight": (ac.get("flight") or "").strip(),
        "r": ac.get("r"),
        "t": ac.get("t"),
        "desc": ac.get("desc"),
        "alt_baro": alt_baro,
        "alt_geom": alt_geom,
        "gs": gs,
        "tas": ac.get("tas"),
        "ias": ac.get("ias"),
        "mach": ac.get("mach"),
        "track": ac.get("track"),
        "true_heading": heading,
        "mag_heading": ac.get("mag_heading"),
        "baro_rate": baro_rate,
        "geom_rate": ac.get("geom_rate"),
        "squawk": ac.get("squawk"),
        "emergency": ac.get("emergency"),
        "category": ac.get("category"),
        "lat": ac.get("lat"),
        "lon": ac.get("lon"),
        "nic": ac.get("nic"),
        "rc": ac.get("rc"),
        "seen_pos": ac.get("seen_pos"),
        "version": ac.get("version", 2),
        "nic_baro": ac.get("nic_baro"),
        "nac_p": ac.get("nac_p"),
        "nac_v": ac.get("nac_v"),
        "sil": ac.get("sil"),
        "sil_type": ac.get("sil_type"),
        "gva": ac.get("gva"),
        "sda": ac.get("sda"),
        "alert": ac.get("alert"),
        "spi": ac.get("spi"),
        "mlat": ac.get("mlat", []),
        "tisb": ac.get("tisb", []),
        "messages": ac.get("messages"),
        "seen": ac.get("seen"),
        "rssi": ac.get("rssi"),
    }


while True:
    try:
        url = f"https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ac_list = data.get("ac", [])
        payload = {"now": int(time.time()), "messages": len(ac_list), "aircraft": [map_aircraft(ac) for ac in ac_list]}
        out_path.write_text(json.dumps(payload), encoding="utf-8")
        print(f"[INFO] adsb-feed: {len(ac_list)} aeronaves", flush=True)
    except Exception as e:
        print(f"[WARN] adsb-feed: {e}", flush=True)
    time.sleep(interval)
PY

touch "$OUT"
cd /data
echo "[INFO] adsb-feed: sirviendo /data en 0.0.0.0:9000"
exec python -m http.server 9000 --bind 0.0.0.0

