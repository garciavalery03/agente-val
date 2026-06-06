"""
historial.py — Persistencia de las conversaciones del chat (auditoría)
=======================================================================

La web de ConsulAlim AI (`web/app.py`) es una conversación en memoria: al cerrar
la sesión se perdía todo. Este módulo guarda **cada conversación en disco** bajo
`data/historial/`, como un JSON por sesión, para poder **auditarla y corregirla**
después (que fue justo lo que faltó en el caso *lachiquitasabrosa*).

Diseño
------
* Un archivo por conversación: `data/historial/<fecha-hora>_<id>.json`.
* Se reescribe en cada turno (guardado incremental): aunque el consultante no
  termine, queda lo conversado hasta ese punto.
* El guardado **nunca debe romper el chat**: si falla el disco, se ignora el error
  (el chat sigue funcionando).

Formato del JSON
----------------
    {
      "id": "a1b2c3d4",
      "inicio": "2026-06-04T20:15:03",
      "actualizado": "2026-06-04T20:18:41",
      "paso": "enviar",
      "producto": {nombre, responsable, ...},   # datos capturados hasta ahora
      "mensajes": [ {"rol": "agente"|"user", "texto": "..."}, ... ]
    }

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from config import DIR_HISTORIAL  # noqa: E402


def nueva_sesion() -> dict:
    """Crea la metadata de una conversación nueva (id, inicio y ruta del archivo)."""
    inicio = datetime.now()
    sesion_id = uuid.uuid4().hex[:8]
    nombre = f"{inicio:%Y%m%d-%H%M%S}_{sesion_id}.json"
    return {
        "id": sesion_id,
        "inicio": inicio.isoformat(timespec="seconds"),
        "archivo": str(DIR_HISTORIAL / nombre),
    }


def guardar(sesion: dict, historial: list, datos: dict, paso: str) -> bool:
    """Reescribe el JSON de la conversación. Devuelve True si guardó.

    `historial` es la lista de tuplas (rol, texto) del chat; `datos` son los
    datos capturados del producto; `paso` es el estado actual de la máquina.
    Tolerante a fallos: ante cualquier error de E/S devuelve False sin lanzar.
    """
    try:
        DIR_HISTORIAL.mkdir(parents=True, exist_ok=True)
        registro = {
            "id": sesion.get("id"),
            "inicio": sesion.get("inicio"),
            "actualizado": datetime.now().isoformat(timespec="seconds"),
            "paso": paso,
            "producto": _resumen_producto(datos),
            "mensajes": [{"rol": rol, "texto": txt} for rol, txt in historial],
        }
        Path(sesion["archivo"]).write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception:  # noqa: BLE001 — el guardado jamás debe tumbar el chat
        return False


def _resumen_producto(datos: dict) -> dict:
    """Copia liviana de los datos capturados (sin objetos no serializables)."""
    if not isinstance(datos, dict):
        return {}
    try:
        return json.loads(json.dumps(datos, ensure_ascii=False, default=str))
    except Exception:  # noqa: BLE001
        return {}


def listar() -> list[dict]:
    """Lista las conversaciones guardadas (más recientes primero) con metadata."""
    if not DIR_HISTORIAL.exists():
        return []
    items: list[dict] = []
    for ruta in DIR_HISTORIAL.glob("*.json"):
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — un archivo corrupto no rompe el listado
            continue
        prod = d.get("producto") or {}
        items.append({
            "archivo": str(ruta),
            "id": d.get("id", ruta.stem),
            "inicio": d.get("inicio", ""),
            "actualizado": d.get("actualizado", ""),
            "paso": d.get("paso", ""),
            "nombre": prod.get("nombre", "(sin nombre)"),
            "responsable": prod.get("responsable", ""),
            "n_mensajes": len(d.get("mensajes", [])),
        })
    items.sort(key=lambda x: x["actualizado"] or x["inicio"], reverse=True)
    return items


def cargar(archivo: str) -> dict:
    """Carga una conversación guardada por su ruta. Lanza si no existe / es inválida."""
    return json.loads(Path(archivo).read_text(encoding="utf-8"))


# --- Diagnóstico rápido: python src/historial.py ---------------------------
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    convs = listar()
    print(f"{len(convs)} conversación(es) en {DIR_HISTORIAL}:")
    for c in convs:
        print(f"  [{c['actualizado']}] {c['nombre']} · {c['responsable']} "
              f"· paso={c['paso']} · {c['n_mensajes']} msgs · {Path(c['archivo']).name}")
