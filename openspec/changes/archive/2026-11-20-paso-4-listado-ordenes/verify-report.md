# Verify Report — paso-4-listado-ordenes (C-04)

Fecha: 2026-11-20

## Veredicto: PASS (con la tarea 5.4 pendiente del orquestador)

0 CRITICAL, 0 WARNING, 3 SUGGESTION. Ningún hallazgo bloquea el archivado; solo falta cerrar la verificación manual 5.4.

## Resultados de ejecución

- `.venv/Scripts/python -m unittest discover -s tests -t .` -> `Ran 342 tests in 87.862s — OK` (tras los ajustes post-verify: `Ran 348 tests — OK`) (la línea "Seed del admin omitido por IntegrityError" es salida esperada).
- `openspec validate paso-4-listado-ordenes --strict` -> `Change 'paso-4-listado-ordenes' is valid`.
- Sondeo adicional con `TestClient` (sin puertos, base temporal): 9 casos borde HTTP (ver "Otros chequeos").

## Completitud

tasks.md: 33 tareas, 32 `[x]`, 1 `[ ]` (5.4, manual, del orquestador). Cada `[x]` tiene código/test correspondiente. `requirements*.txt` sin cambios en git. Sin archivos nuevos fuera de `inventario/`, `tests/`, `CHANGES.md` y el change.

## Correctitud — trazabilidad

Código: F=`services/fechas.py`, OS=`services/orden_service.py`, R=`repositories/sqlite_repo.py`, RT=`api/routers/ordenes.py`, A=`api/app.py`, E=`domain/errors.py`.
Tests: OR=`test_sqlite_orden_repository`, OSV=`test_orden_service`, API=`test_api_ordenes`, FE=`test_fechas`, SES=`test_api_sesion_inexistente`.

### consulta-ordenes

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Orden por fecha / misma fecha / fecha de la orden y no de carga | R:`_ORDEN_LISTAR_ORDENES` (`o.fecha DESC, o.id DESC, p.codigo`) | OR test_sin_filtros_devuelve_ordenes_de_la_mas_nueva_a_la_mas_vieja, test_desempata_por_id_descendente_y_ordena_por_fecha_no_por_created_at | OK |
| Sin órdenes -> lista vacía | R `listar`, OS:124-133 | OR test_sin_ordenes_devuelve_lista_vacia; OSV test_sin_argumentos_... | OK |
| Datos de cada orden (id, número, fecha, usuario, componentes por código) | R `_SQL_LISTAR_ORDENES` + `_a_ordenes` | OR test_componentes_ordenados_por_codigo_con_nombre_y_cantidad; API test_listado_cuerpo_exacto_con_el_mismo_id_del_alta | OK |
| Producto inactivo sigue visible | R: JOIN sin filtro de `activo` | OR test_producto_dado_de_baja_sigue_en_los_componentes; API test_producto_dado_de_baja_sigue_en_la_orden_pero_no_en_inventario | OK |
| Rango inclusivo, un día, solo desde, solo hasta, sin resultados | R `listar` (`>=`, `<=` sobre ISO, parametrizado) | OR test_rango_inclusivo_en_ambos_bordes, test_rangos_abiertos_y_rango_sin_resultados; OSV test_fechas_vacias_son_sin_filtro_y_solo_desde_o_solo_hasta_filtran | OK |
| Fecha formato inválido / inexistente / rango invertido (mensajes de C-02) | F:20-36 (`parsear_filtro_fecha`, `validar_rango`) | FE; OSV test_mensajes_de_fecha_identicos_a_movimientos; API test_422_con_detalle_exacto | OK |
| Fechas vacías = sin filtro | F:22-23 | OSV test_fechas_vacias_...; API test_parametros_vacios_equivalen_a_sin_filtro | OK |
| Número existente / minúsculas y espacios / coincidencia exacta | OS:69-73 + R `o.numero = ?` | OSV test_numero_se_normaliza_y_vacio_es_sin_filtro; OR test_numero_exacto_..., test_numero_no_es_prefijo_ni_parcial | OK |
| Número inexistente -> mensaje con número normalizado | OS:131-132; E:47-50 | OSV test_numero_inexistente_lanza_no_encontrada_con_numero_normalizado | OK |
| Número existente fuera de rango -> `[]`, sin 404 | OS:131 (`existe_numero`) | OSV test_numero_existente_fuera_del_rango_devuelve_lista_vacia; OR test_numero_se_combina_con_fechas_por_and, test_existe_numero_es_exacto | OK |
| Número existente dentro del rango | R | OR test_numero_se_combina_con_fechas_por_and | OK |
| Número vacío nunca es no encontrado | OS:69-73 | OSV test_numero_en_blanco_sin_ordenes_es_lista_vacia | OK |
| Prioridad validación > no encontrado | OS:125-129 antes de la lectura | OSV test_fecha_invalida_tiene_prioridad_sobre_no_encontrada, test_prioridad_de_errores_numero_luego_desde_luego_hasta | OK |
| Número de 31 caracteres | OS:64-65 | OSV test_numero_de_31_caracteres_es_invalido | OK |

