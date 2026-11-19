# Design

> **Revisión 2 (2026-11-19)** — cambio de alcance DD-12: se elimina la CLI y el adaptador pasa a ser FastAPI (D7–D12 nuevas; D1 y D6 actualizadas; D2 corregida con el CHECK de `fecha` real). D3–D5 se conservan tal cual se implementaron (tareas 1–9). Requiere re-aprobación (ver "Aprobación del usuario").

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver `specs/`.

Estado al momento de la revisión: tareas 1–9 implementadas y verdes (62 tests, ~4,7 s): `security.py`, `config.py`, esquema SQLite, dominio, ABCs + repos SQLite, `sembrar_admin`, `AuthService.login`, `InventarioService.listar`. Existe código del grupo 10 (CLI) que queda fuera de alcance y se borra.

Restricciones que moldean el diseño:
- Regla dura 1 (revisada, DD-12): dependencias solo declaradas en `requirements.txt` / `requirements-dev.txt` e instaladas en `.venv`; FastAPI (y Starlette/Pydantic) solo dentro de `inventario/api/`. `domain/` y `services/` tampoco importan `sqlite3`.
- Python 3.10+ (entorno local 3.14.7, SQLite 3.50.4); sin `STRICT` tables.
- Sin secretos en código (RN-SE-01): `SECRET_KEY`, `ADMIN_DEFAULT_PASSWORD` vía `os.environ` (+ `.env` local con `python-dotenv`).
- Tests con `unittest` (endpoints con `TestClient`) y SQLite real, sin mocks de base (Regla dura 4).
- El esquema SQLite debe poder espejarse 1:1 en `db/schema.sql` (Postgres) del Paso 5.

## Goals / Non-Goals

**Goals:**
- Fijar estructura de paquetes y contratos (interfaces de repositorio, firmas de services) para todos los pasos.
- Esquema completo de 5 tablas con constraints que la base hace cumplir por sí misma.
- Hashing reutilizable por el seed de Supabase (IN-01).
- API FastAPI como adaptador delgado: app factory testeable con `TestClient`, auth por cookie firmada, endpoints de login/logout/me/inventario verificables en `/docs`.

**Non-Goals:**
- Métodos de repositorio para escribir productos, movimientos u órdenes (C-02..C-05). Los tests insertan productos con SQL directo.
- Migraciones de esquema (`CREATE ... IF NOT EXISTS` alcanza sin datos productivos).
- Rate limiting / bloqueo por intentos fallidos, cambio de contraseña, alta de usuarios (PA-03).
- Frontend (`static/`), CORS (todo es same-origin), Supabase, Vercel.

## Decisions

### D1 — Estructura de directorios y módulos

