# interfaz-web Specification

## Purpose
Permite operar Inventario-B desde el navegador sin herramientas técnicas: login, inventario, movimientos de stock, órdenes y borrados, consumiendo la API JSON con validación del lado del cliente, mensajes de error en español y el design system aprobado.

## Requirements

### Requirement: Formulario de login
La página de login SHALL pedir usuario y contraseña (contraseña oculta por defecto, con un botón "Mostrar"/"Ocultar"), enviarlos a `POST /api/login` y, con éxito, navegar a `/inventario`. Durante el envío el botón SHALL quedar deshabilitado con el texto "Ingresando…".

#### Scenario: Login correcto
- **GIVEN** la página `/` sin sesión
- **WHEN** el usuario ingresa `admin` y su contraseña y pulsa "Ingresar"
- **THEN** el navegador queda en `/inventario` mostrando el inventario

#### Scenario: Contraseña oculta
- **WHEN** se abre la página de login
- **THEN** el campo de contraseña es de tipo `password`
- **AND** al pulsar "Mostrar" se ve el texto y el botón pasa a "Ocultar"

#### Scenario: Envío en curso
- **GIVEN** el usuario pulsó "Ingresar" y la API todavía no respondió
- **THEN** el botón está deshabilitado con el texto "Ingresando…" y un segundo clic no envía otra petición

### Requirement: Errores del login
Ante un 401 la página SHALL mostrar el mensaje genérico de la API ("Usuario o contraseña incorrectos.") en una alerta, conservar el usuario tipeado, vaciar la contraseña y devolverle el foco. Con usuario o contraseña vacíos SHALL mostrar el error junto al campo sin llamar a la API.

#### Scenario: Credenciales inválidas
- **WHEN** el usuario envía `admin` con una contraseña incorrecta
- **THEN** se ve la alerta "Usuario o contraseña incorrectos."
- **AND** el campo usuario conserva `admin`, la contraseña queda vacía y con el foco

#### Scenario: Campos vacíos
- **WHEN** el usuario pulsa "Ingresar" con la contraseña vacía
- **THEN** se ve "La contraseña es obligatoria." junto al campo y no se envía ninguna petición

### Requirement: Sesión expirada
Ante un 401 de cualquier llamada a la API distinta del login, la interfaz SHALL navegar a `/?sesion=expirada`, y la página de login SHALL mostrar en ese caso el aviso "Tu sesión expiró. Ingresá de nuevo.".

#### Scenario: 401 durante el uso
- **GIVEN** el usuario está en `/inventario` y su sesión deja de ser válida
- **WHEN** registra un ingreso de stock
- **THEN** el navegador queda en `/?sesion=expirada` con el aviso "Tu sesión expiró. Ingresá de nuevo."

#### Scenario: Login sin aviso
- **WHEN** se abre `/` directamente
- **THEN** no se muestra el aviso de sesión expirada

### Requirement: Cabecera y cierre de sesión
Las páginas protegidas SHALL mostrar una cabecera con el título de texto "Inventario" (sin logo), la navegación por secciones con las pestañas "Inventario" (`/inventario`), "Órdenes" (`/ordenes`) y "Reportes" (`/reportes`), marcando la pestaña de la página actual con `aria-current="page"`, el usuario de `GET /api/me` y el botón "Cerrar sesión", que SHALL llamar a `POST /api/logout` y navegar a `/`.

#### Scenario: Cerrar sesión
- **GIVEN** el usuario está en `/inventario`
- **WHEN** pulsa "Cerrar sesión"
- **THEN** el navegador queda en `/` y un acceso posterior a `/inventario` vuelve al login

#### Scenario: Usuario visible
- **WHEN** el `admin` abre `/inventario` en escritorio
- **THEN** la cabecera muestra "Usuario: admin"

#### Scenario: Pestaña Reportes
- **GIVEN** el usuario está en `/inventario` o en `/ordenes`
- **WHEN** pulsa la pestaña "Reportes"
- **THEN** el navegador queda en `/reportes` y esa pestaña está marcada como la actual

#### Scenario: Navegación en móvil
- **GIVEN** un ancho de 390 px
- **WHEN** se abre cualquier página protegida
- **THEN** las tres pestañas se ven completas, sin scroll horizontal de la página

### Requirement: Tabla de inventario
`/inventario` SHALL mostrar primero la barra de acciones ("Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes") y la tabla de productos activos de `GET /api/inventario` (código, nombre, categoría, stock, acción "Eliminar") en el orden de la API, con la cantidad de productos y el stock 0 resaltado. La columna "Categoría" SHALL mostrar el nombre de la categoría del producto (tomado de `GET /api/categorias`) o "Sin categoría" atenuado. Sobre la tabla SHALL mostrar el campo "Buscar", el filtro "Categoría" y el botón "Exportar PDF". La web SHALL NOT ofrecer los antiguos "Ingreso de stock" ni "Egreso de stock".

#### Scenario: Producto sin stock
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se abre `/inventario`
- **THEN** la tabla muestra `A-01` y luego `B-10`, el stock de `B-10` resaltado como sin stock y el texto "2 productos"

#### Scenario: Columna de categoría
- **GIVEN** los productos activos `A-01` (sin categoría) y `F-01` (categoría `filtro`)
- **WHEN** se abre `/inventario`
- **THEN** la fila de `A-01` muestra "Sin categoría" y la de `F-01` muestra "Filtro"

#### Scenario: Cargando
- **GIVEN** `GET /api/inventario` todavía no respondió
- **THEN** se ve el estado "Cargando inventario…" en lugar de la tabla

#### Scenario: Botones nuevos
- **WHEN** se abre `/inventario`
- **THEN** la barra muestra "Nuevo ingreso" y "Modificar stock" y no muestra "Ingreso de stock" ni "Egreso de stock"
- **AND** ningún script de la web llama a `/api/stock/ingreso` ni a `/api/stock/egreso`

#### Scenario: Buscador y exportación visibles
- **GIVEN** al menos un producto activo
- **WHEN** se abre `/inventario`
- **THEN** sobre la tabla se ven el campo "Buscar" (vacío, con etiqueta accesible), el filtro "Categoría" en "Todas las categorías" (con etiqueta accesible) y el botón "Exportar PDF" habilitado

#### Scenario: Categorías no disponibles
- **GIVEN** `GET /api/categorias` falla y `GET /api/inventario` responde
- **WHEN** se abre `/inventario`
- **THEN** la tabla se muestra igual, la columna "Categoría" muestra la clave de cada producto (o "Sin categoría") y el filtro ofrece solo "Todas las categorías"

### Requirement: Inventario vacío
Si `GET /api/inventario` devuelve una lista vacía, `/inventario` SHALL mostrar el cartel "Todavía no hay productos" con la indicación de crear el primero con "Nuevo ingreso", en lugar de una tabla vacía.

#### Scenario: Sin productos
- **GIVEN** ningún producto activo
- **WHEN** se abre `/inventario`
- **THEN** se ve "Todavía no hay productos" y no se ve la tabla

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

### Requirement: Errores de la nueva orden por línea
Ante un 409 con `faltantes`, el modal SHALL mostrar el `detail` y marcar cada línea de ese código con "Disponible D, solicitado S"; ante un 404 de productos o un 422 "Componente N: …", SHALL marcar las líneas afectadas. El modal SHALL quedar abierto con los datos cargados.

#### Scenario: Faltantes por línea
- **GIVEN** `A-01` con stock 1
- **WHEN** el usuario envía una orden con `A-01` x 3 en la línea 2
- **THEN** se ve la alerta con el `detail` del 409 y la línea 2 muestra "Disponible 1, solicitado 3"

#### Scenario: Componente N
- **WHEN** la API responde 422 "Componente 2: La cantidad debe ser un entero entre 1 y 10.000."
- **THEN** se ve ese mensaje y la línea 2 queda marcada como inválida

