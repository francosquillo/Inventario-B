# Design — paso-5h2-filtro-categoria-stock (C-06h2)

## Context

Ver `proposal.md` (Why) y `specs/interfaz-web/spec.md`. Estado actual del código:

- `static/index.html` → plantilla `tpl-mline`: `.mline-head` = número · `select[data-producto]` · "Quitar"; `.mline-body` = aviso de dado de baja, modo + valor + delta y `.mline-two` (nombre nuevo + selector **"Categoría"** `select[data-categoria]`, que cambia la categoría del producto al guardar).
- `static/js/inventario.js`:
  - `llenarSelectMod(select, ocupados, conservar)` arma los grupos "Activos" (`productos`) y "Dados de baja" (`inactivos`), salta los grupos vacíos, deshabilita lo elegido en otras líneas y, con `conservar`, deja visible un código que ya no existe ("(ya no existe)").
  - `refrescarSelectsMod(conservar)` calcula los `ocupados` de cada línea **antes** de rellenar y después llama a `actualizarLineaMod` en todas.
  - `alCambiarLineaMod` (delegado en `#mod-lineas`) distingue producto / categoría / modo; al elegir producto propone el valor ("Fijar en") y precarga la Categoría con `elegirCategoria`.
  - Ya existen, de C-06e, `Busqueda.porCategoria(lista, cat)`, `Busqueda.productoSigueVisible(codigo, lista, cat)`, `Busqueda.SIN_CATEGORIA` y `llenarSelectCategoria(select, primera, conSin)` (usado por el filtro de "Nueva orden" con `"Todas", true`).
- No hay pruebas que ejecuten `inventario.js` (usa DOM): se fija con guardas estáticas (`tests/test_frontend_*.py`) y la lógica pura de `busqueda.js` con Node (`tests/test_busqueda_js.py`).

## Goals / Non-Goals

**Goals:** filtro por línea que reutiliza la lógica de C-06e sin duplicarla; ningún cambio de backend; el filtro nunca altera lo que se envía.

**Non-Goals:** buscador de texto dentro del selector; persistir el filtro; tocar "Nuevo ingreso" o "Nueva orden"; función pura nueva en `busqueda.js` (no hace falta: `porCategoria` ya acepta cualquier lista).

## Decisions

### D1 — Ubicación: en la cabecera de la línea, antes del producto (mockups S1–S3)
`.mline-head` pasa a: número · **filtro** · producto · "Quitar". Ambos selectores llevan **etiqueta visible** (`.mlabel`): "Filtrar por categoría" y "Producto". Grilla: ≥ 640 px una fila `1.25rem 12rem minmax(0,1fr) auto` (`align-items:start`; número y "Quitar" con `margin-top:1.25rem` para quedar a la altura de los campos, debajo de las etiquetas); < 640 px dos filas: `n filtro quitar` / `. producto producto` (390 px sin scroll horizontal, producto a todo el ancho).
- *Por qué*: misma lectura que "Nueva orden" (primero se acota, después se elige) y la etiqueta visible evita confundirlo con "Categoría" (que queda abajo, en `.mline-two`, con su etiqueta de siempre).
- *Alternativas*: (a) solo `aria-label` como en "Nueva orden" → descartada: "Nueva orden" tiene encabezados de columna, "Modificar stock" no, y un "Aceite" suelto junto a otro selector de categoría confunde; (b) filtro en `.mline-body` → queda después del producto (lectura invertida); (c) un único filtro para todo el modal → el pedido es por línea, igual que "Nueva orden".
- **Ancho del modal: de 40rem a 44rem** (el de "Nueva orden", `modal-wide`). Con 40rem la primera captura recortaba "Todas las categor…" y la etiqueta del producto (≈ 300 px); con 44rem y el filtro en 12rem ambos se leen completos (≈ 340 px para el producto). No toca tokens: es el ancho que ya usa otro modal.

