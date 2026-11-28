# edicion-ordenes Specification

## Purpose

Permite corregir una orden de trabajo ya creada (fecha, datos del cliente y la embarcación, servicio general, componentes, servicios adicionales, precios y chequeo final) ajustando el stock por diferencia, de forma atómica, sin tener que borrarla y crearla de nuevo.

## ADDED Requirements

### Requirement: Edición de una orden por número
El sistema SHALL permitir modificar una orden existente, identificada por su número normalizado (recorte + MAYÚSCULAS), reemplazando por completo su fecha, datos del cliente y la embarcación, servicio general, componentes, servicios adicionales, precios y chequeo final. Su número, id, usuario y momento de creación SHALL NOT cambiar. Lo que no se envía SHALL quedar vacío, salvo el servicio general conservado.

#### Scenario: Edición completa
- **GIVEN** la orden `OT-0043` del 2026-11-27 con `A-01` x 2 a 1200000, el proceso "Limpieza" a 1500000, sin cliente y sin servicio general
- **WHEN** se edita con fecha `2026-11-28`, cliente "Juan Pérez", el servicio `servicio-20-hs` a 4500000, `A-01` x 2 a 1300000, el proceso `cambio-filtro` sin precio y el chequeo `entrega` a 500000
- **THEN** `OT-0043` tiene fecha `2026-11-28`, cliente "Juan Pérez", el servicio "Servicio 20 hs" con sus chequeos y precio 4500000, `A-01` x 2 a 1300000, el proceso "Cambio filtro" sin precio, ya no tiene "Limpieza" y su chequeo final es "Entrega" a 500000
- **AND** su número, su usuario y su id no cambian

#### Scenario: Reemplazo completo de los datos opcionales
- **GIVEN** la orden `OT-0043` con cliente "Juan Pérez", celular "11 5555-1234" y el proceso "Limpieza"
- **WHEN** se edita enviando solo fecha y componentes
- **THEN** `OT-0043` queda sin cliente, sin celular y sin procesos

#### Scenario: Número normalizado
- **GIVEN** la orden `OT-0043`
- **WHEN** se edita con el número `  ot-0043 `
- **THEN** se modifica `OT-0043`

#### Scenario: Orden inexistente
- **GIVEN** que no existe la orden `OT-9999`
- **WHEN** se intenta editar `OT-9999` con datos válidos
- **THEN** se rechaza con "No existe una orden con número 'OT-9999'." y no cambia nada

#### Scenario: Edición sin cambios
- **GIVEN** la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita enviando exactamente el mismo contenido
- **THEN** la edición se acepta, la orden queda igual y el stock no cambia

### Requirement: Mismas validaciones que el alta
La edición SHALL validar fecha, datos del cliente, componentes, servicio general, procesos, precios y chequeo final con las mismas reglas y mensajes que el alta (`ordenes-trabajo`, `procesos-ordenes`, `servicios-generales`, `precios-ordenes`, `datos-cliente-ordenes`, `chequeo-final-ordenes`), incluida la consolidación de líneas repetidas por código.

#### Scenario: Sin componentes
- **GIVEN** la orden `OT-0043`
- **WHEN** se edita con la lista de componentes vacía
- **THEN** se rechaza con "La orden requiere al menos un componente." y no cambia nada

#### Scenario: Líneas repetidas
- **GIVEN** la orden `OT-0043` con `A-01` x 1 y `A-01` con stock 10
- **WHEN** se edita con `A-01` x 2 a 1000 y `a-01` x 1 a 500
- **THEN** `OT-0043` tiene una sola línea `A-01` x 3 a 1500 y el stock de `A-01` baja a 8

#### Scenario: Egreso anterior al ingreso
- **GIVEN** la orden `OT-0043`
- **WHEN** se edita con fecha de ingreso `2026-11-29` y fecha de egreso `2026-11-26`
- **THEN** se rechaza con "La fecha de egreso no puede ser anterior a la de ingreso." y no cambia nada

### Requirement: Ajuste de stock por diferencia
Al editar, para cada producto que figura en la orden antes o después de la edición, el sistema SHALL calcular la diferencia entre la cantidad nueva y la anterior: si es positiva SHALL descontar esa diferencia del stock; si es negativa SHALL reintegrar al stock la diferencia; si es cero SHALL NOT tocar el producto. Un producto que deja de estar en la orden SHALL recibir de vuelta toda su cantidad anterior.

#### Scenario: Aumentar la cantidad
- **GIVEN** `A-01` con stock 5 y la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita con `A-01` x 4
- **THEN** `OT-0043` tiene `A-01` x 4 y el stock de `A-01` es 3

