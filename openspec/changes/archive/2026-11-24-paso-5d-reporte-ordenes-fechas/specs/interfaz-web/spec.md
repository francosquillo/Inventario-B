## MODIFIED Requirements

### Requirement: Cabecera y cierre de sesión
Las páginas protegidas SHALL mostrar una cabecera con el título de texto "Inventario" (sin logo), la navegación por secciones con las pestañas "Inventario" (`/inventario`), "Órdenes" (`/ordenes`) y "Reportes" (`/reportes`), marcando la pestaña de la página actual con `aria-current="page"`, el usuario de `GET /api/me` y el botón "Cerrar sesión", que SHALL llamar a `POST /api/logout` y navegar a `/`.

#### Scenario: Cerrar sesión
- **GIVEN** el usuario está en `/inventario`
- **WHEN** pulsa "Cerrar sesión"
- **THEN** el navegador queda en `/` y un acceso posterior a `/inventario` vuelve al login

#### Scenario: Usuario visible
- **WHEN** el `admin` abre `/inventario` en escritorio
- **THEN** la cabecera muestra "Usuario: admin"

#### Scenario: Pestaña Reportes
- **GIVEN** el usuario está en `/inventario` o en `/ordenes`
- **WHEN** pulsa la pestaña "Reportes"
- **THEN** el navegador queda en `/reportes` y esa pestaña está marcada como la actual

#### Scenario: Navegación en móvil
- **GIVEN** un ancho de 390 px
- **WHEN** se abre cualquier página protegida
- **THEN** las tres pestañas se ven completas, sin scroll horizontal de la página

## ADDED Requirements

### Requirement: Pantalla de reportes
`/reportes` SHALL mostrar el título "Reportes" y el reporte "Productos usados en órdenes" con los filtros "Desde (obligatorio)", "Hasta (opcional)" (ayuda "Vacío = hoy") y Producto (opcional), y el botón "Generar". El resultado SHALL ser una tabla con las columnas Código, Nombre, Cantidad y Órdenes, en el orden de la API, y una línea de resumen (decidido por el usuario al aprobar mockups, 2026-11-24).

#### Scenario: Generar con un rango
- **WHEN** el usuario completa Desde `2026-10-01`, Hasta `2026-10-31` y pulsa "Generar"
- **THEN** la interfaz llama a `GET /api/reportes/productos-en-ordenes?desde=2026-10-01&hasta=2026-10-31`, sin `codigo`, y muestra una fila por producto con su cantidad total y sus órdenes

#### Scenario: Generar sin Hasta
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario completa Desde `2026-11-01`, deja Hasta vacío y pulsa "Generar"
- **THEN** la llamada no incluye `hasta` y el rango mostrado es "2026-11-01 a 2026-11-24"

#### Scenario: Línea de resumen
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24 con 5 productos
- **THEN** el resumen dice "2026-11-01 a 2026-11-24 · 5 productos" (con 1 producto, "1 producto"; con el filtro `A-01 · Tornillo`, "A-01 · Tornillo · 2026-11-01 a 2026-11-24 · 1 producto"; con Hasta vacío, el rango usa el `hasta` efectivo), igual que la línea del PDF (decidido por el usuario al aprobar mockups, 2026-11-24)

#### Scenario: Cambiar filtros no altera el resultado mostrado
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24
- **WHEN** el usuario cambia Desde sin pulsar "Generar"
- **THEN** la tabla y el rango mostrado siguen siendo los del reporte generado

### Requirement: Estado inicial del reporte
Al abrir `/reportes`, Desde SHALL venir completado con el primer día del mes en curso y Hasta con la fecha de hoy (fecha local), pero el reporte SHALL NOT generarse hasta que el usuario pulse "Generar" (decisión del usuario, 2026-11-24). Hasta entonces SHALL verse, en lugar de la tabla, el cartel neutro "Elegí el período y pulsá «Generar» para ver el reporte." y "Exportar PDF" SHALL estar deshabilitado.

