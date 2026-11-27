# Spec Delta — servicios-generales

## Purpose

Registra el servicio general hecho a la lancha en cada orden de trabajo: un catálogo de servicios con nombre y lista de chequeos incluidos (por ejemplo, "Servicio 20 hs"), administrado por la API y desde la web, del que cada orden puede tomar uno, guardando una copia de su nombre y sus chequeos.

## ADDED Requirements

### Requirement: Catálogo de servicios generales
El sistema SHALL mantener un catálogo de servicios generales, cada uno con una clave única (minúsculas sin tilde, números y guiones, hasta 30 caracteres), un nombre único sin distinguir mayúsculas (1 a 60 caracteres) y una lista ordenada de chequeos. Al crearse el catálogo SHALL contener `servicio-20-hs` "Servicio 20 hs". El catálogo SHALL administrarse por la API y desde la web, y listarse ordenado por nombre.

#### Scenario: Servicio de ejemplo
- **GIVEN** una base recién inicializada
- **WHEN** se consulta el catálogo de servicios generales
- **THEN** contiene solo `servicio-20-hs` "Servicio 20 hs" con los chequeos "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", en ese orden

#### Scenario: Orden por nombre
- **GIVEN** el catálogo con "Servicio 20 hs" y "Servicio 100 hs"
- **WHEN** se consulta el catálogo
- **THEN** se lista primero "Servicio 100 hs" y luego "Servicio 20 hs"

### Requirement: Chequeos de un servicio general
Cada servicio general SHALL tener entre 1 y 30 chequeos, cada uno recortado, de 1 a 60 caracteres y distinto de los demás chequeos del mismo servicio sin distinguir mayúsculas, conservando el orden indicado. Un error SHALL informarse con la posición del chequeo (desde 1) y sin modificar datos.

#### Scenario: Chequeos recortados y en orden
- **WHEN** se da de alta un servicio con los chequeos `"  Chequeo de motor "` y "Chequeo de hélice"
- **THEN** el servicio guarda "Chequeo de motor" y "Chequeo de hélice", en ese orden

#### Scenario: Sin chequeos
- **WHEN** se da de alta un servicio con la lista de chequeos vacía o sin chequeos
- **THEN** se rechaza con "El servicio general requiere al menos un chequeo." y no se crea nada

#### Scenario: Demasiados chequeos
- **WHEN** se da de alta un servicio con 31 chequeos
- **THEN** se rechaza con "El servicio general admite hasta 30 chequeos."

#### Scenario: Chequeo vacío o largo
- **WHEN** se da de alta un servicio con los chequeos "Chequeo de motor" y `"   "` (o uno de 61 caracteres en la posición 2)
- **THEN** se rechaza con "Chequeo 2: El nombre es obligatorio." o "Chequeo 2: El nombre admite hasta 60 caracteres."

#### Scenario: Chequeo repetido
- **WHEN** se da de alta un servicio con los chequeos "Chequeo de motor" y "CHEQUEO DE MOTOR"
- **THEN** se rechaza con "Chequeo 2: 'CHEQUEO DE MOTOR' está repetido."

#### Scenario: Tipo inválido
- **WHEN** se da de alta un servicio con chequeos `"Chequeo de motor"` (texto en lugar de lista) o `[3]`
- **THEN** se rechaza con "El campo chequeos debe ser una lista de textos."

### Requirement: Alta de servicio general
El alta de un servicio general SHALL recibir un nombre obligatorio (recortado, 1 a 60 caracteres), sus chequeos y opcionalmente una clave; sin clave, la clave SHALL derivarse del nombre con las mismas reglas que las categorías y los procesos. Una clave o un nombre (sin distinguir mayúsculas) ya usados SHALL rechazarse sin crear nada.

#### Scenario: Clave derivada
- **WHEN** se da de alta el servicio con nombre `"  Servicio 100 hs "` y el chequeo "Cambio de aceite"
- **THEN** existe el servicio `servicio-100-hs` "Servicio 100 hs" con el chequeo "Cambio de aceite"

#### Scenario: Clave inválida
- **WHEN** se da de alta un servicio con clave `"serv 100!"`
- **THEN** se rechaza con "La clave del servicio general admite solo minúsculas sin tilde, números y guiones (hasta 30 caracteres)." y no se crea nada

#### Scenario: Nombre repetido
- **WHEN** se da de alta un servicio con nombre "SERVICIO 20 HS"
- **THEN** se rechaza con "Ya existe un servicio general con nombre 'SERVICIO 20 HS'."

#### Scenario: Clave repetida
- **WHEN** se da de alta un servicio con nombre "Service veinte" y clave `Servicio-20-HS`
- **THEN** se rechaza con "Ya existe un servicio general con clave 'servicio-20-hs'."

#### Scenario: Nombre faltante o largo
- **WHEN** se da de alta un servicio sin nombre, con solo espacios o con 61 caracteres
- **THEN** se rechaza con "El campo nombre es obligatorio." o "El nombre del servicio general admite hasta 60 caracteres."

### Requirement: Modificar servicio general
Modificar un servicio general SHALL cambiar su nombre, reemplazar la lista completa de sus chequeos, o ambas cosas, en una sola operación todo o nada, con las mismas reglas que el alta; la clave SHALL ser inmutable. Sin nombre ni chequeos SHALL rechazarse. Las órdenes ya creadas SHALL conservar el nombre y los chequeos que tenía el servicio al crearlas. Una clave inexistente SHALL rechazarse.

