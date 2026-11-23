## ADDED Requirements

### Requirement: Modal de nuevo ingreso
El modal "Nuevo ingreso" SHALL pedir Código, Nombre y Stock (los tres obligatorios; el stock puede ser 0), enviar `POST /api/productos` y, con éxito, cerrarse, recargar el inventario y mostrar una alerta de éxito que diga si el producto fue creado o reactivado.

#### Scenario: Producto nuevo con stock cero
- **GIVEN** ningún producto `N-01`
- **WHEN** el usuario crea `N-01` "Arandela 6mm" con stock 0
- **THEN** el modal se cierra, la tabla muestra `N-01` con stock 0 resaltado y se ve "Producto creado: N-01 · Arandela 6mm (stock 0)."

#### Scenario: Código dado de baja
- **GIVEN** el producto dado de baja `C-99`
- **WHEN** el usuario escribe `C-99` en Código
- **THEN** el modal avisa, sin impedir el envío, "Este código está dado de baja: se va a reactivar con el nombre y el stock que indiques."
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
El modal "Modificar stock" SHALL pedir de 1 a 100 líneas que se agregan y quitan; cada línea elige un producto, un modo ("Fijar en" o "Sumar") con su valor y, opcionalmente, un nombre nuevo. Con éxito SHALL enviar `POST /api/stock/modificaciones`, cerrarse, recargar el inventario y mostrar el resumen.

#### Scenario: Una línea fijando el stock
- **GIVEN** `A-01` "Tornillo M8" con stock 7
- **WHEN** el usuario elige `A-01`, deja "Fijar en" y escribe 12
- **THEN** la línea muestra "Stock actual 7 → 12" y, al guardar, la tabla muestra `A-01` con stock 12

#### Scenario: Valor propuesto al fijar
- **WHEN** el usuario elige un producto con stock 7 en modo "Fijar en"
- **THEN** el campo del valor se propone en 7, de modo que cambiar solo el nombre no altera el stock

#### Scenario: Varias líneas con modos distintos
- **WHEN** el usuario fija `A-01` en 12, suma 4 a `B-10` y renombra `C-03`
- **THEN** se envía una sola petición con las tres líneas en ese orden

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar producto" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea, y con 100 líneas "Agregar producto" queda deshabilitado

### Requirement: Selector de productos de la modificación
El selector de producto de cada línea SHALL ofrecer los productos activos (`GET /api/inventario`) y, en un grupo aparte "Dados de baja", los de `GET /api/productos/inactivos`, cada uno como "CÓDIGO · Nombre (stock N)". Un producto ya elegido en otra línea SHALL quedar deshabilitado en las demás.

#### Scenario: Producto dado de baja
- **GIVEN** el producto dado de baja `C-99` "Junta" con stock 2
- **WHEN** el usuario abre el selector y elige `C-99`
- **THEN** lo encuentra en el grupo "Dados de baja" y la línea avisa según lo que cargue: "Dado de baja: se va a reactivar al guardar." si el stock resultante cambia y queda mayor que 0 (sumar, o fijar en un valor distinto mayor que 0), o "Dado de baja: sigue dado de baja (sin cambio de stock)." / "Dado de baja: sigue dado de baja (stock 0)." si no

#### Scenario: Aviso de un dado de baja según el stock cargado
- **GIVEN** la línea 2 tiene el producto dado de baja `C-99` con stock 2 en modo "Fijar en"
- **WHEN** el usuario deja el valor en 2, lo cambia a 0 o lo cambia a 6
- **THEN** con 2 y con 0 la línea avisa que sigue dado de baja y con 6 avisa "Dado de baja: se va a reactivar al guardar."

#### Scenario: Producto ya elegido
- **GIVEN** la línea 1 tiene `A-01`
- **WHEN** el usuario abre el selector de la línea 2
- **THEN** `A-01` aparece deshabilitado

### Requirement: Resumen de la modificación
Tras una modificación exitosa, la página SHALL mostrar una alerta persistente con un ítem por línea: código, stock anterior → nuevo (o "sin cambios"), el nombre anterior → nuevo si cambió y la marca "reactivado" solo donde la respuesta trae `reactivado: true`.

#### Scenario: Resumen con reactivación
- **WHEN** la API responde con `A-01` (fijar, 7 → 12, nombre "Tornillo" → "Tornillo M8") y `C-99` (sumar, 2 → 5, `reactivado: true`)
- **THEN** la alerta dice "Stock modificado (2 productos)" y lista "A-01 · Tornillo M8: 7 → 12 · nombre antes: Tornillo" y "C-99 · Junta: 2 → 5 (+3) · reactivado"

### Requirement: Errores de la modificación por línea
Ante un 422 "Línea N: …" el modal SHALL marcar la línea N; ante un 404 SHALL marcar las líneas cuyos códigos vienen en `codigos` con "Este producto ya no existe: elegí otro o quitá la línea." y refrescar los selectores. El modal SHALL quedar abierto con los datos y el `detail` en la alerta superior.

#### Scenario: Línea inválida según la API
- **WHEN** la API responde 422 "Línea 2: El stock debe ser un entero entre 0 y 10.000."
- **THEN** se ve ese mensaje arriba y la línea 2 queda marcada como inválida

#### Scenario: Producto borrado de la base
- **WHEN** la API responde 404 con `codigos: ["Z-01"]`
- **THEN** la línea con `Z-01` muestra "Este producto ya no existe: elegí otro o quitá la línea." y los selectores se recargan

