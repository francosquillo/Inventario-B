# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto Inventario-B.
> Cada change corresponde a un paso del brief y se ejecuta de forma estrictamente secuencial, con pausa entre pasos.
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificá el próximo change pendiente (primer `[ ]` cuyas dependencias estén `[x]`).
2. Leé los archivos de "Leer antes" de la KB para ese change.
3. Corré `/opsx:propose <nombre-del-change>` y luego `/opsx:apply` (Strict TDD), verify y `/opsx:archive`.
4. Pausá y esperá la orden "Continuar" del usuario antes de pasar al siguiente.
5. Marcá el checkbox `[x]` del change archivado.

**Test runner (todos los changes)**: `unittest` (`python -m unittest discover`), con `TestClient` de FastAPI (requiere `httpx` en `requirements-dev.txt`) para los endpoints. Strict TDD activo: safety net, RED, GREEN, TRIANGULATE, REFACTOR. Además, cada endpoint se verifica a mano en la Swagger UI (`/docs`).

> **Cambio de alcance 2026-11-19 (decisión explícita del usuario)**: se elimina la CLI. Los pasos 1 a 4b se construyen como backend FastAPI + SQLite local, verificado en `/docs` y con tests. Esto se aparta del brief original (CLI con stdlib en Fase 1). Los nombres de los changes se mantienen sin cambios (`paso-1-base-cli` es un nombre histórico). Dependencias permitidas desde el Paso 1, declaradas en `requirements.txt` / `requirements-dev.txt`, trabajando en `.venv`.

---

## Árbol de dependencias

```
C-01 paso-1-base-cli
 └── C-02 paso-2-movimientos-stock
      └── C-03 paso-3-crear-ordenes
           └── C-04 paso-4-listado-ordenes
                └── C-05 paso-4b-borrado-ordenes-productos
                     └── C-06 paso-5-web-local
                          └── C-06b paso-5b-fixes-menores
                          └── C-06c paso-5c-buscador-pdf
                          └── C-06d paso-5d-reporte-ordenes-fechas
                          └── C-06e paso-5e-categorias-productos
                          └── C-06f paso-5f-procesos-ordenes
                          └── C-06g paso-5g-servicios-generales
                          └── C-06h paso-5h-precios-datos-orden
                          └── C-06h2 paso-5h2-filtro-categoria-stock
                          └── C-06i paso-5i-modificar-ordenes-checkeo
                          └── C-06j paso-5j-impresion-ordenes
                               └── C-07 paso-6-migracion-supabase
                                    └── C-08 paso-7-despliegue-vercel
```

> Los sub-changes de C-06 (C-06b..C-06j) van en la misma columna pero se ejecutan **en secuencia**: cada uno depende del anterior (ver "Dependencias" de cada change). C-07 depende de C-06j.

### Paralelismo por fase

No hay paralelismo: la cadena es lineal y el usuario trabaja UN change a la vez.

```
GATE 0: (inicio)
  → C-01 paso-1-base-cli               [Agente A]
GATE 1..7: cada change archivado desbloquea únicamente el siguiente (sin fork).
```

### Camino crítico (18 changes — mínimo irreducible)

C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-06b → C-06c → C-06d → C-06e → C-06f → C-06g → C-06h → C-06h2 → C-06i → C-06j → C-07 → C-08

> C-06b (`paso-5b-fixes-menores`) es un change intermedio agregado el 2026-11-20 a pedido del usuario, entre C-06 y C-07.
> C-06c..C-06f son changes intermedios agregados el 2026-11-24 a pedido del usuario, antes de C-07, ordenados de más simple a más complejo: los dos primeros no tocan el esquema; los dos últimos agregan tablas/columnas con migración.
> C-06g..C-06j son changes intermedios agregados el 2026-11-26 a pedido del usuario, antes de C-07, ordenados de más simple a más complejo **respetando dependencias**: C-06j (impresión) es el más chico en código pero va último porque el formato impreso necesita los campos que agregan C-06h (precios, cliente, embarcación, fechas) y C-06i (checkeo final); hacerlo antes obligaría a rehacerlo.
> C-06h2 (`paso-5h2-filtro-categoria-stock`) se agregó el 2026-11-27 a pedido del usuario, después de C-06h (decisión explícita: primero los precios). Solo frontend.

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux) | Agente C (Frontend) |
|------|-------------------------|------------------------|---------------------|
| 1 | C-01 | — | — |
| 2 | C-02 | — | — |
| 3 | C-03 | — | — |
| 4 | C-04 | — | — |
| 5 | C-05 | — | — |
| 6 | C-06 (mockups + apply) | — | — |
| 6b | C-06b (mockups + apply) | — | — |
| 6c | C-06c (mockups + apply) | — | — |
| 6d | C-06d (mockups + apply) | — | — |
| 6e | C-06e (mockups + apply) | — | — |
| 6f | C-06f (mockups + apply) | — | — |
| 6g | C-06g (mockups + apply) | — | — |
| 6h | C-06h (mockups + apply) | — | — |
| 6h2 | C-06h2 (mockups + apply) | — | — |
| 6i | C-06i (mockups + apply) | — | — |
| 6j | C-06j (mockups + apply) | — | — |
| 7 | C-07 | — | — |
| 8 | C-08 | — | — |

