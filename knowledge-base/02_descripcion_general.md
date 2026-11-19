# Descripción General

Tipo de sistema: `web_app` (arranca como CLI en Fase 1 y evoluciona a web). Dominio: inventario y órdenes de trabajo para taller/pyme. Escala: equipo chico (pocos usuarios, mismos permisos).

## Stack tecnológico

| Capa | Tecnologías | Versión mínima |
|------|-------------|----------------|
| Fase 1 — lógica y CLI | Python stdlib únicamente: `sqlite3`, `hashlib`, `datetime`, `os` | Python 3.10+ |
| Fase 1 — persistencia | SQLite (archivo local, ruta opcional `INVENTARIO_DB_PATH`) | sqlite 3.x (incluido en Python) |
| Fase 2 — backend | FastAPI (ASGI) + `uvicorn`, Pydantic, cliente `supabase` (Python, síncrono), `python-dotenv`, `itsdangerous` (sesión) | Versiones a fijar en el Paso 6; tests de API con `TestClient` (requiere `httpx`, solo test) |
| Fase 2 — base de datos | Supabase (PostgreSQL gestionado) + funciones PL/pgSQL vía RPC | PostgreSQL 15+ |
| Fase 2 — frontend | HTML5 + Tailwind CSS vía CDN + JavaScript vanilla | Navegadores modernos |
| Fase 3 — despliegue | Vercel (Serverless Functions, runtime Python), GitHub como origen | — |

Las versiones exactas se fijan en `requirements.txt` durante el Paso 5/6.

## Arquitectura general

Separación estricta entre lógica de negocio y adaptadores de entrada/salida:

```
 CLI (Fase 1) ─────────┐
                       ▼
                 ┌──────────────┐        ┌───────────────────────────┐
 FastAPI ────▶  │  Services    │ ─────▶ │ Repositorios (interfaces) │
 (Fase 2)        │ (dominio)    │        └───────┬──────────┬────────┘
                 └──────────────┘                │          │
                                        SQLite impl.    Supabase impl.
                                        (Fase 1)        (Fase 2, RPC)
```

- **Services**: reglas de negocio puras (validaciones, composición de operaciones). No conocen consola ni HTTP.
- **Repositorios/DAO**: contrato abstracto por agregado. Dos implementaciones intercambiables (SQLite y Supabase).
- **Adaptadores**: CLI y API FastAPI son delgados; solo traducen entrada/salida y llaman a los mismos services.
- Justificación: la lógica escrita y probada en Fase 1 se reutiliza sin cambios en Fase 2 (ver DD-02).

## Integraciones externas

| Servicio | Propósito | Tipo |
|----------|-----------|------|
| Supabase | PostgreSQL gestionado; persistencia en Fase 2 | SDK Python (REST/PostgREST + RPC) |
| Vercel | Hosting serverless de FastAPI (ASGI) y estáticos | Plataforma de despliegue (Git) |
| GitHub | Origen del despliegue continuo | Repositorio Git |
| Tailwind CDN | Estilos del frontend sin build | CDN (script) |

## API REST (Fase 2, resumen)

Todas las rutas (salvo login y la página de login) exigen sesión. El frontend es HTML estático (`static/`) que carga los datos con `fetch` a endpoints `/api/...`; ante un 401 el JS redirige al login. Respuestas JSON; errores con código HTTP y mensaje.

| Recurso | Endpoints (propuestos) |
|---------|------------------------|
| Auth | `POST /api/login`, `POST /api/logout`, `GET /api/me` |
| Inventario | `GET /api/productos` (solo activos), `DELETE /api/productos/<id>` (lógico) |
| Movimientos | `POST /api/movimientos/ingreso`, `POST /api/movimientos/egreso` |
| Órdenes | `POST /api/ordenes`, `GET /api/ordenes?desde=&hasta=`, `GET /api/ordenes/<id>`, `DELETE /api/ordenes/<id>?reintegrar=true|false` |
| Páginas | `GET /` (login), `GET /dashboard` |

Los paths exactos se cierran en el change del Paso 5.
