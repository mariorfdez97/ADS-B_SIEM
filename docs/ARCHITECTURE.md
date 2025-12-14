# Arquitectura y estructura del repositorio

Este repo está organizado para separar claramente:
- **servicios** (lo que se ejecuta en Docker),
- **infraestructura** (configuración de ingestión/observabilidad),
- **herramientas** (scripts utilitarios),
- **scripts** (atajos para ejecutar localmente),
- **documentación** (guías y entregas).

## Estructura de carpetas (raíz)

### `docker-compose.yml`
Orquesta el laboratorio completo en un solo comando:
- `adsb-feed` (genera y sirve `aircraft.json` en `9000`)
- `co-atc` (backend+frontend en `8000`)
- `elasticsearch` (`9200`)
- `kibana` (`5601`)
- `logstash` (`9600` API interna; ingesta hacia Elasticsearch)

### `services/`
Contiene servicios auxiliares propios del repo que se ejecutan en Docker.

- `services/adsb-feed/`: contenedor Python que genera `aircraft.json` y lo sirve por HTTP.

### `co-atc-main/`
Proyecto Co‑ATC (Go + frontend) incluido en el repo. Es el “core” de visualización/API de aeronaves.

### `infra/`
Configuración de infraestructura para el laboratorio (lo que “conecta” componentes).

- `infra/logstash/pipeline/logstash.conf`: pipeline que consulta `http://co-atc:8000/api/v1/aircraft?...`, normaliza datos y los envía a Elasticsearch (`adsb-siem-*`).

### `tools/`
Utilidades pensadas para ejecutarse bajo demanda (no son “servicios” por sí mismas).

- `tools/adsb/fetch_adsbfi.py`: adaptador de datos desde `adsb.fi` a `co-atc-main/data/aircraft.json` (modo “sin Docker”).

### `scripts/`
Scripts de comodidad para ejecución local (no Docker) y tareas operativas.

- `scripts/run_coatc_adsbfi.sh`: compila Co‑ATC (si falta) + lanza servidor `aircraft.json` + ejecuta fetcher.
- `scripts/stop_coatc_adsbfi.sh`: detiene procesos lanzados por el script anterior.

### `docs/`
Documentación del proyecto.

- `docs/elastic-stack.md`: guía de cómo funciona la ingesta SIEM actual (Logstash → Elasticsearch → Kibana).
- `docs/informes/`: documentos de entrega/estado (pueden referenciar decisiones antiguas).
- `docs/contexto/`: material de contexto/teoría.
- `docs/legacy/`: documentos antiguos que se conservan por trazabilidad.

## Flujo de datos (SIEM)

1) `adsb-feed` publica `aircraft.json` → `co-atc` lo consume como fuente ADS‑B.
2) `co-atc` expone estado por API: `GET /api/v1/aircraft?...`
3) `logstash` consulta esa API, “aplana”/normaliza y etiqueta anomalías simples.
4) `logstash` envía a Elasticsearch en `adsb-siem-%{+YYYY.MM.dd}` y también escribe `logs/adsb_siem_events.log`.
5) `kibana` explora el índice `adsb-siem-*`.