---

## FASE 1 — Backend API local (FastAPI + SQLite), verificado en /docs

### [C-01] `paso-1-base-cli`
> Nombre histórico: ya no hay CLI; el change entrega la base del backend FastAPI.
- **Estado**: `[x]` archivado (2026-11-19)
- **Scope**:
  - Esqueleto FastAPI (adaptador HTTP fino) + `requirements.txt` (`fastapi`, `uvicorn`, `python-dotenv`, `itsdangerous`) y `requirements-dev.txt` (`httpx`); `.venv` gitignored
  - SQLite local (`sqlite3`): tablas `usuarios`, `productos`, `ordenes`, `orden_items`, `movimientos`; inicialización idempotente y seed del admin al arrancar la app (lifespan de FastAPI)
  - Seed de `admin` con hash PBKDF2-HMAC-SHA256 + salt por usuario, `hmac.compare_digest`; contraseña inicial desde `ADMIN_DEFAULT_PASSWORD` (`os.environ`); si falta, se genera aleatoria y se imprime UNA sola vez en la consola del servidor (log de uvicorn) en la primera inicialización
  - Auth con cookie de sesión firmada (Starlette `SessionMiddleware`, env `SECRET_KEY`); dependencia `get_current_user` que responde 401 sin sesión; endpoints `POST /api/login` (mensaje genérico ante credenciales inválidas), `POST /api/logout`, `GET /api/me`, `GET /api/inventario` (solo activos, stock 0 visible, lista vacía explícita)
  - Estructura Repositorio/DAO + services desacoplados de FastAPI (US-001, US-002, US-003)
  - Verificación manual en `/docs` + tests `unittest`: hashing, login válido/inválido, init idempotente, listado de inventario (SQLite `:memory:`), endpoints con `TestClient`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: ninguna
- **Governance**: CRITICO (auth y modelo core del que depende todo)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md`
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU, §RN-PR, §RN-SE
  - `knowledge-base/06_funcionalidades.md` §US-001..US-003
  - `knowledge-base/08_arquitectura_propuesta.md`
  - `knowledge-base/11_plan_de_pasos_y_despliegue.md`

### [C-02] `paso-2-movimientos-stock`
- **Estado**: `[x]` archivado (2026-11-20)
- **Scope**:
  - Ingreso de stock por código: suma si existe, crea con nombre si no existe, reactiva si está inactivo (US-004)
  - Egreso manual: entero > 0 y <= stock actual (US-005)
  - Registro atómico en `movimientos` (fecha, producto, tipo, cantidad, usuario) sin motivo; transacción SQLite
  - Endpoints `POST /api/stock/ingreso` y `POST /api/stock/egreso` (protegidos, 401 sin sesión), verificados en `/docs`
  - Tests `unittest`: suma, alta, reactivación, rechazo por exceso/cantidad inválida, atomicidad, endpoints con `TestClient`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-01`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST, §RN-PR, §RN-VA
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005
  - `knowledge-base/07_flujos_principales.md`
  - `knowledge-base/04_modelo_de_datos.md` §movimientos

