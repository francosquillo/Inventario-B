# Verify Report — paso-1-base-cli

Fecha: 2026-11-19. Auditoría de solo lectura (no se modificó código, tests ni artefactos; no se commiteó).

## Veredicto: PASS CON OBSERVACIONES

Sin bloqueantes ni mayores. Hay 5 observaciones menores, ninguna impide archivar.

## 1. Ejecución

| Comprobación | Resultado |
|---|---|
| `.venv/Scripts/python -m unittest discover -s tests -t . -v` | **82 tests, OK**, 7,2 s (8,3 s de reloj) |
| `openspec validate paso-1-base-cli --strict` | `Change 'paso-1-base-cli' is valid` |
| `pip check` | No broken requirements |
| Versiones instaladas vs `requirements*.txt` | coinciden (fastapi 0.165.0, uvicorn 0.54.0, itsdangerous 2.2.0, python-dotenv 1.2.4, httpx 0.28.1) |

Observación de ejecución: `TestClient` emite `StarletteDeprecationWarning` ("Using httpx with starlette.testclient is deprecated; install httpx2"). No afecta; relevante al fijar versiones en C-06/C-07.

## 2. Trazabilidad spec → código → test

Leyenda de tests: `T_app`=tests/test_api_app.py, `T_auth`=tests/test_api_auth.py, `T_inv`=tests/test_api_inventario.py, `T_sch`=tests/test_sqlite_schema.py, `T_cfg`=tests/test_config.py.

### api-http

| Requisito / Escenario | Código | Test | Estado |
|---|---|---|---|
| Arranque: base nueva (5 tablas + admin + login 1er request) | app.py:26-37, 54-64 | T_app::LifespanTest.test_arranque_crea_esquema_y_admin; T_auth::LoginTest.test_login_valido_devuelve_usuario_sin_hash (login inmediato tras lifespan) | OK |
| Arranque: repetido | app.py:26-37 | T_app::IdempotenciaTest.test_reinicio_conserva_datos_y_un_solo_admin | OK |
| Contraseña generada: variable ausente → log | app.py:57-62 | T_app::LogPasswordGeneradaTest.test_password_generada_se_loguea_una_vez_y_sirve_para_login | OK |
| Contraseña generada: arranque posterior sin log | inicializacion_service.py:9-10 | idem (assertNoLogs en 2.º arranque) | OK |
| Contraseña generada: variable definida sin log | app.py:57 | T_app::LogPasswordGeneradaTest.test_password_de_entorno_no_se_loguea | OK |
| SECRET_KEY obligatoria | app.py:42-48 | T_app::SecretKeyObligatoriaTest (entorno ausente, "" y "   ") | OK |
| Login: credenciales válidas (200, sin hash, HttpOnly, SameSite=Lax) | auth.py:15-21; app.py:67-74 | T_auth::LoginTest.test_login_valido_devuelve_usuario_sin_hash, test_cookie_de_sesion_sin_vencimiento | OK |
| Login: contraseña incorrecta (401 + sin sesión) | app.py:78-80; auth.py:17 | T_auth::LoginTest.test_rechazos_con_el_mismo_401_generico | OK |
| Login: usuario inexistente | idem | idem | OK |
| Login: usuario solo espacios | auth_service.py:15-16 | idem (`"   "`) | OK |
| Login nuevo reemplaza sesión | auth.py:17 | T_auth::MeTest.test_login_fallido_posterior_cierra_la_sesion | OK |
| Logout con sesión (204 + /me 401) | auth.py:24-27 | T_auth::LogoutTest.test_logout_cierra_sesion | OK |
| Logout sin sesión | auth.py:24-27 | T_auth::LogoutTest.test_logout_sin_sesion_204 | OK |
| /me con sesión | auth.py:30-32; dependencies.py:34-39 | T_auth::MeTest.test_con_sesion_devuelve_usuario | OK |
| /me sin sesión | dependencies.py:37-38 | T_auth::MeTest.test_sin_sesion_401 | OK |
| /me cookie adulterada | SessionMiddleware (Starlette) | T_auth::MeTest.test_cookie_con_firma_invalida_401 | OK |
| Inventario: listado con stock cero (orden, sin_stock, sin inactivos) | inventario.py:12-17 | T_inv::InventarioConSesionTest.test_lista_activos_ordenados_con_claves_exactas | OK |
| Inventario vacío | idem | T_inv::...test_vacio_devuelve_lista_vacia | OK |
| Inventario sin sesión | inventario.py:9 | T_inv::InventarioSinSesionTest.test_sin_sesion_401_sin_productos | OK |
| 422: campo faltante / vacío / tipo incorrecto | schemas.py:5-9 (strict) | T_auth::LoginTest.test_422_por_cuerpo_invalido (6 casos) | OK |
| Docs disponibles + OpenAPI con 4 rutas | FastAPI default | T_app::DocsTest.test_docs_y_openapi_exponen_los_endpoints | OK |