```
Inventario-B/
├── inventario/
│   ├── __init__.py
│   ├── config.py                # os.environ: INVENTARIO_DB_PATH, ADMIN_DEFAULT_PASSWORD, SECRET_KEY, SESSION_HTTPS_ONLY
│   ├── security.py              # hashear_password(), verificar_password(), generar_password()
│   ├── domain/
│   │   ├── entities.py          # dataclasses frozen: Usuario, UsuarioAutenticado, Producto
│   │   └── errors.py            # InventarioError, CredencialesInvalidas, MENSAJE_CREDENCIALES_INVALIDAS
│   ├── repositories/
│   │   ├── base.py              # ABCs: UsuarioRepository, ProductoRepository
│   │   └── sqlite_repo.py       # conectar(), inicializar_esquema(), SqliteUsuarioRepository, SqliteProductoRepository
│   ├── services/
│   │   ├── inicializacion_service.py  # sembrar_admin()
│   │   ├── auth_service.py      # AuthService.login()
│   │   └── inventario_service.py # InventarioService.listar()
│   └── api/                     # ÚNICO lugar con fastapi/starlette/pydantic
│       ├── __init__.py
│       ├── app.py               # crear_app(...) (factory) + lifespan (init esquema + seed); NO instancia `app` al importar
│       ├── main.py              # load_dotenv() + `app = crear_app()` → objetivo de uvicorn (y de api/index.py en Fase 3)
│       ├── dependencies.py      # get_conexion, get_auth_service, get_inventario_service, get_current_user
│       ├── schemas.py           # modelos Pydantic estrictos: LoginRequest, UsuarioOut, ProductoOut
│       └── routers/
│           ├── __init__.py
│           ├── auth.py          # POST /api/login, POST /api/logout, GET /api/me
│           └── inventario.py    # GET /api/inventario
├── tests/
│   ├── helpers.py               # conexion_inicializada(), insertar_producto(); + helper de app de test (D11)
│   ├── test_security.py … test_inventario_service.py   # existentes (tareas 1–9)
│   ├── test_api_app.py          # factory, SECRET_KEY obligatoria, lifespan init/seed, log de contraseña, /docs
│   ├── test_api_auth.py         # login/logout/me, cookie flags, 401/422
│   └── test_api_inventario.py   # GET /api/inventario
├── requirements.txt
├── requirements-dev.txt
├── .env.example                 # solo nombres de variables
└── .gitignore                   # *.db, .env, .venv/, __pycache__/
```

Se eliminan `inventario/cli/`, `inventario/__main__.py` y `tests/test_cli.py`. La separación `app.py` / `main.py` evita que importar la factory en tests dispare `crear_app()` con el entorno real (que fallaría sin `SECRET_KEY`).

Comando de tests (desde la raíz, con `.venv` activo): `python -m unittest discover -s tests -t .`

### D2 — Esquema SQLite y paridad con PostgreSQL

`inicializar_esquema(conn)` ejecuta un único script DDL con `IF NOT EXISTS`. Cada conexión activa `PRAGMA foreign_keys = ON` y usa `row_factory = sqlite3.Row`.

| Tabla | Columnas SQLite | Equivalente Postgres (Paso 5) |
|-------|-----------------|-------------------------------|
| `usuarios` | `id INTEGER PRIMARY KEY`, `username TEXT NOT NULL UNIQUE`, `password_hash TEXT NOT NULL`, `salt TEXT NOT NULL`, `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP` | `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`, `text`, `created_at timestamptz NOT NULL DEFAULT now()` |
| `productos` | `id INTEGER PRIMARY KEY`, `codigo TEXT NOT NULL UNIQUE`, `nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0)`, `stock INTEGER NOT NULL DEFAULT 0 CHECK (typeof(stock) = 'integer' AND stock >= 0)`, `activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))` | `stock integer ... CHECK (stock >= 0)`, `activo boolean NOT NULL DEFAULT true`, `CHECK (btrim(nombre) <> '')` |
| `ordenes` | `id INTEGER PRIMARY KEY`, `numero TEXT NOT NULL UNIQUE`, `fecha TEXT NOT NULL CHECK (date(fecha) IS NOT NULL AND fecha = date(fecha))`, `usuario_id INTEGER NOT NULL REFERENCES usuarios(id)`, `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP` | `numero text UNIQUE`, `fecha date NOT NULL`, `usuario_id bigint REFERENCES usuarios(id)`, `created_at timestamptz` |
| `orden_items` | `orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE`, `producto_id INTEGER NOT NULL REFERENCES productos(id)`, `cantidad INTEGER NOT NULL CHECK (typeof(cantidad) = 'integer' AND cantidad > 0)`, `PRIMARY KEY (orden_id, producto_id)` | idéntico con `bigint` en FKs |
| `movimientos` | `id INTEGER PRIMARY KEY`, `fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`, `producto_id INTEGER NOT NULL REFERENCES productos(id)`, `tipo TEXT NOT NULL CHECK (tipo IN ('ingreso','egreso'))`, `cantidad INTEGER NOT NULL CHECK (typeof(cantidad) = 'integer' AND cantidad > 0)`, `usuario_id INTEGER NOT NULL REFERENCES usuarios(id)` | `fecha timestamptz NOT NULL DEFAULT now()`, mismo CHECK de `tipo` |

