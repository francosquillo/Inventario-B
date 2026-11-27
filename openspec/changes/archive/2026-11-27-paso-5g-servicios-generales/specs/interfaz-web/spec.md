# Spec Delta — interfaz-web

## MODIFIED Requirements

### Requirement: Modal de nueva orden
El modal "Nueva orden" SHALL pedir número, fecha, el servicio general (opcional, según "Servicio general en la nueva orden"), los procesos (opcionales, en líneas, según "Procesos en la nueva orden") y entre 1 y 100 líneas de componente (producto activo y cantidad) que se agregan y quitan; con éxito SHALL enviar `POST /api/ordenes`, cerrarse, recargar el inventario y mostrar "Orden X creada." con un enlace a `/ordenes`. Cada línea SHALL permitir elegir el producto entre todos los activos o filtrarlos por categoría según "Filtro por categoría en la nueva orden" (decisión del usuario, 2026-11-24). La categoría SHALL NOT enviarse a la API ni cambiar la orden creada.

#### Scenario: Orden creada
- **GIVEN** `A-01` con stock 5 y `B-02` con stock 5
- **WHEN** el usuario crea la orden `OT-0001` con fecha `2026-11-20`, `A-01` x 2 y `B-02` x 1
- **THEN** el modal se cierra, la tabla muestra `A-01` con 3 y `B-02` con 4 y se ve "Orden OT-0001 creada."

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar componente" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea
- **AND** con 100 líneas el botón "Agregar componente" queda deshabilitado

#### Scenario: Fecha propuesta
- **WHEN** se abre el modal
- **THEN** la fecha propuesta es la fecha local de hoy en formato `AAAA-MM-DD` y se puede cambiar

#### Scenario: Orden sin procesos
- **WHEN** el usuario crea una orden sin líneas de proceso
- **THEN** la petición envía `"procesos": []` y `"procesos_personalizados": []` y la orden se crea

#### Scenario: Orden sin servicio general
- **WHEN** el usuario crea una orden dejando "Sin servicio general"
- **THEN** la petición envía `"servicio": null` y la orden se crea

### Requirement: Pantalla de órdenes
`/ordenes` SHALL mostrar un enlace "← Inventario", junto al título un botón "Servicios generales" que abre la administración del catálogo (según "Catálogo de servicios generales en la web"), filtros opcionales Desde, Hasta y Número y la lista de `GET /api/ordenes` en el orden de la API con número, fecha, componentes (código, nombre y cantidad, incluidos productos dados de baja), si tiene, una fila "Servicio general:" con su nombre y un elemento por chequeo en el orden de la API y, si tiene, una fila "Procesos:" con un elemento por proceso en el orden de la API; cada orden SHALL tener sus acciones "Exportar PDF" y "Eliminar". Los filtros vacíos SHALL NOT enviarse.

#### Scenario: Todas las órdenes
- **GIVEN** las órdenes `OT-0042` (2026-11-18) y `OT-0041` (2026-11-15)
- **WHEN** se abre `/ordenes`
- **THEN** se listan `OT-0042` y luego `OT-0041` con sus componentes

#### Scenario: Filtro por fechas
- **WHEN** el usuario completa Desde `2026-11-16` y pulsa "Filtrar"
- **THEN** la interfaz llama a `GET /api/ordenes?desde=2026-11-16` y se lista solo `OT-0042`

#### Scenario: Limpiar filtros
- **WHEN** el usuario pulsa "Ver todas"
- **THEN** los filtros se vacían y se listan todas las órdenes

#### Scenario: Exportación por orden
- **GIVEN** las órdenes `OT-0042` y `OT-0041` listadas
- **WHEN** se abre `/ordenes`
- **THEN** cada orden muestra su propio botón "Exportar PDF" junto a "Eliminar", con nombre accesible "Exportar PDF de la orden OT-0042" (y de `OT-0041`)
- **AND** no hay un botón que exporte la lista completa

#### Scenario: Orden con procesos
- **GIVEN** `OT-0042` con los procesos "Cambio motor" y "Pulido" (personalizado) y `OT-0041` sin procesos
- **WHEN** se abre `/ordenes`
- **THEN** `OT-0042` muestra bajo su cabecera "Procesos:" con "Cambio motor" y "Pulido", como texto
- **AND** `OT-0041` no muestra la fila "Procesos:"