#### Scenario: Número duplicado
- **GIVEN** ya existe la orden `OT-0001`
- **WHEN** el usuario envía otra orden `ot-0001`
- **THEN** el modal muestra "Ya existe una orden con número 'OT-0001'." solo en su alerta superior
- **AND** el campo número queda marcado `aria-invalid`, enlazado a esa alerta por `aria-describedby` (sin repetir el mensaje bajo el campo) y con el foco

### Requirement: Confirmación de la baja de producto
La acción "Eliminar" de una fila SHALL abrir un modal de confirmación con el código y nombre del producto, que explique que las órdenes anteriores lo siguen mostrando y que un ingreso posterior lo reactiva; solo al confirmar SHALL enviar `DELETE /api/productos/{codigo}` con el código codificado.

#### Scenario: Confirmar baja
- **GIVEN** `A-01` activo
- **WHEN** el usuario pulsa "Eliminar" en `A-01` y confirma con "Eliminar producto"
- **THEN** `A-01` desaparece de la tabla y se ve "Producto A-01 dado de baja."

#### Scenario: Cancelar baja
- **WHEN** el usuario pulsa "Eliminar" y luego "Cancelar", la X o Escape
- **THEN** no se envía ninguna petición y `A-01` sigue en la tabla

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

### Requirement: Estados de la lista de órdenes
Si la API devuelve `[]`, `/ordenes` SHALL mostrar en lugar de la tabla el cartel "No hay órdenes en ese período" cuando hay algún filtro aplicado, o "No hay órdenes" cuando no hay filtros (decisión del usuario, 2026-11-20); si devuelve 404 por número, SHALL mostrar su `detail`; si devuelve 422, SHALL mostrar su `detail` junto a los filtros.

#### Scenario: Período sin órdenes
- **WHEN** el filtro no coincide con ninguna orden
- **THEN** se ve "No hay órdenes en ese período" y no se ve la tabla

#### Scenario: Sin órdenes y sin filtros
- **GIVEN** no existe ninguna orden
- **WHEN** el usuario abre `/ordenes` sin filtros (o elige "Ver todas")
- **THEN** se ve "No hay órdenes", sin la frase "en ese período", y no se ve la tabla

#### Scenario: Número inexistente
- **WHEN** el usuario busca el número `ot-9999`, que no existe
- **THEN** se ve "No existe una orden con número 'OT-9999'."

#### Scenario: Número fuera del rango
- **GIVEN** la orden `OT-0041` del 2026-11-15
- **WHEN** el usuario busca `OT-0041` con Desde `2026-11-16`
- **THEN** se ve "No hay órdenes en ese período"

### Requirement: Borrado de orden con decisión de reintegro
El borrado de una orden SHALL pedir confirmación en un modal con la casilla "Devolver stock" marcada por defecto; el botón SHALL decir "Borrar y devolver stock" o "Borrar sin devolver stock" según la casilla, y SHALL enviar `DELETE /api/ordenes/{numero}?reintegrar=true|false` con el número codificado con `encodeURIComponent`.

#### Scenario: Valor por defecto
- **WHEN** el usuario pulsa "Eliminar" en la orden `OT-0001`
- **THEN** el modal muestra `OT-0001`, la casilla "Devolver stock" marcada y el botón "Borrar y devolver stock"

#### Scenario: Sin devolver stock
- **WHEN** el usuario desmarca la casilla y confirma
- **THEN** el botón decía "Borrar sin devolver stock" y la petición es `DELETE /api/ordenes/OT-0001?reintegrar=false`

#### Scenario: Número con caracteres especiales
- **GIVEN** la orden `OT/2026#1`
- **WHEN** el usuario la borra devolviendo stock
- **THEN** la petición es `DELETE /api/ordenes/OT%2F2026%231?reintegrar=true` y la orden desaparece de la lista

#### Scenario: Cancelar el borrado
- **WHEN** el usuario cierra el modal con "Cancelar", la X o Escape
- **THEN** no se envía ninguna petición

### Requirement: Resultado del borrado de orden
Tras un borrado exitoso, `/ordenes` SHALL quitar la orden de la lista y mostrar un resumen: con reintegro, una lista con un ítem por producto (código, `+cantidad` devuelta y `(stock N)` final, con "reactivado" si se reactivó); sin reintegro, que el stock no cambió. Un 404 SHALL mostrar su `detail` y recargar la lista.

#### Scenario: Resumen con reintegro
- **WHEN** se borra `OT-0001` devolviendo `A-01` x 2 (stock final 5) y `C-99` x 4 (stock final 5, reactivado)
- **THEN** se ve "Orden OT-0001 borrada. Stock devuelto:" seguido de una lista con un ítem por producto
- **AND** los ítems son "A-01 +2 (stock 5)" y "C-99 +4 (stock 5, reactivado)"

#### Scenario: Resumen sin reintegro
- **WHEN** se borra `OT-0001` sin devolver stock
- **THEN** se ve "Orden OT-0001 borrada sin devolver stock."

#### Scenario: Orden ya borrada
- **GIVEN** la orden `OT-0001` fue borrada desde otra pestaña
- **WHEN** el usuario confirma su borrado
- **THEN** se ve "No existe una orden con número 'OT-0001'." y la lista se recarga sin ella

### Requirement: Validación en el navegador
Antes de llamar a la API, la interfaz SHALL validar: obligatorios (tras recortar espacios), cantidad entera de 1 a 10.000, stock entero de 0 a 10.000, fecha `AAAA-MM-DD` real, Desde ≤ Hasta, número ≤ 30, código ≤ 50 y nombre ≤ 120 caracteres, y un producto por línea sin repetir; cada error SHALL mostrarse junto a su campo, marcado `aria-invalid`, sin enviar la petición.

#### Scenario: Cantidad no entera
- **WHEN** el usuario envía una línea "Sumar" con cantidad `2.5`, `0` o `10001`
- **THEN** se ve "La cantidad debe ser un entero entre 1 y 10.000." junto al campo y no se envía nada

#### Scenario: Stock fuera de rango
- **WHEN** el usuario envía un nuevo ingreso o una línea "Fijar en" con stock `-1`, `2.5` o `10001`
- **THEN** se ve "El stock debe ser un entero entre 0 y 10.000." junto al campo y no se envía nada

#### Scenario: Stock cero aceptado
- **WHEN** el usuario envía un nuevo ingreso o una línea "Fijar en" con stock `0`
- **THEN** la validación del navegador lo acepta y se envía la petición

#### Scenario: Línea sin producto
- **WHEN** el usuario envía una modificación con una línea sin producto elegido
- **THEN** se ve "Elegí un producto." en esa línea y no se envía nada

#### Scenario: Código demasiado largo
- **WHEN** el usuario envía un código de 51 caracteres
- **THEN** se ve "El código admite hasta 50 caracteres." y no se envía nada

#### Scenario: Fecha inválida
- **WHEN** el usuario envía una orden con fecha `2026-02-30`
- **THEN** se ve "La fecha debe ser una fecha real con formato AAAA-MM-DD." y no se envía nada

#### Scenario: Rango invertido
- **WHEN** el usuario filtra con Desde `2026-11-20` y Hasta `2026-11-01`
- **THEN** se ve "Desde no puede ser posterior a Hasta." y no se envía nada

#### Scenario: El backend sigue siendo la autoridad
- **WHEN** la API rechaza con 422 un dato que pasó la validación del navegador
- **THEN** se muestra el `detail` de la API tal cual

### Requirement: Errores de red y del servidor
Si una petición no llega al servidor, la interfaz SHALL mostrar "No se pudo conectar con el servidor. Revisá que esté en marcha y probá de nuevo."; ante un 5xx o una respuesta sin `detail`, SHALL mostrar "Ocurrió un error inesperado. Probá de nuevo."; en ambos casos los datos del formulario SHALL conservarse.

#### Scenario: Servidor caído
- **GIVEN** el servidor se detuvo
- **WHEN** el usuario envía un ingreso
- **THEN** el modal sigue abierto con los datos y se ve el mensaje de conexión

#### Scenario: Carga fallida del inventario
- **WHEN** `GET /api/inventario` falla por red
- **THEN** se ve el mensaje de conexión con un botón "Reintentar"

