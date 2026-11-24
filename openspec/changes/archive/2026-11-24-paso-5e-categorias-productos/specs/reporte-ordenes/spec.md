## MODIFIED Requirements

### Requirement: Totales por producto en un rango de fechas
El reporte SHALL devolver, para un rango de fechas `desde`..`hasta` **inclusivo** sobre la fecha de la orden, una fila por cada producto que aparece en al menos una orden del rango, con su código, su nombre, su categoría actual (o ninguna), si está activo, la suma de las cantidades de ese producto en esas órdenes y la cantidad de órdenes del rango en que aparece. Los productos que no aparecen en ninguna orden del rango SHALL NOT figurar. La categoría SHALL NOT filtrar ni cambiar el orden del reporte.

#### Scenario: Suma de varias órdenes
- **GIVEN** la orden `OT-0001` del 2026-11-03 con `A-01` x 3 y `B-02` x 1, y la orden `OT-0002` del 2026-11-10 con `A-01` x 2
- **WHEN** se consulta el reporte del 2026-11-01 al 2026-11-30
- **THEN** el resultado tiene `A-01` con cantidad 5 en 2 órdenes y `B-02` con cantidad 1 en 1 orden

#### Scenario: Bordes del rango incluidos
- **GIVEN** órdenes del 2026-11-01 y del 2026-11-30 que usan `A-01` x 1 cada una, y otra del 2026-12-01 con `A-01` x 7
- **WHEN** se consulta del 2026-11-01 al 2026-11-30
- **THEN** `A-01` tiene cantidad 2 en 2 órdenes

#### Scenario: Un solo día
- **GIVEN** una orden del 2026-11-15 con `B-02` x 4
- **WHEN** se consulta del 2026-11-15 al 2026-11-15
- **THEN** el resultado es solo `B-02` con cantidad 4 en 1 orden

#### Scenario: Productos sin uso no aparecen
- **GIVEN** el producto activo `C-03` que no está en ninguna orden del rango
- **WHEN** se consulta el reporte del rango
- **THEN** `C-03` no figura en el resultado

#### Scenario: Categoría de cada fila
- **GIVEN** en el rango se usaron `F-01` (categoría `filtro`) y `A-01` (sin categoría)
- **WHEN** se consulta el reporte
- **THEN** la fila de `F-01` indica la categoría `filtro` y la de `A-01` no indica categoría

#### Scenario: Categoría actual, no histórica
- **GIVEN** `F-01` se usó en una orden cuando era de `aceite` y luego se cambió a `filtro`
- **WHEN** se consulta el reporte de ese rango
- **THEN** la fila de `F-01` indica la categoría `filtro`
