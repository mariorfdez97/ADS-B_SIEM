#!/usr/bin/env python3
"""
Fetcher simple para alimentar a Co-ATC con datos de adsb.fi.

Consulta el endpoint v3 de adsb.fi (lat/lon/dist), adapta los campos al
formato tar1090/dump1090 (aircraft.json) y escribe el fichero en
co-atc-main/data/aircraft.json. Sirve de sustituto del inyector local.

Uso:
  python3 tools/adsb/fetch_adsbfi.py --lat 41.2971 --lon 2.0785 --dist 80

Requisitos:
  pip install requests
  Servir el fichero con: (cd co-atc-main/data && python3 -m http.server 9000)
  Config de Co-ATC: adsb.local_source_url = http://127.0.0.1:9000/aircraft.json
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Proxy adsb.fi -> aircraft.json para Co-ATC")
    parser.add_argument("--lat", type=float, required=True, help="Latitud centro (decimal)")
    parser.add_argument("--lon", type=float, required=True, help="Longitud centro (decimal)")
    parser.add_argument(
        "--dist",
        type=float,
        default=80.0,
        help="Radio en NM (adsb.fi permite hasta 250 NM, por defecto 80)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Segundos entre consultas (respeta rate limit de 1 req/s)",
    )
    parser.add_argument(
        "--output",
        default=str(Path("co-atc-main") / "data" / "aircraft.json"),
        help="Ruta de salida del aircraft.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout de cada request en segundos",
    )
    return parser.parse_args()


def safe_alt(value: Any) -> float:
    """Convierte altitudes; 'ground' -> 0, None -> 0."""
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
    """Mapea un objeto de adsb.fi (v3) al formato tar1090/dump1090."""
    alt_baro = safe_alt(ac.get("alt_baro"))
    alt_geom = safe_alt(ac.get("alt_geom", ac.get("alt_baro")))
    gs = ac.get("gs") or ac.get("tas") or ac.get("ias")
    heading = ac.get("true_heading") or ac.get("track") or ac.get("mag_heading")
    baro_rate = ac.get("baro_rate") or ac.get("geom_rate")

    return {
        "hex": (ac.get("hex") or "").upper(),
        "type": ac.get("type"),
        "flight": (ac.get("flight") or "").strip(),
        "r": ac.get("r"),  # registration
        "t": ac.get("t"),  # aircraft type
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


def build_payload(ac_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    now = int(time.time())
    aircraft = [map_aircraft(ac) for ac in ac_list]
    return {
        "now": now,
        "messages": len(aircraft),
        "aircraft": aircraft,
    }


def main() -> None:
    args = parse_args()
    url = f"https://opendata.adsb.fi/api/v3/lat/{args.lat}/lon/{args.lon}/dist/{args.dist}"
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Consultando {url} cada {args.interval:.1f}s. Escribiendo {out_path}")
    while True:
        try:
            resp = requests.get(url, timeout=args.timeout)
            if not resp.ok:
                print(f"[WARN] {resp.status_code} {resp.text}")
                time.sleep(args.interval)
                continue
            data = resp.json()
            ac_list = data.get("ac", [])
            payload = build_payload(ac_list)
            out_path.write_text(json.dumps(payload), encoding="utf-8")
            print(f"[INFO] Escrito {len(ac_list)} aeronaves en {out_path}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {exc}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

