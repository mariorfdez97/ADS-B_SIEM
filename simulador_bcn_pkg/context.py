import logging
import time
from typing import Dict, List, Optional

try:
    import requests
except ImportError as error:
    raise SystemExit(
        "El modulo 'requests' es obligatorio. "
        "Instalalo con `pip install requests` antes de ejecutar este script."
    ) from error

from simulador_bcn_pkg.models import VueloSimulado


class ContextoSimulacion:
    """Gestiona la sesion HTTP y el registro de aeronaves creadas."""

    def __init__(self, url_base: str, modo_simulacion: bool, reintentos: int = 3) -> None:
        self.url_base = url_base.rstrip("/")
        self.modo_simulacion = modo_simulacion
        self.reintentos = reintentos
        self.sesion = requests.Session()
        self.hex_por_vuelo: Dict[str, str] = {}
        self.vuelos_registrados: List[VueloSimulado] = []

    def crear_aeronave(
        self,
        vuelo: VueloSimulado,
        latitud: float,
        longitud: float,
        altitud_ft: float,
        rumbo: float,
        velocidad_kt: float,
        vertical_rate: float,
    ) -> None:
        """Invoca POST /simulation/aircraft y guarda el hex retornado."""
        cuerpo_peticion = {
            "lat": latitud,
            "lon": longitud,
            "altitude": altitud_ft,
            "heading": rumbo,
            "speed": velocidad_kt,
            "vertical_rate": vertical_rate,
            "flight_plan": vuelo.generar_plan_de_vuelo(),
        }
        if self.modo_simulacion:
            logging.info("[DRY-RUN] Creacion %s -> %s", vuelo.identificador, cuerpo_peticion)
            vuelo.hexadecimal = f"DRY{len(self.hex_por_vuelo):03d}"
            self.hex_por_vuelo[vuelo.identificador] = vuelo.hexadecimal
            return
        url = f"{self.url_base}/simulation/aircraft"
        for intento in range(1, self.reintentos + 1):
            respuesta = self.sesion.post(url, json=cuerpo_peticion, timeout=5)
            if respuesta.ok:
                datos = respuesta.json()
                codigo_hex = datos.get("hex") or datos.get("aircraft", {}).get("hex")
                if not codigo_hex:
                    raise RuntimeError("La respuesta de creacion no devolvio hex.")
                vuelo.hexadecimal = codigo_hex
                self.hex_por_vuelo[vuelo.identificador] = codigo_hex
                logging.info(
                    "Creado %s con hex %s en intento %s",
                    vuelo.identificador,
                    codigo_hex,
                    intento,
                )
                return
            logging.warning(
                "Fallo creando %s (intento %s): %s",
                vuelo.identificador,
                intento,
                respuesta.text,
            )
            time.sleep(1.0)
        raise RuntimeError(f"No se pudo crear {vuelo.identificador} tras {self.reintentos} intentos.")

    def actualizar_controles(
        self,
        vuelo: VueloSimulado,
        rumbo: float,
        velocidad_kt: float,
        vertical_rate: float,
        descripcion: str,
    ) -> None:
        """Invoca PUT /simulation/aircraft/{hex}/controls."""
        codigo_hex = self.obtener_hex(vuelo)
        cuerpo_peticion = {
            "heading": rumbo,
            "speed": velocidad_kt,
            "vertical_rate": vertical_rate,
        }
        if self.modo_simulacion:
            logging.info(
                "[DRY-RUN] Actualizacion %s (%s) -> %s",
                vuelo.identificador,
                descripcion,
                cuerpo_peticion,
            )
            return
        url = f"{self.url_base}/simulation/aircraft/{codigo_hex}/controls"
        respuesta = self.sesion.put(url, json=cuerpo_peticion, timeout=5)
        if not respuesta.ok:
            raise RuntimeError(
                f"Error actualizando {vuelo.identificador}: {respuesta.status_code} {respuesta.text}"
            )
        logging.info(
            "Actualizacion enviada para %s (%s): rumbo %.1f, vel %.1f kt, vr %.0f ft/min",
            vuelo.identificador,
            descripcion,
            rumbo,
            velocidad_kt,
            vertical_rate,
        )

    def eliminar_aeronave(self, vuelo: VueloSimulado) -> None:
        """Invoca DELETE /simulation/aircraft/{hex}."""
        codigo_hex = self.obtener_hex(vuelo, permitir_faltante=True)
        if not codigo_hex:
            logging.warning("No se conoce hex para %s, se omite eliminacion.", vuelo.identificador)
            return
        if self.modo_simulacion:
            logging.info("[DRY-RUN] Eliminacion de %s (hex %s)", vuelo.identificador, codigo_hex)
            return
        url = f"{self.url_base}/simulation/aircraft/{codigo_hex}"
        respuesta = self.sesion.delete(url, timeout=5)
        if not respuesta.ok:
            logging.warning(
                "Error eliminando %s: %s %s",
                vuelo.identificador,
                respuesta.status_code,
                respuesta.text,
            )
        else:
            logging.info("Aeronave %s eliminada.", vuelo.identificador)

    def obtener_hex(self, vuelo: VueloSimulado, permitir_faltante: bool = False) -> Optional[str]:
        """Recupera el hex conocido para un vuelo."""
        codigo_hex = self.hex_por_vuelo.get(vuelo.identificador)
        if not codigo_hex and not permitir_faltante:
            raise RuntimeError(
                f"No se ha registrado hex para {vuelo.identificador}. "
                "Verifica que la creacion se ejecuto correctamente."
            )
        return codigo_hex

    def buscar_vuelo_por_id(self, identificador: str) -> Optional[VueloSimulado]:
        """Devuelve el vuelo registrado con el identificador solicitado."""
        for vuelo in self.vuelos_registrados:
            if vuelo.identificador == identificador:
                return vuelo
        return None
