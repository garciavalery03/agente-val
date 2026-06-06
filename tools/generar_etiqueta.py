"""
generar_etiqueta.py — Render de la etiqueta como IMAGEN (canal de salida visual)
================================================================================

Toma los datos del producto (mismo JSON que validan las otras herramientas) y
dibuja una etiqueta en PNG, **basada en los modelos de referencia** de
`data/etiquetas/Ejemplo/`:

    * preenvasado        → ETIQUETA_PREENVASADO.png
    * semisolido         → ETIQUETA_ALIMENTOS_SEMISOLIDOS.png  (incluye Peso escurrido)
    * bebida_alcoholica  → ETIQUETA_BEBIDA_ALCOHOLICA.png      (incluye % Alc y Advertencia)

Replica la estructura de esos modelos: título centrado, "Marca", dos columnas
(Ingredientes | Instrucciones) y el bloque inferior con los datos obligatorios.
Para bebidas alcohólicas añade el grado alcohólico junto al contenido neto y la
advertencia legal obligatoria.

Solo genera la imagen si la etiqueta **CUMPLE** el RTCA (misma regla de salida
que `enviar_etiqueta.py`); con `--forzar` la dibuja aunque falten datos (útil
para previsualizar en desarrollo).

Uso:
    python tools/generar_etiqueta.py data/entrada/producto.json
    cat producto.json | python tools/generar_etiqueta.py - --salida data/etiquetas/mi_etiqueta.png
    python tools/generar_etiqueta.py producto.json --forzar

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from src.modelos import (  # noqa: E402
    ADVERTENCIA_ALCOHOL,
    ErrorDominio,
    Etiqueta,
    EtiquetaInvalida,
    TipoProducto,
)

# --- Paleta y lienzo (inspirados en los modelos de data/etiquetas/Ejemplo/) ---
ANCHO, ALTO = 1200, 680
COLOR_FONDO = (244, 239, 225)      # pergamino claro
COLOR_BORDE = (58, 51, 41)         # marrón oscuro de los marcos
COLOR_TEXTO = (40, 35, 28)
COLOR_TENUE = (120, 110, 95)
COLOR_RESALTE = (240, 226, 150)    # amarillo del recuadro "Advertencia"
MARGEN = 34

_DIR_FONTS = Path("C:/Windows/Fonts")


def _fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    """Carga una fuente TrueType de Windows; si falla, usa la de Pillow."""
    try:
        return ImageFont.truetype(str(_DIR_FONTS / nombre), tam)
    except OSError:
        return ImageFont.load_default()


def _fuente_que_cabe(texto: str, nombre_ttf: str, ancho_max: int,
                     tam_max: int = 52, tam_min: int = 24) -> ImageFont.FreeTypeFont:
    """Mayor tamaño de `nombre_ttf` con el que `texto` cabe en `ancho_max` px.

    Evita que un nombre de producto largo (p. ej. 'BEBIDA CARBONATADA SABOR A
    COCA-COLA') se desborde del marco: reduce el título hasta que entre.
    """
    medidor = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tam = tam_max
    while tam > tam_min:
        fuente = _fuente(nombre_ttf, tam)
        if medidor.textlength(texto, font=fuente) <= ancho_max:
            return fuente
        tam -= 2
    return _fuente(nombre_ttf, tam_min)


# Times New Roman da el aire serif de los modelos de ejemplo.
F_TITULO = _fuente("timesbd.ttf", 52)
F_SUBTITULO = _fuente("timesbd.ttf", 24)
F_ETIQUETA = _fuente("timesbd.ttf", 22)   # rótulos en negrita
F_TEXTO = _fuente("times.ttf", 22)
F_PEQUENA = _fuente("times.ttf", 19)


def _envolver(draw: ImageDraw.ImageDraw, texto: str, fuente, ancho_max: int) -> list[str]:
    """Parte `texto` en líneas que caben en `ancho_max` px."""
    palabras = texto.split()
    lineas: list[str] = []
    actual = ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=fuente) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _bloque(draw, x, y, texto, fuente, ancho_max, alto_linea, color=COLOR_TEXTO):
    """Dibuja texto envuelto desde (x, y). Devuelve la y siguiente."""
    for linea in _envolver(draw, texto, fuente, ancho_max):
        draw.text((x, y), linea, font=fuente, fill=color)
        y += alto_linea
    return y


def _slug(nombre: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")
    return base or "etiqueta"


def dibujar_etiqueta(etiqueta: Etiqueta) -> Image.Image:
    """Renderiza la etiqueta a una imagen PIL, con **altura dinámica**.

    En vez de un lienzo fijo (que se desbordaba con listas largas de ingredientes),
    primero **mide** cuánto ocupa cada bloque y luego dimensiona el alto del lienzo
    para que todo quepa sin encimarse. Si la lista de ingredientes es muy larga,
    usa una fuente un poco menor para mantener la etiqueta compacta y legible.
    """
    p = etiqueta.producto
    es_alcohol = p.tipo == TipoProducto.BEBIDA_ALCOHOLICA

    # Lienzo de medición (no se dibuja): permite calcular el envoltorio del texto.
    medidor = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    x_div = ANCHO / 2
    col_izq_x = MARGEN + 14
    col_der_x = int(x_div) + 22
    ancho_col = int(x_div) - MARGEN - 40

    # --- Medición de las columnas (ingredientes | instrucciones) ---
    ingredientes = p.lista_ingredientes_texto() or "—"
    # Listas muy largas → fuente menor para no estirar la etiqueta de más.
    f_ing = F_TEXTO if len(ingredientes) <= 600 else F_PEQUENA
    li_ing = 27 if f_ing is F_TEXTO else 23
    lineas_ing = _envolver(medidor, ingredientes, f_ing, ancho_col)

    contiene = ("Contiene: " + ", ".join(a.value for a in p.alergenos)) if p.alergenos else None
    lineas_contiene = _envolver(medidor, contiene, F_ETIQUETA, ancho_col) if contiene else []

    titulo_instr = "INSTRUCCIONES PARA EL USO / CONSERVACIÓN O PREPARACIÓN:"
    lineas_ti = _envolver(medidor, titulo_instr, F_ETIQUETA, ancho_col)
    lineas_instr = _envolver(medidor, p.instrucciones_efectivas(), F_TEXTO, ancho_col)

    alto_izq = 32 + len(lineas_ing) * li_ing + (8 + len(lineas_contiene) * 27 if contiene else 0)
    alto_der = len(lineas_ti) * 28 + 6 + len(lineas_instr) * 27
    alto_cols = max(alto_izq, alto_der, 120)

    y_top = 128
    y_cols = y_top + 16
    y_div = y_cols + alto_cols + 14

    # --- Medición del bloque inferior ---
    cn = "Contenido neto: " + (p.contenido_neto_texto() or "______")
    if es_alcohol and p.grado_alcoholico:
        cn += f"     % Alc: {p.grado_alcoholico}"
    lineas_inf_izq = [
        cn,
        f"Registro Sanitario: {etiqueta.registro_sanitario or '______'}",
        f"Lote: {etiqueta.lote or '______'}",
        f"Fecha de vencimiento: {etiqueta.fecha_vencimiento or 'DD/MM/AA'}",
    ]
    if etiqueta.peso_escurrido:
        lineas_inf_izq.append(f"Peso escurrido: {etiqueta.peso_escurrido}")
    alto_inf_izq = len(lineas_inf_izq) * 30

    resp = f"{p.responsable} — {p.direccion_responsable}".strip(" —")
    lineas_resp = _envolver(medidor, resp, F_PEQUENA, ancho_col + 10)
    alto_inf_der = 28 + len(lineas_resp) * 23
    lineas_adv: list[str] = []
    if es_alcohol:
        lineas_adv = _envolver(medidor, f"Advertencia: {ADVERTENCIA_ALCOHOL}", F_PEQUENA, ancho_col)
        alto_inf_der += 8 + 12 + len(lineas_adv) * 22

    y_bottom = y_div + 16
    # +44 reserva el renglón de "País de Origen" al pie, sin encimarse.
    alto = max(ALTO, int(y_bottom + max(alto_inf_izq, alto_inf_der) + 44 + MARGEN))

    # --- Lienzo definitivo ---
    img = Image.new("RGB", (ANCHO, alto), COLOR_FONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([12, 12, ANCHO - 12, alto - 12], outline=COLOR_BORDE, width=3)
    d.rectangle([20, 20, ANCHO - 20, alto - 20], outline=COLOR_BORDE, width=1)

    # --- Título + Marca (centrados) ---
    # El título se reduce solo si el nombre no cabe en el ancho del marco.
    f_titulo = _fuente_que_cabe(p.nombre.upper(), "timesbd.ttf", ANCHO - 2 * MARGEN - 16)
    d.text((ANCHO / 2, 58), p.nombre.upper(), font=f_titulo, fill=COLOR_TEXTO, anchor="mm")
    # Marca comercial propia; si no se indicó, cae al responsable o al nombre.
    marca = p.marca or p.responsable or p.nombre
    d.text((ANCHO / 2, 104), f"Marca: {marca}", font=F_SUBTITULO, fill=COLOR_TEXTO, anchor="mm")

    # --- Líneas guía ---
    d.line([(MARGEN, y_top), (ANCHO - MARGEN, y_top)], fill=COLOR_BORDE, width=2)
    d.line([(x_div, y_top + 6), (x_div, y_div)], fill=COLOR_BORDE, width=1)
    d.line([(MARGEN, y_div), (ANCHO - MARGEN, y_div)], fill=COLOR_BORDE, width=2)

    # --- Columna izquierda: Ingredientes (+ Contiene) ---
    y = y_cols
    d.text((col_izq_x, y), "INGREDIENTES:", font=F_ETIQUETA, fill=COLOR_TEXTO)
    y += 32
    for linea in lineas_ing:
        d.text((col_izq_x, y), linea, font=f_ing, fill=COLOR_TEXTO)
        y += li_ing
    if contiene:
        y += 8
        for linea in lineas_contiene:
            d.text((col_izq_x, y), linea, font=F_ETIQUETA, fill=COLOR_TEXTO)
            y += 27

    # --- Columna derecha: Instrucciones ---
    y = y_cols
    for linea in lineas_ti:
        d.text((col_der_x, y), linea, font=F_ETIQUETA, fill=COLOR_TEXTO)
        y += 28
    y += 6
    for linea in lineas_instr:
        d.text((col_der_x, y), linea, font=F_TEXTO, fill=COLOR_TEXTO)
        y += 27

    # --- Bloque inferior izquierdo: datos obligatorios ---
    y = y_bottom
    for linea in lineas_inf_izq:
        d.text((col_izq_x, y), linea, font=F_TEXTO, fill=COLOR_TEXTO)
        y += 30

    # --- Bloque inferior derecho: responsable y advertencia ---
    y = y_bottom
    d.text((col_der_x, y), "Nombre y Dirección del Fabricante / Distribuidor:",
           font=F_ETIQUETA, fill=COLOR_TEXTO)
    y += 28
    for linea in lineas_resp:
        d.text((col_der_x, y), linea, font=F_PEQUENA, fill=COLOR_TEXTO)
        y += 23
    if es_alcohol:
        y += 8
        alto_caja = 12 + len(lineas_adv) * 22
        d.rectangle([col_der_x - 6, y - 4, ANCHO - MARGEN - 8, y + alto_caja - 4],
                    fill=COLOR_RESALTE, outline=COLOR_BORDE, width=1)
        yy = y + 4
        for linea in lineas_adv:
            d.text((col_der_x, yy), linea, font=F_PEQUENA, fill=COLOR_TEXTO)
            yy += 22

    # --- País de origen (al pie, alineado a la derecha) ---
    d.text((ANCHO - MARGEN - 12, alto - MARGEN - 6),
           f"País de Origen: {p.pais_origen or '______'}",
           font=F_TEXTO, fill=COLOR_TEXTO, anchor="rs")

    return img


def generar(datos: dict, salida: Path | None = None, forzar: bool = False) -> dict:
    """Valida y, si cumple (o con `forzar`), genera el PNG. Devuelve dict JSON-able."""
    try:
        etiqueta = Etiqueta.from_dict(datos)
    except (EtiquetaInvalida, ErrorDominio) as exc:
        return {"ok": False, "generada": False, "error": f"Datos inválidos: {exc}"}

    resultado = etiqueta.validar()
    if not resultado.cumple and not forzar:
        return {
            "ok": True,
            "generada": False,
            "aprobada": False,
            "motivo": "La etiqueta no cumple el RTCA; no se genera la imagen. "
                      "Usa --forzar para previsualizar.",
            "validacion": resultado.to_dict(),
        }

    if salida is None:
        from config import DIR_ETIQUETAS  # import diferido: usa las rutas del proyecto
        DIR_ETIQUETAS.mkdir(parents=True, exist_ok=True)
        salida = DIR_ETIQUETAS / f"{_slug(etiqueta.producto.nombre)}.png"
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    img = dibujar_etiqueta(etiqueta)
    img.save(salida)

    return {
        "ok": True,
        "generada": True,
        "aprobada": resultado.cumple,
        "archivo": str(salida),
        "tipo": etiqueta.producto.tipo.value,
        "observaciones": resultado.observaciones,
    }


def _leer_entrada(arg: str) -> dict:
    # Leer bytes y decodificar UTF-8: en Windows sys.stdin usa cp1252 y rompería
    # los acentos del JSON (ej. "Azúcar").
    crudo = (sys.stdin.buffer.read().decode("utf-8") if arg == "-"
             else Path(arg).read_text(encoding="utf-8"))
    return json.loads(crudo)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    argv = sys.argv[1:]
    if not argv:
        print(json.dumps(
            {"ok": False, "error": "Uso: generar_etiqueta.py <archivo.json|-> "
                                   "[--salida ruta.png] [--forzar]"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    fuente = argv[0]
    forzar = "--forzar" in argv
    salida = None
    if "--salida" in argv:
        i = argv.index("--salida")
        if i + 1 < len(argv):
            salida = argv[i + 1]

    try:
        datos = _leer_entrada(fuente)
    except FileNotFoundError:
        print(json.dumps({"ok": False, "error": f"No existe el archivo: {fuente}"},
                         ensure_ascii=False))
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"JSON inválido: {exc}"},
                         ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(generar(datos, salida=salida, forzar=forzar),
                     ensure_ascii=False, indent=2))
