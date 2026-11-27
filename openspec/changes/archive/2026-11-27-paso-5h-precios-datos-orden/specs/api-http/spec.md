# Spec Delta — api-http

## MODIFIED Requirements

### Requirement: Alta de orden por API
`POST /api/ordenes` SHALL recibir `numero`, `fecha`, `componentes` (lista de `{codigo, cantidad, precio?}`) y, opcionales, `cliente`, `fecha_ingreso`, `fecha_egreso`, `celular`, `casco`, `motor`, `trailer`, `procesos` (claves u objetos `{clave, precio}`), `procesos_personalizados` (textos u objetos `{nombre, precio}`), `servicio` (clave o `null`) y `precio_servicio`, crear la orden según `ordenes-trabajo`, `procesos-ordenes`, `servicios-generales`, `precios-ordenes` y `datos-cliente-ordenes` con el usuario de la sesión y responder 201 con la orden en la forma de "Listado de órdenes por API". Sin sesión SHALL responder 401 sin modificar datos.

#### Scenario: Orden creada
- **GIVEN** un cliente con sesión de `admin` y los productos activos `A-01` "Tornillo" con stock 5 y `B-02` "Tuerca" con stock 10
- **WHEN** envía `POST /api/ordenes` con `{"numero": "ot-0001", "fecha": "2026-11-20", "componentes": [{"codigo": "b-02", "cantidad": 4}, {"codigo": "A-01", "cantidad": 2}, {"codigo": "B-02", "cantidad": 1}]}`
- **THEN** la respuesta es 201 con `numero: "OT-0001"`, `fecha: "2026-11-20"`, `fecha_ingreso`, `fecha_egreso`, `cliente`, `celular`, `casco`, `motor` y `trailer` en `null`, `usuario: "admin"`, un `id` entero, `componentes` igual a `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": null}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5, "precio": null}]`, `procesos` igual a `[]`, `servicio` igual a `null` y `subtotal_servicios`, `subtotal_items` y `total` en 0
- **AND** `GET /api/inventario` muestra `A-01` con stock 3 y `B-02` con stock 5
- **AND** `GET /api/movimientos` no muestra movimientos nuevos

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` válido con `A-01` x 1, `"procesos": ["Limpieza", "cambio-motor"]` y `"procesos_personalizados": [" Pulido "]`
- **THEN** la respuesta es 201 con `procesos` igual a `[{"nombre": "Limpieza", "personalizado": false, "precio": null}, {"nombre": "Cambio motor", "personalizado": false, "precio": null}, {"nombre": "Pulido", "personalizado": true, "precio": null}]`
- **AND** `GET /api/procesos` no incluye "Pulido"

#### Scenario: Orden con servicio general
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` válido con `A-01` x 1 y `"servicio": "Servicio-20-HS"`
- **THEN** la respuesta es 201 con `servicio` igual a `{"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"], "precio": null}`
- **AND** `GET /api/inventario` muestra `A-01` con stock 4

#### Scenario: Servicio nulo o vacío
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` válido con `"servicio": null` o `"servicio": "  "`
- **THEN** la respuesta es 201 con `servicio` igual a `null`

#### Scenario: Orden con datos y precios
- **GIVEN** un cliente con sesión y el producto activo `A-01` "Tornillo" con stock 5
- **WHEN** envía `POST /api/ordenes` con `{"numero": "OT-0043", "fecha": "2026-11-27", "fecha_ingreso": "2026-11-26", "fecha_egreso": "2026-11-29", "cliente": "Juan Pérez", "celular": "11 5555-1234", "casco": "Bermuda 190", "motor": "Mercury 90 HP", "trailer": "", "componentes": [{"codigo": "A-01", "cantidad": 2, "precio": 1200000}], "servicio": "servicio-20-hs", "precio_servicio": 4500000, "procesos": [{"clave": "limpieza", "precio": 1500000}], "procesos_personalizados": [{"nombre": "Pulido"}]}`
- **THEN** la respuesta es 201 con `fecha: "2026-11-27"`, `fecha_ingreso: "2026-11-26"`, `fecha_egreso: "2026-11-29"`, `cliente: "Juan Pérez"`, `celular: "11 5555-1234"`, `casco: "Bermuda 190"`, `motor: "Mercury 90 HP"`, `trailer: null`, `componentes` igual a `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": 1200000}]`, `servicio.precio: 4500000`, `procesos` igual a `[{"nombre": "Limpieza", "personalizado": false, "precio": 1500000}, {"nombre": "Pulido", "personalizado": true, "precio": null}]`, `subtotal_servicios: 6000000`, `subtotal_items: 1200000` y `total: 7200000`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/ordenes` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Listado de órdenes por API
`GET /api/ordenes` SHALL aceptar los parámetros de consulta opcionales `numero`, `desde` y `hasta` (sobre la fecha de la orden), aplicar la consulta según `consulta-ordenes` y responder 200 con una lista sin paginar ni envolver de órdenes, de la más nueva a la más vieja, cada una con exactamente `id`, `numero`, `fecha`, `fecha_ingreso`, `fecha_egreso`, `cliente`, `celular`, `casco`, `motor`, `trailer`, `usuario`, `componentes` (`codigo`, `nombre`, `cantidad`, `precio`; por código), `procesos` (`nombre`, `personalizado`, `precio`; en orden de carga), `servicio` (`null` o `{nombre, chequeos, precio}`), `subtotal_servicios`, `subtotal_items` y `total`. Precios en centavos enteros o `null`; datos ausentes en `null`.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión de `admin` que creó la orden `OT-0001` con fecha `2026-11-20`, cliente "Juan Pérez" y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2, sin precios
- **WHEN** envía `GET /api/ordenes`
- **THEN** la respuesta es 200 con una lista que contiene `{"id": <entero>, "numero": "OT-0001", "fecha": "2026-11-20", "fecha_ingreso": null, "fecha_egreso": null, "cliente": "Juan Pérez", "celular": null, "casco": null, "motor": null, "trailer": null, "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": null}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5, "precio": null}], "procesos": [], "servicio": null, "subtotal_servicios": 0, "subtotal_items": 0, "total": 0}`
- **AND** el `id` es el mismo que devolvió el alta

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y la orden `OT-0002` creada con el proceso `limpieza` y el personalizado "Pulido", y luego `limpieza` renombrado a "Limpieza general"
- **WHEN** envía `GET /api/ordenes?numero=OT-0002`
- **THEN** la orden trae `"procesos": [{"nombre": "Limpieza", "personalizado": false, "precio": null}, {"nombre": "Pulido", "personalizado": true, "precio": null}]`

