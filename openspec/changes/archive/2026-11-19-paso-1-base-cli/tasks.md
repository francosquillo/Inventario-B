# Tasks

> Strict TDD: en cada comportamiento, RED (test que falla por la razón correcta) → GREEN (mínimo código) → TRIANGULATE (segundo caso distinto) → REFACTOR (tests verdes tras cada paso).
> Comando de tests (desde la raíz): `python -m unittest discover -s tests -t .` — un módulo: `python -m unittest tests.test_<modulo> -v`.
> Grupos 1–9: solo stdlib, implementados en la revisión 1. Desde el grupo 10 (revisión 2, DD-12): dependencias solo vía `requirements*.txt` en `.venv`, FastAPI solo en `inventario/api/` (Regla dura 1). Sin mocks de base: SQLite real (`:memory:` en repos/services, archivo temporal en tests de API, D12) (Regla dura 4). Ver `design.md` D1–D12.
> **Gate**: revisión 2 de `design.md` re-aprobada por el usuario el 2026-11-19 (decisiones 1–11, con la 7 modificada: sesión sin `max_age`). Habilitado para continuar desde 10.1.

## 1. Andamiaje

- [x] 1.1 Crear paquetes vacíos `inventario/` (`__init__.py`, `domain/`, `repositories/`, `services/`, `cli/` — este último se elimina en 10.1) y `tests/__init__.py` según D1; verificar que `python -m unittest discover -s tests -t .` corre y reporta `Ran 0 tests` sin errores de import
- [x] 1.2 Crear `.gitignore` con `*.db`, `.env`, `__pycache__/`; verificar con `git check-ignore inventario.db .env` que ambos quedan ignorados

## 2. Hashing de contraseñas (`security.py`) — spec `autenticacion`

- [x] 2.1 RED: en `tests/test_security.py`, test de que `verificar_password` acepta la contraseña con la que se generó el hash (`hashear_password`, iteraciones bajas explícitas); verificar que falla por `ImportError`/`AttributeError`
- [x] 2.2 GREEN: implementar `hashear_password(password, salt=None, iteraciones=PBKDF2_ITERACIONES) -> (hash_hex, salt_hex)` y `verificar_password(...)` con PBKDF2-HMAC-SHA256, salt `secrets.token_bytes(16)`, dklen 32 (D3); verificar test verde
- [x] 2.3 TRIANGULATE: tests de contraseña distinta (`S3creta!`) y vacía → `False`; misma contraseña hasheada dos veces → salts y hashes distintos; hash es hex de 64 caracteres y salt hex de 32; con el mismo salt el hash es determinista; verificar todos verdes
- [x] 2.4 TRIANGULATE: test de que `verificar_password` delega en `hmac.compare_digest` (patch de `inventario.security.hmac.compare_digest` con `wraps`, verificando que fue llamado); test de que el default de iteraciones es `600_000`; verificar verdes
- [x] 2.5 RED→GREEN: test de `generar_password()` → longitud ≥ 16 y dos llamadas distintas; implementar con `secrets.token_urlsafe(16)`; verificar verde
- [x] 2.6 REFACTOR: extraer constantes (`PBKDF2_ITERACIONES`, `SALT_BYTES`, `DKLEN`), docstrings; `python -m unittest tests.test_security -v` verde

## 3. Configuración por entorno (`config.py`) — spec `inicializacion-base-datos`

- [x] 3.1 RED: en `tests/test_config.py` (usando `unittest.mock.patch.dict(os.environ, ...)`), test de que `ruta_db()` devuelve `INVENTARIO_DB_PATH` cuando está definida; verificar que falla
- [x] 3.2 GREEN: implementar `ruta_db()` y verificar verde
- [x] 3.3 TRIANGULATE: sin la variable → `inventario.db` en el cwd; `password_admin()` devuelve el valor si está definida, `None` si falta, vacía o solo espacios; verificar verdes
- [x] 3.4 REFACTOR: nombres de variables como constantes (`ENV_DB_PATH`, `ENV_ADMIN_PASSWORD`); verificar `tests.test_config` verde

## 4. Esquema SQLite (`repositories/sqlite_repo.py`) — spec `inicializacion-base-datos`

