# inicializacion-base-datos Specification

## Purpose
Garantiza que el sistema arranque sin pasos manuales: crea el esquema completo de datos con sus restricciones y siembra el usuario `admin` inicial, sin duplicar nada en arranques posteriores ni exponer secretos en el código.

## Requirements

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