### autenticacion

| Requisito / Escenario | Código | Test | Estado |
|---|---|---|---|
| Hash distinto misma contraseña | security.py:12-18 | test_security::HashingTest.test_misma_contrasena_da_salts_y_hashes_distintos | OK |
| Verificación correcta | security.py:21-24 | test_security::HashingTest.test_verifica_la_contrasena_original | OK |
| Verificación incorrecta (`S3creta!`, vacía) | idem | test_security::HashingTest.test_rechaza_contrasenas_distintas_o_vacia | OK |
| Comparación en tiempo constante | security.py:24 | test_security::HashingTest.test_usa_compare_digest | OK |
| Login admin correcto | auth_service.py:14-22 | test_auth_service::LoginTest.test_login_valido | OK |
| Espacios alrededor del usuario | auth_service.py:15 | test_auth_service::LoginTest.test_espacios_alrededor_del_usuario | OK |
| Rechazo genérico: contraseña incorrecta / inexistente / campos vacíos | auth_service.py:17-21 | test_auth_service::LoginTest.test_credenciales_invalidas_mismo_mensaje; test_usuario_inexistente_igual_deriva_pbkdf2 | OK |
| Operaciones solo con sesión | dependencies.py:34-39; inventario.py:9 | T_inv::InventarioSinSesionTest; T_auth::MeTest.test_sin_sesion_401 | OK |

### consulta-inventario

| Requisito / Escenario | Código | Test | Estado |
|---|---|---|---|
| Solo activos | sqlite_repo.py:113-117; inventario_service.py:8-10 | test_inventario_service::ListarTest.test_solo_activos; test_sqlite_repositories::ProductoRepoTest.test_lista_solo_activos_como_entidades | OK |
| Orden por código | inventario_service.py:10 | test_inventario_service::ListarTest.test_orden_por_codigo | OK |
| Producto sin unidades / con unidades | entities.py:27-29 | test_inventario_service::ListarTest.test_sin_stock; test_domain::ProductoTest.test_sin_stock | OK |
| Sin productos / solo inactivos | idem | test_inventario_service::ListarTest.test_vacio_y_solo_inactivos; ProductoRepoTest.test_base_vacia, test_todos_inactivos | OK |

### inicializacion-base-datos

