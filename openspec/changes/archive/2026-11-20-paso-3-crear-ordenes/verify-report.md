# Verify Report — paso-3-crear-ordenes (C-03)

Fecha: 2026-11-20

## Veredicto: PASS (W-1, W-2, S-1 y S-2 resueltos el 2026-11-20; quedan S-3 y S-4 informativos)

0 CRITICAL, 0 WARNING abiertos (2 resueltos), 2 SUGGESTION abiertas informativas (S-3, S-4) y 2 resueltas. Ningún hallazgo bloquea el archivado. Tras los ajustes: `Ran 301 tests — OK` (284 + 17 nuevos) y `openspec validate paso-3-crear-ordenes --strict` válido.

## Resultados de ejecución

- `.venv/Scripts/python -m unittest discover -s tests -t .` -> `Ran 284 tests in 67.580s — OK` (la línea "Seed del admin omitido por IntegrityError" es salida esperada de un test de arranque, no una falla).
- `openspec validate paso-3-crear-ordenes --strict` -> `Change 'paso-3-crear-ordenes' is valid`.
- Sondeo adicional con `TestClient` (sin puertos, base temporal): 22 casos borde HTTP (ver "Otros chequeos").

## Completitud

tasks.md: 36 tareas, 35 `[x]`, 1 `[ ]` (7.2, manual, del orquestador). Todas las `[x]` tienen código/test correspondiente (ver tablas). `requirements*.txt` sin cambios en git. No hay archivos nuevos fuera de `inventario/`, `tests/` y el change (más el ajuste a `knowledge-base/03_actores_y_roles.md`, modificado antes de este change; ver S-4).

## Correctitud — trazabilidad

Código: R=`repositories/sqlite_repo.py`, OS=`services/orden_service.py`, F=`services/fechas.py`, N=`services/normalizacion.py`, RT=`api/routers/ordenes.py`, SC=`api/schemas.py`, V=`api/errores_validacion.py`, A=`api/app.py`, E=`domain/errors.py`.
Tests: OR=`test_sqlite_orden_repository`, OSV=`test_orden_service`, API=`test_api_ordenes`, EV=`test_errores_validacion`, FE=`test_fechas`, DOM=`test_domain`.

