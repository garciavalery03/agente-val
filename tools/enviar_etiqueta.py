"""
enviar_etiqueta.py — Entrega de la etiqueta aprobada (canal de salida)
======================================================================

Une el flujo final de ConsulAlim AI: valida la etiqueta y, **solo si cumple**
el RTCA, la entrega al emprendedor por correo (usando `src/notificar.py`).
Si NO cumple, no envía nada y devuelve los faltantes para que el emprendedor
los corrija.

Modo simulado: con `--simular` (o si el correo no está configurado en el .env)
NO envía; solo muestra lo que se enviaría. Útil para la demo sin credenciales.

Uso:
    python tools/enviar_etiqueta.py data/entrada/ejemplo_producto.json --para correo@dominio.com
    python tools/enviar_etiqueta.py data/entrada/ejemplo_producto.json --simular
    cat producto.json | python tools/enviar_etiqueta.py - --simular

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src import notificar  # noqa: E402
from src.modelos import Etiqueta, EtiquetaInvalida, ErrorDominio  # noqa: E402
from tools.generar_etiqueta import generar as generar_imagen  # noqa: E402


def enviar_etiqueta(
    datos: dict,
    para: str | None = None,
    simular: bool = False,
    adjuntar_imagen: bool = True,
) -> dict:
    """Valida la etiqueta y la envía si cumple. Devuelve dict JSON-able.

    Si `adjuntar_imagen` es True (por defecto), genera el PNG de la etiqueta y lo
    adjunta al correo, además del texto.
    """
    try:
        etiqueta = Etiqueta.from_dict(datos)
    except (EtiquetaInvalida, ErrorDominio) as exc:
        return {"ok": False, "enviado": False, "error": f"Datos inválidos: {exc}"}

    resultado = etiqueta.validar()
    if not resultado.cumple:
        return {
            "ok": True,
            "enviado": False,
            "aprobada": False,
            "motivo": "La etiqueta no cumple el RTCA; no se envía.",
            "validacion": resultado.to_dict(),
        }

    asunto = f"Etiqueta aprobada: {etiqueta.producto.nombre}"
    cuerpo = (
        "Tu etiqueta cumple con el RTCA. Aquí está el modelo aprobado "
        "(la imagen va adjunta):\n\n"
        + etiqueta.to_texto()
        + "\n\n— ConsulAlim AI"
    )

    # Genera la imagen de la etiqueta para adjuntarla al correo.
    adjuntos: list[str] = []
    if adjuntar_imagen:
        res_img = generar_imagen(datos)
        if res_img.get("generada"):
            adjuntos.append(res_img["archivo"])

    if simular:
        return {
            "ok": True,
            "enviado": False,
            "aprobada": True,
            "modo": "simulado",
            "para": para or "(CORREO_PARA del .env)",
            "asunto": asunto,
            "cuerpo": cuerpo,
            "adjuntos": adjuntos,
        }

    envio = notificar.enviar_correo(asunto=asunto, cuerpo=cuerpo, para=para, adjuntos=adjuntos)
    return {
        "ok": envio["ok"],
        "enviado": envio["ok"],
        "aprobada": True,
        "canal": envio.get("canal"),
        "detalle": envio.get("detalle"),
        "adjuntos": adjuntos,
    }


def _leer_entrada(arg: str) -> dict:
    # Leer bytes y decodificar UTF-8: en Windows sys.stdin usa cp1252 y rompería
    # los acentos del JSON (ej. "Azúcar").
    crudo = (sys.stdin.buffer.read().decode("utf-8") if arg == "-"
             else Path(arg).read_text(encoding="utf-8"))
    return json.loads(crudo)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    argv = sys.argv[1:]
    if not argv:
        print(json.dumps(
            {"ok": False, "error": "Uso: enviar_etiqueta.py <archivo.json|-> [--para correo] [--simular]"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    fuente = argv[0]
    simular = "--simular" in argv
    para = None
    if "--para" in argv:
        i = argv.index("--para")
        if i + 1 < len(argv):
            para = argv[i + 1]

    try:
        datos = _leer_entrada(fuente)
    except FileNotFoundError:
        print(json.dumps({"ok": False, "error": f"No existe el archivo: {fuente}"}, ensure_ascii=False))
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"JSON inválido: {exc}"}, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(enviar_etiqueta(datos, para=para, simular=simular), ensure_ascii=False, indent=2))
