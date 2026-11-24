## MODIFIED Requirements

### Requirement: Tabla de inventario
`/inventario` SHALL mostrar primero la barra de acciones ("Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes") y la tabla de productos activos de `GET /api/inventario` (código, nombre, categoría, stock, acción "Eliminar") en el orden de la API, con la cantidad de productos y el stock 0 resaltado. La columna "Categoría" SHALL mostrar el nombre de la categoría del producto (tomado de `GET /api/categorias`) o "Sin categoría" atenuado. Sobre la tabla SHALL mostrar el campo "Buscar", el filtro "Categoría" y el botón "Exportar PDF". La web SHALL NOT ofrecer los antiguos "Ingreso de stock" ni "Egreso de stock".

#### Scenario: Producto sin stock
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se abre `/inventario`
- **THEN** la tabla muestra `A-01` y luego `B-10`, el stock de `B-10` resaltado como sin stock y el texto "2 productos"

#### Scenario: Columna de categoría
- **GIVEN** los productos activos `A-01` (sin categoría) y `F-01` (categoría `filtro`)
- **WHEN** se abre `/inventario`
- **THEN** la fila de `A-01` muestra "Sin categoría" y la de `F-01` muestra "Filtro"

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
- **THEN** sobre la tabla se ven el campo "Buscar" (vacío, con etiqueta accesible), el filtro "Categoría" en "Todas las categorías" (con etiqueta accesible) y el botón "Exportar PDF" habilitado

#### Scenario: Categorías no disponibles
- **GIVEN** `GET /api/categorias` falla y `GET /api/inventario` responde
- **WHEN** se abre `/inventario`
- **THEN** la tabla se muestra igual, la columna "Categoría" muestra la clave de cada producto (o "Sin categoría") y el filtro ofrece solo "Todas las categorías"

### Requirement: Conteo durante la búsqueda
Mientras haya texto de búsqueda o una categoría elegida en el filtro y se vean menos productos que los activos (V < T), el conteo del inventario SHALL decir "V de T productos" (V visibles, T activos); sin búsqueda ni categoría, o cuando los filtros dejan visibles todos los productos (V = T), SHALL decir "T productos" (cambio pedido por el usuario, 2026-11-24).

#### Scenario: Conteo filtrado
- **GIVEN** 12 productos activos, 2 de los cuales contienen `tor`
- **WHEN** el usuario escribe `tor`
- **THEN** el conteo dice "2 de 12 productos"

#### Scenario: Conteo filtrado por categoría
- **GIVEN** 12 productos activos, 3 de la categoría `aceite`
- **WHEN** el usuario elige "Aceite" en el filtro
- **THEN** el conteo dice "3 de 12 productos"

#### Scenario: La búsqueda coincide con todos los productos
- **GIVEN** 12 productos activos y todos contienen `m`
- **WHEN** el usuario escribe `m`
- **THEN** el conteo dice "12 productos" (no "12 de 12 productos")

#### Scenario: Conteo al borrar la búsqueda
- **GIVEN** el filtro de categoría en "Todas las categorías"
- **WHEN** el usuario vacía el campo "Buscar"
- **THEN** el conteo vuelve a "12 productos"

### Requirement: Búsqueda sin coincidencias
Si la búsqueda y el filtro de categoría juntos no dejan ningún producto, `/inventario` SHALL mostrar en lugar de las filas un cartel con el botón "Limpiar filtros", que vacía el campo "Buscar", vuelve el filtro a "Todas las categorías", muestra todos los productos y devuelve el foco al campo "Buscar". El cartel SHALL decir "Ningún producto coincide con «<texto>»" si solo hay búsqueda, "Ningún producto en la categoría «<categoría>»" si solo hay categoría y "Ningún producto coincide con «<texto>» en la categoría «<categoría>»" si hay ambas. Pulsar Escape dentro del campo "Buscar" SHALL vaciar solo la búsqueda.

#### Scenario: Sin coincidencias
- **WHEN** el usuario escribe `xyz` y ningún producto lo contiene
- **THEN** se ve "Ningún producto coincide con «xyz»" y el botón "Limpiar filtros"
- **AND** el conteo dice "0 de 12 productos"

