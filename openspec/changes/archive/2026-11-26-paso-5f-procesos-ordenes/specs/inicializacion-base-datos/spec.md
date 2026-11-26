# Spec Delta

## MODIFIED Requirements

### Requirement: Creación del esquema al primer arranque
Al iniciar sobre una base vacía, el sistema SHALL crear las tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items`, `movimientos`, `procesos` y `orden_procesos`, con sus claves primarias, claves foráneas, restricciones de unicidad y restricciones CHECK definidas en el modelo de datos, y SHALL sembrar las categorías `motor`, `aceite` y `filtro` y los procesos `cambio-motor`, `cambio-filtro` y `limpieza` solo al crear cada catálogo.

#### Scenario: Base nueva
- **WHEN** el sistema se inicializa sobre una base sin tablas
- **THEN** existen las ocho tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items`, `movimientos`, `procesos` y `orden_procesos`
- **AND** `categorias` contiene `motor`, `aceite` y `filtro`
- **AND** `procesos` contiene `cambio-motor`, `cambio-filtro` y `limpieza`

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

#### Scenario: Categoría en uso no se borra
- **GIVEN** una base inicializada con un producto de categoría `filtro`
- **WHEN** se intenta borrar la categoría `filtro` directamente en la base
- **THEN** la base rechaza la escritura

#### Scenario: Unicidad del catálogo de procesos
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar otro proceso con clave `limpieza` o con nombre "LIMPIEZA"
- **THEN** la base rechaza la escritura

#### Scenario: Proceso de orden inválido
- **GIVEN** una base inicializada con una orden
- **WHEN** se intenta guardar un proceso de esa orden con nombre vacío o de 61 caracteres, o un proceso de una orden inexistente
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
Inicializar el sistema sobre una base ya inicializada SHALL dejar el esquema y los datos existentes intactos, sin errores y sin duplicar registros, incluidas las categorías y procesos del catálogo (aunque se hayan renombrado, borrado o vaciado), la categoría asignada a cada producto y los procesos de cada orden.

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

#### Scenario: Catálogos vaciados no se resiembran
- **GIVEN** una base inicializada donde se borraron todas las categorías y todos los procesos
- **WHEN** el sistema se inicializa dos veces más
- **THEN** `categorias` y `procesos` siguen vacías

#### Scenario: Procesos de órdenes intactos
- **GIVEN** una base inicializada con la orden `OT-0001` con los procesos "Limpieza" y "Pulido"
- **WHEN** el sistema se inicializa de nuevo
- **THEN** `OT-0001` conserva exactamente esos dos procesos

### Requirement: Migración de productos a categorías
Al inicializar una base cuya tabla `productos` no tiene categoría, el sistema SHALL agregarle la categoría opcional y sembrar las categorías de ejemplo (si el catálogo se crea en ese arranque) en una sola transacción, conservando todas las filas de `productos`, `ordenes`, `orden_items` y `movimientos`; los productos existentes SHALL quedar sin categoría. La migración SHALL ser idempotente y, si falla, la base SHALL quedar como estaba y el arranque SHALL informar el error.

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

## ADDED Requirements

### Requirement: Incorporación de procesos a una base existente
Al inicializar una base sin las tablas de procesos, el sistema SHALL crearlas y sembrar el catálogo de procesos en una sola transacción, sin modificar ninguna fila existente; las órdenes existentes SHALL quedar sin procesos. Si falla, la base SHALL quedar sin las tablas nuevas y el arranque SHALL informar el error.

#### Scenario: Base de C-06e
- **GIVEN** una base con el esquema anterior a los procesos, dos órdenes con componentes, productos con categoría y movimientos
- **WHEN** se inicializa la base
- **THEN** existen `procesos` (con los tres de ejemplo) y `orden_procesos` vacía
- **AND** las órdenes, componentes, productos, categorías y movimientos no cambian y cada orden tiene una lista de procesos vacía

#### Scenario: Falla al sembrar
- **GIVEN** una base con el esquema anterior a los procesos
- **WHEN** la siembra de procesos falla
- **THEN** no existen `procesos` ni `orden_procesos`, los datos existentes no cambian y el arranque informa el error
