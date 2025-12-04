# Ingesta y filtrado mínimo de ADS-B y logs Co-ATC en Elastic Stack

## Resumen
- La API de Co-ATC expone aeronaves completas en `/api/v1/aircraft` (y detalle por hex en `/api/v1/aircraft/{hex}`), con filtros para reducir volumen (status, lastSeenMinutes, altitudes, distancia desde refLat/refLon o refHex/refFlight, ventanas de despegue/aterrizaje, callsign). No existe un parámetro para devolver menos campos, así que la reducción se hace vía filtros o en la pipeline.
- Logstash filtra y deja solo los metadatos esenciales de ADS-B (`hex, flight, lat, lon, alt_* , gs, heading, vertical_rate`) y extrae los campos clave de `co_atc.log` (timestamp, nivel, componente, evento, payload JSON) generando además un log limpio `logs/co_atc_parsed.log`.
- Filebeat recolecta `logs/co_atc.log`. El input httpjson opcional puede consultar `/api/v1/aircraft` con filtros para traer solo tráfico activo/reciente.

## Flujo actual
1) **Filebeat** (`filebeat/filebeat.yml`)
   - Input log: `/logs/co_atc.log` con `fields.source_type: co-atc-log`.
   - Input httpjson opcional (comentado) para `http://host.docker.internal:8000/api/v1/aircraft?...` si quieres ingestar la API filtrada.
   - Output: Logstash (`logstash:5044`).

2) **Logstash** (`logstash/pipeline/logstash.conf`)
   - Input: beats 5044.
   - Filtros:
     - `source_type=co-atc-log`: grok con tabs y códigos ANSI, limpieza de color, json del payload final, deja `@timestamp, level, component, event, payload, source_type, host`. Genera también un fichero limpio `logs/co_atc_parsed.log` (codec json_lines).
     - `source_type=adsb`: json → convierte a float → `prune` para guardar solo `hex, flight, lat, lon, alt_baro, alt_geom, gs, heading, vertical_rate, source_type, @timestamp`.
   - Outputs:
     - `co-atc-logs-*` (ES) + fichero `logs/co_atc_parsed.log`
     - `adsb-data-*` (ES)

3) **Elasticsearch/Kibana**: índices `co-atc-logs-*` y `adsb-data-*` (crear index patterns en Kibana).

## Opciones de filtrado en la API /api/v1/aircraft (Co-ATC)
- `status`: active/departed/arrived/unknown
- `lastSeenMinutes`
- `minAltitude`, `maxAltitude`
- `distanceNM` + ref (`refLat/refLon` o `refHex` o `refFlight`)
- Ventanas: `tookOffAfter/Before`, `landedAfter/Before`
- `callsign` (substring)

Ejemplo de URL para httpjson:  
`http://host.docker.internal:8000/api/v1/aircraft?status=active&lastSeenMinutes=5`

## Notas
- Si corres en Linux y usas httpjson, añade en `docker-compose.yml` para filebeat:
  ```
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```
- Los ficheros runtime (`logs/`, `esdata/`, DBs SQLite) están ignorados en `.gitignore`.
- Si quieres parsear más campos de `co_atc.log`, ajusta el grok o el payload JSON según evolucione el formato.
