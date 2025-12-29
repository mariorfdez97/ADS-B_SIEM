# Actualizaciones SIEM y Anomalias (ADS-B)

Este documento describe las modificaciones recientes en el pipeline de anomalias, SIEM y frontend de Co-ATC. Incluye cambios en inyeccion, reglas, logs, y notificaciones en el UI.

## Objetivos

- Reducir ruido: 1 anomalia por avion por ciclo y cooldown por avion.
- Alinear los umbrales de inyeccion con las reglas de Logstash.
- Inyectar RSSI fuerte + distancia incoherente en cualquier anomalia.
- Permitir alertas SIEM en el frontend de Co-ATC y opcion de ocultar aeronaves.

## Componentes afectados

- `services/adsb-feed/feed.py`: logica de inyeccion y log de anomalias.
- `services/adsb-feed/start.sh`: defaults y log de variables.
- `docker-compose.yml`: variables de entorno y volumenes.
- `infra/logstash/pipeline/logstash.conf`: normalizacion, derivadas y reglas SIEM.
- `co-atc-main/internal/api/handlers.go`: endpoint de alertas SIEM.
- `co-atc-main/internal/api/routes.go`: ruta del endpoint SIEM.
- `co-atc-main/www/app.js`: polling de alertas SIEM, UI y ocultacion.
- `co-atc-main/www/map-manager.js`: oculta aeronaves en mapa.

## Inyeccion de anomalias (adsb-feed)

### Reglas de inyeccion

Cada anomalia se ajusta para cruzar umbrales de Logstash y evitar cambios colaterales:

- `velocidad_excesiva`: `gs > 1200`.
- `altitud_negativa`: `alt_baro < -100` con `alt_geom` cercano.
- `posible_spoofing`: `rssi > -10` y `nic < 6`, ademas de `nac_p`, `nac_v`, `sil`, `sda` bajos.
- `squawk_emergencia`: `squawk` en `7500/7600/7700`.
- `salto_posicion`: salto de `lat/lon` dentro de limites validos.

Adicionalmente, cualquier anomalia inyectada fuerza el patron de spoofing RSSI/distancia:

- `rssi` muy fuerte (aprox. `-5` a `-1`).
- distancia implicita grande (ajuste de `lat/lon` a 220-400 NM).

### Inyeccion independiente RSSI + distancia incoherente

Se puede inyectar este patron sin activar otra anomalia:

- `ANOMALY_RSSI_DISTANCE_RATE`
- `ANOMALY_RSSI_DISTANCE_MAX_PER_WRITE`

### Cooldown por avion

Evita repetir anomalias en el mismo avion en ciclos consecutivos:

- `ANOMALY_COOLDOWN_CYCLES`

### Intervalo de ciclo

El ciclo es la iteracion del bucle que descarga el feed y escribe `aircraft.json`.

- `INTERVAL` controla el tiempo entre ciclos.

## Log de anomalias (adsb_feed_anomalies.log)

Formato JSONL con un registro por avion/anomalia:

```json
{
  "ts": "2025-12-29T12:28:40Z",
  "id_icao": "495293",
  "anomaly_type": "squawk_emergencia",
  "changes": [
    {
      "field": "squawk",
      "correct_value": "0421",
      "modified_value": "7700"
    }
  ]
}
```

- `correct_value`: valor original del feed.
- `modified_value`: valor inyectado.

## Logstash (SIEM)

### Distancia

El API de Co-ATC entrega `distance` en NM. En Logstash:

- Se renombra a `distancia_receptor_nm`.
- Se calcula `distancia_receptor_km` (multiplica por 1.852).

### Reglas SIEM consolidadas en Ruby

Todas las reglas de consistencia y alertas quedan dentro del bloque Ruby principal:

- `alerta_velocidad_excesiva`
- `alerta_velocidad_baja_cota`
- `alerta_altitud_negativa`
- `posible_spoofing`
- `alerta_emergencia_aerea`
- `alerta_tasa_vertical_extrema`
- `alerta_baro_geom_desfase`
- `alerta_deriva_imposible`
- `alerta_rssi_distancia_incoherente`
- `alerta_tasa_vertical_inestable`

Regla de RSSI/distancia:

- `distancia_receptor_nm >= 200` y `intensidad_senal_rssi >= -5`

## Frontend: alertas SIEM y accion del controlador

Se incorporo un endpoint y polling desde el frontend:

- Endpoint: `GET /api/v1/siem/alerts`
  - Parametros: `limit` (default 200), `since` (RFC3339).
  - Fuente: `/logs/adsb_siem_events.log`.

En la UI:

- Las alertas SIEM aparecen en la barra superior de alerts.
- Click: descartar alerta.
- Click derecho: ocultar aeronave (no vuelve a aparecer en tabla ni mapa).

La ocultacion es local al frontend (no elimina datos del backend).

## Variables de entorno (docker-compose)

Valores actuales relevantes:

```
ANOMALY_ENABLED=true
ANOMALY_RATE=0.001
ANOMALY_MAX_PER_WRITE=1
ANOMALY_COOLDOWN_CYCLES=30
ANOMALY_RSSI_DISTANCE_RATE=0.0
ANOMALY_RSSI_DISTANCE_MAX_PER_WRITE=1
ANOMALY_TYPES=altitud_negativa,velocidad_excesiva,salto_posicion,squawk_emergencia,posible_spoofing
ANOMALY_LOG=/logs/adsb_feed_anomalies.log
INTERVAL=3
```

Notas:

- `ANOMALY_RSSI_DISTANCE_RATE` es independiente del resto.
- Si se quiere mas frecuencia, bajar `INTERVAL` o subir `ANOMALY_RATE`.

## Endpoints nuevos

- `GET /api/v1/siem/alerts`
  - Respuesta:
    ```json
    {
      "alerts": [
        {
          "hex": "4BCE15",
          "callsign": "SWR123",
          "tags": ["alerta_rssi_distancia_incoherente"],
          "timestamp": "2025-12-29T12:17:31Z"
        }
      ]
    }
    ```

## Volumenes y acceso a logs

Para que Co-ATC lea el log SIEM:

- Se monta `./logs` en el contenedor `co-atc` como solo lectura.
- Ruta por defecto: `/logs/adsb_siem_events.log`.
- Se puede cambiar con `SIEM_LOG_PATH`.

## Pasos de despliegue

Recrear servicios para aplicar cambios:

```
docker-compose up -d --force-recreate adsb-feed
docker-compose up -d --force-recreate co-atc
```

Logstash debe reiniciarse si se cambia el pipeline:

```
docker-compose up -d --force-recreate logstash
```

## Notas operativas

- Las alertas SIEM se leen por polling cada 4s desde el frontend.
- La deduplicacion de alertas en UI se hace por `hex + tags + timestamp`.
- Ocultar aeronaves no elimina datos del SIEM, solo del UI local.