### [C-03] `paso-3-crear-ordenes`
- **Estado**: `[x]` archivado (2026-11-20)
- **Scope**:
  - `POST /api/ordenes`: número único, fecha `YYYY-MM-DD`, >= 1 componente activo con cantidad entera > 0 (US-006)
  - Consolidación de líneas repetidas del mismo producto (RN-OR-11)
  - Validación de stock de TODOS los componentes; rechazo completo si falta; descuento + alta de `ordenes`/`orden_items` en una transacción
  - Los descuentos por orden NO se registran en `movimientos` (RN-ST-06)
  - Verificación en `/docs`
  - Tests `unittest`: éxito, stock insuficiente sin cambios parciales, número duplicado, fecha inválida, consolidación, endpoint con `TestClient`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-02`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR, §RN-VA
  - `knowledge-base/06_funcionalidades.md` §US-006
  - `knowledge-base/07_flujos_principales.md`
  - `knowledge-base/04_modelo_de_datos.md` §ordenes, §orden_items

### [C-04] `paso-4-listado-ordenes`
- **Estado**: `[x]` archivado (2026-11-20)
- **Scope**:
  - `GET /api/ordenes?desde&hasta`: todas o rango `YYYY-MM-DD` inclusivo, validando fechas reales y desde <= hasta (US-007)
  - `desde`/`hasta` opcionales por separado (solo uno = rango abierto; vacío = sin filtro, como en C-02) — a confirmar en el propose
  - Búsqueda por número de orden: `?numero=X` y/o `GET /api/ordenes/{numero}` (404 si no existe) — forma a decidir en el propose (agregado 2026-11-20)
  - Detalle de componentes por orden, mostrando productos dados de baja (RN-PR-04)
  - Verificación en `/docs`
  - Tests `unittest`: sin filtro, rango inclusivo en bordes, un solo día, solo desde / solo hasta, rango invertido, fecha inexistente, sin resultados, búsqueda por número existente / inexistente, endpoint con `TestClient`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-03`
- **Governance**: BAJO (lectura)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR-07, §RN-VA-03
  - `knowledge-base/06_funcionalidades.md` §US-007
  - `knowledge-base/07_flujos_principales.md`

### [C-05] `paso-4b-borrado-ordenes-productos`
- **Estado**: `[x]` archivado (2026-11-20)
- **Scope**:
  - `DELETE /api/ordenes/{numero}?reintegrar=true|false` (borrado por número de orden, no por id; decisión del usuario, 2026-11-20): el parámetro `reintegrar` es obligatorio y explícito en cada llamada (sin valor por defecto); reintegro + borrado atómicos; reactiva productos inactivos al reintegrar (US-008, RN-OR-08/09/12). La confirmación previa es responsabilidad del frontend (Paso 5); la API exige el parámetro explícito
  - `DELETE /api/productos/{codigo}`: baja lógica (`activo = 0`); las órdenes históricas lo siguen mostrando (US-009)
  - Verificación en `/docs`
  - Tests `unittest`: con/sin reintegro, reactivación, parámetro `reintegrar` ausente rechazado, baja lógica e inventario, órdenes históricas intactas, endpoints con `TestClient`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-04`
- **Governance**: ALTO (borrado destructivo con reintegro de datos)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR-08..12, §RN-PR-03, §RN-VA-05
  - `knowledge-base/06_funcionalidades.md` §US-008, §US-009
  - `knowledge-base/07_flujos_principales.md`
  - `knowledge-base/09_decisiones_y_supuestos.md`

---

## FASE 2 — Web local (FastAPI + SQLite + frontend estático)

> Decisión del usuario (2026-11-20): la migración a Supabase sale de este change para poder correr backend y frontend en local sobre SQLite, sin internet ni claves, y cazar bugs antes de migrar.

### [C-06] `paso-5-web-local`
> Nombre histórico: `paso-5-supabase-api-web`. La API ya existe desde C-01..C-05; este change agrega el frontend estático servido por la misma app FastAPI sobre los repositorios SQLite existentes. Ejecutable en local con uvicorn en http://localhost:8000.
- **Estado**: `[x]` archivado (2026-11-20)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`, design-system Revision 1 aprobado. ANTES de `apply` deben crearse y aprobarse los mockups del change en `openspec/changes/paso-5-web-local/mockups/` (basados en `design-system/components.html` y `design-system/ordenes.html`; inventario primero; modales para ingreso/egreso/nueva orden/borrados; órdenes en pantalla aparte `/ordenes`), con renders 390x844 y 1440x900 y `## UI Mockups` en `design.md`
  - La API FastAPI YA EXISTE (C-01..C-05); aquí se endurece la cookie de sesión (HttpOnly, SameSite=Lax, `SECRET_KEY` por entorno) y se sirve `static/` desde la misma app sin cambiar el contrato de los endpoints `/api/...`
  - Frontend HTML estático en `static/` (`login.html`, `index.html`, `ordenes.html`, `js/`, `css/`) + Tailwind CDN + JS vanilla con `fetch` a la API JSON (redirige al login en 401; sin Jinja2 ni `templates/`): login, inventario, modales, `/ordenes` con filtro de fechas y búsqueda por número; validación en front
  - Estado vacío en `/ordenes`: si la API devuelve `[]`, mostrar el cartel "No hay órdenes en ese período" (con filtros; sin filtros, "No hay órdenes" — decisión del usuario, 2026-11-20) (en vez de una tabla vacía); si la búsqueda por número da 404, mostrar su `detail` ("No existe una orden con número 'X'."). Incluir ambos estados en los mockups (decisión del usuario, 2026-11-20)
  - Modal de borrar orden: casilla "Devolver stock" **marcada por defecto**; el botón de confirmar dice el resultado ("Borrar y devolver stock" / "Borrar sin devolver stock"); el frontend siempre envía `reintegrar=true|false` y codifica el número con `encodeURIComponent` en `DELETE /api/ordenes/{numero}` (decisión del usuario, 2026-11-20)
  - Los services y rutas de C-01..C-05 se reutilizan sin modificarlos
  - Revisar CSRF de login/logout (observación verify C-01)
  - Tests `unittest` (rutas FastAPI con `TestClient` (dependencia de test: `httpx`), servicios)
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-05`
- **Governance**: ALTO (sesión/cookies, CSRF) con componente visual; ya no es CRITICO porque no interviene ninguna `service_role` key
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md`
  - `knowledge-base/05_reglas_de_negocio.md` §RN-SE, §RN-AU
  - `knowledge-base/10_preguntas_abiertas.md`
  - `design-system/README.md`

