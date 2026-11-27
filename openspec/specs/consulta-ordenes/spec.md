# consulta-ordenes Specification

## Purpose
Permite a un usuario autenticado consultar el historial de órdenes de trabajo con sus componentes, todas o filtradas por rango de fechas de la orden y por número, incluyendo los productos dados de baja.

## Requirements

### Requirement: Listado de órdenes ordenado
La consulta de órdenes sin filtros SHALL devolver todas las órdenes registradas, ordenadas de la más nueva a la más vieja por la fecha de la orden y, ante igual fecha, de la última cargada a la primera. Sin órdenes SHALL devolver una lista vacía.

#### Scenario: Orden por fecha de la orden
- **GIVEN** las órdenes `OT-1` con fecha `2026-11-18`, `OT-2` con fecha `2026-11-20` y `OT-3` con fecha `2026-11-17`
- **WHEN** se consultan las órdenes sin filtros
- **THEN** se obtienen las tres en el orden `OT-2`, `OT-1`, `OT-3`

#### Scenario: Misma fecha
- **GIVEN** dos órdenes con fecha `2026-11-20`, primero cargada `OT-A` y después `OT-B`
- **WHEN** se consultan las órdenes
- **THEN** `OT-B` aparece antes que `OT-A`

#### Scenario: Fecha de la orden y no momento de carga
- **GIVEN** la orden `OT-VIEJA` cargada hoy con fecha `2025-01-15` y la orden `OT-NUEVA` cargada ayer con fecha `2026-11-19`
- **WHEN** se consultan las órdenes
- **THEN** `OT-NUEVA` aparece antes que `OT-VIEJA`

#### Scenario: Sin órdenes
- **GIVEN** que no hay órdenes registradas
- **WHEN** se consultan las órdenes
- **THEN** se obtiene una lista vacía

### Requirement: Datos de cada orden
Cada orden consultada SHALL incluir su identificador, su número, su fecha, el nombre de usuario que la cargó, sus componentes, cada uno con código, nombre y cantidad, ordenados por código, sus procesos, cada uno con el nombre registrado al crearla y si fue personalizado, en el orden de carga (lista vacía si no tiene), y su servicio general, con el nombre y los chequeos registrados al crearla en su orden (ninguno si no tiene).

#### Scenario: Orden completa
- **GIVEN** que `admin` creó la orden `OT-0001` con fecha `2026-11-20` y componentes `B-02` "Tuerca" x 5 y `A-01` "Tornillo" x 2
- **WHEN** se consultan las órdenes
- **THEN** la orden tiene un identificador entero, número `OT-0001`, fecha `2026-11-20`, usuario `admin` y componentes `A-01` "Tornillo" x 2 seguido de `B-02` "Tuerca" x 5

#### Scenario: Orden con procesos
- **GIVEN** la orden `OT-0002` creada con el proceso `limpieza` y el personalizado "Pulido"
- **WHEN** se consultan las órdenes
- **THEN** `OT-0002` tiene los procesos "Limpieza" (no personalizado) y "Pulido" (personalizado), en ese orden

#### Scenario: Orden anterior a los procesos
- **GIVEN** la orden `OT-0001` creada antes de existir los procesos
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` tiene una lista de procesos vacía

#### Scenario: Orden con servicio general
- **GIVEN** la orden `OT-0003` creada con el servicio `servicio-20-hs`
- **WHEN** se consultan las órdenes
- **THEN** `OT-0003` tiene el servicio general "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", en ese orden

#### Scenario: Orden sin servicio general
- **GIVEN** la orden `OT-0001` creada sin servicio general o antes de existir los servicios generales
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` no tiene servicio general

#### Scenario: Servicio general con varios componentes y procesos
- **GIVEN** la orden `OT-0004` con dos componentes, dos procesos y el servicio "Servicio 20 hs"
- **WHEN** se consultan las órdenes
- **THEN** `OT-0004` aparece una sola vez con sus dos componentes, sus dos procesos y su servicio con tres chequeos, sin repetir ninguno

