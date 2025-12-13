# Documentación del Stack Elastic (ingesta vía API de Co-ATC)

## Objetivo
Ingerir en Elasticsearch los datos de aeronaves activos expuestos por la API de Co-ATC, evitando duplicados, generando también un log local con los eventos que se envían, y disponer de Kibana para visualización.

## Componentes y versiones
- **Elasticsearch 8.14.1**: almacén de datos (`adsb-api-*`).
- **Kibana 8.14.1**: UI para explorar los índices.
- **Logstash 8.14.1**: orquestador de ingesta desde la API → ES y log local.
- **Sin Filebeat**: la obtención de datos es directa por HTTP Poller desde Logstash.

## Estructura de ficheros
- `docker-compose.yml`: orquesta el laboratorio completo (Co‑ATC + feed + Elastic Stack).
- `logstash/pipeline/logstash.conf`: pipeline de ingesta (HTTP poller, filtros, outputs).
- `logs/adsb_siem_events.log`: log generado por Logstash con los eventos ya procesados (lo mismo que se envía a Elasticsearch).

## Configuración principal
### docker-compose.yml
- **adsb-feed**
  - Descarga datos de `adsb.fi`, genera `aircraft.json` y lo sirve por HTTP en `9000`.
  - Se usa como fuente `local_source_url` para Co‑ATC.
- **co-atc**
  - Backend + frontend en `8000`.
  - Usa `co-atc-main/configs/config.docker.toml`.
- **elasticsearch**
  - `xpack.security.enabled=false` para uso sin credenciales.
  - Datos persistentes en volumen `esdata`.
  - Puerto expuesto: `9200`.
  - Healthcheck simple a `/_cluster/health`.
- **kibana**
  - Apunta a `http://elasticsearch:9200`.
  - Puerto expuesto: `5601`.
  - Depende de que Elasticsearch esté saludable.
- **logstash**
  - Monta `./logstash/pipeline` como solo lectura.
  - Monta `./logs` para escribir `adsb_api_parsed.log`.
  - `extra_hosts: host.docker.internal:host-gateway` para que el contenedor resuelva el host (API de Co-ATC en la máquina).
  - `command: ["-w", "1"]` limita a un worker para mantener consistente el estado de deduplicación.
  - Puertos: `5044` (reservado Beats si se necesitara) y `9600` (API interna de Logstash).
  - Healthcheck a `http://localhost:9600/_node/pipelines`.

### logstash/pipeline/logstash.conf
**Input: http_poller**
- GET `http://co-atc:8000/api/v1/aircraft?status=active&lastSeenMinutes=5`.
- Intervalo: 5 s. Timeout: 10 s. Cabecera `Accept: application/json`.
- Espera la estructura: objeto con campo `aircraft` que contiene un array de aeronaves.

**Filter**
1. `split` sobre `[aircraft]`: genera un evento por aeronave.
2. `mutate rename`: extrae y renombra campos clave:
   - `hex`, `flight`, `status`, `on_ground`, `distance`.
   - Del bloque `adsb`: `lat`, `lon`, `alt_baro`, `alt_geom`, `gs`, `heading`, `vertical_rate`.
3. `mutate convert` a `float` donde aplica.
4. `drop` si no hay `hex`.
5. **Deduplicación** (ruby): guarda un mapa en memoria por `hex`; si la firma `(lat, lon, alt_baro, alt_geom, gs, heading, vertical_rate)` no cambia, se cancela el evento. Requiere `-w 1` para coherencia.
6. Limpieza de campos intermedios (`aircraft`, `adsb`, etc.).

**Output**
- Elasticsearch: índice `adsb-siem-%{+YYYY.MM.dd}`.
- Fichero: `/logs/adsb_siem_events.log` (json_lines, `create_if_deleted`).

## Ejecución desde cero
1) Parar y limpiar (incluye huérfanos):
```bash
sudo docker-compose down --remove-orphans
```
2) Levantar:
```bash
sudo docker-compose up -d
```
3) Ver estado:
```bash
sudo docker-compose ps
```
4) Comprobar ingesta en ES:
```bash
curl -s http://localhost:9200/adsb-siem-*/_count
```
5) Ver log procesado:
```bash
tail -f logs/adsb_siem_events.log
```
6) Kibana: abrir http://localhost:5601 y crear un data view `adsb-api-*`.

## Campos mínimos disponibles en ES/log
- Identificación: `hex`, `flight`, `status`, `on_ground`, `distance`.
- Posición/estado: `lat`, `lon`, `alt_baro`, `alt_geom`, `gs`, `heading`, `vertical_rate`.
- `@timestamp`: momento de ingesta (añadido por Logstash).
- `timestamp` (de la API) si viene en la respuesta; no se modifica.

## Consideraciones de duplicados
- El deduplicador evita insertar el mismo estado consecutivo por `hex` si no cambian posición, alturas, velocidad, rumbo ni razón vertical.
- Si la API entrega la misma aeronave con cualquier variación en esos campos, se reenviará (es un nuevo estado).

## Ajustes rápidos
- Cambiar frecuencia de sondeo: `interval` en `http_poller` (segundos).
- Cambiar ventana de la API: modificar `lastSeenMinutes` en la URL.
- Añadir campos: extender el bloque `mutate rename` y los `convert`.
- Desactivar deduplicación: comentar/eliminar el bloque `ruby` y, opcionalmente, subir workers si hace falta más throughput.

## Resolución de problemas
- **Kibana no arranca**: espera a que Elasticsearch esté healthy; revisa `docker-compose ps`.
- **Logstash unhealthy**: ver `sudo docker-compose logs logstash`; revisa la URL o la respuesta de la API.
- **Sin datos en ES**: revisa el log `adsb_api_parsed.log` y `_count`; confirma que la API responde y que la URL usa `host.docker.internal`.
- **Permisos de logs**: `logs` debe existir y ser escribible por el contenedor (montaje en `./logs`).

## Flujo resumen
API Co-ATC (`/api/v1/aircraft?...`) → Logstash HTTP Poller → split y normalización → reglas SIEM + deduplicación → salida a Elasticsearch (`adsb-siem-*`) y a `logs/adsb_siem_events.log`.
