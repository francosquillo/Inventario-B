# chequeo-final-ordenes Specification

## Purpose

Registra en cada orden de trabajo el chequeo final de la embarcación antes de entregarla, con una lista fija de ítems que se marcan y un precio opcional por ítem que se le cobra al cliente.

## ADDED Requirements

### Requirement: Lista fija de ítems de chequeo final
El chequeo final SHALL tener exactamente seis ítems, en este orden y con estas claves y nombres: `combustible` "Combustible", `puesta-en-marcha` "Puesta en marcha", `check-list-y-verificacion-final` "Check-list y verificación final", `prueba-en-el-lago` "Prueba en el lago", `limpieza-de-cortesia` "Limpieza de cortesía" y `entrega` "Entrega". La lista SHALL NOT poder modificarse desde la aplicación ni por API.

#### Scenario: Ítems disponibles
- **WHEN** se consulta qué ítems de chequeo final admite una orden
- **THEN** son Combustible, Puesta en marcha, Check-list y verificación final, Prueba en el lago, Limpieza de cortesía y Entrega, en ese orden

#### Scenario: Clave inexistente
- **GIVEN** una orden válida
- **WHEN** se guarda con el ítem de chequeo `lavado`
- **THEN** se rechaza con "El ítem de chequeo final 'lavado' no existe." y no cambia nada

### Requirement: Marcado y precio de cada ítem
Una orden SHALL poder tener marcados cero o más ítems del chequeo final (por defecto ninguno). Cada ítem marcado SHALL poder llevar un precio opcional con las reglas de `precios-ordenes`; un ítem no marcado SHALL NOT tener precio. Las claves se normalizan (recorte + minúsculas). Un ítem repetido o un precio inválido SHALL rechazarse con el prefijo "Chequeo final N: " (N = posición, desde 1).

#### Scenario: Ítems marcados con y sin precio
- **GIVEN** una orden válida
- **WHEN** se guarda con el chequeo `combustible` a 800000 y `entrega` sin precio
- **THEN** la orden tiene marcados "Combustible" con precio 800000 y "Entrega" sin precio, y los otros tres sin marcar

#### Scenario: Sin chequeo
- **WHEN** se guarda una orden sin chequeo final
- **THEN** la orden no tiene ningún ítem marcado

#### Scenario: Precio inválido
- **GIVEN** una orden válida
- **WHEN** se guarda con el chequeo `combustible` a 800000 y `entrega` a -1
- **THEN** se rechaza con "Chequeo final 2: El precio debe ser un entero de centavos entre 0 y 99.999.999.999." y no cambia nada

#### Scenario: Ítem repetido
- **GIVEN** una orden válida
- **WHEN** se guarda con el chequeo `Entrega` y `entrega`
- **THEN** se rechaza con "Chequeo final 2: 'entrega' está repetido." y no cambia nada

#### Scenario: Tipo inválido
- **GIVEN** una orden válida
- **WHEN** se guarda con el chequeo `"combustible"` (texto en lugar de lista)
- **THEN** se rechaza con "El campo chequeo_final debe ser una lista de claves." y no cambia nada

### Requirement: Chequeo guardado con la orden
El chequeo final SHALL guardarse dentro de la misma unidad atómica que el alta o la edición de la orden, y SHALL borrarse junto con la orden. Marcar ítems de chequeo SHALL NOT tocar stock, productos ni movimientos. Los ítems marcados SHALL devolverse siempre en el orden fijo de la lista, sin importar el orden en que se enviaron.

#### Scenario: Orden fija al consultar
- **GIVEN** una orden guardada con el chequeo `entrega` y `combustible`, en ese orden
- **WHEN** se consulta la orden
- **THEN** el chequeo final es "Combustible" y luego "Entrega"

#### Scenario: Borrado con chequeo
- **GIVEN** una orden con dos ítems de chequeo marcados
- **WHEN** se borra la orden
- **THEN** no queda ningún ítem de chequeo de esa orden

#### Scenario: Falla del alta con chequeo
- **GIVEN** `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 2 y el chequeo `combustible`, y falla la escritura del chequeo
- **THEN** la orden no existe y el stock de `A-01` sigue en 5