#### Scenario: Apertura sin generar
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario abre `/reportes`
- **THEN** Desde vale `2026-11-01` y Hasta vale `2026-11-24`
- **AND** no se llama a `GET /api/reportes/productos-en-ordenes`, se ve el cartel "Elegí el período y pulsá «Generar» para ver el reporte." y "Exportar PDF" está deshabilitado

#### Scenario: Primera generación
- **GIVEN** la página recién abierta el 2026-11-24 con el mes en curso
- **WHEN** el usuario pulsa "Generar"
- **THEN** la interfaz llama a `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-24` y el cartel inicial deja de verse

### Requirement: Selector de producto del reporte
El filtro Producto SHALL ofrecer "Todos los productos" (sin filtro) y solo los productos de `GET /api/reportes/productos-usados`, es decir, usados en al menos una orden de cualquier fecha (decisión del usuario, 2026-11-24): los activos en un grupo "Activos" y los dados de baja en un grupo "Dados de baja", cada uno como "CÓDIGO · Nombre", ordenados por código; un grupo vacío SHALL NOT mostrarse. Elegir un producto SHALL enviar su código como `codigo`.

#### Scenario: Filtrar por un producto activo
- **WHEN** el usuario elige `A-01 · Tornillo` en "Activos" y pulsa "Generar"
- **THEN** la llamada incluye `codigo=A-01` y la tabla muestra solo `A-01`

#### Scenario: Filtrar por un producto dado de baja
- **GIVEN** `C-99` "Viejo" está dado de baja y se usó x 2 en una orden del 2026-11-12
- **WHEN** el usuario elige `C-99 · Viejo` en el grupo "Dados de baja" con el rango 2026-11-01 a 2026-11-24 y pulsa "Generar"
- **THEN** la llamada incluye `codigo=C-99` y la tabla muestra solo `C-99` con cantidad 2, 1 orden y la marca "dado de baja"

#### Scenario: Productos nunca usados no se ofrecen
- **GIVEN** el producto activo `B-02` nunca se usó en una orden
- **WHEN** el usuario abre el selector
- **THEN** `B-02` no está entre las opciones

#### Scenario: Lista de productos no disponible
- **WHEN** falla `GET /api/reportes/productos-usados` al abrir la página
- **THEN** el selector ofrece solo "Todos los productos" y el reporte se puede generar igual

### Requirement: Productos dados de baja en el resultado
Una fila de un producto dado de baja SHALL mostrar junto al nombre la marca de texto "dado de baja" (no solo un color).

#### Scenario: Dado de baja en el reporte general
- **GIVEN** `C-99` "Viejo" dado de baja se usó en una orden del rango
- **WHEN** se genera el reporte sin filtro de producto
- **THEN** la fila de `C-99` muestra "Viejo" con la marca "dado de baja"

### Requirement: Estados del reporte
Mientras la API no responde, `/reportes` SHALL mostrar "Generando reporte…" y deshabilitar "Generar" y "Exportar PDF". Si la API devuelve 422, SHALL mostrar su `detail` junto a los filtros; ante un error de red o del servidor, SHALL mostrar el error con "Reintentar", que repite la última consulta.

#### Scenario: Generando
- **GIVEN** la API todavía no respondió
- **THEN** se ve "Generando reporte…" y "Generar" y "Exportar PDF" están deshabilitados

#### Scenario: Error del servidor
- **WHEN** la API responde 500 o no hay red
- **THEN** se ve el mensaje de error con el botón "Reintentar", que repite la última consulta

### Requirement: Reporte vacío en pantalla
Si la API devuelve `[]`, `/reportes` SHALL mostrar en lugar de la tabla el cartel "No hay productos usados en órdenes entre AAAA-MM-DD y AAAA-MM-DD" o, si se filtró por un producto, "«CÓDIGO · Nombre» no se usó en órdenes entre AAAA-MM-DD y AAAA-MM-DD", con el `hasta` efectivo.

