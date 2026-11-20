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
                          └── C-07 paso-6-migracion-supabase
                               └── C-08 paso-7-despliegue-vercel
```

### Paralelismo por fase

No hay paralelismo: la cadena es lineal y el usuario trabaja UN change a la vez.

```
GATE 0: (inicio)
  → C-01 paso-1-base-cli               [Agente A]
GATE 1..7: cada change archivado desbloquea únicamente el siguiente (sin fork).
```

### Camino crítico (8 changes — mínimo irreducible)

C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-07 → C-08

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux) | Agente C (Frontend) |
|------|-------------------------|------------------------|---------------------|
| 1 | C-01 | — | — |
| 2 | C-02 | — | — |
| 3 | C-03 | — | — |
| 4 | C-04 | — | — |
| 5 | C-05 | — | — |
| 6 | C-06 (mockups + apply) | — | — |
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
- **Test runner**: `unittest` + `TestClient` (Strict TDD)
- **Dependencias**: `C-06`
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
| C-07 | paso-6-migracion-supabase | 3 | C-06 | CRITICO |
| C-08 | paso-7-despliegue-vercel (antes paso-6-despliegue-vercel) | 4 | C-07 | ALTO |

Primer change recomendado: `C-01` (`paso-1-base-cli`).
