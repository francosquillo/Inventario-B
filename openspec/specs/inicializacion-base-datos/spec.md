# inicializacion-base-datos Specification

## Purpose
Garantiza que el sistema arranque sin pasos manuales: crea el esquema completo de datos con sus restricciones y siembra el usuario `admin` inicial, sin duplicar nada en arranques posteriores ni exponer secretos en el código.

## Requirements

### Requirement: Creación del esquema al primer arranque
Al iniciar sobre una base vacía, el sistema SHALL crear las tablas `usuarios`, `productos`, `ordenes`, `orden_items` y `movimientos`, con sus claves primarias, claves foráneas, restricciones de unicidad y restricciones CHECK definidas en el modelo de datos.

#### Scenario: Base nueva
- **WHEN** el sistema se inicializa sobre una base sin tablas
- **THEN** existen las cinco tablas `usuarios`, `productos`, `ordenes`, `orden_items` y `movimientos`

#### Scenario: Unicidad de código de producto
- **GIVEN** una base inicializada con un producto de código `P-001`
- **WHEN** se intenta guardar otro producto con código `P-001`
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
- **WHEN** se intenta guardar un movimiento con tipo distinto de `ingreso` o `egreso`
- **THEN** la base rechaza la escritura

#### Scenario: Integridad referencial activa
- **GIVEN** una base inicializada
- **WHEN** se intenta guardar un movimiento que referencia un producto inexistente
- **THEN** la base rechaza la escritura

### Requirement: Inicialización idempotente
Inicializar el sistema sobre una base ya inicializada SHALL dejar el esquema y los datos existentes intactos, sin errores y sin duplicar registros.

#### Scenario: Segundo arranque
- **GIVEN** una base ya inicializada que contiene el usuario `admin` y productos cargados
- **WHEN** el sistema se inicializa de nuevo
- **THEN** la inicialización termina sin error
- **AND** sigue existiendo exactamente un usuario `admin` con el mismo hash de contraseña
- **AND** los productos existentes no cambian

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
