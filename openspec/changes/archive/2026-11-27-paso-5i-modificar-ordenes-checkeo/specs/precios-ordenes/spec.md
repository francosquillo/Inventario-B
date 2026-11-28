## MODIFIED Requirements

### Requirement: Subtotales y total de la orden
Cada orden SHALL tener, calculados y no guardados (pedido del usuario, 2026-11-27): "Subtotal servicios" = precio del servicio general + suma de los precios de sus servicios adicionales + suma de los precios de los ítems marcados de su chequeo final (C-06i); "Subtotal ítems" = suma de los precios de sus ítems; "Total" = subtotal servicios + subtotal ítems. Un precio vacío SHALL contar como 0; sin ningún precio los tres valen 0.

#### Scenario: Todos los precios cargados
- **GIVEN** una orden con servicio general a 4500000, servicios adicionales a 1500000 y 800000, e ítems a 1200000 y 350000
- **WHEN** se consulta la orden
- **THEN** el subtotal de servicios es 6800000, el de ítems 1550000 y el total 8350000

#### Scenario: Algunos precios vacíos
- **GIVEN** una orden con servicio general sin precio, un servicio adicional a 1500000 y otro sin precio, y los ítems a 1200000 y sin precio
- **WHEN** se consulta la orden
- **THEN** el subtotal de servicios es 1500000, el de ítems 1200000 y el total 2700000

#### Scenario: Orden sin servicio ni procesos
- **GIVEN** una orden sin servicio general ni procesos y un ítem a 99999999999
- **WHEN** se consulta la orden
- **THEN** el subtotal de servicios es 0, el de ítems 99999999999 y el total 99999999999

#### Scenario: Orden sin ningún precio
- **GIVEN** una orden creada antes de existir los precios
- **WHEN** se consulta la orden
- **THEN** el subtotal de servicios, el de ítems y el total valen 0

#### Scenario: Chequeo final con precios
- **GIVEN** una orden con servicio general a 4500000, un servicio adicional a 1500000, el chequeo "Combustible" a 800000 y "Entrega" sin precio, y un ítem a 1200000
- **WHEN** se consulta la orden
- **THEN** el subtotal de servicios es 6800000, el de ítems 1200000 y el total 8000000