#### Scenario: Orden con servicio general
- **GIVEN** un cliente con sesión y la orden `OT-0003` creada con el servicio `servicio-20-hs`, y luego ese servicio renombrado a "Service 20 horas" y con sus chequeos reemplazados por "Chequeo de batería"
- **WHEN** envía `GET /api/ordenes?numero=OT-0003`
- **THEN** la orden trae `"servicio": {"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"], "precio": null}`

#### Scenario: Subtotales con precios vacíos
- **GIVEN** un cliente con sesión y la orden `OT-0004` con el servicio a 4500000, un proceso sin precio, un componente a 1200000 y otro sin precio
- **WHEN** envía `GET /api/ordenes?numero=OT-0004`
- **THEN** la orden trae `"subtotal_servicios": 4500000`, `"subtotal_items": 1200000` y `"total": 5700000`

#### Scenario: Orden anterior a los datos y precios
- **GIVEN** un cliente con sesión y la orden `OT-0001` creada antes de existir los datos y precios
- **WHEN** envía `GET /api/ordenes?numero=OT-0001`
- **THEN** la orden trae `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso` y `fecha_egreso` en `null`, cada `precio` en `null` y `subtotal_servicios`, `subtotal_items` y `total` en 0

#### Scenario: Filtros combinados
- **GIVEN** un cliente con sesión y las órdenes `OT-0001` del 2026-11-19 y `OT-0002` del 2026-11-20
- **WHEN** envía `GET /api/ordenes?numero=ot-0002&desde=2026-11-20&hasta=2026-11-20`
- **THEN** la respuesta es 200 con una lista que contiene solo la orden `OT-0002`

#### Scenario: Rango abierto
- **GIVEN** un cliente con sesión y las órdenes `OT-0001` del 2026-11-17 y `OT-0002` del 2026-11-19
- **WHEN** envía `GET /api/ordenes?desde=2026-11-18`
- **THEN** la respuesta es 200 con una lista que contiene solo la orden `OT-0002`

#### Scenario: Parámetros vacíos
- **GIVEN** un cliente con sesión y una orden registrada
- **WHEN** envía `GET /api/ordenes?numero=&desde=&hasta=`
- **THEN** la respuesta es 200 con todas las órdenes

#### Scenario: Componente dado de baja
- **GIVEN** un cliente con sesión y la orden `OT-0001` con un componente `C-99` "Arandela" x 1 cuyo producto quedó inactivo
- **WHEN** envía `GET /api/ordenes`
- **THEN** la orden `OT-0001` incluye el componente `{"codigo": "C-99", "nombre": "Arandela", "cantidad": 1, "precio": null}`
- **AND** `GET /api/inventario` no muestra `C-99`

#### Scenario: Número inexistente
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `GET /api/ordenes?numero=ot-9`
- **THEN** la respuesta es 404 con `detail` "No existe una orden con número 'OT-9'."

#### Scenario: Número existente fuera del rango
- **GIVEN** un cliente con sesión y la orden `OT-0001` del 2026-11-17
- **WHEN** envía `GET /api/ordenes?numero=OT-0001&desde=2026-11-18`
- **THEN** la respuesta es 200 con `[]`

#### Scenario: Sin órdenes
- **GIVEN** un cliente con sesión y ninguna orden
- **WHEN** envía `GET /api/ordenes`
- **THEN** la respuesta es 200 con `[]`

