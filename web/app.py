"""
app.py — Web de ConsulAlim AI: conversación guiada (Streamlit)
=============================================================

Cuando el usuario entra, el agente lo **recibe** según las reglas de
`valery_garcia.md` (bienvenida cálida, empatía, honestidad) y lo guía **paso a
paso** para capturar los datos de su producto, validar la etiqueta contra el
RTCA y entregarle su etiqueta (texto + imagen + correo).

Es una conversación **determinista** (máquina de pasos), no un LLM: el cerebro
de razonamiento del agente es Claude Code; aquí la web solo conduce el diálogo y
ejecuta las herramientas Python del proyecto. Así no se necesita API key.

Correr (desde la raíz del proyecto):
    streamlit run web/app.py

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))
_WEB = Path(__file__).resolve().parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))

from src.modelos import (
    Alergeno, Etiqueta, Producto, TipoProducto, EtiquetaInvalida, ErrorDominio,
)
from src.conocimiento import (
    corregir_ortografia, detectar_alergenos, identificar_aditivo,
    motivos_alergeno, separar_ingredientes,
)
from src.rag import RAG
from tools.enviar_etiqueta import enviar_etiqueta
from tools.generar_etiqueta import generar as generar_imagen
from src.notificar import email_valido

import streamlit.components.v1 as components
from mascota import html_mascota, FRASES


# ===========================================================================
# Textos del agente (siguen el protocolo de valery_garcia.md)
# ===========================================================================
BIENVENIDA = (
    "¡Hola y bienvenida/o! 🌱 Soy **ConsulAlim AI**, tu **Ingeniero de Alimentos "
    "y Consultor de Regulación Sanitaria**. Felicidades por dar el paso de "
    "formalizar tu producto: estoy aquí para ayudarte a crear una etiqueta "
    "**segura y legal** según el RTCA, paso a paso y sin tecnicismos "
    "complicados. ¡Vamos juntos! 💪"
)
P_NOMBRE = "Para empezar, ¿cuál es el **nombre** con el que quieres comercializar tu producto?"
ADVERTENCIA_NOMBRE = (
    "📌 *Nota legal: el nombre debe reflejar la verdadera naturaleza del alimento "
    "y no inducir a engaño sobre su composición (RTCA).*"
)
P_MARCA = (
    "¿Cuál es la **marca** con la que vendes tu producto? (la que va grande en la "
    "etiqueta). Si todavía no tienes marca, escribe **no**."
)
P_TIPO = (
    "¿Qué **tipo** de producto es? Por ejemplo: *preenvasado* (galletas, snacks…), "
    "*semisólido* (mermelada, salsa, crema…) o *bebida alcohólica* (vino, licor…)."
)
P_DESCRIPCION = (
    "Cuéntame brevemente **cómo es** tu producto (ej. *conserva pasteurizada*, "
    "*deshidratado*, *fermentado artesanal*)."
)
P_INGREDIENTES = (
    "Ahora los **ingredientes**, del que más usas al que menos. Puedes escribirlos "
    "**uno por uno** (ej. `Mora 2 kg`) o **pegar la lista completa separada por comas**. "
    "Yo me encargo de **identificar y clasificar los aditivos** (función + INS) y de "
    "**detectar los alérgenos** por ti. Cuando termines, escribe **listo**."
)
P_ADITIVOS = (
    "Ya **identifiqué y clasifiqué** los aditivos que venían en tu lista. ¿Quieres "
    "**añadir** alguno más que no aparezca? Escríbelo por su nombre o su código "
    "(ej. `benzoato de sodio` o `INS 211`). Si no, escribe **no**."
)
P_CONTENIDO = "¿Cuál es el **contenido neto**? (por ejemplo `250 g` o `750 ml`)"
P_GRADO = (
    "Por ser bebida alcohólica, ¿cuál es el **grado alcohólico**? "
    "(por ejemplo `11% Alc./vol.`)"
)
P_ALERGENOS = (
    "¿Contiene alguno de estos **alérgenos**? trigo, leche, huevo, soya, maní, "
    "nueces, pescado, crustáceos, sulfitos. Sepáralos por coma, o escribe **ninguno**."
)
P_PAIS = "¿En qué **país** se fabrica? (por ejemplo *Honduras*)"
P_RESPONSABLE = "¿Cuál es el **nombre o razón social** del responsable/fabricante?"
P_DIRECCION = "¿Y la **dirección física** completa del responsable?"

_UNIDADES = {"kg", "g", "mg", "l", "ml", "u"}
_ALERGENOS_VALIDOS = {a.value for a in Alergeno}
_SINONIMOS_ALERGENO = {
    "gluten": "trigo", "mani": "maní", "crustaceos": "crustáceos", "nuez": "nueces",
}

# Texto de la pregunta de cada paso (para re-preguntar si hace falta).
PROMPTS = {
    "nombre": P_NOMBRE, "marca": P_MARCA, "tipo": P_TIPO, "descripcion": P_DESCRIPCION,
    "ingredientes": P_INGREDIENTES, "aditivos": P_ADITIVOS, "contenido": P_CONTENIDO,
    "grado": P_GRADO, "alergenos": P_ALERGENOS, "pais": P_PAIS,
    "responsable": P_RESPONSABLE, "direccion": P_DIRECCION,
}

# Pasos cuya respuesta es OBLIGATORIA (sin ella no hay etiqueta legal), con el
# motivo breve para explicárselo al usuario si intenta saltarla.
RAZON_INDISPENSABLE = {
    "nombre": "es el nombre del alimento, obligatorio en la etiqueta.",
    "tipo": "según el tipo elijo qué norma del RTCA aplicar.",
    "contenido": "el contenido neto es obligatorio en la etiqueta.",
    "grado": "el grado alcohólico es obligatorio en bebidas alcohólicas.",
    "pais": "el país de origen es obligatorio en la etiqueta.",
    "responsable": "los datos del responsable son obligatorios.",
    "direccion": "la dirección del responsable es obligatoria.",
}


# ===========================================================================
# Utilidades de parseo (tolerantes)
# ===========================================================================
def parse_tipo(texto: str) -> str:
    """Deduce el TipoProducto a partir de lo que escribe el usuario."""
    t = texto.lower()
    # OJO: "bebida" sola NO implica alcohol (un jugo o gaseosa también es bebida).
    # Solo marca alcohólica con palabras inequívocas (con límites de palabra para que
    # "ron" no coincida dentro de "limón/macarrón").
    if re.search(r"\b(alcoh\w*|vino|licor\w*|cerveza|ron|aguardiente|tequila|whisky|"
                 r"vodka|mezcal|champ\w*|sidra|brandy|ginebra|destil\w*)\b", t):
        return TipoProducto.BEBIDA_ALCOHOLICA.value
    if any(k in t for k in ("semis", "mermelada", "salsa", "crema", "pasta",
                            "jalea", "puré", "pure", "conserva", "miel", "yogur")):
        return TipoProducto.SEMISOLIDO.value
    return TipoProducto.PREENVASADO.value


def parse_ingrediente(texto: str) -> dict:
    """Convierte 'Mora 2 kg' en {nombre, cantidad, unidad}. Tolerante."""
    toks = texto.replace(";", " ").split()
    nombre, cantidad, unidad = texto.strip(), 0.0, "g"
    for i in range(len(toks) - 1, -1, -1):
        num = toks[i].replace(",", ".")
        if re.match(r"^\d+(\.\d+)?$", num):
            cantidad = float(num)
            if i + 1 < len(toks) and toks[i + 1].lower() in _UNIDADES:
                unidad = toks[i + 1].lower()
            nombre = " ".join(toks[:i]).strip() or texto.strip()
            break
    return {"nombre": nombre, "cantidad": cantidad, "unidad": unidad}


def parse_aditivo(texto: str) -> dict:
    """Convierte 'Benzoato de sodio; conservante; 211' en un dict de Aditivo."""
    partes = [p.strip() for p in re.split(r"[;,]", texto) if p.strip()]
    nombre = partes[0] if partes else texto.strip()
    funcion = partes[1] if len(partes) > 1 else "aditivo"
    ins = partes[2] if len(partes) > 2 else ""
    return {"clase": "Aditivo", "nombre": nombre, "cantidad": 0.0, "unidad": "g",
            "funcion": funcion, "ins": ins}


def parse_contenido(texto: str):
    """Extrae [valor, unidad] de '250 g' / '750ml'. None si no se entiende."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b", texto.lower())
    if not m:
        return None
    return [float(m.group(1).replace(",", ".")), m.group(2)]


