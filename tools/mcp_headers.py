"""
mcp_headers.py — Headers de autenticación del MCP de la clase (headersHelper)
=============================================================================

Claude Code NO lee el `.env` del proyecto para expandir `${VAR}` en `.mcp.json`
(solo lee el entorno del sistema). Para tomar el token **desde el `.env`**, este
script actúa como `headersHelper`: imprime en stdout un JSON con los headers, que
Claude Code usa al conectarse al servidor HTTP `uthagentes`.

Orden de búsqueda del token:
    1. Variable de entorno UTHAGENTES_TOKEN (si está definida).
    2. Archivo `.env` del proyecto (clave UTHAGENTES_TOKEN).

Salida (stdout):
    {"Authorization": "Bearer <token>", "ngrok-skip-browser-warning": "true"}

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def leer_token() -> str:
    """Devuelve el token: primero del entorno, luego del `.env` del proyecto."""
    tok = os.environ.get("UTHAGENTES_TOKEN", "").strip()
    if tok:
        return tok
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea.startswith("UTHAGENTES_TOKEN="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    headers = {"ngrok-skip-browser-warning": "true"}
    token = leer_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    print(json.dumps(headers))
