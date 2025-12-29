# Cambios en Co-ATC (SIEM + Frontend)

Este documento describe los cambios realizados en el servicio Co-ATC para integrar alertas SIEM en el frontend y permitir al controlador ocultar aeronaves sospechosas.

## Objetivos

- Exponer un endpoint para consultar alertas SIEM desde el log de Logstash.
- Notificar al controlador en el UI cuando se detectan alertas.
- Permitir ocultar aeronaves desde el frontend sin afectar el backend.

## Cambios en el backend (API)

### Ruta nueva

Se agrega un endpoint para leer eventos SIEM recientes desde el log local:

- `GET /api/v1/siem/alerts`

Parametros:

- `limit` (int, default 200, max 1000)
- `since` (RFC3339)

Respuesta:

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

Fuente de datos:

- `/logs/adsb_siem_events.log` (por defecto)
- se puede sobrescribir con `SIEM_LOG_PATH`.

### Archivos modificados

- `co-atc-main/internal/api/routes.go`
  - Se agrega la ruta `GET /api/v1/siem/alerts`.
- `co-atc-main/internal/api/handlers.go`
  - Se implementa `GetSiemAlerts`.
  - Lectura eficiente de las ultimas lineas del log (hasta 1MB).
  - Filtrado de tags SIEM (`alerta_*` y `posible_spoofing`).
  - Soporte para `limit` y `since`.

### Volumen de logs

Para que el contenedor lea el log:

- Se monta `./logs` como `:ro` en `docker-compose.yml`.

## Cambios en el frontend (UI)

### Polling de SIEM

Se incorpora polling desde el frontend:

- Intervalo: 4s.
- Endpoint: `/api/v1/siem/alerts`.
- Se usa `since` para pedir solo eventos nuevos.

### Notificaciones al controlador

Las alertas SIEM se agregan a la barra superior:

- Estilo rojo y texto `SIEM <tags>: <callsign/hex>`.
- Click izquierdo: descarta la alerta.
- Click derecho: solicita ocultar aeronave.

### Ocultar aeronaves

Accion del controlador:

- Añade el `hex` a `hiddenAircraft`.
- Elimina el avion de mapa, tabla y animaciones.
- Previene que vuelva a aparecer aunque siga llegando del backend.

Esto es solo local al navegador, no afecta el backend ni el SIEM.

### Archivos modificados

- `co-atc-main/www/app.js`
  - Polling SIEM.
  - Deduplicacion local de alertas.
  - Nueva accion `hideAircraft`.
  - Filtro adicional en `aircraftPassesFilters` y en procesamiento de datos.
- `co-atc-main/www/map-manager.js`
  - Oculta marcadores/labels si el avion esta en `hiddenAircraft`.

## Funciones nuevas en frontend

### `startSiemPolling()`

Inicia el intervalo y solicita el primer lote de alertas.

### `fetchSiemAlerts()`

Consulta el endpoint y actualiza `siemLastTimestamp`.

### `addSiemAlert(alert)`

Inserta un elemento en la barra de alertas y añade handlers.

### `hideAircraft(hex)`

Oculta una aeronave en UI y elimina sus marcadores.

## Resumen de archivos

Backend:

- `co-atc-main/internal/api/routes.go`
- `co-atc-main/internal/api/handlers.go`

Frontend:

- `co-atc-main/www/app.js`
- `co-atc-main/www/map-manager.js`

Infra:

- `docker-compose.yml` (volumen `./logs:/logs:ro`)

## Limitaciones actuales

- La ocultacion es local; al recargar el navegador se pierde.
- No hay persistencia en servidor ni bloqueo real de datos.
- El polling es cada 4s, no es push por WebSocket.

## Posibles mejoras

- Persistir lista de bloqueados en backend.
- Enviar alertas SIEM por WebSocket.
- Mostrar detalle completo del evento SIEM en un modal.