### Requirement: Envíos sin duplicar
Mientras una petición de escritura esté en curso, su botón de confirmación SHALL quedar deshabilitado y un nuevo clic o Enter SHALL NOT enviar otra petición.

#### Scenario: Doble clic en crear orden
- **WHEN** el usuario hace doble clic en "Crear orden"
- **THEN** se envía una sola petición `POST /api/ordenes`

### Requirement: Modales accesibles
Cada modal SHALL tener título asociado (`aria-labelledby`), mover el foco a su primer campo al abrirse, mantener el foco dentro mientras esté abierto, cerrarse con Cancelar, la X, Escape o un clic en el fondo, y devolver el foco al control que lo abrió.

#### Scenario: Teclado
- **WHEN** el usuario abre "Nuevo ingreso" con el teclado, recorre con Tab y pulsa Escape
- **THEN** el foco empieza en Código, no sale del modal con Tab y vuelve al botón "Nuevo ingreso" al cerrar

#### Scenario: Etiquetas
- **WHEN** se inspecciona cualquier campo de la interfaz
- **THEN** tiene una etiqueta visible asociada o un `aria-label`, y los errores se anuncian con `role="alert"`

#### Scenario: Modo de cada línea
- **WHEN** se inspecciona el selector "Fijar en" / "Sumar" de una línea de "Modificar stock"
- **THEN** es un grupo de opciones con nombre accesible que incluye el número de línea y se opera con el teclado

### Requirement: Aspecto según el design system
Las páginas SHALL usar los tokens y componentes del design system (Revision 2): foco visible, objetivos de al menos 40 px, tablas con scroll horizontal interno, tema oscuro único (no sigue `prefers-color-scheme`) y animaciones anuladas con `prefers-reduced-motion`; SHALL verse sin scroll horizontal de página a 390x844 y a 1440x900.

#### Scenario: Móvil
- **WHEN** se abre `/inventario` en 390x844
- **THEN** no hay scroll horizontal de la página y la tabla se desplaza dentro de su contenedor

#### Scenario: Tema oscuro con el sistema en modo claro
- **GIVEN** el sistema con `prefers-color-scheme: light`
- **WHEN** se abren `/`, `/inventario` y `/ordenes`
- **THEN** las páginas se ven con el tema oscuro (fondo, tarjetas, modales y campos oscuros, `color-scheme: dark`)

#### Scenario: Movimiento reducido
- **GIVEN** el sistema con `prefers-reduced-motion: reduce`
- **WHEN** se abre un modal
- **THEN** aparece sin animación

### Requirement: Datos mostrados como texto
Todo dato que venga de la API o del usuario (códigos, nombres, números, mensajes) SHALL insertarse en la página como texto, nunca como HTML interpretado.

#### Scenario: Nombre con marcado
- **GIVEN** un producto con nombre `<img src=x onerror=alert(1)>`
- **WHEN** se abre `/inventario`
- **THEN** la tabla muestra ese texto literal y no se ejecuta ningún script

### Requirement: Modal de nuevo ingreso
El modal "Nuevo ingreso" SHALL pedir Código, Nombre y Stock (los tres obligatorios; el stock puede ser 0) y Categoría (selector con "Sin categoría", por defecto, y las categorías de `GET /api/categorias`), enviar `POST /api/productos` y, con éxito, cerrarse, recargar el inventario y mostrar una alerta de éxito que diga si el producto fue creado o reactivado.

#### Scenario: Producto nuevo con stock cero
- **GIVEN** ningún producto `N-01`
- **WHEN** el usuario crea `N-01` "Arandela 6mm" con stock 0 sin tocar Categoría
- **THEN** el modal se cierra, la tabla muestra `N-01` con stock 0 resaltado y "Sin categoría", y se ve "Producto creado: N-01 · Arandela 6mm (stock 0)."

#### Scenario: Producto nuevo con categoría
- **GIVEN** ningún producto `AC-10`
- **WHEN** el usuario crea `AC-10` "Aceite 10W40" con stock 4 y Categoría "Aceite"
- **THEN** se envía `"categoria": "aceite"` y la tabla muestra `AC-10` con "Aceite"

#### Scenario: Código dado de baja
- **GIVEN** el producto dado de baja `C-99`
- **WHEN** el usuario escribe `C-99` en Código
- **THEN** el modal avisa, sin impedir el envío, "Este código está dado de baja: se va a reactivar con el nombre, el stock y la categoría que indiques."
- **AND** al enviarlo con "Junta tórica" y stock 6 se ve "Producto reactivado: C-99 · Junta tórica (stock 6)."

#### Scenario: Código activo repetido
- **GIVEN** el producto activo `A-01`
- **WHEN** el usuario envía `a-01` y la API responde 409 "Ya existe un producto con código 'A-01'."
- **THEN** el modal sigue abierto con los datos y muestra ese `detail` solo en su alerta superior
- **AND** Código queda marcado `aria-invalid`, enlazado a esa alerta por `aria-describedby` (sin repetir el mensaje bajo el campo) y con el foco

#### Scenario: Campos obligatorios
- **WHEN** el usuario envía el modal con Nombre vacío y Stock vacío
- **THEN** se ve "El nombre es obligatorio." y "El stock es obligatorio." junto a cada campo y no se envía nada

### Requirement: Modal de modificar stock
El modal "Modificar stock" SHALL pedir de 1 a 100 líneas que se agregan y quitan; cada línea elige un producto, un modo ("Fijar en" o "Sumar") con su valor, opcionalmente un nombre nuevo y una Categoría (selector con "Sin categoría" y las categorías del catálogo, precargado con la categoría actual del producto elegido, también para los dados de baja). Con éxito SHALL enviar `POST /api/stock/modificaciones` con la categoría de cada línea, cerrarse, recargar el inventario y mostrar el resumen.

#### Scenario: Una línea fijando el stock
- **GIVEN** `A-01` "Tornillo M8" con stock 7
- **WHEN** el usuario elige `A-01`, deja "Fijar en" y escribe 12
- **THEN** la línea muestra "Stock actual 7 → 12" y, al guardar, la tabla muestra `A-01` con stock 12

#### Scenario: Valor propuesto al fijar
- **WHEN** el usuario elige un producto con stock 7 en modo "Fijar en"
- **THEN** el campo del valor se propone en 7, de modo que cambiar solo el nombre o la categoría no altera el stock

#### Scenario: Categoría precargada y cambiada
- **GIVEN** `F-01` con categoría `filtro` y stock 3
- **WHEN** el usuario elige `F-01`, ve Categoría en "Filtro", la cambia a "Aceite" y guarda
- **THEN** se envía la línea con `"categoria": "aceite"` y la tabla muestra `F-01` con "Aceite" y stock 3

#### Scenario: Varias líneas con modos distintos
- **WHEN** el usuario fija `A-01` en 12, suma 4 a `B-10` y renombra `C-03`
- **THEN** se envía una sola petición con las tres líneas en ese orden

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar producto" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea, y con 100 líneas "Agregar producto" queda deshabilitado

### Requirement: Selector de productos de la modificación
El selector de producto de cada línea SHALL ofrecer los productos activos (`GET /api/inventario`) y, en un grupo aparte "Dados de baja", los de `GET /api/productos/inactivos`, cada uno como "CÓDIGO · Nombre (stock N)", limitados ambos grupos por el filtro por categoría de la línea; un grupo sin productos no se muestra. Un producto ya elegido en otra línea SHALL quedar deshabilitado en las demás.

#### Scenario: Producto dado de baja
- **GIVEN** el producto dado de baja `C-99` "Junta" con stock 2
- **WHEN** el usuario abre el selector y elige `C-99`
- **THEN** lo encuentra en el grupo "Dados de baja" y la línea avisa según lo que cargue: "Dado de baja: se va a reactivar al guardar." si el stock resultante cambia y queda mayor que 0 (sumar, o fijar en un valor distinto mayor que 0), o "Dado de baja: sigue dado de baja (sin cambio de stock)." / "Dado de baja: sigue dado de baja (stock 0)." si no

