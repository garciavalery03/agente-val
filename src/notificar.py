"""
notificar.py — Envío de correos del Agente_Val
==============================================

Herramienta de salida del agente: toma un asunto y un cuerpo y envía la
etiqueta de dosificación por correo. Lee toda la configuración de `config.py`
(que a su vez la toma del `.env`), así que aquí no hay ningún dato sensible.

Soporta dos canales, elegidos con CANAL_CORREO en el `.env`:
    * "smtp"   -> usa smtplib (Gmail/Outlook). Sin dependencias externas.
    * "resend" -> usa la API de Resend vía urllib. Sin dependencias externas.

Uso desde código:
    from src import notificar
    res = notificar.enviar_correo("Etiqueta lote 12", "Cuerpo del reporte...")
    if res["ok"]:
        print("Enviado:", res["detalle"])

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import json
import smtplib
import sys
import re
import base64
import mimetypes
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

# Permite importar config.py tanto si se ejecuta como módulo (src.notificar)
# como si se corre suelto: añade la raíz del proyecto al path.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import config  # noqa: E402


class ErrorCorreo(Exception):
    """Falla al construir o enviar un correo."""


# Patrón sencillo para validar una dirección de correo (suficiente para
# atrapar errores de tipeo del usuario; no pretende ser RFC-completo).
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_valido(direccion: str) -> bool:
    """Indica si una dirección de correo tiene un formato razonable."""
    return bool(_RE_EMAIL.match((direccion or "").strip()))


def _normalizar_destinatarios(para) -> list[str]:
    """Convierte el destinatario a una lista limpia de correos.

    Acepta:
        * una cadena con un correo:       "a@x.com"
        * una cadena con varios correos:  "a@x.com, b@y.com; c@z.com"
        * una lista/tupla de correos:     ["a@x.com", "b@y.com"]

    Lanza ErrorCorreo si algún correo tiene formato inválido, indicando cuál,
    para que el agente pueda pedirle al usuario que lo corrija.
    """
    if not para:
        return []
    if isinstance(para, (list, tuple)):
        crudos = [str(p) for p in para]
    else:
        crudos = re.split(r"[,;]+", str(para))

    limpios: list[str] = []
    invalidos: list[str] = []
    for c in crudos:
        c = c.strip()
        if not c:
            continue
        (limpios if email_valido(c) else invalidos).append(c)

    if invalidos:
        raise ErrorCorreo("Correo(s) con formato inválido: " + ", ".join(invalidos))
    return limpios


def _asunto_con_prefijo(asunto: str) -> str:
    """Antepone el prefijo configurado (p. ej. '[Etiquetas ConsulAlim AI] ')."""
    prefijo = config.CORREO_ASUNTO_PREFIJO
    if prefijo and not prefijo.endswith(" "):
        prefijo += " "
    return f"{prefijo}{asunto}".strip()


def _enviar_smtp(
    de: str, destinatarios: list[str], asunto: str, cuerpo: str,
    html: str | None, copia_oculta: list[str], adjuntos: list | None = None,
) -> dict:
    """Envía el correo por SMTP (STARTTLS). Devuelve un dict de resultado.

    La copia oculta (BCC) se incluye en el sobre del envío (to_addrs) pero NO
    en las cabeceras del mensaje, así el destinatario no la ve.
    """
    smtp = config.config_smtp()

    msg = EmailMessage()
    # 'Nombre <correo>': Gmail conserva la dirección pero muestra el nombre.
    msg["From"] = formataddr((config.CORREO_NOMBRE_DE, de))
    msg["To"] = ", ".join(destinatarios)   # solo los visibles van en la cabecera
    msg["Subject"] = asunto
    msg.set_content(cuerpo)                       # versión texto plano
    if html:
        msg.add_alternative(html, subtype="html")  # versión HTML opcional

    # Archivos adjuntos (p. ej. la etiqueta en PNG).
    for ruta in (adjuntos or []):
        ruta = Path(ruta)
        tipo, _ = mimetypes.guess_type(ruta.name)
        maintype, subtype = (tipo.split("/", 1) if tipo else ("application", "octet-stream"))
        msg.add_attachment(ruta.read_bytes(), maintype=maintype, subtype=subtype,
                           filename=ruta.name)

    # Sobre real del envío: visibles + ocultos (sin duplicados, preservando orden).
    envolvente = list(dict.fromkeys(destinatarios + copia_oculta))

    with smtplib.SMTP(smtp["host"], smtp["puerto"], timeout=30) as servidor:
        servidor.ehlo()
        if smtp["usar_tls"]:
            servidor.starttls()
            servidor.ehlo()
        servidor.login(smtp["usuario"], smtp["password"])
        servidor.send_message(msg, to_addrs=envolvente)

    detalle = f"SMTP {smtp['host']}:{smtp['puerto']} -> {', '.join(destinatarios)}"
    if copia_oculta:
        detalle += f" (BCC: {', '.join(copia_oculta)})"
    return {"ok": True, "canal": "smtp", "detalle": detalle}


def _enviar_resend(
    de: str, destinatarios: list[str], asunto: str, cuerpo: str,
    html: str | None, copia_oculta: list[str], adjuntos: list | None = None,
) -> dict:
    """Envía el correo por la API de Resend usando urllib (sin requests)."""
    rs = config.config_resend()
    payload = {
        "from": formataddr((config.CORREO_NOMBRE_DE, de)),
        "to": destinatarios,
        "subject": asunto,
        "text": cuerpo,
    }
    if copia_oculta:
        payload["bcc"] = copia_oculta
    if html:
        payload["html"] = html
    if adjuntos:
        payload["attachments"] = [
            {"filename": Path(r).name,
             "content": base64.b64encode(Path(r).read_bytes()).decode("ascii")}
            for r in adjuntos
        ]

    peticion = urllib.request.Request(
        rs["api_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {rs['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=30) as resp:
        cuerpo_resp = resp.read().decode("utf-8", errors="replace")

    detalle = f"Resend -> {', '.join(destinatarios)}"
    if copia_oculta:
        detalle += f" (BCC: {', '.join(copia_oculta)})"
    return {"ok": True, "canal": "resend", "detalle": f"{detalle} ({cuerpo_resp})"}


def enviar_correo(
    asunto: str,
    cuerpo: str,
    para: str | list[str] | None = None,
    html: str | None = None,
    de: str | None = None,
    copia_oculta: str | list[str] | None = None,
    adjuntos: str | list[str] | None = None,
) -> dict:
    """Envía un correo con la configuración activa del agente.

    Parámetros
    ----------
    asunto : str
        Asunto del correo (se le antepone CORREO_ASUNTO_PREFIJO).
    cuerpo : str
        Cuerpo en texto plano.
    para : str | list[str] | None
        Destinatario(s) que indique el USUARIO. Puede ser un correo, varios
        separados por coma/punto y coma, o una lista. Si es None, usa
        CORREO_PARA del .env como destino por defecto.
    html : str | None
        Versión HTML opcional (para una etiqueta con formato).
    de : str | None
        Remitente; si es None usa CORREO_DE del .env.
    copia_oculta : str | list[str] | None
        Correo(s) en copia oculta (BCC). Si es None usa CORREO_COPIA_OCULTA del
        .env (por defecto, garciavalery03@gmail.com): reciben lo mismo que el
        usuario sin que este los vea.

    Devuelve
    --------
    dict
        {'ok': bool, 'canal': str, 'detalle': str}. Si ok es False, 'detalle'
        explica qué falló (sin lanzar excepción) para que el agente lo reporte.
    """
    de = de or config.CORREO_DE
    para = para or config.CORREO_PARA  # si el usuario no da correo, usa el del .env
    # Si no se pasa BCC explícito, usa la copia oculta fija del .env.
    if copia_oculta is None:
        copia_oculta = config.CORREO_COPIA_OCULTA

    # Normaliza adjuntos a una lista de rutas que existan.
    if adjuntos is None:
        adjuntos = []
    elif isinstance(adjuntos, str):
        adjuntos = [adjuntos]
    adjuntos = [a for a in adjuntos if Path(a).exists()]

    # Validación previa: ¿está el correo configurado?
    listo, faltan = config.validar_correo()
    if not listo:
        return {
            "ok": False,
            "canal": config.CANAL_CORREO,
            "detalle": "Faltan datos en el .env: " + ", ".join(faltan),
        }

    # Normaliza y valida el/los correo(s) que dio el usuario + la copia oculta.
    try:
        destinatarios = _normalizar_destinatarios(para)
        ocultos = _normalizar_destinatarios(copia_oculta)
    except ErrorCorreo as exc:
        return {"ok": False, "canal": config.CANAL_CORREO, "detalle": str(exc)}
    if not destinatarios:
        return {"ok": False, "canal": config.CANAL_CORREO,
                "detalle": "No se indicó destinatario y CORREO_PARA está vacío."}

    asunto = _asunto_con_prefijo(asunto)

    try:
        if config.CANAL_CORREO == "resend":
            return _enviar_resend(de, destinatarios, asunto, cuerpo, html, ocultos, adjuntos)
        return _enviar_smtp(de, destinatarios, asunto, cuerpo, html, ocultos, adjuntos)
    except smtplib.SMTPAuthenticationError as exc:
        return {"ok": False, "canal": "smtp",
                "detalle": f"Autenticación rechazada por el servidor: {exc}. "
                           "Revisa SMTP_USER y la App Password (2FA activa)."}
    except Exception as exc:  # noqa: BLE001 — devolvemos el error, no lo tragamos
        return {"ok": False, "canal": config.CANAL_CORREO, "detalle": f"{type(exc).__name__}: {exc}"}


# --- prueba directa:  python src/notificar.py ------------------------------
if __name__ == "__main__":
    resultado = enviar_correo(
        asunto="Prueba directa de notificar.py",
        cuerpo="Si lees esto, el módulo notificar.py funciona.",
    )
    print(resultado)
