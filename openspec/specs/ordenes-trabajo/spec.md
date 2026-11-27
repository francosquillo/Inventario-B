# ordenes-trabajo Specification

## Purpose
Permite a un usuario autenticado registrar órdenes de trabajo con número único, fecha manual y componentes, descontando de forma atómica el stock de todos los componentes o rechazando la orden completa sin modificar nada.

## Requirements

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
Si una orden tiene varios problemas, SHALL informarse uno solo, con esta prioridad: datos inválidos; número duplicado; productos inexistentes o inactivos; stock insuficiente. Dentro de datos inválidos SHALL ganar el primero de: número, fecha, fecha de ingreso, fecha de egreso, cliente, celular, casco, motor, trailer, componentes (con sus precios), servicio general, precio del servicio, procesos y personalizados (con sus precios).

#### Scenario: Duplicado y stock insuficiente
- **GIVEN** la orden `OT-0001` existente y el producto activo `A-01` con stock 1
- **WHEN** se intenta crear la orden `OT-0001` con `A-01` x 5
- **THEN** se rechaza por número duplicado

#### Scenario: Producto inexistente y stock insuficiente
- **GIVEN** el producto activo `A-01` con stock 1 y ningún producto `X-00`
- **WHEN** se intenta crear una orden con `A-01` x 5 y `X-00` x 1
- **THEN** se rechaza por producto inexistente (`X-00`)

#### Scenario: Cliente largo y componentes vacíos
- **WHEN** se intenta crear una orden con un cliente de 81 caracteres y componentes vacíos
- **THEN** se rechaza con "El cliente admite hasta 80 caracteres."

#### Scenario: Egreso anterior y cliente largo
- **WHEN** se intenta crear una orden con fecha de ingreso `2026-11-27`, fecha de egreso `2026-11-20` y un cliente de 81 caracteres
- **THEN** se rechaza con "La fecha de egreso no puede ser anterior a la de ingreso."

#### Scenario: Fecha inválida y fecha de ingreso inválida
- **WHEN** se intenta crear una orden con fecha `2026-02-30` y fecha de ingreso `30/11/2026`
- **THEN** se rechaza con "La fecha (2026-02-30) no es una fecha válida."

#### Scenario: Precio de componente inválido y servicio inexistente
- **WHEN** se intenta crear una orden con un componente de precio `-1` y el servicio `servicio-500-hs`, que no existe
- **THEN** se rechaza con "Componente 1: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

#### Scenario: Precio inválido y número duplicado
- **GIVEN** la orden `OT-0001` existente
- **WHEN** se intenta crear la orden `OT-0001` con un proceso de precio `-1`
- **THEN** se rechaza por el precio inválido, no por número duplicado

### Requirement: Orden, líneas y stock atómicos
La creación de la orden, de sus líneas, de sus procesos, de su servicio general con sus chequeos y los descuentos de stock SHALL ser una única operación todo o nada: ante cualquier falla SHALL no quedar la orden, ninguna línea, ningún proceso, ningún servicio ni chequeo ni ningún descuento. Dos altas simultáneas SHALL comportarse como si se ejecutaran una después de la otra.

#### Scenario: Falla durante la escritura
- **GIVEN** los productos activos `A-01` con stock 5 y `B-02` con stock 10
- **WHEN** la creación de una orden con `A-01` x 2 y `B-02` x 3 falla después de haber descontado parte del stock (por ejemplo, el usuario de la orden no existe)
- **THEN** no existe la orden ni sus líneas, el stock de `A-01` sigue en 5 y el de `B-02` en 10

#### Scenario: Falla al guardar los procesos
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** la creación de una orden con `A-01` x 2 y el proceso "Limpieza" falla al guardar el proceso, después de descontar el stock
- **THEN** no existe la orden, ni sus líneas, ni ningún proceso, y el stock de `A-01` sigue en 5