#### Scenario: Aviso de un dado de baja según el stock cargado
- **GIVEN** la línea 2 tiene el producto dado de baja `C-99` con stock 2 en modo "Fijar en"
- **WHEN** el usuario deja el valor en 2, lo cambia a 0 o lo cambia a 6
- **THEN** con 2 y con 0 la línea avisa que sigue dado de baja y con 6 avisa "Dado de baja: se va a reactivar al guardar."

#### Scenario: Producto ya elegido
- **GIVEN** la línea 1 tiene `A-01`
- **WHEN** el usuario abre el selector de la línea 2
- **THEN** `A-01` aparece deshabilitado

#### Scenario: Producto ya elegido dentro de un filtro
- **GIVEN** la línea 1 tiene `AC-10` y la línea 2 tiene el filtro en "Aceite"
- **WHEN** el usuario abre el selector de la línea 2
- **THEN** `AC-10` aparece deshabilitado con "— ya está en otra línea"

### Requirement: Resumen de la modificación
Tras una modificación exitosa, la página SHALL mostrar una alerta persistente con un ítem por línea: código, stock anterior → nuevo (o "sin cambios"), el nombre anterior → nuevo si cambió, la categoría anterior → nueva si cambió y la marca "reactivado" solo donde la respuesta trae `reactivado: true`.

#### Scenario: Resumen con reactivación
- **WHEN** la API responde con `A-01` (fijar, 7 → 12, nombre "Tornillo" → "Tornillo M8") y `C-99` (sumar, 2 → 5, `reactivado: true`)
- **THEN** la alerta dice "Stock modificado (2 productos)" y lista "A-01 · Tornillo M8: 7 → 12 · nombre antes: Tornillo" y "C-99 · Junta: 2 → 5 (+3) · reactivado"

#### Scenario: Resumen con cambio de categoría
- **WHEN** la API responde con `F-01` (fijar, 3 → 3, `categoria_anterior: "filtro"`, `categoria: "aceite"`)
- **THEN** la alerta lista "F-01 · Filtro de aceite: sin cambios · categoría: Filtro → Aceite"

### Requirement: Errores de la modificación por línea
Ante un 422 "Línea N: …" el modal SHALL marcar la línea N; ante un 404 SHALL marcar las líneas cuyos códigos vienen en `codigos` con "Este producto ya no existe: elegí otro o quitá la línea." y refrescar los selectores. El modal SHALL quedar abierto con los datos y el `detail` en la alerta superior.

#### Scenario: Línea inválida según la API
- **WHEN** la API responde 422 "Línea 2: El stock debe ser un entero entre 0 y 10.000."
- **THEN** se ve ese mensaje arriba y la línea 2 queda marcada como inválida

#### Scenario: Producto borrado de la base
- **WHEN** la API responde 404 con `codigos: ["Z-01"]`
- **THEN** la línea con `Z-01` muestra "Este producto ya no existe: elegí otro o quitá la línea." y los selectores se recargan

#### Scenario: Enviando
- **WHEN** el usuario pulsa "Guardar cambios"
- **THEN** el botón muestra "Guardando…" deshabilitado hasta la respuesta y se envía una sola petición

### Requirement: Buscador del inventario
El campo "Buscar" de `/inventario` SHALL filtrar, mientras se escribe y sin llamar a la API, las filas de productos activos cuyo código o nombre contiene el texto escrito, sin distinguir mayúsculas ni tildes e ignorando los espacios al principio y al final. Con texto vacío SHALL mostrar todos los productos. Las filas visibles SHALL conservar el orden de la API.

#### Scenario: Por nombre parcial
- **GIVEN** los productos `A-01` "Tornillo M8", `B-10` "Tuerca M8" y `C-03` "Arandela"
- **WHEN** el usuario escribe `tor`
- **THEN** la tabla muestra solo `A-01`
- **AND** no se envía ninguna petición a la API

#### Scenario: Por código parcial y en minúsculas
- **GIVEN** los productos `A-01`, `A-02` y `B-10`
- **WHEN** el usuario escribe `a-0`
- **THEN** la tabla muestra `A-01` y luego `A-02`

#### Scenario: Texto que aparece en código y nombre
- **GIVEN** los productos `M8-1` "Arandela" y `A-01` "Tornillo M8"
- **WHEN** el usuario escribe `m8`
- **THEN** la tabla muestra ambos productos en el orden de la API

#### Scenario: Sin tildes
- **GIVEN** el producto `C-99` "Junta tórica"
- **WHEN** el usuario escribe `TORICA`
- **THEN** la tabla muestra `C-99`

#### Scenario: Solo espacios
- **WHEN** el usuario escribe `"   "`
- **THEN** la tabla muestra todos los productos y el conteo dice "N productos"

### Requirement: Conteo durante la búsqueda
Mientras haya texto de búsqueda o una categoría elegida en el filtro y se vean menos productos que los activos (V < T), el conteo del inventario SHALL decir "V de T productos" (V visibles, T activos); sin búsqueda ni categoría, o cuando los filtros dejan visibles todos los productos (V = T), SHALL decir "T productos" (cambio pedido por el usuario, 2026-11-24).

#### Scenario: Conteo filtrado
- **GIVEN** 12 productos activos, 2 de los cuales contienen `tor`
- **WHEN** el usuario escribe `tor`
- **THEN** el conteo dice "2 de 12 productos"

#### Scenario: Conteo filtrado por categoría
- **GIVEN** 12 productos activos, 3 de la categoría `aceite`
- **WHEN** el usuario elige "Aceite" en el filtro
- **THEN** el conteo dice "3 de 12 productos"

#### Scenario: La búsqueda coincide con todos los productos
- **GIVEN** 12 productos activos y todos contienen `m`
- **WHEN** el usuario escribe `m`
- **THEN** el conteo dice "12 productos" (no "12 de 12 productos")

#### Scenario: Conteo al borrar la búsqueda
- **GIVEN** el filtro de categoría en "Todas las categorías"
- **WHEN** el usuario vacía el campo "Buscar"
- **THEN** el conteo vuelve a "12 productos"

### Requirement: Búsqueda sin coincidencias
Si la búsqueda y el filtro de categoría juntos no dejan ningún producto, `/inventario` SHALL mostrar en lugar de las filas un cartel con el botón "Limpiar filtros", que vacía el campo "Buscar", vuelve el filtro a "Todas las categorías", muestra todos los productos y devuelve el foco al campo "Buscar". El cartel SHALL decir "Ningún producto coincide con «<texto>»" si solo hay búsqueda, "Ningún producto en la categoría «<categoría>»" si solo hay categoría y "Ningún producto coincide con «<texto>» en la categoría «<categoría>»" si hay ambas. Pulsar Escape dentro del campo "Buscar" SHALL vaciar solo la búsqueda.

#### Scenario: Sin coincidencias
- **WHEN** el usuario escribe `xyz` y ningún producto lo contiene
- **THEN** se ve "Ningún producto coincide con «xyz»" y el botón "Limpiar filtros"
- **AND** el conteo dice "0 de 12 productos"

#### Scenario: Categoría sin productos
- **GIVEN** ningún producto activo de la categoría `motor`
- **WHEN** el usuario elige "Motor" en el filtro
- **THEN** se ve "Ningún producto en la categoría «Motor»" y el botón "Limpiar filtros"

#### Scenario: Búsqueda y categoría sin coincidencias
- **GIVEN** `A-01` "Tornillo" sin categoría y ningún producto de `aceite` que contenga `tor`
- **WHEN** el usuario escribe `tor` y elige "Aceite"
- **THEN** se ve "Ningún producto coincide con «tor» en la categoría «Aceite»"

#### Scenario: Limpiar búsqueda
- **WHEN** el usuario pulsa "Limpiar filtros"
- **THEN** el campo queda vacío, el filtro vuelve a "Todas las categorías", se ven todos los productos y el foco está en el campo "Buscar"

