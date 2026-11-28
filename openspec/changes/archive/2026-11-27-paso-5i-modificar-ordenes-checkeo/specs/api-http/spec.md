## ADDED Requirements

### Requirement: Edición de orden por API
`PUT /api/ordenes/{numero}` (con sesión y cuerpo JSON) SHALL editar la orden según `edicion-ordenes`, con el número en la URL como en el borrado. El cuerpo SHALL tener la forma del alta sin `numero`, más `conservar_servicio` (booleano opcional, `false` por defecto). La respuesta SHALL ser 200 con `orden` (forma del listado) y `ajustes` (`{codigo, nombre, cantidad_anterior, cantidad_nueva, stock, reactivado}` de cada producto cuyo stock cambió, por código). No SHALL escribir en `movimientos`.

#### Scenario: Edición con ajustes
- **GIVEN** un cliente con sesión de `admin`, `A-01` "Tornillo" con stock 5, `B-02` "Tuerca" con stock 3 y la orden `OT-0043` del 2026-11-27 con `A-01` x 2 (id 7), sin procesos, servicio ni chequeo
- **WHEN** envía `PUT /api/ordenes/ot-0043` con `{"fecha": "2026-11-27", "componentes": [{"codigo": "B-02", "cantidad": 1, "precio": 50000}], "chequeo_final": [{"clave": "entrega", "precio": 500000}]}`
- **THEN** la respuesta es 200 con `orden.numero` "OT-0043", `orden.id` 7, `orden.componentes` `[{"codigo": "B-02", "nombre": "Tuerca", "cantidad": 1, "precio": 50000}]`, `orden.chequeo_final` `[{"clave": "entrega", "nombre": "Entrega", "precio": 500000}]`, `orden.subtotal_servicios` 500000, `orden.subtotal_items` 50000 y `orden.total` 550000
- **AND** `ajustes` es `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad_anterior": 2, "cantidad_nueva": 0, "stock": 7, "reactivado": false}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad_anterior": 0, "cantidad_nueva": 1, "stock": 2, "reactivado": false}]`
- **AND** `GET /api/movimientos` devuelve los mismos movimientos que antes

#### Scenario: Conservar el servicio por API
- **GIVEN** un cliente con sesión y la orden `OT-0043` con el servicio "Servicio 20 hs"
- **WHEN** envía `PUT /api/ordenes/OT-0043` con fecha, componentes, `"conservar_servicio": true` y `"precio_servicio": 4500000`
- **THEN** la respuesta es 200 y `orden.servicio` es "Servicio 20 hs" con sus chequeos y `"precio": 4500000`

#### Scenario: Número con barra
- **GIVEN** un cliente con sesión y la orden `OT/12`
- **WHEN** envía `PUT /api/ordenes/OT/12` con un cuerpo válido
- **THEN** la respuesta es 200 con `orden.numero` "OT/12"

### Requirement: Rechazos de la edición de orden por API
`PUT /api/ordenes/{numero}` SHALL responder 422 con `detail` en español ante datos inválidos (incluido `numero` en el cuerpo, "El número de la orden no se puede cambiar."), o un servicio a conservar inexistente; 404 si la orden no existe; 404 con `codigos` ante productos inexistentes o no activos; 409 con `faltantes` (`solicitado` = cantidad adicional) si el stock no alcanza; 401 sin sesión; y 422 si el cuerpo no es JSON. Prioridad según `edicion-ordenes`. Ningún rechazo SHALL modificar datos.

#### Scenario: Stock insuficiente
- **GIVEN** un cliente con sesión, `A-01` con stock 1 y la orden `OT-0043` con `A-01` x 2
- **WHEN** envía `PUT /api/ordenes/OT-0043` con `A-01` x 5
- **THEN** la respuesta es 409 con `faltantes` `[{"codigo": "A-01", "disponible": 1, "solicitado": 3}]`
- **AND** `GET /api/ordenes?numero=OT-0043` sigue mostrando `A-01` x 2 y `GET /api/inventario` `A-01` con stock 1

#### Scenario: Orden inexistente
- **GIVEN** un cliente con sesión
- **WHEN** envía `PUT /api/ordenes/OT-9999` con un cuerpo válido
- **THEN** la respuesta es 404 con `detail` "No existe una orden con número 'OT-9999'."

#### Scenario: Número en el cuerpo
- **GIVEN** un cliente con sesión y la orden `OT-0043`
- **WHEN** envía `PUT /api/ordenes/OT-0043` con `"numero": "OT-0044"` y el resto válido
- **THEN** la respuesta es 422 con `detail` "El número de la orden no se puede cambiar." y la orden no cambia

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `PUT /api/ordenes/OT-0043`
- **THEN** la respuesta es 401 y la orden no cambia

#### Scenario: Cuerpo que no es JSON
- **GIVEN** un cliente con sesión y la orden `OT-0043`
- **WHEN** envía `PUT /api/ordenes/OT-0043` con `Content-Type: text/plain` y un cuerpo JSON válido
- **THEN** la respuesta es 422 con `detail` "El cuerpo de la petición debe ser un objeto JSON." y la orden no cambia

### Requirement: Chequeo final en el alta y en las respuestas de órdenes
`POST /api/ordenes` SHALL aceptar el campo opcional `chequeo_final`: lista cuyos elementos son la clave de un ítem (texto) o un objeto `{clave, precio}` (precio en centavos o `null`), validada según `chequeo-final-ordenes`. Toda orden devuelta por la API (alta, listado, borrado y edición) SHALL incluir `chequeo_final` como lista de `{clave, nombre, precio}` en el orden fijo, vacía si no tiene. Los clientes que no envían `chequeo_final` SHALL seguir funcionando igual.

#### Scenario: Alta con chequeo
- **GIVEN** un cliente con sesión y `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con número, fecha, `A-01` x 1 y `"chequeo_final": ["entrega", {"clave": "combustible", "precio": 800000}]`
- **THEN** la respuesta es 201 con `chequeo_final` `[{"clave": "combustible", "nombre": "Combustible", "precio": 800000}, {"clave": "entrega", "nombre": "Entrega", "precio": null}]` y `subtotal_servicios` 800000

#### Scenario: Alta sin chequeo
- **GIVEN** un cliente con sesión y `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` sin `chequeo_final`
- **THEN** la respuesta es 201 con `"chequeo_final": []`

#### Scenario: Ítem inexistente
- **GIVEN** un cliente con sesión y `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `"chequeo_final": ["lavado"]`
- **THEN** la respuesta es 422 con `detail` "El ítem de chequeo final 'lavado' no existe." y el stock de `A-01` sigue en 5
