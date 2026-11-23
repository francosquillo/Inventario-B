## ADDED Requirements

### Requirement: Alta de producto por API
`POST /api/productos` SHALL recibir `codigo`, `nombre` y `stock` (los tres obligatorios), aplicar el alta según `alta-productos` con el usuario de la sesión y responder 201 con `codigo`, `nombre`, `stock`, `sin_stock`, `creado` y `reactivado`. Sin sesión válida SHALL responder 401 sin modificar datos.

#### Scenario: Alta con stock cero
- **GIVEN** un cliente con sesión y ningún producto `N-01`
- **WHEN** envía `POST /api/productos` con `{"codigo": "n-01", "nombre": "Arandela 6mm", "stock": 0}`
- **THEN** la respuesta es 201 con `{"codigo": "N-01", "nombre": "Arandela 6mm", "stock": 0, "sin_stock": true, "creado": true, "reactivado": false}`
- **AND** `GET /api/inventario` incluye `N-01`

#### Scenario: Reactivación
- **GIVEN** un cliente con sesión y el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** envía `POST /api/productos` con `{"codigo": "C-99", "nombre": "Junta tórica", "stock": 6}`
- **THEN** la respuesta es 201 con `nombre: "Junta tórica"`, `stock: 6`, `creado: false` y `reactivado: true`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/productos` con un cuerpo válido
- **THEN** la respuesta es 401 y no se crea ningún producto

### Requirement: Errores del alta de producto por API
`POST /api/productos` SHALL responder 409 con `detail` "Ya existe un producto con código 'X'." si el código pertenece a un producto activo, y 422 con un `detail` en español ante datos faltantes, vacíos, con tipo incorrecto o fuera de rango. Ningún rechazo SHALL modificar datos.

#### Scenario: Código activo repetido
- **GIVEN** un cliente con sesión y el producto activo `A-01`
- **WHEN** envía `POST /api/productos` con `{"codigo": "a-01", "nombre": "Otro", "stock": 1}`
- **THEN** la respuesta es 409 con `detail` "Ya existe un producto con código 'A-01'."

#### Scenario: Nombre faltante
- **WHEN** un cliente con sesión envía `POST /api/productos` con `{"codigo": "N-02", "stock": 3}` o con `"nombre": "   "`
- **THEN** la respuesta es 422 con `detail` "El campo nombre es obligatorio."

#### Scenario: Stock inválido
- **WHEN** un cliente con sesión envía `POST /api/productos` con `"stock": -1`, `"stock": 10001` o `"stock": "5"`
- **THEN** la respuesta es 422 con `detail` "El stock debe ser un entero entre 0 y 10.000."

#### Scenario: Stock faltante
- **WHEN** un cliente con sesión envía `POST /api/productos` sin `stock`
- **THEN** la respuesta es 422 con `detail` "El campo stock es obligatorio."

### Requirement: Productos dados de baja por API
`GET /api/productos/inactivos` SHALL responder 200 con la lista de productos dados de baja (`codigo`, `nombre`, `stock`, `sin_stock`) ordenada por código, o `[]` si no hay ninguno. Sin sesión SHALL responder 401.

#### Scenario: Con productos dados de baja
- **GIVEN** un cliente con sesión, el producto activo `A-01` y los inactivos `C-99` (stock 2) y `B-02` (stock 0)
- **WHEN** envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 200 con `B-02` y luego `C-99`, sin `A-01`

#### Scenario: Ninguno
- **GIVEN** un cliente con sesión y ningún producto dado de baja
- **WHEN** envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 200 con `[]`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 401

### Requirement: Modificación de stock por API
`POST /api/stock/modificaciones` SHALL recibir `{"lineas": [...]}`, cada línea `{"codigo", "modo": "fijar", "stock", "nombre"?}` o `{"codigo", "modo": "sumar", "cantidad", "nombre"?}`, aplicar la modificación según `modificacion-stock` con el usuario de la sesión y responder 200 con `lineas`: por línea `codigo`, `nombre`, `stock`, `sin_stock`, `modo`, `stock_anterior`, `nombre_anterior` y `reactivado`.

#### Scenario: Fijar y sumar
- **GIVEN** un cliente con sesión y los productos activos `A-01` "Tornillo" (stock 5) y `B-10` "Tuerca" (stock 0)
- **WHEN** envía `POST /api/stock/modificaciones` con `{"lineas": [{"codigo": "A-01", "modo": "fijar", "stock": 12, "nombre": "Tornillo M8"}, {"codigo": "b-10", "modo": "sumar", "cantidad": 4}]}`
- **THEN** la respuesta es 200 con `lineas[0]` = `{"codigo": "A-01", "nombre": "Tornillo M8", "stock": 12, "sin_stock": false, "modo": "fijar", "stock_anterior": 5, "nombre_anterior": "Tornillo", "reactivado": false}`
- **AND** `lineas[1]` tiene `codigo: "B-10"`, `stock: 4`, `stock_anterior: 0`, `modo: "sumar"` y `reactivado: false`

#### Scenario: Reactivación
- **GIVEN** un cliente con sesión y el producto inactivo `C-99` con stock 2
- **WHEN** envía `POST /api/stock/modificaciones` con `{"lineas": [{"codigo": "C-99", "modo": "fijar", "stock": 6}]}`
- **THEN** la respuesta es 200 con `stock: 6` y `reactivado: true`
- **AND** `GET /api/inventario` incluye `C-99`

#### Scenario: Fijar en cero un producto dado de baja
- **GIVEN** un cliente con sesión y el producto inactivo `C-99` con stock 2
- **WHEN** envía `POST /api/stock/modificaciones` con `{"lineas": [{"codigo": "C-99", "modo": "fijar", "stock": 0}]}`
- **THEN** la respuesta es 200 con `stock: 0`, `sin_stock: true` y `reactivado: false`
- **AND** `GET /api/inventario` no incluye `C-99` y `GET /api/productos/inactivos` sí

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/stock/modificaciones` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Errores de la modificación de stock por API
`POST /api/stock/modificaciones` SHALL responder 422 con `detail` en español ante datos inválidos, con el prefijo "Línea N: " cuando el error es de una línea, y 404 con `detail` y `codigos` (lista de códigos normalizados) cuando uno o más productos no existen. Ningún rechazo SHALL modificar datos.