#### Scenario: Escape en el campo
- **GIVEN** el campo "Buscar" con `tor` y el filtro en "Aceite"
- **WHEN** el usuario pulsa Escape dentro del campo
- **THEN** el campo queda vacío, el filtro sigue en "Aceite" y se ven todos los productos de esa categoría

#### Scenario: Texto mostrado literal
- **WHEN** el usuario busca `<b>x</b>` sin coincidencias
- **THEN** el cartel muestra ese texto literal, sin interpretarlo como HTML

### Requirement: Búsqueda conservada al actualizar el inventario
Cuando el inventario se recarga tras un nuevo ingreso, una modificación de stock, una orden o una baja, la búsqueda escrita y la categoría elegida en el filtro SHALL conservarse y aplicarse a la lista nueva. Ninguna de las dos SHALL conservarse al volver a abrir la página.

#### Scenario: Recarga tras modificar stock
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario guarda una modificación de stock
- **THEN** el campo sigue con `tor` y la tabla muestra solo las coincidencias con el stock actualizado

#### Scenario: Producto nuevo que no coincide
- **GIVEN** la búsqueda `tor` aplicada
- **WHEN** el usuario crea el producto `N-01` "Arandela"
- **THEN** la alerta de éxito se muestra y `N-01` no aparece en la tabla hasta limpiar los filtros

#### Scenario: Cambio de categoría que saca el producto del filtro
- **GIVEN** el filtro en "Filtro" y `F-01` visible con categoría `filtro`
- **WHEN** el usuario cambia la categoría de `F-01` a "Aceite" con "Modificar stock"
- **THEN** el filtro sigue en "Filtro" y `F-01` deja de verse en la tabla

### Requirement: Exportar el inventario a PDF
"Exportar PDF" en `/inventario` SHALL exportar, según `exportacion-pdf`, exactamente las filas visibles (todas o el resultado de la búsqueda y del filtro de categoría) en el orden de la tabla, con columnas Código, Nombre, Categoría y Stock, el título "Inventario", la cantidad de filas exportadas y la fecha de exportación; con una categoría elegida, la línea del encabezado SHALL empezar con el nombre de esa categoría ("Sin categoría" incluido). El texto de búsqueda y el usuario no se imprimen (revisión pedida por el usuario, 2026-11-24).

#### Scenario: Exportar el resultado de una búsqueda
- **GIVEN** la búsqueda `tor` que muestra `A-01` y `D-07` y el filtro en "Todas las categorías"
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista solo `A-01` y `D-07`, con "2 productos" y sin mostrar «tor»

#### Scenario: Exportar una categoría
- **GIVEN** el filtro en "Aceite" que muestra 3 productos
- **WHEN** el usuario pulsa "Exportar PDF" el 2026-11-24
- **THEN** el documento lista esos 3 productos con su categoría y la línea "Aceite · 3 productos · 2026-11-24"

#### Scenario: Exportar todo el inventario
- **GIVEN** 12 productos, el campo "Buscar" vacío y el filtro en "Todas las categorías"
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento lista los 12 productos con "12 productos"

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

### Requirement: Pantalla de reportes
`/reportes` SHALL mostrar el título "Reportes" y el reporte "Productos usados en órdenes" con los filtros "Desde (obligatorio)", "Hasta (opcional)" (ayuda "Vacío = hoy") y Producto (opcional), y el botón "Generar"; SHALL NOT ofrecer filtro de categoría. El resultado SHALL ser una tabla con las columnas Código, Nombre, Categoría, Cantidad y Órdenes, en el orden de la API, y una línea de resumen (decidido por el usuario al aprobar mockups, 2026-11-24; columna Categoría decidida por el usuario, 2026-11-24). La columna Categoría SHALL mostrar el nombre de la categoría (de `GET /api/categorias`) o "Sin categoría" atenuado; si el catálogo no se puede cargar, la clave.

#### Scenario: Generar con un rango
- **WHEN** el usuario completa Desde `2026-10-01`, Hasta `2026-10-31` y pulsa "Generar"
- **THEN** la interfaz llama a `GET /api/reportes/productos-en-ordenes?desde=2026-10-01&hasta=2026-10-31`, sin `codigo`, y muestra una fila por producto con su categoría, su cantidad total y sus órdenes

#### Scenario: Columna de categoría
- **GIVEN** un reporte con `F-01` (categoría `filtro`) y `A-01` (sin categoría)
- **WHEN** se muestra la tabla
- **THEN** las columnas son Código, Nombre, Categoría, Cantidad y Órdenes, la fila de `F-01` muestra "Filtro" y la de `A-01` "Sin categoría"

#### Scenario: Generar sin Hasta
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario completa Desde `2026-11-01`, deja Hasta vacío y pulsa "Generar"
- **THEN** la llamada no incluye `hasta` y el rango mostrado es "2026-11-01 a 2026-11-24"

#### Scenario: Línea de resumen
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24 con 5 productos
- **THEN** el resumen dice "2026-11-01 a 2026-11-24 · 5 productos" (con 1 producto, "1 producto"; con el filtro `A-01 · Tornillo`, "A-01 · Tornillo · 2026-11-01 a 2026-11-24 · 1 producto"; con Hasta vacío, el rango usa el `hasta` efectivo), igual que la línea del PDF (decidido por el usuario al aprobar mockups, 2026-11-24)

#### Scenario: Cambiar filtros no altera el resultado mostrado
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24
- **WHEN** el usuario cambia Desde sin pulsar "Generar"
- **THEN** la tabla y el rango mostrado siguen siendo los del reporte generado

### Requirement: Estado inicial del reporte
Al abrir `/reportes`, Desde SHALL venir completado con el primer día del mes en curso y Hasta con la fecha de hoy (fecha local), pero el reporte SHALL NOT generarse hasta que el usuario pulse "Generar" (decisión del usuario, 2026-11-24). Hasta entonces SHALL verse, en lugar de la tabla, el cartel neutro "Elegí el período y pulsá «Generar» para ver el reporte." y "Exportar PDF" SHALL estar deshabilitado.

#### Scenario: Apertura sin generar
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario abre `/reportes`
- **THEN** Desde vale `2026-11-01` y Hasta vale `2026-11-24`
- **AND** no se llama a `GET /api/reportes/productos-en-ordenes`, se ve el cartel "Elegí el período y pulsá «Generar» para ver el reporte." y "Exportar PDF" está deshabilitado

#### Scenario: Primera generación
- **GIVEN** la página recién abierta el 2026-11-24 con el mes en curso
- **WHEN** el usuario pulsa "Generar"
- **THEN** la interfaz llama a `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-24` y el cartel inicial deja de verse

### Requirement: Selector de producto del reporte
El filtro Producto SHALL ofrecer "Todos los productos" (sin filtro) y solo los productos de `GET /api/reportes/productos-usados`, es decir, usados en al menos una orden de cualquier fecha (decisión del usuario, 2026-11-24): los activos en un grupo "Activos" y los dados de baja en un grupo "Dados de baja", cada uno como "CÓDIGO · Nombre", ordenados por código; un grupo vacío SHALL NOT mostrarse. Elegir un producto SHALL enviar su código como `codigo`.

#### Scenario: Filtrar por un producto activo
- **WHEN** el usuario elige `A-01 · Tornillo` en "Activos" y pulsa "Generar"
- **THEN** la llamada incluye `codigo=A-01` y la tabla muestra solo `A-01`

#### Scenario: Filtrar por un producto dado de baja
- **GIVEN** `C-99` "Viejo" está dado de baja y se usó x 2 en una orden del 2026-11-12
- **WHEN** el usuario elige `C-99 · Viejo` en el grupo "Dados de baja" con el rango 2026-11-01 a 2026-11-24 y pulsa "Generar"
- **THEN** la llamada incluye `codigo=C-99` y la tabla muestra solo `C-99` con cantidad 2, 1 orden y la marca "dado de baja"

#### Scenario: Productos nunca usados no se ofrecen
- **GIVEN** el producto activo `B-02` nunca se usó en una orden
- **WHEN** el usuario abre el selector
- **THEN** `B-02` no está entre las opciones

