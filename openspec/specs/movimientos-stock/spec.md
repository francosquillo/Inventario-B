# movimientos-stock Specification

## Purpose

Permite a un usuario autenticado mantener el stock al día ingresando y egresando unidades por código interno, dando de alta o reactivando productos al ingresar, y dejando cada operación registrada en la bitácora de movimientos de forma atómica, con la fecha y hora local de Argentina.

## Requirements


### Requirement: Ingreso suma stock a un producto activo
Un ingreso con el código de un producto activo SHALL sumar la cantidad a su stock y conservar su nombre, aunque el ingreso traiga un nombre distinto.

#### Scenario: Suma sobre producto existente
- **GIVEN** el producto activo `A-01` "Tornillo M4" con stock 5
- **WHEN** se ingresan 3 unidades con el código `A-01`
- **THEN** el stock de `A-01` es 8

#### Scenario: Suma sobre producto con stock cero
- **GIVEN** el producto activo `B-10` con stock 0
- **WHEN** se ingresan 4 unidades con el código `B-10`
- **THEN** el stock de `B-10` es 4 y deja de figurar sin stock

#### Scenario: Nombre recibido para un código existente
- **GIVEN** el producto activo `A-01` "Tornillo M4" con stock 5
- **WHEN** se ingresan 2 unidades con el código `A-01` y el nombre "Otro nombre"
- **THEN** el stock de `A-01` es 7 y su nombre sigue siendo "Tornillo M4"

### Requirement: Ingreso crea un producto nuevo
Un ingreso con un código inexistente y un nombre no vacío SHALL crear un producto activo con ese código (normalizado), ese nombre y la cantidad ingresada como stock.

#### Scenario: Alta por ingreso
- **GIVEN** que no existe ningún producto con código `N-01`
- **WHEN** se ingresan 10 unidades con el código `N-01` y el nombre "Arandela 6mm"
- **THEN** existe el producto activo `N-01` "Arandela 6mm" con stock 10
- **AND** aparece en el inventario general

### Requirement: Producto nuevo exige nombre
Un ingreso con un código inexistente sin nombre, o con un nombre vacío o de solo espacios, SHALL rechazarse con un mensaje claro sin crear el producto ni registrar movimientos.

#### Scenario: Código nuevo sin nombre
- **GIVEN** que no existe ningún producto con código `N-02`
- **WHEN** se ingresan 5 unidades con el código `N-02` sin nombre
- **THEN** el ingreso se rechaza indicando que el producto no existe y requiere nombre
- **AND** no existe el producto `N-02` y no se registró ningún movimiento

#### Scenario: Código nuevo con nombre de solo espacios
- **GIVEN** que no existe ningún producto con código `N-03`
- **WHEN** se ingresan 5 unidades con el código `N-03` y el nombre "   "
- **THEN** el ingreso se rechaza y no existe el producto `N-03`

### Requirement: Ingreso reactiva un producto inactivo
Un ingreso con el código de un producto inactivo (dado de baja) SHALL reactivarlo y sumar la cantidad a su stock, conservando su código y su nombre, sin crear un producto nuevo.

#### Scenario: Reactivación
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se ingresan 3 unidades con el código `C-99`
- **THEN** `C-99` queda activo con stock 5 y nombre "Junta"
- **AND** sigue existiendo un único producto con código `C-99`
- **AND** `C-99` aparece en el inventario general

### Requirement: Egreso manual descuenta stock
Un egreso con el código de un producto activo y una cantidad menor o igual a su stock SHALL descontar esa cantidad. Un producto que llega a stock 0 SHALL seguir existiendo y activo.

#### Scenario: Egreso parcial
- **GIVEN** el producto activo `A-01` con stock 8
- **WHEN** se egresan 3 unidades con el código `A-01`
- **THEN** el stock de `A-01` es 5

#### Scenario: Egreso de todo el stock
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se egresan 5 unidades con el código `A-01`
- **THEN** el stock de `A-01` es 0, el producto sigue activo y figura sin stock en el inventario

### Requirement: Egreso que excede el stock se rechaza
Un egreso cuya cantidad supere el stock actual SHALL rechazarse indicando el stock disponible, sin modificar el stock ni registrar movimientos. El stock nunca SHALL quedar negativo.