- [x] 4.1 RED: en `tests/test_sqlite_schema.py`, test de que tras `inicializar_esquema(conectar(":memory:"))` existen las 5 tablas (consulta a `sqlite_master`); verificar que falla
- [x] 4.2 GREEN: implementar `conectar(ruta)` (`row_factory=sqlite3.Row`, `PRAGMA foreign_keys = ON`) e `inicializar_esquema(conn)` con el DDL de D2 e índices; verificar verde
- [x] 4.3 TRIANGULATE constraints (un test por regla, cada uno espera `sqlite3.IntegrityError`): `codigo` duplicado; `stock = -1`; `stock = '5'` (no entero); `nombre` vacío/espacios; `orden_items.cantidad = 0`; `movimientos.cantidad = 0`; `tipo = 'ajuste'`; movimiento con `producto_id` inexistente (FK activa); `ordenes.fecha = '2026-02-30'` y `'2026/01/01'`; `username` duplicado; verificar todos verdes
- [x] 4.4 TRIANGULATE: test de que `ON DELETE CASCADE` borra `orden_items` al borrar la orden; test de que existen los índices `idx_ordenes_fecha`, `idx_orden_items_producto`, `idx_movimientos_producto`, `idx_movimientos_fecha`; verificar verdes
- [x] 4.5 TRIANGULATE idempotencia: llamar `inicializar_esquema` dos veces sobre la misma conexión con un producto insertado entre ambas → sin error y el producto intacto; verificar verde
- [x] 4.6 REFACTOR: DDL como constante `ESQUEMA_SQL`; crear `tests/helpers.py` con `conexion_inicializada()` e `insertar_producto(conn, codigo, nombre, stock, activo)` (SQL directo, parametrizado); verificar `tests.test_sqlite_schema` verde

## 5. Dominio e interfaces de repositorio

- [x] 5.1 RED: test de `Producto(..., stock=0).sin_stock is True` y `stock=5 → False`; verificar que falla
- [x] 5.2 GREEN: `domain/entities.py` (dataclasses frozen `Usuario`, `UsuarioAutenticado`, `Producto` con propiedad `sin_stock`) y `domain/errors.py` (`InventarioError`, `CredencialesInvalidas`, `MENSAJE_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."`); verificar verde
- [x] 5.3 Crear `repositories/base.py` con las ABCs de D4; test de que instanciar `UsuarioRepository()`/`ProductoRepository()` lanza `TypeError` y de que `domain/` y `services/` no importan `sqlite3` (inspección del código fuente con `ast`); verificar verdes

## 6. Repositorios SQLite — specs `autenticacion`, `consulta-inventario`

- [x] 6.1 RED: en `tests/test_sqlite_repositories.py`, test de `SqliteUsuarioRepository.crear(...)` seguido de `obtener_por_username` → devuelve `Usuario` con los mismos datos; verificar que falla
- [x] 6.2 GREEN: implementar `SqliteUsuarioRepository` (consultas parametrizadas, mapeo a `Usuario`); verificar verde
- [x] 6.3 TRIANGULATE: `obtener_por_username` de inexistente → `None`; username con comilla (`o'brien`) se guarda y recupera (parametrización); verificar verdes
- [x] 6.4 RED→GREEN: `SqliteProductoRepository.listar_activos()` devuelve solo activos como `Producto` con `activo` de tipo `bool`; triangular con base vacía → `[]` y con todos inactivos → `[]`; verificar verdes
- [x] 6.5 REFACTOR: función privada de mapeo fila→entidad; verificar `tests.test_sqlite_repositories` verde

## 7. Seed del admin (`services/inicializacion_service.py`) — spec `inicializacion-base-datos`