#### Scenario: Producto inexistente
- **GIVEN** un cliente con sesión, el producto activo `A-01` y ningún producto `Z-01`
- **WHEN** envía una modificación que fija `A-01` en 3 y suma 1 a `z-01`
- **THEN** la respuesta es 404 con `{"detail": "No existe un producto con código 'Z-01'.", "codigos": ["Z-01"]}` y `A-01` no cambia

#### Scenario: Modo inválido o faltante
- **WHEN** un cliente con sesión envía una línea 1 con `"modo": "restar"` o sin `modo`
- **THEN** la respuesta es 422 con `detail` "Línea 1: El campo modo debe ser fijar o sumar."

#### Scenario: Valor del modo faltante
- **WHEN** un cliente con sesión envía la línea 2 con `"modo": "fijar"` sin `stock`
- **THEN** la respuesta es 422 con `detail` "Línea 2: El campo stock es obligatorio."

#### Scenario: Línea repetida
- **WHEN** un cliente con sesión envía dos líneas con `A-01` y `a-01`
- **THEN** la respuesta es 422 con `detail` "Línea 2: el producto 'A-01' ya está en la línea 1."

#### Scenario: Lista vacía
- **WHEN** un cliente con sesión envía `{"lineas": []}`
- **THEN** la respuesta es 422 con `detail` "La modificación requiere al menos una línea."

## MODIFIED Requirements

### Requirement: Consulta de movimientos por API
`GET /api/movimientos` SHALL aceptar los parámetros de consulta opcionales `codigo`, `desde` y `hasta`, aplicar la consulta según `consulta-movimientos` y responder 200 con una lista sin paginar de objetos con exactamente `fecha` (ISO 8601 con offset `-03:00`), `codigo`, `nombre`, `tipo`, `cantidad`, `usuario` (nombre de usuario), `stock_anterior` y `stock_nuevo` (enteros en `ajuste`, `null` en `ingreso` y `egreso`), del más nuevo al más viejo.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión y un ingreso de 3 unidades de `A-01` "Tornillo M4" hecho por `admin` el `2026-11-19T15:30:00-03:00`
- **WHEN** envía `GET /api/movimientos`
- **THEN** la respuesta es 200 con una lista que contiene `{"fecha": "2026-11-19T15:30:00-03:00", "codigo": "A-01", "nombre": "Tornillo M4", "tipo": "ingreso", "cantidad": 3, "usuario": "admin", "stock_anterior": null, "stock_nuevo": null}`

#### Scenario: Ajuste
- **GIVEN** un cliente con sesión que fijó el stock de `A-01` de 7 en 4
- **WHEN** envía `GET /api/movimientos?codigo=A-01`
- **THEN** la respuesta incluye un movimiento con `tipo: "ajuste"`, `cantidad: 3`, `stock_anterior: 7` y `stock_nuevo: 4`

#### Scenario: Filtros combinados
- **GIVEN** un cliente con sesión y movimientos de `A-01` y `B-10` en distintos días
- **WHEN** envía `GET /api/movimientos?codigo=a-01&desde=2026-11-18&hasta=2026-11-19`
- **THEN** la respuesta es 200 solo con los movimientos de `A-01` cuya fecha local está entre el 18 y el 19 de noviembre de 2026 inclusive

#### Scenario: Sin resultados
- **GIVEN** un cliente con sesión y ningún movimiento
- **WHEN** envía `GET /api/movimientos`
- **THEN** la respuesta es 200 con `[]`

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso, egreso y modificación de stock, consulta de movimientos, alta, listado y borrado de órdenes y alta, listado de dados de baja y baja de productos reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las trece rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/stock/modificaciones`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}`, `/api/productos`, `/api/productos/inactivos` y `/api/productos/{codigo}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`
- **AND** `/api/productos` documenta `POST`, `/api/productos/inactivos` documenta `GET` y `/api/stock/modificaciones` documenta `POST`

### Requirement: Rutas de página separadas de la API
Las rutas de página y de estáticos SHALL NOT alterar ninguna respuesta de `/api/...` ni de `/docs`, SHALL NOT figurar en el esquema OpenAPI, y una ruta desconocida (de página o bajo `/api`) SHALL responder 404 con `{"detail": "Not Found"}`.

#### Scenario: OpenAPI sin rutas de página
- **WHEN** se envía `GET /openapi.json`
- **THEN** el esquema lista exactamente las trece rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes` ni `/static`

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
Como defensa CSRF, los endpoints que reciben cuerpo (`POST /api/login`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/stock/modificaciones`, `POST /api/productos`, `POST /api/ordenes`) SHALL responder 422 sin efectos cuando el `Content-Type` no sea JSON (por ejemplo `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`), aunque el cuerpo contenga JSON válido.

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
