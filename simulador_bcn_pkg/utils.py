import math
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Evita dependencias circulares en tiempo de ejecución
    from simulador_bcn_pkg.models import PuntoNavegacion


def calcular_rumbo(origen: "PuntoNavegacion", destino: "PuntoNavegacion") -> float:
    """Devuelve el rumbo (grados verdaderos) del segmento origen->destino."""
    lat1, lon1 = map(math.radians, (origen.latitud, origen.longitud))
    lat2, lon2 = map(math.radians, (destino.latitud, destino.longitud))
    diferencia_longitud = lon2 - lon1
    componente_y = math.sin(diferencia_longitud) * math.cos(lat2)
    componente_x = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(diferencia_longitud)
    )
    rumbo = math.degrees(math.atan2(componente_y, componente_x))
    return (rumbo + 360.0) % 360.0


def calcular_distancia_nm(
    origen: "PuntoNavegacion", destino: "PuntoNavegacion"
) -> float:
    """Calcula la distancia en millas nauticas entre dos puntos."""
    radio_tierra_m = 6_371_000
    lat1, lon1 = map(math.radians, (origen.latitud, origen.longitud))
    lat2, lon2 = map(math.radians, (destino.latitud, destino.longitud))
    diferencia_latitud = lat2 - lat1
    diferencia_longitud = lon2 - lon1
    componente_a = (
        math.sin(diferencia_latitud / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(diferencia_longitud / 2) ** 2
    )
    componente_c = 2 * math.atan2(math.sqrt(componente_a), math.sqrt(1 - componente_a))
    distancia_m = radio_tierra_m * componente_c
    return distancia_m / 1_852.0


def hora_cet(fecha: datetime, horas: int, minutos: int, segundos: int = 0) -> datetime:
    """Combina fecha base con hora CET (UTC+1)."""
    zona_cet = timezone(timedelta(hours=1))
    return datetime(
        year=fecha.year,
        month=fecha.month,
        day=fecha.day,
        hour=horas,
        minute=minutos,
        second=segundos,
        tzinfo=zona_cet,
    )
