# api-http Specification

## Purpose
Expone el sistema como API HTTP JSON para el frontend (Paso 5) y para la verificación manual en la documentación interactiva: arranca inicializando la base, autentica con una cookie de sesión firmada y protege toda operación salvo el login, sin contener reglas de negocio propias.

## Requirements

### Requirement: Arranque inicializa la base antes de atender requests
Al iniciar, la aplicación SHALL crear el esquema y sembrar el `admin` (según `inicializacion-base-datos`) antes de atender el primer request.

#### Scenario: Primer arranque sobre base nueva
- **GIVEN** una ruta de base que todavía no existe
- **WHEN** la aplicación arranca
- **THEN** la base queda creada con sus cinco tablas y el usuario `admin`
- **AND** el login con las credenciales del `admin` funciona desde el primer request

#### Scenario: Arranque repetido
- **GIVEN** una base ya inicializada con el `admin` y productos cargados
- **WHEN** la aplicación arranca de nuevo
- **THEN** arranca sin error y los datos existentes no cambian

### Requirement: Contraseña generada del admin en el log del servidor
Si la inicialización genera la contraseña del `admin` (variable `ADMIN_DEFAULT_PASSWORD` ausente o vacía), la aplicación SHALL escribirla una única vez en el log del servidor junto con la advertencia de anotarla, y nunca SHALL devolverla en una respuesta HTTP ni escribirla en archivos.

#### Scenario: Variable ausente en base nueva
- **GIVEN** una base nueva y `ADMIN_DEFAULT_PASSWORD` no definida
- **WHEN** la aplicación arranca
- **THEN** el log del servidor contiene la contraseña generada y la advertencia de que no se volverá a mostrar

#### Scenario: Arranque posterior no vuelve a mostrarla
- **GIVEN** una base donde el `admin` ya existe
- **WHEN** la aplicación arranca de nuevo sin `ADMIN_DEFAULT_PASSWORD`
- **THEN** el log del servidor no contiene ninguna contraseña

#### Scenario: Variable definida
- **GIVEN** una base nueva y `ADMIN_DEFAULT_PASSWORD` definida
- **WHEN** la aplicación arranca
- **THEN** el log del servidor no contiene esa contraseña ni ninguna otra

### Requirement: Clave de firma de sesión obligatoria
La aplicación SHALL firmar la cookie de sesión con la clave tomada de la variable de entorno `SECRET_KEY` y SHALL negarse a arrancar con un mensaje claro si la clave falta o está vacía. La clave nunca SHALL estar escrita en el código.

#### Scenario: Falta SECRET_KEY
- **GIVEN** `SECRET_KEY` no definida o vacía
- **WHEN** se intenta crear la aplicación
- **THEN** el arranque falla con un mensaje que nombra la variable `SECRET_KEY`

### Requirement: Login por API
`POST /api/login` SHALL recibir un JSON con `username` (1 a 64 caracteres) y `password` (1 a 128 caracteres). Con credenciales válidas SHALL responder 200 con la identidad del usuario (`id`, `username`, sin datos de hash) y establecer una cookie de sesión firmada, HttpOnly y SameSite=Lax. Con credenciales inválidas SHALL responder 401 con el mensaje genérico "Usuario o contraseña incorrectos." sin establecer sesión.

#### Scenario: Credenciales válidas
- **GIVEN** el `admin` sembrado con contraseña conocida
- **WHEN** se envía `POST /api/login` con `admin` y esa contraseña
- **THEN** la respuesta es 200 con `username` igual a `admin` y sin campos de hash ni salt
- **AND** la respuesta establece una cookie de sesión marcada HttpOnly y SameSite=Lax

#### Scenario: Contraseña incorrecta
- **WHEN** se envía `POST /api/login` con `admin` y una contraseña incorrecta
- **THEN** la respuesta es 401 con el mensaje "Usuario o contraseña incorrectos."
- **AND** no se establece sesión

#### Scenario: Usuario inexistente
- **WHEN** se envía `POST /api/login` con un usuario que no existe
- **THEN** la respuesta es 401 con el mismo mensaje "Usuario o contraseña incorrectos."

#### Scenario: Usuario solo con espacios
- **WHEN** se envía `POST /api/login` con usuario `"   "` y cualquier contraseña
- **THEN** la respuesta es 401 con el mismo mensaje genérico

#### Scenario: Límite de longitud en login
- **WHEN** se envía `POST /api/login` con un `username` de más de 64 caracteres o una `password` de más de 128
- **THEN** la respuesta es 422 sin evaluar credenciales
- **AND** valores de exactamente 64 y 128 caracteres se procesan normalmente (401 si las credenciales son incorrectas)

#### Scenario: Login nuevo reemplaza la sesión anterior
- **GIVEN** un cliente con sesión iniciada
- **WHEN** envía `POST /api/login` con credenciales inválidas
- **THEN** la respuesta es 401 y la sesión anterior deja de ser válida

### Requirement: Logout por API
`POST /api/logout` SHALL eliminar la sesión del cliente y responder sin contenido; SHALL ser idempotente (también responde con éxito sin sesión previa).

#### Scenario: Logout con sesión
- **GIVEN** un cliente con sesión iniciada
- **WHEN** envía `POST /api/logout`
- **THEN** la respuesta es 204
- **AND** un `GET /api/me` posterior responde 401

#### Scenario: Logout sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/logout`
- **THEN** la respuesta es 204

### Requirement: Identidad de la sesión
`GET /api/me` SHALL devolver 200 con la identidad (`id`, `username`) del usuario de la sesión, o 401 si no hay sesión válida.

#### Scenario: Con sesión
- **GIVEN** un cliente que inició sesión como `admin`
- **WHEN** envía `GET /api/me`
- **THEN** la respuesta es 200 con `username` igual a `admin`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/me`
- **THEN** la respuesta es 401

#### Scenario: Cookie adulterada
- **WHEN** un cliente envía `GET /api/me` con una cookie de sesión cuya firma no es válida
- **THEN** la respuesta es 401

### Requirement: Inventario por API
`GET /api/inventario` SHALL devolver 200 con la lista JSON de productos activos ordenados por código, cada uno con `codigo`, `nombre`, `stock`, `sin_stock` (`true` si el stock es 0) y `categoria` (clave de la categoría, o `null` si no tiene), o una lista vacía cuando no haya productos activos. Sin sesión válida SHALL responder 401 sin datos.

#### Scenario: Listado con stock cero
- **GIVEN** un cliente con sesión y los productos activos `B-10` (stock 0) y `A-01` (stock 5), más `C-99` inactivo
- **WHEN** envía `GET /api/inventario`
- **THEN** la respuesta es 200 con `A-01` (`sin_stock: false`) seguido de `B-10` (`sin_stock: true`) y sin `C-99`

#### Scenario: Categoría en cada producto
- **GIVEN** un cliente con sesión, `A-01` "Tornillo" (stock 5, sin categoría) y `F-01` "Filtro de aceite" (stock 2, categoría `filtro`)
- **WHEN** envía `GET /api/inventario`
- **THEN** la respuesta es 200 con `[{"codigo": "A-01", "nombre": "Tornillo", "stock": 5, "sin_stock": false, "categoria": null}, {"codigo": "F-01", "nombre": "Filtro de aceite", "stock": 2, "sin_stock": false, "categoria": "filtro"}]`

#### Scenario: Inventario vacío
- **GIVEN** un cliente con sesión y ningún producto activo
- **WHEN** envía `GET /api/inventario`
- **THEN** la respuesta es 200 con una lista vacía

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/inventario`
- **THEN** la respuesta es 401 y no incluye productos

