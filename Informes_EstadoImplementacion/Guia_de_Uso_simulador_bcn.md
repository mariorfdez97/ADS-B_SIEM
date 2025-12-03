# Guia de uso: simulador_bcn.py

Este archivo describe la logica y el modo de ejecucion de `simulador_bcn.py`, el orquestador que automatiza el escenario de trafico simulado para Barcelona-El Prat (LEBL) creado en `trafico-simulado.md` y detallado en `diseno-red-vuelos-bcn.md`.

## Objetivo

- Crear y controlar aeronaves virtuales mediante la API de Co-ATC.
- Reproducir salidas (SID), llegadas (STAR/ILS) y esperas con perfiles realistas.
- Inyectar anomalias deliberadas (altitud negativa, salto de posicion, velocidad negativa) para validar reglas en Elastic Stack.

## Dependencias

- Python 3.11 o superior.
- Biblioteca `requests` (`pip install requests`).
- Instancia de Co-ATC ejecutandose con la API accesible (por defecto `http://127.0.0.1:8000/api/v1`).

## Parametros principales

| Opcion | Descripcion |
|--------|-------------|
| `--url-base` | URL base de la API Co-ATC. |
| `--fecha` | Fecha del escenario (CET). Por defecto la fecha actual. |
| `--factor-tiempo` | Aceleracion temporal (1.0 tiempo real, 2.0 el doble de velocidad). |
| `--modo-prueba` | Activar modo dry-run (no se envian peticiones). |
| `--incluir-anomalias` | Añade los eventos anómalos opcionales (desactivado por defecto). |
| `--log-nivel` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

Ejemplo:

```bash
python3 simulador_bcn.py --url-base http://127.0.0.1:8000/api/v1 --fecha 2024-11-15 --factor-tiempo 2.0 --log-nivel DEBUG
```

## Arquitectura interna

1. **Puntos de navegacion**: tabla con coordenadas de umbrales y fixes (`construir_puntos`).
2. **Vuelos**: cada vuelo (`VueloSimulado`) define hora de creacion, hora de inicio, lista de tramos (`TramoVuelo`) y velocidad/altitud objetivo.
3. **Eventos**: el metodo `generar_eventos` de cada vuelo crea eventos cronologicos (`EventoProgramado`) que invocan los endpoints REST:
   - `POST /simulation/aircraft`
   - `PUT /simulation/aircraft/{hex}/controls`
   - `DELETE /simulation/aircraft/{hex}`
4. **Anomalias**: `construir_anomalias` agrega eventos extra para datos imposibles:
   - Altitud negativa en `VLG201`.
   - Salto brusco de posicion para `VLG201`.
   - Velocidad negativa en rodaje para `EZY8104`.
5. **Scheduler**: `ejecutar_eventos` recorre los eventos ordenados y sincroniza el tiempo usando el factor indicado.

## Escenario cubierto

- **Ventana temporal**: 06:00–06:06 CET (eventos más densos para acelerar la generación).
- **Salidas**:
  - `VLG201` (A320) RWY07R → SID `NELSO-TARRA-TGA-LORET`.
  - `IBE432` (A320) RWY07L → SID `MASNU-BAMES-KENAS-GIRON`.
  - `VY6502` (A320) RWY07R → SID costera `NELSO-SITGE-TGA-LORET`.
  - `RYR221` (B738) RWY07L → Salida norte `MASNU-BAMES-KENAS-GIRON`.
- **Llegadas**:
  - `DLH1421` (A321) vía `LORET-SITGE-SARGO-UBAGA` hasta ILS 07L.
  - `EZY8104` (A320) desde `KENAS` con ILS 07L.
  - `RYR611` (B738) vía `TGA` con espera en `SLL`.
  - `AFR1738` (A320) aproximación corta `MASNU-SLL-DOBRO` a 07R.
- **Anomalias opcionales**:
  - Se activan únicamente con `--incluir-anomalias`.
  - Vuelos generados: `GHOST01` (supersónico), `ANMALT1` (altitud negativa/ascensos extremos), `ANMSPD1` (velocidades > 650 kt a baja cota) y `ANMJMP1` (saltos laterales y verticales abruptos), además de las acciones sobre `VLG201`/`EZY8104` en la función `construir_anomalias`.

## Buenas practicas y personalizacion

- Ajusta `--factor-tiempo` para ensayar escenarios rapidos sin perder detalle.
- En modo `--modo-prueba` puedes validar la planificacion sin levantar Co-ATC.
- Amplia `construir_vuelos` y `construir_anomalias` para nuevos casos (p. ej. duplicados ICAO, DoS de mensajes) manteniendo la estructura de `TramoVuelo`.
- Revisa los logs en `INFO` para verificar que cada tramo se ejecuta y que las peticiones reciben `200 OK`.

## Integracion con Elastic Stack

1. Asegura que Filebeat/Logstash recojan `GET /api/v1/aircraft` o el WebSocket para indexar los datos simulados (`is_simulated = true`).
2. Marca reglas de correlacion con los `anomaly_flags` que emitas desde tu pipeline de ingestion.
3. Corrobora en dashboards que los perfiles verticales, rumbos y tiempos coinciden con las tablas de `diseno-red-vuelos-bcn.md`.

Con este script puedes automatizar ensayos completos de SIEM sobre trafico ADS-B simulado sin hardware real, manteniendo coherencia operacional y generando datos etiquetados para tus informes.
