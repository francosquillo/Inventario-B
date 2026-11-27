# Spec Delta — api-http

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar en `/docs` la documentación interactiva de la API, desde donde se pueden ejecutar todos los endpoints `/api/...` (sesión, inventario, stock, movimientos, órdenes, productos, reportes, categorías, procesos y servicios generales) reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las veintiuna rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/stock/modificaciones`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}`, `/api/productos`, `/api/productos/inactivos`, `/api/productos/{codigo}`, `/api/reportes/productos-en-ordenes`, `/api/reportes/productos-usados`, `/api/categorias`, `/api/categorias/{clave}`, `/api/procesos`, `/api/procesos/{clave}`, `/api/servicios-generales` y `/api/servicios-generales/{clave}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`
- **AND** `/api/productos` documenta `POST`, `/api/productos/inactivos` documenta `GET` y `/api/stock/modificaciones` documenta `POST`
- **AND** `/api/reportes/productos-en-ordenes` documenta solo `GET` con los parámetros `desde`, `hasta` y `codigo`, y `/api/reportes/productos-usados` documenta solo `GET`
- **AND** `/api/categorias`, `/api/procesos` y `/api/servicios-generales` documentan solo `GET` y `POST`, y `/api/categorias/{clave}`, `/api/procesos/{clave}` y `/api/servicios-generales/{clave}` documentan solo `PATCH` y `DELETE`

### Requirement: Rutas de página separadas de la API
Las rutas de página y de estáticos SHALL NOT alterar ninguna respuesta de `/api/...` ni de `/docs`, SHALL NOT figurar en el esquema OpenAPI, y una ruta desconocida (de página o bajo `/api`) SHALL responder 404 con `{"detail": "Not Found"}`.

#### Scenario: OpenAPI sin rutas de página
- **WHEN** se envía `GET /openapi.json`
- **THEN** el esquema lista exactamente las veintiuna rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes`, `/reportes` ni `/static`

#### Scenario: Página y API con el mismo nombre
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /ordenes` y `GET /api/ordenes`
- **THEN** la primera responde HTML y la segunda la lista JSON de órdenes

#### Scenario: Ruta desconocida
- **WHEN** un cliente envía `GET /no-existe` o `GET /api/no-existe`
- **THEN** la respuesta es 404 con `{"detail": "Not Found"}`

#### Scenario: Docs siguen disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva

### Requirement: Escrituras solo con cuerpo JSON
Como defensa CSRF, los endpoints que reciben cuerpo (`POST /api/login`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/stock/modificaciones`, `POST /api/productos`, `POST /api/ordenes`, `POST /api/categorias`, `PATCH /api/categorias/{clave}`, `POST /api/procesos`, `PATCH /api/procesos/{clave}`, `POST /api/servicios-generales` y `PATCH /api/servicios-generales/{clave}`) SHALL responder 422 sin efectos cuando el `Content-Type` no sea JSON (por ejemplo `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`), aunque el cuerpo contenga JSON válido.

#### Scenario: Login con formulario
- **WHEN** se envía `POST /api/login` con `Content-Type: application/x-www-form-urlencoded` o `text/plain` y un cuerpo con credenciales válidas
- **THEN** la respuesta es 422 con `detail` "El cuerpo de la petición debe ser un objeto JSON."
- **AND** la respuesta no establece cookie de sesión

#### Scenario: Ingreso con text/plain
- **GIVEN** un cliente con sesión y `A-01` con stock 5
- **WHEN** envía `POST /api/stock/ingreso` con `Content-Type: text/plain` y cuerpo `{"codigo": "A-01", "cantidad": 3}`
- **THEN** la respuesta es 422 y `A-01` sigue con stock 5 y sin movimientos nuevos

#### Scenario: Orden con multipart
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/ordenes` con `Content-Type: multipart/form-data`
- **THEN** la respuesta es 422 y no se crea ninguna orden

#### Scenario: Modificación y alta con text/plain
- **GIVEN** un cliente con sesión y `A-01` con stock 5
- **WHEN** envía `POST /api/stock/modificaciones` o `POST /api/productos` con `Content-Type: text/plain` y un cuerpo JSON válido
- **THEN** la respuesta es 422, `A-01` sigue con stock 5 y no se crea ningún producto ni movimiento

#### Scenario: Categorías con text/plain
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/categorias` o `PATCH /api/categorias/motor` con `Content-Type: text/plain` y un cuerpo JSON válido
- **THEN** la respuesta es 422 y el catálogo no cambia

#### Scenario: Procesos con text/plain o formulario
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/procesos` o `PATCH /api/procesos/limpieza` con `Content-Type: text/plain` o `application/x-www-form-urlencoded` y un cuerpo JSON válido
- **THEN** la respuesta es 422 y el catálogo de procesos no cambia

#### Scenario: Servicios generales con text/plain o formulario
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/servicios-generales` o `PATCH /api/servicios-generales/servicio-20-hs` con `Content-Type: text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data` y un cuerpo JSON válido
- **THEN** la respuesta es 422 y el catálogo de servicios generales no cambia

### Requirement: Alta de orden por API
`POST /api/ordenes` SHALL recibir `numero`, `fecha`, `componentes` (lista de `{codigo, cantidad}`) y, opcionales, `procesos` (lista de claves del catálogo), `procesos_personalizados` (lista de textos) y `servicio` (clave de un servicio general o `null`), crear la orden según `ordenes-trabajo`, `procesos-ordenes` y `servicios-generales` con el usuario de la sesión y responder 201 con `id`, `numero`, `fecha`, `usuario`, `componentes` (`codigo`, `nombre`, `cantidad` consolidada, por código), `procesos` (`nombre`, `personalizado`, en orden de carga) y `servicio` (`null` o `{nombre, chequeos}` con los chequeos como textos en orden). Sin sesión SHALL responder 401 sin modificar datos.

#### Scenario: Orden creada
- **GIVEN** un cliente con sesión de `admin` y los productos activos `A-01` "Tornillo" con stock 5 y `B-02` "Tuerca" con stock 10
- **WHEN** envía `POST /api/ordenes` con `{"numero": "ot-0001", "fecha": "2026-11-20", "componentes": [{"codigo": "b-02", "cantidad": 4}, {"codigo": "A-01", "cantidad": 2}, {"codigo": "B-02", "cantidad": 1}]}`
- **THEN** la respuesta es 201 con `numero: "OT-0001"`, `fecha: "2026-11-20"`, `usuario: "admin"`, un `id` entero, `componentes` igual a `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}]`, `procesos` igual a `[]` y `servicio` igual a `null`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3 y `B-02` con stock 5
- **AND** `GET /api/movimientos` no muestra movimientos nuevos

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `A-01` x 1, `"procesos": ["Limpieza", "cambio-motor"]` y `"procesos_personalizados": [" Pulido "]`
- **THEN** la respuesta es 201 con `procesos` igual a `[{"nombre": "Limpieza", "personalizado": false}, {"nombre": "Cambio motor", "personalizado": false}, {"nombre": "Pulido", "personalizado": true}]`
- **AND** `GET /api/procesos` no incluye "Pulido"

#### Scenario: Orden con servicio general
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `A-01` x 1 y `"servicio": "Servicio-20-HS"`
- **THEN** la respuesta es 201 con `servicio` igual a `{"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]}`
- **AND** `GET /api/inventario` muestra `A-01` con stock 4

#### Scenario: Servicio nulo o vacío
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` válido con `"servicio": null` o `"servicio": "  "`
- **THEN** la respuesta es 201 con `servicio` igual a `null`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/ordenes` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Listado de órdenes por API
`GET /api/ordenes` SHALL aceptar los parámetros de consulta opcionales `numero`, `desde` y `hasta`, aplicar la consulta según `consulta-ordenes` y responder 200 con una lista sin paginar ni envolver de órdenes con exactamente `id`, `numero`, `fecha` (`YYYY-MM-DD`), `usuario`, `componentes` (cada uno con exactamente `codigo`, `nombre` y `cantidad`, ordenados por código), `procesos` (cada uno con exactamente `nombre` y `personalizado`, en orden de carga) y `servicio` (`null` o exactamente `{nombre, chequeos}`), de la más nueva a la más vieja.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión de `admin` que creó la orden `OT-0001` con fecha `2026-11-20` y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2
- **WHEN** envía `GET /api/ordenes`
- **THEN** la respuesta es 200 con una lista que contiene `{"id": <entero>, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}], "procesos": [], "servicio": null}`
- **AND** el `id` es el mismo que devolvió el alta

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y la orden `OT-0002` creada con el proceso `limpieza` y el personalizado "Pulido", y luego `limpieza` renombrado a "Limpieza general"
- **WHEN** envía `GET /api/ordenes?numero=OT-0002`
- **THEN** la orden trae `"procesos": [{"nombre": "Limpieza", "personalizado": false}, {"nombre": "Pulido", "personalizado": true}]`

#### Scenario: Orden con servicio general
- **GIVEN** un cliente con sesión y la orden `OT-0003` creada con el servicio `servicio-20-hs`, y luego ese servicio renombrado a "Service 20 horas" y con sus chequeos reemplazados por "Chequeo de batería"
- **WHEN** envía `GET /api/ordenes?numero=OT-0003`
- **THEN** la orden trae `"servicio": {"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]}`

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
- **THEN** la orden `OT-0001` incluye el componente `{"codigo": "C-99", "nombre": "Arandela", "cantidad": 1}`
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
`DELETE /api/ordenes/{numero}?reintegrar=true|false` SHALL borrar la orden según `ordenes-trabajo`, identificándola por su número normalizado (los caracteres `?` y `#` deben ir codificados en la URL) y responder 200 con `orden` (misma forma que el alta: `id`, `numero`, `fecha`, `usuario`, `componentes`, `procesos`, `servicio`), `reintegrado` (booleano) y `reintegros` (lista de `{codigo, nombre, cantidad, stock, reactivado}` ordenada por código; vacía sin reintegro).

#### Scenario: Borrado con reintegro
- **GIVEN** un cliente con sesión de `admin`, `A-01` "Tornillo" activo con stock 3, `C-99` "Arandela" dado de baja con stock 1 y la orden `OT-0001` del 2026-11-20 con `A-01` x 2 y `C-99` x 4, sin procesos ni servicio general (creada con id 1)
- **WHEN** envía `DELETE /api/ordenes/ot-0001?reintegrar=true`
- **THEN** la respuesta es 200 con `{"orden": {"id": 1, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4}], "procesos": [], "servicio": null}, "reintegrado": true, "reintegros": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "stock": 5, "reactivado": false}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "stock": 5, "reactivado": true}]}`
- **AND** `GET /api/ordenes` ya no incluye `OT-0001` y `GET /api/inventario` muestra `A-01` y `C-99` con stock 5

#### Scenario: Borrado sin reintegro
- **GIVEN** un cliente con sesión, `A-01` con stock 3 y la orden `OT-0001` con `A-01` x 2
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=false`
- **THEN** la respuesta es 200 con la orden, `"reintegrado": false` y `"reintegros": []`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3

#### Scenario: Borrado con procesos
- **GIVEN** un cliente con sesión y la orden `OT-0002` con el proceso "Limpieza"
- **WHEN** envía `DELETE /api/ordenes/OT-0002?reintegrar=false`
- **THEN** la `orden` de la respuesta trae `"procesos": [{"nombre": "Limpieza", "personalizado": false}]`

#### Scenario: Borrado con servicio general
- **GIVEN** un cliente con sesión y la orden `OT-0003` con el servicio "Servicio 20 hs"
- **WHEN** envía `DELETE /api/ordenes/OT-0003?reintegrar=false`
- **THEN** la `orden` de la respuesta trae `"servicio": {"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]}`
- **AND** `GET /api/servicios-generales` sigue incluyendo `servicio-20-hs`

#### Scenario: Sin movimientos nuevos
- **GIVEN** un cliente con sesión y una orden creada por API
- **WHEN** envía `DELETE /api/ordenes/{numero}?reintegrar=true` con el número de esa orden
- **THEN** `GET /api/movimientos` devuelve los mismos movimientos que antes del borrado

## ADDED Requirements

### Requirement: Rechazos del servicio general en el alta de orden por API
`POST /api/ordenes` SHALL responder 422 con `detail` en español y sin modificar datos ante un servicio general inválido según `servicios-generales`, incluido un `servicio` que no sea texto ni `null` ("El campo servicio debe ser texto.").

#### Scenario: Servicio inexistente
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `A-01` x 1 y `"servicio": "servicio-500-hs"`
- **THEN** la respuesta es 422 con `detail` "El servicio general 'servicio-500-hs' no existe." y `A-01` sigue con stock 5

#### Scenario: Tipo inválido
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"servicio": ["servicio-20-hs"]` o `"servicio": 3`
- **THEN** la respuesta es 422 con `detail` "El campo servicio debe ser texto." y no se crea la orden

### Requirement: Servicios generales por API
`GET /api/servicios-generales` SHALL exigir sesión y responder 200 con el catálogo, cada servicio con exactamente `clave`, `nombre` y `chequeos` (lista de textos en orden), ordenado por nombre, sin modificar datos. Sin sesión SHALL responder 401.

#### Scenario: Servicio de ejemplo
- **GIVEN** un cliente con sesión y una base recién inicializada
- **WHEN** envía `GET /api/servicios-generales`
- **THEN** la respuesta es 200 con `[{"clave": "servicio-20-hs", "nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]}]`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/servicios-generales`
- **THEN** la respuesta es 401 y no incluye servicios

### Requirement: Alta de servicio general por API
`POST /api/servicios-generales` SHALL exigir sesión, recibir `{"nombre", "chequeos", "clave"?}`, aplicar el alta según `servicios-generales` y responder 201 con `{"clave", "nombre", "chequeos"}`; 409 si la clave o el nombre ya existen; 422 ante datos inválidos; 401 sin sesión. Ningún rechazo SHALL modificar datos.

#### Scenario: Alta con clave derivada
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/servicios-generales` con `{"nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite", " Chequeo de motor "]}`
- **THEN** la respuesta es 201 con `{"clave": "servicio-100-hs", "nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite", "Chequeo de motor"]}` y `GET /api/servicios-generales` lo incluye

#### Scenario: Nombre repetido
- **WHEN** un cliente con sesión envía `POST /api/servicios-generales` con `{"nombre": "servicio 20 hs", "chequeos": ["A"]}`
- **THEN** la respuesta es 409 con `detail` "Ya existe un servicio general con nombre 'servicio 20 hs'."

#### Scenario: Chequeos inválidos
- **WHEN** un cliente con sesión envía `POST /api/servicios-generales` con `{"nombre": "Servicio 50 hs", "chequeos": []}`
- **THEN** la respuesta es 422 con `detail` "El servicio general requiere al menos un chequeo." y no se crea nada

#### Scenario: Nombre faltante
- **WHEN** un cliente con sesión envía `POST /api/servicios-generales` con `{"chequeos": ["A"]}`
- **THEN** la respuesta es 422 con `detail` "El campo nombre es obligatorio."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/servicios-generales` con un cuerpo válido
- **THEN** la respuesta es 401 y no se crea ningún servicio

### Requirement: Modificación de servicio general por API
`PATCH /api/servicios-generales/{clave}` SHALL exigir sesión, recibir `{"nombre"?, "chequeos"?}` (al menos uno), modificar según `servicios-generales` y responder 200 con `{"clave", "nombre", "chequeos"}`; 404 si la clave no existe; 409 si el nombre es de otro servicio; 422 ante datos inválidos, un cuerpo sin cambios o con `clave` ("La clave de un servicio general no se puede cambiar."); 401 sin sesión.

#### Scenario: Reemplazar chequeos
- **GIVEN** un cliente con sesión
- **WHEN** envía `PATCH /api/servicios-generales/SERVICIO-20-HS` con `{"chequeos": ["Chequeo de motor", "Chequeo de batería"]}`
- **THEN** la respuesta es 200 con `{"clave": "servicio-20-hs", "nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de batería"]}`

#### Scenario: Renombrar
- **WHEN** un cliente con sesión envía `PATCH /api/servicios-generales/servicio-20-hs` con `{"nombre": "Service 20 horas"}`
- **THEN** la respuesta es 200 con `nombre` "Service 20 horas" y los mismos chequeos

#### Scenario: Cuerpo sin cambios
- **WHEN** un cliente con sesión envía `PATCH /api/servicios-generales/servicio-20-hs` con `{}`
- **THEN** la respuesta es 422 con `detail` "Indicá el nombre o los chequeos a modificar."

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `PATCH /api/servicios-generales/servicio-500-hs` con `{"nombre": "Servicio 500 hs"}`
- **THEN** la respuesta es 404 con `detail` "No existe un servicio general con clave 'servicio-500-hs'."

#### Scenario: Intento de cambiar la clave
- **WHEN** un cliente con sesión envía `PATCH /api/servicios-generales/servicio-20-hs` con `{"nombre": "Service 20", "clave": "service-20"}`
- **THEN** la respuesta es 422 con `detail` "La clave de un servicio general no se puede cambiar." y nada cambia

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `PATCH /api/servicios-generales/servicio-20-hs` con un cuerpo válido
- **THEN** la respuesta es 401 y nada cambia

### Requirement: Borrado de servicio general por API
`DELETE /api/servicios-generales/{clave}` SHALL exigir sesión, borrar el servicio según `servicios-generales` y responder 200 con el servicio borrado `{"clave", "nombre", "chequeos"}`; 404 si la clave no existe; 401 sin sesión sin cambios.

#### Scenario: Borrar un servicio usado por una orden
- **GIVEN** un cliente con sesión y la orden `OT-0001` con el servicio "Servicio 20 hs"
- **WHEN** envía `DELETE /api/servicios-generales/servicio-20-hs`
- **THEN** la respuesta es 200 con `{"clave": "servicio-20-hs", "nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]}`
- **AND** `GET /api/servicios-generales` ya no lo incluye y `GET /api/ordenes` sigue mostrando "Servicio 20 hs" con sus chequeos en `OT-0001`

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `DELETE /api/servicios-generales/servicio-500-hs`
- **THEN** la respuesta es 404 con `detail` "No existe un servicio general con clave 'servicio-500-hs'."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `DELETE /api/servicios-generales/servicio-20-hs`
- **THEN** la respuesta es 401 y el servicio sigue en el catálogo