### ordenes-trabajo

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Alta: dos componentes (stock 3 y 0, B-02 activo) | R:`_crear_en_transaccion` (INSERT + `_SQL_RESTAR`), `_leer_orden` | OR test_crea_orden_devuelve_entidad_y_descuenta_stock, test_stock_en_cero_sigue_activo_y_no_hay_movimientos | OK |
| Alta: un solo componente | R idem | OR test_orden_con_un_solo_componente | OK |
| Número normalizado (`"  ot-0003 "` -> `OT-0003`) | OS:22-30 | OSV test_normaliza_numero_y_codigos_y_usa_el_reloj; API test_orden_creada_cuerpo_exacto | OK |
| Número duplicado (mensaje, stock intacto, una orden) | R `_SQL_ORDEN_EXISTE`; E:41-44 | OR test_numero_duplicado; API test_409_duplicado_sin_faltantes | OK |
| Número vacío / 31 caracteres | OS:22-30 (+ SC `numero` min/max) | OSV test_numero_invalido, test_numero_de_30_caracteres_se_acepta; API test_422_casos | OK |
| Fecha pasada aceptada | OS:33-36, F:10-17 | OSV test_fecha_pasada_y_futura_se_aceptan | OK |
| Fecha formato inválido (`20/11/2026`, `...T10:00`) | F:12-13 | FE test_rechaza_formato; OSV test_fecha_invalida; API test_422_casos | OK |
| Fecha inexistente (`2026-02-30`) | F:14-17 | FE test_rechaza_fecha_inexistente_con_su_mensaje; OSV test_fecha_invalida | OK (ver W-1 para vía HTTP con espacios) |
| Fecha faltante o vacía | OS:34-35; SC `fecha` min_length; V:64 | OSV test_fecha_invalida; API test_422_falta_fecha | partial (S-1: `null` por HTTP da "debe ser texto") |
| Componentes: lista vacía | OS:59-60; SC min_length; V:14 | OSV test_lista_vacia; API test_422_casos | OK |
| Componentes: 101 líneas (se cuentan antes de consolidar) | OS:61-62 (antes de `_validar_linea`) | OSV test_mas_de_100_lineas, test_100_lineas_se_aceptan; API test_422_casos | OK |
| Cantidad inválida en línea 2 (prefijo "Componente 2: ", stock intacto) | OS:39-47 | OSV test_cantidad_invalida_en_la_segunda_linea, test_validaciones_fallidas_no_escriben | OK |
| Código en minúsculas (`" a-01 "` -> `A-01`) | OS:45, N:9-16 | OSV test_normaliza_numero_y_codigos_y_usa_el_reloj | OK |
| Un producto inexistente (404, nada escrito) | R `_SQL_PRODUCTOS_POR_CODIGOS` (activo=1); E:47-55 | OR test_producto_inexistente; API test_404_inexistente_e_inactivo | OK |
| Varios inexistentes/inactivos (orden de aparición, C-99 sigue inactivo) | R ausentes en orden de `items`; E:50-54 | OR test_inexistente_e_inactivo_en_orden_de_aparicion | OK |
| Consolidación: producto repetido (3, stock 2) | OS:63-67 (tras normalizar) | OSV test_codigos_repetidos_se_suman | OK |
| Repetido que excede stock (solicitado 6) | OS:66 + R faltantes | OSV test_consolidado_excede_stock_informa_solicitado_total; API sondeo ("stock sol" 409 solicitado 6) | OK |
| Consolidado >10.000 con stock (12000 -> una línea, stock 0) | sin tope en OS:66 | OSV test_total_consolidado_sobre_10000_se_acepta_con_stock; sondeo HTTP 201 | OK |
| Consolidado >10.000 sin stock (disponible 11000, solicitado 12000) | idem + R | OSV test_total_consolidado_sobre_10000_sin_stock_es_409 | OK |
| Rechazo por stock: un componente / varios en orden de aparición | R `faltantes` iterando `items`; E:58-65 | OR test_un_faltante, test_varios_faltantes_en_orden_de_aparicion, test_stock_cero_cuenta_como_faltante; API test_409_stock_con_faltantes_exactos | OK |
| Prioridad: duplicado > stock; inexistente > stock | R orden de chequeos: existe -> productos -> stock | OR test_prioridad_duplicado_sobre_stock, test_prioridad_inexistente_sobre_stock, test_prioridad_duplicado_sobre_inexistente | OK |
| Atómico: falla durante la escritura (usuario inexistente) | R `_transaccion` + FK | OR test_usuario_inexistente_revierte_todo, test_fecha_naive_no_escribe | OK |
| Concurrencia: mismo stock | R BEGIN IMMEDIATE | OR ConcurrenciaTest test_stock_compartido_una_orden_gana | OK |
| Concurrencia: mismo número | R BEGIN IMMEDIATE + chequeo; respaldo IntegrityError R:336-340 | OR test_mismo_numero_una_orden_gana | OK (el respaldo `IntegrityError` no tiene test propio: S-2) |
| Sin filas en `movimientos` | R no inserta en `movimientos` | OR test_stock_en_cero_sigue_activo_y_no_hay_movimientos; API test_inventario_descontado_y_sin_movimientos | OK |

### api-http

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Orden creada: 201, cuerpo exacto, componentes consolidados y ordenados por código, inventario 3/5, sin movimientos | RT:23-38; SC `OrdenOut`/`orden_out`; R `_SQL_ITEMS_DE_ORDEN ... ORDER BY p.codigo` | API test_orden_creada_cuerpo_exacto, test_inventario_descontado_y_sin_movimientos | OK |
| Sin sesión: 401 sin cambios (también con cuerpo inválido) | `get_current_user` (dependencies:52-57) | API test_sin_sesion_401_sin_cambios, test_sin_sesion_con_cuerpo_invalido_sigue_siendo_401, test_tras_logout_vuelve_a_401 | OK |
| 409 stock: `detail` + `faltantes` exactos en orden de pedido | A `stock_insuficiente_orden`; E:58-65 | API test_409_stock_con_faltantes_exactos, test_409_un_faltante_sobre_producto_con_stock | OK |
| 409 duplicado sin `faltantes` | A `_responder(409)` para `OrdenDuplicada` | API test_409_duplicado_sin_faltantes | OK |
| 404 producto inexistente (e inactivo) | A `ProductosNoEncontrados` -> 404 | API test_404_inexistente_e_inactivo | OK |
| 422 componentes vacíos | V:14, SC min_length | API test_422_casos | OK |
| 422 cantidad `"5"` en línea 1 con prefijo | V:31-45 | API test_422_casos; EV | OK |
| 422 fecha `20/11/2026` | OS/F | API test_422_casos | OK |
| Docs: ocho endpoints | A include_router | API test_lista_los_ocho_endpoints | OK |
| Campo faltante en línea 2: "Componente 2: El campo codigo es obligatorio." | V:31-45 | EV (casos de `OrdenRequest`); API test_422_casos | OK |
| OpenAPI: 422 `ErrorOut` en los cinco endpoints; 409 de ordenes con `faltantes` opcional | RT:27-34; SC `StockInsuficienteOut` | API test_respuestas_documentadas_de_ordenes, test_422_de_otros_endpoints_siguen_con_error_out; sondeo `openapi.json` (201 OrdenOut, 404 ErrorOut, 409 StockInsuficienteOut, 422 ErrorOut) | OK |

