# Verify Report — paso-4b-borrado-ordenes-productos (C-05)

Fecha: 2026-11-20

## Veredicto: PASS (con la tarea 7.5 pendiente del orquestador)

0 CRITICAL, 0 WARNING, 4 SUGGESTION. Ningún hallazgo bloquea el archivado. Governance HIGH: el borrado es una única operación atómica, la búsqueda por número ocurre dentro del lock y no se encontró ningún camino con estado parcial.

## Resultados de ejecución

- `.venv/Scripts/python -m unittest discover -s tests -t .` -> `Ran 416 tests in 110.659s — OK`.
- `openspec validate paso-4b-borrado-ordenes-productos --strict` -> `Change 'paso-4b-borrado-ordenes-productos' is valid`.
- Sondeo adicional con `TestClient` (sin puertos, base temporal), ver "Otros chequeos".
- Mutación D re-ejecutada (ver "Deviaciones del apply").

## Completitud

tasks.md: 45 tareas, 44 `[x]`, 1 `[ ]` (7.5, manual, del orquestador). Cada `[x]` tiene código o test correspondiente. `requirements*.txt` sin cambios en git. Archivos nuevos: `api/routers/productos.py`, `services/producto_service.py` y tres archivos de tests; el resto son ediciones.

## Correctitud — trazabilidad

Código: R=`repositories/sqlite_repo.py`, OS=`services/orden_service.py`, PS=`services/producto_service.py`, RT=`api/routers/ordenes.py`, RP=`api/routers/productos.py`, S=`api/schemas.py`, E=`domain/entities.py`, A=`api/app.py`.
Tests: OR=`test_sqlite_orden_repository` (clases `Borrar*`), OSV=`test_orden_service` (`BorrarServiceTest`), API=`test_api_ordenes`, PR=`test_sqlite_producto_repository`, PSV=`test_producto_service`, APP=`test_api_productos`, SES=`test_api_sesion_inexistente`, D=`test_domain`.

### ordenes-trabajo

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Decisión ausente / vacía / valor no admitido (422 "obligatorio" / "debe ser true o false") | OS `_parsear_reintegrar`; RT query obligatoria; handler 422 | OSV test_reintegrar_faltante_o_vacio, test_reintegrar_distinto_de_true_false_exactos; API test_reintegrar_ausente_o_vacio, test_reintegrar_invalido | OK |
| Reintegro de varios componentes / otras órdenes intactas | R `borrar`/`_reintegrar` | OR test_devuelve_stock_y_detalla_los_reintegros, test_reintegros_ordenados_por_codigo, test_aislamiento_solo_devuelve_lo_de_la_orden_borrada | OK |
| Reactivación por reintegro / sin reintegro no reactiva | R `_SQL_SUMAR_Y_ACTIVAR` solo si `reintegrar` | OR test_reactiva_producto_dado_de_baja, test_sin_reintegro_no_reactiva | OK |
| Borrado sin devolver stock | R `borrar` (`()` sin reintegro) | OR test_borra_orden_y_lineas_sin_tocar_stock; API test_sin_reintegro | OK |
| Número normalizado / con barra / en blanco / demasiado largo | OS `_normalizar_numero` antes del repo | OSV test_numero_se_normaliza, test_numero_en_blanco_o_nulo, test_numero_largo_y_limite; OR test_numero_con_barras_borra_solo_esa; API test_numero_normalizado, test_numero_con_barras, test_numero_en_blanco_y_largo | OK |
| Número inexistente / validación antes que existencia / orden ya borrada | R `OrdenNoEncontrada`; OS orden de validación | OSV test_numero_inexistente_normalizado, test_error_de_reintegrar_gana_sobre_el_de_numero; OR test_inexistente_con_y_sin_reintegro, test_segundo_borrado_del_mismo_numero_no_reintegra_otra_vez; API test_inexistente_y_prioridad_422_sobre_404, test_segundo_borrado_da_404_y_no_reintegra_otra_vez | OK |
| Atomicidad: falla a mitad del reintegro / al borrar | R `_transaccion` | OR test_falla_a_mitad_del_reintegro_revierte_todo, test_falla_al_borrar_revierte_reintegro_y_reactivacion (triggers reales) | OK |
| Producto de una línea ausente (aborta, 500) | R `_reintegrar` `RuntimeError` | OR test_linea_huerfana_aborta_el_reintegro (con y sin reintegro) | OK |
| Borrados simultáneos (uno gana, stock sumado una vez) | R `BEGIN IMMEDIATE` + búsqueda dentro | OR test_dos_borrados_simultaneos_de_la_misma_orden_solo_uno_gana | OK |
| Sin movimientos | R no escribe en `movimientos` | OR test_no_escribe_movimientos; API test_con_reintegro_cuerpo_exacto_y_efectos | OK |
| Resultado con y sin reintegro | E `Reintegro`, `ResultadoBorradoOrden` | D test_reintegro_es_inmutable_y_expone_campos, test_resultado_borrado_es_inmutable_y_expone_campos; OR | OK |

