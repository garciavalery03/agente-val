"""
validar_etiqueta.py — Herramienta de validación RTCA para ConsulAlim AI
=======================================================================

El agente ejecuta este script para validar la etiqueta de un producto contra
la "Regla de Salida" del RTCA (usando las clases Producto/Etiqueta de
`src/modelos.py`). Devuelve JSON limpio: si CUMPLE, qué FALTA y observaciones.

Entrada: un JSON con los datos del producto + etiqueta. Puede venir de:
    * un archivo:    python tools/validar_etiqueta.py data/entrada/producto.json
    * la entrada estándar (stdin):  ... | python tools/validar_etiqueta.py -

Forma del JSON de entrada (campos opcionales se omiten):
    {
      "nombre": "Mermelada de mora",
      "tipo": "semisolido",
      "descripcion": "conserva pasteurizada",
      "ingredientes": [
        {"nombre": "Mora", "cantidad": 55, "unidad": "kg", "funcion": "fruta base"},
        {"clase": "Aditivo", "nombre": "Benzoato de sodio", "cantidad": 0.5,
         "unidad": "kg", "funcion": "conservante", "ins": "211", "dosis_maxima_mg_kg": 1000}
      ],
      "contenido_neto": [250, "g"],
      "pais_origen": "Honduras",
      "responsable": "Emprendimiento La Mora",
      "direccion_responsable": "Tegucigalpa, Honduras",
      "instrucciones": "Consérvese en lugar fresco",
      "alergenos": [],
      "fecha_vencimiento": "31/12/26"
    }

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.modelos import Etiqueta, EtiquetaInvalida, ErrorDominio  # noqa: E402


def validar_etiqueta(datos: dict) -> dict:
    """Construye la etiqueta desde `datos` y la valida. Devuelve dict JSON-able."""
    try:
        etiqueta = Etiqueta.from_dict(datos)
    except (EtiquetaInvalida, ErrorDominio) as exc:
        return {"ok": False, "error": f"Datos inválidos: {exc}"}

    resultado = etiqueta.validar()
    return {
        "ok": True,
        "aprobada": resultado.cumple,
        "producto": etiqueta.producto.nombre,
        "tipo": etiqueta.producto.tipo.value,
        "validacion": resultado.to_dict(),
        "etiqueta_texto": etiqueta.to_texto(),
    }


def _leer_entrada(arg: str) -> dict:
    """Lee el JSON de entrada desde un archivo o desde stdin ('-')."""
    if arg == "-":
        # Leer bytes y decodificar UTF-8: en Windows sys.stdin usa cp1252 y
        # rompería los acentos del JSON (ej. "Azúcar").
        crudo = sys.stdin.buffer.read().decode("utf-8")
    else:
        crudo = Path(arg).read_text(encoding="utf-8")
    return json.loads(crudo)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(json.dumps(
            {"ok": False, "error": "Uso: validar_etiqueta.py <archivo.json | ->"},
            ensure_ascii=False,
        ))
        sys.exit(1)
    try:
        datos = _leer_entrada(sys.argv[1])
    except FileNotFoundError:
        print(json.dumps({"ok": False, "error": f"No existe el archivo: {sys.argv[1]}"},
                         ensure_ascii=False))
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"JSON inválido: {exc}"},
                         ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(validar_etiqueta(datos), ensure_ascii=False, indent=2))
