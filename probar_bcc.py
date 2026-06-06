"""
probar_bcc.py — Verifica el envío con copia oculta (BCC)
=======================================================

Manda un correo al "correo del usuario" (visible) y, en copia oculta, al
CORREO_COPIA_OCULTA del .env. Sirve para confirmar que:
  - el destinatario visible recibe el correo SIN ver la copia oculta;
  - la copia oculta recibe lo mismo que el usuario.

Ejecutar:  python probar_bcc.py
"""
from __future__ import annotations

import config
from src import notificar

# Simula el correo que nos daría el usuario (visible en el 'Para').
CORREO_DEL_USUARIO = "jorgeenriquevs@gmail.com"


def main() -> int:
    print(f"=== Prueba de BCC · {config.AGENTE['nombre']} ===\n")
    print(f"Para (usuario)  : {CORREO_DEL_USUARIO}")
    print(f"Copia oculta    : {config.CORREO_COPIA_OCULTA}\n")

    res = notificar.enviar_correo(
        asunto="Prueba de copia oculta",
        cuerpo=(
            "Hola,\n\nEste correo se envió al destinatario que indicó el usuario.\n"
            "Una copia oculta (BCC) llegó al correo de archivo del agente, sin que "
            "el usuario lo vea.\n\n— ConsulAlim AI"
        ),
        para=CORREO_DEL_USUARIO,
        # copia_oculta se omite -> usa CORREO_COPIA_OCULTA del .env automáticamente.
    )

    if res["ok"]:
        print(f"[OK] {res['detalle']}")
        print("\nRevisa AMBAS bandejas:")
        print(f"  - {CORREO_DEL_USUARIO} debe verlo SIN copia oculta en el encabezado.")
        print(f"  - {config.CORREO_COPIA_OCULTA} debe tener una copia del mismo correo.")
        return 0
    print(f"[X] No se pudo enviar: {res['detalle']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