def parse_alergenos(texto: str) -> list[str]:
    """Lista de alérgenos válidos a partir del texto; ignora desconocidos."""
    if re.search(r"\b(ningun|no|nada)\b", texto.lower()):
        return []
    encontrados: list[str] = []
    for tok in re.split(r"[,;]", texto.lower()):
        tok = tok.strip()
        if tok in _ALERGENOS_VALIDOS:
            encontrados.append(tok)
        elif tok in _SINONIMOS_ALERGENO:
            encontrados.append(_SINONIMOS_ALERGENO[tok])
    return list(dict.fromkeys(encontrados))


def instruccion_sugerida(tipo: str) -> str:
    """Instrucción de conservación deducida para el tipo (reusa el modelo)."""
    try:
        return Producto(nombre="tmp", tipo=tipo).instrucciones_efectivas()
    except Exception:
        return "Consérvese en un lugar fresco y seco."


def registrar_ingrediente(d: dict, item: str) -> tuple[dict, bool, bool]:
    """Anota un ingrediente en `d`, **auto-clasificándolo** y **sin duplicar**.

    Si el texto es un aditivo conocido (por nombre o código INS), lo guarda como
    Aditivo con su función e INS; si no, como materia prima con la ortografía
    corregida. Si ese ingrediente ya estaba en la lista, **no lo repite**.
    Devuelve (registro, es_aditivo, es_duplicado).
    """
    base = parse_ingrediente(item)
    add = identificar_aditivo(base["nombre"])
    if add:
        reg = {
            "clase": "Aditivo", "nombre": add["nombre"], "funcion": add["funcion"],
            "ins": add["ins"], "cantidad": base["cantidad"], "unidad": base["unidad"],
        }
    else:
        reg = {
            "nombre": corregir_ortografia(base["nombre"]),
            "cantidad": base["cantidad"], "unidad": base["unidad"],
        }
    # Evita duplicados: si el mismo ingrediente ya está anotado, no lo repite.
    clave = reg["nombre"].strip().lower()
    if any(i["nombre"].strip().lower() == clave for i in d["ingredientes"]):
        return reg, bool(add), True
    d["ingredientes"].append(reg)
    # Conserva el texto ORIGINAL para detectar alérgenos sin perder señales que el
    # nombre canónico borra (p. ej. "lecitina de soya" → soya).
    d.setdefault("_raw", []).append(base["nombre"])
    return reg, bool(add), False


