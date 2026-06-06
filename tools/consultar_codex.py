"""
consultar_codex.py — Herramienta de consulta en línea (Codex/FAO) para ConsulAlim AI
====================================================================================

Lee las URLs guardadas en los archivos `.txt` de `data/RAG/` (p. ej.
`Base_Codex.txt`, con la base de aditivos del Codex/FAO–GSFA) y verifica que
estén disponibles, trayendo un extracto. **Si una URL está caída o no responde,
la salta** y lo deja registrado, sin detener la consulta y sin inventar nada
(regla del cerebro del agente).

Uso:
    python tools/consultar_codex.py

Salida (JSON):
    {
      "ok": true,
      "fuentes": [
        {"archivo": "Base_Codex.txt", "url": "https://...", "disponible": true,
         "estado": 200, "extracto": "..."},
        ...
      ]
    }

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_DIR_RAG = _RAIZ / "data" / "RAG"

_RE_URL = re.compile(r"https?://\S+")
_TIEMPO_LIMITE = 10  # segundos


def _urls_en_txt(directorio: Path) -> list[tuple[str, str]]:
    """Devuelve [(archivo, url), ...] extraídas de los .txt del directorio."""
    pares: list[tuple[str, str]] = []
    if not directorio.exists():
        return pares
    for txt in sorted(directorio.glob("*.txt")):
        contenido = txt.read_text(encoding="utf-8", errors="replace")
        for url in _RE_URL.findall(contenido):
            pares.append((txt.name, url.strip().rstrip(").,")))
    return pares


def _consultar_url(url: str) -> dict:
    """Intenta abrir la URL. Devuelve disponibilidad, estado y un extracto.

    Nunca lanza: si falla (caída, timeout, DNS), marca disponible=False con el
    motivo, para que el agente la salte y siga con las fuentes locales.
    """
    peticion = urllib.request.Request(url, headers={"User-Agent": "ConsulAlim-AI/0.1"})
    try:
        with urllib.request.urlopen(peticion, timeout=_TIEMPO_LIMITE) as resp:
            estado = resp.getcode()
            crudo = resp.read(4000).decode("utf-8", errors="replace")
        # Extracto legible: quita etiquetas HTML y comprime espacios.
        texto = re.sub(r"<[^>]+>", " ", crudo)
        texto = re.sub(r"\s+", " ", texto).strip()
        return {
            "disponible": True,
            "estado": estado,
            "extracto": texto[:300],
        }
    except Exception as exc:  # noqa: BLE001 — la caída es un dato, no un crash
        return {
            "disponible": False,
            "estado": None,
            "motivo": f"{type(exc).__name__}: {exc}",
            "nota": "URL saltada; usar las fuentes locales (PDFs) del RAG.",
        }


def consultar_codex() -> dict:
    """Verifica todas las URLs de los .txt del RAG. Devuelve dict JSON-able."""
    pares = _urls_en_txt(_DIR_RAG)
    if not pares:
        return {"ok": True, "fuentes": [], "nota": "No hay URLs en data/RAG/*.txt."}
    fuentes = []
    for archivo, url in pares:
        resultado = {"archivo": archivo, "url": url}
        resultado.update(_consultar_url(url))
        fuentes.append(resultado)
    return {"ok": True, "fuentes": fuentes}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(consultar_codex(), ensure_ascii=False, indent=2))