#### Scenario: Falla al guardar el servicio general
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** la creación de una orden con `A-01` x 2 y el servicio "Servicio 20 hs" falla al guardar uno de sus chequeos, después de descontar el stock
- **THEN** no existe la orden, ni sus líneas, ni su servicio, ni ningún chequeo, y el stock de `A-01` sigue en 5

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

### Requirement: Decisión de reintegro explícita
Todo borrado de orden SHALL indicar explícitamente si se reintegra el stock, con uno de los dos valores `true` o `false` y sin valor por defecto. Si falta la decisión, viene vacía o tiene otro valor, el borrado SHALL rechazarse con un mensaje claro sin borrar la orden ni modificar el stock.

#### Scenario: Decisión ausente
- **GIVEN** la orden `OT-0001` con `A-01` x 2
- **WHEN** se pide borrarla sin indicar si se reintegra
- **THEN** el borrado se rechaza con "El campo reintegrar es obligatorio."
- **AND** la orden `OT-0001` sigue existiendo con sus líneas y el stock no cambia

#### Scenario: Decisión vacía
- **GIVEN** la orden `OT-0001`
- **WHEN** se pide borrarla con `reintegrar` vacío
- **THEN** el borrado se rechaza con "El campo reintegrar es obligatorio." y la orden sigue existiendo

#### Scenario: Valor no admitido
- **GIVEN** la orden `OT-0001`
- **WHEN** se pide borrarla con `reintegrar` igual a `si`, `1` o `TRUE`
- **THEN** cada pedido se rechaza con "El campo reintegrar debe ser true o false." y la orden sigue existiendo

### Requirement: Borrado de orden con reintegro
Un borrado con `reintegrar=true` SHALL sumar al stock de cada producto la cantidad de su línea en la orden y SHALL eliminar la orden y todas sus líneas.

#### Scenario: Reintegro de varios componentes
- **GIVEN** los productos activos `A-01` con stock 3 y `B-02` con stock 0, y la orden `OT-0001` con `A-01` x 2 y `B-02` x 5
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** el stock de `A-01` es 5 y el de `B-02` es 5
- **AND** no existe la orden `OT-0001` ni ninguna de sus líneas

#### Scenario: Otras órdenes intactas
- **GIVEN** las órdenes `OT-0001` y `OT-0002`, ambas con `A-01`
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** `OT-0002` sigue existiendo con sus líneas sin cambios
- **AND** solo se reintegra la cantidad de la línea de `OT-0001`

### Requirement: Reintegro reactiva productos dados de baja
Al reintegrar, un producto de la orden que esté dado de baja SHALL reactivarse y recibir las unidades devueltas, sumadas al stock que conservaba. Un borrado sin reintegro SHALL dejar los productos dados de baja como estaban.

#### Scenario: Reactivación por reintegro
- **GIVEN** la orden `OT-0001` con `C-99` "Arandela" x 4 y el producto `C-99` dado de baja con stock 1
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** `C-99` queda activo con stock 5 y nombre "Arandela"
- **AND** `C-99` vuelve a aparecer en el inventario general

#### Scenario: Sin reintegro no reactiva
- **GIVEN** la orden `OT-0001` con `C-99` x 4 y el producto `C-99` dado de baja con stock 1
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** `C-99` sigue dado de baja con stock 1

### Requirement: Borrado de orden sin reintegro
Un borrado con `reintegrar=false` SHALL eliminar la orden y todas sus líneas sin modificar el stock ni el estado de ningún producto.

#### Scenario: Borrado sin devolver stock
- **GIVEN** el producto activo `A-01` con stock 3 y la orden `OT-0001` con `A-01` x 2
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** no existe la orden `OT-0001` ni sus líneas
- **AND** el stock de `A-01` sigue en 3

### Requirement: Borrado de orden por número
El borrado de una orden SHALL identificarla por su número, normalizado igual que en el alta y el filtro (recorte de espacios y MAYÚSCULAS). Un número en blanco o de más de 30 caracteres SHALL rechazarse con un mensaje claro, antes de consultar si la orden existe, sin modificar ningún dato.

