## ADDED Requirements

### Requirement: Chequeo final de cada orden
Además de lo indicado en "Datos de cada orden" y "Datos del cliente y precios de cada orden", cada orden consultada SHALL incluir su chequeo final: la lista de ítems marcados, cada uno con su clave, su nombre y su precio (vacío si no lo tiene), en el orden fijo de `chequeo-final-ordenes`; lista vacía si no tiene ninguno. Las órdenes editadas SHALL mostrarse con su contenido vigente.

#### Scenario: Orden con chequeo
- **GIVEN** la orden `OT-0043` con el chequeo "Combustible" a 800000 y "Entrega" sin precio
- **WHEN** se consultan las órdenes
- **THEN** `OT-0043` tiene chequeo final `combustible` "Combustible" con precio 800000 y `entrega` "Entrega" sin precio

#### Scenario: Orden anterior al chequeo
- **GIVEN** la orden `OT-0001` creada antes de existir el chequeo final
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` tiene el chequeo final vacío

#### Scenario: Orden editada
- **GIVEN** la orden `OT-0043` del 2026-11-27 editada a fecha `2026-11-28` y `A-01` x 3
- **WHEN** se consultan las órdenes con el filtro desde `2026-11-28`
- **THEN** aparece `OT-0043` con fecha `2026-11-28` y `A-01` x 3
