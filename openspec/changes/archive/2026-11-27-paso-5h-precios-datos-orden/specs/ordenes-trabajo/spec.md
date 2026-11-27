# Spec Delta — ordenes-trabajo

## MODIFIED Requirements

### Requirement: Orden de prioridad de los rechazos
Si una orden tiene varios problemas, SHALL informarse uno solo, con esta prioridad: datos inválidos; número duplicado; productos inexistentes o inactivos; stock insuficiente. Dentro de datos inválidos SHALL ganar el primero de: número, fecha, fecha de ingreso, fecha de egreso, cliente, celular, casco, motor, trailer, componentes (con sus precios), servicio general, precio del servicio, procesos y personalizados (con sus precios).

#### Scenario: Duplicado y stock insuficiente
- **GIVEN** la orden `OT-0001` existente y el producto activo `A-01` con stock 1
- **WHEN** se intenta crear la orden `OT-0001` con `A-01` x 5
- **THEN** se rechaza por número duplicado

#### Scenario: Producto inexistente y stock insuficiente
- **GIVEN** el producto activo `A-01` con stock 1 y ningún producto `X-00`
- **WHEN** se intenta crear una orden con `A-01` x 5 y `X-00` x 1
- **THEN** se rechaza por producto inexistente (`X-00`)

#### Scenario: Cliente largo y componentes vacíos
- **WHEN** se intenta crear una orden con un cliente de 81 caracteres y componentes vacíos
- **THEN** se rechaza con "El cliente admite hasta 80 caracteres."

#### Scenario: Egreso anterior y cliente largo
- **WHEN** se intenta crear una orden con fecha de ingreso `2026-11-27`, fecha de egreso `2026-11-20` y un cliente de 81 caracteres
- **THEN** se rechaza con "La fecha de egreso no puede ser anterior a la de ingreso."

#### Scenario: Fecha inválida y fecha de ingreso inválida
- **WHEN** se intenta crear una orden con fecha `2026-02-30` y fecha de ingreso `30/11/2026`
- **THEN** se rechaza con "La fecha (2026-02-30) no es una fecha válida."

#### Scenario: Precio de componente inválido y servicio inexistente
- **WHEN** se intenta crear una orden con un componente de precio `-1` y el servicio `servicio-500-hs`, que no existe
- **THEN** se rechaza con "Componente 1: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

#### Scenario: Precio inválido y número duplicado
- **GIVEN** la orden `OT-0001` existente
- **WHEN** se intenta crear la orden `OT-0001` con un proceso de precio `-1`
- **THEN** se rechaza por el precio inválido, no por número duplicado
