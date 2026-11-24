# Mockups — paso-5c-buscador-pdf (C-06c)

- Design system revision: 2 (`design-system/tokens.css` y `ui.css`, tema oscuro único; cabecera de texto "Inventario", sin logo)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24)

Base visual: mockups aprobados de C-06b (`archive/2026-11-23-paso-5b-fixes-menores/mockups/`) y C-06 (órdenes). `assets/mockup.css` es copia del de C-06b; `assets/mockup-5c.css` tiene lo nuevo de este change (candidato a `static/css/app.css` en el apply). `assets/mockup.js` es solo de la maqueta (filtra de verdad al teclear en el buscador).

## Cómo verlos

Abrir `inventario.html` u `ordenes.html` en el navegador (o servir la raíz del repo con `python -m http.server 8765` y abrir `http://localhost:8765/openspec/changes/paso-5c-buscador-pdf/mockups/inventario.html`). El selector de la barra superior cambia de estado (`#I1`, `#B1`...); `?captura` oculta la barra. Requiere red para el CDN de Tailwind (igual que los mockups anteriores).

Para ver la impresión: elegir P1/P2/P3 (muestran la hoja como papel) y usar Ctrl+P: la barra de la maqueta se oculta y queda solo la hoja. En la app real el mecanismo es el `@media print` sobre la propia página (design D2), no una hoja aparte; la maqueta fija el aspecto.

## Estados

| ID | Pantalla | Qué muestra | Capturas (`previews/`) |
|----|----------|-------------|------------------------|
| I1 | Inventario | Buscador vacío, "Exportar PDF" habilitado, "12 productos" | `inventario-I1-{mobile,desktop}.png` |
| B1 | Inventario | Búsqueda `tor`: 2 filas (Tornillo M8, Junta tórica: coincide sin tilde), "2 de 12 productos" | `inventario-B1-*` |
| B2 | Inventario | `xyz` sin coincidencias: cartel con "Limpiar búsqueda", "0 de 12 productos", "Exportar PDF" deshabilitado | `inventario-B2-*` |
| B3 | Inventario | Cargando: buscador visible, "Exportar PDF" deshabilitado | `inventario-B3-*` |
| O1 | Órdenes | Lista con "Exportar PDF" + "Eliminar" por orden (sin botón global) | `ordenes-O1-*` |
| P1 | Impresión | Inventario filtrado por `tor`: hoja clara, encabezado solo con título, cantidad ("2 productos") y fecha, sin criterio de búsqueda ni usuario, sin controles ni columna de acciones | `inventario-P1-*` + `inventario-P1-A4.pdf` |
| P2 | Impresión | Inventario completo (64 productos de muestra), "0 (sin stock)" en texto, encabezado de tabla repetido por página | `inventario-P2-*` + `inventario-P2-A4.pdf` (3 páginas) |
| P3 | Impresión | Orden `OT-0042` sola: encabezado con "Orden OT-0042" y "Fecha: 2026-11-24 · 3 componentes" (sin "Creada por" ni usuario) | `ordenes-P3-*` + `ordenes-P3-A4.pdf` |

Todas las pantallas a 390x844 y 1440x900 (`-mobile` / `-desktop`). Los P* con `print` emulado (colores de papel, sin barra).

## Decisiones de diseño dentro de la maqueta

- Móvil (390 px): el buscador baja a su propia fila a todo el ancho y "Exportar PDF" queda junto al título/conteo, para que el placeholder "Buscar por código o nombre" no se corte. Desde 640 px todo va en una fila (título, buscador de 18 rem, botón).
- Órdenes: "Exportar PDF" y "Eliminar" van juntos a la derecha del encabezado; a 390 px bajan a una segunda línea (número, fecha y "N componentes" arriba). Sin scroll horizontal.
- Revisión pedida por el usuario (2026-11-24): el encabezado del PDF del inventario es solo título + cantidad exportada + fecha de exportación (`AAAA-MM-DD`); el de una orden es título + fecha de la orden + cantidad de componentes ("Fecha: AAAA-MM-DD · N componentes"). Se quitaron criterio de búsqueda, usuario, línea "Generado" y "Creada por".
- Hoja de impresión: blanco/negro (`#fff`/`#111`), sin columna "Eliminar", stock 0 como "0 (sin stock)", `@page` con margen 15 mm sin forzar tamaño.

## (TBD) / límites

- (TBD) Las fechas del encabezado son de muestra (2026-11-24); en la app la del inventario sale del reloj local y la de una orden de su campo `fecha`.
- Los PDF A4 se generaron con `page.pdf` de Chromium (referencia de paginación); el diálogo de impresión real del navegador del usuario puede variar (márgenes, encabezados/pies del navegador).
- El repetido del encabezado de tabla en P2 se debe a `thead { display: table-header-group }`; el PDF no se pudo rasterizar en esta máquina (sin poppler), así que la repetición no se inspeccionó visualmente (3 páginas confirmadas por el conteo de páginas del PDF).

Approval: approved (2026-11-24, by user)