### baja-productos

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Baja con stock / stock cero / código normalizado | R `dar_de_baja`; PS `normalizar_codigo` | PR test_baja_conserva_stock_y_nombre, test_stock_cero_queda_inactivo_con_cero; PSV test_normaliza_y_da_de_baja | OK |
| Fuera del inventario / no seleccionable en orden / egreso rechazado / órdenes históricas intactas | R (`activo=0`; JOIN de órdenes sin filtro) | PR test_egreso_rechazado, test_alta_de_orden_rechazada, test_orden_previa_sigue_mostrando_el_componente; APP test_orden_previa_egreso_alta_y_reingreso | OK |
| Historial conservado (sin movimientos) | R | PR test_no_toca_movimientos; APP test_no_escribe_movimientos, test_movimientos_previos_siguen_consultables | OK |
| Baja y reingreso suma al stock conservado | `_SQL_SUMAR_Y_ACTIVAR` (C-02) | PR test_ingreso_reactiva_y_suma_al_stock_conservado; APP test_reingreso_suma_al_stock_conservado | OK |
| Inexistente / ya dado de baja / código largo | R `rowcount != 1`; PS | PR test_inexistente, test_ya_inactivo_no_cambia_nada, test_segunda_baja_seguida_falla; PSV test_codigo_vacio_o_en_blanco, test_codigo_largo | OK |
| Doble baja simultánea | R `AND activo = 1` + `BEGIN IMMEDIATE` | PR test_dos_bajas_simultaneas_solo_una_gana | OK |

### api-http

| Requisito / escenario | Código | Test | Estado |
|---|---|---|---|
| Borrado con reintegro (cuerpo exacto `{orden, reintegrado, reintegros[{codigo,nombre,cantidad,stock,reactivado}]}`) | RT `borrar_orden`; S `BorradoOrdenOut`, `borrado_orden_out` | API test_con_reintegro_cuerpo_exacto_y_efectos | OK |
| Sin reintegro (`reintegros: []`) / sin movimientos | RT | API test_sin_reintegro, test_con_reintegro_cuerpo_exacto_y_efectos | OK |
| Reintegrar ausente / vacío / inválido (422, textos exactos) | RT query `str` obligatoria + handler; OS | API test_reintegrar_ausente_o_vacio, test_reintegrar_invalido | OK |
| Número normalizado / con barra (`path`) / con `?` `#` codificados / en blanco / largo | RT `{numero:path}` | API test_numero_normalizado, test_numero_con_barras, test_numero_con_signos_codificados, test_numero_en_blanco_y_largo | OK |
| 404 orden inexistente / segundo borrado | A (`OrdenNoEncontrada`) | API test_inexistente_y_prioridad_422_sobre_404, test_segundo_borrado_da_404_y_no_reintegra_otra_vez | OK |
| Sin sesión 401 (también con validación inválida) | `get_current_user` | API test_sin_sesion_401_y_la_orden_sigue, test_sin_sesion_gana_sobre_la_validacion | OK |
| Baja exitosa (`ProductoOut`) / código con barra / efectos cruzados / reingreso | RP `dar_de_baja`; `producto_out` | APP test_baja_normalizada_cuerpo_exacto, test_codigo_con_barra, test_orden_previa_egreso_alta_y_reingreso, test_reingreso_suma_al_stock_conservado | OK |
| Baja: inexistente / ya baja / código en blanco o largo (404, 422) | PS, A | APP test_inexistente, test_segunda_baja, test_codigo_en_blanco_y_largo | OK |
| Baja sin sesión (401) | `get_current_user` | APP test_sin_sesion_401_y_el_producto_sigue_activo, test_tras_logout_vuelve_a_401 | OK |
| Docs: diez rutas, DELETE documentado | RT/RP `responses` | API test_lista_las_diez_rutas, test_delete_de_orden_documenta_parametros_y_respuestas, test_delete_de_producto_documenta_respuestas | OK |
| Sesión de usuario inexistente en ambos DELETE | `get_current_user` | SES (incluye ambos DELETE); API BorradosConSesionInexistenteTest | OK |
| OpenAPI del 422 (`ErrorOut`) | RT/RP | API tests de documentación (422 y 404 con `ErrorOut`; `reintegrar` con `enum ["true","false"]`) | OK |

