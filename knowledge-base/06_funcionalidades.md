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

**Reglas relacionadas**: RN-OR-01, RN-OR-02, RN-OR-03, RN-OR-04, RN-OR-05, RN-OR-06, RN-ST-06, RN-VA-01, RN-VA-02, RN-VA-03

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

**Reglas relacionadas**: RN-OR-07, RN-PR-04, RN-VA-03

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
