# Spec Delta

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar en `/docs` la documentación interactiva de la API, desde donde se pueden ejecutar todos los endpoints `/api/...` (sesión, inventario, stock, movimientos, órdenes, productos, reportes, categorías y procesos) reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las diecinueve rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/stock/modificaciones`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}`, `/api/productos`, `/api/productos/inactivos`, `/api/productos/{codigo}`, `/api/reportes/productos-en-ordenes`, `/api/reportes/productos-usados`, `/api/categorias`, `/api/categorias/{clave}`, `/api/procesos` y `/api/procesos/{clave}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`
- **AND** `/api/productos` documenta `POST`, `/api/productos/inactivos` documenta `GET` y `/api/stock/modificaciones` documenta `POST`
- **AND** `/api/reportes/productos-en-ordenes` documenta solo `GET` con los parámetros `desde`, `hasta` y `codigo`, y `/api/reportes/productos-usados` documenta solo `GET`
- **AND** `/api/categorias` y `/api/procesos` documentan solo `GET` y `POST`, y `/api/categorias/{clave}` y `/api/procesos/{clave}` documentan solo `PATCH` y `DELETE`

### Requirement: Rutas de página separadas de la API
Las rutas de página y de estáticos SHALL NOT alterar ninguna respuesta de `/api/...` ni de `/docs`, SHALL NOT figurar en el esquema OpenAPI, y una ruta desconocida (de página o bajo `/api`) SHALL responder 404 con `{"detail": "Not Found"}`.

#### Scenario: OpenAPI sin rutas de página
- **WHEN** se envía `GET /openapi.json`
- **THEN** el esquema lista exactamente las diecinueve rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes`, `/reportes` ni `/static`

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
Como defensa CSRF, los endpoints que reciben cuerpo (`POST /api/login`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/stock/modificaciones`, `POST /api/productos`, `POST /api/ordenes`, `POST /api/categorias`, `PATCH /api/categorias/{clave}`, `POST /api/procesos` y `PATCH /api/procesos/{clave}`) SHALL responder 422 sin efectos cuando el `Content-Type` no sea JSON (por ejemplo `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`), aunque el cuerpo contenga JSON válido.

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

### Requirement: Alta de orden por API
`POST /api/ordenes` SHALL recibir `numero`, `fecha`, `componentes` (lista de `{codigo, cantidad}`) y, opcionales, `procesos` (lista de claves del catálogo) y `procesos_personalizados` (lista de textos), crear la orden según `ordenes-trabajo` y `procesos-ordenes` con el usuario de la sesión y responder 201 con `id`, `numero`, `fecha`, `usuario`, `componentes` (`codigo`, `nombre`, `cantidad` consolidada, por código) y `procesos` (`nombre`, `personalizado`, en orden de carga). Sin sesión SHALL responder 401 sin modificar datos.

#### Scenario: Orden creada
- **GIVEN** un cliente con sesión de `admin` y los productos activos `A-01` "Tornillo" con stock 5 y `B-02` "Tuerca" con stock 10
- **WHEN** envía `POST /api/ordenes` con `{"numero": "ot-0001", "fecha": "2026-11-20", "componentes": [{"codigo": "b-02", "cantidad": 4}, {"codigo": "A-01", "cantidad": 2}, {"codigo": "B-02", "cantidad": 1}]}`
- **THEN** la respuesta es 201 con `numero: "OT-0001"`, `fecha: "2026-11-20"`, `usuario: "admin"`, un `id` entero, `componentes` igual a `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}]` y `procesos` igual a `[]`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3 y `B-02` con stock 5
- **AND** `GET /api/movimientos` no muestra movimientos nuevos

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `A-01` x 1, `"procesos": ["Limpieza", "cambio-motor"]` y `"procesos_personalizados": [" Pulido "]`
- **THEN** la respuesta es 201 con `procesos` igual a `[{"nombre": "Limpieza", "personalizado": false}, {"nombre": "Cambio motor", "personalizado": false}, {"nombre": "Pulido", "personalizado": true}]`
- **AND** `GET /api/procesos` no incluye "Pulido"

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/ordenes` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Listado de órdenes por API
`GET /api/ordenes` SHALL aceptar los parámetros de consulta opcionales `numero`, `desde` y `hasta`, aplicar la consulta según `consulta-ordenes` y responder 200 con una lista sin paginar ni envolver de órdenes con exactamente `id`, `numero`, `fecha` (`YYYY-MM-DD`), `usuario`, `componentes` (cada uno con exactamente `codigo`, `nombre` y `cantidad`, ordenados por código) y `procesos` (cada uno con exactamente `nombre` y `personalizado`, en orden de carga), de la más nueva a la más vieja.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión de `admin` que creó la orden `OT-0001` con fecha `2026-11-20` y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2
- **WHEN** envía `GET /api/ordenes`
- **THEN** la respuesta es 200 con una lista que contiene `{"id": <entero>, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}], "procesos": []}`
- **AND** el `id` es el mismo que devolvió el alta

#### Scenario: Orden con procesos
- **GIVEN** un cliente con sesión y la orden `OT-0002` creada con el proceso `limpieza` y el personalizado "Pulido", y luego `limpieza` renombrado a "Limpieza general"
- **WHEN** envía `GET /api/ordenes?numero=OT-0002`
- **THEN** la orden trae `"procesos": [{"nombre": "Limpieza", "personalizado": false}, {"nombre": "Pulido", "personalizado": true}]`

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
`DELETE /api/ordenes/{numero}?reintegrar=true|false` SHALL borrar la orden según `ordenes-trabajo`, identificándola por su número normalizado (los caracteres `?` y `#` deben ir codificados en la URL) y responder 200 con `orden` (misma forma que el alta: `id`, `numero`, `fecha`, `usuario`, `componentes`, `procesos`), `reintegrado` (booleano) y `reintegros` (lista de `{codigo, nombre, cantidad, stock, reactivado}` ordenada por código; vacía sin reintegro).

