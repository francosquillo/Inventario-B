# Flujos Principales

Cada flujo describe la interacción entre el adaptador (API FastAPI), services y repositorio. En Fase 1 se invoca desde la Swagger UI (`/docs`) o `TestClient`; en Fase 2 desde el frontend. Services y endpoints son los mismos en ambas fases.

## Flujo 1: Login
**Disparador**: el usuario ejecuta `POST /api/login` desde `/docs` (Fase 1) o abre la página de login (Fase 2).
**Actor**: Usuario.

**Pasos**:
1. El adaptador recibe usuario y contraseña en el cuerpo JSON.
2. AuthService busca el usuario en el repositorio.
3. Recalcula PBKDF2 con el salt almacenado y compara en tiempo constante.
4. Éxito: FastAPI (`POST /api/login`) guarda `usuario_id` en la cookie firmada (`SessionMiddleware`); en `/docs` el navegador reenvía la cookie same-origin, así los demás endpoints funcionan; en Fase 2 el JS de `static/login.html` redirige a `/inventario` (sirve `static/index.html`). Sin sesión, los endpoints responden 401 (`Depends(get_current_user)`) y el JS redirige al login.

```
Usuario → Adaptador → AuthService → UsuarioRepo
                                  ← usuario (hash, salt)
        ← sesión (cookie firmada)
```

**Casos de error**:
- Usuario inexistente o contraseña incorrecta → mensaje genérico (RN-AU-05).
- Campos vacíos → validación RN-VA-02.

## Flujo 2: Ingreso de stock
> Desde C-06b la web usa los Flujos 2b y 2c; `POST /api/stock/ingreso` y `/egreso` (Flujos 2 y 3) quedan solo por API.

**Disparador**: `POST /api/stock/ingreso` (`/docs`; solo API desde C-06b).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código y cantidad; valida cantidad entera > 0.
2. StockService busca el producto por código.
3. Existe y activo → suma. Existe e inactivo → reactiva y suma. No existe → exige `nombre` en el cuerpo y crea.
4. En una sola operación atómica: actualiza stock y registra movimiento `ingreso`.

```
Usuario → Adaptador → StockService → ProductoRepo / MovimientoRepo
                                    (transacción o RPC)
        ← producto actualizado
```

**Casos de error**:
- Cantidad inválida → rechazo (RN-VA-01).
- Producto nuevo sin nombre → rechazo (RN-PR-07).
- Falla de persistencia → rollback, sin estado parcial.

## Flujo 3: Egreso manual de stock
**Disparador**: `POST /api/stock/egreso` (`/docs`; solo API desde C-06b).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código y cantidad.
2. StockService verifica que el producto exista, esté activo y que 0 < cantidad ≤ stock.
3. Atómico: descuenta stock y registra movimiento `egreso`.

**Casos de error**:
- Producto inexistente/inactivo → mensaje claro.
- Cantidad > stock → rechazo, stock sin cambios (RN-ST-02).
- Concurrencia: en Postgres el descuento usa `UPDATE ... WHERE stock >= cantidad` dentro de la función RPC para evitar negativos.

## Flujo 2b: Nuevo ingreso (alta de producto, C-06b)
**Disparador**: `POST /api/productos` / modal "Nuevo ingreso".
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código, nombre y stock (0 a 10.000), los tres obligatorios; normaliza el código y recorta el nombre.
2. Código nuevo → crea el producto activo; con stock > 0 registra `ingreso`.
3. Código de un producto dado de baja → lo reactiva con nombre y stock nuevos; registra `ajuste` si el stock cambia. La web avisa antes de enviar si el código figura dado de baja.
4. Todo en una transacción; responde 201 con `creado`/`reactivado`.

**Casos de error** (ninguno modifica datos):
- Código de un producto activo → 409 "Ya existe un producto con código 'X'." (la web lo marca en el campo Código).
- Campo faltante o vacío, o stock fuera de 0..10.000 o no entero → 422.
- Sin sesión → 401.

## Flujo 2c: Modificar stock (lote, C-06b)
**Disparador**: `POST /api/stock/modificaciones` / modal "Modificar stock".
**Actor**: Usuario autenticado.

