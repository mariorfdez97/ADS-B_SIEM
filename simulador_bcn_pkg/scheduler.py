import logging
import time
from typing import List

from simulador_bcn_pkg.context import ContextoSimulacion
from simulador_bcn_pkg.models import EventoProgramado


def ejecutar_eventos(
    contexto: ContextoSimulacion,
    eventos: List[EventoProgramado],
    factor_tiempo: float,
) -> None:
    """Reproduce la lista de eventos respetando su orden cronologico."""
    eventos_ordenados = sorted(eventos, key=lambda e: e.instante_cet)
    if not eventos_ordenados:
        logging.warning("No hay eventos programados.")
        return

    instante_inicio = eventos_ordenados[0].instante_cet
    tiempo_real_inicio = time.monotonic()

    for evento in eventos_ordenados:
        delta_simulado = (evento.instante_cet - instante_inicio).total_seconds()
        delta_real_objetivo = delta_simulado / factor_tiempo
        delta_real_actual = time.monotonic() - tiempo_real_inicio
        espera = delta_real_objetivo - delta_real_actual
        if espera > 0:
            time.sleep(espera)
        logging.info("Ejecutando evento %s (%s)", evento.instante_cet, evento.descripcion)
        evento.accion(contexto)