### D2 — Opciones del filtro
`llenarSelectCategoria(select, "Todas las categorías", true)`: "Todas las categorías" (`""`), las categorías del catálogo (orden alfabético que ya devuelve la API) y "Sin categoría" (`Busqueda.SIN_CATEGORIA`). Se usa "Todas las categorías" (como el filtro del inventario) y no "Todas" (como "Nueva orden") porque acá no hay encabezado de columna que lo contextualice. `llenarSelectoresCategoria` agrega `#mod-lineas select[data-filtro]` para refrescarlos al recargar el catálogo (conserva el valor si sigue existiendo; si no, vuelve a "Todas las categorías").

### D3 — Filtrado de los grupos
`llenarSelectMod(select, ocupados, conservar, categoria)`: los grupos pasan a `[["Activos", Busqueda.porCategoria(productos, categoria)], ["Dados de baja", Busqueda.porCategoria(inactivos, categoria)]]`; el resto del armado (grupo vacío oculto, "ya está en otra línea") no cambia. El previo se conserva si `Busqueda.productoSigueVisible(previo, productos.concat(inactivos), categoria)`; si el previo **existe pero quedó fuera del filtro** se resetea a "Elegí un producto…"; si **ya no existe** y `conservar`, se mantiene la opción "(ya no existe)" de hoy (no depende del filtro).

### D4 — Cambio del filtro = deseleccionar si no pertenece
En `alCambiarLineaMod`, rama `select[data-filtro]`: si el producto elegido no sigue visible, se pone el producto en `""` y se aplica **lo mismo que al elegir "Elegí un producto…"** (valor propuesto vacío en "Fijar en", Categoría en "Sin categoría", sin aviso ni delta); luego `refrescarSelectsMod(false)` para que las demás líneas liberen el código. El reseteo se hace **antes** de `refrescarSelectsMod`, porque este calcula los `ocupados` con los valores previos al rellenado. Si el producto pertenece, no se toca nada de la línea (valor, Categoría, nombre).

### D5 — Ayuda de lista vacía
`actualizarAyudaMod(li)`: si el filtro no es "" y ambos grupos filtrados están vacíos, agrega `<p class="help" id="mod-<k>-vacio">No hay productos en esta categoría.</p>` como primer hijo de `.mline-body` y `aria-describedby` en el producto; si no, la quita. Se llama desde `refrescarSelectsMod` (cubre filtro, alta de línea y recarga). No reutiliza `actualizarAyudaLinea` porque esa depende de `selectCategoria`/`selectProducto` de "Nueva orden" (`data-cat`/`data-opts`) y solo mira activos; se comparte el texto con una constante `AYUDA_SIN_PRODUCTOS`.
- *Interacción con `aria-describedby`*: si la línea se marca con un error, `UI.invalido` reemplaza la descripción del producto; `limpiarMarcaMod` la quita y el siguiente `refrescarSelectsMod` vuelve a asociar la ayuda.

### D6 — Accesibilidad y renumeración
`renumerarMod`: filtro con `id="mod-<k>-fil"`, su `<label data-filtro-etiqueta for=…>` y `aria-label="Filtrar por categoría, línea N"`; producto con `id="mod-<k>-prod"`, `<label data-producto-etiqueta for=…>Producto</label>` y su `aria-label` de hoy ("Producto de la línea N"). Foco visible y alto ≥ 44 px vienen de `.field` (design system). El orden de tabulación queda filtro → producto → Quitar → modo → valor → nombre → Categoría.

### D7 — Cuerpo de la petición sin cambios
`leerLineasMod` no lee el filtro; `POST /api/stock/modificaciones` sigue igual. Guarda estática que lo fija.

