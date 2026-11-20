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
`GET /api/inventario` SHALL devolver 200 con la lista JSON de productos activos ordenados por código, cada uno con `codigo`, `nombre`, `stock` y `sin_stock` (`true` si el stock es 0), o una lista vacía cuando no haya productos activos. Sin sesión válida SHALL responder 401 sin datos.

#### Scenario: Listado con stock cero
- **GIVEN** un cliente con sesión y los productos activos `B-10` (stock 0) y `A-01` (stock 5), más `C-99` inactivo
- **WHEN** envía `GET /api/inventario`
- **THEN** la respuesta es 200 con `A-01` (`sin_stock: false`) seguido de `B-10` (`sin_stock: true`) y sin `C-99`

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
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso y egreso de stock y consulta de movimientos reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista los siete endpoints `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso` y `/api/movimientos`

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
`GET /api/movimientos` SHALL aceptar los parámetros de consulta opcionales `codigo`, `desde` y `hasta`, aplicar la consulta según `consulta-movimientos` y responder 200 con una lista sin paginar de objetos con exactamente `fecha` (ISO 8601 con offset `-03:00`), `codigo`, `nombre`, `tipo`, `cantidad` y `usuario` (nombre de usuario), del más nuevo al más viejo.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión y un ingreso de 3 unidades de `A-01` "Tornillo M4" hecho por `admin` el `2026-11-19T15:30:00-03:00`
- **WHEN** envía `GET /api/movimientos`
- **THEN** la respuesta es 200 con una lista que contiene `{"fecha": "2026-11-19T15:30:00-03:00", "codigo": "A-01", "nombre": "Tornillo M4", "tipo": "ingreso", "cantidad": 3, "usuario": "admin"}`

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
Toda respuesta 422 de la API, venga de la validación del cuerpo/parámetros o del dominio, SHALL tener la forma `{"detail": "<mensaje>"}` con un único texto legible en español que nombra el campo como aparece en la API (`codigo`, `nombre`, `cantidad`, `username`, `password`, `desde`, `hasta`).

#### Scenario: Campo faltante
- **WHEN** se envía `POST /api/stock/egreso` con sesión y `{"codigo": "A-01"}`
- **THEN** la respuesta es 422 con `detail` "El campo cantidad es obligatorio."

#### Scenario: JSON mal formado
- **WHEN** se envía `POST /api/login` con el cuerpo de texto `{"username": "admin",` y `Content-Type: application/json`
- **THEN** la respuesta es 422 con `detail` "El cuerpo de la petición no es JSON válido."

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
- **THEN** la respuesta 422 de `/api/login`, `/api/stock/ingreso`, `/api/stock/egreso` y `/api/movimientos` referencia un esquema con un único campo `detail` de tipo texto

