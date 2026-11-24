# Design — paso-5c-buscador-pdf (C-06c)

## Context

Ver `proposal.md` (Why). Estado actual observado (C-01..C-06b archivados):

- **Inventario** (`static/index.html`, `static/js/inventario.js`): `cargar()` pide `GET /api/inventario` (lista completa de activos, sin paginar) y guarda el array en `productos`; `pintarTabla()` arma las filas con `UI.el` (sin `innerHTML`) y escribe el conteo "N productos" en `#inv-conteo`. Estados `cargando | error | datos | vacio` en `mostrarEstado`. El inventario se recarga (`cargar(false)`) tras nuevo ingreso, modificación, orden y baja. La cabecera del panel (`#inv-panel > div`) tiene el título "Inventario" y el conteo.
- **No existe `GET /api/productos`** (el roadmap lo menciona como hipótesis): el listado de activos es `GET /api/inventario`; `/api/productos` solo tiene `POST`, `GET /inactivos` y `DELETE /{codigo}`.
- **Órdenes** (`static/ordenes.html`, `static/js/ordenes.js`): `articulo(o)` arma un `<article class="ord">` con `.ord-head` (número, fecha, "N componentes", botón "Eliminar" con `ml-auto`) y la tabla de componentes. Cada orden de `GET /api/ordenes` trae `id`, `numero`, `fecha`, `usuario` y `componentes`.
- **Usuario**: `sesion.js` lo escribe en `#usuario-nombre` desde `GET /api/me`.
- **CSS**: `tokens.css` y `ui.css` son copias byte a byte del design system (test `CopiasDelDesignSystemTest`); lo propio de la app va a `static/css/app.css` (decisión 13 de C-06b). Tema oscuro único; ninguna regla `@media print` hoy.
- **Tests de JS**: `tests/test_validacion_js.py` ejecuta funciones puras de `validacion.js` con Node (`window = {}` + `require`), y se omite sin Node; `tests/test_frontend_estatico.py` tiene las guardas estáticas (estructura, sin `innerHTML`, campos etiquetados, endpoints usados).
- **Cabeceras de página** (`CABECERAS_PAGINA`): sin CSP; `window.print()` no requiere cambios.

## Goals / Non-Goals

**Goals:**
- Búsqueda instantánea por código o nombre parcial, sin tocar la API ni la paridad de C-07.
- Un mecanismo de exportación a PDF único y reutilizable (C-06d lo usa para su reporte), sin dependencias nuevas.
- Cero cambios de backend: la suite de API, services y repositorios no cambia aserciones; OpenAPI conserva sus rutas.

**Non-Goals:**
- Búsqueda en el servidor, paginación, búsqueda de órdenes por producto, búsqueda en los selectores de "Modificar stock" / "Nueva orden".
- Generación de PDF en el servidor o descarga directa de un archivo sin diálogo.
- Exportar la lista completa de órdenes (decisión del usuario: exportación por orden).
- Exportar a CSV/Excel.

## Decisions

### D1 — Búsqueda en el navegador (decisión 1)

`static/js/busqueda.js` (nuevo, **puro**: sin DOM ni `fetch`, expone `window.Busqueda`):
- `normalizar(texto)`: `String(texto ?? "")` → `trim()` → `toLowerCase()` → `normalize("NFD")` sin marcas diacríticas (`/[̀-ͯ]/g`). Así `TORICA` coincide con "tórica" y `ñ` se compara como `n` (aceptado).
- `filtrar(productos, texto)`: texto normalizado vacío → la misma lista; si no, los productos cuyo `normalizar(codigo)` o `normalizar(nombre)` **contiene** el texto normalizado completo (una sola subcadena; decisión 7). Conserva el orden de entrada.
- `conteo(visibles, total, hayBusqueda)`: "2 de 12 productos" solo si hay búsqueda y `visibles < total`; en cualquier otro caso (sin búsqueda, o búsqueda que deja todos visibles) "12 productos" / "1 producto" (singular como hoy). Cambio pedido por el usuario (2026-11-24): V == T no dice "12 de 12".