#### Scenario: Lista de productos no disponible
- **WHEN** falla `GET /api/reportes/productos-usados` al abrir la página
- **THEN** el selector ofrece solo "Todos los productos" y el reporte se puede generar igual

### Requirement: Productos dados de baja en el resultado
Una fila de un producto dado de baja SHALL mostrar junto al nombre la marca de texto "dado de baja" (no solo un color).

#### Scenario: Dado de baja en el reporte general
- **GIVEN** `C-99` "Viejo" dado de baja se usó en una orden del rango
- **WHEN** se genera el reporte sin filtro de producto
- **THEN** la fila de `C-99` muestra "Viejo" con la marca "dado de baja"

### Requirement: Estados del reporte
Mientras la API no responde, `/reportes` SHALL mostrar "Generando reporte…" y deshabilitar "Generar" y "Exportar PDF". Si la API devuelve 422, SHALL mostrar su `detail` junto a los filtros; ante un error de red o del servidor, SHALL mostrar el error con "Reintentar", que repite la última consulta.

#### Scenario: Generando
- **GIVEN** la API todavía no respondió
- **THEN** se ve "Generando reporte…" y "Generar" y "Exportar PDF" están deshabilitados

#### Scenario: Error del servidor
- **WHEN** la API responde 500 o no hay red
- **THEN** se ve el mensaje de error con el botón "Reintentar", que repite la última consulta

### Requirement: Reporte vacío en pantalla
Si la API devuelve `[]`, `/reportes` SHALL mostrar en lugar de la tabla el cartel "No hay productos usados en órdenes entre AAAA-MM-DD y AAAA-MM-DD" o, si se filtró por un producto, "«CÓDIGO · Nombre» no se usó en órdenes entre AAAA-MM-DD y AAAA-MM-DD", con el `hasta` efectivo.

#### Scenario: Período sin consumo
- **WHEN** el reporte del 2026-10-01 al 2026-10-31 devuelve `[]`
- **THEN** se ve "No hay productos usados en órdenes entre 2026-10-01 y 2026-10-31" y no se ve la tabla

#### Scenario: Producto sin consumo
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el reporte filtrado por `A-01 · Tornillo` desde el 2026-11-01 con Hasta vacío devuelve `[]`
- **THEN** se ve "«A-01 · Tornillo» no se usó en órdenes entre 2026-11-01 y 2026-11-24"

### Requirement: Validación de fechas del reporte en el navegador
Antes de llamar a la API, `/reportes` SHALL validar que Desde esté completo y sea una fecha real `AAAA-MM-DD`, que Hasta, si está completo, también lo sea, y que Desde no sea posterior a Hasta (o a hoy si Hasta está vacío); si no, SHALL mostrar el error junto al campo afectado, marcarlo como inválido, llevar el foco a él y no llamar a la API.

#### Scenario: Desde vacío
- **WHEN** el usuario borra Desde y pulsa "Generar"
- **THEN** se ve "La fecha es obligatoria." bajo Desde y no se llama a la API

#### Scenario: Hasta vacío es válido
- **WHEN** el usuario borra Hasta y pulsa "Generar"
- **THEN** no hay error y se llama a la API sin `hasta`

#### Scenario: Rango invertido
- **WHEN** el usuario pone Desde `2026-11-30`, Hasta `2026-11-01` y pulsa "Generar"
- **THEN** se ve el error de rango bajo Hasta y no se llama a la API

#### Scenario: Desde posterior a hoy sin Hasta
- **GIVEN** la fecha local 2026-11-24
- **WHEN** el usuario pone Desde `2026-12-01`, deja Hasta vacío y pulsa "Generar"
- **THEN** se ve un error de rango bajo Desde y no se llama a la API

### Requirement: Exportar el reporte a PDF
`/reportes` SHALL tener un botón "Exportar PDF" que exporta, según `exportacion-pdf`, solo la tabla del último reporte generado (columnas Código, Nombre, Categoría, Cantidad y Órdenes, con "dado de baja" y "Sin categoría" en texto), sin los filtros. El botón SHALL estar deshabilitado antes de la primera generación, mientras se genera, ante un error o con el reporte vacío.

#### Scenario: Exportar sin filtros en el papel
- **GIVEN** un reporte generado con 5 productos
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** se abre el diálogo de impresión y el documento no muestra los filtros, la navegación ni los botones

#### Scenario: Categoría en el papel
- **GIVEN** un reporte generado con `F-01` (Filtro) y `A-01` (sin categoría)
- **WHEN** el usuario pulsa "Exportar PDF"
- **THEN** el documento tiene la columna Categoría con "Filtro" y "Sin categoría"

#### Scenario: Reporte vacío
- **WHEN** el reporte generado no tiene filas
- **THEN** "Exportar PDF" está deshabilitado

### Requirement: Encabezado del PDF del reporte
El documento exportado del reporte SHALL empezar con el título "Reporte de productos en órdenes" y una sola línea "AAAA-MM-DD a AAAA-MM-DD · N productos" con el `hasta` efectivo del reporte generado, precedida de "CÓDIGO · Nombre · " cuando se filtró por un producto; sin usuario ni hora.

#### Scenario: Encabezado del reporte del mes
- **GIVEN** un reporte generado del 2026-11-01 al 2026-11-24 con 5 productos
- **WHEN** el usuario exporta
- **THEN** el documento empieza con "Reporte de productos en órdenes" y "2026-11-01 a 2026-11-24 · 5 productos"

#### Scenario: Encabezado con Hasta vacío
- **GIVEN** un reporte generado el 2026-11-24 con Desde `2026-11-01` y Hasta vacío, con 3 productos
- **WHEN** el usuario exporta
- **THEN** la línea del encabezado es "2026-11-01 a 2026-11-24 · 3 productos"

#### Scenario: Encabezado de un producto
- **GIVEN** un reporte generado de `A-01 · Tornillo` del 2026-11-01 al 2026-11-24
- **WHEN** el usuario exporta
- **THEN** la línea del encabezado es "A-01 · Tornillo · 2026-11-01 a 2026-11-24 · 1 producto"

### Requirement: Filtro por categoría del inventario
El filtro "Categoría" de `/inventario` SHALL ofrecer "Todas las categorías" (por defecto), cada categoría de `GET /api/categorias` por su nombre y "Sin categoría", y SHALL mostrar, sin llamar a la API, solo los productos activos de la categoría elegida (o sin categoría). Se SHALL combinar con el buscador: una fila se ve solo si cumple ambos criterios. Las filas visibles SHALL conservar el orden de la API.

#### Scenario: Filtrar por una categoría
- **GIVEN** `A-01` (sin categoría), `AC-10` y `AC-20` (`aceite`) y `F-01` (`filtro`)
- **WHEN** el usuario elige "Aceite"
- **THEN** la tabla muestra `AC-10` y luego `AC-20`
- **AND** no se envía ninguna petición a la API

#### Scenario: Sin categoría
- **WHEN** el usuario elige "Sin categoría"
- **THEN** la tabla muestra solo `A-01`

#### Scenario: Combinado con la búsqueda
- **GIVEN** `AC-10` "Aceite 10W40" y `AC-20` "Aceite 20W50" (`aceite`) y `F-01` "Filtro de aceite" (`filtro`)
- **WHEN** el usuario escribe `aceite` y elige "Filtro"
- **THEN** la tabla muestra solo `F-01`

#### Scenario: Volver a todas
- **GIVEN** el filtro en "Aceite"
- **WHEN** el usuario elige "Todas las categorías"
- **THEN** la tabla muestra todos los productos que coinciden con la búsqueda escrita

### Requirement: Filtro por categoría en la nueva orden
Cada línea de componente de "Nueva orden" SHALL tener, antes del producto, un selector de categoría ("Todas" por defecto, cada categoría y "Sin categoría") que limita los productos activos ofrecidos en esa línea. Al cambiar la categoría, el producto elegido SHALL conservarse si pertenece a ella y, si no, la línea SHALL volver a "Elegí un producto…". El filtro de una línea SHALL NOT afectar a las demás.

