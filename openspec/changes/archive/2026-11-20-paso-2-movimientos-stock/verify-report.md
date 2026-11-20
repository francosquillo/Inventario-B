# Verify Report — paso-2-movimientos-stock (C-02)

Fecha: 2026-11-20

## Veredicto: PASS (W-1, W-2, W-3, S-3 y S-4 resueltos el 2026-11-20)

0 CRITICAL, 0 WARNING abiertos (3 resueltos), 2 SUGGESTION abiertas (S-1, S-2); S-3 y S-4 resueltas. Ningún hallazgo bloquea el archivado. 10.2 (manual `/docs`) hecha por el orquestador: OK (ver sección al final).

## Resultados de ejecución

- `.venv/Scripts/python -m unittest discover -s tests -t .` -> `Ran 199 tests in 60.148s — OK` (antes de los ajustes). Tras los ajustes post-verify: `Ran 211 tests — OK`.
- `openspec validate paso-2-movimientos-stock --strict` -> `Change 'paso-2-movimientos-stock' is valid`.

## Completitud

tasks.md: 55 tareas, 54 `[x]`, 1 `[ ]` (10.2, manual). Todas las `[x]` tienen código/test correspondiente (ver tabla). `requirements*.txt` sin cambios (git no los muestra modificados).

## Correctitud — trazabilidad

Código: R=`repositories/sqlite_repo.py`, S=`services/stock_service.py`, M=`services/movimientos_service.py`, V=`api/errores_validacion.py`, A=`api/app.py`.
Tests: SR=`test_sqlite_stock_repository`, SS=`test_stock_service`, API=`test_api_stock`, MR=`test_sqlite_movimiento_repository`, MS=`test_movimientos_service`, AM=`test_api_movimientos`, EV=`test_errores_validacion`, SCH=`test_sqlite_schema`.

### movimientos-stock

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Suma sobre existente / stock cero / nombre ignorado | R:178-198 | SR test_suma_a_producto_existente, test_suma_desde_stock_cero, test_nombre_distinto_en_codigo_existente_se_ignora | OK |
| Alta por ingreso (aparece en inventario) | R:187-193 | SR test_alta_de_codigo_nuevo; API test_alta_con_codigo_en_minusculas... | OK |
| Nombre requerido (sin nombre / solo espacios) | S:20-28, R:187 | SR test_codigo_inexistente_sin_nombre_no_escribe; SS test_nombre_vacio_en_codigo_nuevo_pide_nombre; API test_codigo_nuevo_sin_nombre_422_y_no_crea | OK |
| Reactivación | R:185-186 (UPDATE activo=1, conserva nombre) | SR test_reactivacion_de_inactivo; API test_reactivacion | OK |
| Egreso parcial / total | R:200-215 | SR test_egreso_parcial..., test_egreso_de_todo_deja_cero_y_activo | OK |
| Exceso / stock cero rechazado | R:206-210 | SR test_exceso_informa_disponible..., test_stock_cero_se_rechaza | OK |
| Egreso inexistente / inactivo | R:204 | SR test_inexistente_e_inactivo_no_se_encuentran | OK |
| Cantidades (0, -1, 2.5, "5", True, 10001; 10000 ok) | S:13-17 | SS test_cantidades_invalidas_..., test_cantidad_maxima_aceptada, EgresoServiceTest.test_cantidades_invalidas | OK |
| Código/nombre normalizados (espacios, minúsculas, solo espacios, variantes, nombre recortado) | normalizacion.py:9-16, S:20-28 | SS test_codigo_con_espacios..., test_minusculas_crean..., test_codigo_invalido, test_nombre_se_recorta_en_el_alta | OK |
| Código 50 chars "medidos tras normalizar" | normalizacion.py:14 | SS test_codigo_invalido; **vía HTTP el schema mide antes de normalizar** | partial (W-1) |
| Registro de movimiento (ingreso, alta, egreso, usuario sesión, fecha -03:00) | R:194-196, 211-213 | SR test_suma_y_alta_registran_un_movimiento_con_fecha; API test_movimiento_con_usuario_de_la_sesion_y_fecha_local | OK |
| Fecha siempre en Argentina (UTC -> -03:00; naive rechazada) | R:153-157 | SR test_fecha_en_otra_zona..., test_fecha_naive_lanza_value_error_sin_escribir; test_tiempo | OK |
| Normalización de fechas legadas e idempotencia | R:69-73,85 | SCH NormalizacionFechasLegadasTest (4 tests + base vacía) | OK (ver W-2) |
| Atomicidad (ingreso / alta / egreso) | R:160-172 | SR AtomicidadTest (FK de usuario inexistente, sin mocks) | OK |
| Egresos concurrentes | R:161-165 BEGIN IMMEDIATE + UPDATE condicional | SR ConcurrenciaTest (archivo temporal, 2 hilos, 5 rondas) | OK |