Índices: `idx_ordenes_fecha (fecha)`, `idx_orden_items_producto (producto_id)`, `idx_movimientos_producto (producto_id)`, `idx_movimientos_fecha (fecha)`.

Notas de paridad:
- `INTEGER PRIMARY KEY` sin `AUTOINCREMENT` (la no reutilización de ids no es requisito).
- **Afinidad INTEGER (hallazgo del apply)**: SQLite convierte `'5'` (texto numérico) a `5` *antes* de evaluar el CHECK, así que `typeof(...) = 'integer'` rechaza `5.5` y `'abc'` pero **no** `'5'`. La base no es la defensa contra texto numérico: la capa HTTP lo rechaza con Pydantic estricto (D10) y los services validan tipo en C-02+. Postgres sí rechaza `'5'` en un `integer` vía RPC tipado.
- **CHECK de `fecha` (corregido en el apply)**: `date(fecha) IS NOT NULL AND fecha = date(fecha)`. El `IS NOT NULL` es necesario porque `date('2026/01/01')` devuelve `NULL` y `fecha = NULL` evalúa a `NULL`, que un CHECK acepta. La igualdad rechaza fechas irreales (`2026-02-30` se normaliza a `2026-03-02`), igual que el tipo `date` de Postgres.
- Timestamps: texto UTC `YYYY-MM-DD HH:MM:SS` en SQLite; `timestamptz` en Postgres. Los repos devuelven `str`.
- Booleano `activo`: el repo SQLite convierte 0/1 a `bool`.
- `ordenes.numero` como `TEXT` (PA-06, aprobado).

### D3 — Hashing de contraseñas (`security.py`) — sin cambios

- `hashlib.pbkdf2_hmac("sha256", ..., PBKDF2_ITERACIONES, dklen=32)`, `PBKDF2_ITERACIONES = 600_000`, parámetro `iteraciones` con ese default.
- Salt `secrets.token_bytes(16)`; hash y salt en hex. Comparación con `hmac.compare_digest` (RN-AU-06).
- `generar_password()` → `secrets.token_urlsafe(16)` (22 caracteres).
- Nota del apply: `auth_service` calcula el hash de relleno al importar (~0,3 s, una vez por proceso). Aceptado: en la API ocurre al arrancar el servidor, no por request.

### D4 — Interfaces de repositorio (`repositories/base.py`) — sin cambios

`UsuarioRepository.obtener_por_username / crear`, `ProductoRepository.listar_activos`; devuelven entidades de dominio; repos SQLite reciben la conexión por constructor y usan consultas parametrizadas (RN-SE-05).

### D5 — Services — sin cambios

- `sembrar_admin(usuarios, password_entorno) -> str | None` (devuelve la contraseña solo si fue generada; no lee `os.environ`).
- `AuthService(usuarios).login(username, password) -> UsuarioAutenticado` (recorta el username; vacío/inexistente/incorrecta → `CredencialesInvalidas` con `"Usuario o contraseña incorrectos."`; PBKDF2 de relleno ante inexistente).
- `InventarioService(productos).listar() -> list[Producto]` (activos ordenados por `codigo` en Python; `Producto.sin_stock`).

### D6 — Inicialización idempotente en el lifespan

