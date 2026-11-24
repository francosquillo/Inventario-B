## MODIFIED Requirements

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

## ADDED Requirements

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
