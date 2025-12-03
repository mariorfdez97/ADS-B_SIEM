import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from simulador_bcn_pkg.context import ContextoSimulacion
from simulador_bcn_pkg.models import (
    EventoProgramado,
    PuntoNavegacion,
    TramoVuelo,
    VueloSimulado,
)
from simulador_bcn_pkg.utils import calcular_rumbo, hora_cet


def construir_puntos() -> Dict[str, PuntoNavegacion]:
    """Registra los puntos relevantes del escenario."""
    return {
        "LEBL": PuntoNavegacion("LEBL_TWR", 41.2971, 2.0785),
        "RWY07R": PuntoNavegacion("RWY07R", 41.2863, 2.0886),
        "RWY07L": PuntoNavegacion("RWY07L", 41.2916, 2.0743),
        "IF_07L": PuntoNavegacion("IF_07L", 41.3050, 2.0500),
        "IF_07R": PuntoNavegacion("IF_07R", 41.3050, 2.0650),
        "BASE_07L": PuntoNavegacion("BASE_07L", 41.3350, 2.0300),
        "BASE_07R": PuntoNavegacion("BASE_07R", 41.3350, 2.0450),
        "DOWNWIND_N": PuntoNavegacion("DOWNWIND_N", 41.4000, 2.0200),
        "NELSO": PuntoNavegacion("NELSO", 41.2300, 2.2000),
        "TARRA": PuntoNavegacion("TARRA", 41.0900, 1.5500),
        "TGA": PuntoNavegacion("TGA", 41.1433, 1.1733),
        "LORET": PuntoNavegacion("LORET", 41.4000, 0.9000),
        "MASNU": PuntoNavegacion("MASNU", 41.4800, 2.3000),
        "BAMES": PuntoNavegacion("BAMES", 41.7350, 2.3900),
        "KENAS": PuntoNavegacion("KENAS", 41.8864, 2.5800),
        "GIRON": PuntoNavegacion("GIRON", 41.9000, 2.7600),
        "SITGE": PuntoNavegacion("SITGE", 41.2300, 1.8000),
        "SARGO": PuntoNavegacion("SARGO", 41.2500, 2.1000),
        "UBAGA": PuntoNavegacion("UBAGA", 41.3600, 2.1400),
        "SLL": PuntoNavegacion("SLL", 41.5169, 2.1050),
        "DOBRO": PuntoNavegacion("DOBRO", 41.3200, 2.0000),
        "HOLD_E": PuntoNavegacion("HOLD_SLL_E1", 41.5269, 2.1350),
        "HOLD_W": PuntoNavegacion("HOLD_SLL_W1", 41.5069, 2.0750),
        "GHOST": PuntoNavegacion("GHOST", 41.3500, 2.5000),
        "ANM_EAST": PuntoNavegacion("ANM_EAST", 41.2300, 2.4200),
        "ANM_WEST": PuntoNavegacion("ANM_WEST", 41.2400, 1.6200),
        "ANM_SOUTH": PuntoNavegacion("ANM_SOUTH", 41.1200, 2.1600),
    }


PUNTOS_ESCENARIO = construir_puntos()


