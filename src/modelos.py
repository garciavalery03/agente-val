"""
modelos.py — Modelos de dominio de ConsulAlim AI
================================================

ConsulAlim AI es un **Ingeniero de Alimentos y Consultor de Regulación
Sanitaria automatizado**. Este módulo define las clases de Programación
Orientada a Objetos (POO) que modelan el dominio del **etiquetado** de
alimentos según el RTCA 67.01.07 (Etiquetado General de Alimentos
Previamente Envasados).

Clases:
    - Ingrediente : una materia prima o aditivo declarable en la etiqueta.
    - Aditivo     : un Ingrediente especializado (herencia) con datos
                    regulatorios (código INS/SIN y dosis máxima).
    - Producto    : el alimento del emprendedor (nombre, tipo, ingredientes,
                    contenido neto, alérgenos, responsable, país de origen…).
    - Etiqueta    : el modelo de etiqueta; reúne los campos obligatorios del
                    RTCA y sabe **validarse a sí misma**.
    - ResultadoValidacion : el veredicto de una validación (cumple, qué falta,
                    observaciones), serializable a JSON para el agente.

Nota: las clases de **dosificación/inventario** (Inventario, Receta) quedaron
pausadas en `src/_pausado_dosificacion.py`; no forman parte del flujo actual.

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Excepciones del dominio
# ---------------------------------------------------------------------------
class ErrorDominio(Exception):
    """Excepción base de los errores de negocio del agente."""


class StockInsuficiente(ErrorDominio):
    """Se intentó descontar más cantidad de la disponible (uso de dosificación)."""


class EtiquetaInvalida(ErrorDominio):
    """No se pudo construir una etiqueta con los datos dados."""


# ---------------------------------------------------------------------------
# Enumeraciones (tipos cerrados del dominio)
# ---------------------------------------------------------------------------
class TipoIngrediente(str, Enum):
    """Clasificación de un ingrediente según el RTCA."""

    MATERIA_PRIMA = "materia_prima"
    ADITIVO = "aditivo"


class Unidad(str, Enum):
    """Unidades de medida soportadas por el agente."""

    KILOGRAMO = "kg"
    GRAMO = "g"
    MILIGRAMO = "mg"
    LITRO = "l"
    MILILITRO = "ml"
    UNIDAD = "u"


class TipoProducto(str, Enum):
    """Tipo de producto, que determina qué norma del RAG aplica."""

    PREENVASADO = "preenvasado"            # RTCA Etiquetado General
    SEMISOLIDO = "semisolido"              # RTCA Etiquetado General (semisólidos)
    BEBIDA_ALCOHOLICA = "bebida_alcoholica"  # RTCA Bebidas Alcohólicas


# Advertencia legal obligatoria en la etiqueta de bebidas alcohólicas.
# Texto tomado del modelo de referencia data/etiquetas/Ejemplo/ETIQUETA_BEBIDA_ALCOHOLICA.png.
ADVERTENCIA_ALCOHOL = "EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA LA SALUD"


class Alergeno(str, Enum):
    """Alérgenos de declaración obligatoria (listado de hipersensibilidad)."""

    TRIGO = "trigo"
    LECHE = "leche"
    HUEVO = "huevo"
    SOYA = "soya"
    MANI = "maní"
    NUECES = "nueces"
    PESCADO = "pescado"
    CRUSTACEOS = "crustáceos"
    SULFITOS = "sulfitos"


# Factor para convertir cada unidad a su unidad base (gramos / mililitros / unidad).
_FACTOR_A_BASE: dict[Unidad, float] = {
    Unidad.KILOGRAMO: 1000.0,   # 1 kg  = 1000 g
    Unidad.GRAMO: 1.0,          # base de masa
    Unidad.MILIGRAMO: 0.001,    # 1 mg  = 0.001 g
    Unidad.LITRO: 1000.0,       # 1 l   = 1000 ml
    Unidad.MILILITRO: 1.0,      # base de volumen
    Unidad.UNIDAD: 1.0,         # base de conteo
}

# Dimensión física de cada unidad (no se puede mezclar masa con volumen).
_DIMENSION: dict[Unidad, str] = {
    Unidad.KILOGRAMO: "masa",
    Unidad.GRAMO: "masa",
    Unidad.MILIGRAMO: "masa",
    Unidad.LITRO: "volumen",
    Unidad.MILILITRO: "volumen",
    Unidad.UNIDAD: "conteo",
}

# Unidades válidas del Sistema Internacional para declarar contenido neto.
_UNIDADES_SI_CONTENIDO: set[Unidad] = {
    Unidad.GRAMO, Unidad.KILOGRAMO, Unidad.MILILITRO, Unidad.LITRO,
}

# Instrucciones de conservación sugeridas por tipo de producto. El agente las
# propone cuando el emprendedor no las indica (guía operativa estándar, no una
# afirmación regulatoria); el emprendedor las confirma o personaliza.
_INSTRUCCIONES_SUGERIDAS: dict[TipoProducto, str] = {
    TipoProducto.PREENVASADO:
        "Consérvese en un lugar fresco y seco. Una vez abierto, consúmase pronto.",
    TipoProducto.SEMISOLIDO:
        "Consérvese en un lugar fresco y seco. Refrigérese una vez abierto.",
    TipoProducto.BEBIDA_ALCOHOLICA:
        "Consérvese en un lugar fresco y seco, protegido de la luz solar directa. "
        "Una vez abierto, manténgase refrigerado y consúmase pronto.",
}


def _a_unidad(valor: Unidad | str) -> Unidad:
    """Normaliza un valor (str o Unidad) a un miembro del enum Unidad."""
    if isinstance(valor, Unidad):
        return valor
    try:
        return Unidad(str(valor).strip().lower())
    except ValueError as exc:
        validas = ", ".join(u.value for u in Unidad)
        raise ErrorDominio(f"Unidad desconocida: {valor!r}. Válidas: {validas}") from exc


def _a_tipo(valor: TipoIngrediente | str) -> TipoIngrediente:
    """Normaliza un valor (str o TipoIngrediente) a un miembro del enum."""
    if isinstance(valor, TipoIngrediente):
        return valor
    try:
        return TipoIngrediente(str(valor).strip().lower())
    except ValueError as exc:
        validas = ", ".join(t.value for t in TipoIngrediente)
        raise ErrorDominio(f"Tipo desconocido: {valor!r}. Válidos: {validas}") from exc


def _a_tipo_producto(valor: TipoProducto | str) -> TipoProducto:
    """Normaliza un valor (str o TipoProducto) a un miembro del enum."""
    if isinstance(valor, TipoProducto):
        return valor
    try:
        return TipoProducto(str(valor).strip().lower())
    except ValueError as exc:
        validos = ", ".join(t.value for t in TipoProducto)
        raise EtiquetaInvalida(
            f"Tipo de producto desconocido: {valor!r}. Válidos: {validos}"
        ) from exc


def _a_alergeno(valor: Alergeno | str) -> Alergeno:
    """Normaliza un valor (str o Alergeno) a un miembro del enum."""
    if isinstance(valor, Alergeno):
        return valor
    try:
        return Alergeno(str(valor).strip().lower())
    except ValueError as exc:
        validos = ", ".join(a.value for a in Alergeno)
        raise EtiquetaInvalida(
            f"Alérgeno desconocido: {valor!r}. Válidos: {validos}"
        ) from exc


# ---------------------------------------------------------------------------
# Ingrediente
# ---------------------------------------------------------------------------
class Ingrediente:
    """Una materia prima o aditivo declarable en la etiqueta.

    Atributos
    ---------
    nombre : str
        Nombre del ingrediente (clave única dentro de un producto).
    cantidad : float
        Cantidad usada en la receta, expresada en `unidad`. Sirve para
        ordenar la lista de ingredientes de mayor a menor (regla del RTCA).
    unidad : Unidad
        Unidad de medida de `cantidad` (kg, g, mg, l, ml, u).
    tipo : TipoIngrediente
        materia_prima o aditivo.
    funcion : str
        Función tecnológica en el producto (p. ej. "conservante",
        "edulcorante", "base", "colorante"). Relevante para el etiquetado RTCA.
    """

    def __init__(
        self,
        nombre: str,
        cantidad: float = 0.0,
        unidad: Unidad | str = Unidad.GRAMO,
        tipo: TipoIngrediente | str = TipoIngrediente.MATERIA_PRIMA,
        funcion: str = "",
    ) -> None:
        if not nombre or not nombre.strip():
            raise ErrorDominio("El ingrediente debe tener nombre.")
        if cantidad < 0:
            raise ErrorDominio(f"La cantidad de {nombre!r} no puede ser negativa.")

        self.nombre: str = nombre.strip()
        self.cantidad: float = float(cantidad)
        self.unidad: Unidad = _a_unidad(unidad)
        self.tipo: TipoIngrediente = _a_tipo(tipo)
        self.funcion: str = funcion.strip()

    # --- conversiones de unidad ------------------------------------------
    @property
    def dimension(self) -> str:
        """Dimensión física del ingrediente: 'masa', 'volumen' o 'conteo'."""
        return _DIMENSION[self.unidad]

    @property
    def cantidad_base(self) -> float:
        """Cantidad convertida a la unidad base (g / ml / u)."""
        return self.cantidad * _FACTOR_A_BASE[self.unidad]

    def cantidad_en(self, unidad_destino: Unidad | str) -> float:
        """Devuelve la cantidad expresada en `unidad_destino`."""
        destino = _a_unidad(unidad_destino)
        if _DIMENSION[destino] != self.dimension:
            raise ErrorDominio(
                f"No se puede convertir {self.unidad.value} ({self.dimension}) "
                f"a {destino.value} ({_DIMENSION[destino]})."
            )
        return self.cantidad_base / _FACTOR_A_BASE[destino]

    # --- mutaciones controladas (las usa el módulo de dosificación) ------
    def agregar(self, cantidad: float, unidad: Unidad | str | None = None) -> None:
        """Suma stock al ingrediente (en su misma unidad o en otra compatible)."""
        self.cantidad += self._normalizar_entrada(cantidad, unidad)

    def restar(self, cantidad: float, unidad: Unidad | str | None = None) -> None:
        """Resta stock; lanza StockInsuficiente si no alcanza."""
        requerido = self._normalizar_entrada(cantidad, unidad)
        if requerido > self.cantidad + 1e-9:
            raise StockInsuficiente(
                f"{self.nombre}: se necesitan {requerido:g} {self.unidad.value} "
                f"pero solo hay {self.cantidad:g} {self.unidad.value}."
            )
        self.cantidad -= requerido

    def _normalizar_entrada(self, cantidad: float, unidad: Unidad | str | None) -> float:
        """Convierte una cantidad de entrada a la unidad propia del ingrediente."""
        if cantidad < 0:
            raise ErrorDominio("La cantidad debe ser positiva.")
        if unidad is None:
            return float(cantidad)
        origen = _a_unidad(unidad)
        if _DIMENSION[origen] != self.dimension:
            raise ErrorDominio(
                f"Unidad {origen.value} incompatible con {self.nombre} "
                f"({self.unidad.value})."
            )
        base = float(cantidad) * _FACTOR_A_BASE[origen]
        return base / _FACTOR_A_BASE[self.unidad]

    # --- serialización ----------------------------------------------------
    def to_dict(self) -> dict:
        """Representa el ingrediente como diccionario serializable a JSON."""
        return {
            "clase": "Ingrediente",
            "nombre": self.nombre,
            "cantidad": round(self.cantidad, 6),
            "unidad": self.unidad.value,
            "tipo": self.tipo.value,
            "funcion": self.funcion,
        }

    @staticmethod
    def from_dict(datos: dict) -> "Ingrediente":
        """Reconstruye un Ingrediente (o Aditivo) desde un diccionario."""
        es_aditivo = datos.get("clase") == "Aditivo" or datos.get("tipo") == "aditivo"
        if es_aditivo:
            return Aditivo(
                nombre=datos["nombre"],
                cantidad=datos.get("cantidad", 0.0),
                unidad=datos.get("unidad", Unidad.GRAMO),
                funcion=datos.get("funcion", ""),
                ins=datos.get("ins", ""),
                dosis_maxima_mg_kg=datos.get("dosis_maxima_mg_kg"),
            )
        return Ingrediente(
            nombre=datos["nombre"],
            cantidad=datos.get("cantidad", 0.0),
            unidad=datos.get("unidad", Unidad.GRAMO),
            tipo=datos.get("tipo", TipoIngrediente.MATERIA_PRIMA),
            funcion=datos.get("funcion", ""),
        )

    # --- declaración para etiqueta ---------------------------------------
    def declaracion(self) -> str:
        """Texto con el que el ingrediente aparece en la lista de la etiqueta."""
        return self.nombre

    def __repr__(self) -> str:
        return (
            f"Ingrediente({self.nombre!r}, {self.cantidad:g} "
            f"{self.unidad.value}, tipo={self.tipo.value})"
        )


# ---------------------------------------------------------------------------
# Aditivo (hereda de Ingrediente)  — demuestra herencia y polimorfismo
# ---------------------------------------------------------------------------
class Aditivo(Ingrediente):
    """Aditivo alimentario regulado, con su código INS/SIN y dosis máxima.

    Atributos extra
    ---------------
    ins : str
        Código INS/SIN del aditivo (p. ej. "211" para benzoato de sodio).
    dosis_maxima_mg_kg : float | None
        Límite máximo permitido (mg/kg de producto). None = "según BPF".
    """

    def __init__(
        self,
        nombre: str,
        cantidad: float = 0.0,
        unidad: Unidad | str = Unidad.GRAMO,
        funcion: str = "",
        ins: str = "",
        dosis_maxima_mg_kg: float | None = None,
    ) -> None:
        super().__init__(
            nombre=nombre,
            cantidad=cantidad,
            unidad=unidad,
            tipo=TipoIngrediente.ADITIVO,
            funcion=funcion,
        )
        self.ins: str = str(ins).strip()
        self.dosis_maxima_mg_kg: float | None = (
            float(dosis_maxima_mg_kg) if dosis_maxima_mg_kg is not None else None
        )

    def dosis_en_producto(self, masa_aditivo_g: float, masa_producto_kg: float) -> float:
        """Calcula la dosis real del aditivo en el producto, en mg/kg."""
        if masa_producto_kg <= 0:
            raise ErrorDominio("La masa del producto debe ser mayor que cero.")
        return (masa_aditivo_g * 1000.0) / masa_producto_kg  # g->mg, por kg

    def excede_dosis(self, masa_aditivo_g: float, masa_producto_kg: float) -> bool:
        """Indica si la dosis usada supera el máximo permitido."""
        if self.dosis_maxima_mg_kg is None:
            return False
        return self.dosis_en_producto(masa_aditivo_g, masa_producto_kg) > self.dosis_maxima_mg_kg

    def to_dict(self) -> dict:
        """Serializa incluyendo los campos regulatorios (polimorfismo)."""
        base = super().to_dict()
        base["clase"] = "Aditivo"
        base["ins"] = self.ins
        base["dosis_maxima_mg_kg"] = self.dosis_maxima_mg_kg
        return base

    def declaracion(self) -> str:
        """Declaración RTCA: «Función (Nombre, INS xxx)».

        El RTCA exige declarar el aditivo por su **función tecnológica** seguida de
        su nombre específico o su código INS. Ej.:
        "Conservante (Benzoato de sodio, INS 211)" o "Colorante (Tartrazina, INS 102)".
        """
        funcion = self.funcion or "Aditivo"
        especifico = self.nombre
        if self.ins:
            especifico = f"{self.nombre}, INS {self.ins}"
        return f"{funcion.capitalize()} ({especifico})"

    def __repr__(self) -> str:
        return (
            f"Aditivo({self.nombre!r}, {self.cantidad:g} {self.unidad.value}, "
            f"INS={self.ins or '—'})"
        )


# ---------------------------------------------------------------------------
# Producto
# ---------------------------------------------------------------------------
class Producto:
    """El alimento del emprendedor, con los datos que exige el etiquetado.

    Atributos
    ---------
    nombre : str
        Nombre del alimento (debe reflejar su naturaleza real, no solo la marca).
    tipo : TipoProducto
        Determina qué norma del RAG aplica (preenvasado, semisólido, bebida...).
    descripcion : str
        Naturaleza del producto (deshidratado, conserva, salsa pasteurizada...).
    ingredientes : list[Ingrediente]
        Ingredientes y aditivos usados (con cantidad para poder ordenarlos).
    contenido_neto : tuple[float, Unidad] | None
        Cantidad y unidad del contenido neto (en Sistema Internacional).
    pais_origen : str
        País de origen (p. ej. "Honduras").
    responsable : str
        Nombre/razón social del responsable.
    direccion_responsable : str
        Dirección física completa del responsable.
    instrucciones : str
        Instrucciones de uso/conservación.
    alergenos : list[Alergeno]
        Alérgenos presentes que deben declararse.
    grado_alcoholico : str
        Grado alcohólico (p. ej. "11% Alc./vol."). Obligatorio en la etiqueta de
        las bebidas alcohólicas (RTCA Bebidas Alcohólicas, sección 5); vacío en
        los demás tipos de producto.
    """

    def __init__(
        self,
        nombre: str,
        tipo: TipoProducto | str = TipoProducto.PREENVASADO,
        descripcion: str = "",
        ingredientes: list[Ingrediente] | None = None,
        contenido_neto: tuple[float, Unidad | str] | None = None,
        pais_origen: str = "",
        responsable: str = "",
        direccion_responsable: str = "",
        instrucciones: str = "",
        alergenos: list[Alergeno | str] | None = None,
        grado_alcoholico: str = "",
        marca: str = "",
    ) -> None:
        if not nombre or not nombre.strip():
            raise EtiquetaInvalida("El producto debe tener un nombre.")
        self.nombre: str = nombre.strip()
        # Marca comercial con la que se vende (distinta del fabricante/responsable).
        self.marca: str = str(marca).strip()
        self.tipo: TipoProducto = _a_tipo_producto(tipo)
        self.descripcion: str = descripcion.strip()
        self.ingredientes: list[Ingrediente] = list(ingredientes or [])
        self.pais_origen: str = pais_origen.strip()
        self.responsable: str = responsable.strip()
        self.direccion_responsable: str = direccion_responsable.strip()
        self.instrucciones: str = instrucciones.strip()
        self.alergenos: list[Alergeno] = [_a_alergeno(a) for a in (alergenos or [])]
        self.grado_alcoholico: str = str(grado_alcoholico).strip()

        if contenido_neto is None:
            self.contenido_neto: tuple[float, Unidad] | None = None
        else:
            valor, unidad = contenido_neto
            self.contenido_neto = (float(valor), _a_unidad(unidad))

    # --- reglas del dominio ----------------------------------------------
    def ingredientes_ordenados(self) -> list[Ingrediente]:
        """Ingredientes ordenados de mayor a menor cantidad (regla RTCA)."""
        return sorted(
            self.ingredientes,
            key=lambda ing: ing.cantidad_base,
            reverse=True,
        )

    def aditivos(self) -> list[Aditivo]:
        """Solo los aditivos del producto (subconjunto, vía polimorfismo)."""
        return [ing for ing in self.ingredientes if isinstance(ing, Aditivo)]

    def agregar_ingrediente(self, ingrediente: Ingrediente) -> None:
        """Añade un ingrediente o aditivo al producto."""
        self.ingredientes.append(ingrediente)

    def lista_ingredientes_texto(self) -> str:
        """Lista de ingredientes lista para la etiqueta (orden decreciente)."""
        return ", ".join(ing.declaracion() for ing in self.ingredientes_ordenados())

    def contenido_neto_texto(self) -> str:
        """Contenido neto como texto, o cadena vacía si no se definió."""
        if not self.contenido_neto:
            return ""
        valor, unidad = self.contenido_neto
        return f"{valor:g} {unidad.value}"

    def instrucciones_efectivas(self) -> str:
        """Instrucciones de conservación: las dadas, o una deducida por el tipo.

        Permite que la etiqueta siempre lleve instrucciones aunque el emprendedor
        no las escriba: el agente deduce una por defecto según la naturaleza del
        producto, para que el usuario la confirme o personalice.
        """
        if self.instrucciones:
            return self.instrucciones
        return _INSTRUCCIONES_SUGERIDAS.get(
            self.tipo, "Consérvese en un lugar fresco y seco."
        )

    def instrucciones_son_sugeridas(self) -> bool:
        """True si las instrucciones provienen de la sugerencia (no las dio el usuario)."""
        return not self.instrucciones

    def to_dict(self) -> dict:
        """Serializa el producto a un diccionario JSON-able."""
        return {
            "nombre": self.nombre,
            "marca": self.marca,
            "tipo": self.tipo.value,
            "descripcion": self.descripcion,
            "ingredientes": [ing.to_dict() for ing in self.ingredientes_ordenados()],
            "contenido_neto": self.contenido_neto_texto(),
            "pais_origen": self.pais_origen,
            "responsable": self.responsable,
            "direccion_responsable": self.direccion_responsable,
            "instrucciones": self.instrucciones,
            "alergenos": [a.value for a in self.alergenos],
            "grado_alcoholico": self.grado_alcoholico,
        }

    @staticmethod
    def from_dict(datos: dict) -> "Producto":
        """Reconstruye un Producto desde un diccionario (entrada del agente/web).

        `contenido_neto` puede venir como [valor, unidad] (p. ej. [250, "g"]) o
        como None. Cada ingrediente se reconstruye con Ingrediente.from_dict,
        que distingue automáticamente entre Ingrediente y Aditivo.
        """
        cn = datos.get("contenido_neto")
        contenido = None
        if isinstance(cn, (list, tuple)) and len(cn) == 2:
            contenido = (cn[0], cn[1])
        return Producto(
            nombre=datos.get("nombre", ""),
            marca=datos.get("marca", ""),
            tipo=datos.get("tipo", TipoProducto.PREENVASADO),
            descripcion=datos.get("descripcion", ""),
            ingredientes=[Ingrediente.from_dict(i) for i in datos.get("ingredientes", [])],
            contenido_neto=contenido,
            pais_origen=datos.get("pais_origen", ""),
            responsable=datos.get("responsable", ""),
            direccion_responsable=datos.get("direccion_responsable", ""),
            instrucciones=datos.get("instrucciones", ""),
            alergenos=datos.get("alergenos", []),
            grado_alcoholico=datos.get("grado_alcoholico", ""),
        )

    def __repr__(self) -> str:
        return f"Producto({self.nombre!r}, tipo={self.tipo.value}, {len(self.ingredientes)} ingr.)"


# ---------------------------------------------------------------------------
# ResultadoValidacion
# ---------------------------------------------------------------------------
class ResultadoValidacion:
    """Veredicto de validar una etiqueta contra el RTCA.

    Atributos
    ---------
    faltantes : list[str]
        Requisitos obligatorios ausentes (impiden aprobar la etiqueta).
    observaciones : list[str]
        Avisos que no bloquean, pero conviene revisar.
    """

    def __init__(
        self,
        faltantes: list[str] | None = None,
        observaciones: list[str] | None = None,
    ) -> None:
        self.faltantes: list[str] = list(faltantes or [])
        self.observaciones: list[str] = list(observaciones or [])

    @property
    def cumple(self) -> bool:
        """True solo si no hay requisitos obligatorios faltantes."""
        return len(self.faltantes) == 0

    def agregar_falta(self, mensaje: str) -> None:
        self.faltantes.append(mensaje)

    def agregar_observacion(self, mensaje: str) -> None:
        self.observaciones.append(mensaje)

    def to_dict(self) -> dict:
        """Resultado serializable a JSON (lo consume el agente/herramientas)."""
        return {
            "cumple": self.cumple,
            "faltantes": self.faltantes,
            "observaciones": self.observaciones,
        }

    def __repr__(self) -> str:
        estado = "CUMPLE" if self.cumple else f"NO CUMPLE ({len(self.faltantes)} faltan)"
        return f"ResultadoValidacion({estado})"


# ---------------------------------------------------------------------------
# Etiqueta
# ---------------------------------------------------------------------------
class Etiqueta:
    """Modelo de etiqueta del producto; reúne los campos del RTCA y se valida.

    Composición: una Etiqueta "tiene un" Producto y añade los campos propios
    de la etiqueta (registro sanitario, lote, fecha de vencimiento, peso
    escurrido). El método `validar()` aplica la "Regla de Salida" del RTCA.
    """

    def __init__(
        self,
        producto: Producto,
        registro_sanitario: str = "",
        lote: str = "",
        fecha_vencimiento: str = "",
        peso_escurrido: str = "",
        en_espanol: bool = True,
    ) -> None:
        if not isinstance(producto, Producto):
            raise EtiquetaInvalida("Una etiqueta requiere un Producto válido.")
        self.producto: Producto = producto
        # Para registro/lote/vencimiento, basta con que exista el ESPACIO en la
        # etiqueta; el valor puede llenarse después de imprimir.
        self.registro_sanitario: str = registro_sanitario.strip()
        self.lote: str = lote.strip()
        self.fecha_vencimiento: str = fecha_vencimiento.strip()
        self.peso_escurrido: str = peso_escurrido.strip()
        self.en_espanol: bool = bool(en_espanol)

    # --- validación: Regla de Salida (RTCA 67.01.07) ---------------------
    def validar(self) -> ResultadoValidacion:
        """Verifica los requisitos obligatorios de la etiqueta.

        Devuelve un ResultadoValidacion. La etiqueta se aprueba solo si
        `resultado.cumple` es True (sin faltantes).
        """
        r = ResultadoValidacion()
        p = self.producto

        # 1. Nombre del alimento
        if not p.nombre:
            r.agregar_falta("Falta el nombre del alimento.")

        # 2. Contenido neto, en Sistema Internacional
        if not p.contenido_neto:
            r.agregar_falta("Falta el contenido neto.")
        else:
            _, unidad = p.contenido_neto
            if unidad not in _UNIDADES_SI_CONTENIDO:
                r.agregar_falta(
                    f"El contenido neto debe ir en Sistema Internacional "
                    f"(g, kg, mL, L); se recibió '{unidad.value}'."
                )

        # 2-bis. Grado alcohólico y advertencia legal (solo bebidas alcohólicas)
        if p.tipo == TipoProducto.BEBIDA_ALCOHOLICA:
            if not p.grado_alcoholico:
                r.agregar_falta(
                    "Falta el grado alcohólico (ej. '11% Alc./vol.'), obligatorio "
                    "en la etiqueta de bebidas alcohólicas (RTCA Bebidas Alcohólicas)."
                )
            r.agregar_observacion(
                f"Incluir la advertencia legal: '{ADVERTENCIA_ALCOHOL}'."
            )

        # 4. Lista de ingredientes (precedida por 'Ingredientes:')
        if not p.ingredientes:
            r.agregar_falta("Falta la lista de ingredientes.")

        # 5. Declaración de alérgenos (si los hay)
        if p.alergenos:
            # Se exige que estén explícitamente declarados (los tenemos listados).
            r.agregar_observacion(
                "Verificar leyenda 'Contiene: " +
                ", ".join(a.value for a in p.alergenos) + "'."
            )

        # 6. Datos del responsable
        if not p.responsable:
            r.agregar_falta("Falta el nombre/razón social del responsable.")
        if not p.direccion_responsable:
            r.agregar_falta("Falta la dirección física del responsable.")

        # 7. País de origen
        if not p.pais_origen:
            r.agregar_falta("Falta el país de origen (ej. 'Hecho en Honduras').")

        # 8. Instrucciones de uso y conservación. No bloquean: si el emprendedor
        # no las da, el agente deduce una por el tipo de producto (a confirmar).
        if not p.instrucciones:
            r.agregar_observacion(
                "No diste instrucciones de conservación; se sugiere: "
                f"\"{p.instrucciones_efectivas()}\". Confírmala o personalízala."
            )

        # 9. Registro sanitario (basta el espacio reservado)
        if not self.registro_sanitario:
            r.agregar_observacion(
                "Reservar el espacio 'Registro Sanitario: ______' en la etiqueta."
            )

        # 10. Identificación del lote
        if not self.lote:
            r.agregar_observacion("Reservar el espacio 'Lote: ______'.")

        # 11. Fecha de vencimiento: basta el espacio reservado; el valor real se
        # estampa al imprimir la etiqueta (igual que registro sanitario y lote).
        if not self.fecha_vencimiento:
            r.agregar_observacion(
                "Reservar el espacio 'Vence: DD/MM/AA' (se completa al imprimir)."
            )

        # Criterio de diseño: idioma español
        if not self.en_espanol:
            r.agregar_falta("La información obligatoria debe estar en español.")

        # 3. Peso escurrido: solo si aplica (medio líquido que se desecha)
        # No se exige por defecto; se deja como observación si el tipo lo sugiere.
        return r

    # --- render -----------------------------------------------------------
    def to_texto(self) -> str:
        """Etiqueta renderizada en texto plano (para correo/consola)."""
        p = self.producto
        lineas = [
            p.nombre.upper(),
            f"Marca: {p.marca}" if p.marca else "",
            f"({p.descripcion})" if p.descripcion else "",
            "",
            "Ingredientes: " + (p.lista_ingredientes_texto() or "—"),
        ]
        if p.alergenos:
            lineas.append("Contiene: " + ", ".join(a.value for a in p.alergenos))
        if p.contenido_neto:
            lineas.append("Contenido neto: " + p.contenido_neto_texto())
        if p.grado_alcoholico:
            lineas.append("Grado alcohólico: " + p.grado_alcoholico)
        if self.peso_escurrido:
            lineas.append("Peso escurrido: " + self.peso_escurrido)
        lineas.append("Conservación/Uso: " + p.instrucciones_efectivas())
        if p.responsable or p.direccion_responsable:
            lineas.append(f"Responsable: {p.responsable} — {p.direccion_responsable}")
        if p.pais_origen:
            lineas.append(f"Hecho en {p.pais_origen}")
        if p.tipo == TipoProducto.BEBIDA_ALCOHOLICA:
            lineas.append("Advertencia: " + ADVERTENCIA_ALCOHOL)
        lineas.append(f"Registro Sanitario: {self.registro_sanitario or '______'}")
        lineas.append(f"Lote: {self.lote or '______'}")
        lineas.append(f"Vence: {self.fecha_vencimiento or 'DD/MM/AA'}")
        return "\n".join(l for l in lineas if l != "")

    def to_dict(self) -> dict:
        """Etiqueta serializable a JSON."""
        return {
            "producto": self.producto.to_dict(),
            "registro_sanitario": self.registro_sanitario,
            "lote": self.lote,
            "fecha_vencimiento": self.fecha_vencimiento,
            "peso_escurrido": self.peso_escurrido,
            "en_espanol": self.en_espanol,
        }

    @staticmethod
    def from_dict(datos: dict) -> "Etiqueta":
        """Reconstruye una Etiqueta desde un diccionario.

        Acepta el producto anidado en la clave 'producto', o los datos del
        producto al mismo nivel que los de la etiqueta (lo que sea más cómodo
        para la web/el agente).
        """
        datos_producto = datos.get("producto", datos)
        return Etiqueta(
            producto=Producto.from_dict(datos_producto),
            registro_sanitario=datos.get("registro_sanitario", ""),
            lote=datos.get("lote", ""),
            fecha_vencimiento=datos.get("fecha_vencimiento", ""),
            peso_escurrido=datos.get("peso_escurrido", ""),
            en_espanol=datos.get("en_espanol", True),
        )

    def __repr__(self) -> str:
        return f"Etiqueta({self.producto.nombre!r})"


# ---------------------------------------------------------------------------
# Prueba rápida (demo) — se ejecuta con:  python src/modelos.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # En Windows la consola usa cp1252; forzamos UTF-8 para acentos y '·'.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=== ConsulAlim AI · prueba de modelos POO (etiquetado) ===\n")

    # 1) Construimos un producto con ingredientes y un aditivo (herencia).
    producto = Producto(
        nombre="Mermelada de mora",
        tipo=TipoProducto.SEMISOLIDO,
        descripcion="conserva de fruta pasteurizada",
        ingredientes=[
            Ingrediente("Mora", 55, "kg", funcion="fruta base"),
            Ingrediente("Azúcar", 43, "kg", funcion="edulcorante"),
            Ingrediente("Pectina", 1.5, "kg", funcion="gelificante"),
            Aditivo("Benzoato de sodio", 0.5, "kg", funcion="conservante",
                    ins="211", dosis_maxima_mg_kg=1000),
        ],
        contenido_neto=(250, "g"),
        pais_origen="Honduras",
        responsable="Emprendimiento La Mora S. de R.L.",
        direccion_responsable="Col. Centro, Tegucigalpa, Honduras",
        instrucciones="Consérvese en lugar fresco. Refrigerar después de abrir.",
        alergenos=[],
    )
    print(producto)
    print("\nLista de ingredientes (orden decreciente):")
    print("  " + producto.lista_ingredientes_texto())

    # 2) Armamos la etiqueta y la validamos contra la Regla de Salida del RTCA.
    etiqueta = Etiqueta(
        producto,
        fecha_vencimiento="31/12/26",
    )
    resultado = etiqueta.validar()
    print(f"\nValidación: {resultado}")
    if resultado.faltantes:
        print("  Faltantes (obligatorios):")
        for f in resultado.faltantes:
            print(f"    ✗ {f}")
    if resultado.observaciones:
        print("  Observaciones:")
        for o in resultado.observaciones:
            print(f"    • {o}")

    # 3) Etiqueta renderizada.
    print("\n--- Etiqueta (texto) ---")
    print(etiqueta.to_texto())

    # 4) Confirmamos que el JSON sale limpio (lo que consumirá el agente).
    print("\n--- JSON del resultado ---")
    print(json.dumps(resultado.to_dict(), ensure_ascii=False, indent=2))