#### Scenario: Enviando
- **WHEN** el usuario pulsa "Guardar cambios"
- **THEN** el botón muestra "Guardando…" deshabilitado hasta la respuesta y se envía una sola petición

## MODIFIED Requirements

### Requirement: Tabla de inventario
`/inventario` SHALL mostrar primero la barra de acciones ("Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes") y la tabla de productos activos de `GET /api/inventario` (código, nombre, stock, acción "Eliminar") en el orden de la API, con la cantidad de productos y el stock 0 resaltado. La web SHALL NOT ofrecer los antiguos "Ingreso de stock" ni "Egreso de stock".

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

### Requirement: Inventario vacío
Si `GET /api/inventario` devuelve una lista vacía, `/inventario` SHALL mostrar el cartel "Todavía no hay productos" con la indicación de crear el primero con "Nuevo ingreso", en lugar de una tabla vacía.

#### Scenario: Sin productos
- **GIVEN** ningún producto activo
- **WHEN** se abre `/inventario`
- **THEN** se ve "Todavía no hay productos" y no se ve la tabla

### Requirement: Validación en el navegador
Antes de llamar a la API, la interfaz SHALL validar: obligatorios (tras recortar espacios), cantidad entera de 1 a 10.000, stock entero de 0 a 10.000, fecha `AAAA-MM-DD` real, Desde ≤ Hasta, número ≤ 30, código ≤ 50 y nombre ≤ 120 caracteres, y un producto por línea sin repetir; cada error SHALL mostrarse junto a su campo, marcado `aria-invalid`, sin enviar la petición.

#### Scenario: Cantidad no entera
- **WHEN** el usuario envía una línea "Sumar" con cantidad `2.5`, `0` o `10001`
- **THEN** se ve "La cantidad debe ser un entero entre 1 y 10.000." junto al campo y no se envía nada

#### Scenario: Stock fuera de rango
- **WHEN** el usuario envía un nuevo ingreso o una línea "Fijar en" con stock `-1`, `2.5` o `10001`
- **THEN** se ve "El stock debe ser un entero entre 0 y 10.000." junto al campo y no se envía nada

#### Scenario: Stock cero aceptado
- **WHEN** el usuario envía un nuevo ingreso o una línea "Fijar en" con stock `0`
- **THEN** la validación del navegador lo acepta y se envía la petición

#### Scenario: Línea sin producto
- **WHEN** el usuario envía una modificación con una línea sin producto elegido
- **THEN** se ve "Elegí un producto." en esa línea y no se envía nada

#### Scenario: Código demasiado largo
- **WHEN** el usuario envía un código de 51 caracteres
- **THEN** se ve "El código admite hasta 50 caracteres." y no se envía nada

#### Scenario: Fecha inválida
- **WHEN** el usuario envía una orden con fecha `2026-02-30`
- **THEN** se ve "La fecha debe ser una fecha real con formato AAAA-MM-DD." y no se envía nada

#### Scenario: Rango invertido
- **WHEN** el usuario filtra con Desde `2026-11-20` y Hasta `2026-11-01`
- **THEN** se ve "Desde no puede ser posterior a Hasta." y no se envía nada

#### Scenario: El backend sigue siendo la autoridad
- **WHEN** la API rechaza con 422 un dato que pasó la validación del navegador
- **THEN** se muestra el `detail` de la API tal cual

### Requirement: Modales accesibles
Cada modal SHALL tener título asociado (`aria-labelledby`), mover el foco a su primer campo al abrirse, mantener el foco dentro mientras esté abierto, cerrarse con Cancelar, la X, Escape o un clic en el fondo, y devolver el foco al control que lo abrió.

#### Scenario: Teclado
- **WHEN** el usuario abre "Nuevo ingreso" con el teclado, recorre con Tab y pulsa Escape
- **THEN** el foco empieza en Código, no sale del modal con Tab y vuelve al botón "Nuevo ingreso" al cerrar

#### Scenario: Etiquetas
- **WHEN** se inspecciona cualquier campo de la interfaz
- **THEN** tiene una etiqueta visible asociada o un `aria-label`, y los errores se anuncian con `role="alert"`

#### Scenario: Modo de cada línea
- **WHEN** se inspecciona el selector "Fijar en" / "Sumar" de una línea de "Modificar stock"
- **THEN** es un grupo de opciones con nombre accesible que incluye el número de línea y se opera con el teclado

## REMOVED Requirements

### Requirement: Modal de ingreso de stock
**Reason**: Reemplazado por "Modal de nuevo ingreso" (alta explícita con nombre y stock obligatorios) y por el modo "Sumar" de "Modal de modificar stock" (decisión del usuario, 2026-11-20).
**Migration**: Para crear o reactivar un producto, usar "Nuevo ingreso" (`POST /api/productos`); para sumar unidades, "Modificar stock" en modo "Sumar". `POST /api/stock/ingreso` sigue disponible en la API y en `/docs`.

### Requirement: Modal de egreso de stock
**Reason**: Reemplazado por "Modal de modificar stock": el usuario corrige el stock fijando el valor contado en lugar de restar (decisión del usuario, 2026-11-20).
**Migration**: Usar "Modificar stock" en modo "Fijar en" con el stock resultante. `POST /api/stock/egreso` sigue disponible en la API y en `/docs`; las órdenes siguen descontando stock como hasta ahora.
