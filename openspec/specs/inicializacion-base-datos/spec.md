# inicializacion-base-datos Specification

## Purpose
Garantiza que el sistema arranque sin pasos manuales: crea el esquema completo de datos con sus restricciones y siembra el usuario `admin` inicial, sin duplicar nada en arranques posteriores ni exponer secretos en el código.

## Requirements

### Requirement: Creación del esquema al primer arranque
Al iniciar sobre una base vacía, el sistema SHALL crear las tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items` y `movimientos`, con sus claves primarias, claves foráneas, restricciones de unicidad y restricciones CHECK definidas en el modelo de datos, y SHALL sembrar las categorías de ejemplo `motor`, `aceite` y `filtro` solo si el catálogo está vacío.

#### Scenario: Base nueva
- **WHEN** el sistema se inicializa sobre una base sin tablas
- **THEN** existen las seis tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items` y `movimientos`
- **AND** `categorias` contiene `motor`, `aceite` y `filtro`

#### Scenario: Unicidad de código de producto
- **GIVEN** una base inicializada con un producto de código `P-001`
- **WHEN** se intenta guardar otro producto con código `P-001`
- **THEN** la base rechaza la escritura

#### Scenario: Unicidad de clave de categoría
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar otra categoría con clave `motor`
- **THEN** la base rechaza la escritura

#### Scenario: Categoría de producto inexistente
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un producto que referencia una categoría inexistente
- **THEN** la base rechaza la escritura

#### Scenario: Stock negativo rechazado
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un producto con stock `-1`
- **THEN** la base rechaza la escritura

#### Scenario: Cantidad no positiva en ítem de orden o movimiento
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un ítem de orden o un movimiento con cantidad `0`
- **THEN** la base rechaza la escritura

#### Scenario: Tipo de movimiento inválido
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un movimiento con tipo distinto de `ingreso`, `egreso` o `ajuste`
- **THEN** la base rechaza la escritura

#### Scenario: Ajuste coherente
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un `ajuste` sin stock anterior o sin stock nuevo, con ambos iguales, con alguno negativo o con una cantidad distinta de su diferencia absoluta, o un `ingreso`/`egreso` con stock anterior o nuevo
- **THEN** la base rechaza la escritura

#### Scenario: Integridad referencial activa
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un movimiento que referencia un producto inexistente
- **THEN** la base rechaza la escritura

### Requirement: Inicialización idempotente
Inicializar el sistema sobre una base ya inicializada SHALL dejar el esquema y los datos existentes intactos, sin errores y sin duplicar registros, incluidas las categorías sembradas y la categoría asignada a cada producto.

#### Scenario: Segundo arranque
- **GIVEN** una base ya inicializada que contiene el usuario `admin` y productos cargados
- **WHEN** el sistema se inicializa de nuevo
- **THEN** la inicialización termina sin error
- **AND** sigue existiendo exactamente un usuario `admin` con el mismo hash de contraseña
- **AND** los productos existentes no cambian

#### Scenario: Categorías sin duplicar
- **GIVEN** una base inicializada donde `F-01` tiene categoría `filtro`
- **WHEN** el sistema se inicializa dos veces más
- **THEN** `categorias` sigue con una sola fila por clave y `F-01` conserva la categoría `filtro`

#### Scenario: Catálogo administrado no se resiembra
- **GIVEN** una base inicializada donde `motor` se renombró a "Motor y transmisión" y se creó `frenos`
- **WHEN** el sistema se inicializa de nuevo
- **THEN** `motor` sigue llamándose "Motor y transmisión", `frenos` sigue existiendo y no se agrega ni cambia ninguna categoría

### Requirement: Seed del usuario admin con contraseña desde entorno
Si no existe el usuario `admin`, la inicialización SHALL crearlo con la contraseña tomada de la variable de entorno `ADMIN_DEFAULT_PASSWORD`, guardada únicamente como hash con salt. La contraseña nunca SHALL estar escrita en el código ni guardarse en texto plano.

#### Scenario: Variable de entorno definida
- **GIVEN** `ADMIN_DEFAULT_PASSWORD` definida con un valor no vacío
- **WHEN** el sistema se inicializa sobre una base nueva
- **THEN** existe el usuario `admin` y puede iniciar sesión con ese valor
- **AND** la base no contiene ese valor en texto plano

#### Scenario: Variable vacía o solo espacios
- **GIVEN** `ADMIN_DEFAULT_PASSWORD` definida pero vacía o solo con espacios
- **WHEN** el sistema se inicializa sobre una base nueva
- **THEN** el sistema se comporta como si la variable no estuviera definida