#### Scenario: Categoría sin productos
- **GIVEN** ningún producto activo de la categoría `motor`
- **WHEN** el usuario elige "Motor" en el filtro
- **THEN** se ve "Ningún producto en la categoría «Motor»" y el botón "Limpiar filtros"

#### Scenario: Búsqueda y categoría sin coincidencias
- **GIVEN** `A-01` "Tornillo" sin categoría y ningún producto de `aceite` que contenga `tor`
- **WHEN** el usuario escribe `tor` y elige "Aceite"
- **THEN** se ve "Ningún producto coincide con «tor» en la categoría «Aceite»"

#### Scenario: Limpiar búsqueda
- **WHEN** el usuario pulsa "Limpiar filtros"
- **THEN** el campo queda vacío, el filtro vuelve a "Todas las categorías", se ven todos los productos y el foco está en el campo "Buscar"

#### Scenario: Escape en el campo
- **GIVEN** el campo "Buscar" con `tor` y el filtro en "Aceite"
- **WHEN** el usuario pulsa Escape dentro del campo
- **THEN** el campo queda vacío, el filtro sigue en "Aceite" y se ven todos los productos de esa categoría

#### Scenario: Texto mostrado literal
- **WHEN** el usuario busca `<b>x</b>` sin coincidencias
- **THEN** el cartel muestra ese texto literal, sin interpretarlo como HTML

### Requirement: Búsqueda conservada al actualizar el inventario
Cuando el inventario se recarga tras un nuevo ingreso, una modificación de stock, una orden o una baja, la búsqueda escrita y la categoría elegida en el filtro SHALL conservarse y aplicarse a la lista nueva. Ninguna de las dos SHALL conservarse al volver a abrir la página.

#### Scenario: Recarga tras modificar stock
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario guarda una modificación de stock
- **THEN** el campo sigue con `tor` y la tabla muestra solo las coincidencias con el stock actualizado

#### Scenario: Producto nuevo que no coincide
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario crea el producto `N-01` "Arandela"
- **THEN** la alerta de éxito se muestra y `N-01` no aparece en la tabla hasta limpiar los filtros

#### Scenario: Cambio de categoría que saca el producto del filtro
- **GIVEN** el filtro en "Filtro" y `F-01` visible con categoría `filtro`
- **WHEN** el usuario cambia la categoría de `F-01` a "Aceite" con "Modificar stock"
- **THEN** el filtro sigue en "Filtro" y `F-01` deja de verse en la tabla

### Requirement: Exportar el inventario a PDF
"Exportar PDF" en `/inventario` SHALL exportar, según `exportacion-pdf`, exactamente las filas visibles (todas o el resultado de la búsqueda y del filtro de categoría) en el orden de la tabla, con columnas Código, Nombre, Categoría y Stock, el título "Inventario", la cantidad de filas exportadas y la fecha de exportación; con una categoría elegida, la línea del encabezado SHALL empezar con el nombre de esa categoría ("Sin categoría" incluido). El texto de búsqueda y el usuario no se imprimen (revisión pedida por el usuario, 2026-11-24).

#### Scenario: Exportar el resultado de una búsqueda
- **GIVEN** la búsqueda `tor` que muestra `A-01` y `D-07` y el filtro en "Todas las categorías"
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista solo `A-01` y `D-07`, con "2 productos" y sin mostrar «tor»

#### Scenario: Exportar una categoría
- **GIVEN** el filtro en "Aceite" que muestra 3 productos
- **WHEN** el usuario pulsa "Exportar PDF" el 2026-11-24
- **THEN** el documento lista esos 3 productos con su categoría y la línea "Aceite · 3 productos · 2026-11-24"

#### Scenario: Exportar todo el inventario
- **GIVEN** 12 productos, el campo "Buscar" vacío y el filtro en "Todas las categorías"
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista los 12 productos con "12 productos"

