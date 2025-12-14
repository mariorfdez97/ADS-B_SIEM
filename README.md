# ADS-B_SIEM

Laboratorio de **SIEM con Elastic Stack** aplicado a **telemetría de tráfico aéreo ADS‑B**.

La idea del repo es:
1) Obtener datos de aeronaves (reales o simulados) y visualizarlos en **Co‑ATC** (backend + frontend).
2) Ingerir esos datos en **Elasticsearch** usando **Logstash** (consultando la API de Co‑ATC), para poder analizarlos en **Kibana** y marcar posibles anomalías.

---

## Qué incluye este repositorio

### 1) `co-atc-main/` (Co‑ATC)
Proyecto (Go + frontend web) que:
- expone una **web** y una **API** HTTP en el puerto `8000`
- mantiene estado de aeronaves, fases de vuelo, etc.
- puede leer datos ADS‑B desde una fuente local `aircraft.json` (formato tar1090/dump1090)

Archivos clave:
- `co-atc-main/configs/config.toml`: configuración del servidor (puertos/host) y de la fuente ADS‑B.
- `co-atc-main/www/`: frontend web.
- `co-atc-main/docs/api_spec.md`: referencia de endpoints.

Notas importantes:
- Para que **Logstash (en Docker)** pueda llamar a la API de Co‑ATC, Co‑ATC debe escuchar en todas las interfaces:
  - en `co-atc-main/configs/config.toml` → `[server]` → `host = "0.0.0.0"`
- El frontend usa JavaScript moderno. En este repo se añadió un fallback para `crypto.randomUUID` en:
  - `co-atc-main/www/app.js`

### 2) `tools/adsb/fetch_adsbfi.py` (feed ADS‑B real → `aircraft.json`)
Script Python que consulta el endpoint público de `adsb.fi` y lo convierte al formato que espera Co‑ATC:
- consulta: `https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}`
- salida: `co-atc-main/data/aircraft.json`

Sirve como “adaptador” entre una API externa y el formato tar1090/dump1090.

Parámetros importantes (ver `--help`):
- `--lat`, `--lon`, `--dist`: centro y radio (NM)
- `--interval`: cada cuánto se actualiza el fichero (respeta rate limits)
- `--output`: ruta del `aircraft.json`

### 3) `run_coatc_adsbfi.sh` / `stop_coatc_adsbfi.sh`
Scripts de conveniencia para levantar Co‑ATC con datos reales:
- `scripts/run_coatc_adsbfi.sh` hace:
  1) compilar Co‑ATC si falta el binario
  2) levantar un servidor estático en `9000` que sirve `co-atc-main/data/aircraft.json`
  3) ejecutar `tools/adsb/fetch_adsbfi.py` para rellenar el `aircraft.json`
  4) arrancar Co‑ATC con `co-atc-main/configs/config.toml`
  5) mostrar logs en vivo
- `scripts/stop_coatc_adsbfi.sh` mata los procesos anteriores por patrón

### 4) Elastic Stack (SIEM) en Docker
El stack está en la raíz del repo:
- `docker-compose.yml`: levanta `elasticsearch`, `kibana` y `logstash`.
- `infra/logstash/pipeline/logstash.conf`: pipeline que **consulta la API** de Co‑ATC y envía eventos a Elasticsearch.

Puntos clave del pipeline (versión actual):
- input: `http_poller` a `http://co-atc:8000/api/v1/aircraft?status=active&lastSeenMinutes=5` (red interna de Docker Compose)
- `split` por aeronave
- normalización/renombrado a campos “humanos” en español (ej. `id_icao`, `callsign_vuelo`, `latitud`, `altitud_pies`, etc.)
- crea `location` para uso geográfico en Kibana
- **reglas SIEM** básicas (tags) para anomalías típicas (velocidad excesiva, altitud negativa, emergencias por squawk, etc.)
- deduplicación por estado (evita reinsertar el mismo estado si no cambian campos relevantes)
- output: Elasticsearch en el índice diario `adsb-siem-YYYY.MM.dd`

Documentación específica del stack:
- `docs/elastic-stack.md`

### 5) `logs/` (artefactos de ejecución)
Se generan logs y artefactos runtime (ignorados por git):
- `logs/co_atc.log`: logs del backend Co‑ATC
- `logs/feed_http.log`: servidor estático del `aircraft.json`
- `logs/adsbfi_fetch.log`: logs del fetcher
- `logs/adsb_siem_events.log`: log estructurado (JSON) con lo que Logstash envía al índice `adsb-siem-*`

---

## Requisitos

### Para Co‑ATC + adsb.fi (modo “sin Docker”)
- Go (para compilar Co‑ATC)
- Python 3
- Dependencia Python: `requests`

### Para el SIEM (Elastic Stack)
- Docker + docker-compose (v1 `docker-compose` funciona; v2 sería `docker compose`)
- Acceso a la API de Co‑ATC desde los contenedores (ver “Bind a 0.0.0.0”)

