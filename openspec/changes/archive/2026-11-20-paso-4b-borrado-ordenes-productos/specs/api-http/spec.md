# Spec Delta — api-http

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Documentación interactiva
La aplicación SHALL publicar la documentación interactiva de la API en `/docs`, desde donde se pueden ejecutar login, logout, consulta de identidad, inventario, ingreso y egreso de stock, consulta de movimientos, alta, listado y borrado de órdenes y baja de productos reutilizando la cookie de sesión.

#### Scenario: Docs disponibles
- **WHEN** se envía `GET /docs`
- **THEN** la respuesta es 200 con la documentación interactiva
- **AND** el esquema OpenAPI lista las diez rutas `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos`, `/api/ordenes`, `/api/ordenes/{numero}` y `/api/productos/{codigo}`
- **AND** `/api/ordenes` documenta las operaciones `GET` (listado) y `POST` (alta)
- **AND** `/api/ordenes/{numero}` documenta la operación `DELETE` con el parámetro de consulta obligatorio `reintegrar` (valores `true` y `false`) y `/api/productos/{codigo}` documenta la operación `DELETE`

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

### Requirement: Formato del 422 en OpenAPI
El esquema OpenAPI SHALL documentar el formato `{"detail": "<texto>"}` para las respuestas 422 de los endpoints con validación.

#### Scenario: Esquema OpenAPI del 422
- **WHEN** se lee `GET /openapi.json`
- **THEN** la respuesta 422 de `/api/login`, `/api/stock/ingreso`, `/api/stock/egreso`, `/api/movimientos`, de `GET` y `POST` `/api/ordenes`, de `DELETE /api/ordenes/{numero}` y de `DELETE /api/productos/{codigo}` referencia un esquema con un único campo `detail` de tipo texto
- **AND** la respuesta 404 de `GET /api/ordenes`, de `DELETE /api/ordenes/{numero}` y de `DELETE /api/productos/{codigo}` referencia ese mismo esquema
- **AND** la respuesta 409 de `POST /api/ordenes` referencia un esquema con `detail` de tipo texto y `faltantes` opcional
