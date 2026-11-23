## MODIFIED Requirements

### Requirement: Creación del esquema al primer arranque
Al iniciar sobre una base vacía, el sistema SHALL crear las tablas `usuarios`, `productos`, `ordenes`, `orden_items` y `movimientos`, con sus claves primarias, claves foráneas, restricciones de unicidad y restricciones CHECK definidas en el modelo de datos.

#### Scenario: Base nueva
- **WHEN** el sistema se inicializa sobre una base sin tablas
- **THEN** existen las cinco tablas `usuarios`, `productos`, `ordenes`, `orden_items` y `movimientos`

#### Scenario: Unicidad de código de producto
- **GIVEN** una base inicializada con un producto de código `P-001`
- **WHEN** se intenta guardar otro producto con código `P-001`
- **THEN** la base rechaza la escritura

#### Scenario: Stock negativo rechazado
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un producto con stock `-1`
- **THEN** la base rechaza la escritura

#### Scenario: Cantidad no positiva en ítem de orden o movimiento
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un ítem de orden o un movimiento con cantidad `0`
- **THEN** la base rechaza la escritura

#### Scenario: Tipo de movimiento inválido
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un movimiento con tipo distinto de `ingreso`, `egreso` o `ajuste`
- **THEN** la base rechaza la escritura

#### Scenario: Ajuste coherente
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un `ajuste` sin stock anterior o sin stock nuevo, con ambos iguales, con alguno negativo o con una cantidad distinta de su diferencia absoluta, o un `ingreso`/`egreso` con stock anterior o nuevo
- **THEN** la base rechaza la escritura

#### Scenario: Integridad referencial activa
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un movimiento que referencia un producto inexistente
- **THEN** la base rechaza la escritura

## ADDED Requirements

### Requirement: Migración de la bitácora al tipo ajuste
Al inicializar una base cuya tabla `movimientos` no admite el tipo `ajuste`, el sistema SHALL migrarla al esquema vigente en una sola transacción, conservando todas las filas con su id, fecha, producto, tipo, cantidad y usuario. La migración SHALL ser idempotente y, si falla, la base SHALL quedar como estaba.

#### Scenario: Base anterior al cambio
- **GIVEN** una base con el esquema anterior y tres movimientos (dos ingresos y un egreso)
- **WHEN** se inicializa la base
- **THEN** `movimientos` admite el tipo `ajuste` y conserva los tres movimientos con los mismos ids y datos
- **AND** el stock de los productos no cambia

#### Scenario: Inicialización repetida
- **GIVEN** una base ya migrada
- **WHEN** se inicializa la base dos veces más
- **THEN** la tabla y sus filas no cambian y no hay error

#### Scenario: Falla a mitad de la migración
- **GIVEN** una base con el esquema anterior
- **WHEN** la migración falla después de copiar las filas
- **THEN** la tabla `movimientos` sigue con el esquema anterior y todas sus filas, y el arranque informa el error