`crear_app` registra un `lifespan` (context manager `asynccontextmanager`) que al arrancar:
1. `conn = conectar(ruta_db)` → `inicializar_esquema(conn)`.
2. `generada = sembrar_admin(SqliteUsuarioRepository(conn), password_admin)`, envuelto en `try/except sqlite3.IntegrityError` → si otro proceso creó el `admin` entre la consulta y el insert (dos workers arrancando a la vez), se trata como "ya existe": `generada = None`, sin log de contraseña. `sembrar_admin` no traduce la excepción (decisión del apply); la composición sí conoce SQLite, así que la captura vive en `inventario/api/app.py`, no en services.
3. Si `generada` no es `None`: `logging.getLogger("inventario").warning(...)` con la contraseña y la advertencia "anotala, no se volverá a mostrar". Nivel WARNING porque uvicorn no configura handlers para loggers de la app y Python muestra WARNING+ por stderr (handler de último recurso); en tests se verifica con `assertLogs("inventario", "WARNING")`. No se escribe a archivo ni se devuelve por HTTP.
4. `conn.close()`; la ruta queda en `app.state.ruta_db` para las dependencias.

Idempotencia: `CREATE ... IF NOT EXISTS` + consulta previa del `admin` + `UNIQUE(username)` como red ante carreras.

### D7 — App factory y composition root (`inventario/api/app.py`)

```python
def crear_app(*, ruta_db: str | None = None, secret_key: str | None = None,
              password_admin: str | None = <leer de config>, https_only: bool | None = None) -> FastAPI
```

- Cada parámetro omitido se toma de `config.py` (`ruta_db()`, `secret_key()`, `password_admin()`, `session_https_only()`); los tests pasan valores explícitos y no dependen del entorno real. Para distinguir "no pasado" de `None` en `password_admin` se usa un centinela.
- Si la `secret_key` resultante es `None`/vacía → `RuntimeError("Falta la variable de entorno SECRET_KEY ...")` al crear la app (D8).
- Registra `SessionMiddleware`, los routers `auth` e `inventario` bajo `/api`, y los handlers de errores de dominio: `CredencialesInvalidas` → 401 `{"detail": "Usuario o contraseña incorrectos."}`.
- `title="Inventario-B API"`; `/docs` y `/openapi.json` habilitados (default de FastAPI).
- `main.py`: `from dotenv import load_dotenv; load_dotenv(); app = crear_app()`. `load_dotenv()` no pisa variables ya definidas en el entorno.

### D8 — Sesión por cookie firmada (`SessionMiddleware`)

