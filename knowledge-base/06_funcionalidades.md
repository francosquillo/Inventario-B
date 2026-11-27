# Funcionalidades

Organizadas por épica y por historia de usuario (US-NNN). El campo "Paso" mapea a 11_plan_de_pasos_y_despliegue.md. Los pasos 1-4b entregan la API FastAPI local (Fase 1, sin CLI), verificada en `/docs` y con tests; el Paso 5 agrega el frontend web que consume esa API; el Paso 6 migra a Supabase (C-07); el Paso 7 la despliega.

## Épica 1: Acceso y base (Paso 1; web en Paso 5)

### US-001 — Iniciar sesión
**Como** usuario
**Quiero** loguearme con usuario y contraseña
**Para** acceder al sistema de forma controlada

**Paso**: 1 (API), 5 (web)

**Criterios de aceptación**:
- [ ] `POST /api/login` con credenciales válidas responde 200 y emite la cookie de sesión firmada; `GET /api/me` devuelve el usuario. En web el campo es `type="password"`.
- [ ] Con credenciales inválidas responde 401 con mensaje genérico y no se emite sesión.
- [ ] `POST /api/logout` invalida la sesión.
- [ ] Existe el usuario `admin` tras inicializar la base, con contraseña hasheada.
- [ ] Sin sesión, todo endpoint protegido responde 401.

**Reglas relacionadas**: RN-AU-01, RN-AU-02, RN-AU-03, RN-AU-04, RN-AU-05, RN-AU-06, RN-SE-06

### US-002 — Inicializar la base de datos
**Como** desarrollador/operador
**Quiero** que la base se cree sola con sus tablas y el seed
**Para** arrancar el sistema sin pasos manuales

**Paso**: 1 (SQLite al arrancar la app), 5 (`schema.sql`)

**Criterios de aceptación**:
- [ ] Al arrancar la app (lifespan de FastAPI) la inicialización es idempotente y, la primera vez, se crean `usuarios`, `productos`, `ordenes`, `orden_items`, `movimientos`.
- [ ] Se crea `admin` si no existe; no se duplica en arranques posteriores.
- [ ] La contraseña inicial proviene de `ADMIN_DEFAULT_PASSWORD`, no del código; si falta, se genera aleatoria y se imprime UNA sola vez en la consola del servidor (log de uvicorn) en la primera inicialización.

**Reglas relacionadas**: RN-AU-02, RN-AU-04, RN-SE-01

## Épica 2: Inventario

### US-003 — Ver inventario general
**Como** usuario
**Quiero** ver la lista de productos con código, nombre y stock
**Para** saber qué tengo disponible

**Paso**: 1 (API), 5 (tabla dinámica)

**Criterios de aceptación**:
- [ ] Se listan solo productos activos.
- [ ] Un producto con stock 0 sigue apareciendo.
- [ ] `GET /api/inventario` responde 200 con la lista de productos; si no hay productos, la lista vacía es explícita (y la web mostrará mensaje de inventario vacío).
- [ ] Sin sesión responde 401.

**Reglas relacionadas**: RN-PR-02, RN-PR-05

### US-004 — Ingresar stock (Nuevo ingreso)
**Como** usuario
**Quiero** dar de alta un producto con código, nombre y stock inicial
**Para** mantener el inventario al día

**Paso**: 2 (API de ingreso), 5 (modal), C-06b (alta explícita y modal "Nuevo ingreso")

**Criterios de aceptación**:
- [ ] `POST /api/productos` con código, nombre y stock (0 a 10.000) obligatorios crea el producto activo y responde 201 con `creado`/`reactivado`; con stock > 0 registra un `ingreso`, con stock 0 ningún movimiento.
- [ ] Código de un producto activo → 409 "Ya existe un producto con código 'X'.".
- [ ] Código de un producto dado de baja → se reactiva con el nombre y el stock nuevos (`reactivado: true`); `ajuste` si el stock cambia.
- [ ] Datos faltantes o stock inválido → 422 en español; nada se modifica.
- [ ] La web (modal "Nuevo ingreso") usa `POST /api/productos` y avisa si el código figura dado de baja.
- [ ] `POST /api/stock/ingreso` (código, cantidad > 0, nombre si no existe) sigue disponible solo por API; ya no se usa desde la web.