`inventario.js`: `pintarTabla()` pinta `Busqueda.filtrar(productos, campo.value)`; el evento `input` del campo repinta (sin debounce: listas de cientos de filas). Escape dentro del campo y "Limpiar búsqueda" vacían y repintan con foco en el campo. La recarga tras ingreso/modificación/orden/baja reutiliza el valor del campo (no se resetea); al abrir la página el campo arranca vacío (sin `localStorage`, decisión 9).

**Alternativa descartada**: `GET /api/inventario?q=` con `LIKE` en SQLite e `ilike` en Supabase. Requiere service + repositorio + test de ambos backends (más trabajo en C-07), un request por tecla (o debounce) y, en SQLite, `LIKE`/`lower()` solo pliega ASCII (no `Á`/`Ñ`), así que la búsqueda sin tildes exigiría una columna normalizada o una función registrada. El dataset de un taller chico (decenas a pocos miles de productos) ya viaja completo en `GET /api/inventario`. Si algún día el inventario se pagina, la búsqueda pasa al servidor en ese change.

### D2 — PDF por impresión del navegador (decisión 2)

`static/js/exportar.js` (nuevo, expone `window.Exportar`), reutilizable por cualquier página (C-06d incluido):
- Funciones **puras** (testeables con Node): `fecha(date)` → `"AAAA-MM-DD"`; `nombreArchivo(base, date)` → `base + "-" + fecha` con todo carácter fuera de `[A-Za-z0-9-]` reemplazado por `-` (colapsando repetidos y sin `-` final; `orden-OT/2026#1` → `orden-OT-2026-1-2026-11-24`).
- `imprimir({ titulo, linea, base, modo })`: llena el encabezado de impresión `#print-head` (con `textContent`: título y una sola línea `linea`; revisión pedida por el usuario, 2026-11-24: sin criterio de búsqueda, sin usuario, sin hora; inventario: "N productos · AAAA-MM-DD"; orden: "Fecha: AAAA-MM-DD · N componentes"), pone `document.body.dataset.exportando = modo` (p. ej. `"inventario"`, `"orden"`), cambia `document.title` a `nombreArchivo(base, new Date())`, registra **una vez** la restauración (título original, borrar `data-exportando` y la marca de la orden) en `afterprint`, y llama a `window.print()`.
- Cada página exportable tiene un `<header id="print-head" class="print-only" aria-hidden="true">` vacío en el HTML.

`static/css/app.css` — bloque `@media print` (y `.print-only { display:none }` en pantalla):
- Variables de color redefinidas para papel dentro de `@media print { :root { … } }` (fondo blanco, texto `#111`, bordes grises), `color-scheme: light`, `-webkit-print-color-adjust: exact` solo donde haga falta.
- Oculta: cabecera de la app, `nav`, `.btn`, campos de búsqueda/filtros, alertas (`#aviso-exito`), `.overlay`, la columna de acciones (`.tbl-inv td:last-child, th:last-child`), conteos de pantalla y el cartel de "Ningún producto coincide".
- Tablas: `overflow: visible` en las regiones con scroll, `thead { display: table-header-group }`, `tr { break-inside: avoid }`, `#print-head { break-after: avoid }`; `@page { margin: 15mm }` sin forzar tamaño (respeta A4/Carta del usuario, decisión 12).
- Stock 0: el `<span class="sr-only">, sin stock</span>` existente se acompaña de un `<span class="print-only"> (sin stock)</span>` con `aria-hidden` para que el papel lo diga en texto.
- `body[data-exportando="orden"] .ord:not([data-exportar])` y el resto del `main` ajeno a la orden → `display:none`.

**Alternativa descartada**: PDF en el servidor (`reportlab`/`fpdf2` puros, o WeasyPrint con dependencias nativas GTK/Pango, inviable en Windows y en Vercel). Exigiría dependencias nuevas en `requirements.txt`, endpoints nuevos (`GET /api/inventario.pdf?q=`, `GET /api/ordenes/{numero}.pdf`) con búsqueda en el servidor, maquetado duplicado en Python, peso extra en la función serverless de C-08 y tests de contenido PDF. A favor tendría un archivo idéntico en cualquier navegador y la descarga en un clic; en contra pesa todo lo anterior para una app de un usuario. La impresión del navegador produce PDF con texto seleccionable en Chrome/Edge/Firefox/Safari y en móvil (Compartir → Imprimir → PDF).