## Coherencia con design.md

- Todo o nada en una sola `BEGIN IMMEDIATE`: `_transaccion` (R:190-206) abre, hace rollback ante `BaseException` y confirma al final; la lectura de la orden devuelta (`_leer_orden`) ocurre dentro de la transacción. OK.
- Prioridad 422 -> duplicado -> inexistente -> stock: validación en `OrdenService.crear` antes de tocar el repo; luego R:343-358 en ese orden. OK.
- UPDATE condicional con rowcount: `_SQL_RESTAR` con guarda de stock y `rowcount != 1` -> `StockInsuficienteOrden` (R:367-370), defensa en profundidad. OK.
- Sin filas en `movimientos`: confirmado en código y en tests. OK.
- `created_at` desde el reloj inyectado en `-03:00`: `_fecha_a_texto` valida zona (naive -> ValueError antes de abrir la transacción). OK (OR test_filas_persistidas_y_created_at_explicito).
- Número recortado/mayúsculas/1-30: OS:22-30 y, redundante, SC. OK.
- 1-100 líneas contadas antes de consolidar: OS:61-62. OK.
- Componentes ordenados por código en la respuesta: `ORDER BY p.codigo` (orden binario, correcto para códigos normalizados a mayúsculas). OK.
- `_transaccion` endurecida lanza `RuntimeError` si `conn.in_transaction`: ¿puede dispararse sin querer en producción? No. Cada request abre su propia conexión (`get_conexion`, dependencies:24-29), `get_current_user` solo lee la cookie de sesión (no toca la base), y `OrdenService.crear` no hace lecturas previas por esa conexión; además el `sqlite3` de Python no abre transacción implícita con un `SELECT`, solo con DML. Ningún camino de C-02 hace DML sin commit antes de llamar a `_transaccion` (los helpers de tests ahora confirman, tarea 1.1). Cubierto por test_transaccion_pendiente_lanza_runtimeerror y el test equivalente de `SqliteStockRepository`.
- Refactor de `fechas.py`/`validar_cantidad`: mismos mensajes; `test_movimientos_service`, `test_stock_service`, `test_api_movimientos` y `test_api_stock` verdes sin modificar. OK.

## Reglas duras

1. Dependencias/desacople: sin `fastapi` ni `pydantic` en `domain/`, `services/`, `repositories/` (grep vacío). `requirements*.txt` sin cambios. OK.
2. Sin secretos: grep sin hallazgos nuevos (solo `secrets.*` stdlib preexistente). OK.
3. Atomicidad + doble validación: transacción única; cantidades/fechas/obligatorios validados en Pydantic y en `OrdenService`. OK.
4. `unittest` sin pytest ni mocks de base: sin `pytest`; los `mock.patch` existentes son sobre `os.environ`/`dotenv` y `AuthService` (preexistentes de C-01/C-02), ninguno sobre repositorios; los tests de repo usan `:memory:` y archivo temporal real. OK.
5. Un paso a la vez: sin trabajo de C-04. OK.
6. Sin commits: git muestra todo sin commitear. OK.

## Revisión de las desviaciones del apply

Los grupos 3-6 escribieron todos los casos de triangulación de una vez; el RED real fue `ImportError`/404 y los casos de triangulación nunca fallaron individualmente. Juicio: desviación de proceso menor, no un defecto del producto. El resultado cubre cada escenario con tests de comportamiento (no hay aserciones triviales), los repos usan base real, y el sondeo adicional de este verify no encontró un solo caso que los tests no cubran de forma equivalente. Riesgo residual: no hay evidencia de que cada triangulación hubiera detectado un "Fake It". Mitigación: la implementación es general (consolidación por diccionario, faltantes por comprensión), sin valores hardcodeados. Se registra como observación de proceso (S-3), no como bloqueo.

## Hallazgos

### CRITICAL

Ninguno.

### WARNING