def construir_vuelos(fecha_base: datetime, incluir_anomalias: bool = False) -> List[VueloSimulado]:
    """Define un conjunto de vuelos sencillos y abundantes para poblar el escenario."""
    puntos = PUNTOS_ESCENARIO
    vuelos: List[VueloSimulado] = []

    # Ventana de inicio 06:00 CET
    base_creacion = hora_cet(fecha_base, 6, 0, 0)

    # ----------------------- Salidas (8) -------------------------------------
    salidas = [
        ("DPT101", "A320", "RWY07R", 0, 30, [("NELSO", 200, 3_000), ("LORET", 300, 10_000)]),
        ("DPT102", "A320", "RWY07L", 10, 50, [("MASNU", 210, 4_000), ("KENAS", 280, 11_000)]),
        ("DPT103", "B738", "RWY07R", 20, 70, [("TARRA", 220, 5_000), ("TGA", 290, 12_000)]),
        ("DPT104", "ATR72", "RWY07L", 30, 80, [("SITGE", 170, 3_000), ("SARGO", 190, 6_000)]),
        ("DPT105", "A321", "RWY07R", 40, 90, [("SARGO", 210, 4_500), ("UBAGA", 260, 9_500)]),
        ("DPT106", "B738", "RWY07L", 50, 100, [("NELSO", 200, 3_500), ("LORET", 280, 10_500)]),
        ("DPT107", "CRJ9", "RWY07R", 60, 110, [("MASNU", 200, 4_000), ("BAMES", 250, 9_000)]),
        ("DPT108", "A320", "RWY07L", 70, 120, [("SARGO", 200, 4_000), ("KENAS", 270, 10_000)]),
    ]

    for ident, tipo, punto, offset_crea, offset_inicio, tramos in salidas:
        vuelos.append(
            VueloSimulado(
                identificador=ident,
                tipo_aeronave=tipo,
                punto_inicio=puntos[punto],
                hora_creacion_cet=base_creacion + timedelta(seconds=offset_crea),
                hora_inicio_tramos_cet=base_creacion + timedelta(seconds=offset_inicio),
                altitud_inicial_ft=0.0,
                velocidad_inicial_kt=0.0,
                rumbo_inicial=85.0,
                tramos=[
                    TramoVuelo(destino=puntos[dest], velocidad_objetivo=vel, altitud_destino_ft=alt)
                    for dest, vel, alt in tramos
                ],
            )
        )

    # ----------------------- Llegadas (8) ------------------------------------
    llegadas_inicio = base_creacion + timedelta(minutes=6)
    llegadas = [
        ("ARR201", "A321", "LORET", 0, 20, [("SARGO", 200, 5_000), ("RWY07L", 150, 150)]),
        ("ARR202", "A320", "MASNU", 10, 30, [("SLL", 190, 4_000), ("RWY07R", 145, 120)]),
        ("ARR203", "B738", "TGA", 20, 40, [("SITGE", 200, 5_000), ("RWY07R", 150, 150)]),
        ("ARR204", "A320", "KENAS", 30, 50, [("SLL", 190, 4_000), ("RWY07L", 145, 120)]),
        ("ARR205", "A320", "GIRON", 40, 60, [("MASNU", 200, 5_000), ("RWY07R", 150, 120)]),
        ("ARR206", "A320", "BAMES", 50, 70, [("MASNU", 200, 5_000), ("RWY07L", 150, 140)]),
        ("ARR207", "B738", "UBAGA", 60, 80, [("SLL", 190, 4_000), ("RWY07L", 145, 120)]),
        ("ARR208", "CRJ9", "SARGO", 70, 90, [("IF_07R", 170, 2_800), ("RWY07R", 140, 120)]),
    ]

    for ident, tipo, punto, offset_crea, offset_inicio, tramos in llegadas:
        vuelos.append(
            VueloSimulado(
                identificador=ident,
                tipo_aeronave=tipo,
                punto_inicio=puntos[punto],
                hora_creacion_cet=llegadas_inicio + timedelta(seconds=offset_crea),
                hora_inicio_tramos_cet=llegadas_inicio + timedelta(seconds=offset_inicio),
                altitud_inicial_ft=9_000,
                velocidad_inicial_kt=220,
                rumbo_inicial=220.0,
                tramos=[
                    TramoVuelo(destino=puntos[dest], velocidad_objetivo=vel, altitud_destino_ft=alt)
                    for dest, vel, alt in tramos
                ],
                eliminar_al_final=True,
            )
        )

    if incluir_anomalias:
        hora_creacion_ghost = hora_cet(fecha_base, 6, 2, 0)
        vuelos.append(
            VueloSimulado(
                identificador="GHOST01",
                tipo_aeronave="SIM",
                punto_inicio=puntos["GHOST"],
                hora_creacion_cet=hora_creacion_ghost,
                hora_inicio_tramos_cet=hora_creacion_ghost + timedelta(seconds=15),
                altitud_inicial_ft=25_000,
                velocidad_inicial_kt=500,
                rumbo_inicial=90.0,
                tramos=[
                    TramoVuelo(
                        destino=puntos["ANM_WEST"],
                        velocidad_objetivo=520,
                        altitud_destino_ft=20_000,
                        descripcion="GHOST sobrevuelo rapido",
                        duracion_manual_segundos=25.0,
                        vertical_rate_manual=-3000.0,
                    )
                ],
            )
        )

    return vuelos


