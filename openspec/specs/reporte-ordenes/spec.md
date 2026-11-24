# reporte-ordenes Specification

## Purpose
Define el reporte de productos usados en órdenes de trabajo dentro de un rango de fechas: un total por producto, con filtro opcional por un solo producto, para saber cuánto se consumió de cada pieza en un período.

## Requirements

### Requirement: Totales por producto en un rango de fechas
El reporte SHALL devolver, para un rango de fechas `desde`..`hasta` **inclusivo** sobre la fecha de la orden, una fila por cada producto que aparece en al menos una orden del rango, con su código, su nombre, si está activo, la suma de las cantidades de ese producto en esas órdenes y la cantidad de órdenes del rango en que aparece. Los productos que no aparecen en ninguna orden del rango SHALL NOT figurar.

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

### Requirement: Orden del reporte
Las filas SHALL ordenarse por cantidad total de mayor a menor y, ante igual cantidad, por código ascendente.

#### Scenario: Mayor consumo primero
- **GIVEN** en el rango `B-02` suma 9, `A-01` suma 5 y `C-03` suma 5
- **WHEN** se consulta el reporte
- **THEN** el orden es `B-02`, `A-01`, `C-03`

### Requirement: Incluye productos dados de baja
El reporte SHALL incluir los productos dados de baja que aparecen en órdenes del rango, con su código y nombre registrados e indicando que están inactivos.

#### Scenario: Producto dado de baja con consumo
- **GIVEN** la orden `OT-0003` del 2026-11-12 con `C-99` x 2, y `C-99` dado de baja después
- **WHEN** se consulta del 2026-11-01 al 2026-11-30
- **THEN** `C-99` figura con cantidad 2, en 1 orden, marcado como inactivo

### Requirement: Filtro por un producto
El reporte SHALL aceptar opcionalmente un código de producto, normalizado igual que en ingresos y movimientos (recorte de espacios y MAYÚSCULAS), y devolver solo la fila de ese producto. Un código vacío o de solo espacios SHALL tratarse como ausencia de filtro. Un código inexistente, o sin uso en órdenes del rango, SHALL devolver un resultado vacío.

#### Scenario: Solo el producto elegido
- **GIVEN** en el rango `A-01` suma 5 y `B-02` suma 1
- **WHEN** se consulta el reporte con el código ` a-01 `
- **THEN** el resultado es solo `A-01` con cantidad 5

#### Scenario: Filtro por un producto dado de baja
- **GIVEN** `C-99` dado de baja se usó x 2 en una orden del 2026-11-12 y x 3 en otra del 2026-12-02
- **WHEN** se consulta del 2026-11-01 al 2026-11-30 con el código `C-99`
- **THEN** el resultado es solo `C-99` con cantidad 2 en 1 orden, marcado como inactivo

#### Scenario: Producto sin uso en el rango
- **GIVEN** `B-02` existe pero no aparece en órdenes del rango
- **WHEN** se consulta con el código `B-02`
- **THEN** el resultado es vacío

#### Scenario: Código inexistente
- **WHEN** se consulta con el código `ZZ-99`, que no existe
- **THEN** el resultado es vacío, sin error

#### Scenario: Código en blanco
- **WHEN** se consulta con el código `"   "`
- **THEN** el resultado es el mismo que sin filtro de producto

### Requirement: Validación de las fechas del reporte
`desde` SHALL ser obligatorio y, como `hasta` cuando viene, tener formato `AAAA-MM-DD` y ser una fecha de calendario real; `desde` SHALL NOT ser posterior al `hasta` efectivo. Ante un `desde` faltante o vacío, una fecha mal formada o inexistente o un rango invertido, la consulta SHALL rechazarse con un mensaje en español y sin resultado. No SHALL haber un límite máximo de extensión del rango.

#### Scenario: Falta desde
- **WHEN** se consulta sin `desde` (o con `desde` vacío)
- **THEN** la consulta se rechaza con "La fecha 'desde' es obligatoria."

