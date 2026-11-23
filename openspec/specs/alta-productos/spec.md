# alta-productos Specification

## Purpose
Permite a un usuario autenticado dar de alta un producto de forma explícita, con código, nombre y stock inicial (que puede ser 0), sin duplicar productos activos y recuperando con datos nuevos los productos dados de baja.

## Requirements

### Requirement: Alta de producto con código, nombre y stock
El alta SHALL recibir código, nombre y stock inicial, los tres obligatorios, y crear un producto activo con el código normalizado (recorte + MAYÚSCULAS, hasta 50 caracteres), el nombre recortado (1 a 120 caracteres) y ese stock.

#### Scenario: Alta con stock
- **GIVEN** que no existe ningún producto con código `N-01`
- **WHEN** se da de alta `N-01` "Arandela 6mm" con stock 10
- **THEN** existe el producto activo `N-01` "Arandela 6mm" con stock 10 y aparece en el inventario general

#### Scenario: Código y nombre normalizados
- **GIVEN** que no existe ningún producto `RD-6204`
- **WHEN** se da de alta `"  rd-6204 "` con el nombre `"  Rodamiento 6204  "` y stock 4
- **THEN** existe el producto activo `RD-6204` "Rodamiento 6204" con stock 4

#### Scenario: Falta un dato obligatorio
- **WHEN** se intenta dar de alta un producto sin código, sin nombre (o con nombre de solo espacios) o sin stock
- **THEN** el alta se rechaza con un mensaje que nombra el campo y no se crea ningún producto ni movimiento

### Requirement: Stock inicial entero de 0 a 10.000
El stock inicial del alta SHALL ser un entero de 0 a 10.000; cualquier otro valor SHALL rechazarse con el mensaje "El stock debe ser un entero entre 0 y 10.000." sin modificar datos. Esta excepción a "cantidad > 0" rige solo para el stock inicial del alta y el stock fijado por un ajuste.

#### Scenario: Alta con stock cero
- **GIVEN** que no existe ningún producto con código `N-02`
- **WHEN** se da de alta `N-02` "Buje" con stock 0
- **THEN** existe el producto activo `N-02` con stock 0, figura sin stock en el inventario y no se registró ningún movimiento

#### Scenario: Stock fuera de rango o no entero
- **WHEN** se intenta dar de alta un producto con stock -1, 10.001, 2.5 o el texto `"5"`
- **THEN** el alta se rechaza con "El stock debe ser un entero entre 0 y 10.000." y no se crea el producto

#### Scenario: Stock máximo
- **WHEN** se da de alta `N-03` "Junta" con stock 10.000
- **THEN** existe el producto activo `N-03` con stock 10.000

### Requirement: Código de un producto activo repetido
El alta con el código de un producto activo SHALL rechazarse con el mensaje "Ya existe un producto con código 'X'." (X = código normalizado), sin cambiar su nombre ni su stock ni registrar movimientos.

#### Scenario: Código activo
- **GIVEN** el producto activo `A-01` "Tornillo M4" con stock 5
- **WHEN** se intenta dar de alta `a-01` "Otro" con stock 3
- **THEN** el alta se rechaza con "Ya existe un producto con código 'A-01'."
- **AND** `A-01` sigue "Tornillo M4" con stock 5 y no hay movimiento nuevo

#### Scenario: Altas simultáneas del mismo código
- **GIVEN** que no existe ningún producto `N-04`
- **WHEN** dos altas de `N-04` se procesan a la vez
- **THEN** exactamente una crea el producto y la otra se rechaza con "Ya existe un producto con código 'N-04'."

### Requirement: Alta de un código dado de baja lo reactiva
El alta con el código de un producto dado de baja SHALL reactivarlo, reemplazar su nombre por el nuevo y su stock conservado por el stock indicado, sin crear otro producto, e informar que fue reactivado.

#### Scenario: Reactivación con datos nuevos
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se da de alta `C-99` "Junta tórica" con stock 6
- **THEN** `C-99` queda activo con nombre "Junta tórica" y stock 6, sigue existiendo un único `C-99` y el resultado indica que fue reactivado

#### Scenario: Reactivación con stock cero
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se da de alta `C-99` "Junta" con stock 0
- **THEN** `C-99` queda activo con stock 0 y figura sin stock en el inventario

### Requirement: Movimientos del alta
El alta SHALL registrar en la bitácora, con la fecha local de Argentina y el usuario autenticado: un `ingreso` por el stock inicial si el producto es nuevo y el stock es mayor que 0; ningún movimiento si es nuevo con stock 0; un `ajuste` con stock anterior y nuevo si reactiva y el stock cambia; ninguno si reactiva con el mismo stock.

#### Scenario: Producto nuevo con stock
- **WHEN** el usuario `admin` da de alta `N-01` con stock 10
- **THEN** existe un movimiento `ingreso` de cantidad 10 de `N-01` hecho por `admin`

#### Scenario: Reactivación que cambia el stock
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** el usuario `admin` da de alta `C-99` con stock 6
- **THEN** existe un movimiento `ajuste` de `C-99` con stock anterior 2, stock nuevo 6 y cantidad 4

#### Scenario: Reactivación con el mismo stock
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se da de alta `C-99` con stock 2
- **THEN** `C-99` queda activo y no se registra ningún movimiento

### Requirement: Alta atómica
El alta o la reactivación del producto y el registro de su movimiento SHALL ocurrir como una sola operación todo o nada.

#### Scenario: Falla al registrar el movimiento
- **GIVEN** que no existe el producto `N-05`
- **WHEN** se da de alta `N-05` con stock 3 y el registro del movimiento falla
- **THEN** no existe el producto `N-05`
