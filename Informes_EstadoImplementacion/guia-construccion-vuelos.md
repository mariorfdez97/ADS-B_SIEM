# Guía sencilla del inyector de vuelos ADS-B

Esta nota resume, con lenguaje llano, cómo se construyen y se lanzan los vuelos simulados del inyector (`simulador_bcn.py` + `simulador_bcn_pkg/`). Sirve para entender qué son los puntos de navegación, qué vuelos se crean y qué hace cada función clave.

## Resumen rápido del flujo
- `simulador_bcn.py` llama a `simulador_bcn_pkg/cli.py`.
- `cli.py` arma el escenario con `builders.py`, configura logs y ejecuta eventos.
- `models.py` define los modelos de datos (puntos, tramos, vuelos, eventos).
- `context.py` habla con la API de Co-ATC (crea, mueve y borra aeronaves).
- `scheduler.py` dispara los eventos en orden temporal.
- `utils.py` aporta cálculos de rumbo, distancia y la hora CET.

## Puntos de navegación (fijos del escenario)
Todos viven en `builders.py` (función `construir_puntos`) y forman el diccionario `PUNTOS_ESCENARIO`. Son coordenadas estáticas que se usan como hitos de ruta:
- Pistas/aeropuerto: `LEBL` (torre), `RWY07L`, `RWY07R`.
- Interceptos y maniobras finales: `IF_07L`, `IF_07R`, `BASE_07L`, `BASE_07R`, `DOWNWIND_N`.
- Entradas/salidas habituales: `NELSO`, `TARRA`, `TGA`, `LORET`, `MASNU`, `BAMES`, `KENAS`, `GIRON`, `SITGE`, `SARGO`, `UBAGA`, `SLL`, `DOBRO`.
- Esperas y referencias extra: `HOLD_E`, `HOLD_W`.
- Puntos de anomalía: `GHOST`, `ANM_EAST`, `ANM_WEST`, `ANM_SOUTH`.

## Vuelos que se generan por defecto
`builders.construir_vuelos(fecha_base, incluir_anomalias=False)` arma la lista de `VueloSimulado` a partir de esos puntos. La hora de referencia es las 06:00 CET del día indicado y cada vuelo tiene:
- Hora de creación (cuándo se hace POST de alta).
- Hora de inicio de tramos (primer PUT de controles).
- Punto de inicio, altitud/velocidad/rumbo inicial y la lista de tramos.

### Salidas (8 vuelos)
- `DPT101` A320, arranca en `RWY07R`, sale hacia `NELSO` (200 kt / 3 000 ft) y sigue a `LORET` (300 kt / 10 000 ft).
- `DPT102` A320, `RWY07L` → `MASNU` (210 kt / 4 000 ft) → `KENAS` (280 kt / 11 000 ft).
- `DPT103` B738, `RWY07R` → `TARRA` (220 kt / 5 000 ft) → `TGA` (290 kt / 12 000 ft).
- `DPT104` ATR72, `RWY07L` → `SITGE` (170 kt / 3 000 ft) → `SARGO` (190 kt / 6 000 ft).
- `DPT105` A321, `RWY07R` → `SARGO` (210 kt / 4 500 ft) → `UBAGA` (260 kt / 9 500 ft).
- `DPT106` B738, `RWY07L` → `NELSO` (200 kt / 3 500 ft) → `LORET` (280 kt / 10 500 ft).
- `DPT107` CRJ9, `RWY07R` → `MASNU` (200 kt / 4 000 ft) → `BAMES` (250 kt / 9 000 ft).
- `DPT108` A320, `RWY07L` → `SARGO` (200 kt / 4 000 ft) → `KENAS` (270 kt / 10 000 ft).

### Llegadas (8 vuelos)
Comienzan unos minutos más tarde (06:06 CET) con altitud inicial 9 000 ft y 220 kt:
- `ARR201` A321, entra por `LORET` → `SARGO` (200 kt / 5 000 ft) → `RWY07L` (150 kt / 150 ft).
- `ARR202` A320, `MASNU` → `SLL` (190 kt / 4 000 ft) → `RWY07R` (145 kt / 120 ft).
- `ARR203` B738, `TGA` → `SITGE` (200 kt / 5 000 ft) → `RWY07R` (150 kt / 150 ft).
- `ARR204` A320, `KENAS` → `SLL` (190 kt / 4 000 ft) → `RWY07L` (145 kt / 120 ft).
- `ARR205` A320, `GIRON` → `MASNU` (200 kt / 5 000 ft) → `RWY07R` (150 kt / 120 ft).
- `ARR206` A320, `BAMES` → `MASNU` (200 kt / 5 000 ft) → `RWY07L` (150 kt / 140 ft).
- `ARR207` B738, `UBAGA` → `SLL` (190 kt / 4 000 ft) → `RWY07L` (145 kt / 120 ft).
- `ARR208` CRJ9, `SARGO` → `IF_07R` (170 kt / 2 800 ft) → `RWY07R` (140 kt / 120 ft).