**Reglas relacionadas**: RN-ST-01, RN-ST-03, RN-ST-04, RN-ST-05, RN-PR-01, RN-PR-06, RN-PR-07, RN-PR-08, RN-PR-09, RN-PR-10, RN-VA-01, RN-VA-02

### US-005 — Modificar stock (y egreso manual)
**Como** usuario
**Quiero** corregir el stock de uno o varios productos (fijarlo en un valor o sumar unidades) y descontar sin crear una orden
**Para** que el stock refleje la realidad

**Paso**: 2 (API de egreso), 5 (modal), C-06b (modal "Modificar stock")

**Criterios de aceptación**:
- [ ] `POST /api/stock/modificaciones` recibe 1 a 100 líneas `{codigo, modo: fijar|sumar, stock|cantidad, nombre?}` y es todo o nada.
- [ ] "Fijar en" (0 a 10.000) registra un `ajuste` con stock anterior y nuevo si cambia; "Sumar" (1 a 10.000) registra un `ingreso`; el nombre es opcional y no genera movimiento.
- [ ] Se pueden modificar también productos dados de baja: se reactivan solo si el stock cambia y queda > 0.
- [ ] Errores por línea ("Línea N: ..."), producto repetido → 422, códigos inexistentes → 404 con `codigos`; el stock nunca queda negativo.
- [ ] `GET /api/productos/inactivos` alimenta el selector de la web.
- [ ] (C-06h2, solo web) Cada línea tiene un filtro "Filtrar por categoría" antes del producto ("Todas las categorías" por defecto, cada categoría y "Sin categoría") que acota ambos grupos del selector (activos y dados de baja). Al cambiarlo, el producto elegido se conserva si pertenece a la categoría; si no, la línea vuelve a "Elegí un producto…". Si la categoría no tiene productos, la línea muestra "No hay productos en esta categoría.". El filtro es solo de presentación: no cambia la "Categoría" de la línea ni se envía en `POST /api/stock/modificaciones`.
- [ ] `POST /api/stock/egreso` (cantidad entera > 0 y ≤ stock, `egreso` sin motivo) sigue disponible solo por API; ya no se usa desde la web.

**Reglas relacionadas**: RN-ST-02, RN-ST-03, RN-ST-04, RN-ST-05, RN-ST-07, RN-ST-08, RN-ST-09, RN-ST-10, RN-PR-02, RN-VA-01

## Épica 3: Órdenes de trabajo

### US-006 — Crear orden
**Como** usuario
**Quiero** crear una orden con número, fecha y componentes
**Para** que el stock se descuente automáticamente