Todos los escenarios con estado OK; 0 partial, 0 missing.

## Revisión de seguridad de datos (R1–R10)

| # | Riesgo | Verificación en el código | Estado |
|---|---|---|---|
| R1 | Pérdida irreversible | La respuesta lleva `orden` completa (id, número, fecha, usuario, componentes) y `reintegros`; `reintegrar` obligatorio sin default (RT query, OS:116). Probado con el cuerpo exacto. | OK |
| R2 | Reintegro parcial | `borrar` corre todo dentro de un único `with _transaccion` (R:445-455): búsqueda, reintegro, DELETE de ítems y de orden. `_transaccion` hace `BEGIN IMMEDIATE` y rollback ante `BaseException`. Cada `UPDATE` de reintegro exige `rowcount == 1` (R:463-465) y el `DELETE` de la orden también (R:453). Tests con triggers reales en ambos puntos y `in_transaction == False`. | OK |
| R3 | Doble reintegro / TOCTOU | `_buscar_orden_por_numero` se llama después de `BEGIN IMMEDIATE` y dentro del `with` (R:446-447). El segundo borrado no encuentra el número -> 404. Test con dos conexiones e hilos. | OK |
| R4 | Reuso de id | No aplica: borrado por número. Se usa el `orden.id` leído dentro del lock para ítems y orden (R:451-452). | OK |
| R5 | `reintegrar=false` por error | Sin reintegro no se toca `productos` (`reintegros = ()`); respuesta con `reintegrado: false` y componentes. Probado (stock y `activo` intactos, incluso con producto inactivo). | OK |
| R6 | Reactivación | `_SQL_SUMAR_Y_ACTIVAR` solo se ejecuta con `reintegrar=True`; `reactivado = not activo` por producto. Probado con producto en baja. | OK |
| R7 | Stock inflado | Decisión del usuario por borrado; sin lógica extra. | OK |
| R8 | Línea huérfana | `LEFT JOIN` + `linea["id"] is None` -> `RuntimeError` (R:461-462) dentro de la transacción: rollback y 500. Test con `PRAGMA foreign_keys = OFF`. Sin reintegro la orden se puede borrar. | OK |
| R9 | Base bloqueada | Timeout por defecto de sqlite3 y rollback; sin cambios de configuración. | OK |
| R10 | Baja con stock > 0 | `UPDATE productos SET activo = 0 WHERE codigo = ? AND activo = 1` (R:191) con `rowcount != 1` -> `ProductoNoEncontrado`; no toca `stock`; no escribe `movimientos` (test). | OK |

Chequeos adicionales:

- SQL parametrizado: todo valor entra por `?`. La única concatenación es `_SQL_LISTAR_ORDENES + " WHERE o.numero = ?"` (constantes). Sin f-strings con datos del usuario en SQL.
- Los ítems se borran explícitamente antes que la orden (R:451-452); el `ON DELETE CASCADE` queda como respaldo.
- Normalización (recorte + MAYÚSCULAS, número y código) ocurre en el service antes de llamar al repo (OS:117, PS).
- Ninguna otra ruta llama a `_transaccion` con una transacción pendiente: cada request usa su propia conexión (`get_conexion`) y `_transaccion` lanza `RuntimeError` si ya hay una. `borrar` no invoca otro método transaccional.
- Rutas: ambos son solo DELETE. `GET /api/ordenes` y `POST /api/ordenes` (path vacío) no coinciden con `/{numero:path}`; sondeo: GET 200 `[]`, POST 422 de validación. `PUT /api/ordenes/OT-2` -> 405 sin efecto. Las demás rutas de `/api/` tienen otros prefijos. `x/../A-01`: el cliente (httpx) normaliza el `..` antes de enviar; en el servidor es solo texto que nunca se usa como ruta de archivo.

### Otros chequeos (sondeo con TestClient)

| Caso | Resultado |
|---|---|
| `OT%2F1` (barra codificada) | 200, borra `OT/1` |
| Solo espacios `%20%20` | 422 "El campo numero es obligatorio." |
| Path de 5000 caracteres | 422 "El campo numero admite hasta 30 caracteres." |
| `/api/ordenes/?reintegrar=true` | 422 "El campo numero es obligatorio." |
| Sin `reintegrar` / `TRUE` | 422 "El campo reintegrar es obligatorio." / "El campo reintegrar debe ser true o false." |
| `reintegrar=true&reintegrar=false` | 200 al verificar; corregido (2026-11-20): ahora 422 "El campo reintegrar debe enviarse una sola vez." (SUGGESTION 2) |
| Orden con producto en baja, `reintegrar=true` | 200, `reactivado: true`, `stock` = stock previo + cantidad (4), `activo=1`, 0 movimientos, 0 ítems |
| Orden con producto en baja, `reintegrar=false` | 200, stock y `activo` sin cambios |
| Mismo borrado dos veces | segundo 404, stock sin cambios |
| Sesión caducada en ambos DELETE | 401 "No autenticado." |

## Regresiones

C-02, C-03 y C-04 sin cambios de comportamiento: la suite completa (416 tests al verificar; 419 tras el ajuste post-verify) pasa. Los cambios en tests existentes son el conteo de rutas (8 a 10) y adiciones. Tras dar de baja un producto: el inventario lo oculta, el egreso da 404, la orden nueva con él da 404, el listado de órdenes lo sigue mostrando y un ingreso lo reactiva conservando el stock (cubierto por `test_api_productos` y `test_sqlite_producto_repository`).

## Reglas duras

| Regla | Resultado |
|---|---|
| 1. Sin FastAPI/pydantic en `domain/`, `services/`, `repositories/`; sin dependencias nuevas | OK: grep sin coincidencias; `requirements*.txt` sin cambios |
| 2. Sin secretos | OK |
| 3. Atomicidad + doble validación | OK en backend (el frontend llega en C-06) |
| 4. `unittest`, sin pytest, sin mock de base | OK: `unittest.mock` solo parchea `os.environ` y `dotenv` en tests preexistentes; la atomicidad se prueba con triggers y SQLite real |
| 5. Un paso a la vez | OK |
| 6. Commits a pedido | OK: no se hicieron commits |

## Deviaciones del apply