### Requirement: Rechazo de cuerpos malformados
Los endpoints que reciben JSON SHALL rechazar con 422 los cuerpos ausentes, con JSON mal formado, con campos faltantes, con campos vacíos o con tipos incorrectos, sin convertir tipos implícitamente (por ejemplo, un número donde se espera texto, o el texto `"5"` donde se espera un entero). El cuerpo de la respuesta SHALL ser `{"detail": "<mensaje en español>"}` según "Errores de validación uniformes en español".

#### Scenario: Campo faltante
- **WHEN** se envía `POST /api/login` sin el campo `password`
- **THEN** la respuesta es 422 con `detail` "El campo password es obligatorio."

#### Scenario: Campo vacío
- **WHEN** se envía `POST /api/login` con `password` igual a `""`
- **THEN** la respuesta es 422 con `detail` "El campo password es obligatorio."

#### Scenario: Tipo incorrecto
- **WHEN** se envía `POST /api/login` con `username` numérico (por ejemplo `5`)
- **THEN** la respuesta es 422 con `detail` "El campo username debe ser texto."

#### Scenario: Texto demasiado largo
- **WHEN** se envía `POST /api/login` con un `username` de 65 caracteres
- **THEN** la respuesta es 422 con `detail` "El campo username admite hasta 64 caracteres."

#### Scenario: Cuerpo ausente
- **WHEN** se envía `POST /api/login` sin cuerpo
- **THEN** la respuesta es 422 con `detail` "El cuerpo de la petición es obligatorio."

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

### Requirement: Ingreso de stock por API
`POST /api/stock/ingreso` SHALL recibir `codigo`, `cantidad` y opcionalmente `nombre`, aplicar el ingreso según `movimientos-stock` con el usuario de la sesión y responder 200 con `codigo`, `nombre`, `stock`, `sin_stock`, `creado` y `reactivado`. Sin sesión válida SHALL responder 401 sin modificar datos.

#### Scenario: Suma
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "A-01", "cantidad": 3}`
- **THEN** la respuesta es 200 con `stock: 8`, `sin_stock: false`, `creado: false` y `reactivado: false`

#### Scenario: Alta
- **GIVEN** un cliente con sesión y ningún producto `N-01`
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "N-01", "cantidad": 10, "nombre": "Arandela 6mm"}`
- **THEN** la respuesta es 200 con `codigo: "N-01"`, `nombre: "Arandela 6mm"`, `stock: 10` y `creado: true`
- **AND** `GET /api/inventario` incluye `N-01`

#### Scenario: Alta con código en minúsculas
- **GIVEN** un cliente con sesión y ningún producto `RD-6204`
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "rd-6204", "cantidad": 4, "nombre": "Rodamiento 6204"}`
- **THEN** la respuesta es 200 con `codigo: "RD-6204"` y `creado: true`

#### Scenario: Reactivación
- **GIVEN** un cliente con sesión y el producto inactivo `C-99` con stock 2
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "C-99", "cantidad": 3}`
- **THEN** la respuesta es 200 con `stock: 5`, `creado: false` y `reactivado: true`

#### Scenario: Código nuevo sin nombre
- **GIVEN** un cliente con sesión y ningún producto `N-02`
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "N-02", "cantidad": 5}`
- **THEN** la respuesta es 422 con un `detail` de texto que indica que el producto no existe y requiere nombre
- **AND** `N-02` no existe

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/stock/ingreso` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Egreso de stock por API
`POST /api/stock/egreso` SHALL recibir `codigo` y `cantidad`, aplicar el egreso según `movimientos-stock` con el usuario de la sesión y responder 200 con `codigo`, `nombre`, `stock` y `sin_stock`; 404 si el producto no existe o está inactivo; 409 si la cantidad excede el stock. Sin sesión SHALL responder 401.

#### Scenario: Egreso aceptado
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/stock/egreso` con `{"codigo": "A-01", "cantidad": 5}`
- **THEN** la respuesta es 200 con `stock: 0` y `sin_stock: true`

#### Scenario: Egreso con código en minúsculas
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/stock/egreso` con `{"codigo": "a-01", "cantidad": 1}`
- **THEN** la respuesta es 200 con `codigo: "A-01"` y `stock: 4`

#### Scenario: Exceso de stock
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/stock/egreso` con `{"codigo": "A-01", "cantidad": 6}`
- **THEN** la respuesta es 409 con un `detail` de texto que informa el stock disponible (5)
- **AND** el stock de `A-01` sigue en 5

#### Scenario: Producto inexistente o inactivo
- **GIVEN** un cliente con sesión, ningún producto `X-00` y el producto inactivo `C-99`
- **WHEN** envía `POST /api/stock/egreso` con el código `X-00` o con el código `C-99`
- **THEN** la respuesta es 404 con un `detail` de texto que indica que el producto no existe

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/stock/egreso` con un cuerpo válido
- **THEN** la respuesta es 401 y no se modifica ningún dato

### Requirement: Validación de los cuerpos de stock
Los endpoints de stock SHALL responder 422 con `{"detail": "<mensaje en español>"}`, sin modificar datos, ante `cantidad` faltante, no entera, como texto, booleana, menor que 1 o mayor que 10.000, y ante `codigo` faltante, vacío, de solo espacios o de más de 50 caracteres, o `nombre` de más de 120 caracteres.

#### Scenario: Cantidad como texto
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "A-01", "cantidad": "5"}`
- **THEN** la respuesta es 422 con `detail` "La cantidad debe ser un entero entre 1 y 10.000."

#### Scenario: Cantidad decimal o cero
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/stock/egreso` con `cantidad` igual a `2.5` o a `0`
- **THEN** la respuesta es 422 con `detail` "La cantidad debe ser un entero entre 1 y 10.000."