def cerrar_ingredientes(d: dict) -> None:
    """Al terminar la lista: auto-detecta los alérgenos a partir de los ingredientes.

    Escanea tanto el texto original del consultante como el nombre canónico de los
    aditivos (así detecta sulfitantes ingresados por código INS, p. ej. 'INS 223').
    """
    nombres = d.get("_raw", []) + [i["nombre"] for i in d["ingredientes"]]
    d["alergenos"] = detectar_alergenos(nombres)
    d["_motivos_alergeno"] = motivos_alergeno(nombres)


def resumen_aditivos(d: dict) -> str:
    """Texto con los aditivos ya clasificados (para mostrarle al usuario qué detecté)."""
    adit = [i for i in d["ingredientes"] if i.get("clase") == "Aditivo"]
    if not adit:
        return ""
    lineas = [f"- {a['funcion']} ({a['nombre']}, INS {a['ins']})" for a in adit]
    return "Estos **aditivos** los identifiqué y clasifiqué por ti:\n" + "\n".join(lineas)


def prompt_alergenos(d: dict) -> str:
    """Pregunta de alérgenos, **mostrando los que ya detecté** en los ingredientes."""
    det = d.get("alergenos", [])
    if not det:
        return P_ALERGENOS
    motivos = d.get("_motivos_alergeno", {})
    detalle = []
    for a in det:
        causas = motivos.get(a, [])
        detalle.append(f"**{a}**" + (f" (por {', '.join(causas)})" if causas else ""))
    return (
        "Revisé tus ingredientes y tu producto **contiene: " + ", ".join(detalle) + "**. "
        "Por ley debe ir la leyenda *Contiene: " + ", ".join(det) + "* en la etiqueta. "
        "¿Hay **algún otro** de esta lista? trigo, leche, huevo, soya, maní, nueces, "
        "pescado, crustáceos, sulfitos. Escríbelo, o escribe **ninguno** para confirmar."
    )


def es_fin(texto: str) -> bool:
    """¿El usuario indica que terminó la lista? (listo, ok, ya, eso es todo…)."""
    return bool(re.search(
        r"\b(listo|fin|finalizar|ya|ya est[aá]|termin[ée]|ok|okay|okey|vale|dale|"
        r"correcto|eso es todo|es todo|nada m[aá]s|no m[aá]s)\b",
        texto.lower(),
    ))


