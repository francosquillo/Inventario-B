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
Las páginas protegidas SHALL mostrar una cabecera con el título de texto "Inventario" (sin logo), el usuario de `GET /api/me` y el botón "Cerrar sesión", que SHALL llamar a `POST /api/logout` y navegar a `/`.

#### Scenario: Cerrar sesión
- **GIVEN** el usuario está en `/inventario`
- **WHEN** pulsa "Cerrar sesión"
- **THEN** el navegador queda en `/` y un acceso posterior a `/inventario` vuelve al login

#### Scenario: Usuario visible
- **WHEN** el `admin` abre `/inventario` en escritorio
- **THEN** la cabecera muestra "Usuario: admin"

### Requirement: Tabla de inventario
`/inventario` SHALL mostrar primero la barra de acciones ("Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes") y la tabla de productos activos de `GET /api/inventario` (código, nombre, stock, acción "Eliminar") en el orden de la API, con la cantidad de productos y el stock 0 resaltado. La web SHALL NOT ofrecer los antiguos "Ingreso de stock" ni "Egreso de stock".

#### Scenario: Producto sin stock
- **GIVEN** los productos activos `A-01` (stock 5) y `B-10` (stock 0)
- **WHEN** se abre `/inventario`
- **THEN** la tabla muestra `A-01` y luego `B-10`, el stock de `B-10` resaltado como sin stock y el texto "2 productos"

#### Scenario: Cargando
- **GIVEN** `GET /api/inventario` todavía no respondió
- **THEN** se ve el estado "Cargando inventario…" en lugar de la tabla

#### Scenario: Botones nuevos
- **WHEN** se abre `/inventario`
- **THEN** la barra muestra "Nuevo ingreso" y "Modificar stock" y no muestra "Ingreso de stock" ni "Egreso de stock"
- **AND** ningún script de la web llama a `/api/stock/ingreso` ni a `/api/stock/egreso`

### Requirement: Inventario vacío
Si `GET /api/inventario` devuelve una lista vacía, `/inventario` SHALL mostrar el cartel "Todavía no hay productos" con la indicación de crear el primero con "Nuevo ingreso", en lugar de una tabla vacía.

#### Scenario: Sin productos
- **GIVEN** ningún producto activo
- **WHEN** se abre `/inventario`
- **THEN** se ve "Todavía no hay productos" y no se ve la tabla

### Requirement: Modal de nueva orden
El modal "Nueva orden" SHALL pedir número, fecha y entre 1 y 100 líneas de componente (producto activo y cantidad) que se agregan y quitan; con éxito SHALL enviar `POST /api/ordenes`, cerrarse, recargar el inventario y mostrar "Orden X creada." con un enlace a `/ordenes`.

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
`/ordenes` SHALL mostrar un enlace "← Inventario", filtros opcionales Desde, Hasta y Número, y la lista de `GET /api/ordenes` en el orden de la API con número, fecha y componentes (código, nombre y cantidad, incluidos productos dados de baja). Los filtros vacíos SHALL NOT enviarse.

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
El modal "Nuevo ingreso" SHALL pedir Código, Nombre y Stock (los tres obligatorios; el stock puede ser 0), enviar `POST /api/productos` y, con éxito, cerrarse, recargar el inventario y mostrar una alerta de éxito que diga si el producto fue creado o reactivado.

#### Scenario: Producto nuevo con stock cero
- **GIVEN** ningún producto `N-01`
- **WHEN** el usuario crea `N-01` "Arandela 6mm" con stock 0
- **THEN** el modal se cierra, la tabla muestra `N-01` con stock 0 resaltado y se ve "Producto creado: N-01 · Arandela 6mm (stock 0)."

#### Scenario: Código dado de baja
- **GIVEN** el producto dado de baja `C-99`
- **WHEN** el usuario escribe `C-99` en Código
- **THEN** el modal avisa, sin impedir el envío, "Este código está dado de baja: se va a reactivar con el nombre y el stock que indiques."
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
El modal "Modificar stock" SHALL pedir de 1 a 100 líneas que se agregan y quitan; cada línea elige un producto, un modo ("Fijar en" o "Sumar") con su valor y, opcionalmente, un nombre nuevo. Con éxito SHALL enviar `POST /api/stock/modificaciones`, cerrarse, recargar el inventario y mostrar el resumen.

#### Scenario: Una línea fijando el stock
- **GIVEN** `A-01` "Tornillo M8" con stock 7
- **WHEN** el usuario elige `A-01`, deja "Fijar en" y escribe 12
- **THEN** la línea muestra "Stock actual 7 → 12" y, al guardar, la tabla muestra `A-01` con stock 12

#### Scenario: Valor propuesto al fijar
- **WHEN** el usuario elige un producto con stock 7 en modo "Fijar en"
- **THEN** el campo del valor se propone en 7, de modo que cambiar solo el nombre no altera el stock

#### Scenario: Varias líneas con modos distintos
- **WHEN** el usuario fija `A-01` en 12, suma 4 a `B-10` y renombra `C-03`
- **THEN** se envía una sola petición con las tres líneas en ese orden

#### Scenario: Agregar y quitar líneas
- **WHEN** el usuario pulsa "Agregar producto" y luego "Quitar" en una línea
- **THEN** se agrega una línea vacía y luego se quita, nunca quedando menos de una línea, y con 100 líneas "Agregar producto" queda deshabilitado

### Requirement: Selector de productos de la modificación
El selector de producto de cada línea SHALL ofrecer los productos activos (`GET /api/inventario`) y, en un grupo aparte "Dados de baja", los de `GET /api/productos/inactivos`, cada uno como "CÓDIGO · Nombre (stock N)". Un producto ya elegido en otra línea SHALL quedar deshabilitado en las demás.

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

### Requirement: Resumen de la modificación
Tras una modificación exitosa, la página SHALL mostrar una alerta persistente con un ítem por línea: código, stock anterior → nuevo (o "sin cambios"), el nombre anterior → nuevo si cambió y la marca "reactivado" solo donde la respuesta trae `reactivado: true`.

#### Scenario: Resumen con reactivación
- **WHEN** la API responde con `A-01` (fijar, 7 → 12, nombre "Tornillo" → "Tornillo M8") y `C-99` (sumar, 2 → 5, `reactivado: true`)
- **THEN** la alerta dice "Stock modificado (2 productos)" y lista "A-01 · Tornillo M8: 7 → 12 · nombre antes: Tornillo" y "C-99 · Junta: 2 → 5 (+3) · reactivado"

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