- **W-1 — Resuelto (2026-11-20).** `schemas.py` ya no recorta `fecha` (solo `numero` y `codigo`); `" 2026-11-20 "`, `"2026-11-20\n"` y `"\t2026-11-20"` dan 422 "La fecha debe tener formato AAAA-MM-DD.". Tests: `test_api_ordenes.RechazosTest.test_422_fecha_con_espacios_o_salto_de_linea`, `test_numero_y_codigo_con_espacios_se_recortan`; `test_errores_validacion.MensajeOrdenTest.test_fecha_con_espacios_o_salto_de_linea_no_se_recorta`, `test_numero_y_codigo_siguen_recortandose`; `test_api_movimientos` (`test_errores_de_filtro_en_espanol` con `desde`/`hasta` con espacio y `\n`, ya conformes). Hallazgo original:
  - **W-1 — La fecha con espacios o salto de línea se acepta por HTTP, pero el service la rechaza.** `inventario/api/schemas.py:104-108` (`OrdenRequest` con `str_strip_whitespace=True` y `fecha: str`) recorta antes de que `parsear_fecha` (`services/fechas.py:12`) vea el valor. Escenario: `POST /api/ordenes` con `"fecha": " 2026-11-20 "` (o `"2026-11-20\n"`) responde 201 (verificado en el sondeo), mientras que el spec exige formato `YYYY-MM-DD` estricto y `tests/test_fechas.py` fija que `2026-11-20\n` se rechaza. Es una inconsistencia entre la capa HTTP y el service (la doble validación de la regla 3 no coincide). Impacto bajo: el valor guardado es correcto (`2026-11-20`), pero el contrato real es más laxo que el documentado. Sugerido: `Field(..., min_length=1)` con `strip_whitespace=False` solo para `fecha`, o declarar el recorte en el spec.
- **W-2 — Resuelto (2026-11-20).** `get_current_user` carga el usuario de la base (`UsuarioRepository.obtener_por_id`); si no existe, limpia la sesión y responde 401 "No autenticado." en los seis endpoints protegidos (incluye C-02, `/api/me`, inventario y movimientos). Tests: `tests/test_api_sesion_inexistente.py` (`test_usuario_borrado_da_401_en_todos_los_endpoints_protegidos`, `test_usuario_recreado_con_otro_id_invalida_la_sesion_vieja`, `test_la_cookie_vieja_se_descarta_y_el_login_vuelve_a_funcionar`, `test_sesion_valida_antes_de_borrar_al_usuario`); `test_sqlite_repositories.test_obtener_por_id`, `test_obtener_por_id_inexistente_devuelve_none`. Hallazgo original:
  - **W-2 — `usuario_id` inexistente por la API devuelve 500 sin cuerpo en español.** `repositories/sqlite_repo.py:336-340` re-lanza cualquier `IntegrityError` que no sea de `ordenes.numero`; no hay handler en `api/app.py`. Escenario: la cookie de sesión de un usuario que fue borrado de la base (`usuarios`) crea una orden con FK inválida -> `sqlite3.IntegrityError` -> 500 genérico. Es el mismo comportamiento que ya existe en C-02 para stock (el spec lo usa como caso de prueba de atomicidad, así que revertir es lo correcto); lo que falta es un manejo legible. Poco probable hoy (no hay baja de usuarios), pero la sesión firmada sobrevive a un reseteo de base. No bloquea.

### SUGGESTION

- **S-1 — Resuelto (2026-11-20).** `null` en `fecha`, `numero`, `componentes`, `codigo`, `username`, `password` da "El campo X es obligatorio."; `nombre: null` sigue válido; `cantidad: null` conserva el mensaje de cantidad (C-02). Tests: `test_errores_validacion.MensajeOrdenTest.test_null_en_campos_obligatorios_de_la_orden`, `MensajeValidacionTest.test_null_en_campo_de_texto_obligatorio_es_obligatorio`, `test_nombre_null_es_valido_como_no_enviado`; `test_api_ordenes.RechazosTest.test_422_null_en_numero_y_fecha`; `test_api_auth` (casos `null`), `test_api_stock.test_codigo_faltante_o_vacio`. Hallazgo original:
  - **S-1 — `fecha: null` por HTTP responde "El campo fecha debe ser texto."** (`api/errores_validacion.py:69-70`) en lugar de "El campo fecha es obligatorio." que el spec "Fecha faltante" asigna a "sin fecha". El caso sin la clave y el de `""` sí dan "obligatorio" (el service también maneja `None` bien: OS:34). Lo mismo para `numero: null` ("debe ser texto" vs obligatorio). Ajustar el mapeo de `string_type` con `input is None` a "obligatorio".