### [C-06b] `paso-5b-fixes-menores`
> Change intermedio agregado el 2026-11-20 (pedido del usuario tras usar la web local de C-06).
- **Estado**: `[x]` archivado (2026-11-23)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`, design system Revision 2 aprobado. ANTES de `apply` deben aprobarse los mockups en `openspec/changes/paso-5b-fixes-menores/mockups/` (renders 390x844 y 1440x900, `## UI Mockups` en `design.md`)
  - Botón "Ingreso de stock" → **"Nuevo ingreso"**: alta de producto con Código, Nombre y Stock obligatorios; stock inicial 0 permitido; código activo existente → 409 "Ya existe un producto con código 'X'."; código dado de baja → se reactiva con el nombre y el stock nuevos. Endpoint nuevo `POST /api/productos`
  - Botón "Egreso de stock" → **"Modificar stock"**: modal multi-línea (como nueva orden); por línea, modo "Fijar en" (stock absoluto >= 0, se registra como movimiento nuevo de tipo `ajuste` con stock anterior y nuevo) o "Sumar" (cantidad > 0, movimiento `ingreso`), y cambio opcional del nombre; también sobre productos dados de baja, que se reactivan. Todo o nada en una transacción; errores marcados por línea. Endpoints nuevos `POST /api/stock/modificaciones` y `GET /api/productos/inactivos`
  - Migración idempotente al arrancar de la tabla `movimientos` de SQLite (CHECK de `tipo` con `ajuste` + columnas `stock_anterior`/`stock_nuevo`), reconstruyendo la tabla en una transacción; `GET /api/movimientos` agrega esas dos columnas (null salvo en `ajuste`)
  - `POST /api/stock/ingreso` y `/egreso` siguen en la API (y sus tests) pero salen de la web; las órdenes no cambian
  - Al archivar: actualizar KB 04, 05, 06 y 07 (alta con stock 0, tipo `ajuste`, modificación en lote, reactivación)
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06`
- **Governance**: MEDIO/ALTO (lógica de negocio de stock + migración de esquema sobre datos existentes) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §productos, §movimientos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST, §RN-PR, §RN-VA
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005, §US-009
  - `knowledge-base/07_flujos_principales.md`
  - `design-system/README.md`
  - `openspec/changes/archive/2026-11-20-paso-5-web-local/` (mockups y design de C-06)

### [C-06c] `paso-5c-buscador-pdf`
> Change intermedio agregado el 2026-11-24 (pedido del usuario). El más simple de los cuatro: sin cambios de esquema.
- **Estado**: `[x]` archivado (2026-11-24)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`, design system Revision 2. Mockups aprobados ANTES de `apply`
  - Buscador de productos en el inventario por **código o nombre parcial** (sin distinguir mayúsculas; definir en propose si filtra en el navegador o con un parámetro `q` en `GET /api/productos`)
  - **Exportar a PDF** el resultado de la búsqueda del inventario y el listado de órdenes (el pedido dice "importar"; se interpreta como exportar/descargar, confirmar en propose)
  - Decidir en propose el mecanismo de PDF: impresión del navegador con hoja de estilos `@media print` (sin dependencias nuevas) vs. generación en el servidor con una librería declarada en `requirements.txt`
  - Al archivar: actualizar KB 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06b`
- **Governance**: BAJO/MEDIO (lectura y presentación; sin cambios de datos) con componente visual
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md`
  - `knowledge-base/07_flujos_principales.md`
  - `design-system/README.md`
  - `openspec/changes/archive/2026-11-23-paso-5b-fixes-menores/` (mockups y design de C-06b)

