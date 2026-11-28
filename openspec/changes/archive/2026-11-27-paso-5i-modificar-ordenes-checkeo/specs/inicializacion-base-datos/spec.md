## ADDED Requirements

### Requirement: Incorporación del chequeo final de órdenes
Al inicializar una base nueva o una existente sin el chequeo final, el sistema SHALL crear su tabla en una sola transacción, sin modificar ninguna fila existente; las órdenes existentes SHALL quedar sin chequeo. La base SHALL rechazar claves fuera de la lista fija, precios negativos, no enteros o mayores al tope, y un mismo ítem dos veces en una orden. Si falla, la tabla SHALL NOT quedar creada y el arranque SHALL informar el error.

#### Scenario: Base de C-06h
- **GIVEN** una base con el esquema anterior al chequeo, dos órdenes con componentes, procesos, servicio general, datos y precios, productos con categoría y movimientos
- **WHEN** se inicializa la base
- **THEN** las órdenes tienen el chequeo final vacío
- **AND** la cantidad y el contenido previo de órdenes, componentes, procesos, servicios, chequeos, productos, categorías y movimientos no cambian

#### Scenario: Arranques repetidos
- **GIVEN** una base ya migrada con una orden con chequeo final
- **WHEN** se inicializa la base tres veces
- **THEN** no se agrega ni cambia nada y la orden conserva su chequeo

#### Scenario: Base nueva
- **WHEN** se inicializa una base vacía
- **THEN** se puede crear una orden con chequeo final y precios

#### Scenario: Restricciones en la base
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar directamente un ítem de chequeo con clave `lavado`, con precio -1, 1.5 o 100000000000, o el mismo ítem dos veces en una orden
- **THEN** la base lo rechaza

#### Scenario: Falla al crear la tabla
- **GIVEN** una base con el esquema anterior al chequeo
- **WHEN** falla la creación de la tabla del chequeo
- **THEN** la tabla no queda creada, los datos existentes no cambian y el arranque informa el error
