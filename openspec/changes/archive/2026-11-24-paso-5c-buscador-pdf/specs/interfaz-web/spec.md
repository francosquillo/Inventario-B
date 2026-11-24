## MODIFIED Requirements

### Requirement: Tabla de inventario
`/inventario` SHALL mostrar primero la barra de acciones ("Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes") y la tabla de productos activos de `GET /api/inventario` (código, nombre, stock, acción "Eliminar") en el orden de la API, con la cantidad de productos y el stock 0 resaltado. Sobre la tabla SHALL mostrar el campo "Buscar" y el botón "Exportar PDF". La web SHALL NOT ofrecer los antiguos "Ingreso de stock" ni "Egreso de stock".

#### Scenario: Producto sin stock
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se abre `/inventario`
- **THEN** la tabla muestra `A-01` y luego `B-10`, el stock de `B-10` resaltado como sin stock y el texto "2 productos"

#### Scenario: Cargando
- **GIVEN** `GET /api/inventario` todavía no respondió
- **THEN** se ve el estado "Cargando inventario…" en lugar de la tabla

#### Scenario: Botones nuevos
- **WHEN** se abre `/inventario`
- **THEN** la barra muestra "Nuevo ingreso" y "Modificar stock" y no muestra "Ingreso de stock" ni "Egreso de stock"
- **AND** ningún script de la web llama a `/api/stock/ingreso` ni a `/api/stock/egreso`

#### Scenario: Buscador y exportación visibles
- **GIVEN** al menos un producto activo
- **WHEN** se abre `/inventario`
- **THEN** sobre la tabla se ven el campo "Buscar" (vacío, con etiqueta accesible) y el botón "Exportar PDF" habilitado

### Requirement: Pantalla de órdenes
`/ordenes` SHALL mostrar un enlace "← Inventario", filtros opcionales Desde, Hasta y Número y la lista de `GET /api/ordenes` en el orden de la API con número, fecha y componentes (código, nombre y cantidad, incluidos productos dados de baja); cada orden SHALL tener sus acciones "Exportar PDF" y "Eliminar". Los filtros vacíos SHALL NOT enviarse.

#### Scenario: Todas las órdenes
- **GIVEN** las órdenes `OT-0042` (2026-11-18) y `OT-0041` (2026-11-15)
- **WHEN** se abre `/ordenes`
- **THEN** se listan `OT-0042` y luego `OT-0041` con sus componentes

#### Scenario: Filtro por fechas
- **WHEN** el usuario completa Desde `2026-11-16` y pulsa "Filtrar"
- **THEN** la interfaz llama a `GET /api/ordenes?desde=2026-11-16` y se lista solo `OT-0042`

#### Scenario: Limpiar filtros
- **WHEN** el usuario pulsa "Ver todas"
- **THEN** los filtros se vacían y se listan todas las órdenes

#### Scenario: Exportación por orden
- **GIVEN** las órdenes `OT-0042` y `OT-0041` listadas
- **WHEN** se abre `/ordenes`
- **THEN** cada orden muestra su propio botón "Exportar PDF" junto a "Eliminar", con nombre accesible "Exportar PDF de la orden OT-0042" (y de `OT-0041`)
- **AND** no hay un botón que exporte la lista completa

## ADDED Requirements

### Requirement: Buscador del inventario
El campo "Buscar" de `/inventario` SHALL filtrar, mientras se escribe y sin llamar a la API, las filas de productos activos cuyo código o nombre contiene el texto escrito, sin distinguir mayúsculas ni tildes e ignorando los espacios al principio y al final. Con texto vacío SHALL mostrar todos los productos. Las filas visibles SHALL conservar el orden de la API.

#### Scenario: Por nombre parcial
- **GIVEN** los productos `A-01` "Tornillo M8", `B-10` "Tuerca M8" y `C-03` "Arandela"
- **WHEN** el usuario escribe `tor`
- **THEN** la tabla muestra solo `A-01`
- **AND** no se envía ninguna petición a la API

#### Scenario: Por código parcial y en minúsculas
- **GIVEN** los productos `A-01`, `A-02` y `B-10`
- **WHEN** el usuario escribe `a-0`
- **THEN** la tabla muestra `A-01` y luego `A-02`

#### Scenario: Texto que aparece en código y nombre
- **GIVEN** los productos `M8-1` "Arandela" y `A-01` "Tornillo M8"
- **WHEN** el usuario escribe `m8`
- **THEN** la tabla muestra ambos productos en el orden de la API

#### Scenario: Sin tildes
- **GIVEN** el producto `C-99` "Junta tórica"
- **WHEN** el usuario escribe `TORICA`
- **THEN** la tabla muestra `C-99`

#### Scenario: Solo espacios
- **WHEN** el usuario escribe `"   "`
- **THEN** la tabla muestra todos los productos y el conteo dice "N productos"

### Requirement: Conteo durante la búsqueda
Mientras haya texto de búsqueda y se vean menos productos que los activos (V < T), el conteo del inventario SHALL decir "V de T productos" (V visibles, T activos); sin búsqueda, o cuando la búsqueda deja visibles todos los productos (V = T), SHALL decir "T productos" como hasta ahora (cambio pedido por el usuario, 2026-11-24).

