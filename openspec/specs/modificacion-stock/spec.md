# modificacion-stock Specification

## Purpose
Permite a un usuario autenticado corregir el stock de uno o varios productos en una sola operación todo o nada, fijando un valor absoluto o sumando unidades, cambiando opcionalmente el nombre y reactivando los productos dados de baja cuyo stock cambie y quede mayor que 0.

## Requirements

### Requirement: Modificación en lote
Una modificación SHALL recibir de 1 a 100 líneas; cada línea indica el código de un producto existente (activo o dado de baja), un modo (`fijar` o `sumar`) con su valor y, opcionalmente, un nombre nuevo. Cada línea SHALL aplicarse a su producto y el resultado SHALL listar las líneas en el orden recibido.

#### Scenario: Varias líneas
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se modifica `A-01` fijando 12 y `B-10` sumando 4
- **THEN** `A-01` queda con stock 12 y `B-10` con stock 4, y el resultado lista `A-01` y luego `B-10`

#### Scenario: Sin líneas o demasiadas
- **WHEN** se envía una modificación sin líneas o con 101 líneas
- **THEN** se rechaza con "La modificación requiere al menos una línea." o "La modificación admite hasta 100 líneas." y no cambia ningún dato

### Requirement: Fijar el stock en un valor absoluto
En modo `fijar`, el stock del producto SHALL reemplazarse por el valor indicado, un entero de 0 a 10.000; otro valor SHALL rechazarse con "Línea N: El stock debe ser un entero entre 0 y 10.000." (N = posición desde 1).

#### Scenario: Fijar por debajo y por encima
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 9)
- **WHEN** se fija `A-01` en 8 y `B-10` en 0
- **THEN** `A-01` queda con stock 8 y `B-10` con stock 0, figurando sin stock

#### Scenario: Valor inválido
- **WHEN** la línea 2 fija el stock en -1, 10.001 o 2.5
- **THEN** la modificación completa se rechaza con "Línea 2: El stock debe ser un entero entre 0 y 10.000."

### Requirement: Sumar unidades al stock
En modo `sumar`, la cantidad SHALL sumarse al stock actual y SHALL ser un entero de 1 a 10.000; otro valor SHALL rechazarse con "Línea N: La cantidad debe ser un entero entre 1 y 10.000.".

#### Scenario: Suma
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se suma 3 a `A-01`
- **THEN** `A-01` queda con stock 8

#### Scenario: Suma cero
- **WHEN** la línea 1 suma 0
- **THEN** la modificación se rechaza con "Línea 1: La cantidad debe ser un entero entre 1 y 10.000."

### Requirement: Cambio opcional de nombre
Una línea con nombre SHALL reemplazar el nombre del producto por el nombre recortado (hasta 120 caracteres). Sin nombre, con nombre vacío o de solo espacios, o con el mismo nombre, el nombre no cambia. El cambio de nombre no SHALL registrar movimientos.

#### Scenario: Renombrar y fijar
- **GIVEN** el producto activo `A-01` "Tornillo M4" con stock 5
- **WHEN** se fija `A-01` en 5 con el nombre `"  Tornillo M4 x 20  "`
- **THEN** `A-01` se llama "Tornillo M4 x 20", su stock sigue en 5 y no hay movimiento nuevo

#### Scenario: Nombre demasiado largo
- **WHEN** la línea 3 trae un nombre de 121 caracteres
- **THEN** la modificación se rechaza con "Línea 3: El campo nombre admite hasta 120 caracteres."

### Requirement: Modificación reactiva productos dados de baja
Una línea aceptada sobre un producto dado de baja SHALL reactivarlo únicamente si su stock cambia efectivamente (`fijar` en un valor distinto del actual, o `sumar`) y el stock resultante es mayor que 0; en ese caso el resultado SHALL indicar `reactivado: true`. En cualquier otro caso (fijar en 0, fijar el mismo stock o solo cambiar el nombre) el producto SHALL seguir dado de baja, con el stock y el nombre que resulten de la línea, y el resultado SHALL indicar `reactivado: false`.

#### Scenario: Sumar a un producto dado de baja
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se suma 3 a `C-99`
- **THEN** `C-99` queda activo con stock 5, aparece en el inventario y el resultado indica que fue reactivado

#### Scenario: Fijar un valor distinto mayor que cero
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 6
- **THEN** `C-99` queda activo con stock 6, existe un movimiento `ajuste` 2 → 6 y el resultado indica que fue reactivado

#### Scenario: Fijar en cero un producto dado de baja
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 0
- **THEN** `C-99` queda con stock 0 y sigue dado de baja, existe un movimiento `ajuste` 2 → 0, no aparece en el inventario, sigue en la lista de dados de baja y el resultado indica `reactivado: false`

