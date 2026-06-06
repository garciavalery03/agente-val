"""
rag.py — Recuperación de documentación técnica (RAG) de ConsulAlim AI
=====================================================================

Indexa los documentos normativos de `data/RAG/` (PDFs del RTCA) y, ante una
consulta, devuelve los fragmentos más relevantes **citando su fuente**
(nombre del PDF y número de página). Así el agente fundamenta sus respuestas
en la norma y NO inventa (principio de cero inventos).

Técnica: TF-IDF (scikit-learn) sobre los fragmentos de texto extraídos con
pypdf. Es el patrón clásico de RAG ligero, sin servicios externos.

Las fuentes EN LÍNEA (archivos .txt con URLs, como `Base_Codex.txt`) NO se
indexan aquí: se consultan en vivo con la herramienta `tools/consultar_codex.py`.

Uso desde código:
    from src.rag import RAG
    rag = RAG().construir()
    for frag in rag.consultar("declaración de aditivos", k=3):
        print(frag["fuente"], frag["pagina"], frag["score"])

Uso por consola:
    python src/rag.py "orden de la lista de ingredientes"

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Carpeta por defecto con los documentos del RAG.
_RAIZ = Path(__file__).resolve().parent.parent
_DIR_RAG = _RAIZ / "data" / "RAG"

# Tamaño de cada fragmento (en caracteres) y solapamiento entre fragmentos.
_TAM_FRAGMENTO = 900
_SOLAPE = 150


def _limpiar(texto: str) -> str:
    """Normaliza espacios y saltos de línea de un texto extraído de PDF."""
    texto = texto.replace("\x00", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.strip()


def _trocear(texto: str, tam: int = _TAM_FRAGMENTO, solape: int = _SOLAPE) -> list[str]:
    """Parte un texto largo en fragmentos con solapamiento."""
    texto = texto.strip()
    if len(texto) <= tam:
        return [texto] if texto else []
    fragmentos: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + tam
        fragmentos.append(texto[inicio:fin])
        inicio = fin - solape
    return fragmentos


class Fragmento:
    """Un trozo de un documento, con su origen para poder citarlo."""

    def __init__(self, texto: str, fuente: str, pagina: int) -> None:
        self.texto = texto
        self.fuente = fuente   # nombre del PDF
        self.pagina = pagina   # número de página (1-based)

    def to_dict(self, score: float | None = None) -> dict:
        d = {"fuente": self.fuente, "pagina": self.pagina, "texto": self.texto}
        if score is not None:
            d["score"] = round(float(score), 4)
        return d


class RAG:
    """Índice TF-IDF sobre los PDFs de documentación técnica."""

    def __init__(self, directorio: str | Path = _DIR_RAG) -> None:
        self.directorio = Path(directorio)
        self.fragmentos: list[Fragmento] = []
        self._vectorizador: TfidfVectorizer | None = None
        self._matriz = None

    # --- construcción del índice -----------------------------------------
    def _leer_pdfs(self) -> list[Fragmento]:
        """Extrae y trocea el texto de todos los PDFs del directorio."""
        fragmentos: list[Fragmento] = []
        if not self.directorio.exists():
            return fragmentos
        for pdf in sorted(self.directorio.glob("*.pdf")):
            try:
                lector = PdfReader(str(pdf))
            except Exception as exc:  # noqa: BLE001 — PDF dañado: avisar y seguir
                print(f"[RAG] No se pudo leer {pdf.name}: {exc}", file=sys.stderr)
                continue
            for n, pagina in enumerate(lector.pages, start=1):
                texto = _limpiar(pagina.extract_text() or "")
                for trozo in _trocear(texto):
                    if len(trozo) >= 40:  # ignora fragmentos triviales
                        fragmentos.append(Fragmento(trozo, pdf.name, n))
        return fragmentos

    def construir(self) -> "RAG":
        """Lee los PDFs y arma la matriz TF-IDF. Devuelve self (encadenable)."""
        self.fragmentos = self._leer_pdfs()
        if not self.fragmentos:
            raise RuntimeError(
                f"No se encontraron PDFs con texto en {self.directorio}. "
                "Verifica que data/RAG/ tenga las normas del RTCA."
            )
        self._vectorizador = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
        )
        self._matriz = self._vectorizador.fit_transform(
            f.texto for f in self.fragmentos
        )
        return self

    # --- consulta ---------------------------------------------------------
    def consultar(self, consulta: str, k: int = 3) -> list[dict]:
        """Devuelve los `k` fragmentos más relevantes a la consulta.

        Cada resultado es un dict con: fuente, pagina, texto, score.
        Lanza RuntimeError si el índice aún no se ha construido.
        """
        if self._vectorizador is None or self._matriz is None:
            raise RuntimeError("El índice no está construido: llama a .construir() primero.")
        consulta = (consulta or "").strip()
        if not consulta:
            return []

        vec_consulta = self._vectorizador.transform([consulta])
        similitudes = cosine_similarity(vec_consulta, self._matriz)[0]
        # Índices de los k mejores, de mayor a menor similitud.
        mejores = similitudes.argsort()[::-1][:k]
        resultados: list[dict] = []
        for i in mejores:
            score = float(similitudes[i])
            if score <= 0.0:
                continue
            resultados.append(self.fragmentos[i].to_dict(score))
        return resultados


# --- prueba directa:  python src/rag.py "tu consulta" ----------------------
if __name__ == "__main__":
    # En Windows la consola usa cp1252; forzamos UTF-8 para acentos y '·'.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    consulta = " ".join(sys.argv[1:]) or "declaración de aditivos alimentarios"
    print(f"=== RAG ConsulAlim AI · consulta: {consulta!r} ===\n")
    rag = RAG().construir()
    print(f"Índice: {len(rag.fragmentos)} fragmentos de {rag.directorio}\n")
    resultados = rag.consultar(consulta, k=3)
    if not resultados:
        print("Sin resultados relevantes.")
    for i, r in enumerate(resultados, start=1):
        print(f"[{i}] {r['fuente']} · pág. {r['pagina']} · score {r['score']}")
        vista = r["texto"][:300].replace("\n", " ")
        print(f"    {vista}...\n")
    print("--- JSON ---")
    print(json.dumps(resultados, ensure_ascii=False, indent=2)[:800])
