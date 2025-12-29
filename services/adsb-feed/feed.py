#!/usr/bin/env python3
# -*- coding: ascii -*-

# Este script:
# - descarga datos ADS-B desde la API externa,
# - aplica anomalias (si estan activadas),
# - escribe el archivo aircraft.json que consume co-atc.

import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

# -----------------------------
# Configuracion desde entorno
# -----------------------------

# Coordenadas y radio de consulta.
lat = float(os.environ.get("LAT", "41.2971"))
lon = float(os.environ.get("LON", "2.0785"))
dist = float(os.environ.get("DIST", "80"))

# Intervalo en segundos entre peticiones.
interval = float(os.environ.get("INTERVAL", "2"))

# Ruta donde se escribe aircraft.json.
out_path = Path(os.environ.get("OUT", "/data/aircraft.json"))
out_path.parent.mkdir(parents=True, exist_ok=True)

# Log donde guardamos anomalias (JSONL).
anomaly_log_path = Path(os.environ.get("ANOMALY_LOG", "/data/adsb_feed_anomalies.log"))
anomaly_log_path.parent.mkdir(parents=True, exist_ok=True)

# Anomalias activas o no.
anomaly_enabled = os.environ.get("ANOMALY_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

if anomaly_enabled:
    try:
        anomaly_log_path.touch(exist_ok=True)
    except Exception:
        pass

# Probabilidad de inyectar anomalias (0.0 a 1.0).
try:
    anomaly_rate = float(os.environ.get("ANOMALY_RATE", "0.0"))
except ValueError:
    anomaly_rate = 0.0
anomaly_rate = max(0.0, min(1.0, anomaly_rate))

# Maximo de anomalias por ciclo.
try:
    anomaly_max_per_write = int(os.environ.get("ANOMALY_MAX_PER_WRITE", "0"))
except ValueError:
    anomaly_max_per_write = 0
anomaly_max_per_write = max(0, anomaly_max_per_write)

# Anomalia independiente: RSSI fuerte + distancia incoherente.
try:
    anomaly_rssi_distance_rate = float(os.environ.get("ANOMALY_RSSI_DISTANCE_RATE", "0.0"))
except ValueError:
    anomaly_rssi_distance_rate = 0.0
anomaly_rssi_distance_rate = max(0.0, min(1.0, anomaly_rssi_distance_rate))

try:
    anomaly_rssi_distance_max = int(os.environ.get("ANOMALY_RSSI_DISTANCE_MAX_PER_WRITE", "0"))
except ValueError:
    anomaly_rssi_distance_max = 0
anomaly_rssi_distance_max = max(0, anomaly_rssi_distance_max)

# Cooldown en ciclos para evitar repetir el mismo avion.
try:
    anomaly_cooldown_cycles = int(os.environ.get("ANOMALY_COOLDOWN_CYCLES", "0"))
except ValueError:
    anomaly_cooldown_cycles = 0
anomaly_cooldown_cycles = max(0, anomaly_cooldown_cycles)

# Tipos de anomalias permitidos.
anomaly_types = [
    t.strip()
    for t in os.environ.get("ANOMALY_TYPES", "").split(",")
    if t.strip()
]


# -----------------------------
# Helpers basicos
# -----------------------------

def safe_alt(value: Any) -> float:
    """Convierte altitud a numero seguro."""
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


def map_aircraft(ac: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un avion del feed externo al formato esperado por co-atc."""
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


def clamp(value: float, low: float, high: float) -> float:
    """Recorta un numero para que no salga de un rango."""
    return max(low, min(high, value))


# -----------------------------
# Seleccion de anomalias
# -----------------------------

def pick_indices(count: int, max_count: int, rate: float, seed: int) -> List[int]:
    """Elige indices de la lista a modificar segun la tasa."""
    if count <= 0 or max_count <= 0 or rate <= 0:
        return []

    # Cambia cada 5s para no generar siempre lo mismo.
    window = int(time.time() // 5)
    state = (seed * 1000003) ^ (count * 9176) ^ window

    chosen: List[int] = []
    for i in range(count):
        # Generador simple (no criptografico).
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        r = state / 0x7FFFFFFF
        if r < rate:
            chosen.append(i)
            if len(chosen) >= max_count:
                break
    return chosen


def pick_type(types: List[str], seed: int, hex_code: str) -> str:
    """Elige un tipo de anomalia de forma estable."""
    if not types:
        return "velocidad_excesiva"
    h = 0
    for ch in (hex_code or ""):
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return types[(seed + h) % len(types)]


def inject_anomaly(ac: Dict[str, Any], anomaly_type: str, seed: int) -> Dict[str, List[Any]]:
    """Modifica los campos del avion segun el tipo de anomalia."""

    changes: Dict[str, List[Any]] = {}
    hex_code = str(ac.get("hex") or "")
    now_ms = int(time.time() * 1000)
    rnd = random.Random((seed << 16) ^ now_ms ^ sum(ord(c) for c in hex_code))

    def set_field(field: str, value: Any) -> None:
        before = ac.get(field)
        ac[field] = value
        if before != value:
            changes[field] = [before, value]

    def set_rssi_distance_spoof() -> None:
        """Fuerza RSSI fuerte con distancia incoherente para la regla SIEM."""
        set_field("rssi", round(rnd.uniform(-5.0, -1.0), 1))
        distance_nm = rnd.uniform(220.0, 400.0)
        delta_deg = distance_nm / 60.0
        angle = rnd.uniform(0.0, math.tau)
        dlat = math.cos(angle) * delta_deg
        ref_lat = lat
        ref_lon = lon
        denom = max(0.1, math.cos(math.radians(ref_lat)))
        dlon = (math.sin(angle) * delta_deg) / denom
        set_field("lat", clamp(ref_lat + dlat, -89.9, 89.9))
        set_field("lon", clamp(ref_lon + dlon, -179.9, 179.9))

    if anomaly_type == "altitud_negativa":
        # Regla: altitud_pies < -100.
        alt_baro = -rnd.randint(101, 2000)
        alt_geom = alt_baro + rnd.randint(-200, 200)
        set_field("alt_baro", float(alt_baro))
        set_field("alt_geom", float(alt_geom))
    elif anomaly_type == "velocidad_excesiva":
        # Regla: velocidad_tierra_nudos > 1200.
        set_field("gs", float(rnd.randint(1201, 2000)))
    elif anomaly_type == "salto_posicion":
        lat_v = ac.get("lat")
        lon_v = ac.get("lon")
        if isinstance(lat_v, (int, float)) and isinstance(lon_v, (int, float)):
            lat_delta = rnd.choice([-1, 1]) * rnd.uniform(1.5, 8.0)
            lon_delta = rnd.choice([-1, 1]) * rnd.uniform(1.5, 8.0)
            set_field("lat", clamp(float(lat_v) + lat_delta, -89.9, 89.9))
            set_field("lon", clamp(float(lon_v) + lon_delta, -179.9, 179.9))
        else:
            set_field("lat", round(rnd.uniform(-5.0, 5.0), 4))
            set_field("lon", round(rnd.uniform(-5.0, 5.0), 4))
    elif anomaly_type == "squawk_emergencia":
        choices = ["7700", "7600", "7500"]
        set_field("squawk", rnd.choice(choices))
    elif anomaly_type == "posible_spoofing":
        # Regla: rssi > -10 y nic < 6.
        set_field("rssi", round(rnd.uniform(-5.0, -1.0), 1))
        set_field("nic", rnd.randint(0, 5))
        set_field("nac_p", rnd.randint(0, 6))
        set_field("nac_v", rnd.randint(0, 1))
        set_field("sil", rnd.randint(0, 1))
        set_field("sda", rnd.randint(0, 1))
    else:
        set_field("gs", float(rnd.randint(1201, 2000)))

    set_rssi_distance_spoof()

    return changes


def inject_rssi_distance_only(ac: Dict[str, Any], seed: int) -> Dict[str, List[Any]]:
    """Inyecta solo RSSI+distancia incoherente sin otra anomalia."""
    changes: Dict[str, List[Any]] = {}
    hex_code = str(ac.get("hex") or "")
    now_ms = int(time.time() * 1000)
    rnd = random.Random((seed << 16) ^ now_ms ^ sum(ord(c) for c in hex_code))

    def set_field(field: str, value: Any) -> None:
        before = ac.get(field)
        ac[field] = value
        if before != value:
            changes[field] = [before, value]

    set_field("rssi", round(rnd.uniform(-5.0, -1.0), 1))
    distance_nm = rnd.uniform(220.0, 400.0)
    delta_deg = distance_nm / 60.0
    angle = rnd.uniform(0.0, math.tau)
    dlat = math.cos(angle) * delta_deg
    ref_lat = lat
    ref_lon = lon
    denom = max(0.1, math.cos(math.radians(ref_lat)))
    dlon = (math.sin(angle) * delta_deg) / denom
    set_field("lat", clamp(ref_lat + dlat, -89.9, 89.9))
    set_field("lon", clamp(ref_lon + dlon, -179.9, 179.9))

    return changes


# -----------------------------
# Bucle principal
# -----------------------------

cycle_counter = 0
last_anomaly_cycle: Dict[str, int] = {}

while True:
    try:
        cycle_counter += 1
        # URL de la API externa.
        url = f"https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}"

        # Descarga.
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Lista de aeronaves.
        ac_list = data.get("ac", [])
        aircraft = [map_aircraft(ac) for ac in ac_list]

        # Inyeccion de anomalias.
        modified_hexes = set()
        if anomaly_enabled and anomaly_rate > 0 and anomaly_max_per_write > 0 and aircraft:
            seed = 1337
            indices = pick_indices(len(aircraft), anomaly_max_per_write, anomaly_rate, seed)
            for idx in indices:
                item = aircraft[idx]
                if not isinstance(item, dict):
                    continue
                hex_code = str(item.get("hex") or "")
                if anomaly_cooldown_cycles > 0 and hex_code:
                    last_cycle = last_anomaly_cycle.get(hex_code)
                    if last_cycle is not None and (cycle_counter - last_cycle) <= anomaly_cooldown_cycles:
                        continue
                anomaly_type = pick_type(anomaly_types, seed, str(item.get("hex") or ""))
                changes = inject_anomaly(item, anomaly_type, seed)
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                if changes:
                    if hex_code:
                        last_anomaly_cycle[hex_code] = cycle_counter
                        modified_hexes.add(hex_code)
                    try:
                        with anomaly_log_path.open("a", encoding="utf-8") as fh:
                            detailed_changes = []
                            for field, values in changes.items():
                                detailed_changes.append(
                                    {
                                        "field": field,
                                        "correct_value": values[0],
                                        "modified_value": values[1],
                                    }
                                )
                            record = {
                                "ts": ts,
                                "id_icao": item.get("hex"),
                                "anomaly_type": anomaly_type,
                                "changes": detailed_changes,
                            }
                            fh.write(json.dumps(record) + "\n")
                    except Exception:
                        # Si falla el log, seguimos igual.
                        pass

        if (
            anomaly_enabled
            and anomaly_rssi_distance_rate > 0
            and anomaly_rssi_distance_max > 0
            and aircraft
        ):
            seed = 4242
            indices = pick_indices(
                len(aircraft),
                anomaly_rssi_distance_max,
                anomaly_rssi_distance_rate,
                seed,
            )
            for idx in indices:
                item = aircraft[idx]
                if not isinstance(item, dict):
                    continue
                hex_code = str(item.get("hex") or "")
                if hex_code and hex_code in modified_hexes:
                    continue
                if anomaly_cooldown_cycles > 0 and hex_code:
                    last_cycle = last_anomaly_cycle.get(hex_code)
                    if last_cycle is not None and (cycle_counter - last_cycle) <= anomaly_cooldown_cycles:
                        continue
                changes = inject_rssi_distance_only(item, seed)
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                if changes:
                    if hex_code:
                        last_anomaly_cycle[hex_code] = cycle_counter
                    try:
                        with anomaly_log_path.open("a", encoding="utf-8") as fh:
                            detailed_changes = []
                            for field, values in changes.items():
                                detailed_changes.append(
                                    {
                                        "field": field,
                                        "correct_value": values[0],
                                        "modified_value": values[1],
                                    }
                                )
                            record = {
                                "ts": ts,
                                "id_icao": item.get("hex"),
                                "anomaly_type": "rssi_distancia_incoherente",
                                "changes": detailed_changes,
                            }
                            fh.write(json.dumps(record) + "\n")
                    except Exception:
                        # Si falla el log, seguimos igual.
                        pass

        # Escribimos el archivo que leera co-atc.
        payload = {
            "now": int(time.time()),
            "messages": len(aircraft),
            "aircraft": aircraft,
        }
        out_path.write_text(json.dumps(payload), encoding="utf-8")

        print(f"[INFO] adsb-feed: {len(ac_list)} aeronaves", flush=True)
    except Exception as exc:
        print(f"[WARN] adsb-feed: {exc}", flush=True)

    time.sleep(interval)