#### Scenario: Elegir entre todos
- **GIVEN** `A-01` (sin categoría), `AC-10` (`aceite`) y `F-01` (`filtro`)
- **WHEN** el usuario abre el modal y despliega el producto de la línea 1
- **THEN** la categoría de la línea está en "Todas" y el selector ofrece `A-01`, `AC-10` y `F-01`

#### Scenario: Filtrar una línea por categoría
- **WHEN** el usuario elige "Filtro" en la categoría de la línea 2
- **THEN** el selector de producto de la línea 2 ofrece solo `F-01` y el de la línea 1 sigue ofreciendo todos

#### Scenario: Cambiar la categoría con un producto elegido
- **GIVEN** la línea 1 con `AC-10` elegido y la categoría en "Todas"
- **WHEN** el usuario elige "Aceite" y luego "Filtro" en la categoría de esa línea
- **THEN** con "Aceite" `AC-10` sigue elegido y con "Filtro" la línea vuelve a "Elegí un producto…"

#### Scenario: Categoría sin productos activos
- **GIVEN** ningún producto activo de la categoría `motor`
- **WHEN** el usuario elige "Motor" en la categoría de una línea
- **THEN** el selector de producto de esa línea ofrece solo "Elegí un producto…" y una ayuda "No hay productos en esta categoría."

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

### Requirement: Filtro por categoría en la modificación de stock
Cada línea de "Modificar stock" SHALL tener, antes del producto, un filtro con la etiqueta visible "Filtrar por categoría" ("Todas las categorías" por defecto, cada categoría y "Sin categoría") que limita los productos activos y dados de baja ofrecidos en esa línea. Al cambiarlo, el producto elegido SHALL conservarse si pertenece a la categoría y, si no, la línea SHALL volver a "Elegí un producto…". El filtro de una línea SHALL NOT afectar a las demás.

#### Scenario: Elegir entre todos
- **GIVEN** `A-01` (sin categoría, activo), `AC-10` (`aceite`, activo) y `C-99` (`motor`, dado de baja)
- **WHEN** el usuario abre "Modificar stock" y despliega el producto de la línea 1
- **THEN** el filtro de la línea está en "Todas las categorías" y el selector ofrece `A-01` y `AC-10` en "Activos" y `C-99` en "Dados de baja"

#### Scenario: Filtrar una línea por categoría
- **WHEN** el usuario elige "Aceite" en el filtro de la línea 2
- **THEN** el selector de producto de la línea 2 ofrece solo `AC-10`, sin el grupo "Dados de baja", y el de la línea 1 sigue ofreciendo todos

#### Scenario: Filtrar por una categoría con productos dados de baja
- **WHEN** el usuario elige "Motor" en el filtro de una línea
- **THEN** el selector ofrece solo `C-99` dentro del grupo "Dados de baja", sin el grupo "Activos"

#### Scenario: Filtrar por "Sin categoría"
- **WHEN** el usuario elige "Sin categoría" en el filtro de una línea
- **THEN** el selector ofrece solo los productos sin categoría (`A-01`)

#### Scenario: Cambiar el filtro con un producto elegido
- **GIVEN** la línea 1 con `AC-10` elegido, el filtro en "Todas las categorías" y "Fijar en" con el valor propuesto
- **WHEN** el usuario elige "Aceite" y luego "Filtro" en el filtro de esa línea
- **THEN** con "Aceite" `AC-10` sigue elegido con su valor y su resultado, y con "Filtro" la línea vuelve a "Elegí un producto…" como si el usuario lo hubiera deseleccionado

#### Scenario: Categoría sin productos
- **GIVEN** ningún producto, activo ni dado de baja, de la categoría `helices`
- **WHEN** el usuario elige "Hélices" en el filtro de una línea
- **THEN** el selector de producto de esa línea ofrece solo "Elegí un producto…" y la línea muestra la ayuda "No hay productos en esta categoría.", que desaparece al volver a una categoría con productos

#### Scenario: Línea nueva y reapertura
- **WHEN** el usuario agrega una línea, o cierra y vuelve a abrir el modal
- **THEN** el filtro de cada línea nueva arranca en "Todas las categorías"

### Requirement: Filtro de la modificación separado de la categoría del producto
El filtro de una línea de "Modificar stock" SHALL ser solo de presentación: SHALL NOT cambiar el selector "Categoría" de la línea (que define la categoría del producto al guardar) ni enviarse en `POST /api/stock/modificaciones`. Cada línea SHALL mantener ambos controles con etiquetas distintas.

#### Scenario: Filtrar no cambia la categoría a guardar
- **GIVEN** la línea 1 con `AC-10` elegido y su "Categoría" precargada en "Aceite"
- **WHEN** el usuario cambia el filtro de esa línea a "Todas las categorías" y luego a "Aceite"
- **THEN** la "Categoría" de la línea sigue en "Aceite"

#### Scenario: El cuerpo no incluye el filtro
- **GIVEN** la línea 1 con el filtro en "Aceite", `AC-10` elegido y "Categoría" cambiada a "Filtro"
- **WHEN** el usuario guarda
- **THEN** la petición lleva `"categoria": "filtro"` en esa línea y ningún campo del filtro

#### Scenario: Etiquetas accesibles distintas
- **WHEN** la línea 2 se renderiza
- **THEN** el filtro se anuncia como "Filtrar por categoría, línea 2" y el otro selector como "Categoría de la línea 2"

### Requirement: Botón Editar en cada orden
En `/ordenes`, cada orden SHALL tener un botón "Editar" (con nombre accesible "Editar orden OT-XXXX") junto a "Exportar PDF" y "Eliminar", que abre el modal "Editar orden". El botón SHALL NOT imprimirse en el PDF.

#### Scenario: Abrir la edición
- **GIVEN** un usuario con sesión en `/ordenes` con la orden `OT-0043`
- **WHEN** pulsa "Editar" en `OT-0043`
- **THEN** se abre el modal "Editar orden OT-0043" con el foco en el primer campo editable

### Requirement: Modal de edición de orden
El modal "Editar orden" SHALL mostrar el mismo formulario que "Nueva orden" (fecha, "Cliente y embarcación", servicio general con precio, componentes con importe, servicios adicionales con precio y resumen en vivo), precargado con el contenido vigente de la orden, con el número visible en el título y no editable, más el fieldset "Chequeo final". El botón principal SHALL decir "Guardar cambios". Al cancelar o cerrar, SHALL NOT enviarse nada.

#### Scenario: Formulario precargado
- **GIVEN** la orden `OT-0043` con fecha `2026-11-27`, cliente "Juan Pérez", el servicio "Servicio 20 hs" a 4500000, `ACE-01` x 2 a 1200000, el servicio adicional "Limpieza" a 1500000 y el chequeo "Entrega"
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** el formulario muestra esos valores (importes como `45.000,00`, `12.000,00` y `15.000,00`), "Entrega" marcado y el resumen con Subtotal servicios $ 60.000,00, Subtotal ítems $ 12.000,00 y Total $ 72.000,00

#### Scenario: Cancelar
- **GIVEN** el modal "Editar orden OT-0043" con cambios sin guardar
- **WHEN** el usuario pulsa "Cancelar"
- **THEN** el modal se cierra, no se envía ninguna petición y la orden no cambia

#### Scenario: Servicio que ya no está en el catálogo
- **GIVEN** la orden `OT-0043` con el servicio "Servicio 20 hs" y `servicio-20-hs` borrado del catálogo
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** el selector de servicio general muestra "Servicio 20 hs (actual)" elegido, con sus chequeos guardados en "Incluye:"
- **AND** al guardar sin cambiarlo, la orden conserva ese servicio

#### Scenario: Servicio adicional que ya no está en el catálogo
- **GIVEN** la orden `OT-0043` con el servicio adicional del catálogo "Pulido" a 800000, que luego se borró del catálogo
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** "Pulido" aparece como servicio adicional personalizado con su importe `8.000,00`