#### Scenario: Borrado con reintegro
- **GIVEN** un cliente con sesión de `admin`, `A-01` "Tornillo" activo con stock 3, `C-99` "Arandela" dado de baja con stock 1 y la orden `OT-0001` del 2026-11-20 con `A-01` x 2 y `C-99` x 4, sin procesos (creada con id 1)
- **WHEN** envía `DELETE /api/ordenes/ot-0001?reintegrar=true`
- **THEN** la respuesta es 200 con `{"orden": {"id": 1, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4}], "procesos": []}, "reintegrado": true, "reintegros": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "stock": 5, "reactivado": false}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "stock": 5, "reactivado": true}]}`
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

#### Scenario: Sin movimientos nuevos
- **GIVEN** un cliente con sesión y una orden creada por API
- **WHEN** envía `DELETE /api/ordenes/{numero}?reintegrar=true` con el número de esa orden
- **THEN** `GET /api/movimientos` devuelve los mismos movimientos que antes del borrado

## ADDED Requirements

### Requirement: Rechazos de procesos en el alta de orden por API
`POST /api/ordenes` SHALL responder 422 con `detail` en español y sin modificar datos ante procesos inválidos según `procesos-ordenes`, incluido `procesos` o `procesos_personalizados` que no sean listas de textos ("El campo procesos debe ser una lista de textos." / "El campo procesos_personalizados debe ser una lista de textos.").

#### Scenario: Proceso inexistente
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/ordenes` con `A-01` x 1 y `"procesos": ["pintura"]`
- **THEN** la respuesta es 422 con `detail` "El proceso 'pintura' no existe." y `A-01` sigue con stock 5

#### Scenario: Personalizado vacío
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"procesos_personalizados": ["Pulido", " "]`
- **THEN** la respuesta es 422 con `detail` "Proceso personalizado 2: El nombre es obligatorio." y no se crea la orden

#### Scenario: Tipo inválido
- **WHEN** un cliente con sesión envía `POST /api/ordenes` válido con `"procesos": "limpieza"` o `"procesos": [3]`
- **THEN** la respuesta es 422 con `detail` "El campo procesos debe ser una lista de textos."

### Requirement: Procesos por API
`GET /api/procesos` SHALL exigir sesión y responder 200 con el catálogo de procesos, cada uno con exactamente `clave` y `nombre`, ordenado por nombre, sin modificar datos. Sin sesión SHALL responder 401.

#### Scenario: Procesos de ejemplo
- **GIVEN** un cliente con sesión y una base recién inicializada
- **WHEN** envía `GET /api/procesos`
- **THEN** la respuesta es 200 con `[{"clave": "cambio-filtro", "nombre": "Cambio filtro"}, {"clave": "cambio-motor", "nombre": "Cambio motor"}, {"clave": "limpieza", "nombre": "Limpieza"}]`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/procesos`
- **THEN** la respuesta es 401 y no incluye procesos

### Requirement: Alta de proceso por API
`POST /api/procesos` SHALL exigir sesión, recibir `{"nombre", "clave"?}`, aplicar el alta según `procesos-ordenes` y responder 201 con `{"clave", "nombre"}`; 409 si la clave o el nombre ya existen; 422 ante datos inválidos; 401 sin sesión. Ningún rechazo SHALL modificar datos.

#### Scenario: Alta con clave derivada
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/procesos` con `{"nombre": "Pintura del casco"}`
- **THEN** la respuesta es 201 con `{"clave": "pintura-del-casco", "nombre": "Pintura del casco"}` y `GET /api/procesos` lo incluye

