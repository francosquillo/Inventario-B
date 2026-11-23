## MODIFIED Requirements

### Requirement: Datos de cada movimiento
Cada movimiento consultado SHALL incluir su fecha (hora local de Argentina con offset), el código y el nombre del producto, el tipo (`ingreso`, `egreso` o `ajuste`), la cantidad, el nombre de usuario que lo registró y, solo para los movimientos `ajuste`, el stock anterior y el stock nuevo (vacíos en `ingreso` y `egreso`).

#### Scenario: Movimiento completo
- **GIVEN** que el usuario `admin` ingresó 3 unidades del producto `A-01` "Tornillo M4" el `2026-11-19T15:30:00-03:00`
- **WHEN** se consultan los movimientos
- **THEN** el movimiento tiene fecha `2026-11-19T15:30:00-03:00`, código `A-01`, nombre "Tornillo M4", tipo `ingreso`, cantidad 3 y usuario `admin`
- **AND** no tiene stock anterior ni stock nuevo

#### Scenario: Movimiento de ajuste
- **GIVEN** que el usuario `admin` fijó el stock de `A-01` de 7 en 4
- **WHEN** se consultan los movimientos
- **THEN** el movimiento tiene tipo `ajuste`, cantidad 3, stock anterior 7, stock nuevo 4 y usuario `admin`

#### Scenario: Movimientos anteriores a la migración
- **GIVEN** una base creada antes de existir el tipo `ajuste`, con un egreso de 2 unidades de `A-01`
- **WHEN** se inicializa la base y se consultan los movimientos
- **THEN** el egreso sigue con su fecha, tipo `egreso` y cantidad 2, sin stock anterior ni stock nuevo