### api-http

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Listado sin filtros: cuerpo exacto, mismo id que el alta | RT:174-189; `orden_out` | API test_listado_cuerpo_exacto_con_el_mismo_id_del_alta | OK |
| Filtros combinados / rango abierto | RT, OS | API test_filtros_combinados_y_rango_abierto | OK |
| Parámetros vacíos | OS:69-73, F:22 | API test_parametros_vacios_equivalen_a_sin_filtro | OK |
| Componente dado de baja (y fuera de `/api/inventario`) | R | API test_producto_dado_de_baja_sigue_en_la_orden_pero_no_en_inventario | OK |
| 404 número inexistente | A:111 (`OrdenNoEncontrada`, 404) | API test_numero_inexistente_es_404_con_mensaje | OK |
| Existente fuera de rango -> 200 `[]`; sin órdenes -> `[]` | OS | API test_numero_existente_fuera_del_rango_es_200_vacio, test_sin_ordenes_devuelve_lista_vacia | OK |
| 422: formato, inexistente, invertido, número largo | OS/F -> handler `DatosInvalidos` | API test_422_con_detalle_exacto | OK |
| 422 tiene prioridad sobre 404 | OS | API test_422_tiene_prioridad_sobre_404 | OK |
| Sin sesión -> 401 | `get_current_user` | API test_tras_logout_el_listado_da_401 | OK |
| Docs: ocho endpoints, GET y POST en `/api/ordenes` | RT | API test_lista_los_ocho_endpoints, test_respuestas_documentadas_de_ordenes | OK |
| OpenAPI: 422 y 404 del GET con `ErrorOut`; 409 del POST intacto | RT:174-181 | API test_get_documenta_lista_404_y_422, test_422_de_otros_endpoints_siguen_con_error_out | OK |
| Sesión de usuario inexistente en `GET /api/ordenes` | `get_current_user` | SES (incluye el GET) | OK |

## Coherencia con design.md

- SQL parametrizado: `listar` arma solo fragmentos fijos (`o.numero = ?`, `o.fecha >= ?`, `o.fecha <= ?`) unidos con AND; los valores van en `parametros`. Sin concatenación de entrada de usuario.
- Orden y desempate: `ORDER BY o.fecha DESC, o.id DESC, p.codigo`; `fecha` es `YYYY-MM-DD`, así que el orden lexicográfico es el cronológico.
- `groupby` sobre `f["id"]`: las filas de una orden son contiguas porque `o.id` sigue a la fecha en el ORDER BY; dos órdenes con igual fecha tienen `id` distinto y no se mezclan (test_desempata_por_id...).
- LEFT JOIN: una orden sin ítems es posible a nivel de esquema (el alta exige >= 1 pero no hay constraint); `_a_ordenes` filtra `codigo is not None` y devuelve `componentes: []`. Confirmado con sondeo HTTP (S-1: sin test automatizado).
- `existe_numero` solo se invoca con resultado vacío y `numero` presente (OS:131). Sin test espía (S-2).
- Un solo SELECT con JOINs; `_leer_orden` reutiliza `_SQL_LISTAR_ORDENES` + `WHERE o.id = ?` y `_a_ordenes(...)[0]`. Test OR test_listar_ejecuta_un_solo_select.
- Refactor C-02: `MovimientosService` usa `parsear_filtro_fecha` y `validar_rango` con los mismos mensajes (texto original en el rango invertido); tests de movimientos y de fechas verdes.
- Respuesta del alta C-03 sin cambios: `crear` devuelve `_leer_orden(...)` y los tests del alta siguen en verde.

## Reglas duras

1. Dependencias/desacople: sin imports de `fastapi`/`pydantic` en `domain/`, `services/`, `repositories/` (grep vacío); `requirements*.txt` sin cambios. OK.
2. Sin secretos en código. OK.
3. Validación de fechas y número en backend; consulta de solo lectura (sin atomicidad requerida). OK.
4. Solo `unittest`; sin pytest ni mocks de base (SQLite real en memoria). OK.
5. Un paso a la vez: solo C-04. OK.
6. Sin commits. OK.

## Revisión de las desviaciones del apply

- Triangulaciones sin RED previo: aceptable. Son casos de combinación (rango abierto, número+fechas) sobre una implementación ya genérica y parametrizada; los tests ejercen comportamiento real, no son tautologías. Riesgo bajo.
- Test N+1 sin mutación: verificado mentalmente. `test_listar_ejecuta_un_solo_select` siembra 3 órdenes y exige `len(sentencias) == 1` con `set_trace_callback`; una implementación con una consulta por orden produciría 1 + 3 sentencias y fallaría.

