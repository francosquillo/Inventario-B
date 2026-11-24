# Proposal — paso-5c-buscador-pdf (C-06c)

## Why

Con el inventario creciendo, el usuario necesita encontrar rápido un producto sin recorrer toda la tabla, y llevarse en papel o en un archivo lo que ve: el resultado de una búsqueda del inventario y el listado de órdenes (pedido del 2026-11-24: "buscador por código o nombre" e "importar como PDF", interpretado como **exportar/descargar**; a confirmar). Se hace ahora, antes de C-06d (que reutiliza el mismo mecanismo de PDF para su reporte) y antes de migrar a Supabase (C-07), porque no toca esquema ni API.

Governance **BAJO/MEDIO**: solo lectura y presentación, sin cambios de datos ni de endpoints, con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

- **Buscador del inventario** en `/inventario`: un campo "Buscar" sobre la tabla filtra, mientras se escribe, los productos activos cuyo **código o nombre contiene** el texto, sin distinguir mayúsculas ni tildes. El conteo pasa a "N de M productos" mientras la búsqueda deja menos productos que el total (si los deja todos, sigue "M productos"; cambio pedido por el usuario, 2026-11-24); sin coincidencias se ve un cartel con "Limpiar búsqueda". El filtrado se hace en el navegador sobre la lista que ya devuelve `GET /api/inventario` (recomendado; decisión 1). La búsqueda se conserva tras crear, modificar o dar de baja productos.
- **Exportar PDF del inventario**: botón "Exportar PDF" que genera un documento imprimible con las filas visibles (todas, o solo el resultado de la búsqueda), con encabezado mínimo (título, cantidad y fecha de exportación; sin búsqueda ni usuario, revisión del usuario 2026-11-24) y columnas Código, Nombre y Stock; el stock 0 se marca con texto "sin stock".
- **Exportar PDF de una orden** (decidido por el usuario, 2026-11-24): cada orden de `/ordenes` tiene su propio botón "Exportar PDF", junto a "Eliminar", que exporta **solo esa orden** (título "Orden <número>", fecha, cantidad de componentes y sus componentes; sin usuario). No hay exportación de la lista completa de órdenes.
- **Mecanismo de PDF reutilizable** (recomendado; decisión 2): impresión del navegador (`window.print()`, "Guardar como PDF") con una hoja `@media print` clara (fondo blanco, texto negro, sin cabecera, botones, filtros ni modales) y un módulo JS `static/js/exportar.js` que arma el encabezado del documento y el nombre de archivo sugerido (`inventario-AAAA-MM-DD`, `orden-<número>-AAAA-MM-DD`). Sin dependencias nuevas. C-06d lo reutiliza para su reporte.
- Sin cambios en la API, el esquema, los services ni los repositorios. Los selectores de producto de "Modificar stock" y "Nueva orden" **no** cambian (decisión 4).

## Capabilities

### New Capabilities
- `exportacion-pdf`: cómo la web exporta una vista a PDF (impresión del navegador, hoja de impresión clara, encabezado con metadatos, nombre de archivo sugerido, qué se oculta, saltos de página). Capacidad propia para que C-06d la reutilice sin duplicar requisitos.

### Modified Capabilities
- `interfaz-web`: la tabla de inventario incorpora el buscador y el botón "Exportar PDF"; cada orden de la pantalla de órdenes incorpora su botón "Exportar PDF"; nuevos requisitos de búsqueda sin resultados.

## Impact

- **Frontend**: `static/index.html`, `static/ordenes.html`, `static/js/inventario.js`, `static/js/ordenes.js`, nuevos `static/js/busqueda.js` (puro) y `static/js/exportar.js`, `static/css/app.css` (reglas `@media print` y piezas nuevas; `tokens.css`/`ui.css` del design system intactos).
- **Tests**: `tests/test_frontend_estatico.py` (guardas nuevas), nuevos `tests/test_busqueda_js.py` y `tests/test_exportar_js.py` (funciones puras con Node, mismo patrón que `tests/test_validacion_js.py`). La suite backend no cambia aserciones.
- **API / datos**: ninguno. OpenAPI sigue con las mismas rutas. Paridad C-07 sin trabajo extra (no hay consulta nueva).
- **Dependencias**: ninguna nueva (`requirements.txt` intacto).
- **KB al archivar**: 06 (US-003 con búsqueda y exportación, US-007 con exportación de una orden) y 07 (flujos de búsqueda y de exportación a PDF).