### Requirement: Modal de nuevo ingreso
El modal "Nuevo ingreso" SHALL pedir Código, Nombre y Stock (los tres obligatorios; el stock puede ser 0) y Categoría (selector con "Sin categoría", por defecto, y las categorías de `GET /api/categorias`), enviar `POST /api/productos` y, con éxito, cerrarse, recargar el inventario y mostrar una alerta de éxito que diga si el producto fue creado o reactivado.

#### Scenario: Producto nuevo con stock cero
- **GIVEN** ningún producto `N-01`
- **WHEN** el usuario crea `N-01` "Arandela 6mm" con stock 0 sin tocar Categoría
- **THEN** el modal se cierra, la tabla muestra `N-01` con stock 0 resaltado y "Sin categoría", y se ve "Producto creado: N-01 · Arandela 6mm (stock 0)."

#### Scenario: Producto nuevo con categoría
- **GIVEN** ningún producto `AC-10`
- **WHEN** el usuario crea `AC-10` "Aceite 10W40" con stock 4 y Categoría "Aceite"
- **THEN** se envía `"categoria": "aceite"` y la tabla muestra `AC-10` con "Aceite"

#### Scenario: Código dado de baja
- **GIVEN** el producto dado de baja `C-99`
- **WHEN** el usuario escribe `C-99` en Código
- **THEN** el modal avisa, sin impedir el envío, "Este código está dado de baja: se va a reactivar con el nombre, el stock y la categoría que indiques."
- **AND** al enviarlo con "Junta tórica" y stock 6 se ve "Producto reactivado: C-99 · Junta tórica (stock 6)."

#### Scenario: Código activo repetido
- **GIVEN** el producto activo `A-01`
- **WHEN** el usuario envía `a-01` y la API responde 409 "Ya existe un producto con código 'A-01'."
- **THEN** el modal sigue abierto con los datos y muestra ese `detail` solo en su alerta superior
- **AND** Código queda marcado `aria-invalid`, enlazado a esa alerta por `aria-describedby` (sin repetir el mensaje bajo el campo) y con el foco

#### Scenario: Campos obligatorios
- **WHEN** el usuario envía el modal con Nombre vacío y Stock vacío
- **THEN** se ve "El nombre es obligatorio." y "El stock es obligatorio." junto a cada campo y no se envía nada

### Requirement: Modal de modificar stock
El modal "Modificar stock" SHALL pedir de 1 a 100 líneas que se agregan y quitan; cada línea elige un producto, un modo ("Fijar en" o "Sumar") con su valor, opcionalmente un nombre nuevo y una Categoría (selector con "Sin categoría" y las categorías del catálogo, precargado con la categoría actual del producto elegido, también para los dados de baja). Con éxito SHALL enviar `POST /api/stock/modificaciones` con la categoría de cada línea, cerrarse, recargar el inventario y mostrar el resumen.

#### Scenario: Una línea fijando el stock
- **GIVEN** `A-01` "Tornillo M8" con stock 7
- **WHEN** el usuario elige `A-01`, deja "Fijar en" y escribe 12
- **THEN** la línea muestra "Stock actual 7 → 12" y, al guardar, la tabla muestra `A-01` con stock 12

#### Scenario: Valor propuesto al fijar
- **WHEN** el usuario elige un producto con stock 7 en modo "Fijar en"
- **THEN** el campo del valor se propone en 7, de modo que cambiar solo el nombre o la categoría no altera el stock

#### Scenario: Categoría precargada y cambiada
- **GIVEN** `F-01` con categoría `filtro` y stock 3
- **WHEN** el usuario elige `F-01`, ve Categoría en "Filtro", la cambia a "Aceite" y guarda
- **THEN** se envía la línea con `"categoria": "aceite"` y la tabla muestra `F-01` con "Aceite" y stock 3

#### Scenario: Varias líneas con modos distintos
- **WHEN** el usuario fija `A-01` en 12, suma 4 a `B-10` y renombra `C-03`
- **THEN** se envía una sola petición con las tres líneas en ese orden

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar producto" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea, y con 100 líneas "Agregar producto" queda deshabilitado