def es_negativo(texto: str) -> bool:
    return bool(re.search(r"\b(no|ninguno|nada)\b", texto.lower()))


# Marcos conversacionales que el consultante antepone a un dato ("quisiera que le
# agregaras…", "ponle…", "que diga…"). Sin esto, la frase entera entraba literal
# en la etiqueta (bug del caso lachiquitasabrosa: "quisiera que le agregaras Una
# vez abierto refrigerese").
_MARCO_PETICION = re.compile(
    r"^\s*(por favor[,\s]*)?"
    r"((me\s+)?gustar[ií]a|quisiera|quiero|necesito|deseo|prefiero)\s+que\s+"
    r"(le\s+|me\s+)?(agregar?as|agregue?s?|a[ñn]ad[ae]s?|a[ñn][aá]dele|pongas|"
    r"pong[ao]s?|coloques|escrib[ae]s?|dig[ao]?)\s*[:,]?\s*",
    re.IGNORECASE,
)
_MARCO_IMPERATIVO = re.compile(
    r"^\s*(por favor[,\s]*)?"
    r"(agr[eé]gale|agr[eé]ga(me)?|agreg[aá]|a[ñn][aá]dele|a[ñn]ade|ponle|pon|"
    r"coloca|escribe|escrib[ií]|que\s+(diga|ponga|aparezca))\s*[:,]?\s*",
    re.IGNORECASE,
)


def limpiar_instruccion(texto: str) -> str:
    """Quita el marco de petición de un texto libre y lo deja como leyenda.

    "quisiera que le agregaras Una vez abierto refrigerese"
        -> "Una vez abierto refrigerese."
    Devuelve el texto con la primera letra en mayúscula y punto final.
    """
    limpio = texto.strip()
    for patron in (_MARCO_PETICION, _MARCO_IMPERATIVO):
        nuevo = patron.sub("", limpio, count=1)
        if nuevo != limpio:
            limpio = nuevo.strip()
            break
    limpio = limpio.strip(" \t.;,:\"'")
    if not limpio:
        return texto.strip()
    limpio = limpio[0].upper() + limpio[1:]
    return limpio + "."


def quiere_saltar(texto: str) -> bool:
    """Detecta si el usuario quiere omitir/saltarse la pregunta actual."""
    return bool(re.search(
        r"(omitir|omito|saltar|saltarme|s[aá]ltal[oa]|s[aá]ltate|siguiente|skip|"
        r"no quiero (responder|contestar|decir|dar)|prefiero no|no s[eé]\b|"
        r"sin (este )?dato|no aplica|\bn/?a\b)",
        texto.lower(),
    ))


# ===========================================================================
# Estado de la conversación
# ===========================================================================
def reiniciar() -> None:
    ss = st.session_state
    ss.historial = []
    ss.datos = {"ingredientes": [], "alergenos": []}
    ss.paso = "nombre"
    ss.imagen = None
    ss.expresion = "feliz"
    decir(BIENVENIDA)
    decir(P_NOMBRE)


def decir(texto: str) -> None:
    """El agente añade un mensaje al historial."""
    st.session_state.historial.append(("agente", texto))


@st.cache_resource(show_spinner="Indexando la normativa…")
def cargar_rag() -> RAG:
    return RAG().construir()


# ===========================================================================
# Lógica del diálogo (máquina de pasos)
# ===========================================================================
def finalizar() -> None:
    """Valida, y si cumple genera la imagen y ofrece enviarla."""
    ss = st.session_state
    d = ss.datos
    try:
        etiqueta = Etiqueta.from_dict(d)
    except (EtiquetaInvalida, ErrorDominio) as exc:
        ss.expresion = "triste"
        decir(f"Tuvimos un problema con los datos: {exc}. Escribe **reiniciar** para empezar de nuevo.")
        ss.paso = "fin"
        return

    res = etiqueta.validar()
    if not res.cumple:
        ss.expresion = "triste"
        faltan = "\n".join(f"- ✗ {f}" for f in res.faltantes)
        decir(
            "Casi lo logramos, pero como consultor prefiero no aprobar una "
            "etiqueta incompleta. Faltan estos datos obligatorios:\n" + faltan +
            "\n\nEscribe **reiniciar** para volver a capturarlos."
        )
        ss.paso = "fin"
        return

    ss.expresion = "guino"
    if res.observaciones:
        obs = "\n".join(f"- • {o}" for o in res.observaciones)
        decir("🎉 **¡Tu etiqueta cumple con el RTCA!** Ten en cuenta estas notas:\n" + obs)
    else:
        decir("🎉 **¡Tu etiqueta cumple con el RTCA!**")

    decir("Aquí está tu etiqueta:\n```\n" + etiqueta.to_texto() + "\n```")

    res_img = generar_imagen(d)
    if res_img.get("generada"):
        ss.imagen = res_img["archivo"]
        decir("🖼️ También generé la **imagen** de tu etiqueta (la ves abajo).")

    ss.paso = "enviar"
    decir("📧 Por último, dime tu **correo electrónico** para **enviarte tu etiqueta "
          "aprobada** (la imagen y los datos). Escríbelo, por favor.")