### Requirement: Stock disponible al editar
En el modal de edición, la etiqueta de cada producto SHALL indicar su stock actual y, si la orden ya lo tenía, la cantidad que la orden ya descontó, porque también se puede usar. Los productos dados de baja que ya están en la orden SHALL aparecer en su línea marcados "(dado de baja)" y no SHALL ofrecerse en líneas nuevas. Como en "Nueva orden", el stock lo valida la API (409) y el error se muestra bajo la línea.

#### Scenario: Etiqueta con lo ya descontado
- **GIVEN** la orden `OT-0043` con `ACE-01` x 2 y `ACE-01` con stock 3
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** la línea de `ACE-01` muestra "(stock 3 + 2 en esta orden)" y debajo la ayuda "Hasta 5: 3 en stock + 2 ya descontados por esta orden."

#### Scenario: Producto dado de baja en la orden
- **GIVEN** la orden `OT-0043` con `C-99` x 2 y `C-99` dado de baja
- **WHEN** se abre "Editar orden OT-0043" y se agrega una línea nueva
- **THEN** la línea de `C-99` lo muestra marcado "(dado de baja)" y el selector de la línea nueva no ofrece `C-99`

#### Scenario: Excede lo disponible
- **GIVEN** el modal "Editar orden OT-0043" con `ACE-01` x 2 y stock 3
- **WHEN** el usuario pone 6 en esa línea, pulsa "Guardar cambios" y la API responde 409
- **THEN** la línea de `ACE-01` muestra "Disponible 3, solicitado 4" con `aria-invalid` y el modal sigue abierto

### Requirement: Chequeo final en el formulario de edición
El fieldset "Chequeo final" SHALL mostrar los seis ítems de la lista fija como casillas con su nombre y, en la misma fila, una caja de importe (mismo formato y validación que los demás importes) habilitada solo si la casilla está marcada; al desmarcar, el importe SHALL vaciarse y deshabilitarse. El resumen en vivo SHALL sumar los importes del chequeo al "Subtotal servicios". Cada casilla y cada importe SHALL tener nombre accesible y objetivos táctiles de al menos 44 px.

#### Scenario: Marcar con precio
- **GIVEN** el modal "Editar orden" con Subtotal servicios $ 60.000,00
- **WHEN** el usuario marca "Combustible" y escribe `8.000` en su importe
- **THEN** el resumen muestra Subtotal servicios $ 68.000,00 y el Total aumenta $ 8.000,00

#### Scenario: Desmarcar
- **GIVEN** "Combustible" marcado con importe `8.000`
- **WHEN** el usuario lo desmarca
- **THEN** su importe queda vacío y deshabilitado y el resumen deja de sumarlo

#### Scenario: Importe inválido
- **GIVEN** "Entrega" marcado
- **WHEN** el usuario escribe `12.5` en su importe y pulsa "Guardar cambios"
- **THEN** el importe muestra "Ingresá un importe válido (ej. 12.500,50)." y no se envía nada

### Requirement: Resultado de la edición
Al guardar, el botón SHALL deshabilitarse mientras espera. Si la API acepta, el modal SHALL cerrarse, la lista SHALL recargarse con los filtros vigentes y un aviso persistente SHALL decir "Orden OT-XXXX actualizada." con cada ajuste de stock (descontado o devuelto, stock resultante, reactivado) o "Sin cambios de stock.". Si rechaza, el modal SHALL quedar abierto con lo cargado y mostrar el error en la línea afectada o en la alerta general; si la orden ya no existe, SHALL decirlo.

#### Scenario: Guardado con ajustes
- **GIVEN** el modal "Editar orden OT-0043" con `ACE-01` x 2 pasado a x 3
- **WHEN** el usuario pulsa "Guardar cambios" y la API acepta
- **THEN** el modal se cierra, `OT-0043` aparece con `ACE-01` x 3 y el aviso dice "Orden OT-0043 actualizada." con "ACE-01 −1 descontada (stock 2)" si el stock era 3

#### Scenario: Guardado con reintegro de un producto dado de baja
- **GIVEN** el modal "Editar orden OT-0043" con `FIL-01` (dado de baja, stock 3) x 1 y el usuario quita esa línea
- **WHEN** pulsa "Guardar cambios" y la API acepta
- **THEN** el aviso incluye "FIL-01 +1 devuelta (stock 4, reactivado)"

#### Scenario: Guardado sin ajustes
- **GIVEN** el modal "Editar orden OT-0043" donde solo cambió el cliente
- **WHEN** pulsa "Guardar cambios" y la API acepta
- **THEN** el aviso dice "Orden OT-0043 actualizada." y "Sin cambios de stock."

#### Scenario: Stock insuficiente
- **GIVEN** el modal "Editar orden OT-0043" y otro usuario dejó `ACE-01` sin stock
- **WHEN** el usuario aumenta `ACE-01` y la API responde 409
- **THEN** el modal sigue abierto con lo cargado y la línea de `ACE-01` muestra el faltante

#### Scenario: Orden borrada mientras se editaba
- **GIVEN** el modal "Editar orden OT-0043" abierto y la orden borrada por otro usuario
- **WHEN** el usuario pulsa "Guardar cambios" y la API responde 404
- **THEN** el modal informa que la orden ya no existe y, al cerrarlo, la lista se recarga sin `OT-0043`

### Requirement: Chequeo final en pantalla
En `/ordenes`, cada orden con chequeo final SHALL mostrar una fila "Chequeo final:" con un chip por ítem marcado ("Combustible · $ 8.000,00" o "Entrega · —"), después de los servicios adicionales; sin ítems marcados la fila SHALL NOT mostrarse.

#### Scenario: Orden con chequeo en pantalla
- **GIVEN** la orden `OT-0043` con el chequeo "Combustible" a 800000 y "Entrega" sin precio
- **WHEN** se muestra `/ordenes`
- **THEN** `OT-0043` tiene la fila "Chequeo final:" con "Combustible · $ 8.000,00" y "Entrega · —"

#### Scenario: Orden sin chequeo
- **GIVEN** la orden `OT-0041` sin chequeo final
- **WHEN** se muestra `/ordenes`
- **THEN** `OT-0041` no tiene fila "Chequeo final:"

### Requirement: Chequeo final completo en el PDF de una orden
El PDF de una orden ("Exportar PDF") SHALL incluir, después de "Servicios adicionales" y antes del resumen, la sección "Chequeo final" con los seis ítems de la lista fija en su orden (pedido del usuario, 2026-11-27). Cada ítem hecho SHALL mostrar "[✓]", su nombre, el texto "Hecho" y su precio ("—" si no tiene). Cada ítem no hecho SHALL mostrar "[ ]", su nombre y el texto "No se hizo", sin precio. La marca SHALL leerse por texto y símbolo, también impresa en blanco y negro.

#### Scenario: PDF con chequeo parcial
- **GIVEN** la orden `OT-0043` con el chequeo "Combustible" a 800000 y "Entrega" sin precio
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0043`
- **THEN** la sección "Chequeo final" lista, en orden, "[✓] Combustible · Hecho · $ 8.000,00", "[ ] Puesta en marcha · No se hizo", "[ ] Check-list y verificación final · No se hizo", "[ ] Prueba en el lago · No se hizo", "[ ] Limpieza de cortesía · No se hizo" y "[✓] Entrega · Hecho · —", antes del resumen
- **AND** el botón "Editar" no aparece en la hoja

#### Scenario: PDF de una orden sin chequeo
- **GIVEN** la orden `OT-0041` sin ningún ítem de chequeo marcado
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0041`
- **THEN** la sección "Chequeo final" lista los seis ítems con "[ ]" y "No se hizo"

#### Scenario: Marca legible sin color
- **GIVEN** la hoja de `OT-0043` impresa en blanco y negro
- **WHEN** se lee la sección "Chequeo final"
- **THEN** cada ítem se distingue como hecho o no hecho por su símbolo y su texto, sin depender del color