#### Scenario: Conteo filtrado
- **GIVEN** 12 productos activos, 2 de los cuales contienen `tor`
- **WHEN** el usuario escribe `tor`
- **THEN** el conteo dice "2 de 12 productos"

#### Scenario: La búsqueda coincide con todos los productos
- **GIVEN** 12 productos activos y todos contienen `m`
- **WHEN** el usuario escribe `m`
- **THEN** el conteo dice "12 productos" (no "12 de 12 productos")

#### Scenario: Conteo al borrar la búsqueda
- **WHEN** el usuario vacía el campo "Buscar"
- **THEN** el conteo vuelve a "12 productos"

### Requirement: Búsqueda sin coincidencias
Si la búsqueda no coincide con ningún producto, `/inventario` SHALL mostrar en lugar de las filas el cartel "Ningún producto coincide con «<texto>»" con el botón "Limpiar búsqueda", que vacía el campo, muestra todos los productos y devuelve el foco al campo. Pulsar Escape dentro del campo SHALL tener el mismo efecto.

#### Scenario: Sin coincidencias
- **WHEN** el usuario escribe `xyz` y ningún producto lo contiene
- **THEN** se ve "Ningún producto coincide con «xyz»" y el botón "Limpiar búsqueda"
- **AND** el conteo dice "0 de 12 productos"

#### Scenario: Limpiar búsqueda
- **WHEN** el usuario pulsa "Limpiar búsqueda"
- **THEN** el campo queda vacío, se ven todos los productos y el foco está en el campo "Buscar"

#### Scenario: Escape en el campo
- **GIVEN** el campo "Buscar" con `tor`
- **WHEN** el usuario pulsa Escape dentro del campo
- **THEN** el campo queda vacío y se ven todos los productos

#### Scenario: Texto mostrado literal
- **WHEN** el usuario busca `<b>x</b>` sin coincidencias
- **THEN** el cartel muestra ese texto literal, sin interpretarlo como HTML

### Requirement: Búsqueda conservada al actualizar el inventario
Cuando el inventario se recarga tras un nuevo ingreso, una modificación de stock, una orden o una baja, la búsqueda escrita SHALL conservarse y aplicarse a la lista nueva. La búsqueda SHALL NOT conservarse al volver a abrir la página.

#### Scenario: Recarga tras modificar stock
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario guarda una modificación de stock
- **THEN** el campo sigue con `tor` y la tabla muestra solo las coincidencias con el stock actualizado

#### Scenario: Producto nuevo que no coincide
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario crea el producto `N-01` "Arandela"
- **THEN** la alerta de éxito se muestra y `N-01` no aparece en la tabla hasta limpiar la búsqueda

### Requirement: Exportar el inventario a PDF
"Exportar PDF" en `/inventario` SHALL exportar, según `exportacion-pdf`, exactamente las filas visibles (todas o el resultado de la búsqueda) en el orden de la tabla, con columnas Código, Nombre y Stock, el título "Inventario", la cantidad de filas exportadas y la fecha de exportación; el criterio de búsqueda y el usuario no se imprimen (revisión pedida por el usuario, 2026-11-24).

#### Scenario: Exportar el resultado de una búsqueda
- **GIVEN** la búsqueda `tor` que muestra `A-01` y `D-07`
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista solo `A-01` y `D-07`, con "2 productos" y sin mostrar «tor»

#### Scenario: Exportar todo el inventario
- **GIVEN** 12 productos y el campo "Buscar" vacío
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista los 12 productos con "12 productos"

### Requirement: Exportar una orden a PDF
El botón "Exportar PDF" de una orden en `/ordenes` SHALL exportar, según `exportacion-pdf`, solo esa orden (decisión del usuario, 2026-11-24): encabezado "Orden <número>" y "Fecha: AAAA-MM-DD · N componentes" (sin usuario creador; revisión del usuario, 2026-11-24), y la tabla de sus componentes por código, incluidos productos dados de baja. Las demás órdenes SHALL NOT aparecer.

#### Scenario: Exportar una orden
- **GIVEN** la lista con `OT-0042` (2026-11-18, creada por `admin`, componentes `A-01` x 2 y `B-02` x 1) y `OT-0041`
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0042`
- **THEN** el documento muestra "Orden OT-0042", "Fecha: 2026-11-18 · 2 componentes", `A-01` x 2 y `B-02` x 1
- **AND** no muestra "Creada por" ni `admin`
- **AND** no muestra `OT-0041`

#### Scenario: Componente dado de baja
- **GIVEN** la orden `OT-0001` con el componente `C-99` cuyo producto quedó dado de baja
- **WHEN** el usuario exporta `OT-0001`
- **THEN** el documento incluye `C-99` con su nombre y cantidad

#### Scenario: Lista intacta tras exportar
- **GIVEN** la lista filtrada con Desde `2026-11-16`
- **WHEN** el usuario exporta una orden y cierra el diálogo de impresión
- **THEN** la pantalla sigue mostrando la misma lista filtrada, con todas sus órdenes visibles

#### Scenario: Sin órdenes no hay exportación
- **WHEN** la lista muestra "No hay órdenes" o "No hay órdenes en ese período"
- **THEN** no se ve ningún botón "Exportar PDF"
