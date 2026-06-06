# Bitácora de Aprendizaje — ConsulAlim AI

> Aquí registramos **cómo el agente va aprendiendo a comunicarse**, tanto con
> Claude (desarrollo) como con el emprendedor (atención). No hay "memoria mágica":
> cada ajuste real al comportamiento se anota aquí **y** se aplica en el archivo
> correspondiente (`valery_garcia.md` para el agente, `CLAUDE.md` para Claude).

## Cómo usar esta bitácora
Cuando algo salga mal, sea confuso, o quieras un cambio de tono/regla:
1. **Anota una entrada** con la fecha y qué pasó.
2. **Define la regla** nueva o corregida.
3. **Aplícala** en el archivo que corresponde y marca dónde quedó.

Formato de cada entrada:
```
### [AAAA-MM-DD] Título corto
- **Canal:** Agente↔Emprendedor  |  Claude↔Tú
- **Qué pasó / observación:** ...
- **Regla nueva o ajuste:** ...
- **Aplicado en:** valery_garcia.md (sección X)  |  CLAUDE.md  |  pendiente
```

---

## Registro

### [2026-06-03] Creación de la estructura ConsulAlim AI
- **Canal:** Claude↔Tú
- **Qué pasó / observación:** Se definió que ConsulAlim AI es un **agente
  automatizado** (Ingeniero de Alimentos y Consultor de Regulación Sanitaria),
  no un chatbot. Se estableció que el cerebro vive en `valery_garcia.md` y las
  reglas de desarrollo en `CLAUDE.md`.
- **Regla nueva o ajuste:** El aprendizaje del agente = actualizar archivos +
  registrar el porqué aquí. Trabajo de Claude limitado a la ruta del proyecto.
- **Aplicado en:** CLAUDE.md (creado), valery_garcia.md (cerebro existente).

### [2026-06-03] Estructura de carpetas y fuentes documentada en el cerebro
- **Canal:** Agente↔Emprendedor (y desarrollo)
- **Qué pasó / observación:** Se aclaró el significado real de las carpetas:
  - `data/RAG/` = guías para validar: PDFs del RTCA (locales) + `.txt` con URLs en línea.
  - `Base_Codex.txt` = URL del Codex/FAO–GSFA (aditivos): `https://www.fao.org/gsfaonline/foods/index.html?lang=es`.
  - `data/etiquetas/Ejemplo/` = imágenes modelo (PREENVASADO, BEBIDA_ALCOHOLICA, ALIMENTOS_SEMISOLIDOS).
  - `data/entrada/` = se alimentará desde una **web pequeña** donde el usuario final conversa con ConsulAlim AI.
- **Regla nueva o ajuste:**
  1. Consultar las URLs de los `.txt` en vivo cuando aplique; **si están caídas, saltarlas** y seguir con las fuentes locales, sin inventar.
  2. Elegir el PDF del RTCA según el tipo de producto antes de validar.
- **Aplicado en:** valery_garcia.md (nueva sección "Estructura del Proyecto y Fuentes de Datos"; se corrigió la ruta del RAG que antes decía `src/rag.pdf`).

### [2026-06-03] PENDIENTES detectados (para el backend)
- **Canal:** Claude↔Tú
- **Qué pasó / observación:** Dos desajustes entre el código y la realidad:
  1. `config.py` define `DIR_MANUALES = data/manuales` para el RAG, pero los PDFs viven en `data/RAG/` (y `data/manuales` no existe). → Alinear a `data/RAG/`.
  2. `config.py` describe al agente como "dosificación de alimentos / inventario / RTCA 67.04.54:18", distinto al rol actual de ConsulAlim AI (consultor de etiquetado RTCA). → Revisar al armar el backend.
- **Regla nueva o ajuste:** Pendiente de resolver cuando construyamos el backend con base en la rúbrica.
- **Aplicado en:** pendiente.

### [2026-06-03] Backend etiquetado: componentes 1–5 de la rúbrica
- **Canal:** Claude↔Tú
- **Decisión:** ConsulAlim AI se enfoca en **etiquetado** (RTCA 67.01.07). La
  dosificación/inventario queda **en pausa** (no descartada).
- **Qué se construyó:**
  1. **POO** (`src/modelos.py`): se conservan `Ingrediente`/`Aditivo` (herencia)
     y se agregan `Producto`, `Etiqueta`, `ResultadoValidacion`. La dosificación
     (`Inventario`, `Receta`) se movió a `src/_pausado_dosificacion.py`.
  2. **RAG** (`src/rag.py`): TF-IDF (pypdf + scikit-learn) sobre `data/RAG/`;
     735 fragmentos; devuelve fragmento + fuente (PDF, página).
  3. **Herramientas** (`tools/`): `consultar_norma.py`, `validar_etiqueta.py`,
     `consultar_codex.py`, `enviar_etiqueta.py` — todas devuelven JSON limpio.
  4. **Canal de salida**: `enviar_etiqueta.py` reusa `src/notificar.py`; entrega
     la etiqueta por correo **solo si cumple**; tiene modo `--simular`.
  5. **CLAUDE.md**: se añadió el **flujo del agente** y la tabla de "cuándo usar
     cada herramienta".
- **Pruebas:** los 4 scripts corren OK; el RAG cita el RTCA 67.01.07:10; la
  validación detecta faltantes; el Codex se **salta** correctamente al dar timeout.
- **Aprendizaje técnico:** en Windows la consola es cp1252 → se fuerza
  `sys.stdout.reconfigure(encoding="utf-8")` en cada script para imprimir acentos.