#### Scenario: Número normalizado
- **GIVEN** la orden `OT-0001` con `A-01` x 2 y `A-01` con stock 3
- **WHEN** se pide borrar `  ot-0001 ` con `reintegrar=true`
- **THEN** se borra la orden `OT-0001` y el stock de `A-01` es 5

#### Scenario: Número con barra
- **GIVEN** la orden `OT/2026/01`
- **WHEN** se pide borrar `OT/2026/01` con `reintegrar=false`
- **THEN** la orden `OT/2026/01` queda borrada

#### Scenario: Número en blanco
- **GIVEN** la orden `OT-0001`
- **WHEN** se pide borrar la orden con número vacío o solo espacios
- **THEN** el borrado se rechaza con "El campo numero es obligatorio." y la orden `OT-0001` sigue existiendo

#### Scenario: Número demasiado largo
- **GIVEN** la orden `OT-0001`
- **WHEN** se pide borrar una orden cuyo número tiene 31 caracteres
- **THEN** el borrado se rechaza con "El campo numero admite hasta 30 caracteres." y los datos no cambian

### Requirement: Borrado de orden inexistente
Un borrado de una orden cuyo número no existe SHALL rechazarse con "No existe una orden con número 'X'." (X normalizado, el mismo mensaje de la consulta por número) sin modificar ningún dato, después de validar la decisión de reintegro y el número.

#### Scenario: Número inexistente
- **GIVEN** que no existe ninguna orden con número `OT-0999`
- **WHEN** se pide borrar `ot-0999` con `reintegrar=true`
- **THEN** el borrado se rechaza con "No existe una orden con número 'OT-0999'." y el stock no cambia

#### Scenario: Validación antes que existencia
- **GIVEN** que no existe ninguna orden con número `OT-0999`
- **WHEN** se pide borrar `OT-0999` sin indicar `reintegrar`
- **THEN** el borrado se rechaza con "El campo reintegrar es obligatorio."

#### Scenario: Orden ya borrada
- **GIVEN** la orden `OT-0001`, ya borrada
- **WHEN** se pide borrar `OT-0001` otra vez con `reintegrar=true`
- **THEN** el borrado se rechaza con "No existe una orden con número 'OT-0001'." y no se reintegra stock otra vez

### Requirement: Borrado de orden atómico
El reintegro de stock, la reactivación de productos y la eliminación de la orden, sus líneas, sus procesos y su servicio general con sus chequeos SHALL ser una única operación todo o nada: ante cualquier falla no SHALL quedar ningún reintegro, reactivación ni eliminación parcial.

#### Scenario: Falla a mitad del reintegro
- **GIVEN** los productos `A-01` con stock 3 y `B-02` con stock 0, y la orden `OT-0001` con `A-01` x 2 y `B-02` x 5
- **WHEN** el borrado con `reintegrar=true` falla después de haber reintegrado `A-01` y antes de reintegrar `B-02`
- **THEN** la orden `OT-0001` sigue existiendo con sus dos líneas
- **AND** el stock de `A-01` sigue en 3 y el de `B-02` en 0

#### Scenario: Producto de una línea ausente
- **GIVEN** la orden `OT-0001` con `A-01` x 2 y `B-02` x 5, cuyo producto `B-02` ya no existe en la base por una manipulación externa
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** el borrado falla sin borrar la orden y el stock de `A-01` no cambia

#### Scenario: Falla con procesos
- **GIVEN** la orden `OT-0001` con `A-01` x 2 y los procesos "Limpieza" y "Pulido"
- **WHEN** el borrado falla después de eliminar los procesos y antes de eliminar la orden
- **THEN** `OT-0001` sigue existiendo con su línea y sus dos procesos, y el stock no cambia

#### Scenario: Falla con servicio general
- **GIVEN** la orden `OT-0001` con `A-01` x 2 y el servicio "Servicio 20 hs" con sus tres chequeos
- **WHEN** el borrado falla después de eliminar el servicio y antes de eliminar la orden
- **THEN** `OT-0001` sigue existiendo con su línea y su servicio con los tres chequeos, y el stock no cambia