- `SessionMiddleware(secret_key=..., session_cookie="inventario_session", max_age=None, same_site="lax", https_only=https_only)`; Starlette siempre la marca `HttpOnly`. Requiere `itsdangerous`.
- `max_age=None` → cookie de sesión del navegador (sin `Max-Age`/`Expires`): se borra al cerrar el navegador (decisión del usuario 2026-11-19, reemplaza las 8 h propuestas). Trade-off aceptado: la cookie firmada no tiene vencimiento del lado servidor; si se copiara seguiría siendo válida hasta rotar `SECRET_KEY`. Un test verifica que el `Set-Cookie` no incluye `Max-Age` ni `Expires`.
- `https_only` desde `SESSION_HTTPS_ONLY` (`"1"/"true"` → `True`; default `False` para `http://127.0.0.1` local). En Vercel (C-07) se define en `true`.
- **`SECRET_KEY` ausente → la app no arranca** (fail-closed). Alternativa descartada: generar una clave efímera con advertencia (las sesiones se invalidarían en cada `--reload` y en serverless cada instancia tendría una clave distinta: bugs silenciosos). Para desarrollo local, `.env` (con `python-dotenv`) la provee; `.env.example` documenta cómo generarla: `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Ver "Decisiones a confirmar".
- Contenido de la sesión: `{"usuario_id": int, "username": str}`. Login exitoso: `request.session.clear()` y luego se escriben ambos campos (mitiga fijación de sesión). Login fallido: también limpia la sesión previa. Logout: `request.session.clear()`.
- `get_current_user(request) -> UsuarioAutenticado`: lee la sesión; si falta o está incompleta → `HTTPException(401, "No autenticado.")`. No consulta la base en cada request (no hay borrado ni desactivación de usuarios en el alcance; se revisará con PA-03). Una firma inválida hace que Starlette descarte la cookie → sesión vacía → 401.
- Riesgo aceptado (DD-04): sin revocación individual; rotar `SECRET_KEY` invalida todas las sesiones.

### D9 — Endpoints y dependencias (`dependencies.py`, `routers/`)

| Método y ruta | Auth | Request | Respuesta OK | Errores |
|---|---|---|---|---|
| `POST /api/login` | pública | `LoginRequest` | 200 `UsuarioOut` + cookie | 401 genérico, 422 |
| `POST /api/logout` | pública (idempotente) | — | 204 sin cuerpo | — |
| `GET /api/me` | sesión | — | 200 `UsuarioOut` | 401 |
| `GET /api/inventario` | sesión | — | 200 `list[ProductoOut]` (puede ser `[]`) | 401 |

- Endpoints declarados con `def` (no `async def`): `sqlite3` (y luego el cliente `supabase`) es bloqueante; FastAPI los corre en el threadpool (DD-03).
- **Conexión por request**: `get_conexion(request)` es una dependencia con `yield` que abre `conectar(request.app.state.ruta_db)` y la cierra al terminar. Motivo: `sqlite3` prohíbe por defecto usar una conexión desde otro hilo (`check_same_thread`), y FastAPI ejecuta cada endpoint sync en un hilo del pool distinto al del lifespan. Una conexión por request en el hilo del endpoint es correcta, simple y equivale al patrón del cliente Supabase. Abrir un archivo SQLite local cuesta microsegundos.
- `get_auth_service(conn=Depends(get_conexion)) -> AuthService(SqliteUsuarioRepository(conn))`; `get_inventario_service` análogo. Son el único punto que cambia en el Paso 5 (repos Supabase).
- Routers sin lógica: traducen request → service → schema de salida. `ProductoOut` se construye desde `Producto` (incluye `sin_stock`).

### D10 — Schemas Pydantic estrictos (`schemas.py`)

- `class LoginRequest(BaseModel): model_config = ConfigDict(strict=True); username: str = Field(min_length=1); password: str = Field(min_length=1)` → `5` (número) o `null` en lugar de texto → 422; `""` → 422. No se aplica `str_strip_whitespace`: un username `"   "` pasa Pydantic y el service lo rechaza con el 401 genérico (RN-AU-05); la contraseña nunca se recorta.
- Límites (post-verify): `username` `max_length=64`, `password` `max_length=128` → mitiga DoS por PBKDF2 sobre entradas enormes.
- Convención para C-02+ (fijada ahora porque SQLite no rechaza `'5'`, ver D2): cantidades como `Annotated[int, Field(strict=True, gt=0)]` (equivalente `StrictInt` + `gt=0`) → `"5"`, `5.0`, `true`, `0`, `-1` → 422. Fechas como `datetime.date` (en modo JSON estricto Pydantic acepta solo la cadena ISO `YYYY-MM-DD`).
- Salida: `UsuarioOut {id: int, username: str}`, `ProductoOut {codigo: str, nombre: str, stock: int, sin_stock: bool}` (sin `id` interno ni `activo`: siempre `true` en este listado).
- Los cuerpos de 422 son los de FastAPI por defecto (`detail` con la lista de errores).
- Pydantic es solo la guardia HTTP; los services mantienen su validación (Regla dura 3, doble validación).

### D11 — Entorno, dependencias y ejecución

- `requirements.txt` (runtime, versiones exactas `==` fijadas en el apply con lo que resuelva `pip` en Python 3.14): `fastapi`, `uvicorn`, `itsdangerous`, `python-dotenv`. `requirements-dev.txt`: `-r requirements.txt` + `httpx`. Solo dependencias directas (las transitivas las resuelve pip).
- Setup Windows (desde la raíz del repo):
  - PowerShell: `python -m venv .venv` → `.\.venv\Scripts\Activate.ps1` (si la política lo bloquea: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`) → `python -m pip install -r requirements-dev.txt`.
  - Git Bash: `python -m venv .venv` → `source .venv/Scripts/activate` → `python -m pip install -r requirements-dev.txt`.