- [x] 7.1 RED: en `tests/test_inicializacion_service.py` (repo SQLite real sobre `:memory:`), test de que `sembrar_admin(repo, "Clave-Entorno-1")` crea `admin`, devuelve `None` y `verificar_password("Clave-Entorno-1", ...)` es `True`; verificar que falla
- [x] 7.2 GREEN: implementar `sembrar_admin` según D5/D6; verificar verde
- [x] 7.3 TRIANGULATE: con `password_entorno=None` → devuelve contraseña generada (≥ 16 caracteres) que verifica contra el hash guardado; la tabla `usuarios` no contiene la contraseña en texto plano (ni en `password_hash` ni en `salt`); verificar verdes
- [x] 7.4 TRIANGULATE idempotencia: segunda llamada (con o sin contraseña) → devuelve `None`, sigue habiendo exactamente 1 `admin` y su `password_hash`/`salt` no cambian; verificar verdes
- [x] 7.5 REFACTOR: constante `ADMIN_USERNAME = "admin"`; verificar `tests.test_inicializacion_service` verde

## 8. Login (`services/auth_service.py`) — spec `autenticacion`

- [x] 8.1 RED: en `tests/test_auth_service.py` (admin sembrado en `setUpClass` sobre repo SQLite `:memory:`), test de login válido → `UsuarioAutenticado(id, "admin")` sin campos de hash; verificar que falla
- [x] 8.2 GREEN: implementar `AuthService.login`; verificar verde
- [x] 8.3 TRIANGULATE: contraseña incorrecta, usuario inexistente, usuario vacío/espacios y contraseña vacía → `CredencialesInvalidas` con exactamente `"Usuario o contraseña incorrectos."` en todos los casos; `"  admin  "` con contraseña correcta → éxito; verificar verdes
- [x] 8.4 TRIANGULATE: test de que con usuario inexistente igual se ejecuta la derivación PBKDF2 (patch con `wraps` de `inventario.services.auth_service.verificar_password` o de `hashlib.pbkdf2_hmac`, verificando llamada); verificar verde
- [x] 8.5 REFACTOR: método privado de verificación y salt de relleno como constante de módulo; verificar `tests.test_auth_service` verde

## 9. Inventario (`services/inventario_service.py`) — spec `consulta-inventario`

- [x] 9.1 RED: en `tests/test_inventario_service.py`, test con `P-001` activo, `P-002` inactivo, `P-003` activo → `listar()` devuelve códigos `["P-001", "P-003"]`; verificar que falla
- [x] 9.2 GREEN: implementar `InventarioService.listar` (filtra vía repo, ordena por `codigo`); verificar verde
- [x] 9.3 TRIANGULATE: orden `B-10, A-01, C-05` → `A-01, B-10, C-05`; producto con stock 0 aparece con `sin_stock=True` y stock 5 con `False`; base vacía y solo inactivos → `[]`; verificar verdes
- [x] 9.4 REFACTOR: verificar `tests.test_inventario_service` verde sin duplicación con helpers

## 10. Retiro del código CLI (fuera de alcance por DD-12)

- [x] 10.1 Safety net: correr `python -m unittest discover -s tests -t .` y anotar el baseline (62 tests OK); borrar `inventario/cli/`, `inventario/__main__.py` y `tests/test_cli.py`; volver a correr la suite → verde, con la cantidad de tests reducida solo en los de `test_cli` (anotar el nuevo total); `grep -rn "getpass\|inventario.cli" inventario/ tests/` sin resultados

## 11. Entorno virtual y dependencias (D11)

- [x] 11.1 Agregar `.venv/` a `.gitignore`; verificar con `git check-ignore .venv/ inventario.db .env` que los tres quedan ignorados
- [x] 11.2 Crear `.venv` (`python -m venv .venv`), activarlo e instalar `fastapi`, `uvicorn`, `itsdangerous`, `python-dotenv`, `httpx`; escribir `requirements.txt` (runtime, `==` con las versiones instaladas de las dependencias directas) y `requirements-dev.txt` (`-r requirements.txt` + `httpx==...`); verificar desde un `.venv` recreado que `python -m pip install -r requirements-dev.txt` termina sin errores y que la suite sigue verde. Si alguna dependencia no instala en Python 3.14, detenerse y reportar
- [x] 11.3 Crear `.env.example` con solo los nombres `SECRET_KEY=`, `ADMIN_DEFAULT_PASSWORD=`, `INVENTARIO_DB_PATH=`, `SESSION_HTTPS_ONLY=` y un comentario de cómo generar `SECRET_KEY`; verificar que no contiene valores

## 12. Configuración de sesión (`config.py`) — spec `api-http`