### [C-06d] `paso-5d-reporte-ordenes-fechas`
> Change intermedio agregado el 2026-11-24 (pedido del usuario). Sin cambios de esquema; consulta agregada nueva.
- **Estado**: `[x]` archivado (2026-11-24)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - Reporte de **cantidad de cada producto usada en órdenes dentro de un rango de fechas** (desde/hasta `YYYY-MM-DD`, validado en frontend y backend; desde <= hasta): un total por producto en el rango
  - Filtro opcional por **un solo producto** (si se elige, el reporte muestra solo ese producto en el rango)
  - **Exportar el resultado a PDF**, reutilizando el módulo `static/js/exportar.js` y los estilos `@media print` de C-06c (impresión del navegador, sin PDF en el servidor)
  - Endpoint nuevo de solo lectura (p. ej. `GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=`) con la agregación en el repositorio
  - Pantalla aparte (p. ej. `/reportes`), recomendada frente a una sección dentro de órdenes; confirmar en propose
  - Al archivar: actualizar KB 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06c`
- **Governance**: MEDIO (consulta agregada sobre datos existentes) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §ordenes, §orden_items
  - `knowledge-base/05_reglas_de_negocio.md` §RN-VA (fechas)
  - `knowledge-base/06_funcionalidades.md`
  - `design-system/README.md`

### [C-06e] `paso-5e-categorias-productos`
> Change intermedio agregado el 2026-11-24 (pedido del usuario). Cambia el esquema de `productos`.
- **Estado**: `[x]` archivado (2026-11-24)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - Categoría por producto, con 3 de ejemplo: **motor, aceite, filtro**. Decidir en propose si es una tabla `categorias` (ampliable) o un valor fijo con CHECK, y si la categoría es obligatoria
  - Migración idempotente al arrancar sobre `productos` existentes (qué categoría reciben los productos actuales: a definir en propose)
  - Elegir/cambiar la categoría en "Nuevo ingreso" y "Modificar stock"; filtro por categoría en el inventario (combinable con el buscador de C-06c)
  - Al archivar: actualizar KB 04, 05, 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06d`
- **Governance**: MEDIO/ALTO (migración de esquema sobre datos existentes) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §productos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PR
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005
  - `openspec/changes/archive/2026-11-23-paso-5b-fixes-menores/` (patrón de migración idempotente)

### [C-06f] `paso-5f-procesos-ordenes`
> Change intermedio agregado el 2026-11-24 (pedido del usuario). El más complejo: tabla nueva ligada a órdenes.
- **Estado**: `[x]` archivado (2026-11-26)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - Sección en las órdenes para registrar los **procesos hechos a la lancha**, con 3 de ejemplo: **cambio motor, cambio filtro, limpieza**. Decidir en propose: catálogo en tabla vs. valores fijos, uno o varios procesos por orden, texto libre opcional
  - Tabla(s) nueva(s) (p. ej. `orden_procesos`) con migración idempotente; las órdenes existentes quedan sin procesos
  - Crear orden con procesos dentro de la misma transacción que descuenta stock (regla dura 3); listado/detalle de órdenes y PDF de órdenes (C-06c) muestran los procesos; borrar orden borra sus procesos
  - Al archivar: actualizar KB 04, 05, 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06e`
- **Governance**: ALTO (toca la creación/borrado atómicos de órdenes + migración de esquema) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §ordenes, §orden_items
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR
  - `knowledge-base/06_funcionalidades.md`
  - `knowledge-base/07_flujos_principales.md`

### [C-06g] `paso-5g-servicios-generales`
> Change intermedio agregado el 2026-11-26 (pedido del usuario). Catálogo nuevo ligado a órdenes, sin precios todavía.
- **Estado**: `[x]` archivado (2026-11-27)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - Catálogo de **servicios generales** de las órdenes; cada uno agrupa una lista de chequeos incluidos. Ejemplo: **servicio de 20 hs** = chequeo de motor, chequeo de combustible, chequeo eléctrico, etc.
  - Alta/edición/borrado de servicios generales y de sus chequeos incluidos (patrón del catálogo de procesos de C-06f)
  - Asignar un servicio general al crear la orden (decidir en propose: uno solo u opcional; snapshot del nombre y de los chequeos en la orden, como `orden_procesos`), dentro de la misma transacción que descuenta stock (regla dura 3)
  - Listado/detalle de órdenes y PDF (C-06c) muestran el servicio general y sus chequeos; borrar la orden borra su servicio asignado
  - Tablas nuevas con migración idempotente; las órdenes existentes quedan sin servicio general
  - Al archivar: actualizar KB 04, 05, 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06f`
