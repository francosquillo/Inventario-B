## MODIFIED Requirements

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

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso, egreso y modificación de stock, consulta de movimientos, alta, listado y borrado de órdenes, alta, listado de dados de baja y baja de productos, el reporte de productos en órdenes, la lista de productos usados y el listado, alta y renombre de categorías reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las diecisiete rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/stock/modificaciones`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}`, `/api/productos`, `/api/productos/inactivos`, `/api/productos/{codigo}`, `/api/reportes/productos-en-ordenes`, `/api/reportes/productos-usados`, `/api/categorias` y `/api/categorias/{clave}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`
- **AND** `/api/productos` documenta `POST`, `/api/productos/inactivos` documenta `GET` y `/api/stock/modificaciones` documenta `POST`
- **AND** `/api/reportes/productos-en-ordenes` documenta solo `GET` con los parámetros `desde`, `hasta` y `codigo`, y `/api/reportes/productos-usados` documenta solo `GET`
- **AND** `/api/categorias` documenta solo `GET` y `POST`, y `/api/categorias/{clave}` documenta solo `PATCH`

### Requirement: Rutas de página separadas de la API
Las rutas de página y de estáticos SHALL NOT alterar ninguna respuesta de `/api/...` ni de `/docs`, SHALL NOT figurar en el esquema OpenAPI, y una ruta desconocida (de página o bajo `/api`) SHALL responder 404 con `{"detail": "Not Found"}`.

#### Scenario: OpenAPI sin rutas de página
- **WHEN** se envía `GET /openapi.json`
- **THEN** el esquema lista exactamente las diecisiete rutas `/api/...` de "Documentación interactiva" y ninguna de `/`, `/inventario`, `/ordenes`, `/reportes` ni `/static`

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

### Requirement: Escrituras solo con cuerpo JSON
Como defensa CSRF, los endpoints que reciben cuerpo (`POST /api/login`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/stock/modificaciones`, `POST /api/productos`, `POST /api/ordenes`, `POST /api/categorias` y `PATCH /api/categorias/{clave}`) SHALL responder 422 sin efectos cuando el `Content-Type` no sea JSON (por ejemplo `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`), aunque el cuerpo contenga JSON válido.

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

## ADDED Requirements

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
