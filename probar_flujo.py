"""
probar_flujo.py — Prueba automática del diálogo de la web (sin abrir el navegador)
==================================================================================

Maneja la máquina de pasos de `web/app.py` (la función `procesar`) simulando lo
que el consultante escribiría, y verifica que el agente:

    * auto-clasifique los aditivos (función + INS) sin que se los dicten,
    * auto-detecte los alérgenos (leyenda "Contiene:"),
    * corrija la ortografía,
    * y llegue a una etiqueta que CUMPLE el RTCA.

Para correr la lógica sin Streamlit, se inyecta un *stub* mínimo del módulo
`streamlit` en `sys.modules` ANTES de importar la app. Así probamos el cerebro
del diálogo, no la interfaz.

Uso:
    python probar_flujo.py

Autora: Valery · Maestría en Automatización Industrial · UTH 2026.4
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))


# ---------------------------------------------------------------------------
# Stub de Streamlit: solo lo que app.py toca al importarse y al dialogar.
# ---------------------------------------------------------------------------
class _SessionState(dict):
    """session_state: acceso por atributo y por clave, como el de Streamlit."""

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as exc:
            raise AttributeError(k) from exc

    def __setattr__(self, k, v):
        self[k] = v


class _Dummy:
    """Objeto/-contexto comodín: cualquier método es no-op y encadenable."""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __call__(self, *a, **k):
        return _Dummy()

    def __getattr__(self, _):
        return _Dummy()


def _instalar_stub_streamlit() -> _SessionState:
    st = types.ModuleType("streamlit")
    estado = _SessionState()
    st.session_state = estado
    st.set_page_config = lambda *a, **k: None
    st.title = st.header = st.caption = st.divider = st.markdown = lambda *a, **k: None
    st.image = st.info = st.error = st.write = lambda *a, **k: None
    st.sidebar = _Dummy()
    st.expander = lambda *a, **k: _Dummy()
    st.chat_message = lambda *a, **k: _Dummy()
    st.button = lambda *a, **k: False          # ningún botón se "presiona"
    st.text_input = lambda *a, **k: ""
    st.chat_input = lambda *a, **k: None        # sin entrada en la UI
    st.columns = lambda *a, **k: (_Dummy(), _Dummy())
    st.cache_resource = lambda *a, **k: (lambda f: f)
    st.rerun = lambda *a, **k: None
    st.spinner = lambda *a, **k: _Dummy()

    comp = types.ModuleType("streamlit.components")
    comp_v1 = types.ModuleType("streamlit.components.v1")
    comp_v1.html = lambda *a, **k: None
    comp.v1 = comp_v1
    st.components = comp

    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = comp
    sys.modules["streamlit.components.v1"] = comp_v1
    return estado


_estado = _instalar_stub_streamlit()
# Importar la app DESPUÉS del stub: al importarse llama reiniciar() (paso "nombre").
sys.path.insert(0, str(_RAIZ / "web"))
import app  # noqa: E402


# ---------------------------------------------------------------------------
# Utilidades de la prueba
# ---------------------------------------------------------------------------
def ultimos_mensajes(n: int = 1) -> str:
    """Texto de los últimos n mensajes del agente (para inspeccionar/asertar)."""
    msgs = [t for rol, t in _estado.historial if rol == "agente"]
    return "\n".join(msgs[-n:])


def enviar(texto: str) -> None:
    """Simula que el consultante escribe `texto` y el agente procesa."""
    _estado.historial.append(("user", texto))
    app.procesar(texto)


_fallos: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    estado = "✓" if condicion else "✗ FALLA"
    print(f"  [{estado}] {descripcion}")
    if not condicion:
        _fallos.append(descripcion)


# ---------------------------------------------------------------------------
# Caso 1: snack preenvasado con lista PEGADA (el caso real de la tortilla)
# ---------------------------------------------------------------------------
def caso_tortilla() -> None:
    print("\n=== Caso 1: tortilla de maíz (lista pegada, aditivos + alérgenos) ===")
    app.reiniciar()

    lista = (
        "Maiz mixtamalizado, aceite vegetal, sasonador (quesos, maltodextrina, "
        "sal yodada, especias, glutamato monosodico, harina de trigo, saborizantes "
        "naturales y artificiales, azucares anadidos), acido citrico, solidos de leche, "
        "amarillo ocaso FCF, almidon modificado, dioxido de silicio, tartrazina, "
        "guanilato de sodio, inosinato de sodio, leche entera, caramelo clase IV, "
        "estearato de calcio, acido lactico, fosfato tricalcico, caseinato de sodio, achiote"
    )
    enviar("Tortilla de maíz sabor queso (prueba)")
    enviar("La Tortillería del Valle")     # marca
    enviar("preenvasado")
    enviar("snack de maíz frito")
    enviar(lista)
    enviar("listo")

    d = _estado.datos
    comprobar(d.get("marca") == "La Tortillería del Valle", "Marca capturada en su paso")
    adit = [i for i in d["ingredientes"] if i.get("clase") == "Aditivo"]
    nombres_adit = {a["nombre"] for a in adit}
    comprobar(any(a["ins"] == "621" for a in adit), "Glutamato → INS 621 (Potenciador del sabor)")
    comprobar(any(a["ins"] == "330" for a in adit), "Ácido cítrico → INS 330 (Regulador de acidez)")
    comprobar(any(a["ins"] == "102" for a in adit), "Tartrazina → INS 102 (Colorante)")
    comprobar("Dióxido de silicio" in nombres_adit, "Dióxido de silicio reconocido")
    comprobar(len(adit) >= 10, f"Se clasificaron varios aditivos (fueron {len(adit)})")

    enviar("no")           # sin aditivos extra
    comprobar(d["alergenos"] == ["trigo", "leche"],
              f"Alérgenos auto-detectados = trigo, leche (fueron {d['alergenos']})")

    enviar("335 g")
    enviar("ninguno")      # sin alérgenos adicionales
    comprobar(d["alergenos"] == ["trigo", "leche"], "Alérgenos se conservan tras 'ninguno'")

    enviar("Honduras")
    enviar("Luna S.A de R.L")
    enviar("Res La Cañada, Comayagüela")
    enviar("ok")           # acepta la conservación sugerida

    comprobar(_estado.paso == "enviar", f"Llegó al paso de envío (paso={_estado.paso})")
    comprobar(bool(_estado.get("imagen")), "Se generó la imagen de la etiqueta")
    comprobar("nixtamalizado" in str(d["ingredientes"]), "Ortografía: 'mixtamalizado' → 'nixtamalizado'")

    # El correo es OBLIGATORIO: una entrada que no es correo no debe avanzar.
    # (No enviamos un correo real en la prueba para no spamear.)
    enviar("esto-no-es-un-correo")
    comprobar(_estado.paso == "enviar", "Correo obligatorio: no avanza sin uno válido")

    # Confirma la declaración final completa.
    from src.modelos import Etiqueta
    texto = Etiqueta.from_dict(d).to_texto()
    comprobar("Contiene: trigo, leche" in texto, "Etiqueta lleva 'Contiene: trigo, leche'")
    comprobar("INS 621" in texto and "INS 102" in texto, "Etiqueta declara los aditivos con INS")
    comprobar("Marca: La Tortillería del Valle" in texto, "Etiqueta muestra la marca")
    print("\n--- Etiqueta final (texto) ---")
    print(texto)


# ---------------------------------------------------------------------------
# Caso 2: bebida alcohólica con vino + sulfitos (alérgeno por aditivo)
# ---------------------------------------------------------------------------
def caso_vino() -> None:
    print("\n=== Caso 2: vino (grado alcohólico + sulfitos como alérgeno) ===")
    app.reiniciar()
    enviar("Vino de jamaica")
    enviar("no")                   # sin marca (opcional)
    enviar("vino")                 # → bebida_alcoholica
    enviar("fermentado artesanal")
    enviar("flor de jamaica 5 kg")
    enviar("azucar 2 kg")
    enviar("metabisulfito de sodio")   # aditivo + sulfito
    enviar("listo")
    enviar("no")                   # sin aditivos extra → pasa a contenido
    d = _estado.datos
    comprobar("sulfitos" in d["alergenos"], f"Sulfitos detectados por el metabisulfito ({d['alergenos']})")
    enviar("750 ml")               # contenido neto → por ser bebida, pide grado
    comprobar(_estado.paso == "grado", f"Pide grado alcohólico por ser bebida (paso={_estado.paso})")
    enviar("11% Alc./vol.")        # grado → alérgenos
    enviar("ninguno")
    enviar("Honduras")
    enviar("Viñedo La Flor")
    enviar("Comayagua, Honduras")
    enviar("ok")
    comprobar(_estado.paso == "enviar", "Vino llegó a etiqueta válida")
    from src.modelos import Etiqueta
    texto = Etiqueta.from_dict(d).to_texto()
    comprobar("Advertencia:" in texto, "Vino lleva la advertencia legal de alcohol")
    comprobar("11% Alc./vol." in texto, "Vino declara el grado alcohólico")


# ---------------------------------------------------------------------------
def main() -> int:
    caso_tortilla()
    caso_vino()
    print("\n" + "=" * 60)
    if _fallos:
        print(f"❌ {len(_fallos)} comprobación(es) fallaron:")
        for f in _fallos:
            print(f"   - {f}")
        return 1
    print("✅ Todas las comprobaciones pasaron.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