#### Scenario: Reemplazar chequeos sin alterar órdenes pasadas
- **GIVEN** la orden `OT-0001` con el servicio "Servicio 20 hs" y sus tres chequeos
- **WHEN** se modifica `servicio-20-hs` con los chequeos "Chequeo de motor" y "Chequeo de batería"
- **THEN** el catálogo muestra `servicio-20-hs` con "Chequeo de motor" y "Chequeo de batería"
- **AND** `OT-0001` sigue mostrando "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico"

#### Scenario: Renombrar
- **WHEN** se modifica `SERVICIO-20-HS` con el nombre "Service 20 horas"
- **THEN** el catálogo muestra `servicio-20-hs` "Service 20 horas" con los mismos chequeos

#### Scenario: Chequeos inválidos no cambian nada
- **WHEN** se modifica `servicio-20-hs` con el nombre "Service 20 horas" y los chequeos "A" y "a"
- **THEN** se rechaza con "Chequeo 2: 'a' está repetido." y el nombre y los chequeos siguen iguales

#### Scenario: Nombre de otro servicio
- **GIVEN** el catálogo con "Servicio 20 hs" y "Servicio 100 hs"
- **WHEN** se modifica `servicio-20-hs` con el nombre "servicio 100 HS"
- **THEN** se rechaza con "Ya existe un servicio general con nombre 'servicio 100 HS'." y nada cambia

#### Scenario: Sin cambios pedidos
- **WHEN** se modifica `servicio-20-hs` sin nombre ni chequeos
- **THEN** se rechaza con "Indicá el nombre o los chequeos a modificar."

#### Scenario: Servicio inexistente
- **WHEN** se modifica `servicio-500-hs`, que no existe
- **THEN** se rechaza con "No existe un servicio general con clave 'servicio-500-hs'."

### Requirement: Borrar servicio general
Borrar un servicio general SHALL quitarlo del catálogo junto con sus chequeos aunque haya órdenes que lo registraron; esas órdenes SHALL conservar el servicio con su nombre y sus chequeos. Un servicio borrado SHALL dejar de ofrecerse para nuevas órdenes. Una clave inexistente SHALL rechazarse sin cambios.

#### Scenario: Borrar un servicio usado
- **GIVEN** la orden `OT-0001` con el servicio "Servicio 20 hs"
- **WHEN** se borra `servicio-20-hs`
- **THEN** el catálogo ya no lo incluye y `OT-0001` sigue mostrando "Servicio 20 hs" con sus tres chequeos

#### Scenario: Borrar inexistente
- **WHEN** se borra `servicio-500-hs`, que no existe
- **THEN** se rechaza con "No existe un servicio general con clave 'servicio-500-hs'."

### Requirement: Servicio general de una orden
Una orden SHALL poder registrar cero o un servicio general del catálogo, indicado por su clave (recorte + minúsculas); sin servicio, vacío o nulo SHALL significar "sin servicio general". Una clave que no existe SHALL rechazar la orden completa con "El servicio general 'x' no existe." y un valor que no sea texto con "El campo servicio debe ser texto.", sin modificar datos.

#### Scenario: Orden sin servicio general
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea la orden `OT-0001` con `A-01` x 1 y sin servicio general
- **THEN** la orden se crea sin servicio general

#### Scenario: Orden con servicio general
- **WHEN** se crea una orden válida con el servicio `" Servicio-20-HS "`
- **THEN** la orden registra "Servicio 20 hs" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", en ese orden

#### Scenario: Servicio inexistente
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta crear una orden con `A-01` x 1 y el servicio `servicio-500-hs`, que no existe
- **THEN** se rechaza con "El servicio general 'servicio-500-hs' no existe." y el stock de `A-01` sigue en 5

#### Scenario: Tipo inválido
- **WHEN** se intenta crear una orden válida con el servicio `["servicio-20-hs"]` o `3`
- **THEN** se rechaza con "El campo servicio debe ser texto."

#### Scenario: Servicio inexistente y número duplicado
- **GIVEN** la orden `OT-0001` existente
- **WHEN** se intenta crear otra orden `OT-0001` válida con el servicio `servicio-500-hs`
- **THEN** se rechaza con "El servicio general 'servicio-500-hs' no existe." (datos inválidos antes que número duplicado)

#### Scenario: Servicio inexistente y proceso inexistente
- **WHEN** se intenta crear una orden válida con el servicio `servicio-500-hs` y el proceso `pintura`
- **THEN** se rechaza con "El servicio general 'servicio-500-hs' no existe."

### Requirement: Copia del servicio en la orden
El servicio general registrado en una orden SHALL guardar el nombre y todos los chequeos que tenía el servicio al crear la orden, en el mismo orden. Cambios posteriores en el catálogo SHALL NOT alterarlo.

#### Scenario: Renombrar después de crear la orden
- **GIVEN** la orden `OT-0001` creada con el servicio `servicio-20-hs`
- **WHEN** se renombra `servicio-20-hs` a "Service 20 horas"
- **THEN** `OT-0001` sigue mostrando "Servicio 20 hs"

### Requirement: Servicio general fuera del stock
Registrar un servicio general en una orden SHALL NOT modificar stock, movimientos, productos ni procesos; una orden SHALL seguir requiriendo al menos un componente aunque tenga servicio general.

#### Scenario: Orden solo con servicio
- **WHEN** se intenta crear una orden con el servicio `servicio-20-hs` y la lista de componentes vacía
- **THEN** se rechaza con "La orden requiere al menos un componente."

#### Scenario: Servicio y procesos juntos
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea una orden con `A-01` x 1, el servicio `servicio-20-hs` y el proceso `limpieza`
- **THEN** la orden registra el servicio "Servicio 20 hs" y el proceso "Limpieza", y el stock de `A-01` queda en 4
