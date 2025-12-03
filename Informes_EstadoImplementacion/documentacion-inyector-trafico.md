# Documentacion del inyector de trafico ADS-B (Python)

Esta guia describe con detalle el inyector de trafico simulado escrito en Python que vive en `simulador_bcn.py` y el paquete `simulador_bcn_pkg/`. El objetivo del inyector es poblar la API de Co-ATC con aeronaves virtuales y controlar su evolucion en el tiempo (rutas, velocidades, perfiles verticales y anomalías) para alimentar el laboratorio SIEM.

## Que es y como funciona
- **Punto de entrada**: `simulador_bcn.py` solo delega en `simulador_bcn_pkg/cli.py`, donde se parsean argumentos y se arma el escenario.
- **Construccion de escenario**: `simulador_bcn_pkg/builders.py` define puntos de navegacion, vuelos regulares y, opcionalmente, vuelos/anomalias maliciosas.
- **Modelo de datos**: `simulador_bcn_pkg/models.py` provee `PuntoNavegacion`, `TramoVuelo`, `VueloSimulado` y `EventoProgramado`. Cada tramo calcula rumbo, duracion y razon de ascenso/descenso.
- **Ejecucion temporal**: `simulador_bcn_pkg/scheduler.py` ordena los eventos cronologicamente y los reproduce con un factor de tiempo (aceleracion) usando `time.monotonic`.
- **Interaccion con la API**: `simulador_bcn_pkg/context.py` usa `requests.Session` para enviar `POST /simulation/aircraft`, `PUT /simulation/aircraft/{hex}/controls` y `DELETE /simulation/aircraft/{hex}` hacia Co-ATC. Gestiona reintentos y mapeo vuelo→hex.
- **Utilidades**: `simulador_bcn_pkg/utils.py` calcula rumbos, distancias y genera fechas CET.

## Requisitos previos
- Python 3.11+ y `pip install requests`.
- Co-ATC levantado con API accesible (por defecto `http://127.0.0.1:8000/api/v1`).
- Permisos de red locales para alcanzar el puerto 8000.

## Ejecucion rapida
```
python3 simulador_bcn.py \
  --url-base http://127.0.0.1:8000/api/v1 \
  --fecha 2024-11-15 \
  --factor-tiempo 120 \
  --log-nivel INFO
```
- `--modo-prueba` activa dry-run (imprime payloads pero no llama a la API).
- `--incluir-anomalias` habilita vuelos y acciones maliciosas adicionales.

## Escenario base (sin anomalias)
- Ventana centrada en 06:00 CET. El factor de tiempo acelera la reproduccion (120 = 1 min simulado en 0.5 s reales).
- **Salidas**:  
  - `VLG201` A320 RWY07R → NELSO → TARRA → TGA → LORET.  
  - `IBE432` A320 RWY07L → MASNU → BAMES → KENAS → GIRON.  
  - `VY6502` A320 RWY07R → NELSO → SITGE → TGA → LORET.  
  - `RYR221` B738 RWY07L → MASNU → BAMES → KENAS → GIRON.
- **Llegadas/ILS y espera**:  
  - `EZY8104` A320 desde KENAS hasta ILS 07L via SLL/DOBRO.  
  - `RYR611` B738 desde TGA con espera en SLL y final 07L.  
  - `DLH1421` A321 desde LORET a ILS 07L.  
  - `AFR1738` A320 aproximacion corta MASNU → SLL → DOBRO → 07R.
- Cada vuelo se compone de tramos con velocidad/altitud objetivo y rumbo calculado dinamicamente; si la razon vertical supera ±3000 fpm se acota para evitar rechazos de la API.

## Anomalias opcionales
Se activan con `--incluir-anomalias` y se combinan con el escenario base:
- **Vuelos ficticios**:  
  - `GHOST01`: trayectoria supersónica fija.  
  - `ANMALT1`: descenso a altitud negativa y ascenso extremo.  
  - `ANMSPD1`: velocidades >650 kt a muy baja cota.  
  - `ANMJMP1`: saltos laterales y verticales bruscos.
