# Spec Delta — datos-cliente-ordenes

## Purpose

Registra en cada orden de trabajo, de forma opcional, a quién pertenece la embarcación (cliente y celular), qué se trabaja (casco, motor, trailer) y cuándo la embarcación entra y sale del taller (fecha de ingreso y de egreso, aparte de la fecha de la orden).

## ADDED Requirements

### Requirement: Cliente opcional
La orden SHALL poder indicar el cliente (decidido por el usuario, 2026-11-27: opcional): ausente, `null`, vacío o solo espacios = sin cliente; si se indica, texto recortado de hasta 80 caracteres (espacios internos conservados). Más largo SHALL rechazarse con "El cliente admite hasta 80 caracteres."; no texto, con "El campo cliente debe ser texto.", sin modificar datos.

#### Scenario: Cliente recortado
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 1 y cliente `"  Juan  Pérez "`
- **THEN** la orden se guarda con cliente "Juan  Pérez"

#### Scenario: Orden con todos los datos del cliente vacíos
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 1 sin cliente, celular, casco, motor, trailer ni fechas de ingreso y egreso (ausentes, `null` o `"   "`)
- **THEN** la orden se crea sin ninguno de esos datos y el stock de `A-01` es 4

#### Scenario: Cliente largo
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta crear una orden con un cliente de 81 caracteres
- **THEN** se rechaza con "El cliente admite hasta 80 caracteres." y el stock de `A-01` sigue en 5

#### Scenario: Cliente no texto
- **WHEN** se intenta crear una orden con cliente `3`
- **THEN** se rechaza con "El campo cliente debe ser texto."

#### Scenario: Orden anterior sin cliente
- **GIVEN** la orden `OT-0001` creada antes de existir los datos del cliente
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` no tiene cliente, celular, casco, motor, trailer ni fechas de ingreso y egreso

### Requirement: Celular opcional
La orden SHALL poder indicar un celular: opcional (ausente, `null` o vacío = sin celular; validado solo si se carga), recortado, de 6 a 20 caracteres con solo dígitos, espacios, `-`, paréntesis y un `+` inicial, y al menos 6 dígitos. Un celular inválido SHALL rechazarse con "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)." sin modificar datos.

#### Scenario: Celular con formato local
- **WHEN** se crea una orden válida con celular `" +54 9 11 5555-1234 "`
- **THEN** la orden se guarda con celular "+54 9 11 5555-1234"

#### Scenario: Celular inválido
- **WHEN** se intenta crear una orden válida con celular `"11-abc"`, `"12345"` o `"11+5555 1234"`
- **THEN** se rechaza con "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)."

### Requirement: Casco, motor y trailer opcionales
La orden SHALL poder indicar casco, motor y trailer como textos libres opcionales (ausente, `null` o vacío = sin dato), recortados, de hasta 60 caracteres cada uno. Uno más largo SHALL rechazarse con "El campo <casco|motor|trailer> admite hasta 60 caracteres."; uno que no sea texto, con "El campo <casco|motor|trailer> debe ser texto.".

#### Scenario: Datos de la embarcación
- **WHEN** se crea una orden válida con casco "Bermuda 190", motor "Mercury 90 HP" y trailer "AB 123 CD"
- **THEN** la orden se guarda con esos tres datos

#### Scenario: Dato vacío
- **WHEN** se crea una orden válida con casco `"   "` y sin motor ni trailer
- **THEN** la orden se guarda sin casco, motor ni trailer

#### Scenario: Motor largo
- **WHEN** se intenta crear una orden con un motor de 61 caracteres
- **THEN** se rechaza con "El campo motor admite hasta 60 caracteres."

### Requirement: Fecha de ingreso y fecha de egreso
La orden SHALL poder indicar una fecha de ingreso y una fecha de egreso de la embarcación, ambas opcionales (ausente, `null` o vacía = sin fecha) y distintas de la fecha de la orden, que no cambia. Si se indican, SHALL ser `YYYY-MM-DD` reales; con ambas, el egreso SHALL ser igual o posterior al ingreso. Si no: "La fecha de <ingreso|egreso> debe tener formato AAAA-MM-DD.", "La fecha de <ingreso|egreso> (x) no es una fecha válida." o "La fecha de egreso no puede ser anterior a la de ingreso.".

#### Scenario: Solo la fecha obligatoria
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con fecha `2026-11-27`, `A-01` x 1 y sin fecha de ingreso ni de egreso
- **THEN** la orden se crea con fecha `2026-11-27` y sin fecha de ingreso ni de egreso

#### Scenario: Ingreso y egreso
- **WHEN** se crea una orden válida con fecha `2026-11-27`, fecha de ingreso `2026-11-26` y fecha de egreso `2026-11-29`
- **THEN** la orden tiene fecha `2026-11-27`, fecha de ingreso `2026-11-26` y fecha de egreso `2026-11-29`

#### Scenario: Egreso el mismo día del ingreso
- **WHEN** se crea una orden válida con fecha de ingreso y de egreso `2026-11-27`
- **THEN** la orden se crea

#### Scenario: Egreso anterior al ingreso
- **WHEN** se intenta crear una orden con fecha de ingreso `2026-11-27` y fecha de egreso `2026-11-26`
- **THEN** se rechaza con "La fecha de egreso no puede ser anterior a la de ingreso." sin modificar datos

#### Scenario: Solo egreso
- **WHEN** se crea una orden válida con fecha de egreso `2026-11-20` y sin fecha de ingreso
- **THEN** la orden se crea con fecha de egreso `2026-11-20`

#### Scenario: Sin relación con la fecha de la orden
- **WHEN** se crea una orden válida con fecha `2026-11-27`, fecha de ingreso `2026-11-30` y fecha de egreso `2026-12-02`
- **THEN** la orden se crea, porque la fecha de la orden no se compara con el ingreso ni con el egreso

#### Scenario: Fecha inexistente o mal escrita
- **WHEN** se intenta crear una orden con fecha de egreso `2026-02-30` (o fecha de ingreso `30/11/2026`)
- **THEN** se rechaza con "La fecha de egreso (2026-02-30) no es una fecha válida." (o "La fecha de ingreso debe tener formato AAAA-MM-DD.")

#### Scenario: Filtros por la fecha de la orden
- **GIVEN** la orden `OT-0001` con fecha `2026-11-20`, fecha de ingreso `2026-11-24` y fecha de egreso `2026-11-25`
- **WHEN** se consultan las órdenes desde `2026-11-24`
- **THEN** `OT-0001` no aparece, porque los filtros y reportes usan la fecha de la orden

### Requirement: Datos guardados con la orden
Los datos del cliente y la embarcación y las fechas de ingreso y egreso SHALL guardarse en la misma operación todo o nada que la orden y SHALL NOT tocar stock, movimientos, productos ni catálogos.

#### Scenario: Rechazo por stock con datos válidos
- **GIVEN** el producto activo `A-01` con stock 1
- **WHEN** se intenta crear una orden con cliente "Juan Pérez" y `A-01` x 2
- **THEN** se rechaza por stock insuficiente y no existe la orden ni sus datos
