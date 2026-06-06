"""
mascota.py — Aguacatito reactivo (SVG con expresiones)
======================================================

"Aguacatito": aguacate con gorro de chef y la carita en la PULPA (primera
versión, colores planos). Tiene varias EXPRESIONES y movimiento de cuerpo
(flota, se mece y saluda) para reaccionar según el paso de la conversación.

Uso:
    from mascota import html_mascota, FRASES
    components.html(html_mascota("pensando"), height=240)

Si en web/assets/ existen variantes PNG (aguacatito_feliz.png, etc.), la web las
usa en lugar del dibujo SVG (ver app.py).
"""

from __future__ import annotations

# Cuerpo del aguacate (colores planos). __CARA__ se reemplaza por la expresión.
AGUACATE_SVG = """
<svg viewBox="0 0 180 210" width="150" height="175" aria-label="Aguacatito">
  <ellipse cx="90" cy="200" rx="46" ry="7" fill="rgba(0,0,0,0.12)"/>
  <path d="M50 122 q-16 6 -18 24" stroke="#4e7d34" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M130 122 q18 -2 18 -18" stroke="#4e7d34" stroke-width="7" fill="none"
        stroke-linecap="round" class="brazo"/>
  <path d="M90 54 C58 54,46 86,46 126 C46 168,68 190,90 190 C112 190,134 168,134 126
           C134 86,122 54,90 54 Z" fill="#4e7d34"/>
  <path d="M90 66 C64 66,56 92,56 126 C56 162,74 180,90 180 C106 180,124 162,124 126
           C124 92,116 66,90 66 Z" fill="#dcefb4"/>
  <circle cx="90" cy="140" r="24" fill="#b9824e"/>
  <ellipse cx="82" cy="132" rx="8" ry="6" fill="#d09a66"/>
  <circle cx="66" cy="108" r="6.5" fill="#f4a8a8" opacity="0.7"/>
  <circle cx="114" cy="108" r="6.5" fill="#f4a8a8" opacity="0.7"/>
  <circle cx="71" cy="44" r="14" fill="#ffffff"/>
  <circle cx="90" cy="37" r="17" fill="#ffffff"/>
  <circle cx="109" cy="44" r="14" fill="#ffffff"/>
  <rect x="62" y="50" width="56" height="15" rx="4" fill="#ffffff" stroke="#e2e2e2" stroke-width="1.5"/>
  <g id="cara">__CARA__</g>
</svg>
"""

# Caras sobre la pulpa (ojos ~ y98, boca ~ y116). Ojos grandes con brillito.
CARAS = {
    "feliz": '<circle cx="76" cy="98" r="7.5" fill="#3a2a1a"/><circle cx="104" cy="98" r="7.5" fill="#3a2a1a"/><circle cx="73" cy="95" r="2.6" fill="#fff"/><circle cx="101" cy="95" r="2.6" fill="#fff"/><path d="M76 116 q14 12 28 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/>',
    "sorpresa": '<circle cx="76" cy="96" r="7.5" fill="#fff" stroke="#3a2a1a" stroke-width="2"/><circle cx="104" cy="96" r="7.5" fill="#fff" stroke="#3a2a1a" stroke-width="2"/><circle cx="76" cy="97" r="3.3" fill="#3a2a1a"/><circle cx="104" cy="97" r="3.3" fill="#3a2a1a"/><ellipse cx="90" cy="118" rx="7" ry="9" fill="#7a3b2b"/>',
    "pensando": '<circle cx="78" cy="94" r="6.5" fill="#3a2a1a"/><circle cx="106" cy="94" r="6.5" fill="#3a2a1a"/><circle cx="75.5" cy="91.5" r="2.2" fill="#fff"/><circle cx="103.5" cy="91.5" r="2.2" fill="#fff"/><path d="M80 116 q8 -4 16 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/>',
    "guino": '<circle cx="76" cy="98" r="7.5" fill="#3a2a1a"/><circle cx="73" cy="95" r="2.6" fill="#fff"/><path d="M98 99 q6 -8 12 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M76 116 q14 12 28 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/>',
    "animo": '<path d="M70 98 q6 -8 12 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M98 98 q6 -8 12 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M76 112 q14 12 28 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/>',
    "triste": '<path d="M70 100 q6 6 12 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M98 100 q6 6 12 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M76 118 q14 -10 28 0" stroke="#3a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/><circle cx="112" cy="106" r="3" fill="#7ec8f2"/>',
}

# Frase corta de la burbuja por expresión.
FRASES = {
    "feliz": "¡Aquí estoy para ayudarte! 🥑",
    "sorpresa": "¡Qué interesante! Cuéntame más 😮",
    "pensando": "Déjame revisar la norma… 🤔",
    "guino": "¡Todo en orden! 😉",
    "animo": "¡Tú puedes, vamos! 💪",
    "triste": "Necesito ese dato, porfa 🥺",
}

EXPRESIONES = list(CARAS.keys())

_PLANTILLA = """
<div style="display:flex;align-items:center;gap:14px;font-family:'Segoe UI',sans-serif">
  <div class="flota"><div class="vaiven">__SVG__</div></div>
  <div class="globo">__FRASE__</div>
</div>
<style>
  /* El cuerpo flota, se mece (vaivén) y respira; el brazo saluda. */
  @keyframes flota { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-9px)} }
  @keyframes vaiven { 0%,100%{transform:rotate(-3deg) scale(1)} 50%{transform:rotate(3deg) scale(1.03)} }
  @keyframes saluda { 0%,100%{transform:rotate(0)} 50%{transform:rotate(-20deg)} }
  .flota { animation:flota 3.2s ease-in-out infinite; }
  .vaiven { transform-origin:bottom center; animation:vaiven 4s ease-in-out infinite; }
  .brazo { transform-box:fill-box; transform-origin:bottom left; animation:saluda 1.1s ease-in-out infinite; }
  .globo { background:#f3fae7; border:2px solid #4e7d34; border-radius:16px; padding:12px 16px;
           color:#2f3d22; font-size:15px; box-shadow:0 3px 8px rgba(0,0,0,.12); position:relative; max-width:340px; }
  .globo:before { content:''; position:absolute; left:-12px; top:18px;
           border:7px solid transparent; border-right-color:#4e7d34; }
</style>
"""


def html_mascota(expresion: str = "feliz", frase: str | None = None) -> str:
    """Devuelve el HTML de Aguacatito con la expresión y la frase indicadas."""
    cara = CARAS.get(expresion, CARAS["feliz"])
    texto = frase if frase is not None else FRASES.get(expresion, FRASES["feliz"])
    svg = AGUACATE_SVG.replace("__CARA__", cara)
    return _PLANTILLA.replace("__SVG__", svg).replace("__FRASE__", texto)