#### Scenario: Exceso
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intentan egresar 6 unidades con el código `A-01`
- **THEN** el egreso se rechaza indicando que el stock disponible es 5
- **AND** el stock de `A-01` sigue en 5 y no se registró ningún movimiento

#### Scenario: Egreso sobre stock cero
- **GIVEN** el producto activo `B-10` con stock 0
- **WHEN** se intenta egresar 1 unidad con el código `B-10`
- **THEN** el egreso se rechaza y el stock de `B-10` sigue en 0

### Requirement: Egreso solo sobre productos activos existentes
Un egreso con un código inexistente o de un producto inactivo SHALL rechazarse indicando que el producto no existe, sin modificar datos.

#### Scenario: Código inexistente
- **GIVEN** que no existe ningún producto con código `X-00`
- **WHEN** se intenta egresar 1 unidad con el código `X-00`
- **THEN** el egreso se rechaza indicando que el producto no existe y no se registró ningún movimiento

#### Scenario: Producto inactivo
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se intenta egresar 1 unidad con el código `C-99`
- **THEN** el egreso se rechaza indicando que el producto no existe
- **AND** `C-99` sigue inactivo con stock 2

### Requirement: Cantidades enteras positivas
Ingresos y egresos SHALL aceptar solo cantidades enteras de 1 a 10.000 por operación; cualquier otra cantidad SHALL rechazarse con el mensaje "La cantidad debe ser un entero entre 1 y 10.000." sin modificar datos.

#### Scenario: Cantidad cero o negativa
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta ingresar o egresar 0 o -1 unidades con el código `A-01`
- **THEN** la operación se rechaza y el stock de `A-01` sigue en 5

#### Scenario: Cantidad no entera
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta ingresar 2.5 unidades, o la cantidad como texto `"5"`
- **THEN** la operación se rechaza y el stock de `A-01` sigue en 5

#### Scenario: Cantidad máxima aceptada
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se ingresan 10.000 unidades con el código `A-01`
- **THEN** el stock de `A-01` es 10.005

#### Scenario: Cantidad por encima del máximo
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta ingresar 10.001 unidades con el código `A-01`
- **THEN** la operación se rechaza y el stock de `A-01` sigue en 5

### Requirement: Código y nombre normalizados
El código SHALL recortarse de espacios al inicio y al final y convertirse a MAYÚSCULAS antes de validar, buscar y guardar, de modo que códigos que solo difieren en mayúsculas/minúsculas o espacios identifican al mismo producto. Un código vacío o de solo espacios SHALL rechazarse. El código admite hasta 50 caracteres (medidos tras normalizar). El nombre SHALL recortarse de espacios (sin cambiar mayúsculas) y admite hasta 120 caracteres. Los productos existentes se asumen con código en mayúsculas.

#### Scenario: Código con espacios alrededor
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se ingresan 2 unidades con el código `"  A-01  "`
- **THEN** el stock de `A-01` es 7 y no se crea otro producto

#### Scenario: Código de solo espacios
- **WHEN** se intenta ingresar o egresar con el código `"   "`
- **THEN** la operación se rechaza sin modificar datos

#### Scenario: Minúsculas encuentran el producto existente
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se egresa 1 unidad con el código `" a-01 "`
- **THEN** el stock de `A-01` es 4 y no existe ningún producto `a-01`

#### Scenario: Alta en minúsculas se guarda en mayúsculas
- **GIVEN** que no existe ningún producto `RD-6204`
- **WHEN** se ingresan 4 unidades con el código `rd-6204` y el nombre "Rodamiento 6204"
- **THEN** existe el producto activo `RD-6204` "Rodamiento 6204" con stock 4

#### Scenario: Variantes de mayúsculas no duplican productos
- **GIVEN** que no existe ningún producto `RD-6204`
- **WHEN** se ingresan 4 unidades con el código `rd-6204` y el nombre "Rodamiento 6204" y luego 2 unidades con el código `Rd-6204`
- **THEN** existe un único producto `RD-6204` con stock 6
- **AND** hay dos movimientos de ingreso asociados a ese producto

