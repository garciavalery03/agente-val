# ConsulAlim AI

**Agente de IA — Ingeniero de Alimentos y Consultor de Regulación Sanitaria automatizado.**

ConsulAlim AI ayuda a microemprendedores de alimentos a **formalizar la etiqueta
de su producto de forma segura y legal**: captura los datos del producto, consulta
la normativa **RTCA** mediante RAG, **valida** la etiqueta contra la "Regla de
Salida" del RTCA 67.01.07 y, **solo si cumple**, la **entrega por correo**.

> Proyecto Final · Programación · Maestría en Automatización Industrial · UTH 2026.4
> Variante 5 ("Otra"). El cerebro del agente es **Claude Code**.

---

## ¿Qué hace? (flujo del agente)

```
entrada (datos del producto)
        │
        ▼
  Claude Code (cerebro)  ── consulta ──►  RAG sobre PDFs del RTCA (cita la norma)
        │                                  + Codex/FAO en línea (se salta si cae)
        ▼
  valida la etiqueta (Regla de Salida RTCA 67.01.07)
        │
        ├─ NO cumple → retroalimenta: qué falta y cómo corregirlo
        └─ SÍ cumple → entrega la etiqueta por correo (canal de salida)
                          └─ y avisa a la red de la clase (MCP)
```

## Estructura del proyecto

```
config.py                      Configuración central (correo, rutas; secretos en .env)
src/
  modelos.py                   Clases POO: Ingrediente, Aditivo (herencia), Producto,
                               Etiqueta, ResultadoValidacion
  rag.py                       RAG (TF-IDF) sobre los PDFs de data/RAG/
  notificar.py                 Canal de salida: correo (SMTP / Resend)
  _pausado_dosificacion.py     Inventario/Receta (EN PAUSA, fuera del flujo actual)
tools/
  consultar_norma.py           Consulta el RAG y cita la norma (PDF + página)
  validar_etiqueta.py          Valida una etiqueta contra el RTCA
  consultar_codex.py           Consulta la URL del Codex (la salta si está caída)
  enviar_etiqueta.py           Entrega la etiqueta por correo si cumple
data/
  RAG/                         PDFs del RTCA + .txt con URLs (fuentes del RAG)
  entrada/                     Datos del producto (JSON de entrada)
  etiquetas/Ejemplo/           Modelos de etiqueta de referencia
CLAUDE.md                      System prompt / reglas y flujo del agente
valery_garcia.md               Definición del agente (identidad, tono, protocolo)
BITACORA_APRENDIZAJE.md        Bitácora de aprendizaje del agente
.mcp.json                      Conexión a la red MCP de la clase
requirements.txt               Dependencias
```

## Componentes del proyecto (rúbrica)

| # | Componente | Dónde |
|---|---|---|
| 1 | Clases POO | `src/modelos.py` (`Aditivo` hereda de `Ingrediente`) |
| 2 | RAG | `src/rag.py` (TF-IDF sobre `data/RAG/`, cita PDF y página) |
| 3 | Herramientas (tool calling) | `tools/*.py` (devuelven JSON) |
| 4 | Canal de salida | `src/notificar.py` + `tools/enviar_etiqueta.py` (correo) |
| 5 | System prompt | `CLAUDE.md` + `valery_garcia.md` |
| 6 | Red de agentes (MCP) | `.mcp.json` (servidor `uthAgentes`) |

## Cómo correrlo

### 1. Requisitos
- Python 3.13
- Instalar dependencias:
  ```powershell
  python -m pip install -r requirements.txt
  ```

### 2. Configurar el correo (canal de salida)
Copia `.env.example` a `.env` y rellena tus valores (Gmail App Password, etc.).
El `.env` está ignorado por git: **nunca subas secretos**.

### 3. Probar las piezas
```powershell
# Clases POO (demo)
python src/modelos.py

# RAG: consulta la norma
python src/rag.py "orden de la lista de ingredientes"

# Herramienta: validar una etiqueta de ejemplo
python tools/validar_etiqueta.py data/entrada/ejemplo_producto.json

# Entregar la etiqueta (modo simulado, sin enviar)
python tools/enviar_etiqueta.py data/entrada/ejemplo_producto.json --simular
```

### 4. Conectar la red de la clase (MCP)
Define el token que te da el instructor y reabre Claude Code:
```powershell
setx UTHAGENTES_TOKEN "el-token-del-instructor"
```
La conexión está en `.mcp.json`. El servidor de la clase está activo solo cuando
el instructor lo enciende.

---

**Autora:** Valery · Cátedra: PhD(c) Luis Loo · UTH 2026.4