- **Acciones sobre vuelos existentes** (`construir_anomalias`):  
  - 06:18:00 CET: fuerza altitud negativa en `VLG201`.  
  - 06:18:45 CET: salto de posicion/rumbo para `VLG201` (simula spoofing).  
  - 06:19:00 CET: velocidad negativa en rodaje para `EZY8104`.

## Flujo de ejecucion detallado
1) `cli.main` valida argumentos y fecha CET.  
2) `builders.construir_vuelos` registra `ContextoSimulacion.vuelos_registrados` y genera eventos de creacion, tramos y eliminacion por cada `VueloSimulado`.  
3) `construir_anomalias` añade eventos ad-hoc (si procede).  
4) `scheduler.ejecutar_eventos` calcula la espera real necesaria para cada evento en funcion del factor de tiempo y los dispara en orden.  
5) Cada evento invoca `ContextoSimulacion`:
   - **Creacion**: POST con lat/lon/altitud/heading/velocidad + `flight_plan` completo. El hex devuelto se asocia al identificador.  
   - **Control**: PUT por tramo con heading/velocidad/vertical_rate.  
   - **Eliminacion**: DELETE al finalizar (salvo que `eliminar_al_final=False`).

## Personalizacion y ampliacion
- **Nuevos puntos**: agrega `PuntoNavegacion` en `construir_puntos()` con nombre y coordenadas.
- **Nuevos vuelos**:
  - Define `hora_creacion_cet` y `hora_inicio_tramos_cet` con `utils.hora_cet`.
  - Crea la lista de `TramoVuelo`, usando rumbos automaticos o `rumbo_manual`/`duracion_manual_segundos` para holds o maniobras libres.
  - Instancia `VueloSimulado` con `eliminar_al_final=False` si quieres dejar el trafico persistente.
  - Incluye el vuelo en la lista devuelta por `construir_vuelos`.
- **Anomalias personalizadas**:
  - Añade funciones en `construir_anomalias` que consulten `ContextoSimulacion.buscar_vuelo_por_id` y llamen a `actualizar_controles` con valores fuera de la envolvente.
  - Si necesitas modificar posicion directamente, puedes invocar la API manualmente como en `accion_salto_posicion`.
- **Factor de tiempo**: sube el valor para acelerar ensayos masivos; baja a 1.0 si necesitas trazar cada peticion manualmente.

## Operacion y trazabilidad
- Logging configurado con `logging.basicConfig` en `cli.py`; niveles `DEBUG/INFO/WARNING/ERROR`.
- En `--modo-prueba` veras los payloads completos y los hex simulados `DRYxxx` sin tocar la API.
- En ejecucion real, los logs confirman hex asignado, control updates y eliminaciones. Ante fallos HTTP se reintenta hasta `reintentos=3` en la creacion.
- El scheduler usa `time.monotonic` para evitar saltos si cambia la hora del sistema.

## Diagnostico rapido
- **requests no instalado**: el script aborta con mensaje explicito; instala con `pip install requests`.
- **Conexion rechazada o 404**: verifica que Co-ATC este en `--url-base` y que `lanzar_lab.sh`/`docker-compose` esten activos.
- **Hex no encontrado**: ocurre si un POST fallo; revisa los logs anteriores o ejecuta en dry-run para validar la secuencia de eventos.
- **Valores fuera de rango**: si la API rechaza una razon vertical, el codigo ya limita a ±3000 fpm; ajusta velocidades o usa `vertical_rate_manual`.

## Integracion con Elastic/Logstash
- Usa Filebeat/Logstash para captar los logs de Co-ATC o su WebSocket y etiquetarlos con `is_simulated=true`.
- Crea reglas de correlacion para:
  - Altitud < 0 ft o > 45 000 ft.
  - Velocidad negativa o > 650 kt por debajo de 10 000 ft.
  - Saltos de posicion consecutivos con mas de X NM en menos de Y segundos.
- Los identificadores fijos (`VLG201`, `EZY8104`, etc.) facilitan dashboards comparables entre ejecuciones.

Con esta referencia tienes una vision completa del inyector de trafico, su arquitectura y los pasos necesarios para operarlo, extenderlo y observarlo dentro de tu laboratorio SIEM.
