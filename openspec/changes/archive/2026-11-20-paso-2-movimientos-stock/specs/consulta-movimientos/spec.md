# Spec Delta — consulta-movimientos

## Purpose

Permite a un usuario autenticado consultar la bitácora de movimientos de stock (quién movió qué y cuándo), con filtros opcionales por código de producto y por rango de fechas locales de Argentina.

## ADDED Requirements

### Requirement: Listado de movimientos ordenado
La consulta de movimientos sin filtros SHALL devolver todos los movimientos registrados, ordenados del más nuevo al más viejo por fecha y, ante igual fecha, por orden de registro descendente. Sin movimientos SHALL devolver una lista vacía.

#### Scenario: Orden del más nuevo al más viejo
- **GIVEN** un movimiento de `2026-11-18T09:00:00-03:00`, otro de `2026-11-19T15:30:00-03:00` y otro de `2026-11-17T12:00:00-03:00`
- **WHEN** se consultan los movimientos sin filtros
- **THEN** se obtienen los tres en el orden 2026-11-19, 2026-11-18, 2026-11-17

#### Scenario: Misma fecha
- **GIVEN** dos movimientos registrados con la misma fecha `2026-11-19T15:30:00-03:00`, primero un ingreso y después un egreso
- **WHEN** se consultan los movimientos
- **THEN** el egreso (registrado después) aparece antes que el ingreso

#### Scenario: Sin movimientos
- **GIVEN** que no hay movimientos registrados
- **WHEN** se consultan los movimientos
- **THEN** se obtiene una lista vacía

### Requirement: Datos de cada movimiento
Cada movimiento consultado SHALL incluir su fecha (hora local de Argentina con offset), el código y el nombre del producto, el tipo (`ingreso` o `egreso`), la cantidad y el nombre de usuario que lo registró.

#### Scenario: Movimiento completo
- **GIVEN** que el usuario `admin` ingresó 3 unidades del producto `A-01` "Tornillo M4" el `2026-11-19T15:30:00-03:00`
- **WHEN** se consultan los movimientos
- **THEN** el movimiento tiene fecha `2026-11-19T15:30:00-03:00`, código `A-01`, nombre "Tornillo M4", tipo `ingreso`, cantidad 3 y usuario `admin`

### Requirement: Incluye productos inactivos
La consulta SHALL incluir los movimientos de productos inactivos (dados de baja), porque es historia.

#### Scenario: Producto dado de baja
- **GIVEN** el producto inactivo `C-99` con un movimiento de ingreso registrado antes de su baja
- **WHEN** se consultan los movimientos
- **THEN** el movimiento de `C-99` figura en el resultado

### Requirement: Filtro por código
La consulta SHALL aceptar opcionalmente un código de producto, normalizado igual que en ingresos y egresos (recorte de espacios y MAYÚSCULAS), y devolver solo los movimientos de ese producto (coincidencia exacta). Un código vacío o de solo espacios SHALL tratarse como ausencia de filtro. Un código inexistente SHALL devolver una lista vacía.

#### Scenario: Filtra un producto
- **GIVEN** movimientos de `A-01` y de `B-10`
- **WHEN** se consultan los movimientos con el código `A-01`
- **THEN** solo se obtienen los movimientos de `A-01`

#### Scenario: Código en minúsculas
- **GIVEN** movimientos del producto `RD-6204`
- **WHEN** se consultan los movimientos con el código `" rd-6204 "`
- **THEN** se obtienen los movimientos de `RD-6204`

#### Scenario: Código sin movimientos
- **WHEN** se consultan los movimientos con el código `X-00`, que no existe
- **THEN** se obtiene una lista vacía

### Requirement: Filtro por rango de fechas
La consulta SHALL aceptar opcionalmente `desde` y `hasta` en formato `AAAA-MM-DD`, inclusivos, comparados contra la fecha local (Argentina) del movimiento. Cada uno puede usarse solo. Los filtros de código y de fechas se combinan.

#### Scenario: Rango inclusivo
- **GIVEN** movimientos del `2026-11-17T23:59:59-03:00`, `2026-11-18T00:00:00-03:00`, `2026-11-19T23:59:59-03:00` y `2026-11-20T00:00:00-03:00`
- **WHEN** se consultan los movimientos con `desde` `2026-11-18` y `hasta` `2026-11-19`
- **THEN** se obtienen solo los del 18 a las 00:00:00 y del 19 a las 23:59:59

#### Scenario: Solo desde
- **GIVEN** movimientos del 2026-11-17 y del 2026-11-19
- **WHEN** se consultan los movimientos con `desde` `2026-11-18`
- **THEN** solo se obtiene el del 2026-11-19

#### Scenario: Solo hasta
- **GIVEN** movimientos del 2026-11-17 y del 2026-11-19
- **WHEN** se consultan los movimientos con `hasta` `2026-11-18`
- **THEN** solo se obtiene el del 2026-11-17

#### Scenario: Código y fechas combinados
- **GIVEN** movimientos de `A-01` y de `B-10` el 2026-11-19, y de `A-01` el 2026-11-17
- **WHEN** se consultan los movimientos con el código `A-01` y `desde` `2026-11-18`
- **THEN** solo se obtiene el movimiento de `A-01` del 2026-11-19

### Requirement: Validación de las fechas del filtro
Una fecha de filtro que no tenga formato `AAAA-MM-DD` o que no sea una fecha de calendario válida SHALL rechazarse con un mensaje claro en español. Un `desde` posterior a `hasta` SHALL rechazarse con un mensaje que indique ambas fechas. Una fecha vacía SHALL tratarse como ausencia de filtro.

#### Scenario: Formato inválido
- **WHEN** se consultan los movimientos con `desde` `19/11/2026`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Fecha inexistente
- **WHEN** se consultan los movimientos con `hasta` `2026-02-30`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'hasta' (2026-02-30) no es una fecha válida." (formato correcto pero fecha de calendario inexistente: mensaje distinto al de formato, decisión del usuario 2026-11-19)

#### Scenario: Desde posterior a hasta
- **WHEN** se consultan los movimientos con `desde` `2026-11-20` y `hasta` `2026-11-19`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."
