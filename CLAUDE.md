# ConsulAlim AI — Reglas de proyecto (Canal 1: Tú ↔ Claude)

> Este archivo define cómo **Claude Code** debe trabajar dentro de la ruta
> `C:\Agente_Val\agente-val`. Aplica **únicamente** a este proyecto.

## ¿Qué es este proyecto?
**ConsulAlim AI** es un **agente automatizado** que cumple el rol de
**Ingeniero de Alimentos y Consultor de Regulación Sanitaria**. Su misión es
ayudar a microemprendedores de alimentos a **formalizar la etiqueta de su
producto de forma segura y legal**, validando contra el **RTCA**
(Reglamento Técnico Centroamericano), capturando los datos del producto y
consultando la base de conocimiento (RAG).

- **Definición del agente (Canal 2):** ver `valery_garcia.md` (el "cerebro": identidad, tono, protocolo de captura, estrategia RAG, regla de salida RTCA).
- **Ciclo de aprendizaje:** ver `BITACORA_APRENDIZAJE.md`

## Cómo debo comportarme yo (Claude) en este proyecto
1. **Solo bajo instrucciones, solo en esta ruta.** No modifico ni leo archivos
   fuera de `C:\Agente_Val\agente-val` salvo que tú lo pidas explícitamente.
2. **Principio de honestidad absoluta (cero inventos).** Si no estoy seguro de
   una regla regulatoria, del RTCA, o del contenido del RAG, **no lo invento**.
   Lo digo claramente y pido validación o más datos. Este principio es el mismo
   que rige al agente con el usuario final.
3. **Las reglas del agente viven en archivos.** Si cambiamos cómo el agente
   habla o valida, se edita `valery_garcia.md` y se registra el porqué en
   `BITACORA_APRENDIZAJE.md`. No hay "memoria mágica": el aprendizaje es
   actualizar estos archivos.
4. **Confirmar antes de cambios grandes.** Antes de reescribir lógica, borrar
   archivos o tocar `config.py` / `src/`, explico qué haré y espero tu visto bueno.
5. **No tocar el código sin pedirlo.** `config.py`, `src/`, `data/` y los scripts
   de prueba (`probar_*.py`) no se modifican salvo solicitud explícita.
6. **Idioma:** todo en **español**.

## Estructura del proyecto
```
config.py                  ← configuración (correo, rutas, claves vía .env)
src/modelos.py             ← clases POO de etiquetado: Ingrediente, Aditivo,
                              Producto, Etiqueta, ResultadoValidacion
src/rag.py                 ← RAG (TF-IDF) sobre los PDFs de data/RAG/
src/notificar.py           ← canal de salida (correo SMTP/Resend)
src/_pausado_dosificacion.py ← Inventario/Receta (EN PAUSA, fuera del flujo)
tools/consultar_norma.py   ← herramienta: consulta el RAG y cita la norma
tools/validar_etiqueta.py  ← herramienta: valida una etiqueta contra el RTCA
tools/consultar_codex.py   ← herramienta: consulta la URL del Codex (salta si cae)
tools/enviar_etiqueta.py   ← herramienta: entrega la etiqueta por correo si cumple
data/RAG/                  ← PDFs del RTCA + .txt con URLs (fuentes del RAG)
data/entrada/              ← datos del producto (entrada; luego desde la web)
data/etiquetas/            ← etiquetas generadas + Ejemplo/ (modelos de referencia)
.mcp.json                  ← conexión a la red MCP de la clase (Componente 6)
valery_garcia.md           ← cerebro/definición del agente (Canal 2)
BITACORA_APRENDIZAJE.md    ← registro de ajustes y aprendizaje
```

## Componente 6 — Red de agentes de la clase (MCP uthAgentes)
ConsulAlim AI se conecta al **servidor MCP de la clase** para registrarse y
enviar/leer mensajes. La conexión está en `.mcp.json`, con dos modos:

- **`uthagentes` (HTTP, el que cuenta):** la instancia compartida de la clase.
  El servidor solo está vivo cuando el instructor lo enciende y la URL de ngrok
  puede cambiar — confirmar **URL vigente** y **token** con el instructor.
- **`uthagentes-local` (stdio, opcional):** corre una copia propia con DB propia
  (no comparte con nadie); solo para **ensayar** el flujo. Requiere `pip install mcp`.

**Token:** se guarda en `.env` (clave `UTHAGENTES_TOKEN`, archivo ignorado por
git). Como Claude Code NO lee el `.env` para expandir `${VAR}`, el `.mcp.json`
usa un **`headersHelper`** (`tools/mcp_headers.cmd` → `tools/mcp_headers.py`) que
lee el token del `.env` (o del entorno) y arma el header `Authorization`. Así el
`.mcp.json` no lleva el token en claro (seguro de versionar) y la fuente única
del secreto es el `.env`. Tras pegar el token, **reabrir Claude Code**.

**Herramientas MCP disponibles (las llama Claude Code directamente):**
`registrar_estudiante`, `listar_estudiantes`, `consultar_estado`,
`enviar_mensaje(destino, asunto, cuerpo)`, `historial_mensajes`. Para cumplir la
rúbrica: registrarse una vez y enviar o leer al menos un mensaje.

## Flujo del agente (cómo razona ConsulAlim AI, paso a paso)
Cuando el emprendedor pide ayuda con su etiqueta, el agente sigue este flujo:

1. **Recibir.** Captura los datos del producto paso a paso (ver protocolo en
   `valery_garcia.md`): nombre, tipo, descripción, ingredientes (con cantidad),
   aditivos, contenido neto, responsable, país, etc.
2. **Consultar la norma (RAG).** Para cada duda regulatoria, ejecuta
   `tools/consultar_norma.py "<consulta>"` y **cita** el PDF y la página que
   devuelve. Para aditivos, complementa con `tools/consultar_codex.py`
   (si la URL está caída, la salta y usa los PDFs locales).
3. **Estructurar.** Arma el producto/etiqueta como JSON (clases de `modelos.py`).
4. **Validar.** Ejecuta `tools/validar_etiqueta.py <json>` para comprobar la
   "Regla de Salida" del RTCA. Lee `faltantes` y `observaciones`.
5. **Retroalimentar.** Si NO cumple, explica al emprendedor con empatía qué
   falta y cómo corregirlo. Vuelve al paso 1 con los datos corregidos.
6. **Entregar.** Si cumple, ejecuta `tools/enviar_etiqueta.py <json> --para <correo>`
   para enviar la etiqueta aprobada por correo (usa `--simular` para probar).

Regla transversal: **cero inventos.** Toda afirmación regulatoria se respalda en
el RAG o se marca como “a validar”. Nunca se aprueba una etiqueta con faltantes.

## Herramientas disponibles (tool calling) — cuándo usar cada una
| Herramienta | Cuándo usarla | Devuelve |
|---|---|---|
| `tools/consultar_norma.py "<q>" [k]` | Para fundamentar cualquier regla del RTCA. | JSON con fragmentos + fuente (PDF, página). |
| `tools/consultar_codex.py` | Para aditivos (Codex/FAO–GSFA), como complemento. | JSON; marca la URL como caída y la salta si no responde. |
| `tools/validar_etiqueta.py <json\|->` | Antes de aprobar, para revisar la etiqueta completa. | JSON: `aprobada`, `faltantes`, `observaciones`, texto. |
| `tools/enviar_etiqueta.py <json> [--para] [--simular]` | Solo cuando la etiqueta CUMPLE, para entregarla. | JSON: `enviado`, canal, detalle. |
