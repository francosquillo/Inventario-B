# Mockups — paso-5d-reporte-ordenes-fechas (C-06d)

- Design system revision: 2 (`design-system/tokens.css` y `ui.css`, tema oscuro único; cabecera de texto "Inventario", sin logo)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24)

Base visual: mockups aprobados de C-06c (`archive/2026-11-24-paso-5c-buscador-pdf/mockups/`) y de C-06 (filtros de órdenes). `assets/mockup.css`, `assets/mockup-5c.css` (incluye la hoja de impresión) y `assets/tailwind-config.js` son copias de C-06c; `assets/mockup-5d.css` tiene lo propio de este change; `assets/mockup.js` es solo de la maqueta (selector de estados y datos de muestra).

## Cómo verlos

Abrir `reportes.html` en el navegador (o servir la raíz del repo con `python -m http.server 8765`). El selector de la barra superior cambia de estado (`#R0`, `#R1`...); `?captura` oculta la barra. Requiere red para el CDN de Tailwind. Para ver la impresión: elegir P4/P5 y Ctrl+P (la barra se oculta y queda solo la hoja; en la app real es el `@media print` de `static/css/app.css` sobre la propia página).

## Estados

| ID | Pantalla | Qué muestra | Capturas (`previews/`) |
|----|----------|-------------|------------------------|
| R0 | Reportes | Inicial: Desde 2026-11-01 y Hasta 2026-11-24 precompletados, cartel "Elegí el período y pulsá «Generar» para ver el reporte.", sin tabla, "Exportar PDF" deshabilitado | `reportes-R0-{mobile,desktop}.png` |
| N1 | Navegación | Cabecera con Inventario / Órdenes / Reportes, apilada tres veces con la pestaña actual de cada página | `reportes-N1-*` |
| R1 | Reportes | Mes generado: "5 productos · 2026-11-01 a 2026-11-24", un producto "dado de baja", orden por cantidad desc., "Exportar PDF" habilitado | `reportes-R1-*` |
| R2 | Reportes | Filtrado por `A-01 · Tornillo M8`: 1 fila | `reportes-R2-*` |
| R3 | Reportes | Vacío: "No hay productos usados en órdenes entre 2026-10-01 y 2026-10-31", exportar deshabilitado | `reportes-R3-*` |
| R4 | Reportes | Rango invertido: error bajo Hasta ("Desde no puede ser posterior a Hasta."), campo inválido | `reportes-R4-*` |
| R4b | Reportes | Variante: Desde vacío, error "La fecha es obligatoria." bajo Desde | `reportes-R4b-*` |
| R5 | Reportes | "Generando reporte…", "Generar" y "Exportar PDF" deshabilitados | `reportes-R5-*` |
| R6 | Reportes | Error de servidor con "Reintentar" | `reportes-R6-*` |
| R7 | Reportes | Selector de producto desplegado (ilustración con `<select size>`; el nativo no se captura abierto): "Todos los productos", grupos "Activos" y "Dados de baja" | `reportes-R7-*` |
| R8 | Reportes | Filtrado por `C-99 · Junta tórica` (dado de baja): 1 fila con la marca "dado de baja" | `reportes-R8-*` |
| R9 | Reportes | Hasta vacío (ayuda "Vacío = hoy"): resumen con el hasta efectivo 2026-11-24 | `reportes-R9-*` |
| P4 | Impresión | "Reporte de productos en órdenes" + "2026-11-01 a 2026-11-24 · 5 productos", hoja clara, "dado de baja" en negrita, sin filtros ni nav | `reportes-P4-*` + `reportes-P4-A4.pdf` (1 pág.) |
| P5 | Impresión | Reporte largo (60 filas de muestra) en varias páginas | `reportes-P5-*` + `reportes-P5-A4.pdf` (2 pág.) |

Pantallas a 390x844 y 1440x900 (`-mobile` / `-desktop`, página completa); P4-P5 con `print` emulado.

## Decisiones dentro de la maqueta

- Orden de columnas: Código, Nombre, Cantidad, Órdenes (pedido para esta maqueta); `design.md` D3 y la spec `interfaz-web` dicen "Órdenes, Cantidad": si se aprueba este orden, hay que actualizarlos.
- Móvil: Desde/Hasta en dos columnas, Producto a todo el ancho, botones debajo; la tabla entra en 390 px sin scroll horizontal (`tbl-fit`); la marca "dado de baja" baja bajo el nombre si no cabe.
- Desktop: filtros y botones en una sola fila.
- R4/R4b/R7 muestran el cartel inicial (no hay reporte generado).
- Etiquetas "(obligatorio)" / "(opcional)" y ayuda "Vacío = hoy" bajo Hasta (propuesta; (TBD) si se prefiere sin etiquetas).

## (TBD) / límites

- (TBD) Textos de ayuda del cartel de error y del vacío ("Probá con otro período…") son propuestas.
- (TBD) Nombres de producto de muestra (el pedido usaba "Tornillo" / "Viejo"; se usó "Tornillo M8" y "Junta tórica").
- Los PDF A4 son de Chromium (`page.pdf`); no se pudo rasterizar el PDF (sin poppler), así que la repetición del encabezado de tabla en la página 2 de P5 no se inspeccionó visualmente (2 páginas confirmadas por `/Count`; `thead { display: table-header-group }`).
- Los P4/P5 en PNG se capturan a ancho de viewport; en papel el margen es `@page 15mm`.

Approval: approved (2026-11-24, by user)
