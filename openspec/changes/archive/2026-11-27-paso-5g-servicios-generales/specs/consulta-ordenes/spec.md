# Spec Delta — consulta-ordenes

## MODIFIED Requirements

### Requirement: Datos de cada orden
Cada orden consultada SHALL incluir su identificador, su número, su fecha, el nombre de usuario que la cargó, sus componentes, cada uno con código, nombre y cantidad, ordenados por código, sus procesos, cada uno con el nombre registrado al crearla y si fue personalizado, en el orden de carga (lista vacía si no tiene), y su servicio general, con el nombre y los chequeos registrados al crearla en su orden (ninguno si no tiene).

#### Scenario: Orden completa
- **GIVEN** que `admin` creó la orden `OT-0001` con fecha `2026-11-20` y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2
- **WHEN** se consultan las órdenes
- **THEN** la orden tiene un identificador entero, número `OT-0001`, fecha `2026-11-20`, usuario `admin` y componentes `A-01` "Tornillo" x 2 seguido de `B-02` "Tuerca" x 5

#### Scenario: Orden con procesos
- **GIVEN** la orden `OT-0002` creada con el proceso `limpieza` y el personalizado "Pulido"
- **WHEN** se consultan las órdenes
- **THEN** `OT-0002` tiene los procesos "Limpieza" (no personalizado) y "Pulido" (personalizado), en ese orden

#### Scenario: Orden anterior a los procesos
- **GIVEN** la orden `OT-0001` creada antes de existir los procesos
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` tiene una lista de procesos vacía

#### Scenario: Orden con servicio general
- **GIVEN** la orden `OT-0003` creada con el servicio `servicio-20-hs`
- **WHEN** se consultan las órdenes
- **THEN** `OT-0003` tiene el servicio general "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", en ese orden

#### Scenario: Orden sin servicio general
- **GIVEN** la orden `OT-0001` creada sin servicio general o antes de existir los servicios generales
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` no tiene servicio general

#### Scenario: Servicio general con varios componentes y procesos
- **GIVEN** la orden `OT-0004` con dos componentes, dos procesos y el servicio "Servicio 20 hs"
- **WHEN** se consultan las órdenes
- **THEN** `OT-0004` aparece una sola vez con sus dos componentes, sus dos procesos y su servicio con tres chequeos, sin repetir ninguno