### D3 — Exportación por orden (decisión del usuario, 2026-11-24)

`ordenes.js`: `articulo(o)` agrega en `.ord-head`, antes de "Eliminar", un botón `btn btn-secondary btn-sm` "Exportar PDF" con `data-exportar-orden="<numero>"` y `aria-label="Exportar PDF de la orden <numero>"` (el `ml-auto` pasa al primero de los dos botones). Al pulsarlo: marca el `<article>` con `data-exportar`, y llama a `Exportar.imprimir({ titulo: "Orden " + numero, linea: "Fecha: " + fecha + " · N componentes", base: "orden-" + numero, modo: "orden" })`; la restauración quita la marca. Sin pedidos a la API (los datos ya están en la lista). Sin órdenes no hay botones (el cartel vacío no tiene acciones). La lista, filtros y alertas no cambian en pantalla.

### D4 — Interfaz del inventario

`index.html`, cabecera del panel `#inv-panel`: título + conteo a la izquierda; a la derecha (en móvil, debajo, ancho completo) el campo `<input type="search" id="inv-buscar">` con `<label class="sr-only">Buscar por código o nombre</label>` y placeholder "Buscar por código o nombre", y el botón secundario "Exportar PDF" (`#btn-exportar-inv`). Nuevo bloque `#inv-sin-coincidencias` (`role="status"`) dentro del panel con el texto "Ningún producto coincide con «…»" (texto por `textContent`) y el botón "Limpiar búsqueda". "Exportar PDF" queda `disabled` en `cargando`, `error` y con 0 filas visibles. La exportación llama a `Exportar.imprimir({ titulo: "Inventario", linea: N + " productos · " + Exportar.fecha(new Date()), ... })` con el número de filas visibles (sin "N de M": la búsqueda no se imprime).

### D5 — Lo que no cambia (decisión 4)

Los `<select>` de "Modificar stock" y "Nueva orden" quedan como están (el `<select>` nativo ya permite saltar tecleando el inicio de la opción "CÓDIGO · Nombre"). Agregar un combobox con búsqueda es un cambio de accesibilidad y de mockups aparte; se puede pedir en otro change.

### D6 — Tests (Strict TDD, `unittest`)