def procesar(texto: str) -> None:
    """Avanza la conversación según el paso actual."""
    ss = st.session_state
    d = ss.datos
    paso = ss.paso
    t = texto.strip()
    ss.expresion = "feliz"  # expresión por defecto; algunos pasos la cambian

    if t.lower() in ("reiniciar", "empezar", "reset"):
        reiniciar()
        return

    # --- ¿El usuario quiere omitir la pregunta? --------------------------
    if quiere_saltar(t) and paso not in ("enviar", "fin"):
        # Ingredientes: se puede avanzar solo si ya hay al menos uno.
        if paso == "ingredientes":
            if any(i.get("clase") != "Aditivo" for i in d["ingredientes"]):
                cerrar_ingredientes(d)
                res = resumen_aditivos(d)
                if res:
                    decir(res)
                ss.paso = "aditivos"
                decir("De acuerdo, cerramos la lista de ingredientes. " + P_ADITIVOS)
            else:
                ss.expresion = "triste"
                decir("Con todo respeto, esta no puedo omitirla: necesito al menos "
                      "un ingrediente para la etiqueta. " + P_INGREDIENTES)
            return
        # Pasos obligatorios: no se pueden saltar.
        if paso in RAZON_INDISPENSABLE:
            ss.expresion = "triste"
            decir(f"Con todo respeto, esta pregunta **no se puede omitir**: "
                  f"{RAZON_INDISPENSABLE[paso]} {PROMPTS[paso]}")
            return
        # Pasos opcionales: se omiten con un valor por defecto y se sigue.
        decir("Con gusto, la omitimos. 👍")
        if paso == "marca":
            d["marca"] = ""
            ss.paso = "tipo"
            decir(P_TIPO)
        elif paso == "descripcion":
            d["descripcion"] = ""
            ss.paso = "ingredientes"
            decir(P_INGREDIENTES)
        elif paso == "aditivos":
            ss.paso = "contenido"
            decir(P_CONTENIDO)
        elif paso == "alergenos":
            # Omitir no borra los alérgenos ya detectados: son un dato legal, no opcional.
            if d.get("alergenos"):
                decir("Mantengo los alérgenos que detecté (*Contiene: " +
                      ", ".join(d["alergenos"]) + "*); es información obligatoria.")
            ss.paso = "pais"
            decir(P_PAIS)
        elif paso == "instrucciones":
            finalizar()
        return

    if paso == "nombre":
        d["nombre"] = t
        decir(ADVERTENCIA_NOMBRE)
        ss.paso = "marca"
        decir(P_MARCA)

    elif paso == "marca":
        d["marca"] = "" if es_negativo(t) else t
        if d["marca"]:
            decir(f"¡Perfecto! La marca **{d['marca']}** irá en tu etiqueta. 👍")
        ss.paso = "tipo"
        decir(P_TIPO)

    elif paso == "tipo":
        d["tipo"] = parse_tipo(t)
        decir(f"Lo registro como **{d['tipo'].replace('_', ' ')}**. 👍")
        ss.paso = "descripcion"
        decir(P_DESCRIPCION)

    elif paso == "descripcion":
        d["descripcion"] = t
        ss.paso = "ingredientes"
        decir(P_INGREDIENTES)

    elif paso == "ingredientes":
        if es_fin(t):
            if not any(i for i in d["ingredientes"] if i.get("clase") != "Aditivo"):
                decir("Necesito al menos un ingrediente. Escribe uno, ej. `Mora 2 kg`.")
            else:
                cerrar_ingredientes(d)
                res = resumen_aditivos(d)
                if res:
                    decir(res)
                ss.paso = "aditivos"
                decir(P_ADITIVOS)
        else:
            # Acepta uno o varios (lista pegada, separada por comas/saltos/paréntesis).
            registros = [registrar_ingrediente(d, it) for it in separar_ingredientes(t)]
            nuevos = [r for r in registros if not r[2]]
            n_dup = len(registros) - len(nuevos)
            if not registros:
                decir("No te entendí 🙈. Escribe un ingrediente, ej. `Mora 2 kg`.")
            elif len(registros) == 1:
                reg, es_ad, dup = registros[0]
                if dup:
                    decir(f"**{reg['nombre']}** ya estaba en tu lista, no lo repito. "
                          "Otro ingrediente, o escribe **listo**.")
                elif es_ad:
                    ss.expresion = "sorpresa"
                    decir(f"Identifiqué un **aditivo**: {reg['funcion']} "
                          f"({reg['nombre']}, INS {reg['ins']}). "
                          "Otro ingrediente, o escribe **listo**.")
                else:
                    cant = f" ({reg['cantidad']:g} {reg['unidad']})" if reg["cantidad"] else ""
                    decir(f"Anotado: **{reg['nombre']}**{cant}. "
                          "Otro ingrediente, o escribe **listo**.")
            else:
                n_ad = sum(1 for _, es_ad, _ in nuevos if es_ad)
                ss.expresion = "sorpresa"
                extra = f" · {n_dup} repetido(s) omitido(s)" if n_dup else ""
                decir(f"Anoté **{len(nuevos)}** ingredientes "
                      f"({len(nuevos) - n_ad} materias primas y **{n_ad} aditivos** "
                      f"que clasifiqué por ti){extra}. Agrega más, o escribe **listo**.")

    elif paso == "aditivos":
        if es_negativo(t) or es_fin(t):
            cerrar_ingredientes(d)  # re-detecta alérgenos por si se añadió alguno aquí
            ss.paso = "contenido"
            decir(P_CONTENIDO)
        else:
            add = identificar_aditivo(t)
            if add:
                d["ingredientes"].append({
                    "clase": "Aditivo", "nombre": add["nombre"], "funcion": add["funcion"],
                    "ins": add["ins"], "cantidad": 0.0, "unidad": "g",
                })
                ss.expresion = "sorpresa"
                decir(f"Añadido: {add['funcion']} ({add['nombre']}, INS {add['ins']}). "
                      "Otro aditivo, o escribe **no**.")
            else:
                ad = parse_aditivo(t)
                d["ingredientes"].append(ad)
                decir(f"No tengo **{ad['nombre']}** en mi base de aditivos, así que lo "
                      "anoto tal cual. Si conoces su función e INS, escríbelos así: "
                      "`nombre; función; INS`. Otro aditivo, o escribe **no**.")

    elif paso == "contenido":
        cn = parse_contenido(t)
        if not cn:
            decir("No te entendí 🙈. Escríbelo como `250 g` o `750 ml`.")
            return
        d["contenido_neto"] = cn
        if d.get("tipo") == TipoProducto.BEBIDA_ALCOHOLICA.value:
            ss.paso = "grado"
            decir(P_GRADO)
        else:
            ss.paso = "alergenos"
            decir(prompt_alergenos(d))

    elif paso == "grado":
        d["grado_alcoholico"] = t
        ss.paso = "alergenos"
        decir(prompt_alergenos(d))

    elif paso == "alergenos":
        # A los alérgenos ya detectados (factuales) se suman los que el usuario añada.
        detectados = d.get("alergenos", [])
        extra = parse_alergenos(t)
        nuevos = [a for a in extra if a not in detectados]
        d["alergenos"] = list(dict.fromkeys(detectados + extra))
        if d["alergenos"]:
            ss.expresion = "sorpresa"
            aviso = (f"Añadí **{', '.join(nuevos)}**. " if nuevos else "")
            decir(aviso + "Confirmado: en la etiqueta irá la leyenda *Contiene: " +
                  ", ".join(d["alergenos"]) + "*.")
        else:
            decir("De acuerdo, sin alérgenos de declaración obligatoria.")
        ss.paso = "pais"
        decir(P_PAIS)

    elif paso == "pais":
        d["pais_origen"] = t
        ss.paso = "responsable"
        decir(P_RESPONSABLE)

    elif paso == "responsable":
        d["responsable"] = t
        ss.paso = "direccion"
        decir(P_DIRECCION)

    elif paso == "direccion":
        d["direccion_responsable"] = t
        sug = instruccion_sugerida(d.get("tipo", "preenvasado"))
        ss.expresion = "pensando"
        ss.paso = "instrucciones"
        decir(f"Para la **conservación** te propongo:\n> *{sug}*\n\n"
              "Escribe **ok** para usarla, o escribe la tuya.")

    elif paso == "instrucciones":
        if t.lower() not in ("ok", "sí", "si", "listo", "correcto", "dale", "vale"):
            # Limpia el marco conversacional ("quisiera que le agregaras…") para
            # que no entre literal en la etiqueta.
            d["instrucciones"] = limpiar_instruccion(t)
        finalizar()

    elif paso == "enviar":
        # El envío es OBLIGATORIO cuando la etiqueta está aprobada: se entrega al
        # correo del emprendedor. Por eso aquí se exige un correo válido (sin opción
        # de omitir); solo se puede salir reiniciando.
        if email_valido(t):
            d["correo"] = t
            envio = enviar_etiqueta(d, para=t, simular=False)
            if envio.get("enviado"):
                ss.expresion = "guino"
                decir(f"📧 ¡Listo! Tu etiqueta aprobada (imagen y datos) fue **enviada "
                      f"a {t}**. Revisa tu bandeja de entrada (y la carpeta de "
                      "Spam/Promociones). 🌟")
                ss.paso = "fin"
                decir("¿Quieres etiquetar otro producto? Escribe **reiniciar**.")
            else:
                ss.expresion = "triste"
                decir("Tu etiqueta está **aprobada**, pero no pude enviar el correo en "
                      "este momento: " + str(envio.get("detalle") or envio.get("error")) +
                      ".\n\n¿Me das otro **correo** para reintentar el envío?")
                # Se queda en el paso 'enviar' para reintentar.
        else:
            decir("Para entregarte tu etiqueta aprobada **necesito un correo válido** "
                  "(por ejemplo `nombre@correo.com`). Escríbelo, por favor. 🙂")

    elif paso == "fin":
        decir("Escribe **reiniciar** para etiquetar otro producto. 🙂")


