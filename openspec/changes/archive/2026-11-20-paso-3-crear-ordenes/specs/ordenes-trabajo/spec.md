# Spec Delta — ordenes-trabajo

## Purpose

Permite a un usuario autenticado registrar órdenes de trabajo con número único, fecha manual y componentes, descontando de forma atómica el stock de todos los componentes o rechazando la orden completa sin modificar nada.

## ADDED Requirements

### Requirement: Alta de orden con descuento de stock
Una orden válida SHALL crearse con su número, su fecha, el usuario de la sesión y una línea por producto, y SHALL descontar del stock de cada producto la cantidad de su línea.

#### Scenario: Orden con dos componentes
- **GIVEN** los productos activos `A-01` con stock 5 y `B-02` con stock 10
- **WHEN** el usuario `admin` crea la orden `OT-0001` con fecha `2026-11-20` y componentes `A-01` x 2 y `B-02` x 10
- **THEN** la orden `OT-0001` existe con fecha `2026-11-20`, usuario `admin` y las líneas `A-01` x 2 y `B-02` x 10
- **AND** el stock de `A-01` es 3 y el de `B-02` es 0
- **AND** `B-02` sigue activo y visible en el inventario con stock 0

#### Scenario: Orden con un solo componente
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea la orden `OT-0002` con el componente `A-01` x 5
- **THEN** la orden existe con una sola línea y el stock de `A-01` es 0

### Requirement: Número de orden único y normalizado
El número de orden SHALL ser un texto obligatorio que se recorta y se pasa a MAYÚSCULAS antes de validar, de 1 a 30 caracteres, único entre todas las órdenes. Un número ya usado SHALL rechazarse sin modificar datos.

#### Scenario: Número normalizado
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con número `"  ot-0003 "` y el componente `A-01` x 1
- **THEN** la orden se guarda con número `OT-0003`

#### Scenario: Número duplicado
- **GIVEN** la orden `OT-0001` existente y el producto activo `A-01` con stock 5
- **WHEN** se intenta crear otra orden con número `ot-0001` y el componente `A-01` x 1
- **THEN** se rechaza con el mensaje "Ya existe una orden con número 'OT-0001'."
- **AND** el stock de `A-01` sigue en 5 y existe una sola orden `OT-0001`

#### Scenario: Número vacío o demasiado largo
- **WHEN** se intenta crear una orden con número `"   "` o con un número de 31 caracteres
- **THEN** se rechaza con "El campo numero es obligatorio." o "El campo numero admite hasta 30 caracteres." respectivamente, sin modificar datos

### Requirement: Fecha de la orden ingresada a mano
La fecha de la orden SHALL ser obligatoria, con formato `YYYY-MM-DD` y una fecha real del calendario; se acepta cualquier fecha real, pasada o futura. Una fecha inválida SHALL rechazarse sin modificar datos.

#### Scenario: Fecha pasada aceptada
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con fecha `2025-01-15` y el componente `A-01` x 1
- **THEN** la orden se guarda con fecha `2025-01-15`

#### Scenario: Formato inválido
- **WHEN** se intenta crear una orden con fecha `20/11/2026` o `2026-11-20T10:00`
- **THEN** se rechaza con el mensaje "La fecha debe tener formato AAAA-MM-DD." sin modificar datos

#### Scenario: Fecha inexistente
- **WHEN** se intenta crear una orden con fecha `2026-02-30`
- **THEN** se rechaza con el mensaje "La fecha (2026-02-30) no es una fecha válida." sin modificar datos

#### Scenario: Fecha faltante
- **WHEN** se intenta crear una orden sin fecha o con fecha vacía
- **THEN** se rechaza con el mensaje "El campo fecha es obligatorio."

### Requirement: Componentes obligatorios y válidos
Una orden SHALL tener entre 1 y 100 líneas de componentes; cada línea SHALL tener un código (normalizado con recorte y MAYÚSCULAS, máximo 50) y una cantidad entera de 1 a 10.000. Un error en una línea SHALL informarse con el número de línea (desde 1) y sin modificar datos.

#### Scenario: Sin componentes
- **WHEN** se intenta crear una orden con la lista de componentes vacía
- **THEN** se rechaza con el mensaje "La orden requiere al menos un componente." sin modificar datos

#### Scenario: Demasiadas líneas
- **WHEN** se intenta crear una orden con 101 líneas de componentes
- **THEN** se rechaza con el mensaje "La orden admite hasta 100 componentes."

#### Scenario: Cantidad inválida en una línea
- **GIVEN** los productos activos `A-01` con stock 5 y `B-02` con stock 10
- **WHEN** se intenta crear una orden con `A-01` x 1 y `B-02` x 0
- **THEN** se rechaza con el mensaje "Componente 2: La cantidad debe ser un entero entre 1 y 10.000."
- **AND** el stock de `A-01` sigue en 5 y el de `B-02` en 10

#### Scenario: Código en minúsculas
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con el componente `" a-01 "` x 2
- **THEN** la orden tiene la línea `A-01` x 2 y el stock de `A-01` es 3

### Requirement: Solo productos activos existentes
Cada componente SHALL referirse a un producto existente y activo. Si uno o más no cumplen, la orden SHALL rechazarse completa informando todos esos códigos, sin modificar datos.

#### Scenario: Un producto inexistente
- **GIVEN** el producto activo `A-01` con stock 5 y ningún producto `X-00`
- **WHEN** se intenta crear una orden con `A-01` x 1 y `X-00` x 1
- **THEN** se rechaza con el mensaje "No existe un producto activo con código 'X-00'."
- **AND** el stock de `A-01` sigue en 5 y no se crea la orden