**Paso**: 3 (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `POST /api/ordenes`: número único y fecha `YYYY-MM-DD` válida, enviada en el cuerpo.
- [ ] Al menos 1 componente; cantidades enteras > 0; solo productos activos seleccionables.
- [ ] Si algún componente no tiene stock suficiente, se rechaza toda la orden y no se descuenta nada (el mensaje indica cuáles).
- [ ] Si alcanza, se descuentan todos los componentes y se crea la orden atómicamente.
- [ ] No se generan filas en `movimientos` por la orden.
- [ ] (C-06g) Campo opcional `servicio` (clave del catálogo o `null`): el servicio se guarda como snapshot (nombre y todos sus chequeos) en la misma transacción; si no existe, se rechaza con 422 "El servicio general 'x' no existe." sin tocar stock. Ver US-017.
- [ ] (C-06h) Cada componente y cada servicio adicional aceptan un `precio` opcional en centavos (≥ 0); `precio_servicio` opcional para el servicio general. Sin precio = `NULL`. Ver US-019.
- [ ] (C-06h) Campos opcionales de cliente y embarcación (`cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso`, `fecha_egreso`). Ver US-018.

**Reglas relacionadas**: RN-OR-01, RN-OR-02, RN-OR-03, RN-OR-04, RN-OR-05, RN-OR-06, RN-OR-18, RN-OR-19, RN-ST-06, RN-VA-01, RN-VA-02, RN-VA-03

### US-007 — Listar órdenes
**Como** usuario
**Quiero** listar órdenes, todas, por rango de fechas o buscar una por su número
**Para** consultar el historial

**Paso**: 4 (API), 5 (pantalla `/ordenes`)

**Criterios de aceptación**:
- [ ] `GET /api/ordenes` sin filtro lista todas.
- [ ] Con `?desde&hasta` (`YYYY-MM-DD`), se incluyen ambos extremos; `desde == hasta` busca un solo día.
- [ ] `desde` y `hasta` son opcionales por separado: solo `desde` = "de esa fecha en adelante", solo `hasta` = "hasta esa fecha"; parámetro vacío = sin filtro (mismo criterio que `GET /api/movimientos` en C-02).
- [ ] Búsqueda por número de orden (`?numero=X`, RN-OR-01): coincidencia exacta del número normalizado (recorte + MAYÚSCULAS). Se combina con las fechas por AND. Número inexistente → 404 "No existe una orden con número 'X'."; número existente fuera del rango → `[]`. Parámetro vacío = sin filtro.
- [ ] Orden de la lista: la más nueva primero (fecha de la orden DESC, luego id DESC).
- [ ] Fecha inválida o desde > hasta se rechaza con mensaje claro.
- [ ] Cada orden muestra número, fecha y componentes con cantidades (incluso de productos dados de baja).
- [ ] (C-06g) Cada orden con servicio general muestra su nombre y sus chequeos tal como quedaron al crearla, aunque el catálogo haya cambiado después; sin servicio, no hay fila.

- [ ] (C-06h) Cada orden muestra sus datos del cliente y la embarcación (ingreso y egreso en su fila), sus precios por línea y el resumen de subtotales y total.

**Reglas relacionadas**: RN-OR-07, RN-OR-19, RN-OR-22, RN-OR-23, RN-OR-25, RN-PR-04, RN-VA-03

### US-008 — Borrar orden
**Como** usuario
**Quiero** borrar una orden cargada por error
**Para** corregir errores de carga

**Paso**: 4b (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `DELETE /api/ordenes/{numero}?reintegrar=true|false`: la orden se identifica por su número (no por id); el parámetro `reintegrar` es obligatorio en cada llamada (sin valor por defecto); si falta, está repetido o no es `true`/`false`, se rechaza con 422. Número inexistente → 404.
- [ ] La confirmación previa es del frontend (modal, Paso 5); la API no tiene paso de confirmación propio (IN-02).
- [ ] Si se reintegra, devolución y borrado son atómicos (una transacción); si no, solo se borra la orden. Ninguna de las dos opciones genera movimientos de stock.
- [ ] Reintegrar a un producto inactivo lo reactiva y le suma las unidades (RN-OR-12).

**Reglas relacionadas**: RN-OR-08, RN-OR-09, RN-VA-05

### US-009 — Borrar producto
**Como** usuario
**Quiero** dar de baja un producto
**Para** que no aparezca más en el inventario ni en nuevas órdenes

**Paso**: 4b (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `DELETE /api/productos/{codigo}`; la confirmación previa es del frontend (Paso 5).
- [ ] El borrado es lógico (`activo = 0`); el stock y el historial se conservan. Se reactiva al ingresar stock con su código o al reintegrar una orden que lo usaba.
- [ ] Desaparece del inventario y de la selección de componentes.
- [ ] Las órdenes históricas lo siguen mostrando.

**Reglas relacionadas**: RN-PR-03, RN-PR-04, RN-PR-05, RN-VA-05

## Épica 3b: Búsqueda, exportación y reportes (C-06c, C-06d)

### US-012 — Buscar productos en el inventario
**Como** usuario
**Quiero** filtrar el inventario escribiendo un código o parte del nombre
**Para** encontrar rápido una pieza sin recorrer toda la lista

**Paso**: 5c (solo frontend; sin endpoints nuevos)

**Criterios de aceptación**:
- [ ] El filtro se aplica en el navegador sobre la lista ya cargada, por código o nombre parcial, sin distinguir mayúsculas ni acentos.
- [ ] Se muestra el conteo "N productos"; con filtro activo que reduce la lista, "V de N productos" (solo cuando V < N).
- [ ] Sin coincidencias se muestra un mensaje y el botón "Limpiar búsqueda"; la tecla Escape también limpia el filtro.
- [ ] La búsqueda se conserva al recargar la lista (tras ingreso, modificación, orden o borrado).

**Reglas relacionadas**: RN-PR-02

### US-013 — Exportar a PDF
**Como** usuario
**Quiero** exportar el inventario visible y cada orden a PDF
**Para** imprimirlos o archivarlos

**Paso**: 5c (solo frontend; sin PDF en el servidor)

**Criterios de aceptación**:
- [ ] "Exportar PDF" abre el diálogo de impresión del navegador (el usuario elige "Guardar como PDF"); no hay endpoint ni dependencia de PDF en el servidor.
- [ ] PDF de inventario: solo las filas visibles (respeta la búsqueda), encabezado "Inventario" y "N productos · YYYY-MM-DD".
- [ ] Cada orden tiene su botón "Exportar PDF" (no hay exportación de la lista completa); encabezado "Orden OT-XXXX" y "Fecha: YYYY-MM-DD · N componentes".
- [ ] Página clara, sin controles ni columna de acciones; stock 0 se imprime "0 (sin stock)"; los encabezados de tabla se repiten en cada página.
- [ ] La lógica vive en el módulo reutilizable `static/js/exportar.js` (lo reutilizará C-06d).

### US-014 — Reporte de productos usados en órdenes por rango de fechas
**Como** usuario
**Quiero** ver cuánto se usó de cada producto en las órdenes de un rango de fechas
**Para** saber qué piezas se consumen más y planificar compras

**Paso**: 5d (pantalla `/reportes`; consulta de solo lectura, sin cambios de esquema)

**Criterios de aceptación**:
- [ ] Hay una pestaña "Reportes" (`/reportes`); "Desde" es obligatorio y "Hasta" opcional (vacío = hoy, hora local UTC-03:00); ambas fechas `YYYY-MM-DD` se validan en frontend y backend y desde <= hasta.
- [ ] Los campos arrancan con el mes en curso, pero el reporte se genera solo al pulsar "Generar".
- [ ] Filtro opcional por un solo producto: el selector lista solo productos usados en alguna orden, agrupados en "Activos" y "Dados de baja"; un código desconocido devuelve el reporte vacío.
- [ ] La tabla muestra Código, Nombre, Cantidad (suma en el rango) y Órdenes (cantidad de órdenes en que aparece), ordenada por cantidad descendente y luego por código; el rango es inclusivo sobre la fecha de la orden.
- [ ] Los productos dados de baja se incluyen y se marcan "dado de baja".
- [ ] "Exportar PDF" reutiliza `static/js/exportar.js`: encabezado "Reporte de productos en órdenes" y "AAAA-MM-DD a AAAA-MM-DD · N productos" (con filtro, prefijado "CÓDIGO · Nombre · "); nombre de archivo `reporte-AAAA-MM-DD_AAAA-MM-DD`.
- [ ] Endpoints de solo lectura `GET /api/reportes/productos-en-ordenes` (`desde`, `hasta`, `codigo`) y `GET /api/reportes/productos-usados` (para el selector).

**Reglas relacionadas**: RN-VA-05, RN-PR-03

## Épica 3c: Categorías de productos (C-06e)

### US-015 — Clasificar productos por categoría
**Como** usuario
**Quiero** asignar una categoría (motor, aceite, filtro u otras) a cada producto y filtrar por ella
**Para** ubicar rápido las piezas de un tipo, también al armar una orden

**Paso**: 5e (cambia el esquema: tabla `categorias` + `productos.categoria_id`; migración idempotente)

**Criterios de aceptación**:
- [ ] La categoría es opcional; los productos existentes quedan "Sin categoría" tras la migración, sin perder datos.
- [ ] "Nuevo ingreso" y cada línea de "Modificar stock" tienen un selector de categoría (en Modificar stock se precarga la actual); reactivar por Nuevo ingreso reemplaza la categoría.
- [ ] El inventario muestra la columna "Categoría" y un filtro (Todas / categorías / Sin categoría) combinable con el buscador; conteo "V de N productos"; sin coincidencias ofrece "Limpiar filtros".
- [ ] "Exportar PDF" del inventario imprime las filas visibles con la columna Categoría; con categoría elegida el encabezado la incluye ("Aceite · 3 productos · AAAA-MM-DD"). El reporte de `/reportes` y su PDF suman la columna Categoría (sin filtro por categoría).
- [ ] En "Nueva orden" cada línea tiene un filtro de categoría que acota los productos del selector; el cuerpo de `POST /api/ordenes` no cambia.
- [ ] `GET /api/categorias` lista el catálogo; `POST /api/categorias` crea y `PATCH /api/categorias/{clave}` renombra (solo por API, sin pantalla ni borrado).

**Reglas relacionadas**: RN-PR-11, RN-PR-12, RN-PR-13, RN-PR-14

## Épica 3d: Procesos de órdenes y borrado de categorías (C-06f)

### US-016 — Registrar los procesos hechos en una orden
**Como** usuario
**Quiero** marcar en cada orden los procesos hechos a la lancha (cambio de motor, cambio de filtro, limpieza u otros)
**Para** dejar constancia de qué se hizo, además de qué piezas se usaron

**Paso**: 5f (cambia el esquema: tablas `procesos` y `orden_procesos`; migración idempotente)

**Criterios de aceptación**:
- [ ] Los procesos son opcionales y pueden ser varios; las órdenes existentes quedan sin procesos tras la migración, sin perder datos.
- [ ] "Nueva orden" tiene un bloque "Procesos" con líneas (Agregar proceso / Quitar): cada una elige un proceso del catálogo o "Personalizado" (cuadro de texto, hasta 10, 1 a 60 caracteres); el mismo proceso del catálogo en dos líneas cuenta una vez.
- [ ] Un personalizado no puede igualar un proceso del catálogo ni repetirse; no se agrega al catálogo.
- [ ] La orden y sus procesos se crean en una sola transacción; borrar la orden borra sus procesos.
- [ ] `/ordenes` muestra una fila "Procesos:" por orden (omitida si no tiene) y el PDF de una orden suma el bloque "Procesos realizados" debajo de los componentes.
- [ ] Renombrar o borrar un proceso del catálogo no cambia las órdenes pasadas.
- [ ] Catálogo de procesos por API (sin pantalla): `GET`/`POST /api/procesos`, `PATCH`/`DELETE /api/procesos/{clave}`; `DELETE /api/categorias/{clave}` borra una categoría sin productos (409 si alguno, activo o dado de baja, la usa).

**Reglas relacionadas**: RN-OR-13..RN-OR-17, RN-PR-15

## Épica 3e: Servicios generales de órdenes (C-06g)

### US-017 — Servicio general con chequeos incluidos
**Como** usuario
**Quiero** asignar a una orden un servicio general (por ejemplo, "Servicio 20 hs") que trae una lista de chequeos incluidos, y administrar ese catálogo
**Para** dejar constancia de qué servicio se hizo y qué chequeos incluye

**Paso**: 5g (cambia el esquema: tablas `servicios_generales`, `servicio_chequeos`, `orden_servicio` y `orden_servicio_chequeos`; migración aditiva)

**Criterios de aceptación**:
- [ ] El servicio general es opcional y como máximo uno por orden; las órdenes existentes quedan sin servicio tras la migración, sin perder datos.
- [ ] "Nueva orden" tiene un bloque "Servicio general" entre la fecha y "Componentes": un selector con "Sin servicio general" (por defecto) y los servicios del catálogo; al elegir uno se listan sus chequeos (solo lectura).
- [ ] El servicio y sus chequeos se crean en la misma transacción que el descuento de stock; borrar la orden borra su servicio.
- [ ] `/ordenes` muestra una fila "Servicio general:" bajo la cabecera de cada orden con servicio (antes de "Procesos:"); el PDF de una orden muestra el bloque "Servicio general" primero, antes de la tabla de componentes.
- [ ] Renombrar, cambiar chequeos o borrar un servicio del catálogo no cambia las órdenes pasadas.
- [ ] Botón "Servicios generales" junto al título de `/ordenes` que abre un modal para listar, crear, editar y borrar servicios; cada servicio tiene de 1 a 30 chequeos, sin repetir, y el nombre de hasta 60 caracteres.
- [ ] Catálogo también por API: `GET`/`POST /api/servicios-generales`, `PATCH`/`DELETE /api/servicios-generales/{clave}`.

**Reglas relacionadas**: RN-OR-18, RN-OR-19, RN-OR-20, RN-OR-21

## Épica 3f: Datos del cliente y precios de la orden (C-06h)

### US-018 — Datos del cliente y de la embarcación
**Como** usuario
**Quiero** registrar en cada orden a quién pertenece la embarcación y cuándo entra y sale del taller
**Para** tener el dato del cliente y las fechas de estadía

**Paso**: 6 (cambia el esquema: siete columnas nuevas en `ordenes`; migración aditiva)

**Criterios de aceptación**:
- [ ] Cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso son opcionales; se validan solo si se cargan.
- [ ] Cliente hasta 80 caracteres; casco, motor y trailer hasta 60; celular de 6 a 20 caracteres con solo dígitos, espacios, `+`, `-` y paréntesis.
- [ ] Fechas de ingreso y egreso en `YYYY-MM-DD` reales; con ambas, egreso ≥ ingreso. No tienen relación con la fecha de la orden, que queda como estaba.
- [ ] "Nueva orden" muestra el bloque "Cliente y embarcación" (en ese orden: cliente, celular, casco, motor, trailer y las dos fechas); la validación del navegador es igual que la de la API.
- [ ] `/ordenes` y el PDF muestran los datos; las órdenes existentes quedan sin datos tras la migración.

**Reglas relacionadas**: RN-OR-22, RN-OR-23

### US-019 — Precios de la orden y total
**Como** usuario
**Quiero** tipear el precio del servicio general, de cada ítem y de cada servicio adicional, y ver subtotales y total
**Para** cobrarle al cliente

**Paso**: 6 (cambia el esquema: columna `precio_centavos` en `orden_items`, `orden_procesos` y `orden_servicio`; migración aditiva)

**Criterios de aceptación**:
- [ ] Precios opcionales, en pesos en la web (`12.500`, `12.500,50`, `$ 12.500`; `12.5` es inválido) y en centavos enteros en la API; entre 0 y $ 999.999.999,99.
- [ ] Vacío = sin precio, distinto de 0. En ítems el precio es el importe de la línea.
- [ ] "Procesos" se llama "Servicios adicionales" en la interfaz (la API y las tablas siguen diciendo "procesos"); cada uno tiene su precio.
- [ ] "Nueva orden" muestra "Subtotal servicios", "Subtotal ítems" y "Total", que se actualizan al tipear; un precio vacío cuenta 0.
- [ ] `/ordenes` y el PDF muestran precios por línea y el resumen de subtotales y total de cada orden.
- [ ] Precios y datos se guardan junto con la orden y el descuento de stock en la misma transacción (todo o nada).

**Reglas relacionadas**: RN-OR-24, RN-OR-25, RN-OR-26

## Épica 4: Web y despliegue

### US-010 — Migración a Supabase y frontend web
**Como** usuario
**Quiero** operar el sistema desde el navegador
**Para** no depender de la Swagger UI ni de herramientas técnicas

**Paso**: 5

**Criterios de aceptación**:
- [ ] La API FastAPI de Fase 1 (endpoints JSON `/api/...` con modelos Pydantic, ya existente) pasa a usar repositorios Supabase sin modificar los services ni el contrato de los endpoints.
- [ ] Frontend con login (contraseña oculta), dashboard con tabla dinámica y modales para ingreso, egreso, crear orden, listar órdenes y borrados.
- [ ] Validaciones en frontend y backend.
- [ ] Sesión por cookie firmada (`SessionMiddleware`) con `SECRET_KEY`; la dependencia `get_current_user` devuelve 401 sin sesión.
- [ ] `schema.sql` incluye tablas y funciones RPC atómicas.

**Reglas relacionadas**: RN-AU-03, RN-VA-04, RN-SE-02, RN-SE-03, RN-SE-05

### US-011 — Desplegar en Vercel
**Como** operador
**Quiero** publicar la app en Vercel con una guía paso a paso
**Para** acceder desde cualquier lugar

**Paso**: 6

**Criterios de aceptación**:
- [ ] Estructura `api/index.py`, `static/`, `vercel.json`, `requirements.txt`, `.env.example`, `.gitignore`.
- [ ] README con guía: Supabase, `schema.sql`, GitHub, Vercel, variables de entorno, verificación.
- [ ] Ningún secreto en el repositorio.

**Reglas relacionadas**: RN-SE-01, RN-SE-02, RN-SE-04

## Backlog (fuera de v1)

Roles, edición de órdenes y productos, alertas de stock bajo, motivo en movimientos, vista del historial de movimientos.