### consulta-movimientos

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Orden desc / misma fecha por id / vacío | R:225 `ORDER BY fecha DESC, id DESC` | MR test_devuelve_del_mas_nuevo..., test_misma_fecha_desempata_por_id_mayor_primero, test_sin_movimientos... | OK |
| Datos completos del movimiento | R:228-236 | MR (mapeo) ; AM test_orden_y_serializacion_exacta_de_fecha | OK |
| Incluye inactivos | R:219-224 (sin filtro activo) | MR test_incluye_movimientos_de_productos_inactivos; AM test_incluye_producto_inactivo | OK |
| Filtro código (exacto, minúsculas/espacios, inexistente, vacío = sin filtro) | M:28-31, R:246-248 | MR FiltroCodigoTest; MS test_codigo_en_minusculas..., test_valores_vacios_son_sin_filtro; AM test_codigo_vacio_es_sin_filtro | OK |
| Rango inclusivo / solo desde / solo hasta / combinado | R:249-254 | MR FiltroFechasTest (5 tests); AM test_codigo_en_minusculas_y_fechas, test_filtro_solo_desde | OK |
| Validación fechas: formato, inexistente, desde>hasta, vacía | M:11-37 | MS test_formato_de_fecha_invalido, test_fecha_inexistente, test_desde_posterior_a_hasta; AM test_errores_de_filtro_en_espanol | OK |

### api-http

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Ingreso: suma, alta, minúsculas, reactivación, sin nombre (422), claves exactas | routers/stock.py:27-30, schemas | API IngresoConSesionTest | OK |
| Ingreso sin sesión 401 sin cambios | dependencies.py:46 | API StockSinSesionTest | OK |
| Egreso: aceptado, minúsculas, 409 con disponible, 404 inexistente/inactivo, 401 | routers/stock.py:33-43, A:100-106 | API EgresoConSesionTest, StockSinSesionTest | OK |
| Validación de cuerpos: texto, decimal/cero, límite, solo espacios, 51 chars, nombre 121 | schemas.py:31-47, S | API ValidacionHttpTest | OK |
| GET /api/movimientos: sin filtros, filtros combinados, vacío | routers/movimientos.py | AM MovimientosConSesionTest, MovimientosFiltrosTest | OK |
| Errores de movimientos (formato, desde>hasta, 401) | M, dependencies | AM test_errores_de_filtro_en_espanol, test_sin_sesion_* | OK |
| 422 uniforme en español (campo faltante, JSON mal formado) | A:108-112, V | API test_cantidad_faltante; test_api_auth test_422_por_json_mal_formado; EV | OK |
| Un solo mensaje / error no contemplado | V:48-52, 45 | EV test_varios_errores..., test_tipo_desconocido... | OK (HTTP end-to-end del "varios errores" solo a nivel función; ver S-3) |
| OpenAPI 422 -> ErrorOut (login, ingreso, egreso, movimientos) | routers | AM OpenApiTest; test_api_app OpenApiErrorOutTest | OK |
| MODIFIED login: faltante, vacío, tipo, largo 65, cuerpo ausente | A:108 | test_api_auth test_422_por_cuerpo_invalido, test_422_por_longitud_excesiva | OK |
| MODIFIED docs: siete endpoints | app.py includes | AM OpenApiTest; test_api_app DocsTest | OK (el chequeo manual en /docs es 10.2) |

## Coherencia con design.md

- D1: `StockRepository` con `registrar_ingreso/egreso` atómicos, `ResultadoIngreso` frozen. Cumple.
- D2: `BEGIN IMMEDIATE`, UPDATE condicional `AND stock >= ?` + `rowcount`, movimiento con fecha explícita, rollback total. Cumple.
- D3/D7: `normalizar_codigo` compartida entre stock y movimientos; reloj inyectable (`ahora`), una llamada por operación aceptada (test RelojTest). Cumple.
- D4: errores y mensajes exactos; mapeo 422/404/409. Cumple.
- D5: Pydantic estricto (`strict=True`, `Cantidad`), sin transformaciones, siempre 200; 401 antes que validación (test). Cumple.
- D6: `ZONA_AR` offset fijo sin zoneinfo; serialización con `astimezone(ZONA_AR)`; sin cambio de DDL; migración idempotente. Cumple.
- D9: capability separada, `ORDER BY fecha DESC, id DESC`, query params `str`, router protegido a nivel `dependencies`. Cumple.
- D10: handler único `RequestValidationError`, primer error, `ErrorOut` en OpenAPI. Cumple.