# ===========================================================================
# Interfaz
# ===========================================================================
st.set_page_config(page_title="ConsulAlim AI", page_icon="🥑", layout="centered")

if "historial" not in st.session_state:
    reiniciar()

with st.sidebar:
    st.header("🥑 ConsulAlim AI")
    st.caption("Soy **Aguacatito**, tu Ingeniero de Alimentos y Consultor de Regulación Sanitaria.")
    if st.button("🔄 Empezar de nuevo", use_container_width=True):
        reiniciar()
        st.rerun()
    st.divider()
    with st.expander("📚 Consultar la norma (RAG)"):
        q = st.text_input("Buscar en el RTCA", key="rag_q",
                          placeholder="orden de ingredientes")
        if st.button("Buscar", use_container_width=True) and q.strip():
            try:
                for r in cargar_rag().consultar(q, k=2):
                    st.markdown(f"**{r['fuente']}** · pág. {r['pagina']}")
                    st.caption(r["texto"][:200] + "…")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error en el RAG: {exc}")

st.title("🥑 ConsulAlim AI")

# Aguacatito presente en el chat: reacciona con su expresión actual cada turno.
_expr = st.session_state.get("expresion", "feliz")
_variante = _WEB / "assets" / f"aguacatito_{_expr}.png"
if _variante.exists():
    _c1, _c2 = st.columns([1, 3])
    _c1.image(str(_variante), use_container_width=True)
    _c2.info(FRASES.get(_expr, ""))
else:
    components.html(html_mascota(_expr), height=200)

# Historial del chat (el agente usa a Aguacatito como avatar)
for rol, txt in st.session_state.historial:
    if rol == "agente":
        with st.chat_message("assistant", avatar="🥑"):
            st.markdown(txt)
    else:
        with st.chat_message("user"):
            st.markdown(txt)

# Imagen de la etiqueta (si ya se generó)
if st.session_state.get("imagen"):
    st.image(st.session_state["imagen"], caption="Tu etiqueta")

# Entrada del usuario
entrada = st.chat_input("Escribe tu respuesta…")
if entrada:
    st.session_state.historial.append(("user", entrada))
    procesar(entrada)
    st.rerun()
