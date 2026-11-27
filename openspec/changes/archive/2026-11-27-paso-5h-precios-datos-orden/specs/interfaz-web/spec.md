# Spec Delta — interfaz-web

## MODIFIED Requirements

### Requirement: Modal de nueva orden
El modal "Nueva orden" SHALL pedir número, fecha, los datos del cliente y la embarcación con sus fechas de ingreso y egreso (opcionales, según "Datos del cliente en la nueva orden"), el servicio general con su precio (opcional, según "Servicio general en la nueva orden"), los servicios adicionales con su precio (opcionales, en líneas, según "Procesos en la nueva orden") y entre 1 y 100 líneas de componente (producto activo, cantidad e importe opcional) que se agregan y quitan, y SHALL mostrar el resumen de "Resumen de precios en la nueva orden"; con éxito SHALL enviar `POST /api/ordenes`, cerrarse, recargar el inventario y mostrar "Orden X creada." con un enlace a `/ordenes`. Cada línea SHALL permitir elegir el producto entre todos los activos o filtrarlos por categoría según "Filtro por categoría en la nueva orden" (decisión del usuario, 2026-11-24). La categoría SHALL NOT enviarse a la API ni cambiar la orden creada.

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
- **THEN** la fecha propuesta es la fecha local de hoy en formato `AAAA-MM-DD` y se puede cambiar, y las fechas de ingreso y egreso están vacías

#### Scenario: Orden sin procesos
- **WHEN** el usuario crea una orden sin líneas de servicio adicional
- **THEN** la petición envía `"procesos": []` y `"procesos_personalizados": []` y la orden se crea

#### Scenario: Orden sin servicio general
- **WHEN** el usuario crea una orden dejando "Sin servicio general"
- **THEN** la petición envía `"servicio": null` y `"precio_servicio": null` y la orden se crea

#### Scenario: Orden sin precios
- **WHEN** el usuario crea una orden dejando vacíos todos los importes
- **THEN** la petición envía `"precio": null` en cada componente y la orden se crea

### Requirement: Pantalla de órdenes
`/ordenes` SHALL mostrar un enlace "← Inventario", junto al título un botón "Servicios generales" que abre la administración del catálogo (según "Catálogo de servicios generales en la web"), filtros opcionales Desde, Hasta y Número y la lista de `GET /api/ordenes` en el orden de la API con número, fecha, componentes (código, nombre y cantidad, incluidos productos dados de baja), si tiene, una fila "Servicio general:" con su nombre y un elemento por chequeo en el orden de la API y, si tiene, una fila "Servicios adicionales:" con un elemento por proceso en el orden de la API; cada orden SHALL tener sus acciones "Exportar PDF" y "Eliminar". Los filtros vacíos SHALL NOT enviarse.

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
- **THEN** `OT-0042` muestra bajo su cabecera "Servicios adicionales:" con "Cambio motor" y "Pulido", como texto
- **AND** `OT-0041` no muestra la fila "Servicios adicionales:"

#### Scenario: Orden con servicio general
- **GIVEN** `OT-0042` con el servicio "Servicio 20 hs" (chequeos "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico") y el proceso "Limpieza", y `OT-0041` sin servicio general
- **WHEN** se abre `/ordenes`
- **THEN** `OT-0042` muestra bajo su cabecera "Servicio general:" con "Servicio 20 hs" y sus tres chequeos como texto, antes de la fila "Servicios adicionales:"
- **AND** `OT-0041` no muestra la fila "Servicio general:"

#### Scenario: Acceso a los servicios generales
- **WHEN** se abre `/ordenes`
- **THEN** junto al título "Órdenes" se ve el botón "Servicios generales"
- **AND** el botón no se imprime al exportar una orden

### Requirement: Exportar una orden a PDF
El botón "Exportar PDF" de una orden en `/ordenes` SHALL exportar, según `exportacion-pdf`, solo esa orden: encabezado "Orden <número>" y "Fecha: AAAA-MM-DD · N componentes" (sin usuario creador), los datos del cliente y la embarcación que tenga (con ingreso y egreso), si tiene servicio general un bloque "Servicio general" con nombre, precio y chequeos, la tabla de componentes por código con su importe, si tiene procesos un bloque "Servicios adicionales" con cada uno y su precio, y al final el resumen de subtotales y total. Las demás órdenes SHALL NOT aparecer.