#### Scenario: Nombre recortado al crear
- **WHEN** se ingresan 3 unidades con el código nuevo `N-04` y el nombre `"  Buje  "`
- **THEN** el producto `N-04` queda con el nombre "Buje"

### Requirement: Registro de movimientos sin motivo
Cada ingreso o egreso aceptado SHALL registrar exactamente un movimiento con la fecha y hora local de Argentina (offset fijo UTC-03:00) generada por la aplicación en formato ISO 8601 con segundos y offset (por ejemplo `2026-11-19T15:30:00-03:00`), el producto, el tipo (`ingreso` o `egreso`), la cantidad y el usuario autenticado que lo hizo, sin pedir motivo. El cliente no puede fijar la fecha. Las operaciones rechazadas no registran movimientos.

#### Scenario: Movimiento de ingreso sobre producto existente
- **GIVEN** el usuario `admin` autenticado, el producto activo `A-01` y el reloj de la aplicación en 2026-11-19 15:30:00 hora de Argentina
- **WHEN** ingresa 3 unidades con el código `A-01`
- **THEN** existe un movimiento nuevo de tipo `ingreso`, cantidad 3, producto `A-01`, usuario `admin` y fecha `2026-11-19T15:30:00-03:00`

#### Scenario: Movimiento de alta
- **WHEN** el usuario `admin` ingresa 10 unidades con el código nuevo `N-01` y el nombre "Arandela 6mm"
- **THEN** existe un movimiento de tipo `ingreso`, cantidad 10, asociado al producto `N-01` recién creado

#### Scenario: Movimiento de egreso
- **GIVEN** el producto activo `A-01` con stock 8
- **WHEN** el usuario `admin` egresa 3 unidades con el código `A-01`
- **THEN** existe un movimiento nuevo de tipo `egreso`, cantidad 3, producto `A-01` y usuario `admin`

#### Scenario: Fecha siempre en hora de Argentina
- **GIVEN** que el reloj de la aplicación entrega el instante 2026-11-19 18:30:00 UTC
- **WHEN** se registra un movimiento
- **THEN** su fecha guardada es `2026-11-19T15:30:00-03:00`

### Requirement: Fechas de movimientos en un único formato
Al inicializar la base, los movimientos existentes con fecha en el formato legado `YYYY-MM-DD HH:MM:SS` (UTC) SHALL convertirse a hora local de Argentina con offset (`YYYY-MM-DDTHH:MM:SS-03:00`). La conversión SHALL ser idempotente y no tocar filas ya normalizadas.

#### Scenario: Fila legada normalizada
- **GIVEN** una base existente con un movimiento de fecha `2026-11-19 18:30:00`
- **WHEN** se inicializa la base
- **THEN** la fecha de ese movimiento es `2026-11-19T15:30:00-03:00`

#### Scenario: Inicialización repetida
- **GIVEN** una base con movimientos ya normalizados
- **WHEN** se inicializa la base dos veces
- **THEN** las fechas de los movimientos no cambian

### Requirement: Stock y movimiento atómicos
La actualización del stock (incluidos el alta y la reactivación) y el registro de su movimiento SHALL ocurrir como una sola operación todo o nada: si cualquiera de las dos partes falla, ninguna queda aplicada.

#### Scenario: Falla al registrar el movimiento de un ingreso
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se ingresan 3 unidades y el registro del movimiento falla
- **THEN** el stock de `A-01` sigue en 5 y no hay movimiento nuevo

#### Scenario: Falla al registrar el movimiento de un alta
- **GIVEN** que no existe el producto `N-05`
- **WHEN** se ingresan unidades con el código `N-05` y un nombre, y el registro del movimiento falla
- **THEN** no existe el producto `N-05`

#### Scenario: Falla al registrar el movimiento de un egreso
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se egresan 2 unidades y el registro del movimiento falla
- **THEN** el stock de `A-01` sigue en 5

#### Scenario: Egresos concurrentes
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** dos egresos de 3 unidades cada uno se procesan a la vez
- **THEN** exactamente uno se acepta, el otro se rechaza por stock insuficiente, el stock final es 2 y hay un solo movimiento de egreso