- `tests/test_busqueda_js.py` (Node, se omite sin Node, patrón de `test_validacion_js.py`): `normalizar` (mayúsculas, tildes, espacios, `None`), `filtrar` (código parcial, nombre parcial, coincidencia en ambos sin duplicar, orden conservado, vacío y solo espacios → todos, sin coincidencias → `[]`, texto con `<b>`), `conteo` (singular/plural, con y sin búsqueda, "0 de 12 productos").
- `tests/test_exportar_js.py` (Node): `fecha`, `fechaHora` (relleno con ceros), `nombreArchivo` (inventario, `OT/2026#1`, guiones repetidos), (sin `criterio` ni `fechaHora`: revisión del 2026-11-24).
- `tests/test_frontend_estatico.py` (guardas, siempre corren): `busqueda.js` y `exportar.js` sin `fetch`/`XMLHttpRequest`; `busqueda.js` sin `document`; `exportar.js` usa `window.print`, `afterprint` y restaura `document.title`; `index.html` y `ordenes.html` cargan ambos scripts (los que usan) y tienen `#print-head` con `print-only`; `index.html` tiene `#inv-buscar` etiquetado, `#btn-exportar-inv`, `#inv-sin-coincidencias` oculto y "Limpiar búsqueda"; `ordenes.js` crea el botón con `aria-label` "Exportar PDF de la orden" y `data-exportar-orden`; `ordenes.html` no tiene un "Exportar PDF" global; `app.css` contiene `@media print`, `.print-only`, `table-header-group` y `break-inside: avoid`; `inventario.js` no agrega `q=` a `/api/inventario`; los mensajes "Ningún producto coincide con" y "de … productos" presentes. Las guardas existentes (sin `innerHTML`, campos etiquetados, CSS idéntico al design system) siguen verdes.
- Backend: sin tests nuevos; la suite completa debe seguir verde sin cambiar aserciones (prueba de "sin cambios de API").
- Comportamiento real (filtrado al teclear, diálogo de impresión, hoja de impresión, restauración del título): verify con Playwright (`browser_emulate_media` `print`, `page.pdf` para un A4 de muestra, `page.evaluate` para stubear `window.print` y comprobar título/`data-exportando` antes y después de `afterprint`).

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-24)
- Mockups: openspec/changes/paso-5c-buscador-pdf/mockups/ (a crear: `inventario.html`, `ordenes.html`, `README.md`)
- Approval: approved (2026-11-24, by user)
- Revisión pedida por el usuario (2026-11-24): encabezado del PDF del inventario = título + cantidad + fecha (`AAAA-MM-DD`); de una orden = título + "Fecha: AAAA-MM-DD · N componentes". Sin criterio, usuario, hora ni "Creada por". Mockups P1-P3 y specs actualizados.
- Preview: rendered (2026-11-24, Playwright: 390x844 y 1440x900 en `mockups/previews/`; P1-P3 con `print` emulado y PDF A4 de muestra; sin scroll horizontal a 390 px)
- Visual verify: passed (2026-11-24, Playwright 390x844 y 1440x900 contra uvicorn + base temporal de 45 productos; capturas en `mockups/verify/`; impresión: PDF A4 con `print` emulado, `window.print` stubeado)

Base: mockups aprobados de C-06b (`openspec/changes/archive/2026-11-23-paso-5b-fixes-menores/mockups/inventario.html`) y de C-06 para órdenes, mismos tokens (`design-system/tokens.css`, `ui.css`), cabecera de texto "Inventario", tema oscuro único. Estados previstos:

| ID | Pantalla | Estado |
|----|----------|--------|
| I1 | Inventario | Buscador vacío + "Exportar PDF" habilitado, "12 productos" |
| B1 | Inventario | Búsqueda `tor` → 2 filas, "2 de 12 productos" |
| B2 | Inventario | Sin coincidencias `xyz`: cartel + "Limpiar búsqueda", "0 de 12 productos", "Exportar PDF" deshabilitado |
| B3 | Inventario | Cargando: buscador visible, "Exportar PDF" deshabilitado |
| O1 | Órdenes | Lista con "Exportar PDF" + "Eliminar" por orden (prestar atención al encabezado de la orden a 390 px) |
| P1 | Impresión | Inventario con búsqueda `tor` (hoja clara, encabezado, sin controles ni columna "Eliminar") |
| P2 | Impresión | Inventario completo con un stock 0 → "0 (sin stock)", varias páginas con encabezado de tabla repetido |
| P3 | Impresión | Una orden (`OT-0042`) sola, con "Fecha: … · N componentes" (sin "Creada por") |

Los estados de pantalla se renderizan a 390x844 y 1440x900; los de impresión (P1-P3) con `print` emulado a esos dos anchos y, además, como PDF A4 de muestra en `mockups/previews/`. Estos mockups son criterio de aceptación de los grupos 5-7 de `tasks.md` y del verify.

## Risks / Trade-offs