- **Governance**: MEDIO/ALTO (toca la creación atómica de órdenes + migración de esquema) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §ordenes, §procesos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR
  - `openspec/changes/archive/2026-11-26-paso-5f-procesos-ordenes/` (patrón catálogo + snapshot en la orden)

### [C-06h] `paso-5h-precios-datos-orden`
> Change intermedio agregado el 2026-11-26 (pedido del usuario). Agrega columnas a órdenes y precios en varias tablas.
- **Estado**: `[x]` archivado (2026-11-27)
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - **Precios tipeados por el usuario** en la orden (no hay lista de precios automática): uno para el **servicio general** (C-06g), uno **por cada ítem** de la orden y uno **por cada servicio adicional** (los que hoy se ven como "procesos" en las órdenes, C-06f). Decidir en propose: moneda, decimales (centavos enteros vs. decimal), si el precio es obligatorio u opcional, total calculado, y si "procesos" se renombra a "servicios adicionales" en la UI
  - **Datos nuevos de la orden**: cliente, celular, casco, motor, trailer, fecha de ingreso y fecha de egreso. Decidir en propose cuáles son obligatorios, validación del celular y que egreso ≥ ingreso (fechas `YYYY-MM-DD`, validadas en frontend Y backend)
  - Relación con la `fecha` actual de la orden (¿pasa a ser la fecha de ingreso?): a definir en propose
  - Migración idempotente: las órdenes existentes quedan sin precios ni datos nuevos (NULL)
  - Listado/detalle de órdenes y PDF (C-06c) muestran precios, total y datos nuevos
  - Al archivar: actualizar KB 04, 05, 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06g`
- **Governance**: ALTO (migración de esquema sobre órdenes existentes + validaciones de montos y fechas) con componente visual
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §ordenes, §orden_items, §orden_procesos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR, §RN-VA
  - `knowledge-base/06_funcionalidades.md`

### [C-06h2] `paso-5h2-filtro-categoria-stock`
> Change chico agregado el 2026-11-27 (pedido del usuario). Solo frontend: sin cambios de esquema ni de API.
- **Estado**: `[ ]` pendiente
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups (solo los necesarios) aprobados ANTES de `apply`
  - En el modal **"Modificar stock"**, agregar a cada línea un **filtro por categoría** que acote el selector de producto, igual al de las líneas de "Nueva orden" (C-06e): opción "Todas", cada categoría y "Sin categoría"; si el producto elegido no pertenece a la categoría filtrada se resetea; ayuda "No hay productos en esta categoría." cuando el filtro deja la lista vacía
  - No confundir con el selector "Categoría" que ya tiene la línea, que sirve para **cambiar** la categoría del producto: el filtro es aparte, con etiqueta distinta (p. ej. "Filtrar por categoría"); definir en propose su ubicación en la línea
  - Reutilizar la lógica existente (`Busqueda.porCategoria`, `productoSigueVisible`) sin duplicarla
  - Al archivar: actualizar KB 06 y 07
- **Test runner**: `unittest` (guardas estáticas de frontend) + Node para la lógica JS pura (Strict TDD)
- **Dependencias**: `C-06h`
- **Governance**: BAJO (solo presentación, sin cambios de datos)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-005 (modificar stock)
  - `openspec/changes/archive/` de C-06e (filtro por categoría en las líneas de "Nueva orden")
  - `static/js/inventario.js` (`llenarSelect`, `actualizarAyudaLinea`)

### [C-06i] `paso-5i-modificar-ordenes-checkeo`
> Change intermedio agregado el 2026-11-26 (pedido del usuario). El más complejo: edición de órdenes con ajuste atómico de stock.
- **Estado**: `[ ]` pendiente
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. Mockups aprobados ANTES de `apply`
  - **Modificar órdenes existentes**: servicio general asignado, ítems que la componen (con sus precios), servicios adicionales (con sus precios) y los datos de C-06h
  - Cambiar ítems ajusta el stock por diferencia (reintegra lo quitado, descuenta lo agregado) en una sola transacción, todo o nada (regla dura 3); stock insuficiente → error sin cambios. Decidir en propose si deja movimientos de stock y cómo se registran
  - **Checkeo final** de la orden: checkboxes fijos **Combustible, Puesta en marcha, Prueba en el lago, Limpieza de cortesía y Entrega**, cada uno con un **precio opcional** tipeado por el usuario. Decidir en propose si es lista fija (CHECK) o catálogo, y si entra al total de la orden
  - Detalle de la orden y PDF (C-06c) muestran el checkeo final
  - Al archivar: actualizar KB 04, 05, 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06h2`