### Anomalías opcionales
Si se llama `construir_vuelos(..., incluir_anomalias=True)` se añade `GHOST01`, un vuelo fantasma supersónico (`GHOST` → `ANM_WEST`, 500–520 kt, altitud 25 000 → 20 000 ft) lanzado a las 06:02 CET.

`builders.construir_anomalias(fecha_base)` agrega eventos puntuales sobre vuelos ya creados:
- 06:18:00 CET: fuerza altitud negativa y vr -4000 fpm a `DPT101` apuntándolo a `TGA`.
- 06:18:45 CET: salto brusco de controles en `ARR201` (rumbo 45°, 500 kt, vr 0).
- 06:19:00 CET: asigna velocidad negativa a `ARR205` (rumbo 180°, -35 kt).

## Qué hace cada archivo/función

### builders.py
- `construir_puntos()`: crea todas las referencias geográficas del escenario y devuelve un diccionario `nombre -> PuntoNavegacion`.
- `construir_vuelos(fecha_base, incluir_anomalias)`: arma listas de salidas/llegadas con horas relativas a `hora_cet(fecha_base, 6, 0, 0)`, define tramos y devuelve `List[VueloSimulado]`. Si se piden anomalías, añade el vuelo `GHOST01`.
- `construir_anomalias(fecha_base)`: devuelve `List[EventoProgramado]` que modifican controles en horas concretas (altitud negativa, salto de posición, velocidad negativa).

### context.py
- Clase `ContextoSimulacion`: mantiene la `Session` HTTP, factor de tiempo y el mapa identificador→hex.
  - `crear_aeronave(...)`: POST `/simulation/aircraft` con posición inicial y plan de vuelo; guarda el hex. En `modo_simulacion` solo loguea y genera hexes `DRYxxx`.
  - `actualizar_controles(...)`: PUT `/simulation/aircraft/{hex}/controls` con heading, speed y vertical_rate. Escala por factor de tiempo y limita a ±3000 fpm y 500 kt.
  - `eliminar_aeronave(...)`: DELETE `/simulation/aircraft/{hex}` salvo en dry-run.
  - `obtener_hex(...)`: recupera el hex guardado (lanza error si falta y no se permite ausencia).
  - `buscar_vuelo_por_id(...)`: encuentra un `VueloSimulado` por su identificador.

### models.py
- `PuntoNavegacion`: nombre + latitud/longitud.
- `TramoVuelo`: destino, velocidad y altitud objetivo, con opciones manuales de rumbo, duración y vertical_rate. `calcular_parametros` deduce rumbo, duración (con distancia NM y velocidad) y vertical_rate (acotada a ±3000 fpm).
- `EventoProgramado`: instante CET, descripción y función `accion(contexto)`.
- `VueloSimulado`: datos iniciales de la aeronave y sus tramos.
  - `generar_eventos()`: crea la secuencia de `EventoProgramado` para alta, cada tramo y eliminación final (si `eliminar_al_final=True`).
  - `generar_vertical_rate_inicial()`: devuelve 0 si la velocidad inicial es 0; en otro caso, 1000 fpm suaves.
  - `generar_plan_de_vuelo()`: lista de puntos (lat, lon, altitud, speed) para la creación inicial.

### scheduler.py
- `ejecutar_eventos(contexto, eventos, factor_tiempo)`: ordena los eventos por hora, calcula cuánto esperar en tiempo real usando `time.monotonic` y los ejecuta respetando el factor de aceleración.

### utils.py
- `calcular_rumbo(origen, destino)`: rumbo geodésico en grados (0–360).
- `calcular_distancia_nm(origen, destino)`: distancia entre puntos en millas náuticas.
- `hora_cet(fecha, horas, minutos, segundos=0)`: construye un `datetime` CET (UTC+1) a partir de la fecha base.

## Cómo leerlo mentalmente
1. `construir_puntos` fija el mapa estático de coordenadas.
2. `construir_vuelos` usa esos puntos para montar salidas/llegadas y opcionalmente `GHOST01`.
3. Cada `VueloSimulado` se transforma en eventos (crear, mover por tramos, borrar).
4. `construir_anomalias` añade eventos especiales de prueba SIEM.
5. `scheduler.ejecutar_eventos` reproduce todo en orden mientras `context.py` habla con la API real o en dry-run.
