# Descripción General

Tipo de sistema: `web_app` (arranca como backend API local en Fase 1, sin CLI, y suma frontend web local en Fase 2, Supabase en Fase 3 y despliegue en Fase 4). Dominio: inventario y órdenes de trabajo para taller/pyme. Escala: equipo chico (pocos usuarios, mismos permisos).

## Stack tecnológico

| Capa | Tecnologías | Versión mínima |
|------|-------------|----------------|
| Fase 1 — backend API local | FastAPI (ASGI) + `uvicorn`, Pydantic, `python-dotenv`, `itsdangerous` (sesión); lógica con `sqlite3`, `hashlib`, `hmac`, `datetime`, `os`; `.venv` | Python 3.10+; dependencias en `requirements.txt` |
| Fase 1 — persistencia | SQLite (archivo local, ruta opcional `INVENTARIO_DB_PATH`) | sqlite 3.x (incluido en Python) |
| Fase 1 — verificación | Swagger UI en `/docs` + `unittest` con `TestClient` | `httpx` en `requirements-dev.txt` (solo test) |
| Fase 2 — web local | Mismo FastAPI sirviendo `static/` sobre los repositorios SQLite existentes (uvicorn en http://localhost:8000); cookie de sesión endurecida | Sin dependencias nuevas |
| Fase 2 — frontend | HTML5 + Tailwind CSS vía CDN + JavaScript vanilla | Navegadores modernos |
| Fase 3 — backend Supabase | Se agrega el cliente `supabase` (Python, síncrono) y repositorios Supabase que reemplazan a SQLite sin tocar los services; selector `INVENTARIO_BACKEND=sqlite\|supabase` (por defecto `sqlite`) | Versiones a fijar en el Paso 7 |
| Fase 3 — base de datos | Supabase (PostgreSQL gestionado) + funciones PL/pgSQL vía RPC | PostgreSQL 15+ |
| Fase 4 — despliegue | Vercel (Serverless Functions, runtime Python), GitHub como origen | — |

Las dependencias se declaran en `requirements.txt` (runtime) y `requirements-dev.txt` (test) desde el Paso 1; el cliente `supabase` se agrega en el Paso 6 y las versiones exactas se fijan en el Paso 7.

## Arquitectura general

Separación estricta entre lógica de negocio y adaptadores de entrada/salida:

```
                 ┌──────────────┐        ┌───────────────────────────┐
 FastAPI ────▶  │  Services    │ ─────▶ │ Repositorios (interfaces) │
 (desde Fase 1)  │ (dominio)    │        └───────┬──────────┬────────┘
                 └──────────────┘                │          │
                                        SQLite impl.    Supabase impl.
                                        (Fase 1)        (Fase 3, RPC)
```

- **Services**: reglas de negocio puras (validaciones, composición de operaciones). No conocen HTTP ni FastAPI.
- **Repositorios/DAO**: contrato abstracto por agregado. Dos implementaciones intercambiables (SQLite y Supabase).
- **Adaptador**: la API FastAPI es delgada; solo traduce entrada/salida HTTP y llama a los services. En Fase 1 se verifica en `/docs`; en Fase 2 la consume el frontend estático (en local, sobre SQLite).
- Justificación: la lógica y la API escritas y probadas en Fase 1 se reutilizan sin cambios en Fases 2 y 3 (en la Fase 3 solo cambia la implementación del repositorio) (ver DD-02).

## Integraciones externas

| Servicio | Propósito | Tipo |
|----------|-----------|------|
| Supabase | PostgreSQL gestionado; persistencia desde Fase 3 | SDK Python (REST/PostgREST + RPC) |
| Vercel | Hosting serverless de FastAPI (ASGI) y estáticos | Plataforma de despliegue (Git) |
| GitHub | Origen del despliegue continuo | Repositorio Git |
| Tailwind CDN | Estilos del frontend sin build | CDN (script) |

## API REST (Fase 2, resumen)

Todas las rutas (salvo login y la página de login) exigen sesión. El frontend es HTML estático (`static/`) que carga los datos con `fetch` a endpoints `/api/...`; ante un 401 el JS redirige al login. Respuestas JSON; errores con código HTTP y mensaje.

| Recurso | Endpoints (propuestos) |
|---------|------------------------|
| Auth | `POST /api/login`, `POST /api/logout`, `GET /api/me` |
| Inventario | `GET /api/inventario` (solo activos), `DELETE /api/productos/{codigo}` (lógico, C-05) |
| Movimientos | `POST /api/stock/ingreso`, `POST /api/stock/egreso` |
| Órdenes | `POST /api/ordenes`, `GET /api/ordenes?numero=&desde=&hasta=` (C-04), `DELETE /api/ordenes/{numero}?reintegrar=true|false` (C-05; borrado por número, no por id) |
| Categorías | `GET /api/categorias`, `POST /api/categorias`, `PATCH /api/categorias/{clave}` (C-06e), `DELETE /api/categorias/{clave}` (C-06f; 409 si algún producto la usa); administración solo por API |
| Procesos | `GET /api/procesos`, `POST /api/procesos`, `PATCH /api/procesos/{clave}`, `DELETE /api/procesos/{clave}` (C-06f; catálogo administrado solo por API); `POST /api/ordenes` acepta `procesos` y `procesos_personalizados` |
| Reportes | `GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=` (C-06d; `desde` obligatorio, `hasta` opcional = hoy), `GET /api/reportes/productos-usados` (C-06d; productos para el selector) |
| Páginas | `GET /` (login), `GET /inventario`, `GET /ordenes` (Paso 5, C-06), `GET /reportes` (C-06d) |

Los paths exactos se cierran en el change del Paso 5.
