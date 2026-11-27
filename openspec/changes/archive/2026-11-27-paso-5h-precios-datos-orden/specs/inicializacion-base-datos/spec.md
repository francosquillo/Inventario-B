# Spec Delta — inicializacion-base-datos

## ADDED Requirements

### Requirement: Incorporación de datos y precios de órdenes
Al inicializar una base nueva o una existente sin las columnas de datos y precios de órdenes, el sistema SHALL agregar las que falten en una sola transacción, sin modificar ninguna fila; las órdenes existentes SHALL quedar sin datos del cliente, sin fechas de ingreso y egreso y sin precios, con su fecha intacta. Si falla, ninguna columna nueva SHALL quedar y el arranque SHALL informar el error.

#### Scenario: Base de C-06g
- **GIVEN** una base con el esquema anterior a los precios, dos órdenes con componentes, procesos y servicio general, productos con categoría y movimientos
- **WHEN** se inicializa la base
- **THEN** las órdenes tienen cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso vacíos, su fecha no cambia, y sus componentes, procesos y servicios no tienen precio
- **AND** la cantidad y el contenido previo de órdenes, componentes, procesos, servicios, chequeos, productos, categorías y movimientos no cambian

#### Scenario: Arranques repetidos
- **GIVEN** una base ya migrada con una orden con cliente y precios
- **WHEN** se inicializa la base tres veces
- **THEN** no se agrega ni cambia nada y la orden conserva su cliente y sus precios

#### Scenario: Base nueva
- **WHEN** se inicializa una base vacía
- **THEN** se puede crear una orden con cliente, celular, casco, motor, trailer, fechas de ingreso y egreso y precios

#### Scenario: Restricciones en la base
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar directamente un precio negativo o no entero, un cliente vacío o de 81 caracteres, o una fecha de egreso anterior a la de ingreso
- **THEN** la base lo rechaza

#### Scenario: Falla al agregar columnas
- **GIVEN** una base con el esquema anterior a los precios
- **WHEN** falla el agregado de una de las columnas
- **THEN** no queda ninguna columna nueva, los datos existentes no cambian y el arranque informa el error
