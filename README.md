# ADS-B_SIEM

Laboratorio SIEM con Elastic Stack sobre trafico ADS-B real.

## Requisitos minimos

- Docker y Docker Compose.
- 4 GB RAM.
- 10 GB de disco.
- Internet para el feed ADS-B.

## Ejecutar

```bash
docker-compose up -d --build
```

Parar:

```bash
docker-compose down
```

## URLs

- Co-ATC: `http://localhost:8000`
- Feed: `http://localhost:9000/aircraft.json`
- Elasticsearch: `http://localhost:9200`
- Kibana: `http://localhost:5601`

## Kibana

Crear Data View:
- `adsb-siem-*`
- Time field: `@timestamp`

## Logs

- `logs/adsb_siem_events.log`
- `logs/adsb_feed_anomalies.log`

```bash
tail -f logs/adsb_siem_events.log
```

## Volumenes y limpieza

Volumenes Docker usados:
- `esdata` (datos Elasticsearch)
- `coatc_data` (datos Co-ATC)
- `aircraft_data` (aircraft.json)

Borrar volumenes (resetea datos):

```bash
docker-compose down -v
```
