# Spec Delta

## MODIFIED Requirements

### Requirement: Modal de nueva orden
El modal "Nueva orden" SHALL pedir número, fecha, los procesos (opcionales, en líneas, según "Procesos en la nueva orden") y entre 1 y 100 líneas de componente (producto activo y cantidad) que se agregan y quitan; con éxito SHALL enviar `POST /api/ordenes`, cerrarse, recargar el inventario y mostrar "Orden X creada." con un enlace a `/ordenes`. Cada línea SHALL permitir elegir el producto entre todos los activos o filtrarlos por categoría según "Filtro por categoría en la nueva orden" (decisión del usuario, 2026-11-24). La categoría SHALL NOT enviarse a la API ni cambiar la orden creada.

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

### Requirement: Pantalla de órdenes
`/ordenes` SHALL mostrar un enlace "← Inventario", filtros opcionales Desde, Hasta y Número y la lista de `GET /api/ordenes` en el orden de la API con número, fecha, componentes (código, nombre y cantidad, incluidos productos dados de baja) y, si tiene, una fila "Procesos:" con un elemento por proceso en el orden de la API; cada orden SHALL tener sus acciones "Exportar PDF" y "Eliminar". Los filtros vacíos SHALL NOT enviarse.

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

### Requirement: Exportar una orden a PDF
El botón "Exportar PDF" de una orden en `/ordenes` SHALL exportar, según `exportacion-pdf`, solo esa orden (decisión del usuario, 2026-11-24): encabezado "Orden <número>" y "Fecha: AAAA-MM-DD · N componentes" (sin usuario creador; revisión del usuario, 2026-11-24), luego la tabla de sus componentes por código, incluidos productos dados de baja, y debajo, si tiene procesos, un bloque "Procesos realizados" con uno por línea en el orden de la API. Las demás órdenes SHALL NOT aparecer.

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

#### Scenario: Orden sin procesos
- **GIVEN** `OT-0041` sin procesos
- **WHEN** el usuario exporta `OT-0041`
- **THEN** el documento no muestra "Procesos realizados"

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

### Requirement: Procesos en la nueva orden
El modal "Nueva orden" SHALL mostrar, debajo de "Componentes", un bloque "Procesos" con líneas que se agregan con "Agregar proceso" y se quitan con "Quitar" (cero líneas permitido); cada línea SHALL tener un selector con los procesos de `GET /api/procesos` (por nombre) y "Personalizado". Los del catálogo SHALL enviarse como `procesos` (claves, en el orden de las líneas, una vez cada uno). Si el catálogo no carga, SHALL avisarse y ofrecerse solo "Personalizado".

#### Scenario: Líneas del catálogo
- **WHEN** el usuario agrega dos líneas, elige "Limpieza" y "Cambio motor" y crea la orden
- **THEN** la petición envía `"procesos": ["limpieza", "cambio-motor"]`

#### Scenario: Mismo proceso en dos líneas
- **WHEN** dos líneas tienen "Limpieza"
- **THEN** la petición envía `"limpieza"` una sola vez

#### Scenario: Catálogo no disponible
- **GIVEN** `GET /api/procesos` falla
- **WHEN** se abre el modal
- **THEN** el bloque muestra "No se pudo cargar la lista de procesos.", los selectores ofrecen solo "Personalizado" y la orden se puede crear igual

### Requirement: Procesos personalizados en la nueva orden
Elegir "Personalizado" en una línea SHALL mostrar una caja de texto etiquetada ("Proceso personalizado"), hasta 10 por orden; cambiar la línea a un proceso del catálogo SHALL ocultarla y no enviar su texto. Los textos SHALL enviarse recortados como `procesos_personalizados` en el orden de las líneas.

#### Scenario: Escribir procesos propios
- **WHEN** el usuario agrega dos líneas "Personalizado" y escribe "Pulido" y "Cambio de hélice"
- **THEN** la petición envía `"procesos_personalizados": ["Pulido", "Cambio de hélice"]`

#### Scenario: Cambiar a un proceso del catálogo
- **GIVEN** una línea "Personalizado" con "Pulido" escrito
- **WHEN** el usuario la cambia a "Limpieza" y crea la orden
- **THEN** la caja se oculta y la petición envía `"procesos": ["limpieza"]` y `"procesos_personalizados": []`

#### Scenario: Límite de personalizados
- **WHEN** hay 10 líneas "Personalizado"
- **THEN** no se puede elegir "Personalizado" en otra línea y se ve "Una orden admite hasta 10 procesos personalizados."

### Requirement: Validación de procesos en la nueva orden
Antes de enviar, el modal SHALL validar cada caja personalizada visible: obligatorio tras recortar, hasta 60 caracteres, distinto de los procesos del catálogo y de los demás personalizados sin distinguir mayúsculas; cada error SHALL mostrarse junto a su caja con `aria-invalid`, sin enviar. Un 422 "Proceso personalizado N: …" o de proceso inexistente SHALL mostrarse marcando la línea o el bloque.

#### Scenario: Campo vacío
- **WHEN** el usuario elige "Personalizado", deja la caja vacía y pulsa "Crear orden"
- **THEN** el campo muestra "El nombre es obligatorio." y no se envía la petición

#### Scenario: Igual a uno del catálogo
- **WHEN** el usuario escribe "limpieza" en una caja personalizada y pulsa "Crear orden"
- **THEN** el campo muestra "'limpieza' ya está en la lista de procesos; marcalo ahí." y no se envía la petición

#### Scenario: Proceso borrado mientras el modal estaba abierto
- **GIVEN** el usuario eligió "Cambio motor" en una línea y ese proceso se borró por la API
- **WHEN** pulsa "Crear orden" y la API responde 422 "El proceso 'cambio-motor' no existe."
- **THEN** el modal sigue abierto con ese mensaje junto al bloque "Procesos" y los datos cargados