- [x] 12.1 RED: en `tests/test_config.py`, test de que `secret_key()` devuelve `SECRET_KEY` cuando está definida; verificar que falla
- [x] 12.2 GREEN: implementar `secret_key()`; verificar verde
- [x] 12.3 TRIANGULATE: `secret_key()` → `None` si falta, vacía o solo espacios; `session_https_only()` → `True` para `"1"`/`"true"`/`"TRUE"`, `False` si falta o para `"0"`/`"false"`; verificar verdes
- [x] 12.4 REFACTOR: constantes `ENV_SECRET_KEY`, `ENV_SESSION_HTTPS_ONLY`; `python -m unittest tests.test_config -v` verde

## 13. App factory y lifespan (`inventario/api/app.py`) — specs `api-http`, `inicializacion-base-datos`

- [x] 13.1 RED: en `tests/test_api_app.py`, test de que `crear_app(ruta_db=<archivo en TemporaryDirectory>, secret_key=<token de test>, password_admin="Clave-Test-1")` usado en `with TestClient(app)` crea el archivo con las 5 tablas y el usuario `admin` (verificado abriendo otra conexión con `conectar`); verificar que falla por `ImportError`
- [x] 13.2 GREEN: crear `inventario/api/__init__.py` y `app.py` con `crear_app` + `lifespan` según D6/D7 (init esquema, `sembrar_admin`, `app.state.ruta_db`, cierre de conexión); verificar verde
- [x] 13.3 TRIANGULATE secret: `crear_app` sin `secret_key` con `SECRET_KEY` ausente del entorno (`patch.dict(os.environ, ...)`) y con `secret_key=""` → `RuntimeError` cuyo mensaje contiene `SECRET_KEY`; verificar verdes
- [x] 13.4 TRIANGULATE log de contraseña: con `password_admin=None` sobre base nueva → `assertLogs("inventario", "WARNING")` contiene una contraseña de ≥ 16 caracteres que permite `AuthService.login("admin", ...)`; segundo arranque sobre el mismo archivo → `assertNoLogs("inventario", "WARNING")` y el hash del `admin` no cambió; con `password_admin="Clave-Test-1"` → ningún log contiene `"Clave-Test-1"`; verificar verdes
- [x] 13.5 TRIANGULATE idempotencia: base con `admin` y un producto insertado con `insertar_producto` → nuevo arranque sin error, producto intacto, un solo `admin`; verificar verde
- [x] 13.6 TRIANGULATE carrera del seed (D6): extraer la inicialización del lifespan a una función probable sin servidor (p. ej. `inicializar_base(ruta, password_admin, repo_cls=SqliteUsuarioRepository)`); con una subclase de test de `SqliteUsuarioRepository` cuyo `obtener_por_username` devuelve `None` sobre una base real que ya tiene `admin` → no propaga `sqlite3.IntegrityError`, devuelve/loguea sin contraseña; verificar verde
- [x] 13.7 REFACTOR: helper en `tests/helpers.py` para crear la app de test en directorio temporal (`TemporaryDirectory` + `secrets.token_urlsafe(32)` + salir del `TestClient` antes del cleanup en Windows); `python -m unittest tests.test_api_app -v` verde

## 14. Sesión y autenticación HTTP (`schemas.py`, `dependencies.py`, `routers/auth.py`) — specs `api-http`, `autenticacion`

