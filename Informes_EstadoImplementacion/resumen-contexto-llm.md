# Resumen rápido de contexto y estado actual

Objetivo actual:
- Alimentar Co-ATC con tráfico real vía adsb.fi (open data) y mantener el stack ELK para observabilidad. El inyector local se eliminó; solo se usa un fetcher que convierte la API de adsb.fi al formato `aircraft.json` que consume Co-ATC.

Cambios recientes relevantes:
- Eliminado el inyector Python (`simulador_bcn.py`, `simulador_bcn_pkg/`) y su documentación asociada.
- Eliminado el exportador `co_atc_exporter.py` y scripts `lanzar_lab.sh`/`detener_lab.sh`.
- Pipeline ELK sigue: `docker-compose.yml` (Elastic/Kibana/Logstash/Filebeat), `filebeat.yml` ahora solo lee `logs/co_atc.log`; puedes añadir nuevas fuentes si lo necesitas.
- Añadido `fetch_adsbfi.py`: consulta `https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}` (por defecto LEBL lat=41.2971 lon=2.0785 dist=80 NM, intervalo 1 s) y escribe `co-atc-main/data/aircraft.json` en formato tar1090/dump1090 (campos hex, flight, lat, lon, alt_baro/alt_geom, gs, heading, vertical_rate, etc.).
- Config de Co-ATC `co-atc-main/configs/config.toml`:
  - `adsb.local_source_url = http://127.0.0.1:9000/aircraft.json`
  - Estación LEBL (lat 41.2971, lon 2.0785, elev 14 ft, airport_code LEBL).
  - Bloque `[frequencies]` vacío (sin streams).
- Script de arranque `run_coatc_adsbfi.sh`:
  - Compila Co-ATC si falta.
  - Arranca servidor HTTP local en `co-atc-main/data` (puerto 9000).
  - Lanza `fetch_adsbfi.py` (intervalo 1 s).
  - Arranca Co-ATC con la config anterior.
  - Muestra logs en vivo (`logs/adsbfi_fetch.log`, `logs/co_atc.log`); Ctrl+C mata todo.
- Script de parada `stop_coatc_adsbfi.sh`: mata procesos de `fetch_adsbfi.py`, `python3 -m http.server 9000`, y `bin/co-atc -config`.

Próximos pasos sugeridos:
- Integrar la salida de la API externa en ELK si quieres, añadiendo un input en `filebeat.yml` o un pipeline específico.
- Crear reglas/visualizaciones en Kibana sobre los datos de Co-ATC (índice `adsb-data-*` si usas Logstash actual).
- Ajustar parámetros de fetch (distancia, intervalo) según la zona de interés.