#### Scenario: Reducir la cantidad
- **GIVEN** `A-01` con stock 5 y la orden `OT-0043` con `A-01` x 4
- **WHEN** se edita con `A-01` x 1
- **THEN** `OT-0043` tiene `A-01` x 1 y el stock de `A-01` es 8

#### Scenario: Quitar un producto y agregar otro
- **GIVEN** `A-01` con stock 5, `B-02` con stock 3 y la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita con `B-02` x 3
- **THEN** `OT-0043` tiene solo `B-02` x 3, el stock de `A-01` es 7 y el de `B-02` es 0

#### Scenario: Solo cambian precios
- **GIVEN** `A-01` con stock 5 y la orden `OT-0043` con `A-01` x 2 sin precio
- **WHEN** se edita con `A-01` x 2 a 1200000
- **THEN** el precio de la línea es 1200000 y el stock de `A-01` sigue en 5

#### Scenario: Usar todo el stock disponible más lo ya descontado
- **GIVEN** `A-01` con stock 1 y la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita con `A-01` x 3
- **THEN** la edición se acepta y el stock de `A-01` queda en 0

### Requirement: Productos dados de baja al editar
Al editar, un producto dado de baja que ya estaba en la orden SHALL poder quedar con la misma cantidad o con menos; reintegrarle unidades SHALL reactivarlo (como el reintegro del borrado). Aumentar su cantidad, o agregar un producto dado de baja o inexistente que no estaba en la orden, SHALL rechazar la edición completa informando todos esos códigos, como en el alta.

#### Scenario: Producto dado de baja sin cambios
- **GIVEN** `C-99` dado de baja con stock 1 y la orden `OT-0043` con `C-99` x 2
- **WHEN** se edita con `C-99` x 2 y otro cambio cualquiera
- **THEN** la edición se acepta y `C-99` sigue dado de baja con stock 1

#### Scenario: Reducir un producto dado de baja
- **GIVEN** `C-99` dado de baja con stock 1 y la orden `OT-0043` con `C-99` x 2
- **WHEN** se edita sin `C-99`
- **THEN** `C-99` queda activo con stock 3

#### Scenario: Aumentar un producto dado de baja
- **GIVEN** `C-99` dado de baja con stock 5 y la orden `OT-0043` con `C-99` x 2
- **WHEN** se edita con `C-99` x 3
- **THEN** se rechaza con "No existe un producto activo con código 'C-99'." y no cambia nada

#### Scenario: Agregar un producto inexistente
- **GIVEN** la orden `OT-0043` con `A-01` x 1
- **WHEN** se edita con `A-01` x 1 y `ZZ-99` x 1
- **THEN** se rechaza con "No existe un producto activo con código 'ZZ-99'." y no cambia nada

### Requirement: Rechazo completo por stock insuficiente al editar
Si para algún producto la diferencia a descontar supera su stock actual, la edición SHALL rechazarse completa, informando cada faltante con el stock disponible y la cantidad adicional pedida, y SHALL NOT modificar la orden ni ningún stock.

#### Scenario: Faltante en un producto
- **GIVEN** `A-01` con stock 1, `B-02` con stock 9 y la orden `OT-0043` con `A-01` x 2 y `B-02` x 1
- **WHEN** se edita con `A-01` x 5 y `B-02` x 4
- **THEN** se rechaza con un faltante de `A-01` con disponible 1 y solicitado 3
- **AND** `OT-0043` sigue con `A-01` x 2 y `B-02` x 1, y los stocks siguen en 1 y 9

#### Scenario: Faltante junto a un reintegro
- **GIVEN** `A-01` con stock 0, `B-02` con stock 0 y la orden `OT-0043` con `A-01` x 3
- **WHEN** se edita con `A-01` x 1 y `B-02` x 2
- **THEN** se rechaza con un faltante de `B-02` con disponible 0 y solicitado 2
- **AND** el stock de `A-01` sigue en 0 (el reintegro tampoco se aplica)

### Requirement: Edición atómica
La edición de la orden (sus datos, líneas, procesos, servicio, chequeo y precios) y todos sus ajustes de stock SHALL ocurrir en una sola unidad atómica: ante cualquier falla, nada SHALL quedar modificado. Dos ediciones o borrados simultáneos SHALL serializarse, de modo que el stock final refleje exactamente las cantidades de la orden que quede guardada.

#### Scenario: Falla al guardar el chequeo
- **GIVEN** `A-01` con stock 5 y la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita con `A-01` x 4 y falla la escritura del chequeo final
- **THEN** `OT-0043` sigue con `A-01` x 2 y el stock de `A-01` sigue en 5

#### Scenario: Dos ediciones seguidas
- **GIVEN** `A-01` con stock 5 y la orden `OT-0043` con `A-01` x 2
- **WHEN** se edita con `A-01` x 4 y después, otra vez, con `A-01` x 1
- **THEN** `OT-0043` tiene `A-01` x 1 y el stock de `A-01` es 6

