#!/usr/bin/env python3
"""
Pequeño exportador que consulta periódicamente /api/v1/aircraft de Co-ATC
y vuelca cada aeronave como línea JSON en logs/adsb_events.log para Filebeat/Logstash.
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta estados de Co-ATC a un log JSON por línea.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/aircraft", help="Endpoint de Co-ATC.")
    parser.add_argument("--interval", type=float, default=1.0, help="Segundos entre lecturas.")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "logs" / "adsb_events.log"),
        help="Ruta del fichero de salida (se sobreescribe en cada arranque).",
    )
    parser.add_argument("--log-nivel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def seleccionar(valor: Optional[float], *alternativas: Optional[float]) -> Optional[float]:
    """Devuelve el primer valor no None."""
    if valor is not None:
        return valor
    for alt in alternativas:
        if alt is not None:
            return alt
    return None


def construir_evento(ac: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    adsb = ac.get("adsb") or {}
    controles = ac.get("simulation_controls") or {}
    alt = seleccionar(adsb.get("alt_geom"), adsb.get("alt_baro"))
    speed = seleccionar(adsb.get("gs"), adsb.get("tas"), adsb.get("ias"), controles.get("target_speed"))
    heading = seleccionar(adsb.get("true_heading"), adsb.get("track"), adsb.get("mag_heading"), controles.get("target_heading"))
    vert_rate = seleccionar(adsb.get("geom_rate"), adsb.get("baro_rate"), controles.get("target_vertical_rate"))

    anomaly_flags: List[str] = []
    if alt is not None and alt < 0:
        anomaly_flags.append("NEG_ALT")
    if speed is not None and speed > 1200:
        anomaly_flags.append("IMP_SPEED")

    return {
        "timestamp": timestamp,
        "hex": ac.get("hex"),
        "flight": ac.get("flight"),
        "is_simulated": ac.get("is_simulated"),
        "lat": adsb.get("lat"),
        "lon": adsb.get("lon"),
        "altitude": alt,
        "speed": speed,
        "heading": heading,
        "vertical_rate": vert_rate,
        "on_ground": ac.get("on_ground"),
        "anomaly_flags": anomaly_flags,
        "source": "co_atc_api",
    }


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_nivel), format="%(asctime)s [%(levelname)s] %(message)s")
    destino = Path(args.output)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as fh:
        logging.info("Exportando %s cada %.1f s a %s", args.url, args.interval, destino)
        while True:
            try:
                resp = requests.get(args.url, timeout=3)
                if not resp.ok:
                    logging.warning("Respuesta no OK: %s %s", resp.status_code, resp.text)
                    time.sleep(args.interval)
                    continue
                data = resp.json()
            except Exception as exc:  # noqa: BLE001
                logging.warning("Error consultando API: %s", exc)
                time.sleep(args.interval)
                continue

            ts_obj = data.get("timestamp")
            if isinstance(ts_obj, str):
                ts = ts_obj
            else:
                ts = datetime.now(timezone.utc).isoformat()

            for ac in data.get("aircraft", []):
                evento = construir_evento(ac, ts)
                fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
            fh.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Exportador detenido por el usuario.")
