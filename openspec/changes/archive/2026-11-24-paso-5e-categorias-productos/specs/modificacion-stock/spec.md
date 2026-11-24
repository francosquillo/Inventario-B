## MODIFIED Requirements

### Requirement: Modificación en lote
Una modificación SHALL recibir de 1 a 100 líneas; cada línea indica el código de un producto existente (activo o dado de baja), un modo (`fijar` o `sumar`) con su valor y, opcionalmente, un nombre nuevo y una categoría nueva. Cada línea SHALL aplicarse a su producto y el resultado SHALL listar las líneas en el orden recibido, cada una con su categoría resultante y la anterior.

#### Scenario: Varias líneas
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se modifica `A-01` fijando 12 y `B-10` sumando 4
- **THEN** `A-01` queda con stock 12 y `B-10` con stock 4, y el resultado lista `A-01` y luego `B-10`

#### Scenario: Sin líneas o demasiadas
- **WHEN** se envía una modificación sin líneas o con 101 líneas
- **THEN** se rechaza con "La modificación requiere al menos una línea." o "La modificación admite hasta 100 líneas." y no cambia ningún dato

### Requirement: Modificación reactiva productos dados de baja
Una línea aceptada sobre un producto dado de baja SHALL reactivarlo únicamente si su stock cambia efectivamente (`fijar` en un valor distinto del actual, o `sumar`) y el stock resultante es mayor que 0; en ese caso el resultado SHALL indicar `reactivado: true`. En cualquier otro caso (fijar en 0, fijar el mismo stock, o solo cambiar el nombre o la categoría) el producto SHALL seguir dado de baja, con el stock, el nombre y la categoría que resulten de la línea, y el resultado SHALL indicar `reactivado: false`.

#### Scenario: Sumar a un producto dado de baja
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se suma 3 a `C-99`
- **THEN** `C-99` queda activo con stock 5, aparece en el inventario y el resultado indica que fue reactivado

#### Scenario: Fijar un valor distinto mayor que cero
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 6
- **THEN** `C-99` queda activo con stock 6, existe un movimiento `ajuste` 2 → 6 y el resultado indica que fue reactivado

#### Scenario: Fijar en cero un producto dado de baja
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 0
- **THEN** `C-99` queda con stock 0 y sigue dado de baja, existe un movimiento `ajuste` 2 → 0, no aparece en el inventario, sigue en la lista de dados de baja y el resultado indica `reactivado: false`

#### Scenario: Fijar el mismo stock en un producto dado de baja
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 2
- **THEN** `C-99` sigue dado de baja con stock 2, no hay movimiento nuevo y el resultado indica `reactivado: false`

#### Scenario: Solo cambiar el nombre de un producto dado de baja
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se fija `C-99` en 2 con el nombre "Junta tórica"
- **THEN** `C-99` sigue dado de baja con nombre "Junta tórica" y stock 2, no hay movimiento nuevo y el resultado indica `reactivado: false`

#### Scenario: Solo cambiar la categoría de un producto dado de baja
- **GIVEN** el producto inactivo `C-99` sin categoría y con stock 2
- **WHEN** se fija `C-99` en 2 con la categoría `motor`
- **THEN** `C-99` sigue dado de baja con categoría `motor` y stock 2, no hay movimiento nuevo y el resultado indica `reactivado: false`

### Requirement: Línea sin cambios
Una línea que fija el mismo stock que el producto ya tiene, sin cambiar el nombre ni la categoría, sobre un producto activo, SHALL aceptarse sin modificar el producto ni registrar movimientos, y el resultado SHALL mostrar su stock anterior igual al nuevo y su categoría anterior igual a la nueva.

#### Scenario: Mismo stock
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se fija `A-01` en 5
- **THEN** la modificación se acepta, `A-01` sigue con stock 5 y no hay movimiento nuevo

#### Scenario: Misma categoría
- **GIVEN** el producto activo `F-01` con stock 3 y categoría `filtro`
- **WHEN** se fija `F-01` en 3 con la categoría `FILTRO`
- **THEN** la modificación se acepta, `F-01` no cambia y el resultado indica categoría anterior y nueva `filtro`

### Requirement: Registro de las modificaciones en la bitácora
Cada línea aceptada SHALL registrar, con la fecha local de Argentina y el usuario autenticado: en `fijar` con stock distinto, un movimiento `ajuste` con stock anterior, stock nuevo y cantidad igual a la diferencia absoluta; en `sumar`, un movimiento `ingreso` con la cantidad sumada. Fijar el mismo stock, renombrar y cambiar la categoría no registran movimiento; la reactivación no registra movimiento por sí misma (solo el del cambio de stock que la origina).

#### Scenario: Ajuste hacia abajo
- **GIVEN** el producto activo `A-01` con stock 7 y el usuario `admin`
- **WHEN** fija `A-01` en 4
- **THEN** existe un movimiento `ajuste` de `A-01` con stock anterior 7, stock nuevo 4, cantidad 3 y usuario `admin`

#### Scenario: Suma como ingreso
- **GIVEN** el producto activo `A-01` con stock 7
- **WHEN** el usuario `admin` suma 2 a `A-01`
- **THEN** existe un movimiento `ingreso` de `A-01` con cantidad 2, sin stock anterior ni nuevo

#### Scenario: Cambio de categoría sin movimiento
- **GIVEN** el producto activo `A-01` con stock 7 y sin categoría
- **WHEN** se fija `A-01` en 7 con la categoría `motor`
- **THEN** `A-01` queda con categoría `motor` y no hay movimiento nuevo

## ADDED Requirements

### Requirement: Cambio opcional de categoría
Cada línea SHALL poder indicar la categoría: sin indicarla, no cambia; con "sin categoría", el producto queda sin categoría; con una clave (normalizada según `categorias-productos`), pasa a esa categoría. Una clave inexistente SHALL rechazar la modificación completa con "Línea N: La categoría 'x' no existe.", evaluado como validación de datos de la línea.

#### Scenario: Asignar categoría y sumar
- **GIVEN** el producto activo `AC-10` sin categoría y con stock 2
- **WHEN** se suma 3 a `AC-10` con la categoría `Aceite`
- **THEN** `AC-10` queda con stock 5 y categoría `aceite`, y el resultado indica categoría anterior vacía y nueva `aceite`

#### Scenario: Línea sin categoría indicada
- **GIVEN** el producto activo `F-01` con categoría `filtro` y stock 3
- **WHEN** se suma 1 a `F-01` sin indicar categoría
- **THEN** `F-01` conserva la categoría `filtro`

#### Scenario: Quitar la categoría
- **GIVEN** el producto activo `F-01` con categoría `filtro` y stock 3
- **WHEN** se fija `F-01` en 3 indicando "sin categoría"
- **THEN** `F-01` queda sin categoría y no hay movimiento nuevo

#### Scenario: Categoría inexistente en una línea
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 1)
- **WHEN** la línea 1 fija `A-01` en 9 y la línea 2 suma 1 a `B-10` con la categoría `frenos`
- **THEN** la modificación se rechaza con "Línea 2: La categoría 'frenos' no existe." y ni `A-01` ni `B-10` cambian