- Ejecutar: copiar `.env.example` a `.env` y completar `SECRET_KEY` (y opcionalmente `ADMIN_DEFAULT_PASSWORD`); luego `uvicorn inventario.api.main:app --reload` → `http://127.0.0.1:8000/docs`.
- `.env.example`: `SECRET_KEY=`, `ADMIN_DEFAULT_PASSWORD=`, `INVENTARIO_DB_PATH=`, `SESSION_HTTPS_ONLY=` (sin valores).
- `.gitignore`: agregar `.venv/` (ya tiene `*.db`, `.env`, `__pycache__/`).

### D12 — Tests de la API

- `unittest.TestCase` + `fastapi.testclient.TestClient` usado como context manager (`with TestClient(app) as client:`) para que corra el lifespan.
- Base: **archivo SQLite real en `tempfile.TemporaryDirectory()`**, pasado como `ruta_db` a `crear_app`. `:memory:` no sirve: cada conexión a `:memory:` es una base distinta y la conexión por request (D9) no vería el esquema; compartir una sola conexión con `check_same_thread=False` entre hilos es frágil. Windows: cerrar todas las conexiones antes de que el `TemporaryDirectory` se borre (las cierra `get_conexion` y el lifespan); salir del `with TestClient` antes del cleanup.
- Los tests de repositorios/services existentes siguen con `:memory:` (Regla dura 4 intacta).
- Costo PBKDF2: el parámetro `iteraciones` configurable solo existe en `security.py` (lo usan `test_security`); `sembrar_admin` y `AuthService` usan el default real 600k y no se modifican (tareas 7–8 cerradas). Mitigación: cada clase de test crea la app y siembra el admin en `setUpClass` (un hash por clase) y reutiliza el cliente; cada login exitoso o fallido cuesta ~0,3 s → se limitan a los necesarios por escenario. Estimado: +5–8 s a la suite. Ver "Decisiones a confirmar".
- `secret_key` de test: generada en el test con `secrets.token_urlsafe(32)` (nunca literal en código de producción; en tests no es un secreto real).
- Cookie flags: se verifican sobre el header `set-cookie` de la respuesta de login (`httponly`, `samesite=lax`; sin `secure` con `https_only=False` y con `secure` con `https_only=True`).
- Cookie adulterada: se fija en el cliente una cookie `inventario_session` con firma inválida → `GET /api/me` 401.

## UI Mockups

- Design system revision: 1 (no aplica)
- Decision: no (no UI) — 2026-11-19. Change de backend/API; la Swagger UI (`/docs`) es tooling de verificación, no UI de producto. El frontend llega en C-06 con mockup gate.
- Mockups: —
- Approval: —
- Preview: —
- Visual verify: —

## Risks / Trade-offs

- [600k iteraciones encarecen los tests de API] → admin sembrado una vez por clase y logins mínimos (D12).
- [Iteraciones no persistidas por usuario] → cambiar `PBKDF2_ITERACIONES` invalida hashes existentes; se aborda con PA-03.
- [`CREATE TABLE IF NOT EXISTS` no altera tablas existentes] → si un paso posterior cambia una columna, borrar y recrear la base local.
- [La contraseña generada queda en el log del servidor (DD-12)] → solo una vez, solo en local; recomendado definir `ADMIN_DEFAULT_PASSWORD` en `.env`; recuperación: borrar el `.db`.
- [`/docs` no enmascara la contraseña del body de login (DD-12)] → aceptado para verificación local.
- [Sin rate limiting de login] → brute force posible en red local; backlog antes del deploy (C-07). PBKDF2 600k limita a ~3 intentos/s por worker.
- [`get_current_user` confía en la cookie sin consultar la base] → aceptable sin alta/baja de usuarios; revisar con PA-03.
- [Python 3.14 muy reciente] → si alguna dependencia no tiene wheel, el apply lo reporta como bloqueo antes de seguir (no se baja la versión sin consultar).
- [Conexión por request sobre SQLite con varios requests concurrentes] → SQLite serializa escrituras; en este paso todo es lectura salvo el seed.

