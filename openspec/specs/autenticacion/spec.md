# autenticacion Specification

## Purpose
Controla el acceso al sistema con usuario y contraseña: protege las contraseñas con hashing con salt por usuario, verifica credenciales en tiempo constante y rechaza intentos inválidos sin revelar qué dato falló.

## Requirements

### Requirement: Almacenamiento de contraseñas con hash y salt
El sistema SHALL guardar cada contraseña como hash PBKDF2-HMAC-SHA256 calculado con un salt aleatorio propio de cada usuario; la contraseña en texto plano nunca SHALL persistirse.

#### Scenario: Hash distinto para la misma contraseña
- **WHEN** se hashea dos veces la misma contraseña
- **THEN** se obtienen salts distintos y hashes distintos

#### Scenario: Verificación correcta
- **GIVEN** un hash y salt generados para la contraseña `s3creta!`
- **WHEN** se verifica `s3creta!` contra ese hash y salt
- **THEN** la verificación es exitosa

#### Scenario: Verificación incorrecta
- **GIVEN** un hash y salt generados para la contraseña `s3creta!`
- **WHEN** se verifica `S3creta!` o una cadena vacía contra ese hash y salt
- **THEN** la verificación falla

### Requirement: Comparación de hashes en tiempo constante
La verificación de contraseña SHALL comparar hashes con una función de comparación en tiempo constante, nunca con igualdad directa de cadenas.

#### Scenario: Verificación usa comparación constante
- **WHEN** se verifica una contraseña contra un hash almacenado
- **THEN** la comparación final se realiza con una comparación en tiempo constante

### Requirement: Login con credenciales válidas
El sistema SHALL autenticar a un usuario cuando el nombre de usuario existe y la contraseña coincide con su hash almacenado, devolviendo la identidad del usuario autenticado (id y username, sin datos de hash).

#### Scenario: Admin con contraseña correcta
- **GIVEN** el usuario `admin` sembrado con contraseña conocida
- **WHEN** se intenta el login con `admin` y esa contraseña
- **THEN** el login es exitoso y devuelve la identidad de `admin`

#### Scenario: Espacios alrededor del usuario
- **GIVEN** el usuario `admin` sembrado con contraseña conocida
- **WHEN** se intenta el login con `  admin  ` y esa contraseña
- **THEN** el login es exitoso

### Requirement: Rechazo genérico de credenciales inválidas
Ante usuario inexistente, contraseña incorrecta o campos vacíos, el sistema SHALL rechazar el login con el mismo mensaje genérico, sin revelar cuál de los datos falló.

#### Scenario: Contraseña incorrecta
- **GIVEN** el usuario `admin` existe
- **WHEN** se intenta el login con `admin` y una contraseña incorrecta
- **THEN** el login falla con el mensaje "Usuario o contraseña incorrectos."

#### Scenario: Usuario inexistente
- **WHEN** se intenta el login con un usuario que no existe
- **THEN** el login falla con el mismo mensaje "Usuario o contraseña incorrectos."

#### Scenario: Campos vacíos
- **WHEN** se intenta el login con usuario o contraseña vacíos
- **THEN** el login falla con el mismo mensaje "Usuario o contraseña incorrectos."

### Requirement: Operaciones solo con sesión válida
El sistema SHALL impedir el acceso a cualquier operación (incluido el inventario) mientras no exista un usuario autenticado.

#### Scenario: Sin login no hay operaciones
- **GIVEN** que ningún usuario inició sesión
- **WHEN** se intenta acceder a una operación del sistema
- **THEN** la operación no se ejecuta y se exige iniciar sesión
