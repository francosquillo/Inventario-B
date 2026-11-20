# Spec Delta — api-http

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso y egreso de stock, consulta de movimientos, alta de órdenes y listado de órdenes reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista los ocho endpoints `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos` y `/api/ordenes`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)

### Requirement: Formato del 422 en OpenAPI
El esquema OpenAPI SHALL documentar el formato `{"detail": "<texto>"}` para las respuestas 422 de los endpoints con validación.

#### Scenario: Esquema OpenAPI del 422
- **WHEN** se lee `GET /openapi.json`
- **THEN** la respuesta 422 de `/api/login`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos` y de `GET` y `POST` `/api/ordenes` referencia un esquema con un único campo `detail` de tipo texto
- **AND** la respuesta 404 de `GET /api/ordenes` referencia ese mismo esquema
- **AND** la respuesta 409 de `POST /api/ordenes` referencia un esquema con `detail` de tipo texto y `faltantes` opcional

### Requirement: Sesión de usuario inexistente
Todo endpoint protegido (`GET /api/me`, `GET /api/inventario`, `GET /api/movimientos`, `POST /api/stock/ingreso`, `POST /api/stock/egreso`, `POST /api/ordenes` y `GET /api/ordenes`) SHALL confirmar que el usuario de la sesión existe en la base; si no existe (cookie firmada de un usuario borrado o de una base reseteada), SHALL responder 401 con `detail` "No autenticado.", descartar la sesión y no modificar ningún dato.

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
- **WHEN** envía `GET /api/me`, `GET /api/inventario`, `GET /api/movimientos` o `GET /api/ordenes`
- **THEN** cada respuesta es 401 con `detail` "No autenticado."

#### Scenario: Usuario recreado con otro id
- **GIVEN** un cliente con la sesión del usuario con id 1, que fue borrado y vuelto a crear con id 999
- **WHEN** envía cualquiera de los siete requests anteriores
- **THEN** la respuesta es 401 con `detail` "No autenticado."
