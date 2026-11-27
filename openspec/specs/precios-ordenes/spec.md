# precios-ordenes Specification

## Purpose

Registra en cada orden de trabajo los precios que tipea el usuario (servicio general, cada ítem y cada servicio adicional) y calcula sus subtotales y su total, para poder cobrarle al cliente.

## Requirements

### Requirement: Precios tipeados y opcionales
Cada precio de una orden (servicio general, ítem, servicio adicional) SHALL ser opcional y, si se indica, un entero de centavos de pesos argentinos entre 0 y 99.999.999.999 (hasta $ 999.999.999,99). Sin precio SHALL guardarse como "sin precio", distinto de 0. Un precio inválido SHALL rechazar la orden completa sin modificar datos.

#### Scenario: Precio cero aceptado
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 1 y precio 0
- **THEN** la orden se crea y el ítem `A-01` tiene precio 0

#### Scenario: Sin precio
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 1 sin precio (ausente o `null`)
- **THEN** la orden se crea y el ítem `A-01` no tiene precio

#### Scenario: Precio negativo, decimal, texto o booleano
- **WHEN** se intenta crear una orden cuyo segundo componente tiene precio `-1`, `10.5`, `"1500"` o `true`
- **THEN** se rechaza con "Componente 2: El precio debe ser un entero de centavos entre 0 y 99.999.999.999." y el stock no cambia

#### Scenario: Precio por encima del máximo
- **WHEN** se intenta crear una orden con un componente de precio 100000000000
- **THEN** se rechaza con "Componente 1: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

### Requirement: Precio de cada ítem
Cada componente de la orden SHALL poder llevar el importe de su línea (lo que se cobra por ese producto en esa cantidad, no un precio unitario). Si un mismo producto se repite en varias líneas, la línea consolidada SHALL llevar la suma de los importes indicados, o ningún precio si ninguna línea lo indicó.

#### Scenario: Importe de la línea
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 2 y precio 1500000
- **THEN** el ítem `A-01` x 2 tiene precio 1500000 (no 3000000)

#### Scenario: Producto repetido con precios
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 2 precio 1000, `a-01` x 1 sin precio y `A-01` x 1 precio 500
- **THEN** la orden tiene una sola línea `A-01` x 4 con precio 1500

### Requirement: Precio del servicio general
La orden SHALL poder llevar el precio de su servicio general. Indicar un precio de servicio sin elegir servicio general SHALL rechazarse con "No se puede indicar el precio del servicio general sin elegir uno." sin modificar datos.

#### Scenario: Servicio con precio
- **WHEN** se crea una orden válida con el servicio `servicio-20-hs` y precio de servicio 4500000
- **THEN** el servicio general de la orden es "Servicio 20 hs" con precio 4500000

#### Scenario: Precio sin servicio
- **WHEN** se intenta crear una orden válida sin servicio general y con precio de servicio 1000
- **THEN** se rechaza con "No se puede indicar el precio del servicio general sin elegir uno."

#### Scenario: Precio de servicio inválido
- **WHEN** se intenta crear una orden con el servicio `servicio-20-hs` y precio de servicio `-5`
- **THEN** se rechaza con "El precio del servicio general debe ser un entero de centavos entre 0 y 99.999.999.999."

### Requirement: Precio de cada servicio adicional
Cada proceso de la orden (llamado "servicio adicional" en la interfaz) SHALL poder llevar su precio, indicándolo como objeto (`{clave, precio}` para los del catálogo, `{nombre, precio}` para los personalizados); un texto suelto SHALL seguir valiendo como proceso sin precio. Si una clave del catálogo se repite, SHALL contar solo la primera aparición, con su precio. Un error de precio SHALL informar la posición en su lista.

#### Scenario: Procesos con y sin precio
- **WHEN** se crea una orden válida con los procesos `{"clave": "limpieza", "precio": 1500000}` y `"cambio-filtro"` y el personalizado `{"nombre": "Pulido", "precio": 800000}`
- **THEN** la orden registra "Limpieza" con precio 1500000, "Cambio filtro" sin precio y "Pulido" (personalizado) con precio 800000, en ese orden

#### Scenario: Clave repetida con otro precio
- **WHEN** se crea una orden válida con los procesos `{"clave": "limpieza", "precio": 1000}` y `{"clave": "limpieza", "precio": 2000}`
- **THEN** la orden registra "Limpieza" una sola vez, con precio 1000

#### Scenario: Precio inválido en un proceso
- **WHEN** se intenta crear una orden con los procesos `"limpieza"` y `{"clave": "cambio-motor", "precio": -1}`
- **THEN** se rechaza con "Proceso 2: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

#### Scenario: Precio inválido en un personalizado
- **WHEN** se intenta crear una orden con el personalizado `{"nombre": "Pulido", "precio": "mil"}`
- **THEN** se rechaza con "Proceso personalizado 1: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

### Requirement: Precios guardados con la orden
Los precios SHALL guardarse en la misma operación todo o nada que la orden, sus líneas, procesos, servicio y descuentos de stock, como copia propia de la orden. Registrar precios SHALL NOT tocar stock, movimientos, productos ni catálogos.

#### Scenario: Falla al guardar un precio
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** la creación de una orden con `A-01` x 2 precio 1000 y el servicio "Servicio 20 hs" con precio 5000 falla al guardar el servicio, después de descontar el stock
- **THEN** no existe la orden ni ninguna de sus líneas, procesos o servicio, y el stock de `A-01` sigue en 5

### Requirement: Subtotales y total de la orden
Cada orden SHALL tener, calculados y no guardados (pedido del usuario, 2026-11-27): "Subtotal servicios" = precio del servicio general + suma de los precios de sus servicios adicionales; "Subtotal ítems" = suma de los precios de sus ítems; "Total" = subtotal servicios + subtotal ítems. Un precio vacío SHALL contar como 0; sin ningún precio los tres valen 0.

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