## Reglas duras

1. Dependencias/capas: ningún import de fastapi/pydantic/starlette en `domain/`, `services/`, `repositories/` (grep vacío; además lo cubre `test_domain`/`test_stock_service`). `requirements*.txt` sin cambios. OK.
2. Sin secretos: solo `os.environ`/config; los hits de grep son `secret_key` como parámetro y `secrets` stdlib. OK.
3. Atomicidad + doble validación (Pydantic y service). OK.
4. Sin pytest; `unittest.mock` solo se usa para `os.environ` (`patch.dict`) y una prueba de AuthService de C-01; ningún mock de repositorios ni de la base. OK.
5/6. Sin commits realizados por este change (git muestra solo cambios sin commitear).

## Revisión de las desviaciones del apply

- (a) Tests de la sección 9 sin RED visible: es una desviación de proceso TDD estricto, pero el comportamiento sí está cubierto y la suite es verde. Juicio: aceptable, queda como observación (S-1); no invalida el resultado.
- (b) `_transaccion` hace `commit()` si `conn.in_transaction` antes de `BEGIN IMMEDIATE` (R:163-164). Es seguro en producción: la conexión es por request (`get_conexion`) y, antes del service, solo corre código que no abre transacción (la sesión es cookie; los SELECT no abren transacción implícita). En tests, cierra escrituras pendientes del helper en la misma conexión (comportamiento deseado). Riesgo: si en el futuro un service hiciera DML previo en la misma conexión (p. ej. C-03), un fallo posterior no podría revertir ese DML porque ya habría sido confirmado en silencio. Juicio: aceptable ahora, merece comentario/aserción (S-2).
- (c) JSON mal formado sin sesión devuelve 422 en vez de 401: FastAPI parsea el cuerpo antes de resolver dependencias. El spec solo exige 401 con "cuerpo válido", y el test de cuerpo inválido válido-JSON sí da 401. Juicio: aceptable, sin fuga de información.
- (d) Test espía (spy-repo) eliminado: la cobertura equivalente existe con repo real (RelojTest, atomicidad sin mocks), alineado con la regla dura 4. Juicio: correcto.

## Hallazgos

### CRITICAL
Ninguno.

### WARNING

- **W-1 — Resuelto (2026-11-20)**: `str_strip_whitespace=True` en `IngresoRequest`/`EgresoRequest`; tests `test_api_stock.ValidacionHttpTest.test_codigo_con_espacios_se_mide_tras_normalizar`, `test_codigo_de_51_tras_recortar_sigue_rechazado`, `test_nombre_con_espacios_se_mide_tras_recortar`, `test_egreso_con_codigo_con_espacios_se_mide_tras_normalizar`. Original: `inventario/api/schemas.py:37,39,45` — `max_length=50`/`120` se evalúan sobre el valor crudo, pero el spec dice "50 caracteres (medidos tras normalizar)" y el nombre "se recorta" antes. Un código de 49 caracteres con 2 espacios alrededor (o un nombre con espacios sobrantes > 120 crudos) se rechaza por HTTP con 422 aunque normalizado sea válido. El service sí lo mide bien, así que el comportamiento HTTP diverge del service y del spec. Sin test que lo cubra. Recomendación: quitar `max_length` de Pydantic para `codigo`/`nombre` (el service ya valida) o aceptar la divergencia y documentarla.
- **W-2 — Resuelto (2026-11-20)**: el UPDATE solo toca filas interpretables, el arranque avisa con WARNING; tests `test_sqlite_schema.NormalizacionFechasLegadasTest.test_fecha_no_parseable_no_rompe_el_arranque_y_se_deja_intacta`, `test_sin_filas_no_parseables_no_loguea_advertencia`, `test_fila_no_parseable_sigue_intacta_en_arranques_repetidos`. Original: `inventario/repositories/sqlite_repo.py:69-73,85` — `NORMALIZAR_FECHAS_SQL` corre en cada arranque; una fila legada con fecha no parseable por `strftime` (p. ej. texto basura) produce NULL y el UPDATE falla con `IntegrityError: NOT NULL constraint failed: movimientos.fecha`, por lo que la app no arranca (reproducido en memoria). Con la tabla vacía de C-01 no afecta, pero una base editada a mano quedaría inutilizable. Recomendación: agregar `AND strftime(...) IS NOT NULL` al WHERE (o `COALESCE`) y un test.
- **W-3 — Resuelto (2026-11-20)**: `re.fullmatch` con `[0-9]`; test `test_movimientos_service.test_formato_estricto_rechaza_salto_final_y_digitos_unicode`. Original: `inventario/services/movimientos_service.py:8,15` — el regex `^\d{4}-\d{2}-\d{2}$` acepta un `\n` final (`$`) y dígitos Unicode; `"2026-11-19\n"` pasa el formato y cae en "no es una fecha válida" con un salto de línea dentro del mensaje, en lugar del mensaje de formato. Impacto bajo (solo por query manual). Recomendación: `re.fullmatch` con `[0-9]`.