- **Triangulación no incremental**: aceptable. La evidencia final cubre al menos dos casos por comportamiento (con/sin reintegro, activo/inactivo, existente/inexistente).
- **Test débil reforzado**: aceptado.
- **Mutaciones**: A (sin transacción -> 12 tests fallan) y D (sin `AND activo=1` -> 8 tests fallan) son detectadas. B y C son guardas de línea huérfana superpuestas: cada una queda cubierta por la otra, lo esperable y no un hueco. Re-ejecuté D: quitar `AND activo = 1` de `_SQL_BAJA_PRODUCTO` hizo fallar 9 de los 27 tests de baja; restauré el archivo desde copia (`cmp` idéntico, `grep` confirma la línea original en R:191) y los 27 tests vuelven a pasar.

## Issues

### CRITICAL
Ninguno.

### WARNING
Ninguno.

### SUGGESTION

1. `inventario/api/routers/ordenes.py:57` (`@router.delete("/{numero:path}")`) — `GET /api/ordenes/<algo>` ahora responde 405 en lugar de 404. Sin impacto funcional (esa ruta no existía).
2. `inventario/api/routers/ordenes.py:73-76` (parámetro `reintegrar`) — `?reintegrar=true&reintegrar=false` se acepta y gana el último valor, sin 422. Con un borrado irreversible convendría rechazar el valor múltiple; riesgo bajo (el cliente real envía un solo valor). **Resuelta (2026-11-20)**: el router responde 422 "El campo reintegrar debe enviarse una sola vez." (tests `BorrarErroresTest.test_reintegrar_repetido`, `test_reintegrar_repetido_gana_sobre_404_y_numero_invalido` y `BorrarSinSesionTest.test_sin_sesion_gana_sobre_reintegrar_repetido` en `tests/test_api_ordenes.py`). Suite: 419 tests OK.
3. `inventario/repositories/sqlite_repo.py:453-454` — el `RuntimeError` por `rowcount != 1` en el DELETE de la orden es inalcanzable bajo `BEGIN IMMEDIATE`; es defensa en profundidad documentada, no requiere cambios.
4. KB pendiente al archivar (ya en design.md "Open Questions"): `02_descripcion_general.md` (`DELETE /api/productos/<id>`, `GET /api/productos`), Flujo 6 ("por cascade") y `08_arquitectura_propuesta.md` (`borrar_con_reintegro`).

## 7.5 /docs

**Resultado: OK** (2026-11-20, orquestador, Playwright).

- Entorno: `uvicorn inventario.api.main:app --port 8768` con base temporal nueva fuera del repo y credenciales de prueba por entorno (no se leyó `.env`; no se tocó ninguna base del usuario). Servidor y navegador cerrados al terminar.
- Siembra: `A-01`, `B-02`, `CAJA/10` y órdenes `OT-1`, `OT-2`, `OT/3`, `OT-4`.
- Swagger lista ambos DELETE; `reintegrar` aparece como desplegable `true`/`false` con `true` preseleccionado (coherente con la casilla marcada por defecto de C-06).
- Desde la UI de Swagger ("Try it out" → "Execute"): login 200 y `DELETE /api/ordenes/ot-1?reintegrar=true` → 200 con `OT-1` normalizado, `reintegros` con `stock` posterior (A-01 4→7, B-02 4→6).
- Desde la misma página (misma cookie), 28 casos conformes a spec: segundo borrado → 404; `reintegrar` ausente/vacío → 422 "obligatorio", `TRUE`/`1` → 422 "debe ser true o false"; número vacío/31 → 422; inexistente → 404; 422 antes que 404; borrado sin reintegro sin cambios de stock y `reintegros: []`; baja de `caja/10` (código con `/`) conserva stock, desaparece del inventario, segunda baja/egreso/nueva orden → 404, el listado de órdenes la sigue mostrando; borrar `OT/3` (codificado) con reintegro reactiva `CAJA/10` (`reactivado: true`); baja + ingreso reactiva y suma; borrar sin reintegro no reactiva; sin sesión ambos DELETE → 401.
- SQL final: 0 órdenes y 0 ítems; `A-01` inactivo con stock 7 conservado; `movimientos` solo con los 4 ingresos (ningún borrado ni baja escribió movimientos).
- Consola del navegador: solo los "Failed to load resource" de las respuestas 4xx provocadas.