### Requirement: Resumen de la modificación
Tras una modificación exitosa, la página SHALL mostrar una alerta persistente con un ítem por línea: código, stock anterior → nuevo (o "sin cambios"), el nombre anterior → nuevo si cambió, la categoría anterior → nueva si cambió y la marca "reactivado" solo donde la respuesta trae `reactivado: true`.

#### Scenario: Resumen con reactivación
- **WHEN** la API responde con `A-01` (fijar, 7 → 12, nombre "Tornillo" → "Tornillo M8") y `C-99` (sumar, 2 → 5, `reactivado: true`)
- **THEN** la alerta dice "Stock modificado (2 productos)" y lista "A-01 · Tornillo M8: 7 → 12 · nombre antes: Tornillo" y "C-99 · Junta: 2 → 5 (+3) · reactivado"

#### Scenario: Resumen con cambio de categoría
- **WHEN** la API responde con `F-01` (fijar, 3 → 3, `categoria_anterior: "filtro"`, `categoria: "aceite"`)
- **THEN** la alerta lista "F-01 · Filtro de aceite: sin cambios · categoría: Filtro → Aceite"

### Requirement: Modal de nueva orden
El modal "Nueva orden" SHALL pedir número, fecha y entre 1 y 100 líneas de componente (producto activo y cantidad) que se agregan y quitan; con éxito SHALL enviar `POST /api/ordenes`, cerrarse, recargar el inventario y mostrar "Orden X creada." con un enlace a `/ordenes`. Cada línea SHALL permitir elegir el producto entre todos los activos o filtrarlos por categoría según "Filtro por categoría en la nueva orden" (decisión del usuario, 2026-11-24). La categoría SHALL NOT enviarse a la API ni cambiar la orden creada.

#### Scenario: Orden creada
- **GIVEN** `A-01` con stock 5 y `B-02` con stock 5
- **WHEN** el usuario crea la orden `OT-0001` con fecha `2026-11-20`, `A-01` x 2 y `B-02` x 1
- **THEN** el modal se cierra, la tabla muestra `A-01` con 3 y `B-02` con 4 y se ve "Orden OT-0001 creada."

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar componente" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea
- **AND** con 100 líneas el botón "Agregar componente" queda deshabilitado

#### Scenario: Fecha propuesta
- **WHEN** se abre el modal
- **THEN** la fecha propuesta es la fecha local de hoy en formato `AAAA-MM-DD` y se puede cambiar

### Requirement: Pantalla de reportes
`/reportes` SHALL mostrar el título "Reportes" y el reporte "Productos usados en órdenes" con los filtros "Desde (obligatorio)", "Hasta (opcional)" (ayuda "Vacío = hoy") y Producto (opcional), y el botón "Generar"; SHALL NOT ofrecer filtro de categoría. El resultado SHALL ser una tabla con las columnas Código, Nombre, Categoría, Cantidad y Órdenes, en el orden de la API, y una línea de resumen (decidido por el usuario al aprobar mockups, 2026-11-24; columna Categoría decidida por el usuario, 2026-11-24). La columna Categoría SHALL mostrar el nombre de la categoría (de `GET /api/categorias`) o "Sin categoría" atenuado; si el catálogo no se puede cargar, la clave.

#### Scenario: Generar con un rango
- **WHEN** el usuario completa Desde `2026-10-01`, Hasta `2026-10-31` y pulsa "Generar"
- **THEN** la interfaz llama a `GET /api/reportes/productos-en-ordenes?desde=2026-10-01&hasta=2026-10-31`, sin `codigo`, y muestra una fila por producto con su categoría, su cantidad total y sus órdenes

#### Scenario: Columna de categoría
- **GIVEN** un reporte con `F-01` (categoría `filtro`) y `A-01` (sin categoría)
- **WHEN** se muestra la tabla
- **THEN** las columnas son Código, Nombre, Categoría, Cantidad y Órdenes, la fila de `F-01` muestra "Filtro" y la de `A-01` "Sin categoría"

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

### Requirement: Exportar el reporte a PDF
`/reportes` SHALL tener un botón "Exportar PDF" que exporta, según `exportacion-pdf`, solo la tabla del último reporte generado (columnas Código, Nombre, Categoría, Cantidad y Órdenes, con "dado de baja" y "Sin categoría" en texto), sin los filtros. El botón SHALL estar deshabilitado antes de la primera generación, mientras se genera, ante un error o con el reporte vacío.

