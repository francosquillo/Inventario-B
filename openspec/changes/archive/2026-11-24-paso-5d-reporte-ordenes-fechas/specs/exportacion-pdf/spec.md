## ADDED Requirements

### Requirement: Nombre de archivo de un reporte por rango
Al exportar un reporte por rango de fechas, el navegador SHALL proponer como nombre del PDF `reporte-AAAA-MM-DD_AAAA-MM-DD` con las fechas del rango consultado (o `reporte-<código>-AAAA-MM-DD_AAAA-MM-DD` si se filtró por un producto, con todo carácter del código que no sea letra, dígito o guion reemplazado por `-`), sin la fecha de exportación; al cerrar el diálogo el título de la pestaña SHALL volver a ser el original. Los nombres del inventario y de una orden SHALL NOT cambiar.

#### Scenario: Reporte de todos los productos
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24, exportado el 2026-11-25
- **WHEN** el usuario elige "Guardar como PDF"
- **THEN** el nombre propuesto es `reporte-2026-11-01_2026-11-24`

#### Scenario: Reporte con Hasta vacío
- **GIVEN** un reporte generado el 2026-11-24 con Desde `2026-11-01` y Hasta vacío (hasta efectivo: hoy)
- **WHEN** el usuario exporta
- **THEN** el nombre propuesto es `reporte-2026-11-01_2026-11-24`

#### Scenario: Reporte de un producto con caracteres especiales
- **GIVEN** un reporte generado del producto `A/01` del 2026-11-01 al 2026-11-24
- **WHEN** el usuario exporta
- **THEN** el nombre propuesto es `reporte-A-01-2026-11-01_2026-11-24`

#### Scenario: Inventario sin cambios
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario exporta el inventario
- **THEN** el nombre propuesto sigue siendo `inventario-2026-11-24`

### Requirement: Saltos de página del reporte
Un reporte exportado de varias páginas SHALL repetir la fila de títulos "Código / Nombre / Cantidad / Órdenes" en cada página, sin partir filas entre páginas ni dejar el encabezado del documento separado de la tabla.

#### Scenario: Reporte largo
- **GIVEN** un reporte con 120 productos
- **WHEN** se exporta
- **THEN** cada página repite "Código / Nombre / Cantidad / Órdenes" y ninguna fila queda cortada