| Requisito / Escenario | Código | Test | Estado |
|---|---|---|---|
| Base nueva (5 tablas) | sqlite_repo.py:7-55, 65-67 | T_sch::EsquemaTest.test_crea_las_cinco_tablas | OK |
| Unicidad de código | sqlite_repo.py:18 | T_sch::ConstraintsTest.test_codigo_duplicado | OK |
| Stock negativo | sqlite_repo.py:20-21 | T_sch::ConstraintsTest.test_stock_negativo_o_no_entero | OK |
| Cantidad no positiva (ítem y movimiento) | sqlite_repo.py:36-37, 46-47 | T_sch::ConstraintsTest.test_cantidad_cero_en_item_y_movimiento | OK |
| Tipo de movimiento inválido | sqlite_repo.py:45 | T_sch::ConstraintsTest.test_tipo_de_movimiento_invalido | OK |
| Integridad referencial | sqlite_repo.py:44, 61 | T_sch::ConstraintsTest.test_movimiento_con_producto_inexistente; EsquemaTest.test_claves_foraneas_activas | OK |
| Idempotente: segundo arranque | sqlite_repo.py:8-54 (IF NOT EXISTS); inicializacion_service.py:9-10 | T_sch::IdempotenciaTest.test_reinicializar_no_pierde_datos; T_app::IdempotenciaTest; test_inicializacion_service::SembrarAdminTest.test_idempotente | OK |
| Seed con variable definida (login + sin texto plano) | inicializacion_service.py:7-17; config.py:13-17 | test_inicializacion_service::test_con_password_de_entorno, test_no_guarda_texto_plano; T_auth login | OK |
| Variable vacía o solo espacios | config.py:15-16 | T_cfg::PasswordAdminTest.test_none_si_falta_vacia_o_espacios; test_inicializacion_service::test_sin_password_genera_y_devuelve_una | OK (la cadena config→crear_app→seed no se prueba de punta a punta; cubierta por composición) |
| Contraseña aleatoria cuando falta la variable (>=16, login) | security.py:27-29 | test_security::GenerarPasswordTest; T_app::LogPasswordGeneradaTest | OK |
| No se repite en arranques posteriores | inicializacion_service.py:9-10 | T_app::LogPasswordGeneradaTest (assertNoLogs + hash igual); test_inicializacion_service::test_idempotente | OK |
| Ruta de base definida | config.py:9-10; app.py:41 | T_cfg::RutaDbTest.test_usa_variable_de_entorno (solo config; crear_app se prueba con ruta explícita) | PARCIAL |
| Ruta no definida (`inventario.db` en cwd) | config.py:6, 10 | T_cfg::RutaDbTest.test_default_en_cwd (solo config) | PARCIAL |

**Resumen: 52 escenarios — 50 OK, 2 PARCIAL, 0 FALTA.** Los 2 PARCIAL son de `config.ruta_db()` verificada a nivel función pero no a través de `crear_app` (el cableado `ruta_db or config.ruta_db()` en app.py:41 no tiene test directo). Impacto bajo.

## 3. Conformidad con el diseño (D1–D12 y 11 decisiones)

| Decisión | Evidencia | Estado |
|---|---|---|
| D1 estructura de módulos | Coincide con el árbol; CLI eliminada (sin `inventario/cli/`, `__main__.py`, `test_cli.py`; solo queda un `.pyc` huérfano ignorado por git) | OK |
| D2 esquema | sqlite_repo.py:7-55 idéntico a la tabla: `numero TEXT UNIQUE`, CHECK de fecha corregido (`date(fecha) IS NOT NULL AND fecha = date(fecha)`, línea 28), `typeof(...)='integer'`, CASCADE, 4 índices | OK |
| D3 hashing | PBKDF2-SHA256 600k (security.py:6), salt 16 B, dklen 32, hex, `hmac.compare_digest` (:24), `generar_password` token_urlsafe(16) = 22 car. | OK |
| D4 interfaces | repositories/base.py; consultas parametrizadas | OK |
| D5 services | `sembrar_admin` no lee environ; `login` recorta username, hash de relleno (auth_service.py:7, 18) | OK |
| D6 lifespan | init + seed, `IntegrityError` → `None` (app.py:32-35), WARNING en logger `inventario` (:57-62), `app.state.ruta_db` (:63), conexión cerrada (:36-37) | OK |
| D7 factory | firma con centinela (app.py:23, 40, 51), RuntimeError con `SECRET_KEY` (:42-48), handler 401 (:78-80), `title` | OK |
| D8 sesión | cookie `inventario_session`, `max_age=None`, `same_site="lax"`, `https_only` desde `SESSION_HTTPS_ONLY` (app.py:67-74); `clear()` en login (éxito y fallo) y logout; sesión `{usuario_id, username}` | OK |
| D9 endpoints | `def` sync, conexión por request con yield (dependencies.py:18-23), rutas y códigos según tabla | OK |
| D10 Pydantic | `ConfigDict(strict=True)` + `min_length=1` (schemas.py:5-9); `ProductoOut` sin `id`/`activo` | OK |
| D11 entorno | requirements.txt con 4 deps directas `==`; dev = `-r` + httpx; `.gitignore` con `*.db`, `.env`, `__pycache__/`, `.venv/`; `.env.example` existe (untracked) pero **no verificable** (permiso denegado) | OK / contenido no verificable |
| D12 tests API | TestClient con lifespan, SQLite en archivo temporal (tests/helpers.py), secret de test por `secrets.token_urlsafe` | OK |
| Entrada uvicorn `inventario.api.main:app`; `load_dotenv` solo en main.py | main.py:2-7; grep: `dotenv` solo ahí | OK |
| `max_age=None` (decisión 7 modificada) | app.py:71 + test `test_cookie_de_sesion_sin_vencimiento` | OK |