### Requirement: Incluye productos dados de baja
Los componentes de una orden SHALL mostrarse con su código, nombre y cantidad aunque el producto haya sido dado de baja después de crear la orden (RN-PR-04); la consulta SHALL no omitir órdenes ni componentes por el estado del producto.

#### Scenario: Componente de un producto inactivo
- **GIVEN** la orden `OT-0001` con componentes `A-01` "Tornillo" x 2 y `C-99` "Arandela" x 1, y que luego `C-99` quedó inactivo
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` figura con sus dos componentes, incluido `C-99` "Arandela" x 1

### Requirement: Filtro por rango de fechas de la orden
La consulta SHALL aceptar opcionalmente `desde` y `hasta` en formato `AAAA-MM-DD`, inclusivos en ambos extremos, comparados contra la fecha de la orden. Cada uno puede usarse solo: solo `desde` incluye esa fecha en adelante y solo `hasta` hasta esa fecha.

#### Scenario: Rango inclusivo en los bordes
- **GIVEN** órdenes con fechas `2026-11-17`, `2026-11-18`, `2026-11-19` y `2026-11-20`
- **WHEN** se consultan las órdenes con `desde` `2026-11-18` y `hasta` `2026-11-19`
- **THEN** se obtienen solo las del 2026-11-19 y del 2026-11-18, en ese orden

#### Scenario: Un solo día
- **GIVEN** órdenes con fechas `2026-11-18`, `2026-11-19` y `2026-11-20`
- **WHEN** se consultan las órdenes con `desde` `2026-11-19` y `hasta` `2026-11-19`
- **THEN** se obtiene solo la del 2026-11-19

#### Scenario: Solo desde
- **GIVEN** órdenes con fechas `2026-11-17` y `2026-11-19`
- **WHEN** se consultan las órdenes con `desde` `2026-11-18`
- **THEN** solo se obtiene la del 2026-11-19

#### Scenario: Solo hasta
- **GIVEN** órdenes con fechas `2026-11-17` y `2026-11-19`
- **WHEN** se consultan las órdenes con `hasta` `2026-11-18`
- **THEN** solo se obtiene la del 2026-11-17

#### Scenario: Rango sin resultados
- **GIVEN** órdenes con fechas `2026-11-17` y `2026-11-19`
- **WHEN** se consultan las órdenes con `desde` `2026-12-01` y `hasta` `2026-12-31`
- **THEN** se obtiene una lista vacía

### Requirement: Validación de las fechas del filtro de órdenes
Una fecha de filtro sin formato `AAAA-MM-DD` o que no sea una fecha de calendario válida SHALL rechazarse con un mensaje claro en español, el mismo que en la consulta de movimientos. Un `desde` posterior a `hasta` SHALL rechazarse con un mensaje que indique ambas fechas. Una fecha vacía SHALL tratarse como ausencia de filtro.

#### Scenario: Formato inválido
- **WHEN** se consultan las órdenes con `desde` `19/11/2026`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'desde' debe tener formato AAAA-MM-DD."

#### Scenario: Fecha inexistente
- **WHEN** se consultan las órdenes con `hasta` `2026-02-30`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'hasta' (2026-02-30) no es una fecha válida."

#### Scenario: Rango invertido
- **WHEN** se consultan las órdenes con `desde` `2026-11-20` y `hasta` `2026-11-19`
- **THEN** la consulta se rechaza con el mensaje "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."

#### Scenario: Fechas vacías
- **GIVEN** órdenes con fechas `2026-11-17` y `2026-11-19`
- **WHEN** se consultan las órdenes con `desde` y `hasta` vacíos
- **THEN** se obtienen las dos órdenes

### Requirement: Búsqueda por número de orden
La consulta SHALL aceptar opcionalmente un número de orden, normalizado igual que en el alta (recorte y MAYÚSCULAS, hasta 30 caracteres), y devolver solo la orden con ese número exacto. Vacío = sin filtro. Si ninguna orden tiene ese número, SHALL fallar con "No existe una orden con número '<número normalizado>'."; si existe pero queda fuera del rango de fechas, SHALL devolver una lista vacía. Se combina con las fechas.

#### Scenario: Número existente
- **GIVEN** las órdenes `OT-0001` y `OT-0002`
- **WHEN** se consultan las órdenes con el número `OT-0002`
- **THEN** se obtiene solo la orden `OT-0002` con sus componentes

#### Scenario: Número en minúsculas y con espacios
- **GIVEN** la orden `OT-0003`
- **WHEN** se consultan las órdenes con el número `"  ot-0003 "`
- **THEN** se obtiene la orden `OT-0003`

#### Scenario: Número inexistente
- **GIVEN** la orden `OT-0001`
- **WHEN** se consultan las órdenes con el número `ot-9 `
- **THEN** la consulta se rechaza con el mensaje "No existe una orden con número 'OT-9'."

#### Scenario: Coincidencia exacta
- **GIVEN** las órdenes `OT-1` y `OT-10`
- **WHEN** se consultan las órdenes con el número `OT-1`
- **THEN** se obtiene solo `OT-1`

#### Scenario: Número existente fuera del rango
- **GIVEN** la orden `OT-0001` con fecha `2026-11-17`
- **WHEN** se consultan las órdenes con el número `OT-0001` y `desde` `2026-11-18`
- **THEN** se obtiene una lista vacía
- **AND** no se informa orden no encontrada

#### Scenario: Número existente dentro del rango
- **GIVEN** la orden `OT-0001` con fecha `2026-11-17`
- **WHEN** se consultan las órdenes con el número `OT-0001` y `desde` `2026-11-17`
- **THEN** se obtiene solo la orden `OT-0001`

#### Scenario: Número vacío nunca es no encontrado
- **GIVEN** ninguna orden
- **WHEN** se consultan las órdenes con el número `"   "`
- **THEN** se obtiene una lista vacía

#### Scenario: Prioridad de la validación sobre el no encontrado
- **GIVEN** ninguna orden `OT-9`
- **WHEN** se consultan las órdenes con el número `OT-9` y `desde` `19/11/2026`
- **THEN** la consulta se rechaza con el mensaje de formato de `desde`, no con el de orden no encontrada

#### Scenario: Número demasiado largo
- **WHEN** se consultan las órdenes con un número de 31 caracteres
- **THEN** la consulta se rechaza con el mensaje "El campo numero admite hasta 30 caracteres."

### Requirement: Datos del cliente y precios de cada orden
Además de lo indicado en "Datos de cada orden", cada orden consultada SHALL incluir su cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso (cada uno vacío si no lo tiene), el precio de cada componente, de cada proceso y de su servicio general (vacío si no lo tiene), y su subtotal de servicios, subtotal de ítems y total según `precios-ordenes`.

#### Scenario: Orden con datos y precios
- **GIVEN** la orden `OT-0043` creada con cliente "Juan Pérez", celular "11 5555-1234", casco "Bermuda 190", fecha `2026-11-27`, fecha de ingreso `2026-11-26`, fecha de egreso `2026-11-29`, el servicio `servicio-20-hs` a 4500000, el proceso `limpieza` a 1500000 y el componente `A-01` x 2 a 1200000
- **WHEN** se consultan las órdenes
- **THEN** `OT-0043` tiene esos datos, sin motor ni trailer, el servicio "Servicio 20 hs" con precio 4500000, "Limpieza" con precio 1500000, `A-01` x 2 con precio 1200000, subtotal de servicios 6000000, subtotal de ítems 1200000 y total 7200000

#### Scenario: Orden anterior a los precios
- **GIVEN** la orden `OT-0001` creada antes de existir los datos y precios, con un componente y un proceso
- **WHEN** se consultan las órdenes
- **THEN** `OT-0001` no tiene cliente ni otros datos nuevos, su componente y su proceso no tienen precio y sus subtotales y total valen 0

#### Scenario: Copia de los precios
- **GIVEN** la orden `OT-0043` creada con el proceso `limpieza` a 1500000
- **WHEN** se renombra `limpieza` en el catálogo y se vuelven a consultar las órdenes
- **THEN** `OT-0043` sigue teniendo "Limpieza" con precio 1500000