### Riesgos diferidos

- [Sin token CSRF en login/logout (observación 4 del verify)] → la cookie es SameSite=Lax y la API solo acepta JSON same-origin, lo que mitiga el riesgo; se revisa en C-06 con el frontend (registrado en `CHANGES.md`).

## Migration Plan

Sin datos previos. Pasos de la revisión: borrar el código CLI (sin consumidores), agregar `inventario/api/`, requirements y `.env.example`. Rollback = eliminar `inventario/api/`, `requirements*.txt`, `.venv/` y el `.db` local.

## Decisiones a confirmar por el usuario

Decisiones 1–6 de la revisión 1 siguen aprobadas (numero TEXT, PBKDF2 600k/16B/32, contraseña generada de 22 caracteres, `./inventario.db`, `.gitignore` adelantado) salvo las que la revisión deja sin efecto (3 intentos de la CLI, marcador `SIN STOCK`). Nuevas:

1. **Regla de 3 intentos fallidos**: se elimina a nivel API (no existe "cerrar la CLI"); rate limiting de login queda en backlog para antes de C-07. Recomendado: eliminar + backlog.
2. **`SECRET_KEY` ausente → la app se niega a arrancar** con mensaje claro (alternativa: clave efímera con advertencia). Recomendado: negarse a arrancar.
3. **`python-dotenv` desde este paso** (carga `.env` solo en `main.py`, no en la factory ni en tests). Recomendado: sí.
4. **Conexión SQLite por request** (dependencia con `yield`) y tests de API sobre archivo temporal (no `:memory:`). Recomendado: sí.
5. **Pydantic estricto**: `""` y tipos incorrectos en login → 422 (no 401); username solo espacios → 401 genérico. Convención `Field(strict=True, gt=0)` para enteros desde C-02. Recomendado: sí.
6. **Forma de respuestas**: login/me → `{id, username}`; inventario → lista JSON plana de `{codigo, nombre, stock, sin_stock}`; logout → 204. Recomendado: sí.
7. **Sesión**: cookie `inventario_session`, sin `max_age` (dura hasta cerrar el navegador — cambiado por el usuario), SameSite=Lax, HttpOnly, `https_only` por `SESSION_HTTPS_ONLY` (default false local); login (exitoso o fallido) limpia la sesión previa. Recomendado: sí.
8. **Contraseña generada** por `logging` nivel WARNING del logger `inventario` (visible en la consola de uvicorn). Recomendado: sí.
9. **Tests de API con iteraciones reales** (600k) y admin sembrado por clase, sin agregar parámetro de iteraciones a `sembrar_admin`/`AuthService`. Recomendado: sí (alternativa: inyectar iteraciones, tocando código cerrado).
10. **Entrada de uvicorn**: `inventario.api.main:app` (factory en `app.py` separada). Recomendado: sí.
11. **Versiones exactas** (`==`) de dependencias directas fijadas en el apply según lo que resuelva Python 3.14. Recomendado: sí.

## Aprobación del usuario

- 2026-11-19 (revisión 1): el usuario aprobó explícitamente las 7 decisiones a confirmar (numero TEXT, PBKDF2 600k/16B/32, 3 intentos, contraseña generada de 22 caracteres, `./inventario.db`, `.gitignore` adelantado, marcador `SIN STOCK`). Governance CRÍTICA: habilitado para apply.
- 2026-11-19 (revisión 2, cambio de alcance DD-12): **re-aprobada por el usuario**, revisando las decisiones 1–11 de a una. Todas aprobadas como se recomendó salvo la 7: la sesión dura hasta cerrar el navegador (`max_age=None`). Habilitado para apply desde la tarea 10.1.
