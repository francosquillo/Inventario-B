## ADDED Requirements

### Requirement: Reporte de productos en órdenes por API
`GET /api/reportes/productos-en-ordenes` SHALL exigir sesión, aceptar `desde` (obligatorio), `hasta` (opcional: ausente o vacío = hoy, hora local de Argentina) y `codigo` (opcional), aplicar la consulta según `reporte-ordenes` y responder 200 con una lista sin paginar de objetos con exactamente `codigo`, `nombre`, `activo` (booleano), `cantidad` (suma en el rango) y `ordenes` (órdenes del rango en que aparece), en el orden del reporte. El endpoint SHALL NOT modificar datos.

#### Scenario: Reporte de un mes
- **GIVEN** un cliente con sesión, la orden `OT-0001` del 2026-11-03 con `A-01` "Tornillo" x 3 y `B-02` "Tuerca" x 1, y la orden `OT-0002` del 2026-11-10 con `A-01` x 2
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30`
- **THEN** la respuesta es 200 con `[{"codigo": "A-01", "nombre": "Tornillo", "activo": true, "cantidad": 5, "ordenes": 2}, {"codigo": "B-02", "nombre": "Tuerca", "activo": true, "cantidad": 1, "ordenes": 1}]`

#### Scenario: Sin hasta
- **GIVEN** el mismo estado y la fecha local de Argentina 2026-11-24
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01`
- **THEN** la respuesta es 200 con la misma lista que con `hasta=2026-11-24`

#### Scenario: Filtro por producto
- **GIVEN** el mismo estado
- **WHEN** envía `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30&codigo=b-02`
- **THEN** la respuesta es 200 con solo la fila de `B-02`

#### Scenario: Producto dado de baja
- **GIVEN** `C-99` "Viejo", dado de baja, usado x 2 en una orden del rango
- **WHEN** se consulta el rango
- **THEN** la respuesta incluye `{"codigo": "C-99", "nombre": "Viejo", "activo": false, "cantidad": 2, "ordenes": 1}`

#### Scenario: Filtro por un producto dado de baja
- **GIVEN** el mismo estado
- **WHEN** se consulta el rango con `codigo=c-99`
- **THEN** la respuesta es 200 con solo `{"codigo": "C-99", "nombre": "Viejo", "activo": false, "cantidad": 2, "ordenes": 1}`

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

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso, egreso y modificación de stock, consulta de movimientos, alta, listado y borrado de órdenes, alta, listado de dados de baja y baja de productos el reporte de productos en órdenes y la lista de productos usados reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las quince rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/stock/modificaciones`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}`, `/api/productos`, `/api/productos/inactivos`, `/api/productos/{codigo}`, `/api/reportes/productos-en-ordenes` y `/api/reportes/productos-usados`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`
- **AND** `/api/productos` documenta `POST`, `/api/productos/inactivos` documenta `GET` y `/api/stock/modificaciones` documenta `POST`
- **AND** `/api/reportes/productos-en-ordenes` documenta solo `GET` con los parámetros `desde`, `hasta` y `codigo`, y `/api/reportes/productos-usados` documenta solo `GET`

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

### Requirement: Rutas de página separadas de la API
Las rutas de página y de estáticos SHALL NOT alterar ninguna respuesta de `/api/...` ni de `/docs`, SHALL NOT figurar en el esquema OpenAPI, y una ruta desconocida (de página o bajo `/api`) SHALL responder 404 con `{"detail": "Not Found"}`.

#### Scenario: OpenAPI sin rutas de página
- **WHEN** se envía `GET /openapi.json`
- **THEN** el esquema lista exactamente las quince rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes`, `/reportes` ni `/static`

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