### Requirement: Borrados simultáneos de una orden
Dos borrados simultáneos de la misma orden SHALL comportarse como si se ejecutaran uno después del otro: exactamente uno la borra y el otro se rechaza por orden inexistente, y el stock se reintegra a lo sumo una vez.

#### Scenario: Doble borrado con reintegro
- **GIVEN** el producto `A-01` con stock 3 y la orden `OT-0001` con `A-01` x 2
- **WHEN** dos usuarios borran al mismo tiempo `OT-0001` con `reintegrar=true`
- **THEN** exactamente un borrado se completa y el otro se rechaza con "No existe una orden con número 'OT-0001'."
- **AND** el stock final de `A-01` es 5

### Requirement: Reintegro fuera de la bitácora
El borrado de una orden, con o sin reintegro, SHALL no agregar filas a la bitácora de movimientos ni modificar las existentes.

#### Scenario: Borrado sin movimientos
- **GIVEN** el producto `A-01` con un movimiento de ingreso registrado y la orden `OT-0001` con `A-01` x 2
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** la bitácora de movimientos sigue con ese único movimiento, sin cambios

### Requirement: Resultado del borrado de orden
Un borrado exitoso SHALL informar la orden eliminada tal como estaba (id, número, fecha, usuario, componentes, procesos y servicio general) y si se reintegró. Con reintegro SHALL informar, por cada componente, la cantidad devuelta, el stock resultante y si el producto se reactivó; sin reintegro, ningún reintegro.

#### Scenario: Resultado con reintegro
- **GIVEN** `A-01` activo con stock 3, `C-99` dado de baja con stock 1 y la orden `OT-0001` con `A-01` x 2 y `C-99` x 4
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** el resultado incluye la orden `OT-0001` con sus dos componentes y `reintegrado` verdadero
- **AND** informa `A-01` con 2 devueltas, stock 5 y no reactivado, y `C-99` con 4 devueltas, stock 5 y reactivado, ordenados por código

#### Scenario: Resultado sin reintegro
- **GIVEN** la orden `OT-0001` con `A-01` x 2
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** el resultado incluye la orden `OT-0001`, `reintegrado` falso y una lista de reintegros vacía

#### Scenario: Resultado con procesos
- **GIVEN** la orden `OT-0001` con el proceso "Cambio motor" y el personalizado "Pulido"
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** la orden informada incluye los procesos "Cambio motor" (no personalizado) y "Pulido" (personalizado)

#### Scenario: Resultado con servicio general
- **GIVEN** la orden `OT-0001` con el servicio "Servicio 20 hs" y sus tres chequeos
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** la orden informada incluye el servicio "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico"

### Requirement: Borrado de orden con sus procesos
Borrar una orden, con o sin reintegro, SHALL eliminar también todos sus procesos registrados, sin modificar el catálogo de procesos ni los procesos de otras órdenes.

#### Scenario: Procesos eliminados con la orden
- **GIVEN** las órdenes `OT-0001` y `OT-0002`, ambas con el proceso "Limpieza", y `OT-0001` con el personalizado "Pulido"
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** no queda ningún proceso de `OT-0001`, `OT-0002` conserva "Limpieza" y el catálogo sigue incluyendo `limpieza`

### Requirement: Borrado de orden con su servicio general
Borrar una orden, con o sin reintegro, SHALL eliminar también su servicio general registrado y sus chequeos, sin modificar el catálogo de servicios generales ni el servicio de otras órdenes.

#### Scenario: Servicio eliminado con la orden
- **GIVEN** las órdenes `OT-0001` y `OT-0002`, ambas con el servicio "Servicio 20 hs"
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** no queda servicio ni chequeos de `OT-0001`, `OT-0002` conserva "Servicio 20 hs" con sus chequeos y el catálogo sigue incluyendo `servicio-20-hs`
