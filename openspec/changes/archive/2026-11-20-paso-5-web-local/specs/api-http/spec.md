# Spec Delta — api-http

## ADDED Requirements

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
