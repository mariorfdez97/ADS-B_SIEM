# Diseño detallado de la red de vuelos simulados (LEBL, 06:00 LT)

Este documento amplía el punto 3 de `trafico-simulado.md` con un procedimiento paso a paso para Barcelona-El Prat (LEBL). Se define un bloque operativo entre las 06:00 y las 06:20 hora local (CET, UTC+1) con salidas, llegadas, esperas y casos anómalos, incluyendo todos los cálculos necesarios (rumbo, distancia, perfiles verticales y espaciado) para trasladarlo a tu orquestador de tráfico simulado.

## 1. Preparativos y suposiciones
- **Zona horaria**: CET (UTC+1). Ajusta los sellos de tiempo del simulador a UTC sumando 1 hora.
- **Modelo**: A320/B738 para vuelos regulares; parámetros (velocidades, razones de ascenso/descenso) compatibles con ese tipo de avión.
- **Servicios**: el backend de Co-ATC se alimenta de la simulación (sin receptor ADS-B real) conforme a `trafico-simulado.md`.
- **Coordenadas**: se fijan referencias para runways y waypoints. Todas las distancias/bearings se han obtenido con las fórmulas haversine y de rumbo verdadero (`co-atc-main/internal/adsb/atc_utils.go`).

## 2. Datos base del aeropuerto

| Elemento | Latitud | Longitud | Altitud (ft) | Rumbo operativo |
|----------|---------|----------|--------------|-----------------|
| LEBL TWR (referencia) | 41.2971 | 2.0785 | 14 | – |
| RWY 07R umbral | 41.2863 | 2.0886 | 14 | 085° / 265° |
| RWY 07L umbral | 41.2916 | 2.0743 | 14 | 085° / 265° |
| RWY 02 umbral  | 41.3036 | 2.0713 | 14 | 354° / 174° |
| VOR/DME TGA (Tarragona) | 41.1433 | 1.1733 | 382 | – |
| VOR/DME SLL (Sabadell)  | 41.5169 | 2.1050 | 465 | – |

> Cómo obtener/validar: usa las bases `assets/airports.json` y fuentes aeronáuticas abiertas. Los rumbos se verifican con `calculateBearing` de `atc_utils.go`.

## 3. Waypoints y fixes definidos

| Identificador | Lat | Lon | Uso |
|---------------|-----|-----|-----|
| `NELSO` | 41.2300 | 2.2000 | Salida SE, inicial SID 07R hacia litoral |
| `TARRA` | 41.0900 | 1.5500 | Intermedio hacia TGA (corredor suroeste) |
| `LORET` | 41.4000 | 0.9000 | Fix de transferencia a FIR Barcelona oeste |
| `MASNU` | 41.4800 | 2.3000 | Punto sobre costa del Maresme (transición norte) |
| `BAMES` | 41.7350 | 2.3900 | En ruta hacia GIRONA/VFR norte |
| `KENAS` | 41.8864 | 2.5800 | Entrada STAR norte (sector Girona) |
| `GIRON` | 41.9000 | 2.7600 | Transferencia al FIR francés |
| `SITGE` | 41.2300 | 1.8000 | STAR oeste (sector SITGES) |
| `SARGO` | 41.2500 | 2.1000 | Intersección STAR→final oeste |
| `UBAGA` | 41.3600 | 2.1400 | IAF para ILS 07L |
| `DOBRO` | 41.3200 | 2.0000 | FAF aproximación ILS 07L |
| `HOLD_SLL_E1` | 41.5269 | 2.1350 | Pierna este del circuito de espera SLL |
| `HOLD_SLL_W1` | 41.5069 | 2.0750 | Pierna oeste del circuito de espera SLL |
| `GHOST` | 41.3500 | 2.5000 | Punto artificial para inyectar datos erróneos |

Todos los puntos se usan exclusivamente para la simulación; puedes renombrarlos si dispones de datos reales del AIP España.

