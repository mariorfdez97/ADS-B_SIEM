# Script de arranque único (`lanzar_lab.sh`)

Este script inicia tres procesos con un solo comando:
1. Servidor HTTP local (puerto 9000) que sirve `co-atc-main/data/aircraft.json`.
2. Backend Co-ATC (`bin/co-atc -config configs/config.toml`) usando la configuración del repo (LEBL y fuente local http://127.0.0.1:9000/aircraft.json).
3. Simulador BCN (`python3 simulador_bcn.py`) en modo nominal con factor de tiempo acelerado (`--factor-tiempo 120.0` por defecto; ajustable con `SIM_FACTOR_TIEMPO`).

## Uso
```bash
chmod +x lanzar_lab.sh
./lanzar_lab.sh
```

El script crea `logs/` con:
- `feed_http.log`: salida del servidor estático.
- `co_atc.log`: salida del backend Co-ATC.
- `simulador.log`: salida del simulador.
- `pids.env`: contiene los PID de cada proceso (FEED_PID, CO_ATC_PID, SIM_PID).

## Detener procesos
- Opción recomendada:
  ```bash
  ./detener_lab.sh
  ```
- Opción manual:
  ```bash
  source logs/pids.env
  kill $FEED_PID $CO_ATC_PID $SIM_PID $TAIL_PID
  ```
- Si no existiera `logs/pids.env`, `detener_lab.sh` intentará matar procesos por patrón (`python3 -m http.server 9000`, `bin/co-atc` o `go run ./cmd/server`, `simulador_bcn.py`, `tail -f`).

## Notas
- Requiere Python 3, Go y el contenido del directorio `co-atc-main` ya preparado.
- No modifica código ni configuraciones; solo arranca servicios y deja los logs separados.
- Por defecto NO se eliminan las bases SQLite. Si necesitas arrancar en limpio, exporta `RESET_COATC_DB=1` antes de ejecutar el script para borrar `co-atc-main/data/co-atc-*.db`.
- El script espera a que Co-ATC abra el puerto 8000 antes de lanzar el simulador (timeout 30 s) para evitar fallos de conexión del inyector.
- Se compila Co-ATC a binario `bin/co-atc` si no existe o si se exporta `FORCE_BUILD=1`; luego se arranca el binario (más rápido que `go run`).
- Para inyectar más rápido, usa `SIM_FACTOR_TIEMPO` (por defecto 120.0, aprox 2 min simulados = 1 s real).
