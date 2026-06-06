"""
consultar_norma.py — Herramienta de RAG para ConsulAlim AI
==========================================================

El agente ejecuta este script para consultar la documentación del RTCA
(`data/RAG/`) y obtener fragmentos que **fundamenten** su respuesta, con su
fuente (PDF y página). Devuelve SIEMPRE JSON limpio por stdout, para que
Claude Code lo lea y razone sobre él.

Uso:
    python tools/consultar_norma.py "declaración de aditivos" [k]

Salida (JSON):
    {
      "ok": true,
      "consulta": "...",
      "resultados": [{"fuente": "...", "pagina": 3, "texto": "...", "score": 0.42}, ...]
    }

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite importar el paquete src tanto si se corre suelto como en módulo.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.rag import RAG  # noqa: E402


def consultar_norma(consulta: str, k: int = 3) -> dict:
    """Consulta el RAG y devuelve un dict JSON-able con los fragmentos."""
    consulta = (consulta or "").strip()
    if not consulta:
        return {"ok": False, "error": "Consulta vacía.", "resultados": []}
    try:
        rag = RAG().construir()
        resultados = rag.consultar(consulta, k=k)
        return {
            "ok": True,
            "consulta": consulta,
            "total_fragmentos_indice": len(rag.fragmentos),
            "resultados": resultados,
        }
    except Exception as exc:  # noqa: BLE001 — devolvemos el error como dato
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "resultados": []}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args:
        print(json.dumps(
            {"ok": False, "error": "Uso: consultar_norma.py \"consulta\" [k]"},
            ensure_ascii=False,
        ))
        sys.exit(1)
    # El último argumento, si es número, es k.
    k = 3
    if len(args) > 1 and args[-1].isdigit():
        k = int(args[-1])
        args = args[:-1]
    consulta = " ".join(args)
    print(json.dumps(consultar_norma(consulta, k), ensure_ascii=False, indent=2))