- [x] 14.1 RED: en `tests/test_api_auth.py` (app de test y `admin` sembrado en `setUpClass`), test `POST /api/login` con `admin`/`Clave-Test-1` → 200, cuerpo `{"id": <int>, "username": "admin"}` sin claves `password_hash`/`salt`; verificar que falla (404)
- [x] 14.2 GREEN: `LoginRequest`/`UsuarioOut` (D10), `get_conexion` + `get_auth_service` (D9), router `auth` con `POST /api/login` (limpia sesión, llama a `AuthService.login`, guarda `usuario_id`/`username`), `SessionMiddleware` en `crear_app` (D8) y handler `CredencialesInvalidas` → 401; verificar verde
- [x] 14.3 TRIANGULATE cookie: el `set-cookie` del login exitoso contiene `inventario_session`, `httponly`, `samesite=lax`, no `secure` y no `max-age` ni `expires` (cookie de sesión del navegador); con app `https_only=True` contiene `secure`; verificar verdes
- [x] 14.4 TRIANGULATE rechazos 401: contraseña incorrecta, usuario inexistente y username `"   "` → 401 con `detail == "Usuario o contraseña incorrectos."` idéntico en los tres y sin sesión utilizable; verificar verdes
- [x] 14.5 RED→GREEN `/api/me`: sin sesión → 401; tras login → 200 con `username == "admin"`; implementar `get_current_user` y `GET /api/me`; verificar verdes
- [x] 14.6 TRIANGULATE sesión: cookie `inventario_session` con firma inválida → `/api/me` 401; login exitoso seguido de login fallido en el mismo cliente → `/api/me` 401; verificar verdes
- [x] 14.7 RED→GREEN `/api/logout`: tras login, `POST /api/logout` → 204 y luego `/api/me` → 401; sin sesión previa → 204; implementar; verificar verdes
- [x] 14.8 TRIANGULATE 422 (Pydantic estricto, D10): cuerpo ausente, sin `password`, `password: ""`, `username: ""`, `username: 5`, `password: null` → 422 en todos; verificar verdes
- [x] 14.9 REFACTOR: mensajes y nombre de cookie como constantes; routers sin lógica de negocio; `python -m unittest tests.test_api_auth -v` verde

## 15. Inventario HTTP (`routers/inventario.py`) — specs `api-http`, `consulta-inventario`

- [x] 15.1 RED: en `tests/test_api_inventario.py`, test sin sesión `GET /api/inventario` → 401 sin productos en el cuerpo; verificar que falla (404)
- [x] 15.2 GREEN: `ProductoOut`, `get_inventario_service`, router `inventario` protegido con `Depends(get_current_user)`; verificar verde
- [x] 15.3 TRIANGULATE: con sesión y productos `B-10` (stock 0) y `A-01` (stock 5) activos y `C-99` inactivo (insertados con `insertar_producto` sobre el archivo de la app) → 200 con exactamente `A-01` (`stock: 5`, `sin_stock: false`) seguido de `B-10` (`stock: 0`, `sin_stock: true`) y solo las claves `codigo`, `nombre`, `stock`, `sin_stock`; verificar verde
- [x] 15.4 TRIANGULATE vacío: con sesión y base sin productos activos → 200 con `[]`; verificar verde
- [x] 15.5 TRIANGULATE: tras `POST /api/logout`, `GET /api/inventario` → 401; verificar verde
- [x] 15.6 RED→GREEN docs: en `tests/test_api_app.py`, `GET /docs` → 200 y `GET /openapi.json` contiene los paths `/api/login`, `/api/logout`, `/api/me`, `/api/inventario`; verificar verde
- [x] 15.7 REFACTOR: quitar duplicación de setup entre `test_api_*.py` (helper de login); `python -m unittest tests.test_api_inventario tests.test_api_app -v` verde

## 16. Entrada ASGI (`inventario/api/main.py`) — D7/D11

- [x] 16.1 RED→GREEN: test de que importar `inventario.api.main` con `SECRET_KEY` e `INVENTARIO_DB_PATH` (temporal) definidos en el entorno expone `app` de tipo `FastAPI` (`importlib` + `patch.dict(os.environ)`); implementar `main.py` con `load_dotenv()` + `app = crear_app()`; verificar verde
- [x] 16.2 TRIANGULATE: test de que importar `inventario.api.app` sin `SECRET_KEY` en el entorno no falla ni crea ninguna app; verificar verde

## 17. Verificación integral

