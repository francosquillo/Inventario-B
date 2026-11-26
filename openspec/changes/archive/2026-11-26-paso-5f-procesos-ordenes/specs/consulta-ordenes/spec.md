# Spec Delta

## MODIFIED Requirements

### Requirement: Datos de cada orden
Cada orden consultada SHALL incluir su identificador, su número, su fecha, el nombre de usuario que la cargó, sus componentes, cada uno con código, nombre y cantidad, ordenados por código, y sus procesos, cada uno con el nombre registrado al crearla y si fue personalizado, en el orden de carga (lista vacía si no tiene).

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