**Pasos**:
1. La web carga los productos activos y los dados de baja (`GET /api/inventario`, `GET /api/productos/inactivos`); el usuario arma de 1 a 100 líneas con modo "Fijar en" o "Sumar" y nombre opcional; los ya elegidos quedan deshabilitados.
2. El servicio valida en orden: datos (primera línea inválida), producto repetido, códigos inexistentes.
3. Atómico: por línea fija o suma el stock, registra `ajuste` (fijar con cambio) o `ingreso` (sumar), renombra si corresponde y reactiva un dado de baja solo si el stock cambia y queda > 0.
4. Responde 200 con el resultado por línea (`stock_anterior`, `nombre_anterior`, `reactivado`); la web muestra un resumen persistente.

**Casos de error** (ninguno modifica datos):
- Valor inválido → 422 "Línea N: ..."; modo inválido → 422 "Línea N: El campo modo debe ser fijar o sumar.".
- Producto repetido → 422 "Línea N: el producto 'X' ya está en la línea M.".
- Códigos inexistentes → 404 con `codigos` (la web marca cada línea).
- Lista vacía o de más de 100 líneas → 422.
- Falla a mitad → rollback completo.

## Flujo 4: Crear orden
**Disparador**: `POST /api/ordenes` (Fase 1, `/docs`) / modal de nueva orden (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recoge número, fecha `YYYY-MM-DD`, lista de (producto, cantidad) y, opcionales, `servicio` (clave del catálogo de servicios generales o `null`), `procesos` (claves del catálogo) y `procesos_personalizados` (textos); valida formatos.
2. OrdenService verifica unicidad del número, que haya ≥ 1 componente y que todos sean productos activos.
3. Valida stock de TODOS los componentes; si alguno falla, devuelve la lista de faltantes y no modifica nada.
4. Atómico: inserta la orden, inserta `orden_items`, descuenta stock de cada producto, inserta `orden_procesos` (catálogo primero, luego personalizados; nombre como snapshot) e inserta `orden_servicio` con sus `orden_servicio_chequeos` (snapshot de nombre y chequeos, C-06g).

```
Usuario → Adaptador → OrdenService → OrdenRepo.crear_con_descuento()
                                       SQLite: transacción
                                       Supabase: RPC crear_orden(..., p_servicio, p_procesos, p_procesos_personalizados)
        ← orden creada | error con faltantes
```

**Casos de error**:
- Número duplicado → rechazo (RN-OR-01).
- Fecha inválida → rechazo (RN-VA-03).
- Stock insuficiente en algún componente → rechazo total (RN-OR-04).
- Producto repetido en la misma orden → se consolidan las cantidades sumándolas (RN-OR-11).
- Proceso del catálogo inexistente → 422 "El proceso 'x' no existe." sin tocar stock (RN-OR-13).
- Personalizado vacío o de más de 60 → 422 "Proceso personalizado N: ..."; más de 10 → 422 "La orden admite hasta 10 procesos personalizados."; igual a uno del catálogo o repetido → 422 con su posición (RN-OR-14).
- Orden solo con procesos y sin componentes → 422 "La orden requiere al menos un componente."
- Servicio general inexistente → 422 "El servicio general 'x' no existe."; `servicio` que no es texto ni `null` → 422 "El campo servicio debe ser texto.". Ambos sin tocar stock (RN-OR-18).

**En la web (modal "Nueva orden", C-06f)**: debajo de "Componentes", el bloque "Procesos" con líneas (Agregar proceso / Quitar; cero permitido). Cada línea tiene un selector con los procesos de `GET /api/procesos` y "Personalizado", que muestra un cuadro de texto (hasta 10 líneas personalizadas). Si el catálogo no carga se avisa "No se pudo cargar la lista de procesos." y solo queda "Personalizado". El mismo proceso en dos líneas se envía una vez. Si un proceso fue borrado con el modal abierto, el backend responde 422 y se muestra el mensaje.

**En la web (bloque "Servicio general", C-06g)**: entre la fecha y "Componentes", un selector con "Sin servicio general" (por defecto) y los servicios de `GET /api/servicios-generales`; al elegir uno se listan sus chequeos (solo lectura). Si el catálogo no carga se avisa "No se pudo cargar la lista de servicios generales." y queda solo "Sin servicio general". Si el servicio fue borrado con el modal abierto, el backend responde 422 y se muestra junto al bloque, con el selector vuelto a "Sin servicio general".

## Flujo 5: Listar órdenes
**Disparador**: `GET /api/ordenes?numero&desde&hasta` (Fase 1, `/docs`) / pantalla de órdenes (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario elige "todas", ingresa un número de orden y/o `desde` y `hasta` (cada fecha opcional por separado; vacío = sin filtro).
2. OrdenService normaliza el número (recorte + MAYÚSCULAS), valida fechas y desde ≤ hasta.
3. Repo busca por número exacto y/o `fecha BETWEEN desde AND hasta` (inclusivo, rangos abiertos permitidos), combinados por AND, junto a sus ítems, los nombres de producto (activos o no), su servicio general con chequeos (si tiene) y sus procesos, ordenados por fecha DESC, id DESC.

**Casos de error**:
- Fecha inválida o rango invertido → 422 con mensaje claro.
- Número de más de 30 caracteres → 422.
- Número inexistente → 404 "No existe una orden con número 'X'." (la validación de formato tiene prioridad).
- Número existente fuera del rango de fechas → lista vacía (no es un error).
- Sin resultados → lista vacía.
- Sin sesión válida → 401.

## Flujo 5b: Buscar en el inventario (C-06c)
**Disparador**: el usuario escribe en el buscador de la pantalla de inventario.
**Actor**: Usuario autenticado.

**Pasos**:
1. La web filtra en el navegador la lista cargada por código o nombre parcial (sin distinguir mayúsculas ni acentos); no hay llamada al servidor.
2. Se muestra "N productos" o, con filtro que reduce la lista, "V de N productos".
3. Tras recargar la lista (ingreso, modificación, orden, borrado) se reaplica la búsqueda vigente.

**Casos especiales**:
- Sin coincidencias → mensaje y botón "Limpiar búsqueda" (Escape hace lo mismo).

## Flujo 5c: Exportar a PDF (C-06c)
**Disparador**: botón "Exportar PDF" en el inventario o en una orden.
**Actor**: Usuario autenticado.

**Pasos**:
1. `static/js/exportar.js` arma el documento de impresión con el contenido visible: inventario (filas visibles, "Inventario" + "N productos · YYYY-MM-DD") u orden individual ("Orden OT-XXXX" + "Fecha: YYYY-MM-DD · N componentes").
2. Se abre el diálogo de impresión del navegador; el usuario elige "Guardar como PDF". No se genera PDF en el servidor.
3. Estilos de impresión: página clara, controles y columna de acciones ocultos, stock 0 como "0 (sin stock)", encabezados de tabla repetidos por página.

**Casos especiales**:
- Orden con servicio general (C-06g): el PDF muestra primero el bloque "Servicio general" (nombre y chequeos uno por línea), antes de la tabla de componentes; sin servicio no se muestra.
- No existe exportación de la lista completa de órdenes (solo por orden); el reporte de C-06d (Flujo 5d) reutiliza `exportar.js`.

## Flujo 5d: Reporte de productos usados en órdenes por fechas (C-06d)
**Disparador**: pestaña "Reportes" (`/reportes`) y botón "Generar".
**Actor**: Usuario autenticado.

**Pasos**:
1. La pantalla carga `GET /api/reportes/productos-usados` para poblar el selector de producto (solo productos usados en alguna orden, agrupados en "Activos" y "Dados de baja"). "Desde" y "Hasta" arrancan con el mes en curso; no se genera nada hasta pulsar "Generar".
2. Se valida en el navegador (Desde obligatorio, fechas `YYYY-MM-DD`, desde <= hasta) y se llama a `GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=`. "Hasta" vacío = hoy (UTC-03:00).
3. El backend valida de nuevo y agrega por producto sobre las órdenes con fecha en el rango (inclusivo). Responde `codigo`, `nombre`, `activo`, `cantidad` y `ordenes`, ordenado por cantidad descendente y luego por código.
4. La web muestra la tabla (Código, Nombre, Cantidad, Órdenes) y el resumen; los productos dados de baja se marcan "dado de baja".
5. "Exportar PDF" arma el documento con `exportar.js`: "Reporte de productos en órdenes" + "AAAA-MM-DD a AAAA-MM-DD · N productos" (con filtro: "CÓDIGO · Nombre · " al inicio); nombre propuesto `reporte-AAAA-MM-DD_AAAA-MM-DD`.

**Casos de error / especiales**:
- Sin sesión válida → 401 (antes de validar parámetros).
- `desde` faltante o vacío, fecha mal formada o inexistente, `desde` posterior al `hasta` efectivo, o `codigo` demasiado largo → 422 con `detail` en español; la web lo muestra y no modifica la tabla previa.
- Código desconocido o rango sin órdenes → lista vacía (no es un error); la web muestra un mensaje de sin resultados.
- El endpoint es de solo lectura: no modifica stock ni órdenes.

## Flujo 5e: Categorías de productos (C-06e)
**Actor**: Usuario autenticado.

**Filtrar el inventario por categoría**:
1. La página carga `GET /api/inventario` y `GET /api/categorias` en paralelo (si el catálogo falla, se muestra la clave cruda y el filtro queda solo con "Todas").
2. El `<select>` de categoría (Todas / categorías / "Sin categoría") se combina con el buscador (AND), en el navegador. Conteo "V de N productos"; sin coincidencias, mensaje según el caso y "Limpiar filtros". El filtro y el texto se conservan al recargar la lista.
3. "Exportar PDF" imprime lo visible con la columna Categoría; con categoría elegida, el encabezado la incluye.

**Asignar categoría**:
- "Nuevo ingreso": selector opcional (por defecto "Sin categoría"); si el código está dado de baja, la reactivación reemplaza nombre, stock y categoría.
- "Modificar stock": cada línea precarga la categoría actual; la web envía `categoria` (clave o `null`); el backend solo escribe si cambió, sin movimiento y sin reactivar. El resumen muestra "categoría: Filtro → Aceite".

**Nueva orden**: cada línea tiene su filtro de categoría ("Todas" por defecto); al cambiarlo se conserva el producto si pertenece, si no la línea vuelve a "Elegí un producto…"; sin activos en la categoría, "No hay productos en esta categoría.".

**Administrar categorías (solo API, desde `/docs`)**: `POST /api/categorias {nombre, clave?}` → 201; `PATCH /api/categorias/{clave} {nombre}` → 200. La web ve los cambios al recargar.

**Casos de error**:
- Sin sesión → 401. Categoría desconocida en alta o modificación → 422 "La categoría 'x' no existe." (en lotes con "Línea N: "); `categoria` no textual → 422 "El campo categoria debe ser texto.".
- Alta con clave o nombre repetido → 409; nombre vacío o de más de 40, o clave que queda vacía → 422; renombrar con `clave` en el cuerpo → 422; renombrar clave inexistente → 404.

## Flujo 5f: Procesos de órdenes (C-06f)
**Actor**: Usuario autenticado.

**Ver los procesos**: `/ordenes` muestra bajo la cabecera de cada orden una fila "Procesos:" con los nombres registrados (como texto); si la orden no tiene, no hay fila. "Exportar PDF" de una orden agrega, debajo de la tabla de componentes, "Procesos realizados" con un proceso por línea (omitido si no tiene).

**Administrar el catálogo (solo API, desde `/docs`)**: `GET /api/procesos` lista; `POST /api/procesos {nombre, clave?}` → 201; `PATCH /api/procesos/{clave} {nombre}` → 200; `DELETE /api/procesos/{clave}` → 200 (aunque haya órdenes que lo usaron: conservan su nombre). `DELETE /api/categorias/{clave}` → 200 si ningún producto la usa. La web ve los cambios al recargar.

**Casos de error**:
- Sin sesión → 401.
- Proceso: clave o nombre repetido → 409; nombre vacío o de más de 60, o clave inválida → 422; renombrar con `clave` en el cuerpo → 422; clave inexistente (renombrar o borrar) → 404.
- Categoría: clave inexistente → 404; con algún producto asignado (activo o dado de baja) → 409 "La categoría 'x' está asignada a N producto(s)." sin cambios.

## Flujo 5g: Servicios generales de órdenes (C-06g)
**Actor**: Usuario autenticado.

**Asignar**: al crear la orden, el bloque "Servicio general" (ver Flujo 4) envía `servicio` con la clave elegida o `null`. El snapshot guarda el nombre y todos los chequeos del servicio en ese momento.

**Ver**: `/ordenes` muestra bajo la cabecera de cada orden con servicio una fila "Servicio general:" con el nombre y sus chequeos como chips; sin servicio, no hay fila. El PDF de la orden (Flujo 5c) lo muestra primero, antes de los componentes.

**Administrar el catálogo (web)**: el botón "Servicios generales" junto al título de `/ordenes` abre un modal con tres vistas: lista (cada servicio con "Editar" / "Eliminar" y "Nuevo servicio"), formulario (nombre de hasta 60; chequeos en líneas numeradas, de 1 a 30, cada uno de 1 a 60 caracteres, sin repetir; "Agregar chequeo" / "Quitar"; se guardan en el orden de las líneas) y confirmación de borrado. Tras guardar o eliminar, el modal muestra un mensaje de éxito. La lista de órdenes no se recarga: los snapshots no cambian.

**Administrar el catálogo (API, desde `/docs`)**: `GET /api/servicios-generales` lista por nombre; `POST /api/servicios-generales {nombre, chequeos, clave?}` → 201 (clave derivada del nombre si falta); `PATCH /api/servicios-generales/{clave} {nombre?, chequeos?}` → 200 (`chequeos` reemplaza la lista completa); `DELETE /api/servicios-generales/{clave}` → 200 con el servicio borrado.

**Casos de error**:
- Sin sesión → 401.
- Clave o nombre repetido → 409 "Ya existe un servicio general con clave 'x'." / "…con nombre 'X'."
- Nombre vacío o de más de 60 → 422; chequeos que no son una lista, lista vacía, más de 30, vacío, de más de 60 o repetido → 422 con su posición ("Chequeo N: ...").
- Modificar sin nombre ni chequeos → 422 "Indicá el nombre o los chequeos a modificar."; `clave` en el cuerpo → 422.
- Clave inexistente (modificar o borrar) → 404 "No existe un servicio general con clave 'x'.".

## Flujo 6: Borrar orden
**Disparador**: `DELETE /api/ordenes/{numero}?reintegrar=true|false` (Fase 1, `/docs`) / modal de borrado (Fase 2). La orden se identifica por su número normalizado, nunca por id (C-05).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario indica la orden por su número; en Fase 2 el frontend pide confirmación (modal). La API no tiene confirmación propia.
2. La llamada debe traer `reintegrar=true|false` explícito (en Fase 2 el modal muestra la casilla "Devolver stock", marcada por defecto; el botón dice "Borrar y devolver stock" o "Borrar sin devolver stock").
3. Todo ocurre en una sola transacción (todo o nada):
   - Si `reintegrar=true`: suma la cantidad de cada ítem a su producto. Si el producto estaba dado de baja, lo reactiva (`activo = 1`) (RN-OR-12).
   - Borra explícitamente los ítems de la orden (`orden_items`) y luego la orden. El `ON DELETE CASCADE` queda solo como respaldo.
   - No genera movimientos de stock.
4. Respuesta 200 con `orden`, `reintegrado` y `reintegros` (lista ordenada por código; vacía sin reintegro).

**Casos de error** (ninguno modifica datos):
- Número inexistente → 404 con `detail` "No existe una orden con número 'X'." (X normalizado).
- `reintegrar` ausente, vacío, repetido o distinto de `true`/`false` → 422 "El campo reintegrar es obligatorio." (la API no asume un valor por defecto).
- Número en blanco o de más de 30 caracteres → 422.
- Sin sesión válida, o con sesión de un usuario borrado → 401.
- Falla a mitad de reintegro → rollback completo (RN-OR-09).

## Flujo 7: Borrar producto (lógico)
**Disparador**: `DELETE /api/productos/{codigo}` (Fase 1, `/docs`) / modal de borrado (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario indica el producto; en Fase 2 el frontend pide confirmación (modal).
2. `ProductoService.dar_de_baja` setea `activo = 0` solo si el producto estaba activo; no genera movimientos de stock.
3. El producto sale del inventario y de la selección de componentes; las órdenes históricas siguen mostrándolo.

**Casos de error**: producto inexistente o ya inactivo → 404 "No existe un producto activo con código 'X'."; código vacío o de más de 50 caracteres → 422; sin sesión → 401. Ningún rechazo modifica datos.

## Flujo 8: Despliegue (Fase 4)
**Disparador**: push a GitHub.
**Actor**: Operador.

**Pasos**:
1. Crear proyecto Supabase y ejecutar `schema.sql` (tablas + RPC); correr script de seed del admin.
2. Subir el repo a GitHub.
3. Importar en Vercel; cargar `SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY` (y `ADMIN_DEFAULT_PASSWORD` para el seed).
4. Verificar login, inventario y una orden de prueba.