- [El usuario espera un botón que descargue el PDF directo y en su lugar ve el diálogo de impresión] → etiqueta "Exportar PDF" y, en el diálogo, "Guardar como PDF" es el destino por defecto en Chrome/Edge si ya se usó; se documenta en el README y en KB 07. Si molesta, la decisión 2 puede revisarse en otro change (PDF en el servidor).
- [El resultado varía levemente por navegador (márgenes, encabezados/pies del navegador con URL y fecha)] → `@page` con margen propio; el usuario puede desactivar "Encabezados y pies de página" en el diálogo. Aceptado.
- [`afterprint` poco fiable en algunos navegadores móviles] → además de `afterprint`, la restauración se dispara con `matchMedia("print")` al volver a `false`; si ninguna llega, el título queda con el nombre del archivo hasta la siguiente acción (inocuo) y la marca `data-exportando` solo afecta a la impresión.
- [`normalize("NFD")` pliega `ñ` a `n`: buscar `pina` encuentra "piña"] → aceptado (favorece encontrar).
- [Búsqueda en el navegador no escala a decenas de miles de productos] → fuera del perfil de un taller chico; si se pagina el inventario, pasa al servidor.
- [Un producto recién creado que no coincide con la búsqueda "desaparece"] → la alerta de éxito persistente lo nombra; escenario explícito en la spec.

## Migration Plan

Solo archivos estáticos: desplegar = reiniciar uvicorn (o recargar con `Ctrl+F5`, las páginas van con `Cache-Control: no-store` pero los `.js`/`.css` pueden quedar en caché). Rollback: revertir los archivos de `static/` y los tests nuevos. Sin datos ni esquema afectados.

## Open Questions

- Al archivar, actualizar la KB: 06 (US-003: buscador por código/nombre parcial sin mayúsculas ni tildes y exportación a PDF del resultado; US-007: exportación a PDF de una orden individual) y 07 (flujo "Buscar en el inventario" y flujo "Exportar a PDF" con el diálogo de impresión).

## Decisiones a confirmar por el usuario

> Governance BAJO/MEDIO: decisiones aprobadas el 2026-11-24; el apply no empieza hasta que el usuario apruebe los mockups. ★ = recomendada.

**Ya decidido por el usuario (2026-11-24):**
- **PDF de órdenes = por orden individual**: cada orden tiene su propio botón "Exportar PDF" que exporta solo esa orden. No hay PDF de la lista completa ni de la vista filtrada.

**Aprobadas por el usuario (2026-11-24): las 12 decisiones, como recomendadas (★).** La decisión 3 queda confirmada: "importar como PDF" = exportar/descargar a PDF.
1. **Dónde se filtra la búsqueda.** A ★ En el navegador sobre `GET /api/inventario` (instantáneo, sin cambios de API ni de C-07). B Parámetro `q` en `GET /api/inventario` (servidor; más trabajo en SQLite y Supabase).
2. **Mecanismo de PDF.** A ★ Impresión del navegador con hoja `@media print` + `exportar.js` reutilizable (sin dependencias). B Librería en el servidor (`reportlab`/`fpdf2` en `requirements.txt`) con endpoints `.pdf`.
3. **"Importar como PDF".** A ★ Se interpreta como **exportar/descargar** a PDF. B Otra cosa (p. ej. cargar datos desde un PDF): fuera de este change.
4. **Buscador en los selectores de "Modificar stock" / "Nueva orden".** A ★ No (siguen como `<select>` nativo). B Sí, combobox con búsqueda (más alcance y mockups).
5. **Sin tildes además de sin mayúsculas.** A ★ Sí (`TORICA` encuentra "tórica"; `ñ` ≈ `n`). B Solo sin mayúsculas.
6. **Varias palabras.** A ★ El texto completo es una sola subcadena (`tornillo m8`). B Cada palabra debe aparecer, en cualquier orden.
7. **Qué exporta el inventario.** A ★ Las filas visibles (todo si no hay búsqueda). B Siempre todo el inventario.
8. **Etiqueta del botón.** A ★ "Exportar PDF". B "Imprimir / PDF".
9. **Búsqueda al volver a la página.** A ★ Se conserva al recargar el inventario tras una acción, pero no al reabrir la página. B Recordarla en `sessionStorage`.
10. **Exportar sin filas.** A ★ Botón deshabilitado (cargando, error o 0 coincidencias). B Habilitado, exporta "0 productos".
11. **CSS de impresión.** A ★ En `static/css/app.css` (design system Revision 2 intacto). B Subir el design system a Revision 3 con tokens de impresión.
12. **Tamaño de página.** A ★ Margen 15 mm sin forzar tamaño (A4 o Carta según el navegador). B Forzar A4 vertical.
