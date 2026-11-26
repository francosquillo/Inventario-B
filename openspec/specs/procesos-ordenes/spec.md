# procesos-ordenes Specification

## Purpose
Registra los procesos hechos a la lancha en cada orden de trabajo: un catálogo de procesos administrado por la API (con tres de ejemplo) y procesos personalizados de texto libre que quedan solo en la orden que los usa.

## Requirements

### Requirement: Catálogo de procesos
El sistema SHALL mantener un catálogo de procesos, cada uno con una clave única (minúsculas sin tilde, números y guiones, hasta 30 caracteres) y un nombre para mostrar único sin distinguir mayúsculas, de 1 a 60 caracteres. Al crearse el catálogo SHALL contener `cambio-motor` "Cambio motor", `cambio-filtro` "Cambio filtro" y `limpieza` "Limpieza". El catálogo SHALL administrarse solo por la API y listarse ordenado por nombre.

#### Scenario: Procesos de ejemplo
- **GIVEN** una base recién inicializada
- **WHEN** se consulta el catálogo de procesos
- **THEN** contiene, en este orden, `cambio-filtro` "Cambio filtro", `cambio-motor` "Cambio motor" y `limpieza` "Limpieza"

### Requirement: Alta de proceso
El alta de un proceso SHALL recibir un nombre obligatorio (recortado, 1 a 60 caracteres) y opcionalmente una clave; sin clave, la clave SHALL derivarse del nombre con las mismas reglas que las categorías. Una clave o un nombre (sin distinguir mayúsculas) ya usados en el catálogo SHALL rechazarse sin crear nada.

#### Scenario: Clave derivada
- **WHEN** se da de alta el proceso con nombre `"  Pintura del casco "`
- **THEN** existe el proceso `pintura-del-casco` "Pintura del casco"

#### Scenario: Clave inválida
- **WHEN** se da de alta un proceso con clave `"pin tura!"`
- **THEN** se rechaza con "La clave del proceso admite solo minúsculas sin tilde, números y guiones (hasta 30 caracteres)." y no se crea nada

#### Scenario: Nombre repetido
- **WHEN** se da de alta un proceso con nombre "LIMPIEZA"
- **THEN** se rechaza con "Ya existe un proceso con nombre 'LIMPIEZA'."

#### Scenario: Clave repetida
- **WHEN** se da de alta un proceso con nombre "Limpieza profunda" y clave `Limpieza`
- **THEN** se rechaza con "Ya existe un proceso con clave 'limpieza'."

#### Scenario: Nombre faltante o largo
- **WHEN** se da de alta un proceso sin nombre, con solo espacios o con 61 caracteres
- **THEN** se rechaza con "El campo nombre es obligatorio." o "El nombre del proceso admite hasta 60 caracteres."

### Requirement: Renombrar proceso
Renombrar un proceso SHALL cambiar solo su nombre (mismas reglas que el alta, único entre los demás sin distinguir mayúsculas); la clave SHALL ser inmutable. Las órdenes ya creadas SHALL conservar el nombre que tenía el proceso al crearlas. Una clave inexistente SHALL rechazarse.

#### Scenario: Renombrar sin alterar órdenes pasadas
- **GIVEN** la orden `OT-0001` con el proceso "Limpieza"
- **WHEN** se renombra `limpieza` a "Limpieza general"
- **THEN** el catálogo muestra `limpieza` "Limpieza general" y `OT-0001` sigue mostrando "Limpieza"

#### Scenario: Nombre de otro proceso
- **WHEN** se renombra `limpieza` a "cambio motor"
- **THEN** se rechaza con "Ya existe un proceso con nombre 'cambio motor'." y nada cambia

#### Scenario: Proceso inexistente
- **WHEN** se renombra `pintura`, que no existe
- **THEN** se rechaza con "No existe un proceso con clave 'pintura'."

### Requirement: Borrar proceso
Borrar un proceso SHALL quitarlo del catálogo aunque haya órdenes que lo registraron; esas órdenes SHALL conservar el proceso con su nombre. Un proceso borrado SHALL dejar de ofrecerse para nuevas órdenes. Una clave inexistente SHALL rechazarse sin cambios.

#### Scenario: Borrar un proceso usado
- **GIVEN** la orden `OT-0001` con el proceso "Cambio motor"
- **WHEN** se borra `cambio-motor`
- **THEN** el catálogo ya no lo incluye y `OT-0001` sigue mostrando "Cambio motor"

