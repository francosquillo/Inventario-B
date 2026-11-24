# Tasks

> **GATE: el apply NO empieza hasta que `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`** y el usuario haya revisado las "Decisiones a confirmar por el usuario" (la exportación por orden ya está decidida por el usuario, 2026-11-24). Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). Las funciones puras de JS se prueban con Node desde `unittest` (patrón de `tests/test_validacion_js.py`, se omiten sin Node); el resto del frontend tiene guardas estáticas; el comportamiento en el navegador se verifica en el grupo 8 contra los escenarios de `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base (regla dura 4).
> - Sin dependencias nuevas; `requirements.txt` y `requirements-dev.txt` intactos (regla dura 1).
> - Sin cambios de API, esquema, services ni repositorios: la suite backend no cambia aserciones.
> - `tokens.css` y `ui.css` intactos (copias del design system); CSS nuevo solo en `static/css/app.css`.
> - En JS: datos solo con `textContent`/`createElement`; nada de `innerHTML`.
> - Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups en `openspec/changes/paso-5c-buscador-pdf/mockups/` (`inventario.html` y `ordenes.html` que importan `design-system/tokens.css` y `ui.css`, cabecera de texto "Inventario", tema oscuro único, README con estados y `Approval: pending`) cubriendo I1, B1, B2, B3, O1, P1, P2 y P3 (design § UI Mockups)
- [x] 0.2 Renderizar los estados de pantalla a 390x844 y 1440x900 y los de impresión (P1-P3) con `print` emulado a esos anchos y como PDF A4 de muestra, con Playwright; guardar en `mockups/previews/`, inspeccionar y corregir defectos; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita (y la revisión de las decisiones 1-12); registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar que `node` está disponible (si no, los tests de JS puro se omiten: avisarlo y cubrir esos casos en el verify con `browser_evaluate`)

## 2. Búsqueda pura — spec `interfaz-web` (Buscador, Conteo) (design D1)

- [x] 2.1 RED (`tests/test_busqueda_js.py`, nuevo): `Busqueda.filtrar` con `A-01` "Tornillo M8", `B-10` "Tuerca M8", `C-03` "Arandela" y `tor` → solo `A-01`; verificar rojo (no existe `static/js/busqueda.js`)
- [x] 2.2 GREEN: `static/js/busqueda.js` puro (`window.Busqueda`, sin DOM ni `fetch`) con `normalizar` y `filtrar`. Verificar verde
- [x] 2.3 TRIANGULATE: `a-0` → `A-01`, `A-02` en orden; `m8` coincide en código y en nombre sin duplicar y conserva el orden; `TORICA` → "Junta tórica"; `""`, `"   "` y `null` → lista completa; `xyz` → `[]`; `<b>x</b>` no rompe
- [x] 2.4 RED→GREEN→TRIANGULATE: `Busqueda.conteo` → "12 productos", "1 producto", "2 de 12 productos", "0 de 12 productos"
- [x] 2.5 REFACTOR; suite verde

## 3. Exportación pura — spec `exportacion-pdf` (Encabezado, Nombre de archivo) (design D2)

- [x] 3.1 RED (`tests/test_exportar_js.py`, nuevo): `Exportar.nombreArchivo("inventario", new Date(2026, 10, 24))` → `inventario-2026-11-24`; verificar rojo
- [x] 3.2 GREEN: `static/js/exportar.js` con las funciones puras (`fecha`, `nombreArchivo`) sin tocar el DOM al cargarse. Verificar verde
- [x] 3.3 TRIANGULATE: `orden-OT/2026#1` → `orden-OT-2026-1-2026-11-24`; guiones repetidos colapsados; `fecha` con relleno de ceros (`2026-01-05`)
- [x] 3.4 RED (guardas en `tests/test_frontend_estatico.py`): `exportar.js` usa `window.print`, escucha `afterprint`, restaura `document.title` y no usa `fetch`/`XMLHttpRequest`; verificar rojo
- [x] 3.5 GREEN: `Exportar.imprimir({titulo, linea, base, modo})` que llena `#print-head` con `textContent` (solo título y una línea; sin usuario ni criterio), marca `body[data-exportando]`, cambia y restaura el título (`afterprint` + `matchMedia("print")`, una sola vez) y llama a `window.print()`. Verificar verde
- [x] 3.6 REFACTOR; suite verde

## 4. Hoja de impresión — spec `exportacion-pdf` (Hoja clara, Saltos de página) (design D2)