- **Governance**: ALTO (edición atómica de órdenes con stock + migración de esquema) con componente visual
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-OR, §RN-ST
  - `knowledge-base/07_flujos_principales.md` (crear y borrar orden con reintegro)
  - `openspec/changes/archive/` de C-05 (borrado con reintegro atómico)

### [C-06j] `paso-5j-impresion-ordenes`
> Change intermedio agregado el 2026-11-26 (pedido del usuario). Chico en código, va último porque imprime todos los campos de C-06g..C-06i.
- **Estado**: `[ ]` pendiente
- **Scope**:
  - **Cambio visual**: política `system-and-mockups`. **Insumo obligatorio**: foto de referencia de cómo debe verse la orden impresa, que pasa el usuario antes del propose. Mockup aprobado ANTES de `apply`
  - Formato de impresión de **una orden** (vista imprimible / `@media print`, o PDF por orden: decidir en propose) con servicio general, ítems, servicios adicionales, precios, total, datos del cliente y la embarcación, fechas y checkeo final
  - Botón "Imprimir" desde el detalle de la orden
  - Al archivar: actualizar KB 06 y 07
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06i`
- **Governance**: BAJO/MEDIO (solo lectura y presentación)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md`
  - `openspec/changes/archive/` de C-06c (PDF de órdenes)
  - `design-system/README.md`

---

## FASE 3 — Supabase

### [C-07] `paso-6-migracion-supabase`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `schema.sql` Supabase: 5 tablas + funciones RPC Postgres para las operaciones atómicas: ingreso y egreso con movimiento, crear orden, listar (solo si hace falta), borrar orden por número con reintegro y baja de producto
  - Paridad con el comportamiento SQLite de C-01..C-05: normalización, mensajes, `created_at` en `-03:00` e ids identity que nunca se reutilizan
  - Script de seed del admin (contraseña desde entorno, PBKDF2)
  - Repositorios `supabase` (cliente Python síncrono) que reemplazan la implementación SQLite sin tocar los services
  - Tests de contrato de repositorio compartidos entre ambas implementaciones; `supabase` se agrega a `requirements.txt`
  - Selector de backend por variable de entorno (p. ej. `INVENTARIO_BACKEND=sqlite|supabase`, por defecto `sqlite`), para poder seguir probando en local tras la migración
  - `.env.example` solo con nombres de variables; el usuario crea su `.env`
  - Paridad con C-06b: `movimientos.tipo` admite `ajuste` con `stock_anterior`/`stock_nuevo`; funciones RPC para el alta de producto (`POST /api/productos`) y la modificación de stock en lote (`POST /api/stock/modificaciones`)
  - Paridad con C-06c..C-06f: búsqueda de productos, reporte de productos en órdenes por fechas (RPC `productos_en_ordenes` y `productos_usados`), categorías de productos y procesos de órdenes (tablas, migraciones y RPC equivalentes en Postgres)
  - Paridad con C-06f (procesos): tablas `procesos` (`clave` con CHECK, índice único sobre `lower(nombre)`) y `orden_procesos` (`orden_id` on delete cascade, `nombre` snapshot, `personalizado`, `position`, sin FK al catálogo); RPC `crear_orden` con `p_procesos` y `p_procesos_personalizados` (misma transacción que el descuento de stock); alta/renombrar/borrar de procesos y `DELETE` de categorías como operaciones directas sin RPC (`23505` → 409; `23503` por categoría en uso → 409); seed de `procesos` y `categorias` solo al crear cada tabla (no al estar vacía)
  - Paridad con C-06e (categorías): tabla `categorias` (`clave` única con CHECK, índice único sobre `lower(nombre)`) + `productos.categoria_id` nullable FK; seed `motor`/`aceite`/`filtro` solo con catálogo vacío; RPC de alta y modificación de productos con `p_categoria` (clave); RPC `productos_en_ordenes` devuelve `categoria`; crear (`POST`) y renombrar (`PATCH`) categorías como operaciones directas de una fila (23505 → 409), sin RPC
  - Paridad con C-06g (servicios generales, D10 de su design): tablas `servicios_generales` (`clave` con CHECK, índice único sobre `lower(nombre)`, nombre 1-60), `servicio_chequeos` (`servicio_id` on delete cascade, `posicion`, `nombre`, PK `(servicio_id, posicion)` + índice único `(servicio_id, lower(nombre))`), `orden_servicio` (`orden_id bigint` PK references `ordenes(id)` on delete cascade, `nombre` snapshot) y `orden_servicio_chequeos` (`orden_id` references `orden_servicio(orden_id)` on delete cascade, `posicion`, `nombre`, PK `(orden_id, posicion)` + índice único `(orden_id, lower(nombre))`); seed de `servicio-20-hs` con sus tres chequeos solo al crear las tablas; RPC `crear_orden` con `p_servicio jsonb` (`{nombre, chequeos}` o `null`, ya validado) en la misma transacción que el descuento de stock; alta y modificación de servicio (catálogo y chequeos) por RPC transaccional `guardar_servicio_general` (o equivalente); borrar servicio es una fila (cascade); `23505` → 409; RLS como `ordenes`
  - Paridad con C-06h..C-06j: precios y datos nuevos de la orden, modificación atómica de órdenes con ajuste de stock (RPC) y checkeo final
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06j`
- **Governance**: CRITICO (`service_role` key, migración de datos)
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md`
  - `knowledge-base/04_modelo_de_datos.md` (paridad SQLite/Postgres)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-SE
  - `knowledge-base/09_decisiones_y_supuestos.md`
  - `knowledge-base/10_preguntas_abiertas.md`

