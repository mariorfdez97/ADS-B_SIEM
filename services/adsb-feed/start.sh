#!/usr/bin/env sh
set -eu

LAT="${LAT:-41.2971}"
LON="${LON:-2.0785}"
DIST="${DIST:-80}"
INTERVAL="${INTERVAL:-1}"
OUT="${OUT:-/data/aircraft.json}"
ANOMALY_LOG="${ANOMALY_LOG:-/data/adsb_feed_anomalies.log}"

echo "[INFO] adsb-feed: escribiendo ${OUT} (lat=${LAT} lon=${LON} dist=${DIST} interval=${INTERVAL}s)"
echo "[INFO] adsb-feed: anomalias ANOMALY_ENABLED=${ANOMALY_ENABLED:-false} ANOMALY_RATE=${ANOMALY_RATE:-0.0} ANOMALY_MAX_PER_WRITE=${ANOMALY_MAX_PER_WRITE:-0} ANOMALY_TYPES=${ANOMALY_TYPES:-} ANOMALY_LOG=${ANOMALY_LOG}"

python - <<'PY' &
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

lat = float(os.environ.get("LAT", "41.2971"))
lon = float(os.environ.get("LON", "2.0785"))
dist = float(os.environ.get("DIST", "80"))
interval = float(os.environ.get("INTERVAL", "1"))
out_path = Path(os.environ.get("OUT", "/data/aircraft.json"))
out_path.parent.mkdir(parents=True, exist_ok=True)
anomaly_log_path = Path(os.environ.get("ANOMALY_LOG", "/data/adsb_feed_anomalies.log"))
anomaly_log_path.parent.mkdir(parents=True, exist_ok=True)

anomaly_enabled = os.environ.get("ANOMALY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
try:
    anomaly_rate = float(os.environ.get("ANOMALY_RATE", "0.0"))
except ValueError:
    anomaly_rate = 0.0
anomaly_rate = max(0.0, min(1.0, anomaly_rate))
try:
    anomaly_max_per_write = int(os.environ.get("ANOMALY_MAX_PER_WRITE", "0"))
except ValueError:
    anomaly_max_per_write = 0
anomaly_max_per_write = max(0, anomaly_max_per_write)
anomaly_types = [t.strip() for t in os.environ.get("ANOMALY_TYPES", "").split(",") if t.strip()]


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


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _pick_indices(count: int, max_count: int, rate: float, seed: int) -> List[int]:
    if count <= 0 or max_count <= 0 or rate <= 0:
        return []

    # Ventana para que cambie con el tiempo sin disparar el volumen (cada 5s).
    window = int(time.time() // 5)
    state = (seed * 1000003) ^ (count * 9176) ^ window

    chosen: List[int] = []
    for i in range(count):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        r = state / 0x7FFFFFFF
        if r < rate:
            chosen.append(i)
            if len(chosen) >= max_count:
                break
    return chosen


def _pick_type(types: List[str], seed: int, hex_code: str) -> str:
    if not types:
        return "velocidad_excesiva"
    h = 0
    for ch in (hex_code or ""):
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return types[(seed + h) % len(types)]


def _inject_anomaly(ac: Dict[str, Any], anomaly_type: str, seed: int) -> Dict[str, Any]:
    # Importante: aquí tocamos campos estándar tar1090/dump1090 para que Co-ATC lo “vea”.
    before = {
        "hex": ac.get("hex"),
        "lat": ac.get("lat"),
        "lon": ac.get("lon"),
        "alt_baro": ac.get("alt_baro"),
        "alt_geom": ac.get("alt_geom"),
        "gs": ac.get("gs"),
        "ias": ac.get("ias"),
        "tas": ac.get("tas"),
        "mach": ac.get("mach"),
        "track": ac.get("track"),
        "true_heading": ac.get("true_heading"),
        "mag_heading": ac.get("mag_heading"),
        "baro_rate": ac.get("baro_rate"),
        "geom_rate": ac.get("geom_rate"),
        "squawk": ac.get("squawk"),
        "alert": ac.get("alert"),
        "spi": ac.get("spi"),
        "rssi": ac.get("rssi"),
        "nic": ac.get("nic"),
        "nac_p": ac.get("nac_p"),
    }
    if anomaly_type == "altitud_negativa":
        ac["alt_baro"] = -500
        ac["alt_geom"] = -450
        ac["baro_rate"] = -3000
    elif anomaly_type == "velocidad_excesiva":
        ac["gs"] = 2200.0
        ac["ias"] = 600.0
        ac["tas"] = 650.0
        ac["mach"] = 1.25
    elif anomaly_type == "salto_posicion":
        lat_v = ac.get("lat")
        lon_v = ac.get("lon")
        if isinstance(lat_v, (int, float)) and isinstance(lon_v, (int, float)):
            ac["lat"] = _clamp(float(lat_v) + 0.75, -89.9, 89.9)
            ac["lon"] = _clamp(float(lon_v) + 0.75, -179.9, 179.9)
        else:
            ac["lat"] = 0.0
            ac["lon"] = 0.0
    elif anomaly_type == "squawk_emergencia":
        choices = ["7700", "7600", "7500"]
        idx = (seed + int(time.time() // 10)) % len(choices)
        ac["squawk"] = choices[idx]
        ac["alert"] = 1
        ac["spi"] = 1
    elif anomaly_type == "posible_spoofing":
        ac["rssi"] = -5.0
        ac["nic"] = 3
        ac["nac_p"] = 4
    else:
        ac["gs"] = 1800.0
    after = {
        "lat": ac.get("lat"),
        "lon": ac.get("lon"),
        "alt_baro": ac.get("alt_baro"),
        "alt_geom": ac.get("alt_geom"),
        "gs": ac.get("gs"),
        "ias": ac.get("ias"),
        "tas": ac.get("tas"),
        "mach": ac.get("mach"),
        "track": ac.get("track"),
        "true_heading": ac.get("true_heading"),
        "mag_heading": ac.get("mag_heading"),
        "baro_rate": ac.get("baro_rate"),
        "geom_rate": ac.get("geom_rate"),
        "squawk": ac.get("squawk"),
        "alert": ac.get("alert"),
        "spi": ac.get("spi"),
        "rssi": ac.get("rssi"),
        "nic": ac.get("nic"),
        "nac_p": ac.get("nac_p"),
    }
    return {"type": anomaly_type, "before": before, "after": after}


while True:
    try:
        url = f"https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ac_list = data.get("ac", [])
        aircraft = [map_aircraft(ac) for ac in ac_list]

        if anomaly_enabled and anomaly_rate > 0 and anomaly_max_per_write > 0 and aircraft:
            seed = 1337
            indices = _pick_indices(len(aircraft), anomaly_max_per_write, anomaly_rate, seed)
            for idx in indices:
                item = aircraft[idx]
                if not isinstance(item, dict):
                    continue
                anomaly_type = _pick_type(anomaly_types, seed, str(item.get("hex") or ""))
                record = _inject_anomaly(item, anomaly_type, seed)
                record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                try:
                    with anomaly_log_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(record) + "\n")
                except Exception:
                    pass

        payload = {"now": int(time.time()), "messages": len(aircraft), "aircraft": aircraft}
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