- [x] 4.1 RED (guardas): `app.css` contiene `@media print`, `.print-only`, `table-header-group`, `break-inside: avoid` y `@page`; `index.html` y `ordenes.html` tienen `<header id="print-head" class="print-only" aria-hidden="true">` y cargan `exportar.js`; `tokens.css`/`ui.css` siguen idénticos al design system. Verificar rojo
- [x] 4.2 GREEN: bloque `@media print` en `static/css/app.css` (colores de papel, ocultar cabecera/nav/botones/campos/alertas/modales/columna de acciones, tablas sin scroll, encabezado de tabla repetido, filas sin partir, `@page { margin: 15mm }`, modo `data-exportando="orden"`) y `#print-head` en ambas páginas. Verificar verde

## 5. Inventario: buscador y exportación — spec `interfaz-web` (mockups I1, B1-B3, P1, P2) (design D4)

- [x] 5.1 RED (guardas): `index.html` carga `busqueda.js` y `exportar.js`; tiene `#inv-buscar` (`type="search"`, etiqueta asociada), `#btn-exportar-inv` "Exportar PDF", `#inv-sin-coincidencias` oculto con "Limpiar búsqueda"; `inventario.js` contiene "Ningún producto coincide con", usa `Busqueda.filtrar` y `Exportar.imprimir` y no agrega `q=` a `/api/inventario`. Verificar rojo
- [x] 5.2 GREEN: HTML de la cabecera del panel según I1 (responsive como el mockup) y JS: `pintarTabla` filtra con el valor del campo, `input` repinta, conteo con `Busqueda.conteo`, cartel sin coincidencias con `textContent`, Escape y "Limpiar búsqueda" vacían y devuelven el foco, búsqueda conservada en `cargar(false)`, "Exportar PDF" deshabilitado en cargando/error/0 filas
- [x] 5.3 GREEN: stock 0 con `<span class="print-only" aria-hidden="true"> (sin stock)</span>`; "Exportar PDF" llama a `Exportar.imprimir({titulo: "Inventario", linea: N + " productos · " + Exportar.fecha(new Date()), base: "inventario", modo: "inventario"})`
- [x] 5.4 REFACTOR; suite completa verde (guardas existentes de inventario intactas: campos etiquetados, sin `innerHTML`, endpoints)

## 6. Órdenes: exportación por orden — spec `interfaz-web` (Exportar una orden) (mockups O1, P3) (design D3)

- [x] 6.1 RED (guardas): `ordenes.html` carga `exportar.js` y no tiene un botón "Exportar PDF" global; `ordenes.js` crea por orden un botón con `data-exportar-orden` y `aria-label` "Exportar PDF de la orden …" y llama a `Exportar.imprimir`. Verificar rojo
- [x] 6.2 GREEN: botón en `.ord-head` antes de "Eliminar" (`ml-auto` en el primero), delegación de clic, marca `data-exportar` en el `<article>`, `Exportar.imprimir({titulo: "Orden " + numero, linea: "Fecha: … · N componentes", base: "orden-" + numero, modo: "orden"})`, restauración de la marca. Verificar verde
- [x] 6.3 REFACTOR; suite completa verde (guardas de borrado y filtros intactas)

## 7. Documentación local

- [x] 7.1 `README.md`: cómo buscar y cómo exportar a PDF ("Exportar PDF" → "Guardar como PDF" en el diálogo; desactivar encabezados y pies del navegador si se quiere)

## 8. Verify

- [x] 8.1 Suite completa verde, mismas aserciones backend que el baseline; `openspec validate paso-5c-buscador-pdf --strict`
- [x] 8.2 Playwright contra la app real (uvicorn + base temporal con ~15 productos, uno con stock 0 y uno con tilde, y 2-3 órdenes, una con componente dado de baja) a 390x844 y 1440x900, comparando con los mockups aprobados (I1, B1-B3, O1): capturas en `mockups/verify/`, consola sin errores, red sin pedidos al teclear en "Buscar"
- [x] 8.3 Impresión: con `window.print` stubeado vía `page.evaluate`, comprobar título `inventario-<hoy>` / `orden-<número>-<hoy>`, `data-exportando` y restauración tras `afterprint`; con `print` emulado y `page.pdf` (A4) comparar con P1-P3 (hoja clara, sin controles ni columna "Eliminar", "0 (sin stock)", encabezado de tabla repetido, solo la orden elegida)
- [x] 8.4 Registrar `Visual verify:` en `design.md`

## 9. Cierre (archive)

- [x] 9.1 Actualizar la KB: 06 (US-003 buscador + exportación; US-007 exportación por orden) y 07 (flujos de búsqueda y de exportación a PDF) según `design.md` § Open Questions
- [x] 9.2 Marcar `[x]` C-06c en `CHANGES.md` (y anotar en C-06d que reutiliza `exportar.js` + `@media print`) y esperar "Continuar" del usuario antes de C-06d