Sin desviaciones respecto del diseño.

## 4. Tareas

78/78 marcadas. Muestreo de evidencia: 2.x (test_security), 3.x/12.x (test_config), 4.x (test_sqlite_schema, 162 líneas), 5.3 (AST en test_domain), 6.x, 7.x, 8.x, 9.x, 10.1 (CLI inexistente), 11.1/11.2/11.4 (.gitignore, requirements, pip check), 13.6 (`inicializar_base` con `repo_cls` + CarreraDelSeedTest), 14.x, 15.x, 16.x, 17.2 (test AST ampliado), 17.3 (grep propio sin resultados). Todas con código/test real. 11.3 y 17.5 no son verificables por esta auditoría (`.env.example` ilegible por permisos; 17.5 es manual y su nota de cierre declara verificación con Playwright, no re-ejecutada aquí). Ninguna tarea marcada sin evidencia.

## 5. Reglas duras

| Regla | Resultado |
|---|---|
| 1. Sin paquetes externos fuera de `api/` | grep: fastapi/starlette/pydantic/dotenv solo en `inventario/api/`; domain/services/repositories limpios (además test AST `test_capas_internas_no_importan_frameworks_web`). Dependencias declaradas en requirements. **OK** |
| 2. Sin secretos en código | grep de `password=`/`secret=`/URLs/tokens: solo nombres de variable de entorno y literales de test (`Clave-Test-1`, `"mala"`), no de producción. `.env`/`.venv`/`*.db` ignorados por git. `.env.example` no verificable. **OK** |
| 3. Atomicidad / doble validación | Sin operaciones multi-producto en este change. CHECKs de BD presentes y probados; Pydantic estricto en HTTP; services validan credenciales. **OK (N/A mayormente)** |
| 4. Solo `unittest`, sin mocks de BD | Sin imports de pytest. `unittest.mock` solo para `os.environ`, `dotenv.load_dotenv`, y espías `wraps` de `compare_digest`/`verificar_password`; ninguno mockea la BD. Repos con SQLite real (`:memory:` o archivo temporal). Único doble: `RepoQueNoVeAlAdmin` (subclase del repo real, sobre BD real) para la carrera del seed. **OK** |
| 6. Commits solo a pedido | `git log`: solo `ba5f036`, `db44e23` (previos). Cambios sin commitear (inventario/, tests/, requirements*, .gitignore, .env.example, change). **OK** |

## 6. Revisión de calidad

Sin bugs funcionales encontrados. Puntos positivos: fijación de sesión mitigada (`session.clear()` antes de autenticar, también ante fallo, auth.py:17); `compare_digest` y PBKDF2 de relleno para usuarios inexistentes; 401 genérico idéntico; 422 vs 401 como se decidió; sin referencias residuales a CLI/getpass/`__main__` en `inventario/` ni `tests/`.