#### Scenario: Exportar sin filtros en el papel
- **GIVEN** un reporte generado con 5 productos
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** se abre el diálogo de impresión y el documento no muestra los filtros, la navegación ni los botones

#### Scenario: Categoría en el papel
- **GIVEN** un reporte generado con `F-01` (Filtro) y `A-01` (sin categoría)
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento tiene la columna Categoría con "Filtro" y "Sin categoría"

#### Scenario: Reporte vacío
- **WHEN** el reporte generado no tiene filas
- **THEN** "Exportar PDF" está deshabilitado

## ADDED Requirements

### Requirement: Filtro por categoría del inventario
El filtro "Categoría" de `/inventario` SHALL ofrecer "Todas las categorías" (por defecto), cada categoría de `GET /api/categorias` por su nombre y "Sin categoría", y SHALL mostrar, sin llamar a la API, solo los productos activos de la categoría elegida (o sin categoría). Se SHALL combinar con el buscador: una fila se ve solo si cumple ambos criterios. Las filas visibles SHALL conservar el orden de la API.

#### Scenario: Filtrar por una categoría
- **GIVEN** `A-01` (sin categoría), `AC-10` y `AC-20` (`aceite`) y `F-01` (`filtro`)
- **WHEN** el usuario elige "Aceite"
- **THEN** la tabla muestra `AC-10` y luego `AC-20`
- **AND** no se envía ninguna petición a la API

#### Scenario: Sin categoría
- **WHEN** el usuario elige "Sin categoría"
- **THEN** la tabla muestra solo `A-01`

#### Scenario: Combinado con la búsqueda
- **GIVEN** `AC-10` "Aceite 10W40" y `AC-20` "Aceite 20W50" (`aceite`) y `F-01` "Filtro de aceite" (`filtro`)
- **WHEN** el usuario escribe `aceite` y elige "Filtro"
- **THEN** la tabla muestra solo `F-01`

#### Scenario: Volver a todas
- **GIVEN** el filtro en "Aceite"
- **WHEN** el usuario elige "Todas las categorías"
- **THEN** la tabla muestra todos los productos que coinciden con la búsqueda escrita

### Requirement: Filtro por categoría en la nueva orden
Cada línea de componente de "Nueva orden" SHALL tener, antes del producto, un selector de categoría ("Todas" por defecto, cada categoría y "Sin categoría") que limita los productos activos ofrecidos en esa línea. Al cambiar la categoría, el producto elegido SHALL conservarse si pertenece a ella y, si no, la línea SHALL volver a "Elegí un producto…". El filtro de una línea SHALL NOT afectar a las demás.

#### Scenario: Elegir entre todos
- **GIVEN** `A-01` (sin categoría), `AC-10` (`aceite`) y `F-01` (`filtro`)
- **WHEN** el usuario abre el modal y despliega el producto de la línea 1
- **THEN** la categoría de la línea está en "Todas" y el selector ofrece `A-01`, `AC-10` y `F-01`

#### Scenario: Filtrar una línea por categoría
- **WHEN** el usuario elige "Filtro" en la categoría de la línea 2
- **THEN** el selector de producto de la línea 2 ofrece solo `F-01` y el de la línea 1 sigue ofreciendo todos

#### Scenario: Cambiar la categoría con un producto elegido
- **GIVEN** la línea 1 con `AC-10` elegido y la categoría en "Todas"
- **WHEN** el usuario elige "Aceite" y luego "Filtro" en la categoría de esa línea
- **THEN** con "Aceite" `AC-10` sigue elegido y con "Filtro" la línea vuelve a "Elegí un producto…"

#### Scenario: Categoría sin productos activos
- **GIVEN** ningún producto activo de la categoría `motor`
- **WHEN** el usuario elige "Motor" en la categoría de una línea
- **THEN** el selector de producto de esa línea ofrece solo "Elegí un producto…" y una ayuda "No hay productos en esta categoría."