### Requirement: Contraseña aleatoria del admin cuando falta la variable
Si `ADMIN_DEFAULT_PASSWORD` no está definida al crear el `admin`, el sistema SHALL generar una contraseña aleatoria criptográficamente segura, crear el `admin` con su hash y comunicarla al operador una única vez durante esa inicialización (en la API, por el log del servidor; ver `api-http`).

#### Scenario: Variable ausente en base nueva
- **GIVEN** `ADMIN_DEFAULT_PASSWORD` no definida
- **WHEN** el sistema se inicializa sobre una base nueva
- **THEN** se comunica al operador una contraseña generada de al menos 16 caracteres
- **AND** el usuario `admin` puede iniciar sesión con esa contraseña

#### Scenario: Contraseña generada no se repite en arranques posteriores
- **GIVEN** una base donde el `admin` ya fue creado con contraseña generada
- **WHEN** el sistema se inicializa de nuevo
- **THEN** no se genera ni se muestra ninguna contraseña
- **AND** la contraseña del `admin` no cambia

### Requirement: Ubicación configurable de la base local
El sistema SHALL usar como archivo de base la ruta indicada en la variable de entorno `INVENTARIO_DB_PATH` y, si no está definida, un archivo `inventario.db` en el directorio de trabajo.

#### Scenario: Ruta definida
- **GIVEN** `INVENTARIO_DB_PATH` apunta a una ruta de archivo
- **WHEN** el sistema arranca
- **THEN** la base se crea y usa en esa ruta

#### Scenario: Ruta no definida
- **GIVEN** `INVENTARIO_DB_PATH` no definida
- **WHEN** el sistema arranca
- **THEN** la base se crea y usa en `inventario.db` del directorio de trabajo

### Requirement: Migración de la bitácora al tipo ajuste
Al inicializar una base cuya tabla `movimientos` no admite el tipo `ajuste`, el sistema SHALL migrarla al esquema vigente en una sola transacción, conservando todas las filas con su id, fecha, producto, tipo, cantidad y usuario. La migración SHALL ser idempotente y, si falla, la base SHALL quedar como estaba.

#### Scenario: Base anterior al cambio
- **GIVEN** una base con el esquema anterior y tres movimientos (dos ingresos y un egreso)
- **WHEN** se inicializa la base
- **THEN** `movimientos` admite el tipo `ajuste` y conserva los tres movimientos con los mismos ids y datos
- **AND** el stock de los productos no cambia

#### Scenario: Inicialización repetida
- **GIVEN** una base ya migrada
- **WHEN** se inicializa la base dos veces más
- **THEN** la tabla y sus filas no cambian y no hay error

#### Scenario: Falla a mitad de la migración
- **GIVEN** una base con el esquema anterior
- **WHEN** la migración falla después de copiar las filas
- **THEN** la tabla `movimientos` sigue con el esquema anterior y todas sus filas, y el arranque informa el error

### Requirement: Migración de productos a categorías
Al inicializar una base cuya tabla `productos` no tiene categoría, el sistema SHALL agregarle la categoría opcional y sembrar las categorías de ejemplo (si el catálogo está vacío) en una sola transacción, conservando todas las filas de `productos`, `ordenes`, `orden_items` y `movimientos`; los productos existentes SHALL quedar sin categoría. La migración SHALL ser idempotente y, si falla, la base SHALL quedar como estaba y el arranque SHALL informar el error.

#### Scenario: Base anterior al cambio
- **GIVEN** una base con el esquema anterior, tres productos (uno dado de baja), una orden con dos componentes y cuatro movimientos
- **WHEN** se inicializa la base
- **THEN** los tres productos conservan id, código, nombre, stock y estado activo, y quedan sin categoría
- **AND** la orden, sus componentes y los cuatro movimientos no cambian
- **AND** existen las categorías `motor`, `aceite` y `filtro`

#### Scenario: Inicialización repetida
- **GIVEN** una base ya migrada en la que luego se asignó la categoría `aceite` a un producto
- **WHEN** se inicializa la base dos veces más
- **THEN** el producto conserva la categoría `aceite`, no se duplican categorías y no hay error

#### Scenario: Falla a mitad de la migración
- **GIVEN** una base con el esquema anterior
- **WHEN** la migración falla después de agregar la categoría a `productos`
- **THEN** `productos` sigue sin categoría y con todas sus filas, no existe una siembra parcial y el arranque informa el error