#### Scenario: Borrar inexistente
- **WHEN** se borra `pintura`, que no existe
- **THEN** se rechaza con "No existe un proceso con clave 'pintura'."

### Requirement: Procesos del catálogo en una orden
Una orden SHALL poder registrar cero o más procesos del catálogo, indicados por su clave (recorte + minúsculas). Una clave repetida SHALL contarse una sola vez. Una clave que no existe en el catálogo SHALL rechazar la orden completa con "El proceso 'x' no existe." sin modificar datos.

#### Scenario: Orden sin procesos
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se crea la orden `OT-0001` con `A-01` x 1 y sin procesos
- **THEN** la orden se crea con una lista de procesos vacía

#### Scenario: Varios procesos con uno repetido
- **WHEN** se crea una orden válida con los procesos `"Limpieza"`, `cambio-filtro` y `limpieza`
- **THEN** la orden registra "Limpieza" y "Cambio filtro", una vez cada uno

#### Scenario: Proceso inexistente
- **GIVEN** el producto activo `A-01` con stock 5
- **WHEN** se intenta crear una orden con `A-01` x 1 y el proceso `pintura`, que no existe
- **THEN** se rechaza con "El proceso 'pintura' no existe." y el stock de `A-01` sigue en 5

### Requirement: Procesos personalizados en una orden
Una orden SHALL poder registrar hasta 10 procesos personalizados de texto libre (recortado, 1 a 60 caracteres). No SHALL agregarse al catálogo ni ofrecerse en otras órdenes. Un error SHALL informarse con su posición (desde 1) y sin modificar datos.

#### Scenario: Personalizado solo en su orden
- **WHEN** se crea la orden `OT-0001` con el personalizado `"  Pintura del casco "`
- **THEN** `OT-0001` registra "Pintura del casco" como personalizado y el catálogo de procesos no cambia

#### Scenario: Personalizado vacío o largo
- **WHEN** se intenta crear una orden con los personalizados "Pulido" y `"   "` (o uno de 61 caracteres en la posición 2)
- **THEN** se rechaza con "Proceso personalizado 2: El nombre es obligatorio." o "Proceso personalizado 2: El nombre admite hasta 60 caracteres."

#### Scenario: Demasiados personalizados
- **WHEN** se intenta crear una orden con 11 procesos personalizados
- **THEN** se rechaza con "La orden admite hasta 10 procesos personalizados."

### Requirement: Nombres de procesos sin repetir en una orden
Los nombres de los procesos de una orden SHALL ser distintos sin distinguir mayúsculas. Un personalizado con el nombre de un proceso del catálogo SHALL rechazarse pidiendo elegirlo de la lista, y uno repetido entre personalizados SHALL rechazarse, ambos con su posición y sin modificar datos.

#### Scenario: Personalizado igual a uno del catálogo
- **WHEN** se intenta crear una orden con el personalizado "limpieza"
- **THEN** se rechaza con "Proceso personalizado 1: 'limpieza' ya está en la lista de procesos; marcalo ahí."

#### Scenario: Personalizados repetidos
- **WHEN** se intenta crear una orden con los personalizados "Pulido" y "PULIDO"
- **THEN** se rechaza con "Proceso personalizado 2: 'PULIDO' está repetido."

### Requirement: Orden y nombre de los procesos registrados
Cada proceso registrado en una orden SHALL guardar el nombre que tenía al crearla y si fue personalizado. Los procesos de una orden SHALL devolverse en el orden de carga: primero los del catálogo en el orden indicado y luego los personalizados en el orden indicado.

#### Scenario: Orden de carga
- **WHEN** se crea una orden con los procesos `limpieza` y `cambio-motor` y el personalizado "Pulido"
- **THEN** la orden devuelve "Limpieza" (no personalizado), "Cambio motor" (no personalizado) y "Pulido" (personalizado), en ese orden

### Requirement: Procesos fuera del stock
Registrar procesos en una orden SHALL NOT modificar stock, movimientos ni productos; una orden SHALL seguir requiriendo al menos un componente aunque tenga procesos.

#### Scenario: Orden solo con procesos
- **WHEN** se intenta crear una orden con el proceso `limpieza` y la lista de componentes vacía
- **THEN** se rechaza con "La orden requiere al menos un componente."