### SUGGESTION

- **S-1** Sección 9 (tests de la API/handler) sin evidencia RED: documentar la desviación en el reporte del apply.
- **S-2** `inventario/repositories/sqlite_repo.py:163-164` — dejar un comentario más explícito (o aserción en tests) de que el commit implícito asume una conexión sin trabajo pendiente; revisarlo al llegar a C-03/C-05.
- **S-3 — Resuelto (2026-11-20)**: `test_api_stock.ValidacionHttpTest.test_varios_errores_responde_solo_el_primero`. Original: Falta un test HTTP del escenario "Varios errores" (`POST /api/stock/ingreso` con `{"cantidad": 0}` -> "El campo codigo es obligatorio."); hoy solo se verifica sobre `mensaje_validacion` (EV test_varios_errores_devuelve_solo_el_primero). Probable que pase, pero el spec lo define a nivel API.
- **S-4 — Resuelto (2026-11-20)**: el listado omite filas con fecha no interpretable y avisa (ver design.md, "Ajustes post-verify"); tests `test_sqlite_movimiento_repository.FechaLegadaNoParseableTest`. Original: `inventario/repositories/sqlite_repo.py:226-236` — `datetime.fromisoformat` en `_a_movimiento` rompería el listado completo (500) si hubiera una fila con fecha no ISO; relacionado con W-2 (la normalización la evitaría).

## Otros chequeos de casos borde

- Reactivación de inactivos: conserva nombre, suma stock, `reactivado=true`, un solo producto (cubierto en repo y API).
- Empates de orden: `ORDER BY m.fecha DESC, m.id DESC` correcto y probado.
- FK de usuario inexistente produce `IntegrityError` -> 500; riesgo aceptado en design (PA-03).
- Comparación textual de rangos correcta mientras todas las filas compartan offset `-03:00` (garantizado por serialización + migración).

## 10.2 /docs

**Resultado: OK** (2026-11-20, orquestador, Playwright).

- Entorno: `uvicorn inventario.api.main:app --port 8765` con base temporal fuera del repo (`INVENTARIO_DB_PATH` en el scratchpad) y `ADMIN_DEFAULT_PASSWORD`/`SECRET_KEY` de prueba por entorno (no se leyó `.env`). Servidor y navegador cerrados al terminar.
- Swagger lista los 7 endpoints; el esquema `ErrorOut` está publicado y referenciado en los 422.
- Desde la UI de Swagger ("Try it out" → "Execute"): login 200 y ingreso `"  tor-01 "` → 200 `TOR-01`, `creado: true` (reutiliza la cookie de sesión).
- Desde la misma página (misma cookie), 30 casos, todos conformes a spec: suma con nombre ignorado; código nuevo sin nombre 422; cantidad 0 / 10001 / `"5"` / 2.5 → 422; código vacío / 51 caracteres, nombre 121 → 422; JSON inválido 422; egreso parcial 200, excedido 409 (disponible/solicitado), inexistente 404, a cero `sin_stock: true`; movimientos más nuevo primero con `-03:00` y `usuario: admin`, filtro por código en minúsculas, parámetros vacíos = sin filtro, un día, futuro `[]`, los tres mensajes de fecha; login sin password 422; logout 204; sin sesión ingreso/egreso/movimientos 401.
- SQL: `movimientos` tiene exactamente 4 filas (2 ingresos, 2 egresos); los intentos rechazados no dejaron filas ni productos (`NUEVO-1`, `LARGO` no existen).
- Reinicio de la app sobre la base existente: arranca, login 200, movimientos intactos. No existe `prueba.db` en el repo, así que no se probó con una base legada de C-01 (ver W-2).
- Consola del navegador: solo los "Failed to load resource" de las respuestas 4xx provocadas.
- Observaciones: JSON mal formado sin sesión → 422 (no 401), ya conocido; OpenAPI no documenta el 401 de los endpoints protegidos (la spec no lo exige).
