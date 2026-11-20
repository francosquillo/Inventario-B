# Spec Delta — baja-productos

## Purpose

Permite a un usuario autenticado dar de baja (borrado lógico) un producto que ya no se usa, para que deje de figurar en el inventario y en las nuevas órdenes, conservando su stock, su historial de movimientos y las órdenes en las que aparece.

## ADDED Requirements

### Requirement: Baja lógica de un producto activo
La baja de un producto activo, identificado por su código normalizado (recorte + MAYÚSCULAS), SHALL marcarlo como inactivo y conservar su código, nombre y stock sin cambios. El producto no SHALL eliminarse de la base.

#### Scenario: Baja con stock
- **GIVEN** el producto activo `A-01` "Tornillo M4" con stock 7
- **WHEN** se da de baja el producto `A-01`
- **THEN** `A-01` queda inactivo con nombre "Tornillo M4" y stock 7
- **AND** sigue existiendo un único producto con código `A-01`

#### Scenario: Baja con stock cero
- **GIVEN** el producto activo `B-10` con stock 0
- **WHEN** se da de baja el producto `B-10`
- **THEN** `B-10` queda inactivo con stock 0

#### Scenario: Código normalizado
- **GIVEN** el producto activo `A-01`
- **WHEN** se da de baja el producto `"  a-01 "`
- **THEN** `A-01` queda inactivo

### Requirement: Efectos de la baja sobre el inventario y las órdenes
Un producto dado de baja SHALL desaparecer del inventario general y no SHALL poder usarse como componente de una orden nueva ni en un egreso manual, mientras que las órdenes existentes SHALL seguir mostrándolo con su código, nombre y cantidad.

#### Scenario: Fuera del inventario
- **GIVEN** los productos activos `A-01` y `B-02`
- **WHEN** se da de baja `A-01`
- **THEN** el inventario general lista solo `B-02`

#### Scenario: No seleccionable en una orden nueva
- **GIVEN** el producto `A-01` dado de baja con stock 7
- **WHEN** se crea una orden con `A-01` x 1
- **THEN** la orden se rechaza indicando que no existe un producto activo con código `A-01`

#### Scenario: Egreso rechazado
- **GIVEN** el producto `A-01` dado de baja con stock 7
- **WHEN** se egresa 1 unidad de `A-01`
- **THEN** el egreso se rechaza y el stock sigue en 7

#### Scenario: Órdenes históricas intactas
- **GIVEN** la orden `OT-0001` con `A-01` "Tornillo M4" x 2
- **WHEN** se da de baja `A-01`
- **THEN** el listado de órdenes sigue mostrando en `OT-0001` el componente `A-01` "Tornillo M4" x 2

### Requirement: Baja sin movimientos
La baja de un producto SHALL no agregar filas a la bitácora de movimientos, y los movimientos previos del producto SHALL seguir consultables.

#### Scenario: Historial conservado
- **GIVEN** el producto activo `A-01` con un ingreso de 5 registrado en la bitácora
- **WHEN** se da de baja `A-01`
- **THEN** la bitácora sigue con ese único movimiento y la consulta de movimientos de `A-01` lo devuelve

### Requirement: Reactivación posterior conserva el stock
Un ingreso posterior con el código de un producto dado de baja SHALL reactivarlo y sumar la cantidad al stock que conservaba al darse de baja.

#### Scenario: Baja y reingreso
- **GIVEN** el producto activo `A-01` con stock 7
- **WHEN** se da de baja `A-01` y luego se ingresan 3 unidades con el código `A-01`
- **THEN** `A-01` queda activo con stock 10 y vuelve a aparecer en el inventario general

### Requirement: Baja de un producto inexistente o ya inactivo
La baja de un código que no corresponde a un producto activo (inexistente o ya dado de baja) SHALL rechazarse con "No existe un producto activo con código 'X'." (X normalizado) sin modificar ningún dato. Un código vacío o de más de 50 caracteres SHALL rechazarse con los mensajes de validación de código existentes.

#### Scenario: Código inexistente
- **GIVEN** que no existe ningún producto con código `Z-99`
- **WHEN** se da de baja el producto `z-99`
- **THEN** la baja se rechaza con "No existe un producto activo con código 'Z-99'."

#### Scenario: Ya dado de baja
- **GIVEN** el producto `A-01` dado de baja con stock 7
- **WHEN** se da de baja `A-01` otra vez
- **THEN** la baja se rechaza con "No existe un producto activo con código 'A-01'." y el stock sigue en 7

#### Scenario: Código demasiado largo
- **WHEN** se da de baja un código de 51 caracteres
- **THEN** la baja se rechaza con "El campo codigo admite hasta 50 caracteres."

### Requirement: Bajas simultáneas de un producto
Dos bajas simultáneas del mismo producto SHALL comportarse como si se ejecutaran una después de la otra: exactamente una se completa y la otra se rechaza por producto inexistente o inactivo.

#### Scenario: Doble baja
- **GIVEN** el producto activo `A-01`
- **WHEN** dos usuarios dan de baja `A-01` al mismo tiempo
- **THEN** exactamente una baja se completa y la otra se rechaza con "No existe un producto activo con código 'A-01'."