#### Scenario: Varios productos inexistentes o inactivos
- **GIVEN** ningún producto `X-00` y el producto inactivo `C-99` con stock 4
- **WHEN** se intenta crear una orden con `X-00` x 1 y `C-99` x 1
- **THEN** se rechaza con el mensaje "No existen productos activos con código: 'X-00', 'C-99'."
- **AND** `C-99` sigue inactivo con stock 4

### Requirement: Consolidación de líneas repetidas
Las líneas con el mismo código normalizado SHALL sumarse en una sola línea antes de validar el stock. El máximo de 10.000 aplica a cada línea, no al total consolidado: el total por producto solo SHALL estar limitado por el stock disponible.

#### Scenario: Producto repetido
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 2 y `a-01` x 1
- **THEN** la orden tiene una sola línea `A-01` x 3 y el stock de `A-01` es 2

#### Scenario: Repetido que en total excede el stock
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta crear una orden con `A-01` x 3 y `A-01` x 3
- **THEN** se rechaza por stock insuficiente informando `A-01` con disponible 5 y solicitado 6

#### Scenario: Total consolidado por encima de 10.000 con stock suficiente
- **GIVEN** el producto activo `A-01` con stock 12000
- **WHEN** se crea una orden con `A-01` x 6000 y `A-01` x 6000
- **THEN** la orden se crea con una sola línea `A-01` x 12000 y el stock de `A-01` es 0

#### Scenario: Total consolidado por encima de 10.000 sin stock suficiente
- **GIVEN** el producto activo `A-01` con stock 11000
- **WHEN** se intenta crear una orden con `A-01` x 6000 y `A-01` x 6000
- **THEN** se rechaza por stock insuficiente informando `A-01` con disponible 11000 y solicitado 12000
- **AND** el stock de `A-01` sigue en 11000 y no existe la orden

### Requirement: Rechazo completo por stock insuficiente
Si el stock de uno o más componentes no alcanza, la orden SHALL rechazarse completa, sin descontar stock de ningún producto, informando cada faltante con su código, el stock disponible y la cantidad solicitada, en el orden en que aparecen en la orden.

#### Scenario: Un componente no alcanza
- **GIVEN** los productos activos `A-01` con stock 5 y `B-02` con stock 1
- **WHEN** se intenta crear una orden con `A-01` x 2 y `B-02` x 3
- **THEN** se rechaza informando el faltante `B-02` (disponible 1, solicitado 3)
- **AND** el stock de `A-01` sigue en 5, el de `B-02` en 1 y no existe la orden

#### Scenario: Varios componentes no alcanzan
- **GIVEN** los productos activos `A-01` con stock 1, `B-02` con stock 0 y `D-04` con stock 9
- **WHEN** se intenta crear una orden con `A-01` x 2, `D-04` x 1 y `B-02` x 1
- **THEN** se rechaza informando, en este orden, `A-01` (disponible 1, solicitado 2) y `B-02` (disponible 0, solicitado 1)
- **AND** ningún stock cambia

### Requirement: Orden de prioridad de los rechazos
Si una orden tiene varios problemas, SHALL informarse uno solo, con esta prioridad: datos inválidos; número duplicado; productos inexistentes o inactivos; stock insuficiente.

#### Scenario: Duplicado y stock insuficiente
- **GIVEN** la orden `OT-0001` existente y el producto activo `A-01` con stock 1
- **WHEN** se intenta crear la orden `OT-0001` con `A-01` x 5
- **THEN** se rechaza por número duplicado

#### Scenario: Producto inexistente y stock insuficiente
- **GIVEN** el producto activo `A-01` con stock 1 y ningún producto `X-00`
- **WHEN** se intenta crear una orden con `A-01` x 5 y `X-00` x 1
- **THEN** se rechaza por producto inexistente (`X-00`)

### Requirement: Orden, líneas y stock atómicos
La creación de la orden, de sus líneas y los descuentos de stock SHALL ser una única operación todo o nada: ante cualquier falla SHALL no quedar la orden, ninguna línea ni ningún descuento. Dos altas simultáneas SHALL comportarse como si se ejecutaran una después de la otra.

#### Scenario: Falla durante la escritura
- **GIVEN** los productos activos `A-01` con stock 5 y `B-02` con stock 10
- **WHEN** la creación de una orden con `A-01` x 2 y `B-02` x 3 falla después de haber descontado parte del stock (por ejemplo, el usuario de la orden no existe)
- **THEN** no existe la orden ni sus líneas, el stock de `A-01` sigue en 5 y el de `B-02` en 10

#### Scenario: Órdenes simultáneas sobre el mismo stock
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** dos usuarios crean al mismo tiempo órdenes distintas con `A-01` x 3 cada una
- **THEN** exactamente una se crea y la otra se rechaza por stock insuficiente
- **AND** el stock final de `A-01` es 2 y existe una sola orden

#### Scenario: Mismo número simultáneo
- **GIVEN** el producto activo `A-01` con stock 10
- **WHEN** dos usuarios crean al mismo tiempo la orden `OT-0009` con `A-01` x 1
- **THEN** exactamente una se crea y la otra se rechaza por número duplicado
- **AND** el stock final de `A-01` es 9

### Requirement: Descuentos por orden fuera de la bitácora
Los descuentos de stock generados por una orden SHALL quedar fuera de la bitácora de movimientos (sin filas nuevas); quedan reflejados en las líneas de la orden.

#### Scenario: Orden sin movimientos
- **GIVEN** el producto activo `A-01` con stock 5 y la bitácora de movimientos vacía
- **WHEN** se crea una orden con `A-01` x 2
- **THEN** la bitácora de movimientos sigue vacía
