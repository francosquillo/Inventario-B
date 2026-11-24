# categorias-productos Specification

## Purpose
Catálogo de categorías de producto (motor, aceite, filtro y las que se agreguen por API), la asignación opcional de una categoría a cada producto y su administración (crear y renombrar) por la API.

## Requirements

### Requirement: Catálogo de categorías
El sistema SHALL mantener un catálogo de categorías de producto, cada una con una clave única (identificador estable: minúsculas, sin tildes, números y guiones, hasta 30 caracteres) y un nombre para mostrar único sin distinguir mayúsculas. Una base nueva SHALL empezar con las categorías de ejemplo `motor` ("Motor"), `aceite` ("Aceite") y `filtro` ("Filtro"). En este paso las categorías SHALL administrarse solo por la API (sin pantalla en la web).

#### Scenario: Categorías de ejemplo
- **GIVEN** una base recién inicializada
- **WHEN** se consulta el catálogo de categorías
- **THEN** contiene exactamente `aceite` "Aceite", `filtro` "Filtro" y `motor` "Motor"

#### Scenario: Orden del listado
- **WHEN** se consulta el catálogo de categorías
- **THEN** las categorías aparecen ordenadas por nombre: "Aceite", "Filtro", "Motor"

### Requirement: Alta de categoría
El alta de una categoría SHALL recibir un nombre obligatorio (recortado, 1 a 40 caracteres) y opcionalmente una clave. Sin clave, la clave SHALL derivarse del nombre: minúsculas, sin tildes, cada tramo de caracteres que no sean letras `a-z` o números pasa a un guion, sin guiones en los bordes, hasta 30 caracteres. Con clave, SHALL normalizarse (recorte + minúsculas) y validarse con el mismo formato. Una clave o un nombre (sin distinguir mayúsculas) ya usados SHALL rechazarse sin crear nada.

#### Scenario: Clave derivada del nombre
- **WHEN** se da de alta la categoría con nombre `"  Tren delantero "`
- **THEN** existe la categoría `tren-delantero` "Tren delantero"

#### Scenario: Clave derivada sin tildes
- **WHEN** se da de alta la categoría con nombre "Encendido / Bujías"
- **THEN** existe la categoría `encendido-bujias` "Encendido / Bujías"

#### Scenario: Clave indicada
- **WHEN** se da de alta la categoría con clave `" Frenos "` y nombre "Sistema de frenos"
- **THEN** existe la categoría `frenos` "Sistema de frenos"

#### Scenario: Clave inválida
- **WHEN** se da de alta una categoría con clave `"fre nos!"` o con un nombre del que no se deriva ninguna letra ni número (por ejemplo `"***"`)
- **THEN** el alta se rechaza con "La clave de la categoría admite solo minúsculas sin tilde, números y guiones (hasta 30 caracteres)." y no se crea nada

#### Scenario: Clave repetida
- **GIVEN** la categoría `motor`
- **WHEN** se da de alta otra con nombre "Motor diésel" y clave `MOTOR`
- **THEN** el alta se rechaza con "Ya existe una categoría con clave 'motor'."

#### Scenario: Nombre repetido
- **GIVEN** la categoría `aceite` "Aceite"
- **WHEN** se da de alta otra con nombre "ACEITE" y clave `lubricante`
- **THEN** el alta se rechaza con "Ya existe una categoría con nombre 'ACEITE'."

#### Scenario: Nombre faltante o largo
- **WHEN** se da de alta una categoría sin nombre, con nombre de solo espacios o con un nombre de 41 caracteres
- **THEN** el alta se rechaza con "El campo nombre es obligatorio." o "El nombre de la categoría admite hasta 40 caracteres."

### Requirement: Renombrar categoría
Renombrar una categoría SHALL cambiar solo su nombre (mismas reglas de nombre que el alta, único sin distinguir mayúsculas entre las demás); su clave SHALL ser inmutable y los productos de la categoría SHALL conservarla. Renombrar con el mismo nombre SHALL aceptarse sin cambios. Una clave inexistente SHALL rechazarse.

#### Scenario: Renombrar
- **GIVEN** la categoría `motor` "Motor" asignada a `M-01`
- **WHEN** se renombra `motor` a "Motor y transmisión"
- **THEN** la categoría `motor` se llama "Motor y transmisión" y `M-01` sigue con la categoría `motor`

#### Scenario: Cambiar solo mayúsculas
- **WHEN** se renombra `aceite` a "ACEITE"
- **THEN** la categoría `aceite` se llama "ACEITE"

#### Scenario: Nombre de otra categoría
- **GIVEN** las categorías `aceite` "Aceite" y `filtro` "Filtro"
- **WHEN** se renombra `filtro` a "aceite"
- **THEN** se rechaza con "Ya existe una categoría con nombre 'aceite'." y nada cambia

#### Scenario: Categoría inexistente
- **WHEN** se renombra `frenos`, que no existe
- **THEN** se rechaza con "No existe una categoría con clave 'frenos'."

### Requirement: Categoría opcional por producto
Cada producto SHALL tener a lo sumo una categoría del catálogo o ninguna ("Sin categoría"). Un producto sin categoría SHALL comportarse igual que cualquier otro en stock, órdenes, bajas, reintegros y reportes.

#### Scenario: Producto sin categoría
- **GIVEN** el producto activo `A-01` sin categoría
- **WHEN** se consulta el inventario
- **THEN** `A-01` aparece con categoría vacía (`null`)

#### Scenario: Producto con categoría
- **GIVEN** el producto activo `F-01` "Filtro de aceite" con categoría `filtro`
- **WHEN** se consulta el inventario
- **THEN** `F-01` aparece con categoría `filtro`

#### Scenario: La categoría no afecta las órdenes
- **GIVEN** `F-01` (categoría `filtro`, stock 5) y `A-01` (sin categoría, stock 5)
- **WHEN** se crea una orden con `F-01` x 2 y `A-01` x 1
- **THEN** la orden se crea igual que antes de existir las categorías y el stock queda en 3 y 4

### Requirement: Clave de categoría normalizada
La categoría indicada en un alta o una modificación de producto SHALL normalizarse recortando espacios y pasando a minúsculas antes de buscarla en el catálogo. Un valor de texto vacío o de solo espacios SHALL tratarse como "sin categoría". Una clave que no existe en el catálogo SHALL rechazarse con "La categoría 'x' no existe." (x = la clave normalizada) sin modificar datos; un valor que no sea texto ni nulo SHALL rechazarse con "El campo categoria debe ser texto.".

#### Scenario: Mayúsculas y espacios
- **WHEN** se da de alta `F-02` "Filtro de aire" con stock 1 y categoría `"  Filtro "`
- **THEN** `F-02` queda con categoría `filtro`

#### Scenario: Categoría inexistente
- **WHEN** se da de alta `X-01` "Bujía" con stock 1 y categoría `"encendido"`
- **THEN** el alta se rechaza con "La categoría 'encendido' no existe." y no se crea `X-01`

#### Scenario: Texto vacío
- **WHEN** se da de alta `X-02` "Bujía" con stock 1 y categoría `"   "`
- **THEN** `X-02` queda sin categoría
