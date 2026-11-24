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
1. Adaptador recoge número, fecha `YYYY-MM-DD` y lista de (producto, cantidad); valida formatos.
2. OrdenService verifica unicidad del número, que haya ≥ 1 componente y que todos sean productos activos.
3. Valida stock de TODOS los componentes; si alguno falla, devuelve la lista de faltantes y no modifica nada.
4. Atómico: inserta la orden, inserta `orden_items`, descuenta stock de cada producto.

```
Usuario → Adaptador → OrdenService → OrdenRepo.crear_con_descuento()
                                       SQLite: transacción
                                       Supabase: RPC crear_orden(...)
        ← orden creada | error con faltantes
```

**Casos de error**:
- Número duplicado → rechazo (RN-OR-01).
- Fecha inválida → rechazo (RN-VA-03).
- Stock insuficiente en algún componente → rechazo total (RN-OR-04).
- Producto repetido en la misma orden → se consolidan las cantidades sumándolas (RN-OR-11).

## Flujo 5: Listar órdenes
**Disparador**: `GET /api/ordenes?numero&desde&hasta` (Fase 1, `/docs`) / pantalla de órdenes (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario elige "todas", ingresa un número de orden y/o `desde` y `hasta` (cada fecha opcional por separado; vacío = sin filtro).
2. OrdenService normaliza el número (recorte + MAYÚSCULAS), valida fechas y desde ≤ hasta.
3. Repo busca por número exacto y/o `fecha BETWEEN desde AND hasta` (inclusivo, rangos abiertos permitidos), combinados por AND, junto a sus ítems y los nombres de producto (activos o no), ordenados por fecha DESC, id DESC.

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
- No existe exportación de la lista completa de órdenes (solo por orden); C-06d reutilizará `exportar.js`.

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
