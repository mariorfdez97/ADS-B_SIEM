from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from simulador_bcn_pkg.utils import calcular_rumbo, calcular_distancia_nm


@dataclass(frozen=True)
class PuntoNavegacion:
    """Representa un punto fijo de referencia (runway, fix, etc.)."""

    nombre: str
    latitud: float
    longitud: float


@dataclass
class TramoVuelo:
    """
    Define un tramo de vuelo recto con velocidad y altitud objetivo.

    Puede utilizar duraciones o rumbos manuales para cubrir maniobras como holds.
    """

    destino: PuntoNavegacion
    velocidad_objetivo: float
    altitud_destino_ft: float
    descripcion: str = ""
    duracion_manual_segundos: Optional[float] = None
    rumbo_manual: Optional[float] = None
    vertical_rate_manual: Optional[float] = None

    def calcular_parametros(
        self, origen: PuntoNavegacion, altitud_inicial_ft: float
    ) -> Dict[str, float]:
        """Calcula rumbo, vertical rate y duracion en segundos."""
        rumbo = (
            self.rumbo_manual
            if self.rumbo_manual is not None
            else calcular_rumbo(origen, self.destino)
        )
        if self.duracion_manual_segundos is not None:
            duracion_segundos = self.duracion_manual_segundos
        else:
            distancia_nm = calcular_distancia_nm(origen, self.destino)
            if self.velocidad_objetivo <= 0:
                raise ValueError("Velocidad objetivo debe ser positiva.")
            duracion_segundos = (distancia_nm / self.velocidad_objetivo) * 3600.0
        if self.vertical_rate_manual is not None:
            vertical_rate = self.vertical_rate_manual
        else:
            if duracion_segundos == 0:
                vertical_rate = 0.0
            else:
                variacion_altitud = self.altitud_destino_ft - altitud_inicial_ft
                vertical_rate = variacion_altitud / (duracion_segundos / 60.0)
            # Evita rechazos de la API limitando a 3000 fpm (rango permitido).
            # Evita rechazos de la API limitando a 3000 fpm (rango permitido).
            if vertical_rate > 3000:
                vertical_rate = 3000.0
            if vertical_rate < -3000:
                vertical_rate = -3000.0
        return {
            "rumbo": rumbo,
            "duracion_segundos": duracion_segundos,
            "vertical_rate": vertical_rate,
        }


@dataclass
class EventoProgramado:
    """Accion atomica programada a una hora concreta (CET)."""

    instante_cet: datetime
    descripcion: str
    accion: Callable[["ContextoSimulacion"], None]


@dataclass
class VueloSimulado:
    """
    Agrupa los parametros y tramos de cada aeronave simulada.

    - `hora_creacion_cet`: momento en el que se invoca la API para crear el avion.
    - `hora_inicio_tramos_cet`: primer momento en el que se le asignan controles.
    """

    identificador: str
    tipo_aeronave: str
    punto_inicio: PuntoNavegacion
    hora_creacion_cet: datetime
    hora_inicio_tramos_cet: datetime
    altitud_inicial_ft: float
    velocidad_inicial_kt: float
    rumbo_inicial: float
    tramos: List[TramoVuelo]
    eliminar_al_final: bool = True
    hexadecimal: Optional[str] = field(default=None, init=False)

    def generar_eventos(self) -> List[EventoProgramado]:
        """Construye la secuencia completa de eventos para este vuelo."""
        eventos: List[EventoProgramado] = []

        def accion_creacion(contexto: "ContextoSimulacion") -> None:
            contexto.crear_aeronave(
                vuelo=self,
                latitud=self.punto_inicio.latitud,
                longitud=self.punto_inicio.longitud,
                altitud_ft=self.altitud_inicial_ft,
                rumbo=self.rumbo_inicial,
                velocidad_kt=self.velocidad_inicial_kt,
                vertical_rate=self.generar_vertical_rate_inicial(),
            )

        eventos.append(
            EventoProgramado(
                instante_cet=self.hora_creacion_cet,
                descripcion=f"Creacion de {self.identificador}",
                accion=accion_creacion,
            )
        )

        instante_actual = self.hora_inicio_tramos_cet
        altitud_actual = self.altitud_inicial_ft
        punto_actual = self.punto_inicio

        for indice, tramo in enumerate(self.tramos, start=1):
            parametros = tramo.calcular_parametros(punto_actual, altitud_actual)
            rumbo = parametros["rumbo"]
            duracion = parametros["duracion_segundos"]
            vertical_rate = parametros["vertical_rate"]
            descripcion = tramo.descripcion or f"Tramo {indice} de {self.identificador}"

            def accion_tramo(
                contexto: "ContextoSimulacion",
                vuelo: VueloSimulado = self,
                rumbo_tramo: float = rumbo,
                velocidad_tramo: float = tramo.velocidad_objetivo,
                vertical_rate_tramo: float = vertical_rate,
                info: str = descripcion,
            ) -> None:
                contexto.actualizar_controles(
                    vuelo=vuelo,
                    rumbo=rumbo_tramo,
                    velocidad_kt=velocidad_tramo,
                    vertical_rate=vertical_rate_tramo,
                    descripcion=info,
                )

            eventos.append(
                EventoProgramado(
                    instante_cet=instante_actual,
                    descripcion=descripcion,
                    accion=accion_tramo,
                )
            )

            altitud_actual = tramo.altitud_destino_ft
            punto_actual = tramo.destino
            instante_actual = instante_actual + timedelta(seconds=duracion)

        if self.eliminar_al_final:
            def accion_eliminacion(contexto: "ContextoSimulacion", vuelo: VueloSimulado = self) -> None:
                contexto.eliminar_aeronave(vuelo=vuelo)

            eventos.append(
                EventoProgramado(
                    instante_cet=instante_actual,
                    descripcion=f"Eliminacion de {self.identificador}",
                    accion=accion_eliminacion,
                )
            )

        return eventos

    def generar_vertical_rate_inicial(self) -> float:
        """Permite definir una razon de ascenso inicial suave."""
        if self.velocidad_inicial_kt == 0:
            return 0.0
        return 1_000.0

    def generar_plan_de_vuelo(self) -> List[Dict[str, float]]:
        """Genera la lista de puntos que componen el plan de vuelo."""
        plan = []
        # Punto inicial
        plan.append({
            "lat": self.punto_inicio.latitud,
            "lon": self.punto_inicio.longitud,
            "altitude": self.altitud_inicial_ft,
            "speed": self.velocidad_inicial_kt,
            "heading": self.rumbo_inicial
        })

        for tramo in self.tramos:
            plan.append({
                "lat": tramo.destino.latitud,
                "lon": tramo.destino.longitud,
                "altitude": tramo.altitud_destino_ft,
                "speed": tramo.velocidad_objetivo,
                "heading": 0.0 # El rumbo se calcula dinamicamente
            })
        
        return plan
