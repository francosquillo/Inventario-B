# Funcionalidades

Organizadas por épica y por historia de usuario (US-NNN). El campo "Paso" mapea a 11_plan_de_pasos_y_despliegue.md. Los pasos 1-4b entregan la API FastAPI local (Fase 1, sin CLI), verificada en `/docs` y con tests; el Paso 5 migra a Supabase y agrega el frontend web que consume esa API; el Paso 6 la despliega.

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

### US-004 — Ingresar stock
**Como** usuario
**Quiero** ingresar unidades por código interno
**Para** mantener el inventario al día

**Paso**: 2 (API), 5 (modal)

**Criterios de aceptación**:
- [ ] Si el código existe y está activo, se suma la cantidad.
- [ ] `POST /api/stock/ingreso` con código, cantidad y (si el código no existe) nombre no vacío: se crea el producto con esa cantidad; sin nombre responde 422/400.
- [ ] Si el código existe inactivo, se reactiva y se suma la cantidad.
- [ ] Cantidad no entera o ≤ 0 se rechaza (422/400).
- [ ] Se registra un movimiento tipo `ingreso` sin pedir motivo.

**Reglas relacionadas**: RN-ST-01, RN-ST-03, RN-ST-04, RN-ST-05, RN-PR-01, RN-PR-06, RN-PR-07, RN-VA-01, RN-VA-02

### US-005 — Egreso manual de stock
**Como** usuario
**Quiero** descontar unidades sin crear una orden (rotura, pérdida, consumo interno)
**Para** que el stock refleje la realidad

**Paso**: 2 (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `POST /api/stock/egreso`: cantidad entera > 0 y ≤ stock actual; si excede, se rechaza (400/409) y el stock no cambia.
- [ ] El stock nunca queda negativo; si llega a 0 el producto sigue existiendo.
- [ ] Se registra un movimiento tipo `egreso` sin motivo.
- [ ] Solo se puede operar sobre productos activos existentes.

**Reglas relacionadas**: RN-ST-02, RN-ST-03, RN-ST-04, RN-ST-05, RN-PR-02, RN-VA-01

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

**Paso**: 4 (API), 5 (modal de listado)

**Criterios de aceptación**:
- [ ] `GET /api/ordenes` sin filtro lista todas.
- [ ] Con `?desde&hasta` (`YYYY-MM-DD`), se incluyen ambos extremos; `desde == hasta` busca un solo día.
- [ ] `desde` y `hasta` son opcionales por separado: solo `desde` = "de esa fecha en adelante", solo `hasta` = "hasta esa fecha"; parámetro vacío = sin filtro (mismo criterio que `GET /api/movimientos` en C-02). *(Agregado 2026-11-20, a confirmar en el propose de C-04.)*
- [ ] Búsqueda por número de orden (RN-OR-01, único): forma a definir en el propose de C-04 — filtro `?numero=X` combinable con fechas y/o detalle `GET /api/ordenes/{numero}` (404 si no existe). *(Agregado 2026-11-20 a pedido del usuario.)*
- [ ] Fecha inválida o desde > hasta se rechaza con mensaje claro.
- [ ] Cada orden muestra número, fecha y componentes con cantidades (incluso de productos dados de baja).

**Reglas relacionadas**: RN-OR-07, RN-PR-04, RN-VA-03

### US-008 — Borrar orden
**Como** usuario
**Quiero** borrar una orden cargada por error
**Para** corregir errores de carga

**Paso**: 4b (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `DELETE /api/ordenes/{id}?reintegrar=true|false`: el parámetro `reintegrar` es obligatorio en cada llamada (sin valor por defecto); si falta, se rechaza.
- [ ] La confirmación previa es del frontend (modal, Paso 5); la API no tiene paso de confirmación propio (IN-02).
- [ ] Si se reintegra, devolución y borrado son atómicos; si no, solo se borra la orden.
- [ ] Reintegrar a un producto inactivo lo reactiva y le suma las unidades (RN-OR-12).

**Reglas relacionadas**: RN-OR-08, RN-OR-09, RN-VA-05

### US-009 — Borrar producto
**Como** usuario
**Quiero** dar de baja un producto
**Para** que no aparezca más en el inventario ni en nuevas órdenes

**Paso**: 4b (API), 5 (modal)

**Criterios de aceptación**:
- [ ] `DELETE /api/productos/{codigo}`; la confirmación previa es del frontend (Paso 5).
- [ ] El borrado es lógico (`activo = 0`); el stock y el historial se conservan.
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