## 7. Verificación visual

N/A. design.md registra `Decision: no (no UI)`; `/docs` es tooling. `Visual verify: —` correcto.

## Hallazgos priorizados

**Blocker:** ninguno.
**Major:** ninguno.

**Minor**
1. app.py:41 / config.py:9 — Escenarios "Ruta de base definida/no definida" sólo probados a nivel `config.ruta_db()`; ningún test pasa por `crear_app()` sin `ruta_db` explícito (PARCIAL). Sugerencia: un test con `patch.dict(os.environ, {"INVENTARIO_DB_PATH": ..., "SECRET_KEY": ...})` que cree la app y verifique el archivo.
2. app.py:32-35 — `except sqlite3.IntegrityError` captura cualquier IntegrityError del seed y devuelve `None` en silencio (diseño D6 lo prevé para la carrera del `admin`; otras violaciones quedarían ocultas). Aceptable hoy; considerar loguear a nivel debug/warning.
3. schemas.py:8-9 — Sin `max_length` en `username`/`password`: una contraseña enorme obliga a PBKDF2 sobre input arbitrario (DoS leve). Considerar tope antes de C-07 junto con el rate limiting ya en backlog.
4. dependencies.py:34-39 / auth.py:24 — Logout y login por POST con cookie SameSite=Lax y sin token CSRF; aceptable en este alcance (JSON, same-origin), revisar en C-06 al llegar el frontend. `get_current_user` no consulta la base (riesgo ya aceptado en D8/DD-04).
5. Higiene: `tests/__pycache__/test_cli.cpython-314.pyc` huérfano (ignorado por git, inofensivo); `tests/helpers.py` tiene imports a mitad de archivo (líneas del bloque "Helpers de la API"); `StarletteDeprecationWarning` por `httpx` en tests.

**No verificable:** contenido de `.env` y `.env.example` (permiso denegado por configuración del usuario; no se intentaron rodeos). Tarea 17.5 (manual) no re-ejecutada.

## Acción recomendada

Archivar: `/opsx:archive paso-1-base-cli`, marcar `[x]` C-01 en `CHANGES.md` y esperar "Continuar" antes de C-02 (Regla dura 5). Las observaciones menores 1–4 pueden pasar al backlog (rate limiting/tope de longitud antes de C-07; CSRF en C-06); ninguna requiere corregirse antes de archivar.


## Re-verificación (2026-11-19, post-correcciones)

Correcciones aprobadas por el usuario (tarea 18 de `tasks.md`), con Strict TDD (RED confirmado: 3 fallos esperados; GREEN: 88 OK):

1. Obs. 1 corregida: `RutaDbPorEntornoTest.test_usa_inventario_db_path_del_entorno` y `test_sin_variable_usa_inventario_db_en_el_directorio_actual` (cwd temporal; el repo no recibe `inventario.db`). El código ya cumplía; los tests cierran la brecha de cobertura.
2. Obs. 2 corregida: `CarreraDelSeedTest.test_integrity_error_se_loguea_como_warning` y `test_sin_conflicto_no_loguea` (logger `inventario`, WARNING, sin secretos).
3. Obs. 3 corregida: `LoginTest.test_422_por_longitud_excesiva` y `test_longitudes_limite_se_procesan` (username max 64, password max 128); spec `api-http` y design D10 actualizados.
4. Obs. 4 DIFERIDA a C-06: registrada en design.md ("Riesgos diferidos") y en el scope de C-06 de `CHANGES.md`.
5. Obs. 5 corregida: `.pyc` huérfanos borrados e imports de `tests/helpers.py` movidos a la cabecera.

Resultado final: suite 88 tests, OK, ~8,4 s. `openspec validate paso-1-base-cli --strict`: válido.
