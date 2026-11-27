# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario revise las decisiones D1–D8 de `design.md` (en especial D1, ubicación y etiquetas del filtro) y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)` para S1, S2 y S3. Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). JS puro con Node desde `unittest` (patrón de `tests/test_busqueda_js.py`, se omite sin Node); el resto del frontend con guardas estáticas (patrón de `tests/test_frontend_categorias.py`); el comportamiento en el navegador se verifica en el grupo 6 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest; sin dependencias nuevas (reglas duras 1 y 4).
> - Solo `static/` y `tests/`: sin cambios en `domain/`, `services/`, `repositories/`, `api/` ni en el esquema. El cuerpo de `POST /api/stock/modificaciones` no cambia.
> - `design-system/tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css` con tokens existentes. En JS: solo `textContent`/`createElement`, sin `innerHTML`.
> - Nunca leer ni escribir `.env`; el verify usa una **copia** de `dev-local.db`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear solo los mockups necesarios en `openspec/changes/paso-5h2-filtro-categoria-stock/mockups/` (`modificar-stock.html` S1, S2, S3; `README.md` con estados, omisiones justificadas y `Approval: pending`) y verificar que abren localmente
- [x] 0.2 Renderizar a 390x844 y 1440x900 en `mockups/previews/`; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir la lógica pura en el verify con `browser_evaluate`) y que `tests.test_busqueda_js`, `tests.test_frontend_categorias` y `tests.test_frontend_estatico` están verdes

## 2. Reutilización de `Busqueda` con dados de baja — spec `interfaz-web` (Filtro por categoría en la modificación de stock) (design D3, D8)

- [x] 2.1 TRIANGULATE (red de seguridad de la reutilización, `tests/test_busqueda_js.py`): `porCategoria` sobre una lista de dados de baja (`C-99` `motor`, `D-05` sin categoría) con `"motor"` → `["C-99"]`, con `SIN_CATEGORIA` → `["D-05"]`, con `"helices"` → `[]`; `productoSigueVisible("C-99", activos + inactivos, "motor")` → true y con `"aceite"` → false; `productoSigueVisible("", …)` → false. Se espera verde sin código nuevo (comportamiento existente): anotarlo; si alguno falla, es RED real y se corrige `busqueda.js` sin cambiar la API pública
- [x] 2.2 Verificar que `busqueda.js` no cambió (o, si cambió en 2.1, que `tests.test_busqueda_js` completo sigue verde)

## 3. Plantilla y estilos de la línea — spec `interfaz-web` (Filtro por categoría…, Filtro separado de la categoría del producto) (mockups S1–S3 = criterio de aceptación) (design D1, D6)

- [x] 3.1 RED (`tests/test_frontend_filtro_modificar.py`, nuevo): la plantilla `tpl-mline` tiene `<select … data-filtro>` **antes** de `select[data-producto]` dentro de `.mline-head`; etiquetas visibles `data-filtro-etiqueta` "Filtrar por categoría" y `data-producto-etiqueta` "Producto"; el selector `data-categoria` con su etiqueta "Categoría" sigue en `.mline-two`; `app.css` define la grilla de `.mline-head` con la columna del filtro (≥ 640 px una fila con el filtro en 12rem; < 640 px producto en su propia fila); el modal `#modal-modificar` mide 44rem. Verificar rojo
- [x] 3.2 GREEN: plantilla y ancho del modal en `static/index.html` y CSS en `static/css/app.css` (tokens existentes, `align-items:start` con número y "Quitar" bajados 1.25rem como en el mockup, sin scroll horizontal a 390 px). Verificar verde
- [x] 3.3 TRIANGULATE: la guarda de C-06e `ModificarCategoriaTest.test_plantilla_con_selector_etiquetado` y `tests.test_frontend_estatico` siguen verdes; sin `innerHTML` en la plantilla
- [x] 3.4 REFACTOR; suite verde

## 4. Lógica del filtro en `inventario.js` — spec `interfaz-web` (Filtro por categoría…, Selector de productos de la modificación) (design D2, D3, D4, D5)

