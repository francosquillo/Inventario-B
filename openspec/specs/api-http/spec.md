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
Los endpoints que reciben JSON SHALL rechazar con 422 los cuerpos ausentes, con campos faltantes, con campos vacíos o con tipos incorrectos, sin convertir tipos implícitamente (por ejemplo, un número donde se espera texto, o el texto `"5"` donde se espera un entero).

#### Scenario: Campo faltante
- **WHEN** se envía `POST /api/login` sin el campo `password`
- **THEN** la respuesta es 422

#### Scenario: Campo vacío
- **WHEN** se envía `POST /api/login` con `password` igual a `""`
- **THEN** la respuesta es 422

#### Scenario: Tipo incorrecto
- **WHEN** se envía `POST /api/login` con `username` numérico (por ejemplo `5`)
- **THEN** la respuesta es 422

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, consulta de identidad e inventario reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista `/api/login`, `/api/logout`, `/api/me` y `/api/inventario`
