"""
conocimiento.py — Conocimiento técnico del agente (aditivos, alérgenos, ortografía)
==================================================================================

Una de las tareas **primordiales** de ConsulAlim AI es reconocer por sí mismo los
aditivos y alérgenos de un producto, **sin que el consultante tenga que dictarlos**
(la mayoría no conoce su función ni su código INS). Este módulo es ese "saber":

    * ADITIVOS  → tabla curada nombre/sinónimos → (nombre canónico, función RTCA, INS).
    * ALERGENOS → patrones de ingrediente → alérgeno de declaración obligatoria.
    * CORRECCIONES → ortografía/acentos de los términos de alimentos más comunes.

Y tres funciones que el flujo de captura usa directamente:

    * `identificar_aditivo(texto)` → datos del aditivo si el texto lo es; None si no.
    * `detectar_alergenos(nombres)` → lista de Alergeno presentes en esos ingredientes.
    * `corregir_ortografia(nombre)` → el nombre con acentos/ortografía corregidos.
    * `separar_ingredientes(texto)` → parte una lista pegada en ingredientes sueltos.

Las dosis máximas NO se fijan aquí: dependen de la categoría de alimento y se
consultan en la norma (RTCA 419-2019 / Codex GSFA). El agente no las inventa.

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path


# ---------------------------------------------------------------------------
# Normalización (para comparar sin que estorben acentos/mayúsculas)
# ---------------------------------------------------------------------------
def _sin_acentos(texto: str) -> str:
    """Quita acentos/diacríticos de una cadena (para comparar, no para mostrar)."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    """Clave de comparación: sin acentos, en minúsculas y con espacios colapsados."""
    return re.sub(r"\s+", " ", _sin_acentos(texto).lower()).strip()


# ---------------------------------------------------------------------------
# Tabla de aditivos: (INS, nombre canónico, función RTCA, [sinónimos])
# Los sinónimos cubren cómo los escribe la gente (sin acentos, abreviados…).
# ---------------------------------------------------------------------------
_TABLA_ADITIVOS: list[tuple[str, str, str, list[str]]] = [
    # --- Colorantes ---
    ("102", "Tartrazina", "Colorante", ["amarillo 5", "fd&c amarillo 5"]),
    ("110", "Amarillo ocaso FCF", "Colorante",
     ["amarillo ocaso", "amarillo crepusculo", "sunset yellow", "amarillo 6"]),
    ("129", "Rojo allura AC", "Colorante", ["rojo allura", "rojo 40", "allura red"]),
    ("133", "Azul brillante FCF", "Colorante", ["azul brillante", "azul 1"]),
    ("124", "Rojo Ponceau 4R", "Colorante", ["ponceau", "rojo cochinilla", "rojo 4r"]),
    ("150a", "Caramelo natural (clase I)", "Colorante", ["caramelo clase i", "caramelo natural"]),
    ("150c", "Caramelo amónico (clase III)", "Colorante", ["caramelo clase iii"]),
    ("150d", "Caramelo sulfito amónico (clase IV)", "Colorante",
     ["caramelo clase iv", "caramelo iv", "color caramelo"]),
    ("160a", "Betacaroteno", "Colorante", ["beta caroteno", "caroteno"]),
    ("160b", "Achiote (annato)", "Colorante", ["achiote", "annato", "annatto", "bixina", "urucum"]),
    ("160c", "Oleorresina de páprika", "Colorante", ["paprika", "oleorresina de paprika", "pimenton"]),
    ("171", "Dióxido de titanio", "Colorante", ["dioxido de titanio"]),
    # --- Conservantes ---
    ("200", "Ácido sórbico", "Conservante", ["acido sorbico"]),
    ("202", "Sorbato de potasio", "Conservante", ["sorbato de potasio", "sorbato"]),
    ("210", "Ácido benzoico", "Conservante", ["acido benzoico"]),
    ("211", "Benzoato de sodio", "Conservante", ["benzoato de sodio", "benzoato sodico", "benzoato"]),
    ("212", "Benzoato de potasio", "Conservante", ["benzoato de potasio"]),
    ("250", "Nitrito de sodio", "Conservante", ["nitrito de sodio", "nitrito sodico"]),
    ("251", "Nitrato de sodio", "Conservante", ["nitrato de sodio"]),
    ("280", "Ácido propiónico", "Conservante", ["acido propionico"]),
    ("281", "Propionato de sodio", "Conservante", ["propionato de sodio"]),
    ("282", "Propionato de calcio", "Conservante", ["propionato de calcio"]),
    # --- Sulfitos (además son alérgeno) ---
    ("220", "Dióxido de azufre", "Conservante", ["dioxido de azufre", "anhidrido sulfuroso"]),
    ("223", "Metabisulfito de sodio", "Conservante", ["metabisulfito de sodio", "metabisulfito sodico"]),
    ("224", "Metabisulfito de potasio", "Conservante", ["metabisulfito de potasio"]),
    # --- Reguladores de acidez / acidulantes ---
    ("260", "Ácido acético", "Regulador de acidez", ["acido acetico"]),
    ("270", "Ácido láctico", "Regulador de acidez", ["acido lactico"]),
    ("296", "Ácido málico", "Regulador de acidez", ["acido malico"]),
    ("330", "Ácido cítrico", "Regulador de acidez", ["acido citrico"]),
    ("331", "Citrato de sodio", "Regulador de acidez", ["citrato de sodio", "citrato sodico"]),
    ("334", "Ácido tartárico", "Regulador de acidez", ["acido tartarico"]),
    ("338", "Ácido fosfórico", "Regulador de acidez", ["acido fosforico"]),
    ("339", "Fosfato de sodio", "Regulador de acidez", ["fosfato de sodio"]),
    ("341", "Fosfato tricálcico", "Regulador de acidez", ["fosfato tricalcico", "fosfato tricálcico"]),
    ("500", "Bicarbonato de sodio", "Regulador de acidez",
     ["bicarbonato de sodio", "bicarbonato sodico", "carbonato de sodio"]),
    ("501", "Carbonato de potasio", "Regulador de acidez", ["carbonato de potasio"]),
    # --- Antiaglomerantes ---
    ("341iii", "Fosfato tricálcico", "Antiaglomerante", []),  # alterno; 341 ya cubre el nombre
    ("470", "Estearato de calcio", "Antiaglomerante", ["estearato de calcio", "estearato"]),
    ("551", "Dióxido de silicio", "Antiaglomerante", ["dioxido de silicio", "silice", "dioxido de silice"]),
    ("552", "Silicato de calcio", "Antiaglomerante", ["silicato de calcio"]),
    ("554", "Silicato de sodio y aluminio", "Antiaglomerante", ["silicato de sodio y aluminio"]),
    # --- Potenciadores del sabor ---
    ("621", "Glutamato monosódico", "Potenciador del sabor",
     ["glutamato monosodico", "glutamato de sodio", "gms", "msg", "glutamato"]),
    ("627", "Guanilato de sodio", "Potenciador del sabor",
     ["guanilato de sodio", "guanilato disodico", "guanilato"]),
    ("631", "Inosinato de sodio", "Potenciador del sabor",
     ["inosinato de sodio", "inosinato disodico", "inosinato"]),
    ("635", "Ribonucleótidos de sodio", "Potenciador del sabor",
     ["ribonucleotidos de sodio", "ribonucleotidos disodicos", "ribonucleotidos"]),
    # --- Emulsionantes / estabilizantes / espesantes / gelificantes ---
    ("322", "Lecitina", "Emulsionante",
     ["lecitina", "lecitina de soya", "lecitina de soja",
      # "lectina" (sin la i) es un error de tipeo muy común por "lecitina".
      "lectina", "lectina de soya", "lectina de soja"]),
    ("471", "Mono y diglicéridos de ácidos grasos", "Emulsionante",
     ["mono y digliceridos", "monogliceridos", "mono-digliceridos", "monoglicerido",
      "monoestearato de glicerol", "monoestarato de glicerol", "monoestearato"]),
    ("481", "Estearoil-2-lactilato de sodio", "Emulsionante",
     ["estearoil lactilato de sodio", "estearoil-2-lactilato de sodio",
      "estearoil 2 lactilato de sodio", "estearoil lactilato", "ssl"]),
    ("412", "Goma guar", "Espesante", ["goma guar"]),
    ("415", "Goma xantana", "Espesante", ["goma xantana", "xantana", "goma xantan"]),
    ("414", "Goma arábiga", "Estabilizante", ["goma arabiga"]),
    ("440", "Pectina", "Gelificante", ["pectina"]),
    ("407", "Carragenina", "Espesante", ["carragenina", "carrageno", "carragenano"]),
    ("1400", "Almidón modificado", "Estabilizante",
     ["almidon modificado", "almidón modificado", "almidon pregelatinizado"]),
    # --- Antioxidantes ---
    ("300", "Ácido ascórbico", "Antioxidante", ["acido ascorbico", "vitamina c"]),
    ("301", "Ascorbato de sodio", "Antioxidante", ["ascorbato de sodio"]),
    ("306", "Tocoferoles", "Antioxidante", ["tocoferoles", "vitamina e"]),
    ("320", "BHA", "Antioxidante", ["bha", "butilhidroxianisol"]),
    ("321", "BHT", "Antioxidante", ["bht", "butilhidroxitolueno"]),
    # --- Edulcorantes ---
    ("950", "Acesulfame de potasio", "Edulcorante", ["acesulfame k", "acesulfame de potasio", "acesulfame"]),
    ("951", "Aspartame", "Edulcorante", ["aspartame", "aspartamo"]),
    ("952", "Ciclamato de sodio", "Edulcorante", ["ciclamato", "ciclamato de sodio"]),
    ("954", "Sacarina", "Edulcorante", ["sacarina"]),
    ("955", "Sucralosa", "Edulcorante", ["sucralosa"]),
    ("960", "Glucósidos de esteviol (estevia)", "Edulcorante", ["estevia", "stevia", "glucosidos de esteviol"]),
]


def _construir_indices() -> dict[str, dict]:
    """Índice de búsqueda: clave normalizada (nombre/sinónimo) → datos del aditivo."""
    indice: dict[str, dict] = {}
    for ins, nombre, funcion, sinonimos in _TABLA_ADITIVOS:
        datos = {"nombre": nombre, "funcion": funcion, "ins": ins.rstrip("iv") or ins}
        # El INS "real" para mostrar es el numérico base (621, 150d…), sin sufijos internos.
        datos["ins"] = re.match(r"\d+[a-d]?", ins).group(0) if re.match(r"\d", ins) else ins
        for clave in [nombre, *sinonimos]:
            indice.setdefault(_norm(clave), datos)
    return indice


_INDICE_ADITIVOS = _construir_indices()

# Búsqueda por código INS suelto que el usuario escriba (ej. "INS 621", "E-330", "(551)").
_RE_INS = re.compile(r"\b(?:ins|sin|e)[\s\-]*?(\d{3,4}[a-d]?)\b", re.IGNORECASE)
_POR_INS = {d["ins"]: d for d in _INDICE_ADITIVOS.values()}


def _cargar_base_norma() -> int:
    """Carga los aditivos auto-extraídos de la norma como **respaldo de cola larga**.

    Los lee de `data/aditivos_rtca.json` (lo genera `tools/construir_aditivos.py` a
    partir del RTCA 419-2019). La tabla **curada a mano de arriba SIEMPRE tiene
    prioridad**: un aditivo de la norma solo se añade si su INS y su nombre no están
    ya cubiertos. Si el archivo no existe, el agente sigue con la tabla manual.
    """
    ruta = Path(__file__).resolve().parent.parent / "data" / "aditivos_rtca.json"
    if not ruta.exists():
        return 0
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0  # archivo dañado: el agente no se cae, usa solo la tabla manual
    añadidos = 0
    for ins, info in datos.get("aditivos", {}).items():
        nombre = (info.get("nombre") or "").strip()
        if not nombre:
            continue
        datos_ad = {"nombre": nombre, "funcion": info.get("funcion") or "Aditivo", "ins": ins}
        if ins not in _POR_INS:               # la manual manda: no se pisa un INS conocido
            _POR_INS[ins] = datos_ad
            añadidos += 1
        _INDICE_ADITIVOS.setdefault(_norm(nombre), datos_ad)  # ni un nombre conocido
    return añadidos


_ADITIVOS_NORMA = _cargar_base_norma()


# ---------------------------------------------------------------------------
# Alérgenos: patrón en el nombre del ingrediente → alérgeno obligatorio
# (se evalúa sobre el texto completo del ingrediente, sin acentos)
# ---------------------------------------------------------------------------
# value del enum Alergeno (no se importa para no acoplar; el llamador mapea).
# Importante: las palabras cortas llevan límites de palabra (\b...\b) para no coincidir
# DENTRO de otra palabra (p. ej. "nata" coincidía dentro de "carboNATAda" → falso "leche").
_PATRONES_ALERGENO: list[tuple[str, str]] = [
    ("trigo",     r"\btrigo\b|gluten|\bsemola\b|\bcebada\b|\bmalta\b|\bcenteno\b|espelta"),
    ("leche",     r"\bleche\b|lactosa|lacteo|suero de leche|caseina|caseinato|mantequilla|"
                  r"crema de leche|\bnata\b|yogur|cuajada|\bqueso\b"),
    ("huevo",     r"\bhuevo\b|clara de huevo|\byema\b|albumina|ovoalbumina"),
    ("soya",      r"\bsoya\b|\bsoja\b|lecitina de soya|lecitina de soja|proteina de soya|"
                  r"edamame|tofu"),
    ("maní",      r"\bmani\b|cacahuat|cacahuet|peanut"),
    ("nueces",    r"\bnuez\b|nueces|almendra|avellana|maranon|anacardo|pistacho|"
                  r"pecana|macadamia|castana"),
    ("pescado",   r"\bpescado\b|anchoa|\batun\b|bacalao|\bsalmon\b|sardina|merluza|tilapia|surimi"),
    ("crustáceos", r"crustace|camaron|langosta|cangrejo|langostino|\bgamba\b|marisco"),
    # Solo agentes sulfitantes reales: NO la palabra "sulfito" suelta (evita falsos
    # positivos como "Caramelo sulfito amónico", que no declara sulfitos).
    ("sulfitos",  r"metabisulfito|bisulfito|sulfito de (sodio|potasio|calcio|amonio)|"
                  r"dioxido de azufre|anhidrido sulfuroso|\bso2\b|\bsulfuroso\b"),
]
_PATRONES_ALERGENO_COMP = [(a, re.compile(p, re.IGNORECASE)) for a, p in _PATRONES_ALERGENO]


# ---------------------------------------------------------------------------
# Correcciones ortográficas de términos de alimentos comunes
# (clave normalizada sin acento → forma correcta para mostrar)
# ---------------------------------------------------------------------------
_CORRECCIONES: dict[str, str] = {
    "maiz": "maíz", "mais": "maíz", "mixtamalizado": "nixtamalizado",
    "azucar": "azúcar", "azucares": "azúcares", "almidon": "almidón",
    "fecula": "fécula", "proteina": "proteína", "proteinas": "proteínas",
    "hidrolizada": "hidrolizada", "dioxido": "dióxido", "sodico": "sódico",
    "sodio": "sodio", "citrico": "cítrico", "citrica": "cítrica",
    "lactico": "láctico", "lactica": "láctica", "malico": "málico",
    "fosforico": "fosfórico", "ascorbico": "ascórbico", "sorbico": "sórbico",
    "benzoico": "benzoico", "organico": "orgánico", "organica": "orgánica",
    "sasonador": "sazonador", "sazonador": "sazonador", "limon": "limón",
    "jamon": "jamón", "anis": "anís", "sesamo": "sésamo", "oregano": "orégano",
    "cafe": "café", "te": "té", "pure": "puré", "platano": "plátano",
    "manteca": "manteca", "naturalesy": "naturales", "artificialesy": "artificiales",
    "vainilla": "vainilla", "achiote": "achiote", "paprika": "páprika",
    "yodada": "yodada", "tricalcico": "tricálcico", "tricalcica": "tricálcica",
    "solidos": "sólidos", "solido": "sólido", "anadidos": "añadidos",
    "anadido": "añadido", "anadida": "añadida", "anadidas": "añadidas",
    "anejo": "añejo", "pina": "piña", "frijol": "frijol", "frijoles": "frijoles",
    "butirica": "butírica", "butirico": "butírico", "chipas": "chispas",
    "descremada": "descremada", "cacao": "cacao", "cafeina": "cafeína",
    "carbonatada": "carbonatada", "fosforico": "fosfórico",
}


def corregir_ortografia(nombre: str) -> str:
    """Corrige acentos/ortografía de un nombre de ingrediente, palabra por palabra.

    Solo toca términos conocidos del vocabulario de alimentos; lo demás se deja
    igual. No cambia mayúsculas iniciales del usuario salvo limpiar espacios.

    >>> corregir_ortografia("Maiz mixtamalizado")
    'Maíz nixtamalizado'
    >>> corregir_ortografia("acido citrico")
    'ácido cítrico'
    """
    if not nombre:
        return nombre

    def _corr_palabra(palabra: str) -> str:
        # Conserva signos pegados (comas, paréntesis) alrededor del núcleo.
        m = re.match(r"^(\W*)(.*?)(\W*)$", palabra, re.DOTALL)
        pre, nucleo, post = m.group(1), m.group(2), m.group(3)
        correcta = _CORRECCIONES.get(_norm(nucleo))
        if correcta is None:
            return palabra
        # Respeta si el usuario lo escribió con inicial mayúscula.
        if nucleo[:1].isupper():
            correcta = correcta[:1].upper() + correcta[1:]
        return pre + correcta + post

    return re.sub(r"\s+", " ", " ".join(_corr_palabra(p) for p in nombre.split())).strip()


def identificar_aditivo(texto: str) -> dict | None:
    """Si `texto` es (o contiene) un aditivo conocido, devuelve sus datos RTCA.

    Reconoce por **nombre/sinónimo** o por **código INS** escrito por el usuario
    (ej. "INS 211", "E-330", "(551)"). Devuelve dict con nombre canónico, función
    e INS, listo para construir un Aditivo; o None si no es un aditivo conocido.

    >>> identificar_aditivo("glutamato monosodico")["funcion"]
    'Potenciador del sabor'
    >>> identificar_aditivo("INS 102")["nombre"]
    'Tartrazina'
    """
    if not texto or not texto.strip():
        return None
    clave = _norm(texto)

    # 1) Coincidencia exacta por nombre/sinónimo.
    if clave in _INDICE_ADITIVOS:
        return dict(_INDICE_ADITIVOS[clave])

    # 2) Código INS suelto dentro del texto.
    m = _RE_INS.search(texto)
    if m and m.group(1) in _POR_INS:
        return dict(_POR_INS[m.group(1)])

    # 3) Coincidencia por contención (el nombre del aditivo aparece dentro del texto).
    #    Se prueba del sinónimo más largo al más corto para evitar falsos cortos.
    for sin_clave in sorted(_INDICE_ADITIVOS, key=len, reverse=True):
        if len(sin_clave) >= 4 and re.search(rf"\b{re.escape(sin_clave)}\b", clave):
            return dict(_INDICE_ADITIVOS[sin_clave])

    # 4) Tolerancia a errores de tipeo LEVES (p. ej. "monoestarato", "lectina").
    #    Se limita a nombres largos y a una similitud alta para no inventar
    #    coincidencias en ingredientes comunes (regla de cero inventos).
    if len(clave) >= 8:
        candidatas = [k for k in _INDICE_ADITIVOS if len(k) >= 8]
        cercanas = difflib.get_close_matches(clave, candidatas, n=1, cutoff=0.88)
        if cercanas:
            return dict(_INDICE_ADITIVOS[cercanas[0]])
    return None


def detectar_alergenos(nombres: list[str]) -> list[str]:
    """Lista de alérgenos (values del enum Alergeno) presentes en esos ingredientes.

    Escanea el texto completo de cada ingrediente; un mismo alérgeno se reporta una
    sola vez y se conserva el orden del listado oficial.

    >>> detectar_alergenos(["harina de trigo", "solidos de leche", "caseinato de sodio"])
    ['trigo', 'leche']
    """
    blob = " ; ".join(_sin_acentos(n).lower() for n in nombres if n)
    encontrados: list[str] = []
    for alergeno, patron in _PATRONES_ALERGENO_COMP:
        if patron.search(blob) and alergeno not in encontrados:
            encontrados.append(alergeno)
    return encontrados


# Marcas de motivo: por qué se detectó cada alérgeno (para explicárselo al usuario).
def motivos_alergeno(nombres: list[str]) -> dict[str, list[str]]:
    """Para cada alérgeno detectado, qué ingredientes lo dispararon (para transparencia)."""
    motivos: dict[str, list[str]] = {}
    for nombre in nombres:
        if not nombre:
            continue
        plano = _sin_acentos(nombre).lower()
        for alergeno, patron in _PATRONES_ALERGENO_COMP:
            if patron.search(plano):
                motivos.setdefault(alergeno, [])
                if nombre not in motivos[alergeno]:
                    motivos[alergeno].append(nombre)
    return motivos


def separar_ingredientes(texto: str) -> list[str]:
    """Parte una lista de ingredientes pegada en elementos sueltos.

    Acepta separación por saltos de línea, comas o punto y coma, y **aplana los
    paréntesis** (un ingrediente compuesto declara sus sub-ingredientes), de modo
    que "sazonador (queso, sal, INS 621)" se vuelve cuatro elementos. Si el texto
    es un solo ingrediente con cantidad ("Mora 2 kg"), lo devuelve tal cual.

    >>> separar_ingredientes("harina de trigo, azucar, sal")
    ['harina de trigo', 'azucar', 'sal']
    """
    plano = texto.replace("(", ", ").replace(")", ", ")
    partes = re.split(r"[\n;,]+", plano)
    limpios = [p.strip(" \t.·-") for p in partes]
    return [p for p in limpios if p]


# ---------------------------------------------------------------------------
# Prueba rápida:  python src/conocimiento.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    caso = [
        "Maiz mixtamalizado", "aceite vegetal", "queso", "maltodextrina",
        "sal yodada", "glutamato monosodico", "harina de trigo", "acido citrico",
        "solidos de leche", "amarillo ocaso FCF", "dioxido de silicio", "tartrazina",
        "guanilato de sodio", "inosinato de sodio", "leche entera", "caramelo clase IV",
        "caseinato de sodio", "achiote", "INS 211",
    ]
    print("=== Clasificación de ingredientes ===")
    for ing in caso:
        ad = identificar_aditivo(ing)
        if ad:
            print(f"  ADITIVO  {ing!r:35} → {ad['funcion']} ({ad['nombre']}, INS {ad['ins']})")
        else:
            print(f"  materia  {ing!r:35} → {corregir_ortografia(ing)}")
    print("\nAlérgenos detectados:", detectar_alergenos(caso))
    print("Motivos:", motivos_alergeno(caso))