---

## FASE 4 — Despliegue en Vercel

### [C-08] `paso-7-despliegue-vercel`
> Nombre histórico: `paso-6-despliegue-vercel`.
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `api/index.py` (entrypoint serverless, exporta `app` FastAPI; despliega con el backend Supabase, `INVENTARIO_BACKEND=supabase`), `static/` (servido con `StaticFiles` y/o ruteo estático: definir aquí), `vercel.json`
  - `requirements.txt` (`fastapi`, `uvicorn`, `supabase`, `python-dotenv`, `itsdangerous`; versiones fijadas en este paso; `httpx` solo en `requirements-dev.txt`), `.env.example` (solo nombres), `.gitignore` (incluye `.env`)
  - README con guía: Supabase, `schema.sql`, seed admin, GitHub, Vercel, variables de entorno, verificación (US-011)
  - Tests `unittest`: smoke del entrypoint, ausencia de secretos hardcodeados, presencia de variables en `.env.example`
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-07`
- **Governance**: ALTO (configuración de despliegue y secretos)
- **Leer antes**:
  - `knowledge-base/11_plan_de_pasos_y_despliegue.md`
  - `knowledge-base/08_arquitectura_propuesta.md`
  - `knowledge-base/05_reglas_de_negocio.md` §RN-SE

---

## Resumen

| ID | Change | Fase | Dependencias | Governance |
|----|--------|------|--------------|------------|
| C-01 | paso-1-base-cli (nombre histórico) | 1 | — | CRITICO |
| C-02 | paso-2-movimientos-stock | 1 | C-01 | MEDIO |
| C-03 | paso-3-crear-ordenes | 1 | C-02 | MEDIO |
| C-04 | paso-4-listado-ordenes | 1 | C-03 | BAJO |
| C-05 | paso-4b-borrado-ordenes-productos | 1 | C-04 | ALTO |
| C-06 | paso-5-web-local (antes paso-5-supabase-api-web) | 2 | C-05 | ALTO |
| C-06b | paso-5b-fixes-menores | 2 | C-06 | MEDIO/ALTO |
| C-06c | paso-5c-buscador-pdf | 2 | C-06b | BAJO/MEDIO |
| C-06d | paso-5d-reporte-ordenes-fechas | 2 | C-06c | MEDIO |
| C-06e | paso-5e-categorias-productos | 2 | C-06d | MEDIO/ALTO |
| C-06f | paso-5f-procesos-ordenes | 2 | C-06e | ALTO |
| C-06g | paso-5g-servicios-generales | 2 | C-06f | MEDIO/ALTO |
| C-06h | paso-5h-precios-datos-orden | 2 | C-06g | ALTO |
| C-06h2 | paso-5h2-filtro-categoria-stock | 2 | C-06h | BAJO |
| C-06i | paso-5i-modificar-ordenes-checkeo | 2 | C-06h2 | ALTO |
| C-06j | paso-5j-impresion-ordenes | 2 | C-06i | BAJO/MEDIO |
| C-07 | paso-6-migracion-supabase | 3 | C-06j | CRITICO |
| C-08 | paso-7-despliegue-vercel (antes paso-6-despliegue-vercel) | 4 | C-07 | ALTO |

Primer change recomendado: `C-01` (`paso-1-base-cli`).
