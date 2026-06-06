"""
config.py — Configuración central del Agente_Val
================================================

Único lugar donde vive la configuración del agente de dosificaciones de
alimentos. Aquí se define:

    1. La IDENTIDAD del agente (nombre, versión, autoría).
    2. El SIGNIFICADO de cada carpeta del proyecto (qué guarda y para qué).
    3. La CONFIGURACIÓN DE CORREO para reportar las etiquetas de dosificación.

Reglas de oro
-------------
* Los SECRETOS (contraseñas, API keys) NUNCA se escriben aquí: se leen del
  entorno o de un archivo `.env` local (ver `.env.example`). Este `config.py`
  sí se sube al repo; el `.env` NO.
* Las RUTAS se resuelven siempre relativas a la carpeta del proyecto, así el
  agente funciona sin importar desde dónde se ejecute.

Uso típico
----------
    import config
    config.asegurar_rutas()                 # crea las carpetas si faltan
    print(config.AGENTE["nombre"])          # -> "Agente_Val"
    cfg = config.config_correo()            # dict con la config de email
    ok, faltan = config.validar_correo()    # ¿está listo para enviar?

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import os
from pathlib import Path


# ===========================================================================
# 0. Carga del archivo .env (sin dependencias externas)
# ===========================================================================
def _cargar_env(ruta: Path | None = None) -> None:
    """Carga el `.env` ubicado junto a este archivo, si existe.

    No sobreescribe variables que ya estén definidas en el entorno del sistema
    (las del sistema tienen prioridad). Ignora líneas vacías y comentarios.
    """
    ruta = ruta or Path(__file__).resolve().parent / ".env"
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_cargar_env()


def _env(clave: str, defecto: str = "") -> str:
    """Lee una variable de entorno como texto, con valor por defecto."""
    return os.environ.get(clave, defecto).strip()


def _env_bool(clave: str, defecto: bool = False) -> bool:
    """Lee una variable de entorno como booleano ('1','true','sí' = True)."""
    valor = _env(clave, "1" if defecto else "0").lower()
    return valor in {"1", "true", "t", "yes", "y", "si", "sí"}


def _env_int(clave: str, defecto: int) -> int:
    """Lee una variable de entorno como entero, con valor por defecto."""
    try:
        return int(_env(clave, str(defecto)))
    except ValueError:
        return defecto


# ===========================================================================
# 1. Identidad del agente
# ===========================================================================
AGENTE: dict[str, str] = {
    "nombre": _env("AGENTE_NOMBRE", "Agente_Val"),
    "version": "0.1.0",
    "descripcion": (
        "Asistente de dosificación de alimentos para microemprendedores: "
        "calcula formulaciones por lote, verifica límites de aditivos del "
        "RTCA 67.04.54:18 y reporta la etiqueta de dosificación por correo."
    ),
    "autora": "Valery",
    "curso": "Programación · Maestría en Automatización Industrial · UTH 2026.4",
}


# ===========================================================================
# 2. Significado de las carpetas y rutas del proyecto
# ===========================================================================
# Raíz del proyecto = la carpeta donde vive este config.py
RAIZ: Path = Path(__file__).resolve().parent

# --- carpetas principales --------------------------------------------------
DIR_SRC: Path = RAIZ / "src"          # código fuente (modelos, tools, agente)
DIR_DATA: Path = RAIZ / "data"        # datos persistentes del agente

# --- subcarpetas de data ---------------------------------------------------
DIR_ENTRADA: Path = DIR_DATA / "entrada"      # CSV de inventario/dosificación que ENTRA al agente
DIR_ETIQUETAS: Path = DIR_DATA / "etiquetas"  # etiquetas generadas que SALEN (texto/HTML/PDF)
DIR_MANUALES: Path = DIR_DATA / "manuales"    # PDFs (RTCA, fichas) para el RAG
DIR_HISTORIAL: Path = DIR_DATA / "historial"  # conversaciones guardadas del chat (auditoría)

# --- archivos clave --------------------------------------------------------
ARCHIVO_INVENTARIO: Path = DIR_DATA / "inventario.json"   # estado persistente del inventario
CSV_INVENTARIO: Path = DIR_ENTRADA / "inventario.csv"     # inventario inicial de las primeras pruebas

# Diccionario "significador": para qué sirve cada carpeta (se puede imprimir
# en la demo o consultar desde el agente).
SIGNIFICADO_CARPETAS: dict[str, str] = {
    str(DIR_SRC): "Código fuente: clases POO (modelos.py), herramientas y orquestador del agente.",
    str(DIR_DATA): "Datos persistentes del agente (estado y archivos de trabajo).",
    str(DIR_ENTRADA): "ENTRADA: CSV de inventario/dosificaciones que el agente lee en las pruebas.",
    str(DIR_ETIQUETAS): "SALIDA: etiquetas de dosificación generadas, listas para enviar por correo.",
    str(DIR_MANUALES): "Manuales y normas en PDF (RTCA 67.04.54:18, fichas técnicas) para el RAG.",
    str(DIR_HISTORIAL): "Conversaciones del chat guardadas (JSON) para auditar y corregir.",
}

# Carpetas que el agente necesita que existan para trabajar.
_CARPETAS_REQUERIDAS: tuple[Path, ...] = (
    DIR_SRC, DIR_DATA, DIR_ENTRADA, DIR_ETIQUETAS, DIR_MANUALES, DIR_HISTORIAL,
)


def asegurar_rutas() -> None:
    """Crea las carpetas del proyecto si todavía no existen (idempotente)."""
    for carpeta in _CARPETAS_REQUERIDAS:
        carpeta.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# 3. Configuración de correo (reporte de etiquetas)
# ===========================================================================
# Canal de envío: "resend" (API, recomendado) o "smtp" (smtplib estándar).
CANAL_CORREO: str = _env("CANAL_CORREO", "smtp").lower()

# Remitente y destinatario por defecto (no son secretos; pueden vivir en .env).
CORREO_DE: str = _env("CORREO_DE", "")            # ej. "agente@tudominio.com"
# Nombre visible del remitente (lo que ve el destinatario en vez de la dirección).
# Con Gmail SMTP la dirección no cambia, pero sí el nombre que se muestra.
CORREO_NOMBRE_DE: str = _env("CORREO_NOMBRE_DE", AGENTE["nombre"])
CORREO_PARA: str = _env("CORREO_PARA", "")        # destinatario por defecto del reporte
# Copia oculta (BCC): recibe SIEMPRE una copia de cada correo, sin que el
# destinatario lo vea. Útil para archivar/auditar lo que recibió el usuario.
CORREO_COPIA_OCULTA: str = _env("CORREO_COPIA_OCULTA", "")
CORREO_ASUNTO_PREFIJO: str = _env("CORREO_ASUNTO_PREFIJO", "[Agente_Val] ")


def config_smtp() -> dict:
    """Parámetros del servidor SMTP (para CANAL_CORREO='smtp').

    Defaults pensados para Gmail (smtp.gmail.com:587 con STARTTLS). Para
    Outlook/Hotmail usar host 'smtp.office365.com'. La CONTRASEÑA se lee del
    entorno (SMTP_PASSWORD) y nunca se guarda en este archivo.
    """
    return {
        "host": _env("SMTP_HOST", "smtp.gmail.com"),
        "puerto": _env_int("SMTP_PORT", 587),
        "usuario": _env("SMTP_USER", ""),          # normalmente = tu correo
        "password": _env("SMTP_PASSWORD", ""),     # SECRETO (App Password en Gmail)
        "usar_tls": _env_bool("SMTP_TLS", True),   # STARTTLS en el puerto 587
    }


def config_resend() -> dict:
    """Parámetros del proveedor Resend (para CANAL_CORREO='resend')."""
    return {
        "api_key": _env("RESEND_API_KEY", ""),     # SECRETO (re_...)
        "api_url": _env("RESEND_API_URL", "https://api.resend.com/emails"),
    }


def config_correo() -> dict:
    """Devuelve la configuración de correo del canal activo, ya unificada."""
    base = {
        "canal": CANAL_CORREO,
        "de": CORREO_DE,
        "nombre_de": CORREO_NOMBRE_DE,
        "para": CORREO_PARA,
        "copia_oculta": CORREO_COPIA_OCULTA,
        "prefijo_asunto": CORREO_ASUNTO_PREFIJO,
    }
    if CANAL_CORREO == "resend":
        base.update(config_resend())
    else:
        base.update(config_smtp())
    return base


def validar_correo() -> tuple[bool, list[str]]:
    """Indica si el correo está listo para enviar.

    Devuelve (ok, faltantes) donde `faltantes` lista los campos/variables que
    aún hay que definir (típicamente en el `.env`). Útil para que el agente
    avise con claridad antes de intentar un envío.
    """
    faltan: list[str] = []
    if not CORREO_DE:
        faltan.append("CORREO_DE (remitente)")
    if not CORREO_PARA:
        faltan.append("CORREO_PARA (destinatario por defecto)")

    if CANAL_CORREO == "resend":
        if not config_resend()["api_key"]:
            faltan.append("RESEND_API_KEY")
    else:  # smtp
        smtp = config_smtp()
        if not smtp["usuario"]:
            faltan.append("SMTP_USER")
        if not smtp["password"]:
            faltan.append("SMTP_PASSWORD")
        if not smtp["host"]:
            faltan.append("SMTP_HOST")
    return (len(faltan) == 0, faltan)


# ===========================================================================
# 4. Diagnóstico rápido — python config.py
# ===========================================================================
if __name__ == "__main__":
    asegurar_rutas()
    print(f"=== {AGENTE['nombre']} v{AGENTE['version']} ===")
    print(AGENTE["descripcion"])
    print(f"\nRaíz del proyecto: {RAIZ}\n")

    print("Carpetas del proyecto:")
    for ruta, significado in SIGNIFICADO_CARPETAS.items():
        existe = "✓" if Path(ruta).exists() else "�—"
        print(f"  [{existe}] {Path(ruta).name:<10} {significado}")

    print(f"\nCanal de correo activo: {CANAL_CORREO}")
    ok, faltan = validar_correo()
    if ok:
        print("Correo: LISTO para enviar.")
    else:
        print("Correo: faltan datos en el .env ->")
        for f in faltan:
            print(f"  - {f}")
        print("  (copia .env.example a .env y llénalo)")