#### Scenario: Exportar una orden
- **GIVEN** la lista con `OT-0042` (2026-11-18, creada por `admin`, componentes `A-01` x 2 y `B-02` x 1) y `OT-0041`
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0042`
- **THEN** el documento muestra "Orden OT-0042", "Fecha: 2026-11-18 · 2 componentes", `A-01` x 2 y `B-02` x 1
- **AND** no muestra "Creada por" ni `admin`
- **AND** no muestra `OT-0041`

#### Scenario: Exportar una orden con procesos
- **GIVEN** `OT-0042` con los procesos "Cambio motor" a $ 150.000,00 y "Pulido" sin precio
- **WHEN** el usuario exporta `OT-0042`
- **THEN** debajo de la tabla de componentes se ve "Servicios adicionales" con "Cambio motor" y "$ 150.000,00", y "Pulido" con "—", uno por línea
- **AND** el encabezado sigue siendo "Orden OT-0042" y "Fecha: 2026-11-18 · 2 componentes"

#### Scenario: Exportar una orden con servicio general
- **GIVEN** `OT-0042` con el servicio "Servicio 20 hs" a $ 45.000,00 y el proceso "Limpieza"
- **WHEN** el usuario exporta `OT-0042`
- **THEN** después del encabezado y de los datos del cliente, y antes de la tabla de componentes, se ve el bloque "Servicio general" con "Servicio 20 hs", "$ 45.000,00" y "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico", uno por línea
- **AND** luego se ve la tabla de componentes, debajo "Servicios adicionales" con "Limpieza" y al final el resumen

#### Scenario: Exportar una orden con datos y precios
- **GIVEN** `OT-0043` con fecha 2026-11-27, ingreso 2026-11-26, egreso 2026-11-29, cliente "Juan Pérez", celular "11 5555-1234", casco "Bermuda 190", servicio a $ 45.000,00, proceso a $ 15.000,00 y `A-01` x 2 a $ 12.000,00
- **WHEN** el usuario exporta `OT-0043`
- **THEN** el documento muestra "Fecha: 2026-11-27 · 1 componente", "Cliente: Juan Pérez", "Celular: 11 5555-1234", "Casco: Bermuda 190", "Ingreso: 2026-11-26", "Egreso: 2026-11-29", la columna "Importe" con "$ 12.000,00" y al final "Subtotal servicios $ 60.000,00", "Subtotal ítems $ 12.000,00" y "Total $ 72.000,00"
- **AND** no muestra "Motor" ni "Trailer" porque no los tiene

#### Scenario: Orden sin procesos
- **GIVEN** `OT-0041` sin procesos
- **WHEN** el usuario exporta `OT-0041`
- **THEN** el documento no muestra el bloque "Servicios adicionales"

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

### Requirement: Procesos en la nueva orden
El modal "Nueva orden" SHALL mostrar, debajo de "Componentes", un bloque "Servicios adicionales" con líneas que se agregan con "Agregar servicio adicional" y se quitan con "Quitar" (cero líneas permitido); cada línea SHALL tener un selector con los procesos de `GET /api/procesos` (por nombre) y "Personalizado", y su propio importe opcional. Los del catálogo SHALL enviarse como `procesos` (objetos `{clave, precio}`, en el orden de las líneas). Si el catálogo no carga, SHALL avisarse y ofrecerse solo "Personalizado".

#### Scenario: Líneas del catálogo
- **WHEN** el usuario agrega dos líneas, elige "Limpieza" con importe "15.000" y "Cambio motor" sin importe y crea la orden
- **THEN** la petición envía `"procesos": [{"clave": "limpieza", "precio": 1500000}, {"clave": "cambio-motor", "precio": null}]`

#### Scenario: Mismo proceso en dos líneas
- **WHEN** dos líneas tienen "Limpieza" y el usuario pulsa "Crear orden"
- **THEN** la segunda línea muestra "Ya está en otra línea." con `aria-invalid` y no se envía la petición

#### Scenario: Catálogo no disponible
- **GIVEN** `GET /api/procesos` falla
- **WHEN** se abre el modal
- **THEN** el bloque muestra "No se pudo cargar la lista de servicios adicionales.", los selectores ofrecen solo "Personalizado" y la orden se puede crear igual

### Requirement: Procesos personalizados en la nueva orden
Elegir "Personalizado" en una línea SHALL mostrar una caja de texto etiquetada ("Servicio adicional personalizado"), hasta 10 por orden; cambiar la línea a un proceso del catálogo SHALL ocultarla y no enviar su texto. Los textos SHALL enviarse recortados como `procesos_personalizados` (objetos `{nombre, precio}` con el importe de su línea) en el orden de las líneas.

#### Scenario: Escribir procesos propios
- **WHEN** el usuario agrega dos líneas "Personalizado", escribe "Pulido" con importe "8.000" y "Cambio de hélice" sin importe
- **THEN** la petición envía `"procesos_personalizados": [{"nombre": "Pulido", "precio": 800000}, {"nombre": "Cambio de hélice", "precio": null}]`

#### Scenario: Cambiar a un proceso del catálogo
- **GIVEN** una línea "Personalizado" con "Pulido" escrito
- **WHEN** el usuario la cambia a "Limpieza" y crea la orden
- **THEN** la caja se oculta y la petición envía `"procesos": [{"clave": "limpieza", "precio": null}]` y `"procesos_personalizados": []`

#### Scenario: Límite de personalizados
- **WHEN** hay 10 líneas "Personalizado"
- **THEN** no se puede elegir "Personalizado" en otra línea y se ve "Una orden admite hasta 10 servicios adicionales personalizados."

## ADDED Requirements

### Requirement: Datos del cliente en la nueva orden
El modal "Nueva orden" SHALL mostrar, después del número y la fecha (sin cambios), un bloque "Cliente y embarcación" con Cliente (hasta 80), Celular, Casco, Motor, Trailer (hasta 60), Fecha de ingreso y Fecha de egreso, todos opcionales y sin marca de obligatorio (usuario, 2026-11-27), y SHALL enviarlos recortados (`null` si están vacíos). Cada error SHALL mostrarse junto a su campo con `aria-invalid`, sin enviar.

#### Scenario: Todos los datos del cliente vacíos
- **WHEN** el usuario deja vacíos Cliente, Celular, Casco, Motor, Trailer, Fecha de ingreso y Fecha de egreso y crea una orden válida con la fecha propuesta
- **THEN** la petición envía esos campos en `null` y la orden se crea

#### Scenario: Cliente largo
- **WHEN** el usuario pega un cliente de 81 caracteres y pulsa "Crear orden"
- **THEN** el campo muestra "El cliente admite hasta 80 caracteres." y no se envía la petición

#### Scenario: Egreso anterior al ingreso
- **WHEN** el usuario elige Fecha de ingreso `2026-11-27` y Fecha de egreso `2026-11-26` y pulsa "Crear orden"
- **THEN** el campo de egreso muestra "La fecha de egreso no puede ser anterior a la de ingreso." y no se envía la petición

#### Scenario: Solo fecha de egreso
- **WHEN** el usuario completa solo Fecha de egreso `2026-11-20` y crea una orden válida
- **THEN** la petición envía `"fecha_ingreso": null` y `"fecha_egreso": "2026-11-20"` y la orden se crea

#### Scenario: Celular inválido
- **WHEN** el usuario escribe "11-abc" en Celular y pulsa "Crear orden"
- **THEN** el campo muestra "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)." y no se envía la petición

#### Scenario: Datos opcionales vacíos
- **WHEN** el usuario completa solo Cliente "Juan Pérez" y crea la orden
- **THEN** la petición envía `"cliente": "Juan Pérez"` y `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso` y `fecha_egreso` en `null`

### Requirement: Importes en la nueva orden
Cada importe del modal (servicio general, línea de componente y línea de servicio adicional) SHALL ser una caja de texto opcional en pesos que acepte `12500`, `12.500`, `12500,5`, `12.500,50` o `$ 12.500` (punto de miles, coma decimal, hasta 2 decimales) y SHALL enviarse en centavos enteros (`null` si está vacía). Un valor inválido SHALL mostrar "Ingresá un importe válido (ej. 12.500,50)." y uno mayor a $ 999.999.999,99 "El importe admite hasta $ 999.999.999,99.", sin enviar.

#### Scenario: Importe con miles y centavos
- **WHEN** el usuario escribe "12.500,50" como importe de una línea de componente y crea la orden
- **THEN** la petición envía `"precio": 1250050` en ese componente

#### Scenario: Importe ambiguo o inválido
- **WHEN** el usuario escribe "12.5", "-100", "1,234" con tres decimales o "abc" como importe y pulsa "Crear orden"
- **THEN** la línea muestra "Ingresá un importe válido (ej. 12.500,50)." con `aria-invalid` y no se envía la petición

#### Scenario: Precio del servicio sin servicio
- **WHEN** el usuario deja "Sin servicio general"
- **THEN** la caja de precio del servicio está deshabilitada y vacía, y la petición envía `"precio_servicio": null`

### Requirement: Resumen de precios en la nueva orden
El modal "Nueva orden" SHALL mostrar al pie, actualizados al tipear o al agregar o quitar líneas (pedido del usuario, 2026-11-27), "Subtotal servicios" (servicio general + servicios adicionales), "Subtotal ítems" (componentes) y "Total", en formato `$ 12.500,00`. Los importes vacíos o todavía inválidos SHALL contar como 0. El resumen SHALL NOT enviarse a la API.

#### Scenario: Resumen en vivo
- **GIVEN** el modal abierto con el servicio "Servicio 20 hs" a "45.000", los servicios adicionales "Limpieza" a "15.000" y "Pulido" sin importe y los componentes a "12.000" y sin importe
- **WHEN** el usuario termina de escribir
- **THEN** se ve "Subtotal servicios $ 60.000,00", "Subtotal ítems $ 12.000,00" y "Total $ 72.000,00"

#### Scenario: Quitar una línea
- **GIVEN** el resumen anterior
- **WHEN** el usuario quita la línea de "Limpieza"
- **THEN** se ve "Subtotal servicios $ 45.000,00" y "Total $ 57.000,00"

#### Scenario: Sin importes
- **WHEN** se abre el modal
- **THEN** los tres valores muestran "$ 0,00"

### Requirement: Datos y precios de cada orden en pantalla
En `/ordenes`, cada orden SHALL mantener su fecha en la cabecera como hoy; si tiene datos del cliente o fechas de ingreso/egreso, una fila con los que tenga ("Cliente", "Cel.", "Casco", "Motor", "Trailer", "Ingreso", "Egreso"); el precio del servicio general y de cada servicio adicional junto a su nombre; una columna "Importe" en la tabla de componentes; y al pie el resumen "Subtotal servicios", "Subtotal ítems" y "Total" de la API. Un precio vacío SHALL verse como "—".

#### Scenario: Orden con datos y precios
- **GIVEN** `OT-0043` con fecha 2026-11-27, ingreso 2026-11-26, egreso 2026-11-29, cliente "Juan Pérez", servicio a 4500000, "Limpieza" a 1500000, "Pulido" sin precio y `A-01` x 2 a 1200000
- **WHEN** se abre `/ordenes`
- **THEN** `OT-0043` muestra en su cabecera "2026-11-27" y en la fila de datos "Cliente: Juan Pérez", "Ingreso: 2026-11-26" y "Egreso: 2026-11-29", "Servicio 20 hs" con "$ 45.000,00", "Limpieza" con "$ 15.000,00" y "Pulido" con "—", `A-01` con importe "$ 12.000,00" y al pie "Subtotal servicios $ 60.000,00", "Subtotal ítems $ 12.000,00" y "Total $ 72.000,00"

#### Scenario: Orden anterior a los precios
- **GIVEN** `OT-0041` creada antes de existir los datos y precios
- **WHEN** se abre `/ordenes`
- **THEN** `OT-0041` no muestra la fila del cliente, sus importes se ven como "—" y el resumen muestra "$ 0,00" en los tres valores