---

## Cómo lanzar (rápido)

### Opción 0 (recomendada): levantar TODO con Docker
Esto levanta en una sola orden:
- `adsb-feed` (adsb.fi → `aircraft.json` + servidor HTTP en `9000`)
- `co-atc` (API+frontend en `8000`)
- `elasticsearch` (9200), `kibana` (5601), `logstash` (polling API → ES)

```bash
sudo docker-compose up -d --build
```

URLs:
- Co‑ATC: `http://localhost:8000`
- API: `http://localhost:8000/api/v1/aircraft?status=active&lastSeenMinutes=5`
- Elasticsearch: `http://localhost:9200`
- Kibana: `http://localhost:5601`

Índices SIEM:
- `adsb-siem-*`

Parar:
```bash
sudo docker-compose down
```

### A) Arrancar Co‑ATC con tráfico real (adsb.fi)
1) Instala dependencias Python:
```bash
python3 -m pip install -r requirements.txt  # si existe
# o mínimo:
python3 -m pip install requests
```

2) Arranca:
```bash
chmod +x scripts/run_coatc_adsbfi.sh
./scripts/run_coatc_adsbfi.sh
```

3) Abre:
- Frontend: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api/v1/aircraft?status=active&lastSeenMinutes=5`

4) Parar:
```bash
./scripts/stop_coatc_adsbfi.sh
```

### B) Arrancar el SIEM (Elastic + Kibana + Logstash)
1) Levantar stack:
```bash
sudo docker-compose up -d
```

2) Verificar:
```bash
sudo docker-compose ps
curl -s http://localhost:9200
```

3) Kibana:
- `http://localhost:5601`
- Crea un *Data View* para `adsb-siem-*` y usa `@timestamp` como campo de tiempo.

4) Comprobar que está entrando dato:
```bash
curl -s 'http://localhost:9200/adsb-siem-*/_count'
```

Log estructurado (mismo evento que indexa ES):
```bash
tail -f logs/adsb_siem_events.log
```

---

## Cambios típicos (configuración)

### 1) Cambiar zona (centro/radio) del feed adsb.fi
Edita el comando en `run_coatc_adsbfi.sh` o ejecútalo a mano:
```bash
python3 tools/adsb/fetch_adsbfi.py --lat 41.2971 --lon 2.0785 --dist 80 --interval 1
```

### 2) Permitir que Logstash (Docker) llame a Co‑ATC
En `co-atc-main/configs/config.toml`:
- `[server]` → `host = "0.0.0.0"`

### 3) Ajustar la ingesta SIEM
En `infra/logstash/pipeline/logstash.conf`:
- cambia el `schedule` (frecuencia)
- cambia la URL (`lastSeenMinutes`, filtros)
- añade/quita reglas SIEM (tags)
- ajusta la deduplicación (firma)

Después:
```bash
sudo docker-compose restart logstash
```

---

## Gestión de datos en Elasticsearch

### Ver índices
```bash
curl -s 'http://localhost:9200/_cat/indices?v'
```

### Borrar índices (cuando `*` está bloqueado)
Por seguridad, ES puede bloquear borrados con wildcard. Lista y borra por nombre:
```bash
curl -s 'http://localhost:9200/_cat/indices/adsb-siem-*?h=index'
curl -X DELETE 'http://localhost:9200/adsb-siem-2025.12.05'
```

### Reset total (borra volumen)
```bash
sudo docker-compose down
sudo docker volume rm ads-b_siem_esdata
sudo docker-compose up -d
```

---

## Troubleshooting (errores comunes)

### “Connection refused” desde Logstash a la API de Co‑ATC
Dentro de Docker, `localhost` no es el host.
- Logstash llama a Co‑ATC por DNS interno: `http://co-atc:8000/...` (ya está en el pipeline).
- asegúrate de que Co‑ATC está levantado y expone el puerto `8000`.

### Kibana “campos vacíos”
Normalmente es *Data View* desactualizado o rango de tiempo incorrecto:
- refresca “field list”
- usa `@timestamp`
- amplía el “time picker” (últimos 15 min / Today)

### Frontend de Co‑ATC se rompe con `crypto.randomUUID`
Se añadió un fallback en `co-atc-main/www/app.js`. Si sigues viendo el error:
- recarga dura (Ctrl+Shift+R)
- limpia cache del navegador

---

## Documentos y contexto del proyecto (asignatura)
- `docs/informes/`: guías y resúmenes del estado.
- `docs/contexto/`: contexto/temario de la parte teórica.
- `docs/elastic-stack.md`: guía del stack SIEM en este repo.

---

## Licencias / atribuciones
- Co‑ATC dentro de `co-atc-main/` mantiene su propia documentación y contexto (ver `co-atc-main/README.md`).
