"""
construir_aditivos.py — Genera la base de aditivos desde la norma (RTCA 419-2019)
================================================================================

Lee el Anexo A del PDF `data/RAG/RTCA_No.-419-2019-ADITIVOS-ALIMENTARIOS.pdf`
(la *Lista de Aditivos Alimentarios Permitidos*) y construye una tabla
**INS → (nombre, función)** que sirve de **respaldo de cola larga** para el
reconocimiento de aditivos del agente.

Importante (honestidad de datos):
    * La extracción usa `pdfplumber` para aislar la **columna "Función"** de cada
      tabla; aun así, muchos aditivos son **multifunción** y la norma no marca una
      función "principal" única. Por eso la función aquí es **best-effort** (la más
      votada entre todas las categorías de alimento donde aparece el aditivo).
    * La fuente de **calidad** sigue siendo la tabla curada a mano de
      `src/conocimiento.py`, que **siempre tiene prioridad**. Este JSON solo cubre
      los aditivos que NO están en esa tabla.
    * No se inventan dosis: no se extraen aquí (dependen de la categoría de alimento).

Salida: `data/aditivos_rtca.json`.

Uso:
    python tools/construir_aditivos.py

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_PDF = _RAIZ / "data" / "RAG" / "RTCA_No.-419-2019-ADITIVOS-ALIMENTARIOS.pdf"
_SALIDA = _RAIZ / "data" / "aditivos_rtca.json"

# Texto de la columna "Función" → categoría funcional del RTCA (orden = prioridad).
# Se evalúa de arriba abajo: el primer término que aparezca define la función.
_FUNCIONES: list[tuple[str, str]] = [
    ("retención de color", "Estabilizador del color"),
    ("colorante", "Colorante"),
    ("conservador", "Conservante"),
    ("conservante", "Conservante"),
    ("potenciador", "Potenciador del sabor"),
    ("realzador", "Potenciador del sabor"),
    ("regulador", "Regulador de acidez"),
    ("acidulante", "Regulador de acidez"),
    ("acidez", "Regulador de acidez"),
    ("edulcorante", "Edulcorante"),
    ("antioxidante", "Antioxidante"),
    ("emulsion", "Emulsionante"),
    ("gelificante", "Gelificante"),
    ("espesante", "Espesante"),
    ("estabiliz", "Estabilizante"),
    ("antiaglomer", "Antiaglomerante"),
    ("antiapelmaz", "Antiaglomerante"),
    ("humectante", "Humectante"),
    ("secuestrante", "Secuestrante"),
    ("leudante", "Leudante"),
    ("gasificante", "Leudante"),
    ("endurecedor", "Endurecedor"),
    ("espumante", "Espumante"),
    ("antiespumante", "Antiespumante"),
    ("glaseado", "Agente de glaseado"),
    ("tratamiento de las harinas", "Tratamiento de harinas"),
    ("propelente", "Propelente"),
    ("propulsor", "Propelente"),
    ("gasificante", "Leudante"),
    ("sabor", "Potenciador del sabor"),
]

# Acrónimos que title() rompe; se restauran tras normalizar el nombre.
_ACRONIMOS = {"Fcf": "FCF", "Bha": "BHA", "Bht": "BHT", "Edta": "EDTA",
              "Ins": "INS", "Fd&C": "FD&C", " Iv": " IV", " Iii": " III",
              " Ii": " II", " Vi": " VI"}


def _clasificar_funcion(texto: str | None) -> str | None:
    """Mapea el texto de la columna Función a una categoría funcional del RTCA."""
    if not texto:
        return None
    bajo = texto.lower()
    for clave, funcion in _FUNCIONES:
        if clave in bajo:
            return funcion
    return None


def _limpiar_nombre(crudo: str) -> str:
    """Normaliza un nombre de aditivo en MAYÚSCULAS a 'Tipo Título', con acrónimos."""
    nombre = re.sub(r"\s+", " ", crudo.replace("\n", " ")).strip(" -·,")
    nombre = nombre.title()
    for malo, bueno in _ACRONIMOS.items():
        nombre = nombre.replace(malo, bueno)
    return nombre


def _indice_columna(encabezado: list, subcadena: str) -> int | None:
    """Índice de la columna cuyo encabezado contiene `subcadena` (sin importar caso)."""
    for j, celda in enumerate(encabezado):
        if celda and subcadena.lower() in celda.lower():
            return j
    return None


def construir() -> dict:
    """Extrae la tabla de aditivos del PDF. Devuelve el dict que se guardará."""
    import pdfplumber  # import diferido: solo se necesita al regenerar la base

    if not _PDF.exists():
        raise FileNotFoundError(f"No se encontró la norma: {_PDF}")

    votos_funcion: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    votos_nombre: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    filas_leidas = 0

    with pdfplumber.open(str(_PDF)) as pdf:
        for pg in pdf.pages:
            for tabla in pg.extract_tables():
                i_nom = i_ins = i_fun = None
                for fila in tabla:
                    # Encabezado de la tabla: fija las columnas Denominación / INS / Función.
                    if any(c and "Denominación" in c for c in fila) and \
                       any(c and "Función" in c for c in fila):
                        i_nom = _indice_columna(fila, "Denominación")
                        i_ins = _indice_columna(fila, "INS")
                        i_fun = _indice_columna(fila, "Función")
                        continue
                    if i_ins is None or i_nom is None:
                        continue
                    nom = fila[i_nom] if i_nom < len(fila) else ""
                    ins_celda = fila[i_ins] if i_ins < len(fila) else ""
                    fun = fila[i_fun] if (i_fun is not None and i_fun < len(fila)) else ""
                    if not nom or not ins_celda:
                        continue
                    # INS de 3 o 4 cifras (p. ej. 330, 150a, 331iii, 1400, 1520).
                    m = re.match(r"(\d{3,4}[a-z]{0,4})", str(ins_celda).lower().replace("ª", "a"))
                    nombre = _limpiar_nombre(str(nom))
                    if not m or len(nombre) < 3:
                        continue
                    ins = m.group(1)
                    filas_leidas += 1
                    votos_nombre[ins][nombre] += 1
                    funcion = _clasificar_funcion(fun)
                    if funcion:
                        votos_funcion[ins][funcion] += 1

    aditivos: dict[str, dict] = {}
    for ins, nombres in votos_nombre.items():
        nombre = nombres.most_common(1)[0][0]
        funcion = (votos_funcion[ins].most_common(1)[0][0]
                   if votos_funcion.get(ins) else "Aditivo")
        aditivos[ins] = {"nombre": nombre, "funcion": funcion}

    return {
        "_meta": {
            "fuente": "RTCA 67.04.54:18 (RTCA No. 419-2019), Anexo A",
            "generado_de": _PDF.name,
            "metodo": "pdfplumber + voto por mayoría (best-effort)",
            "nota": "Respaldo de cola larga. La tabla curada de src/conocimiento.py "
                    "tiene prioridad. La función de aditivos multifunción es aproximada.",
            "filas_leidas": filas_leidas,
            "aditivos_unicos": len(aditivos),
        },
        "aditivos": dict(sorted(aditivos.items())),
    }


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"Leyendo {_PDF.name} …")
    datos = construir()
    _SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = datos["_meta"]
    print(f"✓ {meta['aditivos_unicos']} aditivos únicos "
          f"(de {meta['filas_leidas']} filas de tabla) → {_SALIDA.relative_to(_RAIZ)}")
    # Muestra una pequeña verificación.
    muestra = ["330", "102", "200", "954", "1400", "440", "415"]
    for ins in muestra:
        a = datos["aditivos"].get(ins)
        if a:
            print(f"    INS {ins:5} {a['funcion']:22} {a['nombre']}")
