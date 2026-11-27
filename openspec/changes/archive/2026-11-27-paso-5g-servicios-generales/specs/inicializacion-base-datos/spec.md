# Spec Delta — inicializacion-base-datos

## MODIFIED Requirements

### Requirement: Creación del esquema al primer arranque
Al iniciar sobre una base vacía, el sistema SHALL crear las tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items`, `movimientos`, `procesos`, `orden_procesos`, `servicios_generales`, `servicio_chequeos`, `orden_servicio` y `orden_servicio_chequeos`, con sus claves primarias, claves foráneas, restricciones de unicidad y restricciones CHECK definidas en el modelo de datos, y SHALL sembrar las categorías `motor`, `aceite` y `filtro`, los procesos `cambio-motor`, `cambio-filtro` y `limpieza` y el servicio general `servicio-20-hs` con sus tres chequeos solo al crear cada catálogo.

#### Scenario: Base nueva
- **WHEN** el sistema se inicializa sobre una base sin tablas
- **THEN** existen las doce tablas `usuarios`, `categorias`, `productos`, `ordenes`, `orden_items`, `movimientos`, `procesos`, `orden_procesos`, `servicios_generales`, `servicio_chequeos`, `orden_servicio` y `orden_servicio_chequeos`
- **AND** `categorias` contiene `motor`, `aceite` y `filtro`
- **AND** `procesos` contiene `cambio-motor`, `cambio-filtro` y `limpieza`
- **AND** `servicios_generales` contiene `servicio-20-hs` "Servicio 20 hs" con los chequeos "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico"

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

#### Scenario: Unicidad del catálogo de servicios generales
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar otro servicio general con clave `servicio-20-hs` o con nombre "SERVICIO 20 HS"
- **THEN** la base rechaza la escritura

#### Scenario: Chequeo de catálogo inválido
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un chequeo de `servicio-20-hs` con nombre vacío, de 61 caracteres o igual (sin distinguir mayúsculas) a otro chequeo del mismo servicio, o un chequeo de un servicio inexistente
- **THEN** la base rechaza la escritura

#### Scenario: Un solo servicio por orden
- **GIVEN** una base inicializada con una orden que ya tiene servicio general
- **WHEN** se intenta guardar un segundo servicio general para esa orden, o un servicio de una orden inexistente
- **THEN** la base rechaza la escritura

#### Scenario: Chequeo de orden inválido
- **GIVEN** una base inicializada con una orden con servicio general
- **WHEN** se intenta guardar un chequeo de esa orden con nombre vacío o de 61 caracteres, repetido sin distinguir mayúsculas, o un chequeo de una orden sin servicio
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
Inicializar el sistema sobre una base ya inicializada SHALL dejar el esquema y los datos existentes intactos, sin errores y sin duplicar registros, incluidas las categorías, procesos y servicios generales del catálogo (aunque se hayan renombrado, modificado, borrado o vaciado), la categoría asignada a cada producto y los procesos y el servicio general de cada orden.

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
- **GIVEN** una base inicializada donde se borraron todas las categorías, todos los procesos y todos los servicios generales
- **WHEN** el sistema se inicializa dos veces más
- **THEN** `categorias`, `procesos` y `servicios_generales` siguen vacías

#### Scenario: Servicio general modificado no se resiembra
- **GIVEN** una base inicializada donde `servicio-20-hs` quedó con los chequeos "Chequeo de motor" y "Chequeo de batería"
- **WHEN** el sistema se inicializa de nuevo
- **THEN** `servicio-20-hs` conserva exactamente esos dos chequeos

#### Scenario: Procesos de órdenes intactos
- **GIVEN** una base inicializada con la orden `OT-0001` con los procesos "Limpieza" y "Pulido"
- **WHEN** el sistema se inicializa de nuevo
- **THEN** `OT-0001` conserva exactamente esos dos procesos

#### Scenario: Servicio de órdenes intacto
- **GIVEN** una base inicializada con la orden `OT-0001` con el servicio "Servicio 20 hs" y sus tres chequeos
- **WHEN** el sistema se inicializa de nuevo
- **THEN** `OT-0001` conserva exactamente ese servicio y esos tres chequeos

## ADDED Requirements

### Requirement: Incorporación de servicios generales a una base existente
Al inicializar una base sin las tablas de servicios generales, el sistema SHALL crearlas y sembrar el catálogo en una sola transacción, sin modificar ninguna fila existente; las órdenes existentes SHALL quedar sin servicio general. Si falla, la base SHALL quedar sin las tablas nuevas y el arranque SHALL informar el error.

#### Scenario: Base de C-06f
- **GIVEN** una base con el esquema anterior a los servicios generales, dos órdenes con componentes y procesos, productos con categoría y movimientos
- **WHEN** se inicializa la base
- **THEN** existen `servicios_generales` (con `servicio-20-hs` y sus tres chequeos en `servicio_chequeos`), `orden_servicio` vacía y `orden_servicio_chequeos` vacía
- **AND** las órdenes, componentes, procesos, productos, categorías y movimientos no cambian y ninguna orden tiene servicio general

#### Scenario: Falla al sembrar
- **GIVEN** una base con el esquema anterior a los servicios generales
- **WHEN** la siembra de servicios generales falla
- **THEN** no existe ninguna de las cuatro tablas nuevas, los datos existentes no cambian y el arranque informa el error