### D8 — Tests (Strict TDD, `unittest`)
- `tests/test_busqueda_js.py` (Node): triangulación de `porCategoria`/`productoSigueVisible` con listas de **dados de baja** y la unión activos + dados de baja (con `SIN_CATEGORIA` y categoría sin productos). Pasan desde el primer run (comportamiento ya existente): son red de seguridad de la reutilización, no RED.
- `tests/test_frontend_filtro_modificar.py` (guardas estáticas, RED reales): plantilla con `select[data-filtro]` antes de `select[data-producto]` y etiquetas "Filtrar por categoría"/"Producto"; `llenarSelectMod` usa `Busqueda.porCategoria` sobre `productos` e `inactivos` y `productoSigueVisible`; rama `data-filtro` en `alCambiarLineaMod`; `llenarSelectoresCategoria` incluye `data-filtro` con "Todas las categorías"; texto de ayuda; `leerLineasMod` sin filtro; `renumerarMod` con "Filtrar por categoría, línea "; CSS de `.mline-head` con la columna del filtro; sin `innerHTML`.
- Comportamiento en el navegador: verify con Playwright sobre una copia de `dev-local.db` contra los mockups.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-27)
- Mockups: openspec/changes/paso-5h2-filtro-categoria-stock/mockups/ (`modificar-stock.html`, `README.md`)
- Visual verify: passed (2026-11-27; Playwright 1440x900 y 390x844 sobre copia de dev-local.db, capturas en `mockups/verify/`: S1/S2/S3 desktop, S1/S3 mobile, foco del filtro; consola sin errores, red sin pedidos fallidos; cuerpo del POST sin campo de filtro; sin scroll horizontal a 390 px). Pantallas no capturadas: errores de línea y resumen tras guardar (sin cambios).
- Approval: approved (2026-11-27, by user) — incluye D1 (filtro antes del producto, etiquetas "Filtrar por categoría" / "Producto", default "Todas las categorías") y modal de 40rem a 44rem
- Preview: rendered (2026-11-27, 390x844 y 1440x900 vía http local, página completa con `?captura&largo`; `mockups/previews/modificar-stock-S1-{mobile,desktop}.png`, `modificar-stock-S2-{mobile,desktop}.png`, `modificar-stock-S3-{mobile,desktop}.png`)
- Independent verify: PASS WITH WARNINGS (2026-11-27)

Base: modal "Modificar stock" de `static/index.html` (ensanchado a 44rem, D1) y mockup M1 aprobado de C-06e, tokens `design-system/tokens.css` + `ui.css`, tema oscuro único, cabecera de texto "Inventario". Solo los estados que cambian:

| ID | Estado |
|----|--------|
| S1 | Modal con dos líneas, filtro en "Todas las categorías": línea 1 `FIL-01` elegido (Categoría "Filtro"), línea 2 vacía |
| S2 | Línea 2 filtrada por "Motor": selector desplegado (ilustración) con "Activos" `MOT-01`, `MOT-02` y "Dados de baja" `C-99`; `FIL-01` de la línea 1 no aparece |
| S3 | Línea 2 filtrada por "Hélices" (sin productos): producto solo "Elegí un producto…" + ayuda "No hay productos en esta categoría." |

Sin mockup propio (justificado en `mockups/README.md`): el reseteo al cambiar el filtro (la línea queda como S1 línea 2), "Sin categoría" (mismo control que S2), errores de la línea (estilos ya aprobados), resumen tras guardar (sin cambios).

## Risks / Trade-offs

- [La cabecera de cada línea gana una fila de etiquetas (~18 px) y en móvil una fila más] → aceptable: el modal ya scrollea; se valida en 390 px en los mockups.
- [Producto más angosto en escritorio (≈ 340 px dentro de 44rem): nombres muy largos se recortan en el cerrado] → el `<select>` nativo muestra la etiqueta completa al desplegar (S2); el modal pasa a 44rem (D1).
- [Reseteo silencioso al filtrar fuera del producto elegido] → mismo comportamiento ya aprobado en "Nueva orden"; la línea muestra "Elegí un producto…" y el valor se vacía, visible antes de guardar.
- [Recarga de productos (404) con un producto recategorizado desde otra pestaña quedando fuera del filtro] → se resetea (D3); caso raro, y el usuario lo ve antes de guardar.

## Migration Plan

Sin migración ni cambios de API: es solo `static/`. Rollback = revertir `index.html`, `inventario.js` y `app.css`.
