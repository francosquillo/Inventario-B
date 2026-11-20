# Spec Delta — ordenes-trabajo

## ADDED Requirements

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
El reintegro de stock, la reactivación de productos y la eliminación de la orden y sus líneas SHALL ser una única operación todo o nada: ante cualquier falla no SHALL quedar ningún reintegro, reactivación ni eliminación parcial.

#### Scenario: Falla a mitad del reintegro
- **GIVEN** los productos `A-01` con stock 3 y `B-02` con stock 0, y la orden `OT-0001` con `A-01` x 2 y `B-02` x 5
- **WHEN** el borrado con `reintegrar=true` falla después de haber reintegrado `A-01` y antes de reintegrar `B-02`
- **THEN** la orden `OT-0001` sigue existiendo con sus dos líneas
- **AND** el stock de `A-01` sigue en 3 y el de `B-02` en 0

#### Scenario: Producto de una línea ausente
- **GIVEN** la orden `OT-0001` con `A-01` x 2 y `B-02` x 5, cuyo producto `B-02` ya no existe en la base por una manipulación externa
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** el borrado falla sin borrar la orden y el stock de `A-01` no cambia

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
Un borrado exitoso SHALL informar la orden eliminada tal como estaba (id, número, fecha, usuario y componentes) y si se reintegró. Con reintegro SHALL informar, por cada componente, la cantidad devuelta, el stock resultante y si el producto se reactivó; sin reintegro, ningún reintegro.

#### Scenario: Resultado con reintegro
- **GIVEN** `A-01` activo con stock 3, `C-99` dado de baja con stock 1 y la orden `OT-0001` con `A-01` x 2 y `C-99` x 4
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** el resultado incluye la orden `OT-0001` con sus dos componentes y `reintegrado` verdadero
- **AND** informa `A-01` con 2 devueltas, stock 5 y no reactivado, y `C-99` con 4 devueltas, stock 5 y reactivado, ordenados por código

#### Scenario: Resultado sin reintegro
- **GIVEN** la orden `OT-0001` con `A-01` x 2
- **WHEN** se borra `OT-0001` con `reintegrar=false`
- **THEN** el resultado incluye la orden `OT-0001`, `reintegrado` falso y una lista de reintegros vacía