def construir_anomalias(fecha_base: datetime) -> List[EventoProgramado]:
    """Genera eventos adicionales para falsos datos y pruebas SIEM."""
    zona_cet = timezone(timedelta(hours=1))
    eventos: List[EventoProgramado] = []

    instante_neg_alt = datetime(
        year=fecha_base.year,
        month=fecha_base.month,
        day=fecha_base.day,
        hour=6,
        minute=18,
        second=0,
        tzinfo=zona_cet,
    )

    def accion_altitud_negativa(contexto: ContextoSimulacion) -> None:
        vuelo = contexto.buscar_vuelo_por_id("DPT101")
        if not vuelo:
            logging.warning("No se encontro DPT101 para inyectar altitud negativa.")
            return
        contexto.actualizar_controles(
            vuelo=vuelo,
            rumbo=calcular_rumbo(vuelo.punto_inicio, PUNTOS_ESCENARIO["TGA"]),
            velocidad_kt=320,
            vertical_rate=-4000,
            descripcion="Anomalia: altitud negativa forzada",
        )

    eventos.append(
        EventoProgramado(
            instante_cet=instante_neg_alt,
            descripcion="Inyeccion de altitud negativa en VLG201",
            accion=accion_altitud_negativa,
        )
    )

    instante_salto = datetime(
        year=fecha_base.year,
        month=fecha_base.month,
        day=fecha_base.day,
        hour=6,
        minute=18,
        second=45,
        tzinfo=zona_cet,
    )

    def accion_salto_posicion(contexto: ContextoSimulacion) -> None:
        vuelo = contexto.buscar_vuelo_por_id("ARR201")
        if not vuelo:
            return
        codigo_hex = contexto.obtener_hex(vuelo, permitir_faltante=True)
        if not codigo_hex:
            return
        cuerpo_peticion = {
            "heading": 45.0,
            "speed": 500,
            "vertical_rate": 0,
        }
        if contexto.modo_simulacion:
            logging.info("[DRY-RUN] Salto de posicion para ARR201 -> %s", cuerpo_peticion)
            return
        url = f"{contexto.url_base}/simulation/aircraft/{codigo_hex}/controls"
        respuesta = contexto.sesion.put(url, json=cuerpo_peticion, timeout=5)
        if not respuesta.ok:
            logging.warning("Error aplicando salto de posicion: %s %s", respuesta.status_code, respuesta.text)
        else:
            logging.info("Salto de posicion aplicado a ARR201 (simula spoofing).")

    eventos.append(
        EventoProgramado(
            instante_cet=instante_salto,
            descripcion="Anomalia: salto brusco de posicion",
            accion=accion_salto_posicion,
        )
    )

    instante_velocidad_negativa = datetime(
        year=fecha_base.year,
        month=fecha_base.month,
        day=fecha_base.day,
        hour=6,
        minute=19,
        second=0,
        tzinfo=zona_cet,
    )

    def accion_velocidad_negativa(contexto: ContextoSimulacion) -> None:
        vuelo = contexto.buscar_vuelo_por_id("ARR205")
        if not vuelo:
            logging.warning("No se encontro ARR205 para velocidad negativa.")
            return
        contexto.actualizar_controles(
            vuelo=vuelo,
            rumbo=180.0,
            velocidad_kt=-35.0,
            vertical_rate=0.0,
            descripcion="Anomalia: velocidad negativa en rodaje",
        )

    eventos.append(
        EventoProgramado(
            instante_cet=instante_velocidad_negativa,
            descripcion="Inyeccion de velocidad negativa",
            accion=accion_velocidad_negativa,
        )
    )

    return eventos