#### Scenario: Período sin consumo
- **WHEN** el reporte del 2026-10-01 al 2026-10-31 devuelve `[]`
- **THEN** se ve "No hay productos usados en órdenes entre 2026-10-01 y 2026-10-31" y no se ve la tabla

#### Scenario: Producto sin consumo
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el reporte filtrado por `A-01 · Tornillo` desde el 2026-11-01 con Hasta vacío devuelve `[]`
- **THEN** se ve "«A-01 · Tornillo» no se usó en órdenes entre 2026-11-01 y 2026-11-24"

### Requirement: Validación de fechas del reporte en el navegador
Antes de llamar a la API, `/reportes` SHALL validar que Desde esté completo y sea una fecha real `AAAA-MM-DD`, que Hasta, si está completo, también lo sea, y que Desde no sea posterior a Hasta (o a hoy si Hasta está vacío); si no, SHALL mostrar el error junto al campo afectado, marcarlo como inválido, llevar el foco a él y no llamar a la API.

#### Scenario: Desde vacío
- **WHEN** el usuario borra Desde y pulsa "Generar"
- **THEN** se ve "La fecha es obligatoria." bajo Desde y no se llama a la API

#### Scenario: Hasta vacío es válido
- **WHEN** el usuario borra Hasta y pulsa "Generar"
- **THEN** no hay error y se llama a la API sin `hasta`

#### Scenario: Rango invertido
- **WHEN** el usuario pone Desde `2026-11-30`, Hasta `2026-11-01` y pulsa "Generar"
- **THEN** se ve el error de rango bajo Hasta y no se llama a la API

#### Scenario: Desde posterior a hoy sin Hasta
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario pone Desde `2026-12-01`, deja Hasta vacío y pulsa "Generar"
- **THEN** se ve un error de rango bajo Desde y no se llama a la API

### Requirement: Exportar el reporte a PDF
`/reportes` SHALL tener un botón "Exportar PDF" que exporta, según `exportacion-pdf`, solo la tabla del último reporte generado (columnas Código, Nombre, Cantidad y Órdenes, con "dado de baja" en texto), sin los filtros. El botón SHALL estar deshabilitado antes de la primera generación, mientras se genera, ante un error o con el reporte vacío.

#### Scenario: Exportar sin filtros en el papel
- **GIVEN** un reporte generado con 5 productos
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** se abre el diálogo de impresión y el documento no muestra los filtros, la navegación ni los botones

#### Scenario: Reporte vacío
- **WHEN** el reporte generado no tiene filas
- **THEN** "Exportar PDF" está deshabilitado

### Requirement: Encabezado del PDF del reporte
El documento exportado del reporte SHALL empezar con el título "Reporte de productos en órdenes" y una sola línea "AAAA-MM-DD a AAAA-MM-DD · N productos" con el `hasta` efectivo del reporte generado, precedida de "CÓDIGO · Nombre · " cuando se filtró por un producto; sin usuario ni hora.

#### Scenario: Encabezado del reporte del mes
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24 con 5 productos
- **WHEN** el usuario exporta
- **THEN** el documento empieza con "Reporte de productos en órdenes" y "2026-11-01 a 2026-11-24 · 5 productos"

#### Scenario: Encabezado con Hasta vacío
- **GIVEN** un reporte generado el 2026-11-24 con Desde `2026-11-01` y Hasta vacío, con 3 productos
- **WHEN** el usuario exporta
- **THEN** la línea del encabezado es "2026-11-01 a 2026-11-24 · 3 productos"

#### Scenario: Encabezado de un producto
- **GIVEN** un reporte generado de `A-01 · Tornillo` del 2026-11-01 al 2026-11-24
- **WHEN** el usuario exporta
- **THEN** la línea del encabezado es "A-01 · Tornillo · 2026-11-01 a 2026-11-24 · 1 producto"