- **S-2 — Resuelto (2026-11-20).** `test_sqlite_orden_repository.RespaldoUniqueNumeroTest` (`test_unique_de_numero_se_traduce_a_orden_duplicada`, `test_otro_numero_no_dispara_el_respaldo`, `test_otro_integrity_error_se_propaga_sin_traducir`), con SQLite real; verificado por mutación. Hallazgo original:
  - **S-2 — El respaldo `IntegrityError` -> `OrdenDuplicada` (R:336-340) no tiene test.** Con `BEGIN IMMEDIATE` y el chequeo previo es inalcanzable en la práctica, así que es código defensivo sin cobertura. Un test que fuerce la carrera (por ejemplo, insertando una orden con el mismo número fuera de `_transaccion` entre el chequeo y el alta) o la eliminación del respaldo lo dejaría consistente con el design.
- **S-3 — Proceso TDD del apply (grupos 3-6).** Ver "Revisión de las desviaciones". Para próximos changes, escribir el primer caso, verlo en verde y recién después agregar el segundo, y registrar el RED de cada triangulación.
- **S-4 — Cambio en `knowledge-base/03_actores_y_roles.md` sin mención en tasks.** `git status` lo muestra modificado; no es parte del alcance declarado de C-03. Confirmar que es un ajuste intencional (p. ej. ruta pública/privada `/api/ordenes`) antes de archivar. Además queda pendiente del follow-up de tasks: marcar C-03 en `CHANGES.md`, actualizar PA-06 en `10_preguntas_abiertas.md` y el tipo de `ordenes.numero` en `04_modelo_de_datos.md`.

## Otros chequeos de casos borde (sondeo con TestClient)

| Caso | Resultado |
|---|---|
| `componentes: null` / `{}` / `"x"` | 422 "El campo componentes debe ser una lista." |
| línea que no es objeto (`["x"]`) | 422 "Componente 1: debe ser un objeto con codigo y cantidad." |
| 101 líneas (incluso con la primera inválida) | 422 "La orden admite hasta 100 componentes." (el tope se evalúa primero) |
| cantidad `true` / `1.0` | 422 con el mensaje de cantidad y prefijo de línea |
| campos extra en el cuerpo | ignorados, 201 |
| producto inactivo (`C-99`) | 404 "No existe un producto activo con código 'C-99'." |
| `z` x 6000 + ` Z ` x 6000, stock 20000 | 201, una línea `Z` x 12000 |
| `a-01` x 3 + `A-01` x 3, stock 3 | 409, `solicitado: 6` (cantidad consolidada) |
| número de 30 con espacios alrededor | 201 (recorte antes de medir) |
| número de 31 | 422 "El campo numero admite hasta 30 caracteres." |
| cuerpo `[1]` / JSON roto | 422 con los mensajes de C-02 |
| fecha `null` / entero | 422 "El campo fecha es obligatorio." (`null`, corregido S-1) / "debe ser texto." (entero) |
| fecha con espacios | 422 formato (corregido W-1) |

## 7.2 /docs

**Resultado: OK** (2026-11-20, orquestador, Playwright).

- Entorno: `uvicorn inventario.api.main:app --port 8766` con base temporal nueva fuera del repo y credenciales de prueba por entorno (no se leyó `.env`). Servidor y navegador cerrados al terminar.
- Swagger lista `POST /api/ordenes` junto a los 7 endpoints previos.
- Desde la UI de Swagger ("Try it out" → "Execute"): login 200 y orden `"  ot-0001 "` con líneas `b-02`×2, `A-01`×3, `" a-01"`×1 → **201** `OT-0001`, `A-01` consolidado en 4, componentes ordenados por código, `usuario: admin`.
- Desde la misma página (misma cookie), 28 casos, todos conformes a spec: duplicado `ot-0001` 409; inexistentes + faltante → 404 con `'X-00', 'Y-99'` (prioridad respetada); faltante de 2 componentes → 409 con `detail` y `faltantes` en orden del pedido, inventario sin cambios; decisión 4: 6000+6000 con stock 11000 → 409 (solicitado 12000) y con stock 12000 → 201, stock 0; 422 con mensajes en español para línea 10001 y cantidad 0 ("Componente 2: …"), código vacío, 0 y 101 líneas, componentes no lista, número vacío y de 31, fecha con formato malo e inexistente, fecha null, JSON inválido; fechas 2030 y 2001 → 201; logout 204; sin sesión → 401 (también con cuerpo inválido).
- SQL: 4 órdenes con `created_at` ISO `-03:00`; `orden_items` consolidados (1 fila por producto); `movimientos` solo tiene los 5 ingresos de siembra (ninguno de órdenes, RN-ST-06).
- Consola del navegador: solo los 19 "Failed to load resource" de las respuestas 4xx provocadas.
- S-4: el cambio en `knowledge-base/03_actores_y_roles.md` es intencional (decisión del usuario del 2026-11-20: solo `admin` opera, sin roles).
