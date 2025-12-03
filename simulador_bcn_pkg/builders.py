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
    """Define los vuelos principales del escenario."""
    puntos = PUNTOS_ESCENARIO

    vuelos: List[VueloSimulado] = []

    # ----------------------- VLG201 - SID TGA7W ---------------------------------------
    hora_creacion_vlg = hora_cet(fecha_base, 5, 59, 0)
    hora_inicio_vlg = hora_cet(fecha_base, 6, 0, 0)
    tramos_vlg = [
        TramoVuelo(
            destino=puntos["NELSO"],
            velocidad_objetivo=200,
            altitud_destino_ft=3_000,
            descripcion="VLG201 tramo 1: despegue y ascenso a NELSO",
        ),
        TramoVuelo(
            destino=puntos["TARRA"],
            velocidad_objetivo=250,
            altitud_destino_ft=8_000,
            descripcion="VLG201 tramo 2: rumbo oeste hacia TARRA",
        ),
        TramoVuelo(
            destino=puntos["TGA"],
            velocidad_objetivo=280,
            altitud_destino_ft=12_000,
            descripcion="VLG201 tramo 3: cruce de TGA",
        ),
        TramoVuelo(
            destino=puntos["LORET"],
            velocidad_objetivo=320,
            altitud_destino_ft=18_000,
            descripcion="VLG201 tramo 4: salida del TMA via LORET",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="VLG201",
            tipo_aeronave="A320",
            punto_inicio=puntos["RWY07R"],
            hora_creacion_cet=hora_creacion_vlg,
            hora_inicio_tramos_cet=hora_inicio_vlg,
            altitud_inicial_ft=0.0,
            velocidad_inicial_kt=0.0,
            rumbo_inicial=85.6,
            tramos=tramos_vlg,
        )
    )

    # ----------------------- IBE432 - SID KENAS5N -------------------------------------
    hora_creacion_ibe = hora_cet(fecha_base, 6, 0, 15)
    hora_inicio_ibe = hora_cet(fecha_base, 6, 0, 45)
    tramos_ibe = [
        TramoVuelo(
            destino=puntos["MASNU"],
            velocidad_objetivo=190,
            altitud_destino_ft=4_000,
            descripcion="IBE432 tramo 1: ascenso hacia MASNU",
        ),
        TramoVuelo(
            destino=puntos["BAMES"],
            velocidad_objetivo=240,
            altitud_destino_ft=9_000,
            descripcion="IBE432 tramo 2: ruta norte a BAMES",
        ),
        TramoVuelo(
            destino=puntos["KENAS"],
            velocidad_objetivo=280,
            altitud_destino_ft=15_000,
            descripcion="IBE432 tramo 3: intercepta KENAS",
        ),
        TramoVuelo(
            destino=puntos["GIRON"],
            velocidad_objetivo=300,
            altitud_destino_ft=20_000,
            descripcion="IBE432 tramo 4: salida a GIRON",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="IBE432",
            tipo_aeronave="A320",
            punto_inicio=puntos["RWY07L"],
            hora_creacion_cet=hora_creacion_ibe,
            hora_inicio_tramos_cet=hora_inicio_ibe,
            altitud_inicial_ft=0.0,
            velocidad_inicial_kt=0.0,
            rumbo_inicial=85.0,
            tramos=tramos_ibe,
        )
    )

    # ----------------------- VY6502 - SID LORET1W -------------------------------------
    hora_creacion_vy = hora_cet(fecha_base, 6, 0, 45)
    hora_inicio_vy = hora_cet(fecha_base, 6, 1, 30)
    tramos_vy = [
        TramoVuelo(
            destino=puntos["NELSO"],
            velocidad_objetivo=200,
            altitud_destino_ft=3_000,
            descripcion="VY6502 tramo 1: salida costera NELSO",
        ),
        TramoVuelo(
            destino=puntos["SITGE"],
            velocidad_objetivo=240,
            altitud_destino_ft=7_000,
            descripcion="VY6502 tramo 2: viraje hacia SITGE",
        ),
        TramoVuelo(
            destino=puntos["TGA"],
            velocidad_objetivo=280,
            altitud_destino_ft=12_000,
            descripcion="VY6502 tramo 3: ascenso sobre TGA",
        ),
        TramoVuelo(
            destino=puntos["LORET"],
            velocidad_objetivo=320,
            altitud_destino_ft=19_000,
            descripcion="VY6502 tramo 4: salida del TMA rumbo LORET",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="VY6502",
            tipo_aeronave="A320",
            punto_inicio=puntos["RWY07R"],
            hora_creacion_cet=hora_creacion_vy,
            hora_inicio_tramos_cet=hora_inicio_vy,
            altitud_inicial_ft=0.0,
            velocidad_inicial_kt=0.0,
            rumbo_inicial=85.6,
            tramos=tramos_vy,
        )
    )

    # ----------------------- RYR221 - SID GIRON1N -------------------------------------
    hora_creacion_ryr221 = hora_cet(fecha_base, 6, 1, 20)
    hora_inicio_ryr221 = hora_cet(fecha_base, 6, 2, 15)
    tramos_ryr221 = [
        TramoVuelo(
            destino=puntos["MASNU"],
            velocidad_objetivo=200,
            altitud_destino_ft=4_000,
            descripcion="RYR221 tramo 1: ascenso inicial hacia MASNU",
        ),
        TramoVuelo(
            destino=puntos["BAMES"],
            velocidad_objetivo=240,
            altitud_destino_ft=9_000,
            descripcion="RYR221 tramo 2: seguimiento costa norte",
        ),
        TramoVuelo(
            destino=puntos["KENAS"],
            velocidad_objetivo=260,
            altitud_destino_ft=13_000,
            descripcion="RYR221 tramo 3: cruce Girona TMA",
        ),
        TramoVuelo(
            destino=puntos["GIRON"],
            velocidad_objetivo=300,
            altitud_destino_ft=17_000,
            descripcion="RYR221 tramo 4: salida FIR via GIRON",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="RYR221",
            tipo_aeronave="B738",
            punto_inicio=puntos["RWY07L"],
            hora_creacion_cet=hora_creacion_ryr221,
            hora_inicio_tramos_cet=hora_inicio_ryr221,
            altitud_inicial_ft=0.0,
            velocidad_inicial_kt=0.0,
            rumbo_inicial=85.0,
            tramos=tramos_ryr221,
        )
    )

    # ----------------------- EZY8104 - STAR KENAS1M + ILS -----------------------------
    hora_creacion_ezy = hora_cet(fecha_base, 5, 57, 0)
    hora_inicio_ezy = hora_cet(fecha_base, 6, 4, 0)
    tramos_ezy = [
        TramoVuelo(
            destino=puntos["BAMES"],
            velocidad_objetivo=250,
            altitud_destino_ft=10_000,
            descripcion="EZY8104 tramo 1: KENAS a BAMES",
        ),
        TramoVuelo(
            destino=puntos["MASNU"],
            velocidad_objetivo=230,
            altitud_destino_ft=7_000,
            descripcion="EZY8104 tramo 2: descenso hacia MASNU",
        ),
        TramoVuelo(
            destino=puntos["SLL"],
            velocidad_objetivo=210,
            altitud_destino_ft=6_000,
            descripcion="EZY8104 tramo 3: SLL inicial",
        ),
        TramoVuelo(
            destino=puntos["DOWNWIND_N"],
            velocidad_objetivo=200,
            altitud_destino_ft=5_500,
            descripcion="EZY8104 tramo 4: tramo a downwind norte",
        ),
        TramoVuelo(
            destino=puntos["BASE_07L"],
            velocidad_objetivo=190,
            altitud_destino_ft=4_500,
            descripcion="EZY8104 tramo 5: tramo base 07L",
        ),
        TramoVuelo(
            destino=puntos["IF_07L"],
            velocidad_objetivo=180,
            altitud_destino_ft=3_500,
            descripcion="EZY8104 tramo 6: intercepta localizador ILS 07L",
        ),
        TramoVuelo(
            destino=puntos["DOBRO"],
            velocidad_objetivo=170,
            altitud_destino_ft=2_500,
            descripcion="EZY8104 tramo 7: tramo final de aproximacion",
        ),
        TramoVuelo(
            destino=puntos["RWY07L"],
            velocidad_objetivo=140,
            altitud_destino_ft=50,
            descripcion="EZY8104 tramo 8: final ILS 07L",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="EZY8104",
            tipo_aeronave="A320",
            punto_inicio=puntos["KENAS"],
            hora_creacion_cet=hora_creacion_ezy,
            hora_inicio_tramos_cet=hora_inicio_ezy,
            altitud_inicial_ft=12_000,
            velocidad_inicial_kt=250,
            rumbo_inicial=223.0,
            tramos=tramos_ezy,
            eliminar_al_final=False,
        )
    )

    # ----------------------- RYR611 - STAR TGA3W + HOLD -------------------------------
    hora_creacion_ryr = hora_cet(fecha_base, 6, 4, 30)
    hora_inicio_ryr = hora_cet(fecha_base, 6, 5, 0)
    tramos_ryr = [
        TramoVuelo(
            destino=puntos["SITGE"],
            velocidad_objetivo=280,
            altitud_destino_ft=15_000,
            descripcion="RYR611 tramo 1: TGA a SITGE",
        ),
        TramoVuelo(
            destino=puntos["SARGO"],
            velocidad_objetivo=240,
            altitud_destino_ft=9_000,
            descripcion="RYR611 tramo 2: aproximacion via SARGO",
        ),
        TramoVuelo(
            destino=puntos["UBAGA"],
            velocidad_objetivo=220,
            altitud_destino_ft=7_000,
            descripcion="RYR611 tramo 3: IAF UBAGA",
        ),
        TramoVuelo(
            destino=puntos["SLL"],
            velocidad_objetivo=200,
            altitud_destino_ft=5_000,
            descripcion="RYR611 tramo 4: rumbo a SLL para espera",
        ),
        TramoVuelo(
            destino=puntos["HOLD_W"],
            velocidad_objetivo=180,
            altitud_destino_ft=5_000,
            descripcion="RYR611 hold tramo outbound",
            duracion_manual_segundos=45.0,
            rumbo_manual=246.0,
            vertical_rate_manual=0.0,
        ),
        TramoVuelo(
            destino=puntos["HOLD_E"],
            velocidad_objetivo=180,
            altitud_destino_ft=5_000,
            descripcion="RYR611 hold tramo inbound",
            duracion_manual_segundos=45.0,
            rumbo_manual=66.0,
            vertical_rate_manual=0.0,
        ),
        TramoVuelo(
            destino=puntos["DOBRO"],
            velocidad_objetivo=170,
            altitud_destino_ft=2_500,
            descripcion="RYR611 tramo 5: abandonando hold hacia DOBRO",
        ),
        TramoVuelo(
            destino=puntos["DOWNWIND_N"],
            velocidad_objetivo=180,
            altitud_destino_ft=4_500,
            descripcion="RYR611 tramo 6: downwind norte",
        ),
        TramoVuelo(
            destino=puntos["BASE_07L"],
            velocidad_objetivo=170,
            altitud_destino_ft=3_800,
            descripcion="RYR611 tramo 7: tramo base",
        ),
        TramoVuelo(
            destino=puntos["IF_07L"],
            velocidad_objetivo=160,
            altitud_destino_ft=3_000,
            descripcion="RYR611 tramo 8: captura localizador ILS 07L",
        ),
        TramoVuelo(
            destino=puntos["RWY07L"],
            velocidad_objetivo=140,
            altitud_destino_ft=50,
            descripcion="RYR611 tramo 9: final ILS 07L",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="RYR611",
            tipo_aeronave="B738",
            punto_inicio=puntos["TGA"],
            hora_creacion_cet=hora_creacion_ryr,
            hora_inicio_tramos_cet=hora_inicio_ryr,
            altitud_inicial_ft=20_000,
            velocidad_inicial_kt=280,
            rumbo_inicial=80.0,
            tramos=tramos_ryr,
            eliminar_al_final=False,
        )
    )

    # ----------------------- DLH1421 - STAR via LORET ---------------------------------
    hora_creacion_dlh = hora_cet(fecha_base, 5, 56, 30)
    hora_inicio_dlh = hora_cet(fecha_base, 6, 3, 0)
    tramos_dlh = [
        TramoVuelo(
            destino=puntos["SITGE"],
            velocidad_objetivo=250,
            altitud_destino_ft=15_000,
            descripcion="DLH1421 tramo 1: LORET a SITGE",
        ),
        TramoVuelo(
            destino=puntos["SARGO"],
            velocidad_objetivo=230,
            altitud_destino_ft=9_000,
            descripcion="DLH1421 tramo 2: descenso sobre costa",
        ),
        TramoVuelo(
            destino=puntos["UBAGA"],
            velocidad_objetivo=210,
            altitud_destino_ft=6_000,
            descripcion="DLH1421 tramo 3: IAF UBAGA",
        ),
        TramoVuelo(
            destino=puntos["SLL"],
            velocidad_objetivo=190,
            altitud_destino_ft=5_000,
            descripcion="DLH1421 tramo 4: tramo intermedio SLL",
        ),
        TramoVuelo(
            destino=puntos["DOWNWIND_N"],
            velocidad_objetivo=185,
            altitud_destino_ft=4_500,
            descripcion="DLH1421 tramo 5: downwind norte",
        ),
        TramoVuelo(
            destino=puntos["BASE_07L"],
            velocidad_objetivo=175,
            altitud_destino_ft=3_800,
            descripcion="DLH1421 tramo 6: tramo base 07L",
        ),
        TramoVuelo(
            destino=puntos["IF_07L"],
            velocidad_objetivo=165,
            altitud_destino_ft=3_000,
            descripcion="DLH1421 tramo 7: intercepta ILS 07L",
        ),
        TramoVuelo(
            destino=puntos["DOBRO"],
            velocidad_objetivo=160,
            altitud_destino_ft=2_500,
            descripcion="DLH1421 tramo 8: tramo final de aproximacion",
        ),
        TramoVuelo(
            destino=puntos["RWY07L"],
            velocidad_objetivo=150,
            altitud_destino_ft=50,
            descripcion="DLH1421 tramo 9: final pista 07L",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="DLH1421",
            tipo_aeronave="A321",
            punto_inicio=puntos["LORET"],
            hora_creacion_cet=hora_creacion_dlh,
            hora_inicio_tramos_cet=hora_inicio_dlh,
            altitud_inicial_ft=18_000,
            velocidad_inicial_kt=250,
            rumbo_inicial=104.0,
            tramos=tramos_dlh,
            eliminar_al_final=False,
        )
    )

    # ----------------------- AFR1738 - STAR via MASNU ---------------------------------
    hora_creacion_afr = hora_cet(fecha_base, 5, 57, 30)
    hora_inicio_afr = hora_cet(fecha_base, 6, 6, 0)
    tramos_afr = [
        TramoVuelo(
            destino=puntos["SLL"],
            velocidad_objetivo=220,
            altitud_destino_ft=6_000,
            descripcion="AFR1738 tramo 1: MASNU a SLL",
        ),
        TramoVuelo(
            destino=puntos["DOWNWIND_N"],
            velocidad_objetivo=200,
            altitud_destino_ft=5_000,
            descripcion="AFR1738 tramo 2: downwind norte",
        ),
        TramoVuelo(
            destino=puntos["BASE_07R"],
            velocidad_objetivo=185,
            altitud_destino_ft=4_000,
            descripcion="AFR1738 tramo 3: tramo base 07R",
        ),
        TramoVuelo(
            destino=puntos["IF_07R"],
            velocidad_objetivo=170,
            altitud_destino_ft=3_200,
            descripcion="AFR1738 tramo 4: captura localizador 07R",
        ),
        TramoVuelo(
            destino=puntos["RWY07R"],
            velocidad_objetivo=150,
            altitud_destino_ft=50,
            descripcion="AFR1738 tramo 5: final 07R",
        ),
    ]
    vuelos.append(
        VueloSimulado(
            identificador="AFR1738",
            tipo_aeronave="A320",
            punto_inicio=puntos["MASNU"],
            hora_creacion_cet=hora_creacion_afr,
            hora_inicio_tramos_cet=hora_inicio_afr,
            altitud_inicial_ft=9_000,
            velocidad_inicial_kt=220,
            rumbo_inicial=284.0,
            tramos=tramos_afr,
            eliminar_al_final=False,
        )
    )

    if incluir_anomalias:
        hora_creacion_ghost = hora_cet(fecha_base, 6, 8, 0)
        hora_inicio_ghost = hora_creacion_ghost + timedelta(seconds=10)
        tramos_ghost = [
            TramoVuelo(
                destino=puntos["GHOST"],
                velocidad_objetivo=620,
                altitud_destino_ft=35_000,
                descripcion="GHOST01 tramo 1: aparicion supersanica",
                duracion_manual_segundos=30.0,
                rumbo_manual=90.0,
                vertical_rate_manual=0.0,
            )
        ]
        vuelos.append(
            VueloSimulado(
                identificador="GHOST01",
                tipo_aeronave="UNKNOWN",
                punto_inicio=puntos["GHOST"],
                hora_creacion_cet=hora_creacion_ghost,
                hora_inicio_tramos_cet=hora_inicio_ghost,
                altitud_inicial_ft=35_000,
                velocidad_inicial_kt=620,
                rumbo_inicial=90.0,
                tramos=tramos_ghost,
            )
        )

        # Trayectoria con altitud negativa persistente
        hora_creacion_anm_alt = hora_cet(fecha_base, 6, 2, 30)
        hora_inicio_anm_alt = hora_creacion_anm_alt + timedelta(seconds=15)
        tramos_anm_alt = [
            TramoVuelo(
                destino=puntos["ANM_WEST"],
                velocidad_objetivo=450,
                altitud_destino_ft=-500,
                descripcion="ANMALT1 tramo 1: descenso a altitud negativa",
                duracion_manual_segundos=40.0,
                vertical_rate_manual=-4500.0,
            ),
            TramoVuelo(
                destino=puntos["GHOST"],
                velocidad_objetivo=480,
                altitud_destino_ft=9_000,
                descripcion="ANMALT1 tramo 2: ascenso extremo tras vuelo rasante",
                duracion_manual_segundos=55.0,
                vertical_rate_manual=10_500.0,
            ),
        ]
        vuelos.append(
            VueloSimulado(
                identificador="ANMALT1",
                tipo_aeronave="SIM",
                punto_inicio=puntos["ANM_EAST"],
                hora_creacion_cet=hora_creacion_anm_alt,
                hora_inicio_tramos_cet=hora_inicio_anm_alt,
                altitud_inicial_ft=1_500,
                velocidad_inicial_kt=320,
                rumbo_inicial=270.0,
                tramos=tramos_anm_alt,
            )
        )

        # Trayectoria con velocidades imposibles a baja cota
        hora_creacion_anm_spd = hora_cet(fecha_base, 6, 3, 15)
        hora_inicio_anm_spd = hora_creacion_anm_spd + timedelta(seconds=15)
        tramos_anm_spd = [
            TramoVuelo(
                destino=puntos["MASNU"],
                velocidad_objetivo=650,
                altitud_destino_ft=2_000,
                descripcion="ANMSPD1 tramo 1: crucero supersónico en TMA",
                duracion_manual_segundos=35.0,
                vertical_rate_manual=0.0,
            ),
            TramoVuelo(
                destino=puntos["ANM_SOUTH"],
                velocidad_objetivo=700,
                altitud_destino_ft=1_500,
                descripcion="ANMSPD1 tramo 2: viraje supersónico sin ascenso significativo",
                duracion_manual_segundos=30.0,
                vertical_rate_manual=-1000.0,
            ),
        ]
        vuelos.append(
            VueloSimulado(
                identificador="ANMSPD1",
                tipo_aeronave="SIM",
                punto_inicio=puntos["ANM_EAST"],
                hora_creacion_cet=hora_creacion_anm_spd,
                hora_inicio_tramos_cet=hora_inicio_anm_spd,
                altitud_inicial_ft=2_000,
                velocidad_inicial_kt=620,
                rumbo_inicial=310.0,
                tramos=tramos_anm_spd,
            )
        )

        # Trayectoria con saltos laterales bruscos
        hora_creacion_anm_jump = hora_cet(fecha_base, 6, 3, 45)
        hora_inicio_anm_jump = hora_creacion_anm_jump + timedelta(seconds=10)
        tramos_anm_jump = [
            TramoVuelo(
                destino=puntos["ANM_EAST"],
                velocidad_objetivo=400,
                altitud_destino_ft=8_000,
                descripcion="ANMJMP1 tramo 1: teletransporte inicial",
                duracion_manual_segundos=15.0,
                rumbo_manual=45.0,
                vertical_rate_manual=12_000.0,
            ),
            TramoVuelo(
                destino=puntos["ANM_WEST"],
                velocidad_objetivo=420,
                altitud_destino_ft=500,
                descripcion="ANMJMP1 tramo 2: caída abrupta tras salto lateral",
                duracion_manual_segundos=20.0,
                rumbo_manual=260.0,
                vertical_rate_manual=-10_500.0,
            ),
            TramoVuelo(
                destino=puntos["ANM_SOUTH"],
                velocidad_objetivo=380,
                altitud_destino_ft=7_500,
                descripcion="ANMJMP1 tramo 3: subida instantánea fuera de envolvente",
                duracion_manual_segundos=18.0,
                rumbo_manual=170.0,
                vertical_rate_manual=12_500.0,
            ),
        ]
        vuelos.append(
            VueloSimulado(
                identificador="ANMJMP1",
                tipo_aeronave="SIM",
                punto_inicio=puntos["GHOST"],
                hora_creacion_cet=hora_creacion_anm_jump,
                hora_inicio_tramos_cet=hora_inicio_anm_jump,
                altitud_inicial_ft=500,
                velocidad_inicial_kt=350,
                rumbo_inicial=70.0,
                tramos=tramos_anm_jump,
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
        vuelo = contexto.buscar_vuelo_por_id("VLG201")
        if not vuelo:
            logging.warning("No se encontro VLG201 para inyectar altitud negativa.")
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
        vuelo = contexto.buscar_vuelo_por_id("VLG201")
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
            logging.info("[DRY-RUN] Salto de posicion para VLG201 -> %s", cuerpo_peticion)
            return
        url = f"{contexto.url_base}/simulation/aircraft/{codigo_hex}/controls"
        respuesta = contexto.sesion.put(url, json=cuerpo_peticion, timeout=5)
        if not respuesta.ok:
            logging.warning("Error aplicando salto de posicion: %s %s", respuesta.status_code, respuesta.text)
        else:
            logging.info("Salto de posicion aplicado a VLG201 (simula spoofing).")

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
        vuelo = contexto.buscar_vuelo_por_id("EZY8104")
        if not vuelo:
            logging.warning("No se encontro EZY8104 para velocidad negativa.")
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