#### Scenario: Cantidad en el límite
- **GIVEN** un cliente con sesión y el producto activo `A-01` con stock 5
- **WHEN** envía `POST /api/stock/ingreso` con `cantidad` `10000` y luego con `cantidad` `10001`
- **THEN** la primera respuesta es 200 con `stock: 10005` y la segunda es 422 sin modificar el stock

#### Scenario: Código de solo espacios
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/stock/ingreso` con `{"codigo": "   ", "cantidad": 1, "nombre": "X"}`
- **THEN** la respuesta es 422 con `detail` "El campo codigo es obligatorio." y no se crea ningún producto

#### Scenario: Código demasiado largo
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/stock/ingreso` con un `codigo` de 51 caracteres
- **THEN** la respuesta es 422 con `detail` "El campo codigo admite hasta 50 caracteres."

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

### Requirement: Errores de la consulta de movimientos por API
`GET /api/movimientos` SHALL responder 422 con `detail` de texto en español ante fechas de filtro inválidas o `desde` posterior a `hasta`, y 401 sin sesión válida.

#### Scenario: Fecha con formato inválido
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/movimientos?desde=19/11/2026`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Desde posterior a hasta
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/movimientos?desde=2026-11-20&hasta=2026-11-19`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/movimientos`
- **THEN** la respuesta es 401

### Requirement: Errores de validación uniformes en español
Toda respuesta 422 de la API, venga de la validación del cuerpo/parámetros o del dominio, SHALL tener la forma `{"detail": "<mensaje>"}` con un único texto legible en español que nombra el campo como aparece en la API (`codigo`, `nombre`, `cantidad`, `username`, `password`, `desde`, `hasta`, `numero`, `fecha`, `componentes`). Los errores dentro de una línea de `componentes` SHALL anteponer "Componente N: " (N desde 1).

#### Scenario: Campo faltante
- **WHEN** se envía `POST /api/stock/egreso` con sesión y `{"codigo": "A-01"}`
- **THEN** la respuesta es 422 con `detail` "El campo cantidad es obligatorio."

#### Scenario: JSON mal formado
- **WHEN** se envía `POST /api/login` con el cuerpo de texto `{"username": "admin",` y `Content-Type: application/json`
- **THEN** la respuesta es 422 con `detail` "El cuerpo de la petición no es JSON válido."

#### Scenario: Campo faltante en una línea de componentes
- **WHEN** se envía `POST /api/ordenes` con sesión y un segundo componente `{"cantidad": 1}` sin `codigo`
- **THEN** la respuesta es 422 con `detail` "Componente 2: El campo codigo es obligatorio."

### Requirement: Un solo mensaje por error de validación
Si una petición tiene varios errores de validación, el 422 SHALL informar solo el primero según el orden de declaración de los campos; ante un error no contemplado SHALL usar un mensaje genérico en español.

#### Scenario: Varios errores
- **WHEN** se envía `POST /api/stock/ingreso` con sesión y `{"cantidad": 0}`
- **THEN** la respuesta es 422 con `detail` "El campo codigo es obligatorio." (el primer campo declarado con error)

#### Scenario: Error no contemplado
- **WHEN** la validación produce un tipo de error sin mensaje específico para el campo `x`
- **THEN** la respuesta es 422 con `detail` "El campo x no es válido."

### Requirement: Formato del 422 en OpenAPI
El esquema OpenAPI SHALL documentar el formato `{"detail": "<texto>"}` para las respuestas 422 de los endpoints con validación.

#### Scenario: Esquema OpenAPI del 422
- **WHEN** se lee `GET /openapi.json`
- **THEN** la respuesta 422 de `/api/login`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos`, de `GET` y `POST` `/api/ordenes`, de `DELETE /api/ordenes/{numero}` y de `DELETE /api/productos/{codigo}` referencia un esquema con un único campo `detail` de tipo texto
- **AND** la respuesta 404 de `GET /api/ordenes`, de `DELETE /api/ordenes/{numero}` y de `DELETE /api/productos/{codigo}` referencia ese mismo esquema
- **AND** la respuesta 409 de `POST /api/ordenes` referencia un esquema con `detail` de tipo texto y `faltantes` opcional

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

### Requirement: Rechazos del alta de orden por API
`POST /api/ordenes` SHALL responder 422 ante datos inválidos, 409 ante número duplicado, 404 ante productos inexistentes o inactivos y 409 ante stock insuficiente, siempre con `detail` en español y sin modificar datos; el 409 por stock SHALL incluir además `faltantes` con `codigo`, `disponible` y `solicitado` de cada componente que no alcanza.

#### Scenario: Stock insuficiente
- **GIVEN** un cliente con sesión y los productos activos `A-01` con stock 1 y `B-02` con stock 0
- **WHEN** envía `POST /api/ordenes` con `A-01` x 2 y `B-02` x 1
- **THEN** la respuesta es 409 con `detail` "Stock insuficiente para la orden: 'A-01' (disponible 1, solicitado 2); 'B-02' (disponible 0, solicitado 1)."
- **AND** `faltantes` es `[{"codigo": "A-01", "disponible": 1, "solicitado": 2}, {"codigo": "B-02", "disponible": 0, "solicitado": 1}]`
- **AND** el inventario no cambia

#### Scenario: Número duplicado
- **GIVEN** un cliente con sesión y la orden `OT-0001` existente
- **WHEN** envía `POST /api/ordenes` con `numero` `"OT-0001"` y componentes válidos
- **THEN** la respuesta es 409 con `detail` "Ya existe una orden con número 'OT-0001'." y sin `faltantes`

#### Scenario: Producto inexistente
- **GIVEN** un cliente con sesión y ningún producto `X-00`
- **WHEN** envía `POST /api/ordenes` con el componente `X-00` x 1
- **THEN** la respuesta es 404 con `detail` "No existe un producto activo con código 'X-00'."

#### Scenario: Componentes vacíos
- **WHEN** un cliente con sesión envía `POST /api/ordenes` con `"componentes": []`
- **THEN** la respuesta es 422 con `detail` "La orden requiere al menos un componente."

#### Scenario: Cantidad no entera en una línea
- **WHEN** un cliente con sesión envía `POST /api/ordenes` cuyo primer componente tiene `"cantidad": "5"`
- **THEN** la respuesta es 422 con `detail` "Componente 1: La cantidad debe ser un entero entre 1 y 10.000."

#### Scenario: Fecha con formato inválido
- **WHEN** un cliente con sesión envía `POST /api/ordenes` con `"fecha": "20/11/2026"`
- **THEN** la respuesta es 422 con `detail` "La fecha debe tener formato AAAA-MM-DD."

### Requirement: Sesión de usuario inexistente
Todo endpoint protegido (`GET /api/me`, `GET /api/inventario`, `GET /api/movimientos`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/ordenes`, `GET /api/ordenes`, `DELETE /api/ordenes/{numero}` y `DELETE /api/productos/{codigo}`) SHALL confirmar que el usuario de la sesión existe en la base; si no existe (cookie firmada de un usuario borrado o de una base reseteada), SHALL responder 401 con `detail` "No autenticado.", descartar la sesión y no modificar ningún dato.

#### Scenario: Usuario de la sesión borrado
- **GIVEN** un cliente que inició sesión como `admin` y cuya fila fue borrada de `usuarios`
- **WHEN** envía `POST /api/ordenes` con un cuerpo válido
- **THEN** la respuesta es 401 con `detail` "No autenticado."
- **AND** no se crea ninguna orden y el stock no cambia

#### Scenario: Ingreso y egreso con usuario borrado
- **GIVEN** un cliente con la sesión de un usuario que ya no existe en `usuarios`
- **WHEN** envía `POST /api/stock/ingreso` o `POST /api/stock/egreso` con un cuerpo válido
- **THEN** la respuesta es 401 con `detail` "No autenticado." y no se crean movimientos ni cambia el stock

#### Scenario: Borrados con usuario borrado
- **GIVEN** un cliente con la sesión de un usuario que ya no existe en `usuarios`, una orden existente y un producto activo
- **WHEN** envía `DELETE /api/ordenes/{numero}?reintegrar=true` o `DELETE /api/productos/{codigo}`
- **THEN** cada respuesta es 401 con `detail` "No autenticado."
- **AND** la orden sigue existiendo, el producto sigue activo y el stock no cambia

#### Scenario: Consultas con usuario borrado
- **GIVEN** un cliente con la sesión de un usuario que ya no existe en `usuarios`
- **WHEN** envía `GET /api/me`, `GET /api/inventario`, `GET /api/movimientos` o `GET /api/ordenes`
- **THEN** cada respuesta es 401 con `detail` "No autenticado."

#### Scenario: Usuario recreado con otro id
- **GIVEN** un cliente con la sesión del usuario con id 1, que fue borrado y vuelto a crear con id 999
- **WHEN** envía cualquiera de los nueve requests anteriores
- **THEN** la respuesta es 401 con `detail` "No autenticado."

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

### Requirement: Errores del listado de órdenes por API
`GET /api/ordenes` SHALL responder 422 con `detail` de texto en español ante fechas de filtro inválidas, `desde` posterior a `hasta` o un número de más de 30 caracteres, 404 con `detail` "No existe una orden con número '<número normalizado>'." si se filtra por un número que no existe (la validación 422 tiene prioridad), y 401 sin sesión válida.

#### Scenario: Fecha con formato inválido
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/ordenes?desde=19/11/2026`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Fecha inexistente
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/ordenes?hasta=2026-02-30`
- **THEN** la respuesta es 422 con `detail` "La fecha 'hasta' (2026-02-30) no es una fecha válida."

#### Scenario: Desde posterior a hasta
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/ordenes?desde=2026-11-20&hasta=2026-11-19`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."

#### Scenario: Número demasiado largo
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/ordenes` con un `numero` de 31 caracteres
- **THEN** la respuesta es 422 con `detail` "El campo numero admite hasta 30 caracteres."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/ordenes`
- **THEN** la respuesta es 401

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

### Requirement: Errores del borrado de orden por API
`DELETE /api/ordenes/{numero}` SHALL responder 422 con `detail` en español si `reintegrar` falta, está vacío, se repite o no es `true`/`false`, o si el número está en blanco o tiene más de 30 caracteres; 404 con `detail` "No existe una orden con número 'X'." (X normalizado) si la orden no existe (la validación 422 tiene prioridad); y 401 sin sesión válida. Ningún rechazo SHALL modificar datos.

#### Scenario: Reintegrar ausente
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/OT-0001`
- **THEN** la respuesta es 422 con `detail` "El campo reintegrar es obligatorio."
- **AND** la orden sigue en `GET /api/ordenes`

#### Scenario: Reintegrar repetido
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=true&reintegrar=false` (o con valores iguales)
- **THEN** la respuesta es 422 con `detail` "El campo reintegrar debe enviarse una sola vez."
- **AND** el stock y la orden no cambian

#### Scenario: Reintegrar vacío
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=`
- **THEN** la respuesta es 422 con `detail` "El campo reintegrar es obligatorio."

#### Scenario: Reintegrar inválido
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=si`, `?reintegrar=1` o `?reintegrar=TRUE`
- **THEN** cada respuesta es 422 con `detail` "El campo reintegrar debe ser true o false."

#### Scenario: Número normalizado
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/%20ot-0001%20?reintegrar=false`
- **THEN** la respuesta es 200 con `"numero": "OT-0001"`

#### Scenario: Número con barra
- **GIVEN** un cliente con sesión y la orden `OT/2026/01`
- **WHEN** envía `DELETE /api/ordenes/OT/2026/01?reintegrar=true`
- **THEN** la respuesta es 200 con `"numero": "OT/2026/01"`

#### Scenario: Número en blanco
- **GIVEN** un cliente con sesión y la orden `OT-0001`
- **WHEN** envía `DELETE /api/ordenes/%20%20?reintegrar=true`
- **THEN** la respuesta es 422 con `detail` "El campo numero es obligatorio."
- **AND** la orden sigue en `GET /api/ordenes`

#### Scenario: Número demasiado largo
- **GIVEN** un cliente con sesión
- **WHEN** envía `DELETE /api/ordenes/{numero}?reintegrar=true` con un número de 31 caracteres
- **THEN** la respuesta es 422 con `detail` "El campo numero admite hasta 30 caracteres."

#### Scenario: Orden inexistente
- **GIVEN** un cliente con sesión y ninguna orden con número `OT-0999`
- **WHEN** envía `DELETE /api/ordenes/ot-0999?reintegrar=false`
- **THEN** la respuesta es 404 con `detail` "No existe una orden con número 'OT-0999'."

#### Scenario: Segundo borrado de la misma orden
- **GIVEN** un cliente con sesión que ya borró la orden `OT-0001`
- **WHEN** envía otra vez `DELETE /api/ordenes/OT-0001?reintegrar=true`
- **THEN** la respuesta es 404 con `detail` "No existe una orden con número 'OT-0001'." y el stock no cambia

#### Scenario: Sin sesión
- **GIVEN** la orden `OT-0001`
- **WHEN** un cliente sin sesión envía `DELETE /api/ordenes/OT-0001?reintegrar=true`
- **THEN** la respuesta es 401 y la orden sigue existiendo

### Requirement: Baja de producto por API
`DELETE /api/productos/{codigo}` SHALL dar de baja el producto según `baja-productos` y responder 200 con `codigo`, `nombre`, `stock` y `sin_stock` del producto dado de baja. El código SHALL aceptarse tal como está guardado, incluso si contiene `/`.

#### Scenario: Baja exitosa
- **GIVEN** un cliente con sesión y el producto activo `A-01` "Tornillo" con stock 7
- **WHEN** envía `DELETE /api/productos/a-01`
- **THEN** la respuesta es 200 con `{"codigo": "A-01", "nombre": "Tornillo", "stock": 7, "sin_stock": false}`
- **AND** `GET /api/inventario` ya no muestra `A-01`

#### Scenario: Código con barra
- **GIVEN** un cliente con sesión y el producto activo `CAJA/10`
- **WHEN** envía `DELETE /api/productos/CAJA/10`
- **THEN** la respuesta es 200 con `"codigo": "CAJA/10"`

#### Scenario: Efectos en el resto de la API
- **GIVEN** un cliente con sesión, la orden `OT-0001` con `A-01` "Tornillo" x 2 y `A-01` dado de baja por `DELETE /api/productos/A-01`
- **WHEN** envía `GET /api/ordenes`, `POST /api/stock/egreso` con `A-01` x 1 y `POST /api/ordenes` con `A-01` x 1
- **THEN** `GET /api/ordenes` sigue mostrando `A-01` "Tornillo" x 2 en `OT-0001`
- **AND** el egreso y el alta de orden responden 404 con `detail` "No existe un producto activo con código 'A-01'."

#### Scenario: Reingreso tras la baja
- **GIVEN** un cliente con sesión y `A-01` con stock 7 dado de baja por `DELETE /api/productos/A-01`
- **WHEN** envía `POST /api/stock/ingreso` con `A-01` x 3
- **THEN** la respuesta es 200 con `"stock": 10` y `"reactivado": true`

### Requirement: Errores de la baja de producto por API
`DELETE /api/productos/{codigo}` SHALL responder 404 con `detail` "No existe un producto activo con código 'X'." (X normalizado) si el producto no existe o ya está dado de baja, 422 con el `detail` de validación de código existente si el código es vacío o tiene más de 50 caracteres, y 401 sin sesión válida. Ningún rechazo SHALL modificar datos.

#### Scenario: Inexistente
- **GIVEN** un cliente con sesión
- **WHEN** envía `DELETE /api/productos/z-99`
- **THEN** la respuesta es 404 con `detail` "No existe un producto activo con código 'Z-99'."

#### Scenario: Ya dado de baja
- **GIVEN** un cliente con sesión que ya dio de baja `A-01`
- **WHEN** envía otra vez `DELETE /api/productos/A-01`
- **THEN** la respuesta es 404 con `detail` "No existe un producto activo con código 'A-01'."

#### Scenario: Código en blanco o demasiado largo
- **GIVEN** un cliente con sesión
- **WHEN** envía `DELETE /api/productos/%20%20` o un código de 51 caracteres
- **THEN** la respuesta es 422 con `detail` "El campo codigo es obligatorio." o "El campo codigo admite hasta 50 caracteres." respectivamente

#### Scenario: Sin sesión
- **GIVEN** el producto activo `A-01`
- **WHEN** un cliente sin sesión envía `DELETE /api/productos/A-01`
- **THEN** la respuesta es 401 y `A-01` sigue activo

### Requirement: Página de login en la raíz
`GET /` SHALL responder 200 con la página HTML de login cuando no haya una sesión válida (sin sesión, con firma inválida, vencida o de un usuario que ya no existe), y SHALL redirigir con 303 a `/inventario` cuando la sesión sea válida.

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /`
- **THEN** la respuesta es 200 con `Content-Type` `text/html` y el formulario de login

#### Scenario: Con sesión válida
- **GIVEN** un cliente que inició sesión como `admin`
- **WHEN** envía `GET /`
- **THEN** la respuesta es 303 con `Location` `/inventario`

#### Scenario: Sesión de un usuario inexistente
- **GIVEN** un cliente con una cookie firmada cuyo `usuario_id` ya no existe en la base
- **WHEN** envía `GET /`
- **THEN** la respuesta es 200 con la página de login (no redirige)

### Requirement: Páginas protegidas por sesión
`GET /inventario`, `GET /ordenes` y `GET /reportes` SHALL responder 200 con su página HTML cuando la sesión sea válida y SHALL redirigir con 303 a `/` cuando no lo sea, sin incluir datos del inventario, de las órdenes ni de los reportes en ningún caso (los datos llegan solo por `/api/...`).

#### Scenario: Inventario con sesión
- **GIVEN** un cliente que inició sesión
- **WHEN** envía `GET /inventario`
- **THEN** la respuesta es 200 con `Content-Type` `text/html`

#### Scenario: Órdenes con sesión
- **GIVEN** un cliente que inició sesión
- **WHEN** envía `GET /ordenes`
- **THEN** la respuesta es 200 con `Content-Type` `text/html`

#### Scenario: Sin sesión redirige al login
- **WHEN** un cliente sin sesión envía `GET /inventario`, `GET /ordenes` o `GET /reportes`
- **THEN** la respuesta es 303 con `Location` `/`

#### Scenario: La página no embebe datos
- **GIVEN** un cliente con sesión y el producto activo `A-01` "Tornillo"
- **WHEN** envía `GET /inventario` o `GET /reportes`
- **THEN** el HTML de la respuesta no contiene `A-01` ni `Tornillo`

### Requirement: Archivos estáticos públicos
La aplicación SHALL servir los archivos de `static/` bajo `/static/` sin exigir sesión, con el tipo de contenido según la extensión, y SHALL responder 404 a archivos inexistentes, a directorios y a cualquier intento de salir de `static/`.

#### Scenario: Hoja de estilos
- **WHEN** un cliente sin sesión envía `GET /static/css/tokens.css`
- **THEN** la respuesta es 200 con `Content-Type` `text/css`

#### Scenario: Script
- **WHEN** un cliente sin sesión envía `GET /static/js/api.js`
- **THEN** la respuesta es 200 con un `Content-Type` de JavaScript

#### Scenario: Travesía de rutas
- **WHEN** un cliente envía `GET /static/..%2Finventario.db` o `GET /static/../requirements.txt`
- **THEN** la respuesta es 404 y no incluye el contenido del archivo

#### Scenario: Directorio
- **WHEN** un cliente envía `GET /static/` o `GET /static/js/`
- **THEN** la respuesta es 404

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

### Requirement: Cabeceras de seguridad de las páginas
Las respuestas HTML de `/`, `/inventario` y `/ordenes` SHALL incluir `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` y `Cache-Control: no-store`. Las respuestas de `/api/...` SHALL quedar como estaban.

#### Scenario: Cabeceras en el login
- **WHEN** un cliente sin sesión envía `GET /`
- **THEN** la respuesta incluye las cuatro cabeceras con esos valores

#### Scenario: Cabeceras en páginas protegidas
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /inventario` o `GET /ordenes`
- **THEN** la respuesta incluye las cuatro cabeceras con esos valores

### Requirement: Vigencia de la sesión
La cookie de sesión SHALL vencer a las 12 horas de la última respuesta que la renovó: SHALL emitirse con `Max-Age=43200` y la aplicación SHALL rechazar como sesión inválida (401 en `/api`, login en las páginas) una cookie cuya firma tenga más de 12 horas.

#### Scenario: Max-Age en el login
- **WHEN** se envía `POST /api/login` con credenciales válidas
- **THEN** la cookie de sesión se emite con `Max-Age=43200`, HttpOnly y SameSite=Lax

#### Scenario: Cookie vencida
- **GIVEN** una cookie de sesión del `admin` firmada con la `SECRET_KEY` correcta hace 13 horas
- **WHEN** el cliente envía `GET /api/me`
- **THEN** la respuesta es 401

#### Scenario: Cookie vigente
- **GIVEN** una cookie de sesión del `admin` firmada con la `SECRET_KEY` correcta hace 11 horas
- **WHEN** el cliente envía `GET /api/me`
- **THEN** la respuesta es 200 con `username` igual a `admin`

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

### Requirement: Sin acceso entre orígenes
La aplicación SHALL NOT habilitar CORS: ninguna respuesta SHALL incluir cabeceras `Access-Control-Allow-*`, y una petición de verificación previa (`OPTIONS` con `Origin` y `Access-Control-Request-Method`) a una ruta `/api/...` SHALL NOT responder con éxito.

#### Scenario: Preflight de un DELETE desde otro origen
- **WHEN** se envía `OPTIONS /api/ordenes/OT-0001` con `Origin: http://evil.example` y `Access-Control-Request-Method: DELETE`
- **THEN** la respuesta no es 2xx y no incluye `Access-Control-Allow-Origin`

#### Scenario: Petición con Origin ajeno
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/inventario` con `Origin: http://evil.example`
- **THEN** la respuesta no incluye `Access-Control-Allow-Origin` ni `Access-Control-Allow-Credentials`

### Requirement: Alta de producto por API
`POST /api/productos` SHALL recibir `codigo`, `nombre` y `stock` (los tres obligatorios) y `categoria` opcional (clave del catálogo, sin distinguir mayúsculas; ausente, `null` o texto vacío = sin categoría), aplicar el alta según `alta-productos` con el usuario de la sesión y responder 201 con `codigo`, `nombre`, `stock`, `sin_stock`, `categoria`, `creado` y `reactivado`. Sin sesión válida SHALL responder 401 sin modificar datos.

#### Scenario: Alta con stock cero
- **GIVEN** un cliente con sesión y ningún producto `N-01`
- **WHEN** envía `POST /api/productos` con `{"codigo": "n-01", "nombre": "Arandela 6mm", "stock": 0}`
- **THEN** la respuesta es 201 con `{"codigo": "N-01", "nombre": "Arandela 6mm", "stock": 0, "sin_stock": true, "categoria": null, "creado": true, "reactivado": false}`
- **AND** `GET /api/inventario` incluye `N-01`

#### Scenario: Alta con categoría
- **GIVEN** un cliente con sesión y ningún producto `AC-10`
- **WHEN** envía `POST /api/productos` con `{"codigo": "AC-10", "nombre": "Aceite 10W40", "stock": 4, "categoria": "Aceite"}`
- **THEN** la respuesta es 201 con `categoria: "aceite"`
- **AND** `GET /api/inventario` muestra `AC-10` con `categoria: "aceite"`

#### Scenario: Reactivación
- **GIVEN** un cliente con sesión y el producto inactivo `C-99` "Junta" con stock 2 y categoría `motor`
- **WHEN** envía `POST /api/productos` con `{"codigo": "C-99", "nombre": "Junta tórica", "stock": 6}`
- **THEN** la respuesta es 201 con `nombre: "Junta tórica"`, `stock: 6`, `categoria: null`, `creado: false` y `reactivado: true`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/productos` con un cuerpo válido
- **THEN** la respuesta es 401 y no se crea ningún producto

### Requirement: Errores del alta de producto por API
`POST /api/productos` SHALL responder 409 con `detail` "Ya existe un producto con código 'X'." si el código pertenece a un producto activo (sea cual sea la categoría enviada), y 422 con un `detail` en español ante datos faltantes, vacíos, con tipo incorrecto o fuera de rango, o ante una categoría inexistente. Ningún rechazo SHALL modificar datos.

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

#### Scenario: Categoría inexistente
- **WHEN** un cliente con sesión envía `POST /api/productos` con `{"codigo": "N-06", "nombre": "Bujía", "stock": 2, "categoria": "encendido"}`
- **THEN** la respuesta es 422 con `detail` "La categoría 'encendido' no existe." y no se crea `N-06`

#### Scenario: Categoría con tipo incorrecto
- **WHEN** un cliente con sesión envía `POST /api/productos` con `"categoria": 3`
- **THEN** la respuesta es 422 con `detail` "El campo categoria debe ser texto."

### Requirement: Productos dados de baja por API
`GET /api/productos/inactivos` SHALL responder 200 con la lista de productos dados de baja (`codigo`, `nombre`, `stock`, `sin_stock`, `categoria`) ordenada por código, o `[]` si no hay ninguno. Sin sesión SHALL responder 401.

#### Scenario: Con productos dados de baja
- **GIVEN** un cliente con sesión, el producto activo `A-01` y los inactivos `C-99` (stock 2, categoría `motor`) y `B-02` (stock 0, sin categoría)
- **WHEN** envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 200 con `B-02` (`categoria: null`) y luego `C-99` (`categoria: "motor"`), sin `A-01`

#### Scenario: Ninguno
- **GIVEN** un cliente con sesión y ningún producto dado de baja
- **WHEN** envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 200 con `[]`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/productos/inactivos`
- **THEN** la respuesta es 401

### Requirement: Modificación de stock por API
`POST /api/stock/modificaciones` SHALL recibir `{"lineas": [...]}`, cada línea `{"codigo", "modo": "fijar", "stock", "nombre"?, "categoria"?}` o `{"codigo", "modo": "sumar", "cantidad", "nombre"?, "categoria"?}` (`categoria` ausente = no cambia; `null` o texto vacío = sin categoría; clave = esa categoría), aplicar la modificación según `modificacion-stock` con el usuario de la sesión y responder 200 con `lineas`: por línea `codigo`, `nombre`, `stock`, `sin_stock`, `categoria`, `modo`, `stock_anterior`, `nombre_anterior`, `categoria_anterior` y `reactivado`.

#### Scenario: Fijar y sumar
- **GIVEN** un cliente con sesión y los productos activos `A-01` "Tornillo" (stock 5, sin categoría) y `B-10` "Tuerca" (stock 0, sin categoría)
- **WHEN** envía `POST /api/stock/modificaciones` con `{"lineas": [{"codigo": "A-01", "modo": "fijar", "stock": 12, "nombre": "Tornillo M8", "categoria": "motor"}, {"codigo": "b-10", "modo": "sumar", "cantidad": 4}]}`
- **THEN** la respuesta es 200 con `lineas[0]` = `{"codigo": "A-01", "nombre": "Tornillo M8", "stock": 12, "sin_stock": false, "categoria": "motor", "modo": "fijar", "stock_anterior": 5, "nombre_anterior": "Tornillo", "categoria_anterior": null, "reactivado": false}`
- **AND** `lineas[1]` tiene `codigo: "B-10"`, `stock: 4`, `stock_anterior: 0`, `modo: "sumar"`, `categoria: null`, `categoria_anterior: null` y `reactivado: false`

#### Scenario: Quitar la categoría
- **GIVEN** un cliente con sesión y el producto activo `F-01` (stock 3, categoría `filtro`)
- **WHEN** envía `POST /api/stock/modificaciones` con `{"lineas": [{"codigo": "F-01", "modo": "fijar", "stock": 3, "categoria": null}]}`
- **THEN** la respuesta es 200 con `categoria: null` y `categoria_anterior: "filtro"`

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
`POST /api/stock/modificaciones` SHALL responder 422 con `detail` en español ante datos inválidos (incluida una categoría inexistente o de tipo incorrecto), con el prefijo "Línea N: " cuando el error es de una línea, y 404 con `detail` y `codigos` (lista de códigos normalizados) cuando uno o más productos no existen. Ningún rechazo SHALL modificar datos.

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

#### Scenario: Categoría inexistente en una línea
- **GIVEN** un cliente con sesión y los productos activos `A-01` y `B-10`
- **WHEN** envía una modificación cuya línea 2 suma 1 a `B-10` con `"categoria": "frenos"`
- **THEN** la respuesta es 422 con `detail` "Línea 2: La categoría 'frenos' no existe." y ningún producto cambia

### Requirement: Reporte de productos en órdenes por API
`GET /api/reportes/productos-en-ordenes` SHALL exigir sesión, aceptar `desde` (obligatorio), `hasta` (opcional: ausente o vacío = hoy, hora local de Argentina) y `codigo` (opcional), aplicar la consulta según `reporte-ordenes` y responder 200 con una lista sin paginar de objetos con exactamente `codigo`, `nombre`, `categoria` (clave o `null`), `activo` (booleano), `cantidad` (suma en el rango) y `ordenes` (órdenes del rango en que aparece), en el orden del reporte. El endpoint SHALL NOT aceptar filtro de categoría ni modificar datos.

#### Scenario: Reporte de un mes
- **GIVEN** un cliente con sesión, la orden `OT-0001` del 2026-11-03 con `A-01` "Tornillo" (sin categoría) x 3 y `B-02` "Tuerca" (categoría `motor`) x 1, y la orden `OT-0002` del 2026-11-10 con `A-01` x 2
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30`
- **THEN** la respuesta es 200 con `[{"codigo": "A-01", "nombre": "Tornillo", "categoria": null, "activo": true, "cantidad": 5, "ordenes": 2}, {"codigo": "B-02", "nombre": "Tuerca", "categoria": "motor", "activo": true, "cantidad": 1, "ordenes": 1}]`

#### Scenario: Sin hasta
- **GIVEN** el mismo estado y la fecha local de Argentina 2026-11-24
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01`
- **THEN** la respuesta es 200 con la misma lista que con `hasta=2026-11-24`

#### Scenario: Filtro por producto
- **GIVEN** el mismo estado
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30&codigo=b-02`
- **THEN** la respuesta es 200 con solo la fila de `B-02`

#### Scenario: Producto dado de baja
- **GIVEN** `C-99` "Viejo", dado de baja y sin categoría, usado x 2 en una orden del rango
- **WHEN** se consulta el rango
- **THEN** la respuesta incluye `{"codigo": "C-99", "nombre": "Viejo", "categoria": null, "activo": false, "cantidad": 2, "ordenes": 1}`

#### Scenario: Filtro por un producto dado de baja
- **GIVEN** el mismo estado
- **WHEN** se consulta el rango con `codigo=c-99`
- **THEN** la respuesta es 200 con solo `{"codigo": "C-99", "nombre": "Viejo", "categoria": null, "activo": false, "cantidad": 2, "ordenes": 1}`

#### Scenario: Sin resultados
- **GIVEN** un cliente con sesión y ninguna orden en octubre de 2026
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-10-01&hasta=2026-10-31`
- **THEN** la respuesta es 200 con `[]`

#### Scenario: Código inexistente
- **WHEN** un cliente con sesión envía el rango con `codigo=ZZ-99`, que no existe
- **THEN** la respuesta es 200 con `[]`

### Requirement: Errores del reporte de productos en órdenes por API
`GET /api/reportes/productos-en-ordenes` SHALL responder 401 sin sesión válida (antes de validar parámetros) y 422 con `detail` de texto en español (formato uniforme de "Errores de validación uniformes en español") ante un `desde` faltante o vacío, una fecha mal formada o inexistente, `desde` posterior al `hasta` efectivo (hoy si falta) o un `codigo` más largo que el máximo admitido.

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30`
- **THEN** la respuesta es 401

#### Scenario: Sin sesión y sin parámetros
- **WHEN** un cliente sin sesión envía `GET /api/reportes/productos-en-ordenes`
- **THEN** la respuesta es 401, no 422

#### Scenario: Falta desde
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?hasta=2026-11-30`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' es obligatoria."

#### Scenario: Desde futuro sin hasta
- **GIVEN** un cliente con sesión y la fecha local de Argentina 2026-11-24
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-12-01`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' (2026-12-01) no puede ser posterior a 'hasta' (2026-11-24)."

#### Scenario: Formato inválido
- **GIVEN** un cliente con sesión
- **WHEN** envía `desde=01/11/2026&hasta=2026-11-30`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Rango invertido
- **GIVEN** un cliente con sesión
- **WHEN** envía `desde=2026-11-30&hasta=2026-11-01`
- **THEN** la respuesta es 422 con `detail` "La fecha 'desde' (2026-11-30) no puede ser posterior a 'hasta' (2026-11-01)."

### Requirement: Productos usados por API
`GET /api/reportes/productos-usados` SHALL exigir sesión (401 sin ella), no aceptar filtros, aplicar la consulta "Productos usados en órdenes" de `reporte-ordenes` y responder 200 con una lista de objetos con exactamente `codigo`, `nombre` y `activo` (booleano), ordenada por código. El endpoint SHALL NOT modificar datos.

#### Scenario: Productos usados
- **GIVEN** un cliente con sesión, `A-01` "Tornillo" activo usado en órdenes, `C-99` "Viejo" dado de baja usado en una orden y `B-02` nunca usado
- **WHEN** envía `GET /api/reportes/productos-usados`
- **THEN** la respuesta es 200 con `[{"codigo": "A-01", "nombre": "Tornillo", "activo": true}, {"codigo": "C-99", "nombre": "Viejo", "activo": false}]`

#### Scenario: Sin órdenes
- **GIVEN** un cliente con sesión y ninguna orden
- **WHEN** envía `GET /api/reportes/productos-usados`
- **THEN** la respuesta es 200 con `[]`

#### Scenario: Productos usados sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/reportes/productos-usados`
- **THEN** la respuesta es 401

### Requirement: Página de reportes protegida
`GET /reportes` SHALL responder 200 con su página HTML cuando la sesión sea válida y SHALL redirigir con 303 a `/` cuando no lo sea, sin incluir datos del reporte, del inventario ni de las órdenes en el HTML, y con las mismas cabeceras de seguridad que las demás páginas.

#### Scenario: Reportes con sesión
- **GIVEN** un cliente que inició sesión
- **WHEN** envía `GET /reportes`
- **THEN** la respuesta es 200 con `Content-Type` `text/html`

#### Scenario: Reportes sin sesión
- **WHEN** un cliente sin sesión envía `GET /reportes`
- **THEN** la respuesta es 303 con `Location` `/`

### Requirement: Alta de categoría por API
`POST /api/categorias` SHALL exigir sesión, recibir `{"nombre", "clave"?}`, aplicar el alta según `categorias-productos` y responder 201 con `{"clave", "nombre"}`. SHALL responder 409 con `detail` si la clave o el nombre ya existen y 422 con `detail` en español ante datos inválidos. Sin sesión SHALL responder 401. Ningún rechazo SHALL modificar datos.

#### Scenario: Alta con clave derivada
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/categorias` con `{"nombre": "Tren delantero"}`
- **THEN** la respuesta es 201 con `{"clave": "tren-delantero", "nombre": "Tren delantero"}`
- **AND** `GET /api/categorias` la incluye ordenada por nombre

#### Scenario: Clave repetida
- **GIVEN** un cliente con sesión
- **WHEN** envía `POST /api/categorias` con `{"nombre": "Motor diésel", "clave": "Motor"}`
- **THEN** la respuesta es 409 con `detail` "Ya existe una categoría con clave 'motor'."

#### Scenario: Nombre repetido
- **WHEN** un cliente con sesión envía `POST /api/categorias` con `{"nombre": "filtro"}`
- **THEN** la respuesta es 409 con `detail` "Ya existe una categoría con nombre 'filtro'."

#### Scenario: Nombre faltante
- **WHEN** un cliente con sesión envía `POST /api/categorias` con `{}` o `{"nombre": "  "}`
- **THEN** la respuesta es 422 con `detail` "El campo nombre es obligatorio."

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `POST /api/categorias` con un cuerpo válido
- **THEN** la respuesta es 401 y no se crea ninguna categoría

### Requirement: Renombre de categoría por API
`PATCH /api/categorias/{clave}` SHALL exigir sesión, recibir `{"nombre"}`, renombrar según `categorias-productos` y responder 200 con `{"clave", "nombre"}`. SHALL responder 404 si la clave no existe, 409 si el nombre pertenece a otra categoría y 422 ante un nombre inválido o un intento de cambiar la clave. Sin sesión SHALL responder 401.

#### Scenario: Renombrar
- **GIVEN** un cliente con sesión y la categoría `motor` asignada a `M-01`
- **WHEN** envía `PATCH /api/categorias/motor` con `{"nombre": "Motor y transmisión"}`
- **THEN** la respuesta es 200 con `{"clave": "motor", "nombre": "Motor y transmisión"}` y `GET /api/inventario` sigue mostrando `M-01` con `categoria: "motor"`

#### Scenario: Clave en mayúsculas en la ruta
- **WHEN** un cliente con sesión envía `PATCH /api/categorias/MOTOR` con `{"nombre": "Motor"}`
- **THEN** la respuesta es 200 con `clave: "motor"`

#### Scenario: Inexistente
- **WHEN** un cliente con sesión envía `PATCH /api/categorias/frenos` con `{"nombre": "Frenos"}`
- **THEN** la respuesta es 404 con `detail` "No existe una categoría con clave 'frenos'."

#### Scenario: Nombre de otra categoría
- **WHEN** un cliente con sesión envía `PATCH /api/categorias/filtro` con `{"nombre": "Aceite"}`
- **THEN** la respuesta es 409 con `detail` "Ya existe una categoría con nombre 'Aceite'."

#### Scenario: Intento de cambiar la clave
- **WHEN** un cliente con sesión envía `PATCH /api/categorias/filtro` con `{"nombre": "Filtros", "clave": "filtros"}`
- **THEN** la respuesta es 422 con `detail` "La clave de una categoría no se puede cambiar." y nada cambia

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `PATCH /api/categorias/motor` con un cuerpo válido
- **THEN** la respuesta es 401 y nada cambia

### Requirement: Categorías por API
`GET /api/categorias` SHALL exigir sesión y responder 200 con la lista de categorías del catálogo, cada una con exactamente `clave` y `nombre`, ordenada por nombre. El endpoint SHALL NOT modificar datos. Sin sesión SHALL responder 401.

#### Scenario: Categorías de ejemplo
- **GIVEN** un cliente con sesión y una base recién inicializada
- **WHEN** envía `GET /api/categorias`
- **THEN** la respuesta es 200 con `[{"clave": "aceite", "nombre": "Aceite"}, {"clave": "filtro", "nombre": "Filtro"}, {"clave": "motor", "nombre": "Motor"}]`

#### Scenario: Sin sesión
- **WHEN** un cliente sin sesión envía `GET /api/categorias`
- **THEN** la respuesta es 401 y no incluye categorías

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