- [x] 17.1 Ejecutar la suite completa `python -m unittest discover -s tests -t .` con `.venv` activo → todos verdes, 0 errores; anotar total y tiempo
- [x] 17.2 Regla dura 1: extender el test AST de 5.3 para que `inventario/domain/`, `inventario/services/` e `inventario/repositories/` no importen `fastapi`, `starlette`, `pydantic`, `uvicorn` ni `dotenv`; además `grep -rnE "^\s*(import|from)\s+(fastapi|starlette|pydantic|uvicorn|dotenv)" inventario/` solo muestra archivos de `inventario/api/`
- [x] 17.3 Regla dura 2: `grep -rniE "(password|secret_key|secret)\s*=\s*['\"][^'\"]+['\"]" inventario/` sin resultados; `.env.example` sin valores; `git status --porcelain --ignored` muestra `.env`, `.venv/` y `*.db` solo como ignorados
- [x] 17.4 `requirements.txt` contiene solo `fastapi`, `uvicorn`, `itsdangerous`, `python-dotenv` con `==`; `requirements-dev.txt` agrega solo `httpx`
- [x] 17.5 **MANUAL (usuario)**: con `.venv` activo y `.env` con `SECRET_KEY` (sin `ADMIN_DEFAULT_PASSWORD`) e `INVENTARIO_DB_PATH` apuntando a un `.db` de prueba nuevo, correr `uvicorn inventario.api.main:app --reload`; confirmar que la consola muestra la contraseña generada una sola vez; en `http://127.0.0.1:8000/docs`: `GET /api/inventario` → 401; `POST /api/login` con `admin` y la contraseña → 200; `GET /api/me` → `admin`; `GET /api/inventario` → `[]`; login con contraseña incorrecta → 401 genérico; `POST /api/logout` → 204 y `GET /api/me` → 401; reiniciar el servidor y verificar que no vuelve a mostrar contraseña; borrar el `.db` de prueba al final

## 18. Correcciones post-verify (aprobadas por el usuario 2026-11-19)

- [x] 18.1 `crear_app()` sin `ruta_db` explícito usa `INVENTARIO_DB_PATH` del entorno y cae a `./inventario.db` si no está definida (tests con `patch.dict(os.environ)` y `chdir` a un directorio temporal; sin mocks de base; limpiar archivos creados; el repo raíz no recibe ningún `inventario.db`)
- [x] 18.2 Loguear con logger `inventario` a nivel WARNING el `sqlite3.IntegrityError` tragado en `inicializar_base` (`inventario/api/app.py`), sin secretos; test con `assertLogs`; el resto del comportamiento igual
- [x] 18.3 `LoginRequest`: `username` `max_length=64`, `password` `max_length=128` (strict + `min_length=1`); tests: 65 chars → 422, 129 chars → 422, límites 64/128 aceptados (401); escenario en `specs/api-http/spec.md` y línea en `design.md` D10
- [x] 18.4 Higiene: borrar `.pyc` huérfanos de `tests/__pycache__` (p. ej. `test_cli`); mover a la cabecera los imports a mitad de archivo de `tests/helpers.py` (sin cambio de comportamiento)
- [x] 18.5 Registrar la observación 4 (sin token CSRF; SameSite=Lax mitiga) en `design.md` bajo "Riesgos diferidos" y agregar el bullet "Revisar CSRF de login/logout (observación verify C-01)" al scope de C-06 en `CHANGES.md`
- [x] 18.6 Suite completa verde + `openspec validate paso-1-base-cli --strict`

## Workflow follow-up

- Verify del change contra specs/design/tasks (`openspec-verify`).
- `/opsx:archive paso-1-base-cli` y marcar `[x]` C-01 en `CHANGES.md`.
- Backlog: rate limiting de login antes de C-07 (decisión 1 de la revisión 2).
- Pausa: esperar "Continuar" del usuario antes de C-02 (Regla dura 5). Commit solo a pedido (Regla dura 6).


> **Notas de cierre del apply (2026-11-19)**
> - 11.3: `.env.example` lo creó el usuario con PowerShell (los permisos del entorno bloquean a los agentes leer/escribir `.env*`); su contenido no pudo verificarse automáticamente.
> - 17.5: verificado por el orquestador a pedido del usuario, con Playwright sobre `/docs` y una base temporal propia (sin tocar `prueba.db`): login desde Swagger 200 `{id:1, username:admin}`; `/api/me` 200; `/api/inventario` 200 `[]`; logout 204; luego `/api/me` y `/api/inventario` 401 "No autenticado."; login con contraseña mala y usuario inexistente 401 "Usuario o contraseña incorrectos."; `username` vacío y numérico 422. Contraseña generada: 1 aviso en el primer arranque, 0 en el segundo.