## 4. Herramientas de cálculo recomendadas
1. **Scripts auxiliares**: usa Python 3 (disponible por defecto) con funciones haversine y bearing. Ejemplo:
   ```python
   import math

   def bearing(p1, p2):
       lat1, lon1 = map(math.radians, p1)
       lat2, lon2 = map(math.radians, p2)
       y = math.sin(lon2 - lon1) * math.cos(lat2)
       x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
       return (math.degrees(math.atan2(y, x)) + 360) % 360

   def distance_nm(p1, p2):
       R = 6371000
       lat1, lon1 = map(math.radians, p1)
       lat2, lon2 = map(math.radians, p2)
       dlat = lat2 - lat1
       dlon = lon2 - lon1
       a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
       return (2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))) / 1852
   ```
2. **Validación**: contrasta los resultados con la UI del simulador (`leaflet.js`) para asegurarte de que los trazados son coherentes en el mapa.

## 5. Programación temporal (06:00–06:20 CET)

| Hora CET | Evento | Vuelo | Tipo | Ruta/Observaciones |
|----------|--------|-------|------|--------------------|
| 05:58 | Spawn | EZY8104 | A320 | En STAR norte a FL120 en `KENAS` |
| 06:00 | Despegue | VLG201 | A320 | SID `NELSO–TARRA–TGA–LORET` (salida oeste) |
| 06:04 | Taxi | IBE432 | A320 | Rodaje a RWY07L, salida norte |
| 06:06 | Despegue | IBE432 | A320 | SID `MASNU–BAMES–KENAS–GIRON` |
| 06:08 | Inserción anomalía | GHOST01 | — | Avión ficticio en `GHOST` (velocidad absurda) |
| 06:10 | Aproximación | EZY8104 | A320 | STAR `KENAS–BAMES–MASNU–SLL`, ILS 07L |
| 06:12 | Llegada | RYR611 | B738 | STAR `TGA–SITGE–SARGO–UBAGA`, con hold SLL |
| 06:14 | Hold | RYR611 | B738 | 1 circuito completo a 5000 ft |
| 06:16 | Final | RYR611 | B738 | Salida del hold hacia ILS 07L |
| 06:18 | Datos erróneos 2 | VLG201 | A320 | Inyección de altitud negativa durante crucero (test SIEM) |
| 06:19 | Estabilización | EZY8104 | A320 | Rodaje liberando pista; reinicio timeline |

El desfase de minutos garantiza el espaciado mínimo (≥ 3 minutos / 6 NM) entre sucesos conflictivos.

## 6. Salidas: definición de SIDs simuladas

### 6.1 VLG201 – SID “TGA7W” (Runway 07R)
1. **Creación** (`05:59:30`): `POST /simulation/aircraft` con estado inicial (lat/lon RWY07R, alt 0 ft, heading 085°, speed 0 kt).
2. **Takeoff roll (06:00:00)**: aumentar `speed` gradualmente hasta 160 kt, `vertical_rate` 1500 ft/min.
3. **Secuencia de waypoints y cálculos**:

| Leg | De → A | Dist (NM) | Rumbo | V objetivo (kt) | Alt objetivo (ft) | Tiempo (min) | V/S (ft/min) |
|-----|--------|-----------|-------|-----------------|-------------------|--------------|--------------|
| 1 | RWY07R → NELSO | 6.06 | 124° | 200 | 3000 | 1.82 | +1650 |
| 2 | NELSO → TARRA | 30.56 | 254° | 250 | 8000 | 7.33 | +680 |
| 3 | TARRA → TGA | 17.34 | 281° | 280 | 12000 | 3.72 | +1080 |
| 4 | TGA → LORET | 19.74 | 321° | 320 | 18000 | 3.70 | +1620 |

4. **Cruce de TGA**: mantener rumbo 321° hasta salir del área de interés (LORET). A partir de ese punto el orquestador puede handoff y dejar al avión seguir en crucero recto.
5. **Monitorización**: marca `is_simulated=true` y añade metadatos (`phase: "CLIMB"`, `sid: "TGA7W"`).

### 6.2 IBE432 – SID “KENAS5N” (Runway 07L)
1. **Creación** (`06:04:30`): posición RWY07L, heading 085°.
2. **Despegue (06:06:00)**: acelerar hasta 170 kt, ascenso inicial 1200 ft/min.
3. **Waypoints**:

| Leg | De → A | Dist (NM) | Rumbo | V (kt) | Alt (ft) | Tiempo (min) | V/S (ft/min) |
|-----|--------|-----------|-------|--------|----------|--------------|--------------|
| 1 | RWY07L → MASNU | 15.21 | 042° | 190 | 4000 | 4.80 | +830 |
| 2 | MASNU → BAMES | 15.83 | 015° | 240 | 9000 | 3.96 | +1260 |
| 3 | BAMES → KENAS | 12.45 | 043° | 280 | 15000 | 2.67 | +2250 |
| 4 | KENAS → GIRON | 8.09 | 084° | 300 | 20000 | 1.62 | +3090 |

4. **Salida del TMA**: tras `GIRON`, fijar rumbo 070° y velocidad 320 kt durante 5 NM antes de ceder control.
5. **Separación vs VLG201**: el orquestador debe comprobar distancia lateral ≥ 10 NM y vertical ≥ 1000 ft antes de autorizar el viraje sobre `MASNU`.

## 7. Llegadas: STAR e ILS 07L

### 7.1 EZY8104 – STAR “KENAS1M” + ILS 07L
1. **Spawn (05:58)**: en `KENAS`, FL120, rumbo 223°, velocidad 250 kt.
2. **Descenso escalonado** según tabla:

| Leg | De → A | Dist (NM) | Rumbo | V (kt) | Alt inicio→fin (ft) | Tiempo (min) | V/S (ft/min) |
|-----|--------|-----------|-------|--------|----------------------|--------------|--------------|
| 1 | KENAS → BAMES | 12.45 | 223° | 250 | 12000 → 10000 | 2.99 | −670 |
| 2 | BAMES → MASNU | 15.83 | 195° | 230 | 10000 → 7000 | 4.13 | −730 |
| 3 | MASNU → SLL | 9.04 | 284° | 210 | 7000 → 4000 | 2.58 | −1160 |
| 4 | SLL → DOBRO | 12.73 | 202° | 180 | 4000 → 2500 | 4.24 | −350 |
| 5 | DOBRO → RWY07L | 3.76 | 117° | 150 → 140 (final) | 2500 → 50 | 1.50 | −1630 |

3. **Interceptación ILS**:
   - En `UBAGA` (fijar a 5000 ft, 200 kt) gira a rumbo 078° para interceptar el localizador.
   - Al cruzar `DOBRO` desciende 3° (≈ 700 ft/min a 140 kt) y extiende tren de aterrizaje.
4. **Rodaje**: tras aterrizaje (06:18) solicita desactivación (`DELETE /simulation/aircraft`) o rola a `stand 204` con `speed` 20 kt, `vertical_rate` 0.

### 7.2 RYR611 – STAR “TGA3W” + espera en SLL
1. **Spawn (06:10)**: en `TGA`, FL200, velocidad 280 kt.
2. **Perfil descentente**:

| Leg | De → A | Dist (NM) | Rumbo | V (kt) | Alt inicio→fin (ft) | Tiempo (min) | V/S (ft/min) |
|-----|--------|-----------|-------|--------|----------------------|--------------|--------------|
| 1 | TGA → SITGE | 28.79 | 079° | 280 | 20000 → 15000 | 6.17 | −810 |
| 2 | SITGE → SARGO | 13.60 | 085° | 240 | 15000 → 9000 | 3.40 | −1765 |
| 3 | SARGO → UBAGA | 6.85 | 015° | 220 | 9000 → 7000 | 1.87 | −1070 |
| 4 | UBAGA → SLL | 9.55 | 351° | 200 | 7000 → 5000 | 2.87 | −696 |

3. **Espera SLL** (06:14–06:16):
   - Altitud 5000 ft, velocidad 180 kt.
   - Circuito estándar a derechas:
     - `HOLD_SLL_FIX` → `HOLD_SLL_W1`: rumbo 246°, 1.48 NM, 0.49 min.
     - Viraje estándar (25°) durante 1 min hasta interceptar tramo recíproco.
     - `HOLD_SLL_W1` → `HOLD_SLL_FIX`: rumbo 066°, 1.48 NM, 0.49 min.
   - Mantener `vertical_rate` 0; el orquestador recalcula heading cada 5 s.