- [x] 4.1 RED (guardas en `tests/test_frontend_filtro_modificar.py`): `llenarSelectMod` recibe la categoría y usa `Busqueda.porCategoria(productos, …)` y `Busqueda.porCategoria(inactivos, …)` y `Busqueda.productoSigueVisible(` con `productos.concat(inactivos)`; `nuevaLineaMod` llena el filtro con `llenarSelectCategoria(…, "Todas las categorías", true)`; `llenarSelectoresCategoria` incluye `#mod-lineas select[data-filtro]`; `alCambiarLineaMod` tiene la rama `select[data-filtro]`; el texto "No hay productos en esta categoría." sale de una constante compartida con "Nueva orden"; no hay una segunda implementación del filtrado (ningún `.filter(` sobre `categoria` en `inventario.js`). Verificar rojo
- [x] 4.2 GREEN: implementar D2–D5 (filtro de ambos grupos, grupo vacío oculto, conservar si pertenece / resetear si no, reseteo antes de `refrescarSelectsMod`, "(ya no existe)" intacto con `conservar`, ayuda `mod-<k>-vacio` con `aria-describedby`). Verificar verde
- [x] 4.3 TRIANGULATE (guardas): la ayuda se quita cuando el filtro vuelve a tener productos o es "Todas las categorías" (la función elimina el `<p>` previo y el `aria-describedby` antes de decidir); el reseteo deja el valor vacío y la Categoría en "Sin categoría" por el mismo camino que elegir "Elegí un producto…" (una sola función, no código duplicado); guardas de C-06e de "Nueva orden" (`NuevaOrdenCategoriaTest`) verdes
- [x] 4.4 REFACTOR; suite verde

## 5. Accesibilidad y cuerpo de la petición — spec `interfaz-web` (Filtro separado de la categoría del producto) (design D6, D7)

- [x] 5.1 RED (guardas): `renumerarMod` pone `id` `mod-<k>-fil`/`mod-<k>-prod`, el `for` de ambas etiquetas y `aria-label` `"Filtrar por categoría, línea " + n` (y conserva `"Producto de la línea "` y `"Categoría de la línea "`); `leerLineasMod` no lee `data-filtro`. Verificar rojo
- [x] 5.2 GREEN: `renumerarMod`. Verificar verde
- [x] 5.3 TRIANGULATE: `leerLineasMod` sigue con exactamente `codigo`, `modo`, `valor`, `nombre`, `categoria`; `tests.test_api_modificaciones` verde (la API no cambió)
- [x] 5.4 REFACTOR; suite completa verde (baseline + nuevos, cero fallas) y `openspec validate paso-5h2-filtro-categoria-stock --strict` sin errores

## 6. Verify en el navegador

- [x] 6.1 Playwright contra la app real (uvicorn sobre una **copia** de `dev-local.db` con al menos una categoría sin productos y un dado de baja con categoría) a 1440x900 y 390x844, comparando con S1–S3: filtro "Todas las categorías" por defecto; filtrar una línea no afecta la otra; "Motor" muestra el dado de baja en su grupo; "Sin categoría"; cambio de filtro que conserva y que resetea (valor vacío, Categoría "Sin categoría"); producto de otra línea deshabilitado dentro del filtro; ayuda de lista vacía que aparece y desaparece; filtro sin cambiar la "Categoría"; guardar envía el cuerpo de siempre (inspeccionar el request) y el resumen sale igual; línea nueva y reapertura en "Todas las categorías"; teclado (orden de tabulación y foco visible); sin scroll horizontal a 390 px. Capturas en `mockups/verify/`, consola sin errores y red sin pedidos fallidos inesperados. Detener el servidor iniciado (solo su PID)
- [x] 6.2 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar KB 06 (US-005, filtro por categoría por línea) y 07 (flujo de modificar stock), y `CHANGES.md` (C-06h2 `[x]` con fecha).
- Esperar "Continuar" del usuario antes de proponer C-06i (`paso-5i-modificar-ordenes-checkeo`).
