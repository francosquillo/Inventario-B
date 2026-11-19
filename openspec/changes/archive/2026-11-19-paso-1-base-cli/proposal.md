# Proposal

> **Cambio de alcance (2026-11-19, decisión explícita del usuario, DD-12)**: se elimina la CLI. El Paso 1 entrega la base de un backend **FastAPI sobre SQLite local**, verificado a mano en la Swagger UI (`/docs`) y con tests `unittest` + `TestClient`. El nombre del change (`paso-1-base-cli`) se conserva como nombre histórico. Esta revisión requiere re-aprobación del usuario antes de continuar el apply (governance CRÍTICA).

## Why

Inventario-B no tenía código: ni base de datos, ni forma de autenticarse, ni de ver el stock. El Paso 1 (C-01) construye el cimiento del que dependen todos los pasos siguientes (movimientos, órdenes, borrados, Supabase y frontend del Paso 5): el modelo de datos completo, el acceso con usuario y contraseña hasheada, la arquitectura Repositorio/Services y, desde ahora, el adaptador HTTP (FastAPI) que reemplaza a la CLI. Construir la API desde el inicio evita escribir y descartar una interfaz de consola y deja la superficie lista para el frontend.

## What Changes

- Paquete Python `inventario/` con capas `domain/`, `services/`, `repositories/`, `security.py`, `config.py` (ya implementadas) y el nuevo adaptador HTTP `inventario/api/` (FastAPI). La lógica (`domain/`, `services/`, `repositories/`) no importa FastAPI.
- Base SQLite local (`sqlite3`) con las 5 tablas del modelo: `usuarios`, `productos`, `ordenes`, `orden_items`, `movimientos`. Ruta por `INVENTARIO_DB_PATH` (opcional, default `./inventario.db`).
- Inicialización idempotente al arrancar la app (lifespan de FastAPI): crea tablas e índices si no existen y siembra `admin` solo si no existe.
- Contraseña inicial del `admin` desde `ADMIN_DEFAULT_PASSWORD`; si falta, se genera una aleatoria y se escribe **una única vez** en el log del servidor (DD-07, DD-12).
- Hashing PBKDF2-HMAC-SHA256 con salt aleatorio por usuario y verificación con `hmac.compare_digest`.
- Sesión por cookie firmada (`SessionMiddleware`, `SECRET_KEY` desde entorno), HttpOnly, SameSite=Lax.
- Endpoints JSON: `POST /api/login`, `POST /api/logout`, `GET /api/me`, `GET /api/inventario` (protegidos con 401 salvo login); validación de entrada con modelos Pydantic estrictos (422 ante cuerpos malformados); Swagger UI en `/docs`.
- Inventario: solo productos activos, ordenados por código, stock 0 visible con marca `sin_stock`, lista vacía explícita.
- Dependencias declaradas en `requirements.txt` (runtime) y `requirements-dev.txt` (`httpx`, solo test), instaladas en `.venv`.
- **Se elimina** el código CLI ya escrito (`inventario/cli/`, `inventario/__main__.py`, `tests/test_cli.py`).
- Suite `unittest` (SQLite real, sin mocks de base): hashing, login válido/inválido, init idempotente, listado de inventario y endpoints con `TestClient`.

## Capabilities

### New Capabilities
- `inicializacion-base-datos`: creación idempotente del esquema (5 tablas, constraints, índices) y seed del usuario `admin` con contraseña desde entorno o generada.
- `autenticacion`: hashing de contraseñas (PBKDF2 + salt), verificación en tiempo constante y login con mensaje genérico; condición de sesión para operar.
- `consulta-inventario`: listado del inventario general (solo activos, stock 0 incluido, orden estable, estado vacío).
- `api-http`: adaptador HTTP JSON: arranque con inicialización, sesión por cookie firmada, endpoints de login/logout/me/inventario, códigos 401/422 y documentación interactiva en `/docs`.

### Removed (antes de archivar, sin spec principal previo)
- `interfaz-cli`: descartada por el cambio de alcance; nunca llegó a `openspec/specs/`, por lo que se elimina el delta del change sin bloque REMOVED.

### Modified Capabilities
<!-- Ninguna: no existen specs previos en openspec/specs/. -->

## Impact

- **Código**: `inventario/` (paquete; nuevo `inventario/api/`), `tests/` (suite `unittest`). Se borran `inventario/cli/`, `inventario/__main__.py` y `tests/test_cli.py`. No hay `python -m inventario`; el servidor se levanta con `uvicorn`.
- **Dependencias (Regla dura 1 revisada)**: `fastapi`, `uvicorn`, `itsdangerous`, `python-dotenv` en `requirements.txt`; `httpx` en `requirements-dev.txt`. La lógica sigue usando solo stdlib + `sqlite3`.
- **Configuración**: `SECRET_KEY` (sensible, obligatoria), `ADMIN_DEFAULT_PASSWORD` (sensible), `INVENTARIO_DB_PATH` (opcional), `SESSION_HTTPS_ONLY` (opcional). Se agrega `.env.example` solo con nombres y `.gitignore` incluye `*.db`, `.env`, `.venv/`, `__pycache__/`.
- **Fases posteriores**: C-02..C-05 agregan endpoints sobre la misma app y dependencias; el Paso 5 cambia el repositorio a Supabase sin tocar services ni endpoints y agrega `static/`; `security.py` lo reutiliza el seed de Supabase.
- **Fuera de alcance**: ingreso/egreso de stock, órdenes, borrados, alta de usuarios y cambio de contraseña (PA-03), rate limiting de login, frontend web (Paso 5).