- **Aplicado en:** modelos.py, rag.py, tools/*, CLAUDE.md, requirements.txt.

### [2026-06-03] PENDIENTES tras componentes 1–5
- **Componente 6 (MCP):** el usuario indicó que existe "en otro lado"; falta integrarlo.
- **Componente 8 (repo):** falta `git init`, GitHub, README. `.gitignore` aún
  menciona `data/manuales` (debería ser `data/RAG`) y oculta `data/etiquetas/*`
  (revisar si se quiere versionar `data/etiquetas/Ejemplo/`).
- **config.py:** `DIR_MANUALES = data/manuales` debería apuntar a `data/RAG`.

### [2026-06-03] Componente 6 (MCP) preparado en el proyecto
- **Canal:** Claude↔Tú
- **Qué se hizo:** Se conectó ConsulAlim AI a la red MCP de la clase creando
  `.mcp.json` (bloque `uthagentes` HTTP + `uthagentes-local` stdio para ensayo).
  Se documentó en CLAUDE.md y se agregó `UTHAGENTES_TOKEN` a `.env.example`.
  El servidor de la clase está en `C:\Agente_Val\uthAgentes\mcp-server` (FastMCP +
  SQLite); expone registrar_estudiante, listar_estudiantes, consultar_estado,
  enviar_mensaje, historial_mensajes.
- **Hallazgos:** (1) la URL ngrok del ejemplo respondió 404 → servidor apagado
  (el docente lo enciende a ratos) y la URL ngrok-free puede cambiar; (2) el
  token no está definido aún; (3) el paquete `mcp` no está instalado (solo afecta
  al modo local de ensayo, no al HTTP).
- **Pendiente:** token + URL vigente del instructor; reabrir Claude Code para que
  cargue el MCP; correr registrar + enviar/leer un mensaje cuando esté encendido.
- **Aplicado en:** .mcp.json (nuevo), .env.example, CLAUDE.md.

### [2026-06-03] Componente 8 (repo) preparado local
- **Canal:** Claude↔Tú
- **Qué se hizo:** Se creó `README.md` (mapea los componentes), se corrigió
  `.gitignore` (quita `data/manuales`, conserva `data/etiquetas/Ejemplo/`, ignora
  `*.db` e `data/inventario.json`). `git init` + stage; **verificado que `.env`
  NO entra** (sin secretos). 33 archivos listos, incluida la rúbrica PDF (por
  decisión del usuario) y los PDFs del RTCA (los necesita el RAG del evaluador).
- **Decisión:** el usuario sube el repo con **GitHub Desktop** a su cuenta (repo
  público). Identidad/commit los hará Desktop al iniciar sesión.
- **Aplicado en:** README.md, .gitignore, repo git inicializado.

### [2026-06-03] Validación robusta: tipo/alérgeno inválidos ya no crashean
- **Canal:** Claude↔Tú
- **Qué pasó / observación:** Al probar la funcionalidad, `validar_etiqueta.py`
  se caía con un **traceback crudo** (`ValueError: 'liquido' is not a valid
  TipoProducto`) cuando el JSON traía un `tipo` fuera del enum. Mismo bug latente
  con `alergenos` (p. ej. "gluten" en vez de "trigo"): `TipoProducto(...)` y
  `Alergeno(...)` lanzaban `ValueError` pelón, no una excepción del dominio, así
  que el `try/except` de la herramienta (que captura `EtiquetaInvalida`/
  `ErrorDominio`) no lo atrapaba.
- **Regla nueva o ajuste:** Toda normalización de un enum de entrada debe lanzar
  una excepción **del dominio** con la lista de valores válidos, igual que ya
  hacían `_a_unidad` y `_a_tipo`. Una herramienta **nunca** debe terminar en
  traceback ante datos malos: devuelve JSON `{"ok": false, "error": ...}` que diga
  qué corregir. Coherente con el principio de cero inventos / pedir validación.
- **Qué se hizo:** En `src/modelos.py` se agregaron los helpers
  `_a_tipo_producto()` y `_a_alergeno()` (mismo patrón que `_a_unidad`/`_a_tipo`),
  que lanzan `EtiquetaInvalida` con los válidos. `Producto.__init__` ahora usa
  esos helpers en vez del cast crudo. No se tocó `validar_etiqueta.py` (ya
  capturaba `EtiquetaInvalida`).
- **Pruebas:** `tipo:"liquido"` → error JSON listando preenvasado/semisolido/
  bebida_alcoholica; `alergenos:["gluten"]` → error JSON listando trigo/leche/…;
  ejemplo válido sigue aprobando sin cambios.
- **Aplicado en:** src/modelos.py (helpers `_a_tipo_producto`, `_a_alergeno`;
  `Producto.__init__`).

### [2026-06-03] Bebidas alcohólicas: grado alcohólico obligatorio, advertencia legal e imagen de etiqueta
- **Canal:** Agente↔Emprendedor (y desarrollo)
- **Qué pasó / observación:** Al probar el flujo con una **bebida alcohólica
  artesanal** (vino de flor de Jamaica), el validador la aprobaba **sin exigir el
  grado alcohólico** (`% Alc./vol.`), que el RTCA de Bebidas Alcohólicas (sección
  5) sí pide. Además, al comparar con el modelo
  `data/etiquetas/Ejemplo/ETIQUETA_BEBIDA_ALCOHOLICA.png` faltaban dos cosas que
  ese ejemplo sí trae: el campo **% Alc** junto al contenido neto y la
  **advertencia legal** "EL ABUSO EN EL CONSUMO DE ESTE PRODUCTO ES NOCIVO PARA
  LA SALUD". Por último, el agente entregaba solo texto: faltaba la **imagen** de
  la etiqueta basada en los modelos de ejemplo.
- **Regla nueva o ajuste:**
  1. **Grado alcohólico obligatorio solo para `bebida_alcoholica`.** Si falta, es
     un faltante que bloquea la aprobación; en los demás tipos no se exige (regla
     condicionada por tipo, no global).
  2. **Advertencia legal automática** en bebidas alcohólicas: el sistema la añade
     siempre (constante `ADVERTENCIA_ALCOHOL`), no depende de que el emprendedor
     la escriba; se confirma como observación y se renderiza en la etiqueta.
  3. **Salida visual:** el agente genera la **imagen** de la etiqueta basándose en
     el modelo de `data/etiquetas/Ejemplo/` que corresponde al tipo de producto.
- **Qué se hizo:**
  - `src/modelos.py`: campo `Producto.grado_alcoholico` (+ `to_dict`/`from_dict`);
    constante `ADVERTENCIA_ALCOHOL` (texto tomado del modelo de ejemplo); en
    `Etiqueta.validar()` la regla 2-bis (grado obligatorio + observación de
    advertencia, solo si `tipo == BEBIDA_ALCOHOLICA`); en `Etiqueta.to_texto()`
    se renderizan el grado y la advertencia.
  - `tools/generar_etiqueta.py` (**nuevo**): dibuja la etiqueta en PNG con Pillow,
    replicando la plantilla del ejemplo según el tipo (dos columnas, datos
    obligatorios; para bebidas, `% Alc` y recuadro de advertencia). Solo genera si
    la etiqueta CUMPLE (`--forzar` para previsualizar). Sale a `data/etiquetas/`.
  - `requirements.txt`: se agregó `Pillow>=10.0`.
- **Pruebas:** bebida sin grado → faltante (no aprueba); con grado "11% Alc./vol."
  → aprueba, con advertencia en observaciones y en el texto; imagen generada fiel
  al modelo (`data/etiquetas/vino_artesanal_de_flor_de_jamaica.png`). Regresión OK:
  demo POO sigue CUMPLE y el ejemplo semisólido se aprueba **sin** pedir grado ni
  advertencia (regla bien acotada por tipo).
- **Aplicado en:** src/modelos.py, tools/generar_etiqueta.py (nuevo),
  requirements.txt.

### [2026-06-03] Web local (Streamlit) para primeras pruebas
- **Canal:** Agente↔Emprendedor (entrada) / dashboard de salida
- **Qué se hizo:** Se creó `web/app.py` (Streamlit): formulario del producto
  (tabla dinámica de ingredientes/aditivos), validación contra el RTCA reusando
  `src/modelos.py`, vista previa de la etiqueta, entrega por correo (modo simulado)
  reusando `tools/enviar_etiqueta.py`, y buscador del RAG que cita PDF y página
  (índice cacheado con `st.cache_resource`).
- **Dependencias:** `streamlit` (y `Pillow`, ya usado por generar_etiqueta.py).
- **Prueba:** la app levanta OK (health `200 ok`, sin errores). Se corre con
  `streamlit run web/app.py`.
- **Ajuste pendiente detectado:** el formulario debe incluir el **grado alcohólico**
  (campo nuevo del modelo, obligatorio para bebidas) y, a futuro, mostrar la
  imagen PNG de `tools/generar_etiqueta.py`.
- **Aplicado en:** web/app.py (nuevo), requirements.txt.

### [2026-06-03] Prueba de punta a punta (Componente 7) + 2 reglas afinadas
- **Canal:** Agente↔Emprendedor
- **Qué pasó:** Se corrió el flujo completo con una **bebida alcohólica** (vino de
  flor de Jamaica): recibir → validar (incompleta) → consultar norma (RAG) →
  retroalimentar → completar → validar (cumple) → generar imagen → entregar
  (simulado). Funcionó de principio a fin.
- **Ajustes de reglas (a partir de feedback del usuario):**
  1. **Instrucciones de conservación**: ya NO bloquean. Si el emprendedor no las
     da, el agente las **deduce** según el tipo de producto (constante
     `_INSTRUCCIONES_SUGERIDAS` + `Producto.instrucciones_efectivas()`), se
     incluyen en la etiqueta y se deja una observación para que las confirme.
  2. **Fecha de vencimiento**: pasa de faltante a **observación** ("reservar el
     espacio 'Vence: DD/MM/AA'"), igual que Registro Sanitario y Lote, porque el
     valor real se estampa al imprimir, no al diseñar.
- **Pruebas/regresión:** vino completo → CUMPLE con instrucciones deducidas y
  fecha como espacio reservado; demo POO y ejemplo semisólido siguen aprobando.
- **Bug del stdin (RESUELTO):** leer JSON por **stdin** en Windows usaba cp1252 y
  rompía acentos ("AzÃºcar"). Arreglado en `validar_etiqueta.py`,
  `enviar_etiqueta.py` y `generar_etiqueta.py`: ahora `_leer_entrada` lee
  `sys.stdin.buffer.read().decode("utf-8")`. Probado: "Azúcar" pasa bien.
- **Aplicado en:** src/modelos.py, tools/generar_etiqueta.py.

### [2026-06-04] Correo con la imagen de la etiqueta adjunta
- **Canal:** Agente↔Emprendedor (salida)
- **Qué se hizo:** `src/notificar.py` ahora acepta `adjuntos` (SMTP vía
  `msg.add_attachment` con MIME adivinado; Resend vía base64). `enviar_etiqueta.py`
  genera el PNG (`generar_imagen`) y lo adjunta automáticamente (`adjuntar_imagen=True`),
  además del texto. La web hereda la mejora sin cambios (llama a `enviar_etiqueta`).
- **Prueba:** envío real a garciavalery03@gmail.com con el adjunto
  `vino_artesanal_de_flor_de_jamaica.png`.
- **Aplicado en:** src/notificar.py, tools/enviar_etiqueta.py.

### [2026-06-04] MCP: token tomado desde el .env vía headersHelper
- **Canal:** Claude↔Tú
- **Qué pasó / observación:** El usuario quería que `.mcp.json` tomara el token
  del `.env`. Confirmado con la doc de Claude Code: `${VAR}` en `.mcp.json` solo
  se expande desde el **entorno del sistema**, NO desde el `.env` del proyecto.
  La forma oficial de leerlo del `.env` es un **`headersHelper`**.
- **Qué se hizo:** `tools/mcp_headers.py` (lee UTHAGENTES_TOKEN del entorno o del
  `.env` y emite el JSON de headers) + `tools/mcp_headers.cmd` (lo ejecuta con el
  Python real). `.mcp.json` cambió `headers` fijo → `headersHelper`. El token se
  guardó en `.env` (ignorado por git) y también como variable de entorno (setx).
- **Pruebas:** el helper emite `Authorization: Bearer …` + `ngrok-skip…`; JSON OK.
  Falta probar la conexión real (servidor de la clase aún apagado: HTTP 404).
- **Aplicado en:** .mcp.json, tools/mcp_headers.py (nuevo), tools/mcp_headers.cmd
  (nuevo), .env (token), .env.example, CLAUDE.md.

### [2026-06-04] Web rediseñada: conversación guiada (recibe según las reglas)
- **Canal:** Agente↔Emprendedor
- **Qué se hizo:** `web/app.py` pasó de formulario a **chat guiado** (st.chat_message
  / st.chat_input). Al entrar, el agente **recibe** al usuario con la bienvenida de
  `valery_garcia.md` y lo lleva paso a paso siguiendo el protocolo de captura:
  nombre (+advertencia legal), tipo, descripción, ingredientes (uno a uno, mayor a
  menor), aditivos, contenido neto, grado (si bebida), alérgenos, país, responsable,
  dirección, e instrucciones (deduce y pide confirmar). Luego valida, genera la
  imagen y ofrece enviarla por correo. Sidebar con "Empezar de nuevo" y consulta RAG.
- **Arquitectura:** máquina de pasos determinista (sin API key); el razonamiento
  libre sigue siendo de Claude Code. Parseo tolerante de texto (ingredientes,
  contenido, alérgenos) reusando las clases/herramientas existentes.
- **Prueba:** arranca OK (health 200, sin errores) en localhost:8501.
- **Aplicado en:** web/app.py (reescrito).

### [2026-06-04] Regla: manejo de omisiones en la conversación guiada
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** El usuario pidió que, con el mayor respeto, si el
  consultante quiere omitir/no responder/saltarse una pregunta, el agente pase a
  la siguiente **solo si el dato no es indispensable**; si lo es, debe indicarle
  que esa no se puede saltar.
- **Regla nueva o ajuste:**
  - **NO indispensables** (se omiten y se sigue, con valor por defecto): descripción,
    aditivos, alérgenos, instrucciones de conservación (estas se deducen por tipo).
  - **Indispensables** (no se pueden omitir; explicar por qué y volver a pedir):
    nombre, tipo, ingredientes (≥1), contenido neto, grado alcohólico (solo bebidas),
    país de origen, responsable y dirección.
  - Tono siempre de apoyo; nunca presionar ni regañar.
- **Qué se hizo:** En `web/app.py` se añadió `quiere_saltar()` y un bloque en
  `procesar()` que aplica la regla (avanza con default o insiste según el paso).
  Se documentó la regla en `valery_garcia.md` (sección "Manejo de Omisiones").
- **Aplicado en:** web/app.py, valery_garcia.md.

### [2026-06-04] Caso lachiquitasabrosa (Mermelada de Melocotón): 3 errores corregidos
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** Revisando la etiqueta que el agente generó para
  *lachiquitasabrosa S.A de R.l* (`data/etiquetas/mermelada_de_melocoton.png`)
  aparecieron tres fallas:
  1. **Marco conversacional en la etiqueta (bug).** En conservación quedó literal
     *"quisiera que le agregaras Una vez abierto refrigerese"*. El consultante hizo una
     **petición** y el agente la guardó entera como instrucción (en `app.py`,
     `paso == "instrucciones"` hacía `d["instrucciones"] = t` sin limpiar).
  2. **Aditivos como ingredientes comunes, sin INS.** Pectina, ácido cítrico y sorbato de
     potasio se declararon dentro de la lista de ingredientes, sin su función ni número INS.
  3. **Sin tildes / ortografía** (MELOCOTON, azucar, acido citrico, refrigerese).
- **Regla nueva o ajuste:**
  1. Toda entrada de texto libre se **limpia** del marco de petición antes de estamparse:
     se guarda solo la leyenda (helper `limpiar_instruccion`).
  2. Las sustancias que son aditivos se declaran por **función + INS/SIN** (RTCA 419-2019),
     no como ingredientes comunes.
  3. Normalizar acentos y mayúscula inicial en los datos de la etiqueta, sin alterar el sentido.
- **Qué se hizo:**
  - `web/app.py`: helper `limpiar_instruccion()` (+ regex de marcos de petición e
    imperativos); se aplica en el paso `instrucciones`. Probado con varios casos.
  - `valery_garcia.md`: nueva sección **"Limpieza y Normalización de los Datos del
    Consultante"** (marco conversacional, ortografía/tildes, separar aditivos con INS).
  - Se **regeneró** la etiqueta de lachiquitasabrosa con los datos corregidos.
- **Aplicado en:** web/app.py, valery_garcia.md, data/etiquetas/mermelada_de_melocoton.png.

### [2026-06-04] Mascota "Aguacatito" integrada en la web
- **Canal:** Agente↔Emprendedor
- **Qué se hizo:** El usuario aportó una imagen propia (generada con Gemini) de un
  aguacate partido con gorro de chef y cucharita. Se copió a
  `web/assets/aguacatito.png` y se integró en `web/app.py` como **avatar del agente**
  en el chat y como imagen en la barra lateral; el agente se presenta como Aguacatito.
- **Nota:** se exploraron mascotas dibujadas en SVG (`web/mascotas_demo.py`), pero
  se optó por usar la imagen del usuario "tal cual" (idéntica). Con imagen estática
  no hay cambio de expresión por paso; si se quiere, habría que generar variantes
  (feliz/pensando/aprobar) y cambiarlas según el paso del chat.
- **Aplicado en:** web/app.py, web/assets/aguacatito.png (nuevo).

### [2026-06-04] Aguacatito reactivo (1ª versión) con expresiones y movimiento
- **Canal:** Agente↔Emprendedor
- **Qué se hizo:** Se eligió volver a la **primera versión** de la mascota
  (aguacate con la carita en la **pulpa**, colores planos) en `web/mascota.py`,
  con 6 expresiones (feliz, sorpresa, pensando, guiño, ánimo, triste), **burbuja**
  de frase y **movimiento del cuerpo** (flota + vaivén/mecido + brazo que saluda).
- **Reactividad:** `web/app.py` cambia `st.session_state.expresion` según el paso
  (saludo→feliz, aditivo/alérgeno→sorpresa, deduciendo→pensando, cumple→guiño,
  dato obligatorio no omitible→triste). Vive en la barra lateral.
- **Nota:** se descartó la versión con cara en la semilla y el look "sticker"
  (degradados/contorno). La imagen PNG del usuario queda como avatar pequeño en el
  chat; si se quieren expresiones con ESE arte, generar variantes
  `web/assets/aguacatito_<expr>.png` y la web las usa automáticamente.
- **Aplicado en:** web/mascota.py, web/app.py.

### [2026-06-04] Aguacatito dentro del chat (no en la barra lateral)
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** El usuario quiere que Aguacatito interactúe dentro de
  la conversación, no parado en la barra lateral.
- **Qué se hizo:** En `web/app.py` se movió el Aguacatito reactivo **arriba del
  chat** (presidiendo la conversación; cambia de expresión y muestra burbuja cada
  turno). La barra lateral quedó con su retrato fijo (imagen del usuario), y su
  carita sigue como avatar de cada mensaje del agente.
- **Aplicado en:** web/app.py.

### [2026-06-05] Limpieza: se deja solo la mascota en uso
- **Canal:** Claude↔Tú
- **Qué se hizo:** Se eliminó `web/mascotas_demo.py` (contenía las mascotas
  descartadas: Consu, Hamby y los Aguacatitos previos). Queda únicamente la
  mascota en uso: `web/mascota.py` (Aguacatito carita en la pulpa) + el avatar
  `web/assets/aguacatito.png`. Verificado que `app.py` solo importa `mascota`.
- **Aplicado en:** se eliminó web/mascotas_demo.py.

### [2026-06-05] Web: una sola mascota (se quita el PNG)
- **Canal:** Agente↔Emprendedor
- **Qué se hizo:** En la web convivían dos depicciones de Aguacatito (el SVG
  dibujado y el PNG del usuario). Se dejó **solo el SVG** (`web/mascota.py`): se
  quitó `st.image(MASCOTA)` de la barra lateral, el avatar de los mensajes pasó a
  "🥑", se eliminó la constante MASCOTA y el archivo `web/assets/aguacatito.png`
  (el original del usuario permanece en su carpeta Descargas).
- **Aplicado en:** web/app.py; se eliminó web/assets/aguacatito.png.

### [2026-06-05] Caso tortilla (Luna S.A): el agente YA reconoce aditivos y alérgenos por sí mismo
- **Canal:** Agente↔Emprendedor (y desarrollo)
- **Qué pasó / observación:** Probando en la web una *Tortilla de maíz sabor queso*
  (Luna S.A de R.L, `data/etiquetas/tortilla_de_maiz_sabor_queso.png`) reaparecieron
  los 3 errores de lachiquitasabrosa, pero más graves porque la lista venía **pegada**:
  1. **Aditivos sin función ni INS**, metidos en un párrafo corrido (glutamato
     monosódico, ácido cítrico, tartrazina, amarillo ocaso FCF, dióxido de silicio,
     guanilato/inosinato de sodio, caramelo IV…).
  2. **Sin leyenda "Contiene:"** pese a tener trigo (harina de trigo) y leche
     (sólidos de leche, leche entera, caseinato de sodio) → fallo legal y de seguridad.
  3. **Sin acentos/ortografía** (Maiz, monosodico, citrico, almidon, dioxido…).
  La causa raíz era **de diseño**: el flujo le pedía al consultante que *dictara* la
  función e INS de cada aditivo y que *escribiera* los alérgenos. El usuario aclaró
  que **identificar aditivos y alérgenos solo es tarea PRIMORDIAL del agente**, no del
  consultante (la mayoría no los conoce).
- **Regla nueva o ajuste:**
  1. El agente **reconoce y clasifica** los aditivos por sí mismo (función + INS,
     formato RTCA `Función (Nombre, INS xxx)`), aunque el consultante solo escriba el
     nombre común o pegue la lista entera.
  2. El agente **detecta los alérgenos** a partir de los ingredientes y **declara
     siempre** la leyenda *Contiene: …* (dato legal, no opcional: omitir no la borra).
  3. **Cero inventos en dosis:** no se fija dosis máxima (depende de la categoría de
     alimento); se consulta en la norma/RAG.
  4. La **tabla curada a mano manda**; la lista extraída de la norma es solo respaldo.
- **Qué se hizo:**
  - `src/conocimiento.py` (**nuevo**): el "saber" del agente — tabla curada de ~64
    aditivos (nombre/sinónimos → función → INS), patrones de 9 alérgenos y corrector
    ortográfico. Funciones `identificar_aditivo`, `detectar_alergenos`,
    `corregir_ortografia`, `separar_ingredientes`. La detección de alérgenos corre
    sobre el **texto original** del consultante (no solo el nombre canónico), para no
    perder señales (p. ej. "lecitina **de soya**" → soya).
  - `tools/construir_aditivos.py` (**nuevo**) + `data/aditivos_rtca.json` (**nuevo**):
    extrae con `pdfplumber` la columna **Función** del Anexo A del
    `RTCA_419-2019-ADITIVOS` (182 aditivos únicos de 1006 filas, voto por mayoría).
    Sirve de **respaldo de cola larga**; la tabla manual tiene prioridad por INS y por
    nombre. `conocimiento.py` lo carga con `_cargar_base_norma()`.
  - `src/modelos.py`: `Aditivo.declaracion()` pasó de `Nombre · INS` a
    `Función (Nombre, INS xxx)` (formato que pide el RTCA).
  - `web/app.py`: los pasos **ingredientes/aditivos/alérgenos** se reescribieron para
    auto-clasificar (acepta pegar la lista completa o ir uno por uno) y auto-detectar;
    ya no se le pide al consultante que dicte función/INS ni que liste alérgenos a mano.
  - `tools/generar_etiqueta.py`: el lienzo pasó a **altura dinámica** (mide el
    contenido y crece para que no se desborde la lista; fuente algo menor si es muy
    larga). Antes una lista larga se encimaba con el bloque inferior.
  - `probar_flujo.py` (**nuevo**): arnés que maneja el diálogo de la web sin navegador
    (stub de Streamlit) y verifica el flujo de punta a punta.
- **Aprendizaje técnico:**
  1. La **función de un aditivo no es única** en el RTCA 419 (cada aditivo lista varias
     según la categoría de alimento), así que la auto-extracción da una función
     *plausible* pero no autoritativa → por eso la tabla curada es la fuente de calidad
     y la norma solo respalda la cola larga.
  2. Los **INS de 4 cifras** (1400, 1520…) se truncaban a 3 con un regex `\d{3}`; se
     corrigió a `\d{3,4}` en el extractor y en la búsqueda por INS.
  3. **Falso positivo de sulfitos:** el nombre "Caramelo sulfito amónico (clase IV)"
     disparaba el alérgeno; el patrón se acotó a los **agentes sulfitantes reales**
     (metabisulfito, bisulfito, SO₂…), no la palabra "sulfito" suelta.
  4. `pdfplumber` (no pypdf) es lo que aísla bien las **columnas** de una tabla en PDF.
- **Pruebas:** `python probar_flujo.py` → todo verde (tortilla preenvasada con 13
  aditivos clasificados + "Contiene: trigo, leche"; vino con grado + advertencia +
  sulfitos por el metabisulfito). Etiquetas larga y corta renderizan sin encimarse.
  Regresión: la manual gana (Dióxido de silicio→Antiaglomerante, Pectina→Gelificante,
  Lecitina→Emulsionante) y la cola larga ahora se reconoce (INS 415, 1400, 1520…).
- **Aplicado en:** src/conocimiento.py (nuevo), tools/construir_aditivos.py (nuevo),
  data/aditivos_rtca.json (nuevo), probar_flujo.py (nuevo), src/modelos.py,
  web/app.py, tools/generar_etiqueta.py, requirements.txt (pdfplumber).
- **Pendiente (opcional):** reflejar en `valery_garcia.md` que la regla de
  reconocimiento de aditivos/alérgenos ya está **automatizada en código** (antes solo
  documentada); y, si se quiere, regenerar la etiqueta real de la tortilla.

### [2026-06-05] Caso galleta (LA CHIQUI): variantes/typos de aditivos, duplicados y tolerancia a tipeo
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** Probando en la web una *Galleta con chispas de chocolate*
  (LA CHIQUI S.A, `data/etiquetas/galleta_con_chispas_de_chocolate.png`), el flujo ya
  arreglado de aditivos/alérgenos funcionó (detectó *Contiene: trigo, leche, soya* y
  clasificó propilenglicol y los caramelos), pero se colaron fallos por **variantes mal
  escritas** que el reconocimiento exacto no atrapaba:
  1. **"Lectina de soya"** (typo de *lecitina*) no se reconoció como aditivo y además
     quedó **DUPLICADA** en la lista. Debía ser *Emulsionante (Lecitina, INS 322)*.
  2. **"monoestarato de glicerol"** (typo de *monoestearato*) quedó como ingrediente
     común. Es *Emulsionante (INS 471)*.
  3. **"estearoil lactilato de sodio"** no estaba en la base. Es *Emulsionante (INS 481)*.
  4. Ortografía menor sin corregir: *butirica*→butírica, *chipas*→chispas.
- **Regla nueva o ajuste:**
  1. La base de aditivos incluye **variantes y errores de tipeo comunes** como sinónimos
     (p. ej. "lectina"→lecitina, "monoestarato"→monoestearato), y se añadió el INS 481.
  2. **Tolerancia a tipeos leves**: si no hay match exacto, se busca el aditivo más
     parecido (difflib), **solo para nombres largos (≥8) y con similitud ≥0.88**, para
     no generar falsos positivos en materias primas (regla de cero inventos).
  3. La captura **elimina ingredientes duplicados** (no repite el mismo nombre).
  4. Se ampliaron las correcciones ortográficas (butírica, chispas, etc.).
- **Qué se hizo:**
  - `src/conocimiento.py`: sinónimos/typos en INS 322 y 471; nuevo INS 481
    (estearoil-2-lactilato de sodio); paso 4 de `identificar_aditivo` con `difflib`
    (acotado a nombres largos y cutoff 0.88); nuevas entradas en `_CORRECCIONES`.
  - `web/app.py`: `registrar_ingrediente` ahora **deduplica** (devuelve flag
    `es_duplicado`); el paso de ingredientes informa los repetidos omitidos.
  - Se **regeneró** la etiqueta de la galleta con los datos corregidos.
- **Pruebas:** los 3 aditivos ahora se reconocen (incluso con typo y con coma de por
  medio); 11 materias primas comunes (harina de trigo, leche entera, manteca de cacao,
  grasa butírica, saborizante artificial…) **no** dan falso positivo; `probar_flujo.py`
  sigue todo en verde. Etiqueta regenerada sin duplicados y sin desbordarse.
- **Límite conocido:** si el consultante escribe el nombre de UN aditivo **partido por
  una coma** (lista: "…, estearoil, lactilato de sodio, …"), la coma lo separa en dos
  ítems antes de reconocerlo; conviene escribir cada aditivo sin comas internas.
- **Aplicado en:** src/conocimiento.py, web/app.py,
  data/etiquetas/galleta_con_chispas_de_chocolate.png.

### [2026-06-05] Caso bebida carbonatada: falso "Contiene: leche" por subcadena + "bebida" no es alcohol
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** Al etiquetar una *Bebida carbonatada sabor a Coca-Cola*
  (`data/etiquetas/bebida_carbonatada_sabor_a_coca_cola.png`), la etiqueta declaró
  **"Contiene: leche"** aunque el producto **no lleva leche** (es agua carbonatada,
  azúcar, caramelo IV, ácido fosfórico, saborizantes y cafeína). El usuario lo
  confirmó. Causa: el patrón del alérgeno *leche* incluía `nata` y coincidía **dentro
  de** "agua carbo**nata**da" (coincidencia por subcadena). Además se detectó un **bug
  latente**: la palabra "bebida" estaba en el disparador de *bebida alcohólica*, así
  que un jugo/gaseosa podía clasificarse como alcohólico y pedir grado.
- **Regla nueva o ajuste:**
  1. Los patrones de alérgenos usan **límites de palabra** (`\b…\b`) en los términos
     cortos, para no coincidir dentro de otra palabra (nata/queso/yema/atún/salmón…).
  2. La detección de **tipo** solo marca *bebida alcohólica* con palabras inequívocas
     (alcohólica, vino, licor, cerveza, ron, tequila, whisky, vodka, etc., con límites
     de palabra para que "ron" no coincida en "limón/macarrón"); **"bebida" sola NO**.
  3. Más correcciones ortográficas: cafeína, fosfórico.
- **Qué se hizo:**
  - `src/conocimiento.py`: `_PATRONES_ALERGENO` reescrito con `\b…\b` (quitado el
    `nata` suelto y el `ovo` suelto que también era riesgoso); nuevas correcciones.
  - `web/app.py`: `parse_tipo` usa regex con límites de palabra y ya no incluye
    "bebida" como disparador de alcohol.
  - Se **regeneró** la etiqueta de la bebida (ya sin la leyenda de leche).
- **Pruebas:** "agua carbonatada…" → **sin alérgenos** ✓; siguen detectándose los
  reales (tortilla→trigo/leche, galleta→trigo/leche/soya, mayonesa→huevo,
  surimi→pescado, vino→sulfitos); tipos: "bebida carbonatada"/"jugo de limón"/
  "macarrones"→no alcohol, "vino/ron/licor"→alcohol. `probar_flujo.py` todo verde.
- **Pendiente menor (visual):** los **nombres muy largos** desbordan el título (fuente
  fija 52); convendría auto-reducir el tamaño del título cuando no quepa.
- **Aplicado en:** src/conocimiento.py, web/app.py,
  data/etiquetas/bebida_carbonatada_sabor_a_coca_cola.png.

### [2026-06-05] Título de la etiqueta con auto-ajuste (nombres largos ya no se desbordan)
- **Canal:** Agente↔Emprendedor (salida visual)
- **Qué pasó / observación:** En la *Bebida carbonatada sabor a Coca-Cola* el nombre
  era tan largo que el **título tocaba/desbordaba los bordes** del marco, porque la
  fuente del título era de **tamaño fijo (52)**.
- **Regla nueva o ajuste:** El título **se reduce automáticamente** hasta que el nombre
  cabe dentro del ancho del marco (entre 52 y 24 px), conservando el centrado.
- **Qué se hizo:** `tools/generar_etiqueta.py`: nuevo helper `_fuente_que_cabe()` que
  elige el mayor tamaño con el que el texto entra en el ancho disponible; el título lo
  usa en vez de la constante fija. Se regeneró la etiqueta de la bebida.
- **Pruebas:** la bebida (nombre largo) ya no se desborda; nombres normales siguen a
  tamaño 52. `probar_flujo.py` todo verde.
- **Aplicado en:** tools/generar_etiqueta.py,
  data/etiquetas/bebida_carbonatada_sabor_a_coca_cola.png.

### [2026-06-05] Marca propia como campo + envío de correo OBLIGATORIO al aprobar
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** El usuario pidió dos cosas: (1) que el agente **pregunte
  la marca** del producto y se vea en la etiqueta (antes el "Marca:" de la etiqueta
  reusaba el nombre del responsable/fabricante, no una marca propia); (2) que, **si la
  etiqueta está aprobada, se envíe sí o sí al correo del emprendedor** (percibía que no
  se pedía el correo / no se enviaba). Diagnóstico: el envío SÍ estaba implementado y el
  SMTP configurado (`validar_correo()=True`), pero el correo se pedía al final como algo
  **opcional** ("…o escribe no"), poco visible.
- **Regla nueva o ajuste:**
  1. Nuevo paso **"marca"** (después del nombre), **opcional** (si no tiene marca,
     escribe "no"). Se guarda en `Producto.marca` y la etiqueta muestra esa marca; si
     no se dio, cae al responsable o al nombre (como antes).
  2. El **correo es obligatorio cuando la etiqueta CUMPLE**: el agente lo pide de forma
     explícita y **no avanza** hasta recibir un correo **válido**; entonces envía la
     etiqueta (imagen + datos). Solo se puede salir reiniciando.
- **Qué se hizo:**
  - `src/modelos.py`: campo `Producto.marca` (+ `to_dict`/`from_dict`); `to_texto()`
    muestra "Marca: …".
  - `tools/generar_etiqueta.py`: el rótulo "Marca:" usa `p.marca or responsable or nombre`.
  - `web/app.py`: paso `marca` (y su omisión opcional); el paso `enviar` ahora exige
    correo **válido** (valida con `notificar.email_valido`), envía con
    `enviar_etiqueta(...)` y, si el envío falla, se queda para reintentar; se quitó la
    salida con "no". Se importó `email_valido`.
  - `probar_flujo.py`: cubre el paso de marca y que el correo es obligatorio (sin
    enviar correos reales).
- **Pruebas:** `probar_flujo.py` todo verde (marca capturada y mostrada; el paso de
  envío no avanza con texto que no es correo). Render con marca propia (“Doña Rosa”)
  distinta del fabricante: se ve correcto.
- **Nota:** el envío real usa el SMTP del `.env` y manda copia oculta a la dirección
  configurada (`CORREO_COPIA_OCULTA`). Si el SMTP fallara, el agente lo informa y
  ofrece reintentar con otro correo.
- **Aplicado en:** src/modelos.py, tools/generar_etiqueta.py, web/app.py, probar_flujo.py.

### [2026-06-05] Caso refresco (Canada Dry): "ok" se colaba como ingrediente
- **Canal:** Agente↔Emprendedor
- **Qué pasó / observación:** En un *Refresco carbonatado 100% sabor natural con jengibre*
  (marca Canada Dry, `data/etiquetas/refresco_carbonatado_100_sabor_natural_con_jengibre.png`)
  todo salió bien (título largo auto-ajustado; **Marca: Canada Dry** separada del
  fabricante; aditivos clasificados: ác. cítrico 330, benzoato 211, caramelo IV 150d,
  **sucralosa 955**, **acesulfame 950**; sin falso alérgeno), **excepto** que al final de
  la lista de ingredientes apareció **"ok"** como si fuera un ingrediente. Causa: el
  emprendedor escribió "ok" para cerrar la lista, pero `es_fin()` solo reconocía
  "listo/fin/ya/terminé", así que "ok" se registró como ingrediente.
- **Regla nueva o ajuste:** `es_fin()` reconoce más formas de "terminé": **ok, okay,
  okey, vale, dale, correcto, eso es todo, es todo, nada más, no más, finalizar, ya
  está** (además de listo/fin/ya/terminé). Aplica tanto al paso de **ingredientes**
  como al de **aditivos** (ambos usan `es_fin`).
- **Qué se hizo:** `web/app.py`: se amplió `es_fin()` con esas variantes (con límites de
  palabra para no coincidir dentro de otras, p. ej. "ya" no matchea en "papaya"). Se
  regeneró la etiqueta del refresco sin el "ok".
- **Pruebas:** `probar_flujo.py` todo verde; "ok"/"vale"/"eso es todo" cierran la lista
  y ya no se agregan como ingrediente.
- **Aplicado en:** web/app.py,
  data/etiquetas/refresco_carbonatado_100_sabor_natural_con_jengibre.png.

<!-- Próximas entradas debajo de esta línea -->