#### Scenario: Nombre repetido
- **WHEN** un cliente con sesión envía `POST /api/procesos` con `{"nombre": "limpieza"}`
- **THEN** la respuesta es 409 con `detail` "Ya existe un proceso con nombre 'limpieza'."

#### Scenario: Nombre faltante
- **WHEN** un cliente con sesión envía `POST /api/procesos` con `{}`
- **THEN** la respuesta es 422 con `detail` "El campo nombre es obligatorio."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/procesos` con un cuerpo válido
- **THEN** la respuesta es 401 y no se crea ningún proceso

### Requirement: Renombre de proceso por API
`PATCH /api/procesos/{clave}` SHALL exigir sesión, recibir `{"nombre"}`, renombrar según `procesos-ordenes` y responder 200 con `{"clave", "nombre"}`; 404 si la clave no existe; 409 si el nombre es de otro proceso; 422 ante un nombre inválido o un cuerpo con `clave` ("La clave de un proceso no se puede cambiar."); 401 sin sesión.

#### Scenario: Renombrar
- **GIVEN** un cliente con sesión
- **WHEN** envía `PATCH /api/procesos/LIMPIEZA` con `{"nombre": "Limpieza general"}`
- **THEN** la respuesta es 200 con `{"clave": "limpieza", "nombre": "Limpieza general"}`

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `PATCH /api/procesos/pintura` con `{"nombre": "Pintura"}`
- **THEN** la respuesta es 404 con `detail` "No existe un proceso con clave 'pintura'."

#### Scenario: Intento de cambiar la clave
- **WHEN** un cliente con sesión envía `PATCH /api/procesos/limpieza` con `{"nombre": "Lavado", "clave": "lavado"}`
- **THEN** la respuesta es 422 con `detail` "La clave de un proceso no se puede cambiar." y nada cambia

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `PATCH /api/procesos/limpieza` con un cuerpo válido
- **THEN** la respuesta es 401 y nada cambia

### Requirement: Borrado de proceso por API
`DELETE /api/procesos/{clave}` SHALL exigir sesión, borrar el proceso según `procesos-ordenes` y responder 200 con el proceso borrado `{"clave", "nombre"}`; 404 si la clave no existe; 401 sin sesión sin cambios.

#### Scenario: Borrar un proceso usado por una orden
- **GIVEN** un cliente con sesión y la orden `OT-0001` con el proceso "Cambio motor"
- **WHEN** envía `DELETE /api/procesos/cambio-motor`
- **THEN** la respuesta es 200 con `{"clave": "cambio-motor", "nombre": "Cambio motor"}`
- **AND** `GET /api/procesos` ya no lo incluye y `GET /api/ordenes` sigue mostrando "Cambio motor" en `OT-0001`

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `DELETE /api/procesos/pintura`
- **THEN** la respuesta es 404 con `detail` "No existe un proceso con clave 'pintura'."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `DELETE /api/procesos/limpieza`
- **THEN** la respuesta es 401 y el proceso sigue en el catálogo

### Requirement: Borrado de categoría por API
`DELETE /api/categorias/{clave}` SHALL exigir sesión, borrar la categoría según `categorias-productos` y responder 200 con la categoría borrada `{"clave", "nombre"}`; 409 si algún producto la usa; 404 si no existe; 401 sin sesión. Ningún rechazo SHALL modificar datos.

#### Scenario: Borrar
- **GIVEN** un cliente con sesión y la categoría `motor` sin productos
- **WHEN** envía `DELETE /api/categorias/Motor`
- **THEN** la respuesta es 200 con `{"clave": "motor", "nombre": "Motor"}` y `GET /api/categorias` ya no la incluye

#### Scenario: En uso
- **GIVEN** un cliente con sesión y la categoría `filtro` asignada a un producto
- **WHEN** envía `DELETE /api/categorias/filtro`
- **THEN** la respuesta es 409 con `detail` "La categoría 'filtro' está asignada a 1 producto(s)." y la categoría sigue en el catálogo

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `DELETE /api/categorias/frenos`
- **THEN** la respuesta es 404 con `detail` "No existe una categoría con clave 'frenos'."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `DELETE /api/categorias/motor`
- **THEN** la respuesta es 401 y la categoría sigue en el catálogo
