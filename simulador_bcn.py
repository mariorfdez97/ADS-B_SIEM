#!/usr/bin/env python3
"""
Punto de entrada del simulador de tráfico ADS-B.
Delegamos toda la lógica en el paquete `simulador_bcn_pkg` para
mantener el código organizado sin alterar la funcionalidad original.
"""

from simulador_bcn_pkg.cli import main


if __name__ == "__main__":
    main()
