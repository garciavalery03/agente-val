"""
_pausado_dosificacion.py — Módulo EN PAUSA (no forma parte del flujo actual)
============================================================================

ConsulAlim AI se enfoca ahora en el **etiquetado** (RTCA 67.01.07). La parte de
**dosificación / inventario** quedó pausada temporalmente, pero NO se descarta:
se conserva aquí para retomarla más adelante.

Contiene las clases de dosificación que antes vivían en `modelos.py`:
    - Inventario : la bodega; carga/guarda en JSON, verifica stock y descuenta.
    - Receta     : formulación porcentual; calcula la dosificación por lote.

Reutiliza las clases y utilidades base que siguen en `modelos.py`
(`Ingrediente`, `Aditivo`, `Unidad`, etc.), así no se duplica nada.

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
Cátedra: PhD(c) Luis Loo
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

# Reutiliza el dominio base que permanece en modelos.py
from .modelos import (
    Aditivo,
    ErrorDominio,
    Ingrediente,
    StockInsuficiente,
    Unidad,
    _a_unidad,
    _DIMENSION,
    _FACTOR_A_BASE,
)


class FormulacionInvalida(ErrorDominio):
    """Los porcentajes de una receta no son válidos (no suman ~100%, etc.)."""


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------
class Inventario:
    """Bodega de ingredientes del emprendimiento, persistida en JSON.

    Mantiene los ingredientes indexados por nombre y ofrece operaciones de
    negocio: cargar/guardar, verificar stock para una receta y descontar el
    consumo cuando se procesa un lote.
    """

    def __init__(self, ruta: str | Path = "data/inventario.json") -> None:
        self.ruta: Path = Path(ruta)
        self._items: dict[str, Ingrediente] = {}

    # --- acceso tipo colección -------------------------------------------
    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Ingrediente]:
        return iter(self._items.values())

    def __contains__(self, nombre: str) -> bool:
        return nombre.strip() in self._items

    def obtener(self, nombre: str) -> Ingrediente | None:
        """Devuelve el ingrediente por nombre, o None si no existe."""
        return self._items.get(nombre.strip())

    def agregar(self, ingrediente: Ingrediente) -> None:
        """Agrega un ingrediente nuevo o acumula stock si ya existe."""
        clave = ingrediente.nombre
        existente = self._items.get(clave)
        if existente is None:
            self._items[clave] = ingrediente
        else:
            existente.agregar(ingrediente.cantidad, ingrediente.unidad)

    # --- persistencia -----------------------------------------------------
    def cargar(self) -> "Inventario":
        """Carga el inventario desde el archivo JSON (si existe)."""
        if not self.ruta.exists():
            self._items = {}
            return self
        with self.ruta.open("r", encoding="utf-8") as fh:
            datos = json.load(fh)
        self._items = {}
        for registro in datos.get("ingredientes", []):
            ing = Ingrediente.from_dict(registro)
            self._items[ing.nombre] = ing
        return self

    def guardar(self) -> Path:
        """Escribe el inventario al archivo JSON (crea la carpeta si falta)."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {"ingredientes": [ing.to_dict() for ing in self._items.values()]}
        with self.ruta.open("w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=2)
        return self.ruta

    # --- reglas de negocio ------------------------------------------------
    def verificar_stock(
        self, receta: "Receta", tamano_lote: float, unidad: Unidad | str = Unidad.KILOGRAMO
    ) -> tuple[bool, dict[str, dict]]:
        """Verifica si hay stock suficiente para producir un lote de la receta."""
        requerimientos = receta.calcular(tamano_lote, unidad)
        faltantes: dict[str, dict] = {}
        for nombre, requerido in requerimientos.items():
            ing = self._items.get(nombre)
            disponible = ing.cantidad_en(unidad) if ing is not None else 0.0
            if disponible + 1e-9 < requerido:
                faltantes[nombre] = {
                    "requerido": round(requerido, 4),
                    "disponible": round(disponible, 4),
                    "unidad": _a_unidad(unidad).value,
                    "falta": round(requerido - disponible, 4),
                }
        return (len(faltantes) == 0, faltantes)

    def procesar_lote(
        self, receta: "Receta", tamano_lote: float, unidad: Unidad | str = Unidad.KILOGRAMO
    ) -> dict[str, float]:
        """Descuenta del inventario los ingredientes para producir un lote."""
        suficiente, faltantes = self.verificar_stock(receta, tamano_lote, unidad)
        if not suficiente:
            detalle = "; ".join(
                f"{n}: faltan {d['falta']:g} {d['unidad']}" for n, d in faltantes.items()
            )
            raise StockInsuficiente(f"No se puede procesar el lote. {detalle}")

        consumo = receta.calcular(tamano_lote, unidad)
        for nombre, requerido in consumo.items():
            self._items[nombre].restar(requerido, unidad)
        return consumo


# ---------------------------------------------------------------------------
# Receta
# ---------------------------------------------------------------------------
class Receta:
    """Formulación porcentual de un producto."""

    def __init__(
        self,
        producto: str,
        formulacion: dict[str, float],
        tolerancia: float = 0.5,
    ) -> None:
        if not producto or not producto.strip():
            raise FormulacionInvalida("La receta debe indicar el producto.")
        if not formulacion:
            raise FormulacionInvalida("La receta no tiene ingredientes.")

        self.producto: str = producto.strip()
        self.formulacion: dict[str, float] = {
            nombre.strip(): float(pct) for nombre, pct in formulacion.items()
        }
        self.tolerancia: float = float(tolerancia)
        self.validar()

    @property
    def suma_porcentajes(self) -> float:
        """Suma de todos los porcentajes de la formulación."""
        return sum(self.formulacion.values())

    def validar(self) -> None:
        """Verifica que los porcentajes sean positivos y sumen ~100 %."""
        for nombre, pct in self.formulacion.items():
            if pct <= 0:
                raise FormulacionInvalida(
                    f"El porcentaje de {nombre!r} debe ser positivo (es {pct})."
                )
        if abs(self.suma_porcentajes - 100.0) > self.tolerancia:
            raise FormulacionInvalida(
                f"Los porcentajes de '{self.producto}' suman "
                f"{self.suma_porcentajes:g} %, deberían sumar 100 % "
                f"(±{self.tolerancia} %)."
            )

    def calcular(
        self, tamano_lote: float, unidad: Unidad | str = Unidad.KILOGRAMO
    ) -> dict[str, float]:
        """Calcula la cantidad real de cada ingrediente para un lote dado."""
        if tamano_lote <= 0:
            raise ErrorDominio("El tamaño de lote debe ser mayor que cero.")
        unidad = _a_unidad(unidad)
        if _DIMENSION[unidad] != "masa":
            raise ErrorDominio("El tamaño de lote debe expresarse en masa (kg, g o mg).")

        return {
            nombre: round(tamano_lote * pct / 100.0, 6)
            for nombre, pct in self.formulacion.items()
        }

    def calcular_detallado(
        self, tamano_lote: float, unidad: Unidad | str = Unidad.KILOGRAMO
    ) -> list[dict]:
        """Como `calcular`, pero devuelve filas listas para mostrar/imprimir."""
        unidad = _a_unidad(unidad)
        cantidades = self.calcular(tamano_lote, unidad)
        return [
            {
                "ingrediente": nombre,
                "porcentaje": self.formulacion[nombre],
                "cantidad": cantidad,
                "unidad": unidad.value,
            }
            for nombre, cantidad in cantidades.items()
        ]

    def __repr__(self) -> str:
        return f"Receta({self.producto!r}, {len(self.formulacion)} ingredientes)"
