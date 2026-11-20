# Spec Delta — api-http

## ADDED Requirements

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
Todo endpoint protegido (`GET /api/me`, `GET /api/inventario`, `GET /api/movimientos`, `POST /api/stock/ingreso`, `POST /api/stock/egreso` y `POST /api/ordenes`) SHALL confirmar que el usuario de la sesión existe en la base; si no existe (cookie firmada de un usuario borrado o de una base reseteada), SHALL responder 401 con `detail` "No autenticado.", descartar la sesión y no modificar ningún dato.

#### Scenario: Usuario de la sesión borrado
- **GIVEN** un cliente que inició sesión como `admin` y cuya fila fue borrada de `usuarios`
- **WHEN** envía `POST /api/ordenes` con un cuerpo válido
- **THEN** la respuesta es 401 con `detail` "No autenticado."
- **AND** no se crea ninguna orden y el stock no cambia

#### Scenario: Ingreso y egreso con usuario borrado
- **GIVEN** un cliente con la sesión de un usuario que ya no existe en `usuarios`
- **WHEN** envía `POST /api/stock/ingreso` o `POST /api/stock/egreso` con un cuerpo válido
- **THEN** la respuesta es 401 con `detail` "No autenticado." y no se crean movimientos ni cambia el stock

#### Scenario: Consultas con usuario borrado
- **GIVEN** un cliente con la sesión de un usuario que ya no existe en `usuarios`
- **WHEN** envía `GET /api/me`, `GET /api/inventario` o `GET /api/movimientos`
- **THEN** cada respuesta es 401 con `detail` "No autenticado."

#### Scenario: Usuario recreado con otro id
- **GIVEN** un cliente con la sesión del usuario con id 1, que fue borrado y vuelto a crear con id 999
- **WHEN** envía cualquiera de los seis requests anteriores
- **THEN** la respuesta es 401 con `detail` "No autenticado."

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso y egreso de stock, consulta de movimientos y alta de órdenes reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista los ocho endpoints `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos` y `/api/ordenes`

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

### Requirement: Formato del 422 en OpenAPI
El esquema OpenAPI SHALL documentar el formato `{"detail": "<texto>"}` para las respuestas 422 de los endpoints con validación.

#### Scenario: Esquema OpenAPI del 422
- **WHEN** se lee `GET /openapi.json`
- **THEN** la respuesta 422 de `/api/login`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos` y `/api/ordenes` referencia un esquema con un único campo `detail` de tipo texto
- **AND** la respuesta 409 de `/api/ordenes` referencia un esquema con `detail` de tipo texto y `faltantes` opcional
