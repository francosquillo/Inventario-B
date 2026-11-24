# exportacion-pdf Specification

## Purpose
Define cómo la web de Inventario-B exporta a PDF lo que el usuario está viendo (el inventario, una orden y, en adelante, reportes), con un formato imprimible uniforme, sin dependencias nuevas y reutilizable por cualquier pantalla.

## Requirements

### Requirement: Exportación por el diálogo de impresión
La acción "Exportar PDF" SHALL abrir el diálogo de impresión del navegador, desde el que el usuario elige "Guardar como PDF" o una impresora. La exportación SHALL NOT llamar a la API ni modificar datos, y SHALL usar los datos ya cargados en la pantalla.

#### Scenario: Exportar sin pedidos a la API
- **GIVEN** `/inventario` con la tabla cargada
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** se abre el diálogo de impresión del navegador
- **AND** no se envía ninguna petición a la API

#### Scenario: Cancelar la exportación
- **WHEN** el usuario cierra el diálogo de impresión sin guardar
- **THEN** la pantalla queda igual que antes (búsqueda, filtros, lista y título de la pestaña)

### Requirement: Encabezado del documento exportado
El documento exportado SHALL empezar con un encabezado mínimo (revisión pedida por el usuario, 2026-11-24): el título de lo exportado, una fecha en formato `AAAA-MM-DD` y la cantidad de elementos exportados (productos del inventario; componentes de una orden). El encabezado SHALL NOT incluir el criterio de búsqueda ni de filtros, el usuario de la sesión, la hora de generación ni "Creada por". Este encabezado SHALL NOT verse en pantalla.

#### Scenario: Encabezado del inventario con búsqueda
- **GIVEN** el usuario `admin` buscó `tor` y se ven 2 de 12 productos, el 2026-11-24
- **WHEN** exporta el inventario
- **THEN** el documento empieza con "Inventario", "2 productos" y "2026-11-24"
- **AND** no muestra la búsqueda `tor`, el usuario `admin` ni la hora

#### Scenario: Encabezado del inventario completo
- **GIVEN** no hay búsqueda aplicada y hay 64 productos, el 2026-11-24
- **WHEN** el usuario exporta
- **THEN** el encabezado dice "Inventario", "64 productos" y "2026-11-24", sin línea de criterio

#### Scenario: Oculto en pantalla
- **WHEN** se ve `/inventario` o `/ordenes` en pantalla
- **THEN** el encabezado de exportación no es visible

### Requirement: Hoja de impresión clara
El documento exportado SHALL usar fondo blanco y texto oscuro (independiente del tema oscuro de pantalla), y SHALL ocultar la cabecera de la app, la navegación, los botones, los campos de búsqueda y filtros, las alertas, los modales y la columna de acciones. Los datos de la tabla SHALL conservarse completos, sin recortes ni scroll horizontal.

#### Scenario: Sin controles en el papel
- **WHEN** se exporta el inventario
- **THEN** el documento no muestra "Cerrar sesión", "Nuevo ingreso", "Exportar PDF", el campo de búsqueda ni la columna "Eliminar"

#### Scenario: Colores para papel
- **GIVEN** la pantalla con el tema oscuro
- **WHEN** se exporta cualquier vista
- **THEN** el documento tiene fondo blanco y texto oscuro

#### Scenario: Marcas sin depender del color
- **GIVEN** un producto con stock 0
- **WHEN** se exporta el inventario
- **THEN** su stock se lee "0 (sin stock)" en el documento

### Requirement: Nombre de archivo sugerido
Al exportar, el navegador SHALL proponer como nombre del PDF el nombre de lo exportado seguido de la fecha local `AAAA-MM-DD` (por ejemplo `inventario-2026-11-24` u `orden-OT-0042-2026-11-24`), reemplazando por `-` todo carácter que no sea letra, dígito o guion; al cerrar el diálogo, el título de la pestaña SHALL volver a ser el original.

#### Scenario: Nombre del inventario
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario exporta el inventario y elige "Guardar como PDF"
- **THEN** el nombre propuesto es `inventario-2026-11-24`

#### Scenario: Nombre de una orden con caracteres especiales
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario exporta la orden `OT/2026#1`
- **THEN** el nombre propuesto es `orden-OT-2026-1-2026-11-24`

#### Scenario: Título restaurado
- **WHEN** el usuario cierra el diálogo de impresión
- **THEN** la pestaña vuelve a titularse como antes de exportar

### Requirement: Saltos de página legibles
En un documento de varias páginas, la fila de títulos de cada tabla SHALL repetirse en cada página y ninguna fila SHALL partirse entre páginas; el encabezado del documento SHALL NOT quedar solo al pie de una página, separado de la tabla.

#### Scenario: Inventario largo
- **GIVEN** 120 productos visibles
- **WHEN** se exporta el inventario
- **THEN** cada página repite "Código / Nombre / Stock" y ninguna fila queda cortada

#### Scenario: Orden con muchos componentes
- **GIVEN** una orden con 60 componentes
- **WHEN** se exporta esa orden
- **THEN** cada página repite "Código / Nombre / Cantidad" y ninguna fila queda cortada

### Requirement: Exportación deshabilitada sin datos
Un botón "Exportar PDF" de una lista (como el del inventario) SHALL estar deshabilitado mientras la lista está cargando, muestra un error o no tiene elementos visibles, y habilitado cuando hay al menos un elemento.

#### Scenario: Búsqueda sin coincidencias
- **WHEN** la búsqueda del inventario no coincide con ningún producto
- **THEN** "Exportar PDF" está deshabilitado

#### Scenario: Cargando
- **GIVEN** la lista todavía no respondió
- **THEN** "Exportar PDF" está deshabilitado

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