### Requirement: Borrado de orden por API
`DELETE /api/ordenes/{numero}?reintegrar=true|false` SHALL borrar la orden según `ordenes-trabajo`, identificándola por su número normalizado (los caracteres `?` y `#` deben ir codificados en la URL) y responder 200 con `orden` (misma forma que "Listado de órdenes por API", con datos, precios, subtotales y total), `reintegrado` (booleano) y `reintegros` (lista de `{codigo, nombre, cantidad, stock, reactivado}` ordenada por código; vacía sin reintegro).

#### Scenario: Borrado con reintegro
- **GIVEN** un cliente con sesión de `admin`, `A-01` "Tornillo" activo con stock 3, `C-99` "Arandela" dado de baja con stock 1 y la orden `OT-0001` del 2026-11-20 con cliente "Juan Pérez", `A-01` x 2 a 1000 y `C-99` x 4 sin precio, sin procesos ni servicio general (creada con id 1)
- **WHEN** envía `DELETE /api/ordenes/ot-0001?reintegrar=true`
- **THEN** la respuesta es 200 con `{"orden": {"id": 1, "numero": "OT-0001", "fecha": "2026-11-20", "fecha_ingreso": null, "fecha_egreso": null, "cliente": "Juan Pérez", "celular": null, "casco": null, "motor": null, "trailer": null, "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": 1000}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "precio": null}], "procesos": [], "servicio": null, "subtotal_servicios": 0, "subtotal_items": 1000, "total": 1000}, "reintegrado": true, "reintegros": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "stock": 5, "reactivado": false}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "stock": 5, "reactivado": true}]}`
- **AND** `GET /api/ordenes` ya no incluye `OT-0001` y `GET /api/inventario` muestra `A-01` y `C-99` con stock 5

#### Scenario: Borrado sin reintegro
- **GIVEN** un cliente con sesión, `A-01` con stock 3 y la orden `OT-0001` con `A-01` x 2
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=false`
- **THEN** la respuesta es 200 con la orden, `"reintegrado": false` y `"reintegros": []`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3

#### Scenario: Borrado con procesos
- **GIVEN** un cliente con sesión y la orden `OT-0002` con el proceso "Limpieza" a 1500000
- **WHEN** envía `DELETE /api/ordenes/OT-0002?reintegrar=false`
- **THEN** la `orden` de la respuesta trae `"procesos": [{"nombre": "Limpieza", "personalizado": false, "precio": 1500000}]`

#### Scenario: Borrado con servicio general
- **GIVEN** un cliente con sesión y la orden `OT-0003` con el servicio "Servicio 20 hs" sin precio
- **WHEN** envía `DELETE /api/ordenes/OT-0003?reintegrar=false`
- **THEN** la `orden` de la respuesta trae `"servicio": {"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"], "precio": null}`
- **AND** `GET /api/servicios-generales` sigue incluyendo `servicio-20-hs`

#### Scenario: Sin movimientos nuevos
- **GIVEN** un cliente con sesión y una orden creada por API
- **WHEN** envía `DELETE /api/ordenes/{numero}?reintegrar=true` con el número de esa orden
- **THEN** `GET /api/movimientos` devuelve los mismos movimientos que antes del borrado

## ADDED Requirements

### Requirement: Rechazos de datos y precios en el alta de orden por API
`POST /api/ordenes` SHALL responder 422 con `detail` en español y sin modificar datos ante datos del cliente, fechas de ingreso o egreso o precios inválidos según `datos-cliente-ordenes` y `precios-ordenes`. Los datos del cliente son opcionales: omitirlos no es un error.

#### Scenario: Datos del cliente vacíos
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `{"numero": "OT-0050", "fecha": "2026-11-27", "cliente": "  ", "celular": "", "casco": null, "componentes": [{"codigo": "A-01", "cantidad": 1}]}`
- **THEN** la respuesta es 201 con `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso` y `fecha_egreso` en `null`

#### Scenario: Cliente largo
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` válido con un `cliente` de 81 caracteres
- **THEN** la respuesta es 422 con `detail` "El cliente admite hasta 80 caracteres." y `A-01` sigue con stock 5

#### Scenario: Egreso anterior al ingreso
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"fecha_ingreso": "2026-11-27"` y `"fecha_egreso": "2026-11-26"`
- **THEN** la respuesta es 422 con `detail` "La fecha de egreso no puede ser anterior a la de ingreso."

#### Scenario: Precio no entero
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido cuyo primer componente tiene `"precio": 1500.5`
- **THEN** la respuesta es 422 con `detail` "Componente 1: El precio debe ser un entero de centavos entre 0 y 99.999.999.999."

#### Scenario: Precio de servicio sin servicio
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"servicio": null` y `"precio_servicio": 1000`
- **THEN** la respuesta es 422 con `detail` "No se puede indicar el precio del servicio general sin elegir uno."

#### Scenario: Celular inválido
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"celular": "abc"`
- **THEN** la respuesta es 422 con `detail` "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)."

#### Scenario: Solo fecha de egreso
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"fecha_egreso": "2026-11-20"` y sin `fecha_ingreso`
- **THEN** la respuesta es 201 con `fecha_ingreso: null` y `fecha_egreso: "2026-11-20"`