#### Scenario: Orden con servicio general
- **GIVEN** `OT-0042` con el servicio "Servicio 20 hs" (chequeos "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico") y el proceso "Limpieza", y `OT-0041` sin servicio general
- **WHEN** se abre `/ordenes`
- **THEN** `OT-0042` muestra bajo su cabecera "Servicio general:" con "Servicio 20 hs" y sus tres chequeos como texto, antes de la fila "Procesos:"
- **AND** `OT-0041` no muestra la fila "Servicio general:"

#### Scenario: Acceso a los servicios generales
- **WHEN** se abre `/ordenes`
- **THEN** junto al título "Órdenes" se ve el botón "Servicios generales"
- **AND** el botón no se imprime al exportar una orden

### Requirement: Exportar una orden a PDF
El botón "Exportar PDF" de una orden en `/ordenes` SHALL exportar, según `exportacion-pdf`, solo esa orden (decisión del usuario, 2026-11-24): encabezado "Orden <número>" y "Fecha: AAAA-MM-DD · N componentes" (sin usuario creador; revisión del usuario, 2026-11-24), luego, si tiene servicio general, un bloque "Servicio general" con su nombre y sus chequeos uno por línea en el orden de la API (decisión del usuario, 2026-11-27), luego la tabla de sus componentes por código, incluidos productos dados de baja, y debajo, si tiene procesos, un bloque "Procesos realizados" con uno por línea en el orden de la API. Las demás órdenes SHALL NOT aparecer.

