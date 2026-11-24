# Mockups — paso-5e-categorias-productos (C-06e)

- Design system revision: 2 (`design-system/tokens.css` y `ui.css`, tema oscuro único; cabecera de texto "Inventario", sin logo)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24)

Base visual: mockups aprobados de C-06c (inventario, buscador, hoja de impresión), C-06b (modales de ingreso y modificación) y C-06d (`/reportes`). `assets/mockup.css`, `assets/mockup-5c.css` y `assets/tailwind-config.js` son copias de C-06d; `assets/mockup-5e.css` tiene lo propio de este change (candidato a `static/css/app.css`); `assets/mockup.js` y `assets/mockup-rep.js` son solo de la maqueta (selector de estados y datos de muestra, sin `innerHTML`).

## Cómo verlos

Abrir `inventario.html` o `reportes.html` en el navegador (o servir la raíz del repo con `python -m http.server 8765`). El selector de la barra superior cambia de estado (`#I1`, `#M1`...); `?captura` oculta la barra. Requiere red para el CDN de Tailwind. El buscador y el filtro de categoría de `inventario.html` filtran de verdad sobre los datos de muestra. Para ver la impresión: elegir P1 / P2 y Ctrl+P (en la app real es el `@media print` de `static/css/app.css` sobre la propia página).

## Estados

| ID | Archivo | Qué muestra | Capturas (`previews/`) |
|----|---------|-------------|------------------------|
| I1 | inventario | Columna "Categoría" (Aceite / Filtro / Motor; "Sin categoría" atenuado), filtro en "Todas las categorías", "12 productos" | `inventario-I1-{mobile,desktop}.png` |
| I2 | inventario | Filtro "Aceite": 3 filas, "3 de 12 productos" | `inventario-I2-*` |
| I3 | inventario | Búsqueda `aceite` + filtro "Filtro": 1 fila, "1 de 12 productos" | `inventario-I3-*` |
| I4 | inventario | Categoría sin productos: "Ningún producto en la categoría «Motor»" + "Limpiar filtros" (muestra con los de Motor dados de baja: "0 de 10 productos") | `inventario-I4-*` |
| I4b | inventario | Combinada: "Ningún producto coincide con «tor» en la categoría «Aceite»" + "Limpiar filtros" | `inventario-I4b-*` |
| I5 | inventario | Filtro desplegado (ilustración con `size`): Todas las categorías / Aceite / Filtro / Motor / Sin categoría | `inventario-I5-*` |
| I6 | inventario | Barra con valores (`10w` + "Aceite"): buscador + filtro + "Exportar PDF", sin scroll horizontal a 390 px | `inventario-I6-*` |
| A1 | inventario (modal) | Nuevo ingreso con "Categoría (opcional)" en "Sin categoría" | `inventario-A1-*` |
| A1b | inventario (modal) | Variante con "Aceite" elegido | `inventario-A1b-*` |
| A2 | inventario (modal) | Código dado de baja: "…con el nombre, el stock y la categoría que indiques." (la categoría no se precarga) | `inventario-A2-*` |
| M1 | inventario (modal) | Modificar stock: FIL-01 con "Filtro" precargado cambiado a "Aceite"; C-99 dado de baja con "Motor" precargado | `inventario-M1-*` |
| M2 | inventario | Resumen "FIL-01 · Filtro de aceite Ford: stock 9 sin cambios · categoría: Filtro → Aceite"; la tabla ya lo muestra en Aceite | `inventario-M2-*` |
| O1 | inventario (modal) | Nueva orden: línea 1 "Todas" + ACE-01; línea 2 "Filtro" con su lista corta (ilustración desplegada) | `inventario-O1-*` |
| O2 | inventario (modal) | Categoría "Motor" sin productos activos: solo "Elegí un producto…" + "No hay productos en esta categoría." | `inventario-O2-*` |
| P1 | inventario (hoja) | PDF filtrado por "Aceite": "Aceite · 3 productos · 2026-11-24", Código / Nombre / Categoría / Stock, "0 (sin stock)" en texto | `inventario-P1-*` + `inventario-P1-A4.pdf` |
| R10 | reportes | Reporte del mes: Código, Nombre, Categoría, Cantidad, Órdenes; "Sin categoría" atenuado; C-99 con "dado de baja"; sin filtro de categoría | `reportes-R10-*` |
| P2 | reportes (hoja) | PDF del reporte con la columna Categoría en texto | `reportes-P2-*` + `reportes-P2-A4.pdf` |

Pantallas a 390x844 y 1440x900 (`-mobile` / `-desktop`); las pantallas completas son de página entera, los modales (A*, M1, O*) del viewport; P1/P2 con `print` emulado.

## Decisiones dentro de la maqueta (a revisar)

- **Categoría en móvil**: a 390 px la tabla (inventario y reporte) no entra con una columna más, así que la columna "Categoría" se oculta y la categoría va como segunda línea bajo el nombre (en el reporte, bajo la marca "dado de baja"). Desde 640 px y en el papel es una columna. Alternativa: columna propia con scroll horizontal interno.
- **Barra del inventario en móvil**: buscador y filtro apilados a todo el ancho; "Exportar PDF" queda junto al título. Desde 640 px, los tres en una fila.
- **Nueva orden**: categoría (6,75 rem) y producto en una fila, cantidad y "Quitar" debajo; el producto elegido queda truncado en el desplegado cerrado a 390 px (como en C-06b).
- **Modificar stock**: "Nuevo nombre" y "Categoría" en la misma fila desde 640 px; apilados en móvil. No muestra "antes → después" en la línea (solo el resumen posterior).
- Nuevo ingreso: "Categoría (opcional)" va después de Stock.
- Estados agregados respecto de `design.md`: A1b (variante con Aceite) e I4b (combinada).
- I4 y O2 usan un catálogo de muestra sin productos activos de Motor (en I1 hay dos).

## (TBD) / límites

- (TBD) Nombres de producto de muestra.
- Los desplegables nativos no se capturan abiertos: I5 y la lista de O1 son ilustraciones con `<select size>`.
- Las capturas P1/P2 son de ancho de viewport; los PDF A4 son de Chromium (`page.pdf`) y no se abrieron ni rasterizaron.

Approval: approved (2026-11-24, by user)
