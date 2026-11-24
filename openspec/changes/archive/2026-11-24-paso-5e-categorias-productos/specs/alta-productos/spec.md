## MODIFIED Requirements

### Requirement: Alta de producto con código, nombre y stock
El alta SHALL recibir código, nombre y stock inicial, los tres obligatorios, y opcionalmente una categoría del catálogo; SHALL crear un producto activo con el código normalizado (recorte + MAYÚSCULAS, hasta 50 caracteres), el nombre recortado (1 a 120 caracteres), ese stock y la categoría indicada (normalizada según `categorias-productos`) o ninguna si no se indica.

#### Scenario: Alta con stock
- **GIVEN** que no existe ningún producto con código `N-01`
- **WHEN** se da de alta `N-01` "Arandela 6mm" con stock 10
- **THEN** existe el producto activo `N-01` "Arandela 6mm" con stock 10, sin categoría, y aparece en el inventario general

#### Scenario: Alta con categoría
- **GIVEN** que no existe ningún producto con código `AC-10`
- **WHEN** se da de alta `AC-10` "Aceite 10W40" con stock 4 y categoría `aceite`
- **THEN** existe el producto activo `AC-10` con stock 4 y categoría `aceite`

#### Scenario: Código y nombre normalizados
- **GIVEN** que no existe ningún producto `RD-6204`
- **WHEN** se da de alta `"  rd-6204 "` con el nombre `"  Rodamiento 6204  "` y stock 4
- **THEN** existe el producto activo `RD-6204` "Rodamiento 6204" con stock 4

#### Scenario: Falta un dato obligatorio
- **WHEN** se intenta dar de alta un producto sin código, sin nombre (o con nombre de solo espacios) o sin stock
- **THEN** el alta se rechaza con un mensaje que nombra el campo y no se crea ningún producto ni movimiento

#### Scenario: Categoría inexistente
- **WHEN** se intenta dar de alta `N-06` "Bujía" con stock 2 y categoría `encendido`
- **THEN** el alta se rechaza con "La categoría 'encendido' no existe." y no se crea ningún producto ni movimiento

### Requirement: Alta de un código dado de baja lo reactiva
El alta con el código de un producto dado de baja SHALL reactivarlo, reemplazar su nombre por el nuevo, su stock conservado por el stock indicado y su categoría por la indicada (o ninguna si no se indica), sin crear otro producto, e informar que fue reactivado. La categoría SHALL NOT influir en si el alta se acepta, reactiva o rechaza.

#### Scenario: Reactivación con datos nuevos
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se da de alta `C-99` "Junta tórica" con stock 6
- **THEN** `C-99` queda activo con nombre "Junta tórica" y stock 6, sigue existiendo un único `C-99` y el resultado indica que fue reactivado

#### Scenario: Reactivación con stock cero
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se da de alta `C-99` "Junta" con stock 0
- **THEN** `C-99` queda activo con stock 0 y figura sin stock en el inventario

#### Scenario: Reactivación reemplaza la categoría
- **GIVEN** el producto inactivo `C-99` "Junta" con categoría `motor`
- **WHEN** se da de alta `C-99` "Junta" con stock 1 y categoría `filtro`, o sin categoría
- **THEN** `C-99` queda activo con categoría `filtro`, o sin categoría, respectivamente
