"""
probar_correo.py — Prueba de extremo a extremo del envío de correo
==================================================================

Manda un correo de prueba usando la configuración del `.env` para confirmar
que el Agente_Val puede notificar etiquetas por correo. No toca el inventario
ni las recetas: es solo el canal de salida.

Ejecutar desde la carpeta del proyecto:
    python probar_correo.py
    (o:  py probar_correo.py)
"""

from __future__ import annotations

import config
from src import notificar


def main() -> int:
    print(f"=== Prueba de correo · {config.AGENTE['nombre']} ===\n")

    # 1) Mostrar la configuración (sin revelar la contraseña).
    cfg = config.config_correo()
    print(f"Canal     : {cfg['canal']}")
    print(f"Remitente : {cfg['de']}")
    print(f"Destino   : {cfg['para']}")
    if cfg["canal"] == "smtp":
        print(f"Servidor  : {cfg['host']}:{cfg['puerto']} (TLS={cfg['usar_tls']})")

    # 2) Validar que no falte nada antes de intentar enviar.
    listo, faltan = config.validar_correo()
    if not listo:
        print("\n[X] El correo NO está listo. Faltan en el .env:")
        for f in faltan:
            print(f"    - {f}")
        return 1

    # 3) Enviar el correo de prueba.
    print("\nEnviando correo de prueba...")
    cuerpo = (
        f"Hola,\n\nEste es un correo de prueba enviado por {config.AGENTE['nombre']}.\n"
        "Si lo recibiste, el canal de correo del agente funciona correctamente "
        "y ya podemos reportar etiquetas de dosificación por este medio.\n\n"
        "— Agente_Val"
    )
    resultado = notificar.enviar_correo(
        asunto="Correo de prueba del agente",
        cuerpo=cuerpo,
    )

    # 4) Reportar el resultado.
    if resultado["ok"]:
        print(f"\n[OK] Correo enviado. {resultado['detalle']}")
        print(f"     Revisa la bandeja de {cfg['para']} (y la carpeta de spam).")
        return 0
    print(f"\n[X] No se pudo enviar: {resultado['detalle']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