#### Scenario: Exportar una orden
- **GIVEN** la lista con `OT-0042` (2026-11-18, creada por `admin`, componentes `A-01` x 2 y `B-02` x 1) y `OT-0041`
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0042`
- **THEN** el documento muestra "Orden OT-0042", "Fecha: 2026-11-18 · 2 componentes", `A-01` x 2 y `B-02` x 1
- **AND** no muestra "Creada por" ni `admin`
- **AND** no muestra `OT-0041`

#### Scenario: Exportar una orden con procesos
- **GIVEN** `OT-0042` con los procesos "Cambio motor" y "Pulido"
- **WHEN** el usuario exporta `OT-0042`
- **THEN** debajo de la tabla de componentes se ve "Procesos realizados" con "Cambio motor" y "Pulido", uno por línea
- **AND** el encabezado sigue siendo "Orden OT-0042" y "Fecha: 2026-11-18 · 2 componentes"

#### Scenario: Exportar una orden con servicio general
- **GIVEN** `OT-0042` con el servicio "Servicio 20 hs" y el proceso "Limpieza"
- **WHEN** el usuario exporta `OT-0042`
- **THEN** justo después del encabezado y antes de la tabla de componentes se ve el bloque "Servicio general" con "Servicio 20 hs" y "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", uno por línea
- **AND** luego se ve la tabla de componentes y debajo "Procesos realizados" con "Limpieza"
- **AND** el encabezado sigue siendo "Orden OT-0042" y "Fecha: 2026-11-18 · 2 componentes"

#### Scenario: Orden sin procesos
- **GIVEN** `OT-0041` sin procesos
- **WHEN** el usuario exporta `OT-0041`
- **THEN** el documento no muestra "Procesos realizados"

#### Scenario: Orden sin servicio general
- **GIVEN** `OT-0041` sin servicio general
- **WHEN** el usuario exporta `OT-0041`
- **THEN** el documento no muestra el bloque "Servicio general"

#### Scenario: Componente dado de baja
- **GIVEN** la orden `OT-0001` con el componente `C-99` cuyo producto quedó dado de baja
- **WHEN** el usuario exporta `OT-0001`
- **THEN** el documento incluye `C-99` con su nombre y cantidad

#### Scenario: Lista intacta tras exportar
- **GIVEN** la lista filtrada con Desde `2026-11-16`
- **WHEN** el usuario exporta una orden y cierra el diálogo de impresión
- **THEN** la pantalla sigue mostrando la misma lista filtrada, con todas sus órdenes visibles

#### Scenario: Sin órdenes no hay exportación
- **WHEN** la lista muestra "No hay órdenes" o "No hay órdenes en ese período"
- **THEN** no se ve ningún botón "Exportar PDF"

## ADDED Requirements

### Requirement: Servicio general en la nueva orden
El modal "Nueva orden" SHALL mostrar un bloque "Servicio general" con un selector cuya opción inicial es "Sin servicio general", seguida de los servicios de `GET /api/servicios-generales` por nombre. Al elegir un servicio SHALL mostrar, como texto de solo lectura, los chequeos que incluye. Se SHALL enviar `servicio` con la clave elegida o `null`.

#### Scenario: Elegir un servicio
- **WHEN** el usuario elige "Servicio 20 hs"
- **THEN** el bloque muestra "Incluye:" con "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico"
- **AND** al crear la orden la petición envía `"servicio": "servicio-20-hs"`

#### Scenario: Volver a sin servicio
- **GIVEN** el usuario eligió "Servicio 20 hs"
- **WHEN** vuelve a elegir "Sin servicio general"
- **THEN** la lista de chequeos se oculta y la petición envía `"servicio": null`

#### Scenario: Modal reabierto
- **GIVEN** el usuario creó una orden con "Servicio 20 hs"
- **WHEN** vuelve a abrir "Nueva orden"
- **THEN** el selector muestra "Sin servicio general" y no se ve ninguna lista de chequeos

### Requirement: Errores del servicio general en la nueva orden
Si el catálogo de servicios generales no carga, el bloque SHALL avisar "No se pudo cargar la lista de servicios generales." y ofrecer solo "Sin servicio general", permitiendo crear la orden. Antes de enviar, el modal SHALL verificar que el servicio elegido siga en el catálogo cargado. Un 422 del servicio SHALL mostrarse junto al bloque, recargar el catálogo y dejar el modal abierto con los datos cargados.

#### Scenario: Catálogo no disponible
- **GIVEN** `GET /api/servicios-generales` falla
- **WHEN** se abre el modal
- **THEN** el bloque muestra "No se pudo cargar la lista de servicios generales.", el selector ofrece solo "Sin servicio general" y la orden se puede crear igual

#### Scenario: Servicio borrado mientras el modal estaba abierto
- **GIVEN** el usuario eligió "Servicio 20 hs" y ese servicio se borró por la API
- **WHEN** pulsa "Crear orden" y la API responde 422 "El servicio general 'servicio-20-hs' no existe."
- **THEN** el modal sigue abierto con ese mensaje junto al bloque "Servicio general", el catálogo se recarga y el selector queda en "Sin servicio general" con el resto de los datos cargados

### Requirement: Catálogo de servicios generales en la web
El botón "Servicios generales" de `/ordenes` SHALL abrir un modal con el catálogo de `GET /api/servicios-generales` ordenado por nombre, cada servicio con su nombre, sus chequeos en orden y las acciones "Editar" y "Eliminar", más un botón "Nuevo servicio". Sin servicios SHALL mostrar "No hay servicios generales."; si la carga falla, "No se pudo cargar la lista de servicios generales." con "Reintentar".

#### Scenario: Ver el catálogo
- **GIVEN** el catálogo con "Servicio 100 hs" (1 chequeo) y "Servicio 20 hs" (3 chequeos)
- **WHEN** el usuario pulsa "Servicios generales"
- **THEN** el modal lista "Servicio 100 hs" y luego "Servicio 20 hs", cada uno con sus chequeos como texto y sus botones "Editar" y "Eliminar" con nombre accesible que incluye el servicio

#### Scenario: Catálogo vacío
- **GIVEN** que se borraron todos los servicios generales
- **WHEN** el usuario abre el modal
- **THEN** se ve "No hay servicios generales." y el botón "Nuevo servicio"

#### Scenario: Error de carga
- **GIVEN** `GET /api/servicios-generales` falla
- **WHEN** el usuario abre el modal
- **THEN** se ve "No se pudo cargar la lista de servicios generales." y "Reintentar" vuelve a pedir la lista

### Requirement: Formulario de servicio general
"Nuevo servicio" y "Editar" SHALL mostrar en el mismo modal un formulario con "Nombre" y la lista ordenada de chequeos (una caja de texto por línea, "Quitar" por línea, "Agregar chequeo", entre 1 y 30 líneas). "Guardar" SHALL enviar `POST` (nuevo) o `PATCH` con `nombre` y `chequeos` (edición) y, con éxito, volver a la lista actualizada con "Servicio general X guardado."; "Volver" SHALL descartar los cambios.

#### Scenario: Crear un servicio
- **WHEN** el usuario pulsa "Nuevo servicio", escribe "Servicio 100 hs", deja una línea "Cambio de aceite", agrega otra con "Chequeo de motor" y pulsa "Guardar"
- **THEN** se envía `POST /api/servicios-generales` con `{"nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite", "Chequeo de motor"]}`
- **AND** el modal vuelve a la lista, que incluye "Servicio 100 hs", y se ve "Servicio general Servicio 100 hs guardado."

#### Scenario: Editar nombre y chequeos
- **GIVEN** "Servicio 20 hs" con tres chequeos
- **WHEN** el usuario pulsa "Editar", quita "Chequeo eléctrico", agrega "Chequeo de batería" y pulsa "Guardar"
- **THEN** se envía `PATCH /api/servicios-generales/servicio-20-hs` con `{"nombre": "Servicio 20 hs", "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo de batería"]}` y la lista muestra los chequeos nuevos

#### Scenario: Límites de líneas
- **WHEN** el formulario tiene una sola línea de chequeo
- **THEN** su "Quitar" está deshabilitado
- **AND** con 30 líneas "Agregar chequeo" queda deshabilitado con la ayuda "Un servicio general admite hasta 30 chequeos."

#### Scenario: Volver sin guardar
- **WHEN** el usuario cambia el nombre en "Editar" y pulsa "Volver"
- **THEN** no se envía ninguna petición y la lista muestra el servicio sin cambios

### Requirement: Validación del formulario de servicio general
Antes de enviar, el formulario SHALL validar: nombre obligatorio tras recortar, hasta 60 caracteres y distinto de los demás servicios del catálogo sin distinguir mayúsculas; cada chequeo obligatorio tras recortar, hasta 60 caracteres y sin repetir en el servicio. Cada error SHALL mostrarse junto a su campo con `aria-invalid`, sin enviar. Los rechazos de la API (409, 422 "Chequeo N: …", 404) SHALL mostrarse junto al campo o la línea correspondiente, con el formulario abierto.

#### Scenario: Nombre repetido
- **WHEN** el usuario crea un servicio con nombre "servicio 20 HS"
- **THEN** el campo "Nombre" muestra "Ya existe un servicio general con nombre 'servicio 20 HS'." y no se envía la petición

#### Scenario: Chequeo vacío o repetido
- **WHEN** el usuario guarda con los chequeos "Chequeo de motor", "" y "CHEQUEO DE MOTOR"
- **THEN** la línea 2 muestra "El nombre es obligatorio.", la línea 3 muestra "'CHEQUEO DE MOTOR' está repetido." y no se envía la petición

#### Scenario: Servicio borrado mientras se editaba
- **GIVEN** el usuario edita "Servicio 20 hs" y ese servicio se borró desde otra pestaña
- **WHEN** pulsa "Guardar" y la API responde 404
- **THEN** el modal vuelve a la lista recargada y muestra "No existe un servicio general con clave 'servicio-20-hs'."

### Requirement: Borrado de servicio general en la web
"Eliminar" SHALL pedir confirmación en el mismo modal ("¿Eliminar el servicio general X? Las órdenes que ya lo tienen lo conservan.") con "Cancelar" y "Eliminar servicio"; al confirmar SHALL enviar `DELETE /api/servicios-generales/{clave}` y volver a la lista actualizada con "Servicio general X eliminado.".

#### Scenario: Eliminar un servicio
- **WHEN** el usuario pulsa "Eliminar" en "Servicio 20 hs" y confirma con "Eliminar servicio"
- **THEN** se envía `DELETE /api/servicios-generales/servicio-20-hs`, la lista ya no incluye "Servicio 20 hs" y se ve "Servicio general Servicio 20 hs eliminado."
- **AND** las órdenes de `/ordenes` que lo tenían siguen mostrando "Servicio general: Servicio 20 hs"

#### Scenario: Cancelar
- **WHEN** el usuario pulsa "Eliminar" y luego "Cancelar"
- **THEN** no se envía ninguna petición y vuelve la lista sin cambios
