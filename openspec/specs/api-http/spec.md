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
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso y egreso de stock, consulta de movimientos, alta, listado y borrado de órdenes y baja de productos reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las diez rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}` y `/api/productos/{codigo}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`

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
`POST /api/ordenes` SHALL recibir `numero`, `fecha` y `componentes` (lista de `{codigo, cantidad}`), crear la orden según `ordenes-trabajo` con el usuario de la sesión y responder 201 con `id`, `numero`, `fecha`, `usuario` y `componentes` (cada uno con `codigo`, `nombre` y `cantidad` consolidada, ordenados por código). Sin sesión SHALL responder 401 sin modificar datos.

#### Scenario: Orden creada
- **GIVEN** un cliente con sesión de `admin` y los productos activos `A-01` "Tornillo" con stock 5 y `B-02` "Tuerca" con stock 10
- **WHEN** envía `POST /api/ordenes` con `{"numero": "ot-0001", "fecha": "2026-11-20", "componentes": [{"codigo": "b-02", "cantidad": 4}, {"codigo": "A-01", "cantidad": 2}, {"codigo": "B-02", "cantidad": 1}]}`
- **THEN** la respuesta es 201 con `numero: "OT-0001"`, `fecha: "2026-11-20"`, `usuario: "admin"`, un `id` entero y `componentes` igual a `[{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}]`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3 y `B-02` con stock 5
- **AND** `GET /api/movimientos` no muestra movimientos nuevos

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
`GET /api/ordenes` SHALL aceptar los parámetros de consulta opcionales `numero`, `desde` y `hasta`, aplicar la consulta según `consulta-ordenes` y responder 200 con una lista sin paginar ni envolver de órdenes con exactamente `id`, `numero`, `fecha` (`YYYY-MM-DD`), `usuario` y `componentes` (cada uno con exactamente `codigo`, `nombre` y `cantidad`, ordenados por código), de la más nueva a la más vieja.

#### Scenario: Listado sin filtros
- **GIVEN** un cliente con sesión de `admin` que creó la orden `OT-0001` con fecha `2026-11-20` y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2
- **WHEN** envía `GET /api/ordenes`
- **THEN** la respuesta es 200 con una lista que contiene `{"id": <entero>, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5}]}`
- **AND** el `id` es el mismo que devolvió el alta

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
`DELETE /api/ordenes/{numero}?reintegrar=true|false` SHALL borrar la orden según `ordenes-trabajo`, identificándola por su número normalizado (los caracteres `?` y `#` deben ir codificados en la URL) y responder 200 con `orden` (misma forma que el alta: `id`, `numero`, `fecha`, `usuario`, `componentes`), `reintegrado` (booleano) y `reintegros` (lista de `{codigo, nombre, cantidad, stock, reactivado}` ordenada por código; vacía sin reintegro).

#### Scenario: Borrado con reintegro
- **GIVEN** un cliente con sesión de `admin`, `A-01` "Tornillo" activo con stock 3, `C-99` "Arandela" dado de baja con stock 1 y la orden `OT-0001` del 2026-11-20 con `A-01` x 2 y `C-99` x 4 (creada con id 1)
- **WHEN** envía `DELETE /api/ordenes/ot-0001?reintegrar=true`
- **THEN** la respuesta es 200 con `{"orden": {"id": 1, "numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin", "componentes": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4}]}, "reintegrado": true, "reintegros": [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "stock": 5, "reactivado": false}, {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "stock": 5, "reactivado": true}]}`
- **AND** `GET /api/ordenes` ya no incluye `OT-0001` y `GET /api/inventario` muestra `A-01` y `C-99` con stock 5

#### Scenario: Borrado sin reintegro
- **GIVEN** un cliente con sesión, `A-01` con stock 3 y la orden `OT-0001` con `A-01` x 2
- **WHEN** envía `DELETE /api/ordenes/OT-0001?reintegrar=false`
- **THEN** la respuesta es 200 con la orden, `"reintegrado": false` y `"reintegros": []`
- **AND** `GET /api/inventario` muestra `A-01` con stock 3

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
`GET /inventario` y `GET /ordenes` SHALL responder 200 con su página HTML cuando la sesión sea válida y SHALL redirigir con 303 a `/` cuando no lo sea, sin incluir datos del inventario ni de las órdenes en ningún caso (los datos llegan solo por `/api/...`).

#### Scenario: Inventario con sesión
- **GIVEN** un cliente que inició sesión
- **WHEN** envía `GET /inventario`
- **THEN** la respuesta es 200 con `Content-Type` `text/html`

#### Scenario: Órdenes con sesión
- **GIVEN** un cliente que inició sesión
- **WHEN** envía `GET /ordenes`
- **THEN** la respuesta es 200 con `Content-Type` `text/html`

#### Scenario: Sin sesión redirige al login
- **WHEN** un cliente sin sesión envía `GET /inventario` o `GET /ordenes`
- **THEN** la respuesta es 303 con `Location` `/`

#### Scenario: La página no embebe datos
- **GIVEN** un cliente con sesión y el producto activo `A-01` "Tornillo"
- **WHEN** envía `GET /inventario`
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
- **THEN** el esquema lista exactamente las diez rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes` ni `/static`

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
Como defensa CSRF, los endpoints que reciben cuerpo (`POST /api/login`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/ordenes`) SHALL responder 422 sin efectos cuando el `Content-Type` no sea JSON (por ejemplo `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`), aunque el cuerpo contenga JSON válido.

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

### Requirement: Sin acceso entre orígenes
La aplicación SHALL NOT habilitar CORS: ninguna respuesta SHALL incluir cabeceras `Access-Control-Allow-*`, y una petición de verificación previa (`OPTIONS` con `Origin` y `Access-Control-Request-Method`) a una ruta `/api/...` SHALL NOT responder con éxito.

#### Scenario: Preflight de un DELETE desde otro origen
- **WHEN** se envía `OPTIONS /api/ordenes/OT-0001` con `Origin: http://evil.example` y `Access-Control-Request-Method: DELETE`
- **THEN** la respuesta no es 2xx y no incluye `Access-Control-Allow-Origin`

#### Scenario: Petición con Origin ajeno
- **GIVEN** un cliente con sesión
- **WHEN** envía `GET /api/inventario` con `Origin: http://evil.example`
- **THEN** la respuesta no incluye `Access-Control-Allow-Origin` ni `Access-Control-Allow-Credentials`