#### Scenario: Edición de una orden recién borrada
- **GIVEN** la orden `OT-0043` borrada
- **WHEN** se intenta editar `OT-0043`
- **THEN** se rechaza con "No existe una orden con número 'OT-0043'." y el stock no cambia

### Requirement: Ajustes de la edición fuera de la bitácora
Los descuentos y reintegros de stock producidos por una edición SHALL NOT registrarse en `movimientos`, igual que los del alta y el borrado de órdenes. El resultado de la edición SHALL informar, por cada producto cuyo stock cambió y ordenados por código, su código, nombre, cantidad anterior en la orden, cantidad nueva, stock resultante y si fue reactivado.

#### Scenario: Sin movimientos nuevos
- **GIVEN** la orden `OT-0043` con `A-01` x 2 y `A-01` con stock 5
- **WHEN** se edita con `A-01` x 4
- **THEN** la bitácora de movimientos no cambia

#### Scenario: Detalle de los ajustes
- **GIVEN** `A-01` con stock 5, `B-02` con stock 3, `C-99` dado de baja con stock 0 y la orden `OT-0043` con `A-01` x 2, `B-02` x 1 y `C-99` x 1
- **WHEN** se edita con `A-01` x 3 y `B-02` x 1
- **THEN** el resultado informa `A-01` de 2 a 3 con stock 4 sin reactivar y `C-99` de 1 a 0 con stock 1 reactivado, y no informa `B-02`

### Requirement: Servicio general conservado al editar
Al editar, el servicio general SHALL poder (a) conservarse tal como quedó guardado (nombre y chequeos), aunque el catálogo lo haya cambiado o borrado, actualizando solo su precio; (b) reemplazarse por uno del catálogo, copiando su nombre y chequeos actuales; o (c) quitarse. Conservar y a la vez elegir uno del catálogo, o conservar en una orden sin servicio, SHALL rechazarse sin cambios.

#### Scenario: Conservar un servicio borrado del catálogo
- **GIVEN** la orden `OT-0043` con el servicio "Servicio 20 hs" (tres chequeos) sin precio, y `servicio-20-hs` borrado del catálogo
- **WHEN** se edita conservando el servicio con precio 4500000
- **THEN** `OT-0043` sigue con "Servicio 20 hs", sus tres chequeos y precio 4500000

#### Scenario: Reemplazar por el del catálogo
- **GIVEN** la orden `OT-0043` con el servicio "Servicio 20 hs" con tres chequeos, y el catálogo con `servicio-20-hs` modificado a dos chequeos
- **WHEN** se edita con el servicio `servicio-20-hs`
- **THEN** `OT-0043` tiene "Servicio 20 hs" con los dos chequeos actuales del catálogo

#### Scenario: Quitar el servicio
- **GIVEN** la orden `OT-0043` con servicio general
- **WHEN** se edita sin servicio y sin pedir conservarlo
- **THEN** `OT-0043` queda sin servicio general

#### Scenario: Conservar y elegir a la vez
- **GIVEN** la orden `OT-0043` con servicio general
- **WHEN** se edita pidiendo conservar el servicio y eligiendo `servicio-20-hs`
- **THEN** se rechaza con "No se puede elegir un servicio general y conservar el actual a la vez." y no cambia nada

#### Scenario: Conservar sin servicio
- **GIVEN** la orden `OT-0041` sin servicio general
- **WHEN** se edita pidiendo conservar el servicio
- **THEN** se rechaza con "La orden no tiene un servicio general para conservar." y no cambia nada

### Requirement: Orden de prioridad de los rechazos de la edición
Ante varios errores, la edición SHALL informar uno solo, en este orden: número inválido; intento de cambiar el número; datos inválidos en el orden del alta (fecha, ingreso, egreso, cliente, celular, casco, motor, trailer, componentes, servicio, precio del servicio, servicio conservado y elegido a la vez, procesos, personalizados, chequeo); orden inexistente; servicio a conservar inexistente; productos no activos; stock insuficiente.

#### Scenario: Datos inválidos en una orden inexistente
- **GIVEN** que no existe la orden `OT-9999`
- **WHEN** se intenta editar `OT-9999` con la fecha `2026-02-30`
- **THEN** se rechaza con "La fecha (2026-02-30) no es una fecha válida."

#### Scenario: Producto inexistente y stock insuficiente
- **GIVEN** la orden `OT-0043` con `A-01` x 1 y `A-01` con stock 0
- **WHEN** se edita con `A-01` x 5 y `ZZ-99` x 1
- **THEN** se rechaza informando el producto inexistente `ZZ-99`
