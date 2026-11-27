# Spec Delta — ordenes-trabajo

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Borrado de orden con su servicio general
Borrar una orden, con o sin reintegro, SHALL eliminar también su servicio general registrado y sus chequeos, sin modificar el catálogo de servicios generales ni el servicio de otras órdenes.

#### Scenario: Servicio eliminado con la orden
- **GIVEN** las órdenes `OT-0001` y `OT-0002`, ambas con el servicio "Servicio 20 hs"
- **WHEN** se borra `OT-0001` con `reintegrar=true`
- **THEN** no queda servicio ni chequeos de `OT-0001`, `OT-0002` conserva "Servicio 20 hs" con sus chequeos y el catálogo sigue incluyendo `servicio-20-hs`