4. **Salida del hold**: al liberar, reanudar tramo `SLL → DOBRO → RWY07L` idéntico a EZY8104, pero con velocidad 170 kt hasta `DOBRO`.

## 8. Reglas de espaciado y sincronización
- **Longitudinal**: distancia ≥ 5 NM o Δt ≥ 2.5 min entre aeronaves en la misma SID/STAR.
- **Vertical**: mantener Δalt ≥ 1000 ft cuando rutas se cruzan (`MASNU` y `SLL`).
- **Intersecciones críticas**:
  - `MASNU`: verifica que VLG201 ya está > 7000 ft cuando EZY8104 pasa por 4000 ft.
  - `SLL`: RYR611 entra en el hold solo cuando EZY8104 ha dejado la senda hacia `DOBRO`.
- **Implementación**: en tu orquestador, antes de cada `PUT /controls`, consulta posición/altitud actual vía `GET /simulation/aircraft` y aplica la regla.

## 9. Codificación en el orquestador
1. **Catálogo de planes**: almacena cada tabla anterior como una lista de “legs” con los campos `waypoint`, `lat`, `lon`, `alt_ft`, `gs_kts`, `duration_s`.
2. **Interpolación**:
   - Recalcula cada 5 s el rumbo con la fórmula del apartado 4.
   - Calcula `vertical_rate = (alt_next - alt_curr) / duration_min`.
3. **API loop**:
   - `create_aircraft` → `update_controls` en cada leg.
   - Usa `time.sleep(duration_s)` o `asyncio.sleep`.
4. **Sincronización global**: gestiona un scheduler central (por ejemplo `heapq` con (timestamp, action)) para lanzar legs a la hora correcta.

## 10. Paquete de anomalías y datos imposibles
Inyecta registros maliciosos para probar reglas SIEM:
1. **GHOST01 (06:08)**:
   - `create_aircraft` en `GHOST` con `altitude = 35000`, `speed = 620`, `vertical_rate = 0`.
   - En 30 s cambia a `altitude = -300`, `speed = 620` (velocidad supersónica a altitud negativa). Marca `anomaly_flags=["NEG_ALT","HYPER_SPEED"]`.
2. **Duplicado ICAO (06:12)**:
   - Crea `VLG201B` reutilizando el `hex` de VLG201 (modifica el field en el orquestador) y sitúalo 5 NM detrás a 1500 ft → detecta spoofing.
3. **Salto de posición (06:18)**:
   - Para VLG201, actualiza instantáneamente a `lat = 41.6000, lon = 1.0000` manteniendo `altitude = 18000`. Marca `anomaly_flags=["JUMP"]`.
4. **Velocidad negativa (06:19)**:
   - EZY8104 en rodaje: `speed = -35` durante 10 s → prueba reglas de validación de sensores.

Documenta cada evento para que las reglas de Elastic (detección de altitud negativa, velocidad imposible, duplicación de ICAO) tengan ground truth.

## 11. Validación en Elastic Stack
1. **Ingesta**: Filebeat/Logstash deben enviar los documentos con campos personalizados (`flight`, `leg`, `anomaly_flags`, `sid/star`).
2. **Dashboards**: crea visualizaciones con filtros:
   - `phase.keyword: "CLIMB"` contra `phase.keyword: "APPROACH"`.
   - `is_simulated:true AND anomaly_flags:*`.
3. **Alertas**:
   - Regla de duplicado de ICAO: `count(distinct hex) != count(hex)` en ventana de 2 min.
   - Altitud negativa: `adsb.alt_baro < 0` o `adsb.alt_geom < 0`.
   - Velocidad > 600 kt por debajo de FL100.
4. **Logbook**: registra resultados (hora, regla disparada, captura) para la memoria final de la asignatura.

Siguiendo estos pasos tendrás un escenario reproducible, con rutas lógicas, procedimientos de aproximación/espera y anomalías controladas, listo para instrumentar en tu simulador y en Elastic Stack.