#### Scenario: Formato inválido
- **WHEN** se consulta con `desde` `01/11/2026`
- **THEN** la consulta se rechaza con "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Fecha inexistente
- **WHEN** se consulta con `hasta` `2026-02-30`
- **THEN** la consulta se rechaza con "La fecha 'hasta' (2026-02-30) no es una fecha válida."

#### Scenario: Rango invertido
- **WHEN** se consulta con `desde` `2026-11-30` y `hasta` `2026-11-01`
- **THEN** la consulta se rechaza con "La fecha 'desde' (2026-11-30) no puede ser posterior a 'hasta' (2026-11-01)."

#### Scenario: Rango de varios años
- **WHEN** se consulta del 2020-01-01 al 2026-12-31
- **THEN** la consulta se acepta y devuelve los totales de todo ese período

### Requirement: Hasta opcional
`hasta` SHALL ser opcional (decisión del usuario, 2026-11-24): ausente o vacío SHALL tomarse como la fecha de hoy en la hora local de Argentina (UTC-03:00), que pasa a ser el `hasta` efectivo para el filtro y para la validación del rango.

#### Scenario: Hasta vacío significa hoy
- **GIVEN** la fecha local de Argentina es 2026-11-24 y hay órdenes del 2026-11-03 y del 2026-11-24 que usan `A-01` x 1 cada una
- **WHEN** se consulta con `desde` `2026-11-01` y sin `hasta`
- **THEN** el resultado es el mismo que del 2026-11-01 al 2026-11-24: `A-01` con cantidad 2 en 2 órdenes

#### Scenario: Desde futuro sin hasta
- **GIVEN** la fecha local de Argentina es 2026-11-24
- **WHEN** se consulta con `desde` `2026-12-01` y sin `hasta`
- **THEN** la consulta se rechaza con "La fecha 'desde' (2026-12-01) no puede ser posterior a 'hasta' (2026-11-24)."

### Requirement: Productos usados en órdenes
La consulta de productos usados SHALL devolver, sin filtro de fechas, cada producto que aparece en al menos una orden registrada (de cualquier fecha), una sola vez, con su código, su nombre y si está activo, ordenados por código. Los productos que nunca se usaron en una orden SHALL NOT figurar; sin órdenes SHALL devolver una lista vacía. La consulta SHALL NOT modificar datos.

#### Scenario: Activos y dados de baja usados
- **GIVEN** `A-01` activo usado en dos órdenes, `C-99` dado de baja usado en una orden y `B-02` activo que nunca se usó
- **WHEN** se consultan los productos usados
- **THEN** el resultado es `A-01` (activo) y `C-99` (inactivo), en ese orden, cada uno una sola vez, y no incluye `B-02`

#### Scenario: Sin órdenes
- **GIVEN** no hay órdenes registradas
- **WHEN** se consultan los productos usados
- **THEN** el resultado es una lista vacía

#### Scenario: Producto de una orden borrada
- **GIVEN** `D-04` solo se usó en una orden que luego se borró
- **WHEN** se consultan los productos usados
- **THEN** `D-04` no figura

### Requirement: Reporte sin resultados
Si ninguna orden del rango tiene componentes (o no hay órdenes en el rango), el reporte SHALL devolver una lista vacía.

#### Scenario: Período sin órdenes
- **GIVEN** no hay órdenes entre el 2026-10-01 y el 2026-10-31
- **WHEN** se consulta ese rango
- **THEN** el resultado es una lista vacía

### Requirement: Reporte de solo lectura
Consultar el reporte SHALL NOT modificar productos, stock, órdenes ni movimientos.

#### Scenario: Sin efectos
- **GIVEN** un estado de productos, órdenes y movimientos
- **WHEN** se consulta el reporte cualquier cantidad de veces
- **THEN** productos, stock, órdenes y movimientos quedan idénticos
