# Spec Delta — consulta-ordenes

## ADDED Requirements

### Requirement: Datos del cliente y precios de cada orden
Además de lo indicado en "Datos de cada orden", cada orden consultada SHALL incluir su cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso (cada uno vacío si no lo tiene), el precio de cada componente, de cada proceso y de su servicio general (vacío si no lo tiene), y su subtotal de servicios, subtotal de ítems y total según `precios-ordenes`.

#### Scenario: Orden con datos y precios
- **GIVEN** la orden `OT-0043` creada con cliente "Juan Pérez", celular "11 5555-1234", casco "Bermuda 190", fecha `2026-11-27`, fecha de ingreso `2026-11-26`, fecha de egreso `2026-11-29`, el servicio `servicio-20-hs` a 4500000, el proceso `limpieza` a 1500000 y el componente `A-01` x 2 a 1200000
- **WHEN** se consultan las órdenes
- **THEN** `OT-0043` tiene esos datos, sin motor ni trailer, el servicio "Servicio 20 hs" con precio 4500000, "Limpieza" con precio 1500000, `A-01` x 2 con precio 1200000, subtotal de servicios 6000000, subtotal de ítems 1200000 y total 7200000

#### Scenario: Orden anterior a los precios
- **GIVEN** la orden `OT-0001` creada antes de existir los datos y precios, con un componente y un proceso
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` no tiene cliente ni otros datos nuevos, su componente y su proceso no tienen precio y sus subtotales y total valen 0

#### Scenario: Copia de los precios
- **GIVEN** la orden `OT-0043` creada con el proceso `limpieza` a 1500000
- **WHEN** se renombra `limpieza` en el catálogo y se vuelven a consultar las órdenes
- **THEN** `OT-0043` sigue teniendo "Limpieza" con precio 1500000