## Hallazgos

### CRITICAL
Ninguno.

### WARNING
Ninguno.

### SUGGESTION

- S-1: la rama de orden sin ítems (`f["codigo"] is not None` en `inventario/repositories/sqlite_repo.py` `_a_ordenes`, LEFT JOIN en `_SQL_LISTAR_ORDENES`) no tiene test automatizado; solo el sondeo manual. Agregar un test de repositorio que inserte una orden sin `orden_items` y verifique `items == ()`. **Resuelto (2026-11-20)**: `ListarTest.test_orden_sin_items_aparece_con_componentes_vacios`, `test_orden_sin_items_convive_con_ordenes_normales_agrupadas_y_ordenadas`, `test_orden_con_todos_los_productos_dados_de_baja_sigue_listada_con_sus_items` (`tests/test_sqlite_orden_repository.py`). Mutación `if True` en el guard: 2 tests fallan.
- S-2: ningún test fija que `existe_numero` NO se llama cuando hay resultados o no hay `numero` (`inventario/services/orden_service.py:131`). Un repositorio espía en OSV lo cubriría. **Resuelto (2026-11-20)**: `ListarServiceTest.test_existe_numero_no_se_consulta_sin_numero`, `test_existe_numero_no_se_consulta_si_el_filtro_devuelve_resultados`, `test_existe_numero_se_consulta_solo_con_numero_y_resultado_vacio` (`tests/test_orden_service.py`; subclase espía del `SqliteOrdenRepository` real sobre `:memory:`). Mutación (llamar siempre a `existe_numero`): los tests nuevos fallan.
- S-3: `listar` y `existe_numero` no comparten transacción; una orden creada entre ambas podría dar un 404 transitorio. Irrelevante en la práctica; informativo.

## Otros chequeos de casos borde (sondeo con TestClient)

| Caso | Resultado |
|---|---|
| `?hasta=2026-02-30&desde=19/11/2026` | 422 con el mensaje de `desde` (se valida `desde` primero) |
| `?numero=OT-9&desde=19/11/2026` (sin OT-9) | 422, no 404 |
| `?numero=%20%20` | 200, sin filtro |
| `?numero=` + 31 `a` | 422 "El campo numero admite hasta 30 caracteres." |
| `?numero=` espacio + 30 `a` + espacio, inexistente | 404 con número normalizado en mayúsculas (recorte antes del límite) |
| `?desde=2026-01-01&desde=zzz` (repetido) | toma el último valor -> 422 de formato |
| `?desde=%202026-01-01` (con espacio) | 422 de formato (igual que C-02) |
| `?desde=0001-01-01&hasta=9999-12-31` | 200 con todas las órdenes |
| Orden sin ítems | 200, `componentes: []` |
| Lista grande | sin tope ni paginación, según decisión 8 |

## 5.4 /docs

**Resultado: OK** (2026-11-20, orquestador, Playwright).

- Entorno: `uvicorn inventario.api.main:app --port 8767` con base temporal nueva fuera del repo y credenciales de prueba por entorno (no se leyó `.env`). Servidor y navegador cerrados al terminar.
- Siembra: 3 productos y 4 órdenes (`OT-1` 2026-11-01, `OT-10` y `OT-2` 2026-11-15, `OT-3` 2026-11-30).
- Desde la UI de Swagger ("Try it out" → "Execute"): login 200 y `GET /api/ordenes?numero=ot-1` → 200 con **solo** `OT-1` (no `OT-10`), componentes por código.
- Desde la misma página (misma cookie), 18 casos conformes a spec: orden `OT-3, OT-2, OT-10, OT-1` (fecha DESC, id DESC); vacíos = sin filtro; rango inclusivo, un día, solo `desde`, solo `hasta`, rango sin órdenes → `[]`; número en minúsculas con espacios encontrado; número inexistente → 404 "No existe una orden con número 'OT-9'."; existente fuera de rango → `[]`; dentro de rango → la orden; 31 caracteres → 422; los 3 mensajes de fecha idénticos a C-02; 422 gana sobre 404; sin sesión → 401.
- Producto dado de baja (`UPDATE productos SET activo=0` sobre `C-03`, C-05 aún no existe): desaparece de `/api/inventario` y sigue en `OT-10` con su nombre (RN-PR-04).
- OpenAPI de `GET /api/ordenes`: parámetros `numero`, `desde`, `hasta`; respuestas 200 (lista de `OrdenOut`), 404 y 422 con `ErrorOut`.
- Consola del navegador: solo los 8 "Failed to load resource" de las respuestas 4xx provocadas.
