import argparse
import logging
import sys
from datetime import datetime
from typing import List
from pathlib import Path

from simulador_bcn_pkg.builders import construir_anomalias, construir_vuelos
from simulador_bcn_pkg.context import ContextoSimulacion
from simulador_bcn_pkg.models import EventoProgramado
from simulador_bcn_pkg.scheduler import ejecutar_eventos


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orquestador de trafico simulado para LEBL (Co-ATC)."
    )
    parser.add_argument(
        "--url-base",
        default="http://127.0.0.1:8000/api/v1",
        help="URL base de la API de Co-ATC (por defecto: %(default)s).",
    )
    parser.add_argument(
        "--fecha",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Fecha CET del escenario (formato YYYY-MM-DD).",
    )
    parser.add_argument(
        "--factor-tiempo",
        type=float,
        default=1.0,
        help="Factor de aceleracion temporal (1.0 = tiempo real).",
    )
    parser.add_argument(
        "--modo-prueba",
        action="store_true",
        help="Muestra las llamadas sin ejecutar la API (dry-run).",
    )
    parser.add_argument(
        "--incluir-anomalias",
        action="store_true",
        help="Activa la inyeccion de trafico anomalo (por defecto desactivado).",
    )
    parser.add_argument(
        "--log-nivel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de log para la ejecucion.",
    )
    return parser.parse_args()


def configurar_logging(nivel: str) -> None:
    """Configura logging en consola y en archivo limpio por ejecución."""
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)  # Siempre recolectamos todo en el archivo

    formato = "%(asctime)s [%(levelname)s] %(message)s"

    # Consola: nivel configurable
    consola = logging.StreamHandler()
    consola.setLevel(getattr(logging, nivel))
    consola.setFormatter(logging.Formatter(formato))
    logger.addHandler(consola)

    # Archivo estructurado y reiniciado en cada ejecución
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    archivo = logging.FileHandler(logs_dir / "inyector.log", mode="w", encoding="utf-8")
    archivo.setLevel(logging.DEBUG)
    archivo.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(archivo)


def main() -> None:
    argumentos = parsear_argumentos()
    configurar_logging(argumentos.log_nivel)

    try:
        fecha_base = datetime.strptime(argumentos.fecha, "%Y-%m-%d")
    except ValueError as error:
        raise SystemExit(f"Fecha invalida: {argumentos.fecha}") from error

    vuelos = construir_vuelos(fecha_base, incluir_anomalias=argumentos.incluir_anomalias)
    contexto = ContextoSimulacion(
        url_base=argumentos.url_base,
        modo_simulacion=argumentos.modo_prueba,
        factor_tiempo=argumentos.factor_tiempo,
    )
    contexto.vuelos_registrados = vuelos

    eventos: List[EventoProgramado] = []
    for vuelo in vuelos:
        eventos.extend(vuelo.generar_eventos())

    if argumentos.incluir_anomalias:
        eventos.extend(construir_anomalias(fecha_base))

    logging.info("Total de eventos programados: %s", len(eventos))
    ejecutar_eventos(contexto, eventos, factor_tiempo=argumentos.factor_tiempo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Ejecucion interrumpida por el usuario.")
        sys.exit(1)