#### Scenario: Fijar el mismo stock en un producto dado de baja
- **GIVEN** el producto inactivo `C-99` con stock 2
- **WHEN** se fija `C-99` en 2
- **THEN** `C-99` sigue dado de baja con stock 2, no hay movimiento nuevo y el resultado indica `reactivado: false`

#### Scenario: Solo cambiar el nombre de un producto dado de baja
- **GIVEN** el producto inactivo `C-99` "Junta" con stock 2
- **WHEN** se fija `C-99` en 2 con el nombre "Junta tórica"
- **THEN** `C-99` sigue dado de baja con nombre "Junta tórica" y stock 2, no hay movimiento nuevo y el resultado indica `reactivado: false`

### Requirement: Línea sin cambios
Una línea que fija el mismo stock que el producto ya tiene, sin cambiar el nombre, sobre un producto activo, SHALL aceptarse sin modificar el producto ni registrar movimientos, y el resultado SHALL mostrar su stock anterior igual al nuevo.

#### Scenario: Mismo stock
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se fija `A-01` en 5
- **THEN** la modificación se acepta, `A-01` sigue con stock 5 y no hay movimiento nuevo

### Requirement: Registro de las modificaciones en la bitácora
Cada línea aceptada SHALL registrar, con la fecha local de Argentina y el usuario autenticado: en `fijar` con stock distinto, un movimiento `ajuste` con stock anterior, stock nuevo y cantidad igual a la diferencia absoluta; en `sumar`, un movimiento `ingreso` con la cantidad sumada. Fijar el mismo stock y renombrar no registran movimiento; la reactivación no registra movimiento por sí misma (solo el del cambio de stock que la origina).

#### Scenario: Ajuste hacia abajo
- **GIVEN** el producto activo `A-01` con stock 7 y el usuario `admin`
- **WHEN** fija `A-01` en 4
- **THEN** existe un movimiento `ajuste` de `A-01` con stock anterior 7, stock nuevo 4, cantidad 3 y usuario `admin`

#### Scenario: Suma como ingreso
- **GIVEN** el producto activo `A-01` con stock 7
- **WHEN** el usuario `admin` suma 2 a `A-01`
- **THEN** existe un movimiento `ingreso` de `A-01` con cantidad 2, sin stock anterior ni nuevo

### Requirement: Código normalizado y producto inexistente
El código de cada línea SHALL normalizarse (recorte + MAYÚSCULAS, hasta 50 caracteres). Si uno o más códigos no corresponden a ningún producto (ni activo ni dado de baja), la modificación completa SHALL rechazarse indicando todos esos códigos.

#### Scenario: Código en minúsculas
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se suma 1 a `" a-01 "`
- **THEN** `A-01` queda con stock 6

#### Scenario: Códigos inexistentes
- **GIVEN** el producto activo `A-01` y ningún producto `Z-01` ni `Z-02`
- **WHEN** se modifica `A-01`, `Z-01` y `Z-02`
- **THEN** la modificación se rechaza con "No existen productos con código: 'Z-01', 'Z-02'." y `A-01` no cambia

### Requirement: Producto repetido en el lote
Un mismo producto (tras normalizar el código) SHALL aparecer en una sola línea; si se repite, la modificación SHALL rechazarse con "Línea N: el producto 'X' ya está en la línea M." (N = la repetición, M = la primera aparición).

#### Scenario: Código repetido
- **WHEN** la línea 1 fija `A-01` en 3 y la línea 3 suma 2 a `a-01`
- **THEN** la modificación se rechaza con "Línea 3: el producto 'A-01' ya está en la línea 1." y no cambia ningún dato

### Requirement: Modificación atómica
Todas las líneas, sus reactivaciones y sus movimientos SHALL aplicarse como una sola operación todo o nada. Los rechazos SHALL evaluarse en este orden: validación de datos (primera línea inválida), producto repetido, códigos inexistentes.

#### Scenario: Una línea falla
- **GIVEN** el producto activo `A-01` con stock 5 y ningún producto `Z-01`
- **WHEN** se fija `A-01` en 9 y se suma 1 a `Z-01`
- **THEN** la modificación se rechaza, `A-01` sigue con stock 5 y no hay movimientos nuevos

#### Scenario: Falla al registrar un movimiento
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 2)
- **WHEN** se fija `A-01` en 9 y se suma 1 a `B-10` y el registro del segundo movimiento falla
- **THEN** `A-01` sigue con stock 5, `B-10` con stock 2 y no hay movimientos nuevos

#### Scenario: Validación antes que inexistencia
- **GIVEN** ningún producto `Z-01`
- **WHEN** la línea 1 suma 1 a `Z-01` y la línea 2 suma 0 a `A-01`
- **THEN** la modificación se rechaza con "Línea 2: La cantidad debe ser un entero entre 1 y 10.000."
