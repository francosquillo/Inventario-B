# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario revise las decisiones 1-14 de `design.md` (Q1-Q11 ya decididas el 2026-11-27) y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)` para L1, E1, E2 y P1 (cumplido el 2026-11-27). Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). JS puro con Node desde `unittest` (patrón de `tests/test_procesos_js.py`, se omite sin Node); resto del frontend con guardas estáticas (patrón de `tests/test_frontend_ordenes_precios.py`); el navegador se verifica en el grupo 13 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorios, services y migración con SQLite real (`:memory:` o archivo temporal) (regla dura 4).
> - Sin dependencias nuevas; sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - **Edición de orden con todos sus ajustes de stock en UNA transacción, todo o nada** (regla dura 3); la migración también. Datos, cantidades, importes y chequeo validados en el navegador Y en el backend. Nunca `float` para dinero.
> - `tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css`. En JS: datos solo con `textContent`/`createElement`, sin `innerHTML`.
> - **Nunca** migrar ni borrar `dev-local.db` real durante el apply (solo se copia en 1.3); tests con bases temporales y verify sobre una copia. Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear solo los mockups necesarios en `openspec/changes/paso-5i-modificar-ordenes-checkeo/mockups/` (`ordenes.html` con L1, E1, E2 y P1; `README.md` con estados, omisiones justificadas y `Approval: pending`) y verificar que abren localmente
- [x] 0.2 Renderizar a 390x844 y 1440x900 en `mockups/previews/`; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir el JS puro en el verify con `browser_evaluate`)
- [x] 1.3 Backup: copiar `dev-local.db` a `dev-local.bak-5i.db` en la raíz (copia de archivo, sin abrirlo con SQLite) y verificar con `git status` que no aparece y que ambos archivos tienen el mismo tamaño

## 2. Migración y esquema — spec `inicializacion-base-datos` (design D6, D8)

- [x] 2.1 RED (`tests/test_sqlite_migracion_chequeo_final.py`, nuevo): DDL de C-06h **copiado literal** (con las columnas de datos y precios) y dos órdenes con ítems, procesos, servicio, datos y precios, productos con categoría y movimientos → `inicializar_esquema` crea `orden_chequeo_final` vacía; verificar rojo
- [x] 2.2 GREEN: `inventario/domain/chequeo_final.py` (`CHEQUEO_FINAL`) y `_crear_chequeo_final(conn, loguear)` (si no existe la tabla: `_transaccion`, conteos, `CREATE TABLE`, log) llamada tras `_migrar_datos_precios_orden` y antes de `NORMALIZAR_FECHAS_SQL`. Verificar verde
- [x] 2.3 TRIANGULATE: filas existentes idénticas en todas las tablas; tres arranques sin cambios y una orden con chequeo lo conserva; falla inyectada en el `CREATE` → no queda la tabla y la excepción sube; log solo si la base existía. Verificar verde
- [x] 2.4 RED→GREEN (`tests/test_sqlite_schema.py`): base nueva con `orden_chequeo_final`; la base rechaza clave `lavado`, precio -1, 1.5, `'10'` y 100000000000, la misma clave dos veces en una orden, y acepta `NULL`/0/99999999999; borrar la orden borra su chequeo (CASCADE). Verificar verde
- [x] 2.5 REFACTOR (CHECK de claves generado desde `CHEQUEO_FINAL`); suite verde

## 3. Dominio — specs `chequeo-final-ordenes`, `precios-ordenes` (Subtotales y total) (design D2, D6)

- [x] 3.1 RED (`tests/test_orden_totales.py`): `Orden` con servicio 4500000, adicional 1500000, chequeo Combustible 800000 y Entrega sin precio, ítem 1200000 → `subtotal_servicios` 6800000, `subtotal_items` 1200000, `total` 8000000; verificar rojo
- [x] 3.2 GREEN: `ChequeoFinal(clave, nombre, precio=None)`, `Orden.chequeo_final = ()`, `subtotal_servicios` suma el chequeo; `AjusteStock(codigo, nombre, cantidad_anterior, cantidad_nueva, stock, reactivado)` y `ResultadoEdicionOrden(orden, ajustes)`. Verificar verde
- [x] 3.3 TRIANGULATE: casos de C-06h siguen dando lo mismo (chequeo vacío); chequeo solo con precios vacíos → no suma; chequeo con tope 99999999999. Verificar verde
- [x] 3.4 REFACTOR; suite verde (constructores existentes intactos gracias a los defaults)

## 4. Repositorio: chequeo en alta, lectura y borrado — specs `chequeo-final-ordenes`, `consulta-ordenes` (design D6)

- [x] 4.1 RED (`tests/test_sqlite_orden_repository.py`): `crear(..., chequeo_final=(ChequeoFinal("entrega", "Entrega", None), ChequeoFinal("combustible", "Combustible", 800000)))` → la orden devuelta trae el chequeo en el orden fijo (Combustible, Entrega); verificar rojo
- [x] 4.2 GREEN: `OrdenRepository.crear(..., chequeo_final=())`; INSERT en `orden_chequeo_final` dentro de la misma `_transaccion`; `_leer_chequeo_final` por lote ordenado por posición en `CHEQUEO_FINAL`; `_a_ordenes` con `chequeo_final`; `borrar` borra el chequeo. Verificar verde
- [x] 4.3 TRIANGULATE: sin chequeo → `()`; `listar` y `_buscar_orden_por_numero` con chequeo sin multiplicar filas (orden con 2 ítems, 2 procesos y 2 chequeos); `borrar` devuelve la orden con su chequeo y no deja filas
- [x] 4.4 RED→GREEN (atomicidad del alta): falla inyectada al escribir el chequeo → no existe la orden, ni ítems, ni procesos, ni servicio, y el stock no cambió
- [x] 4.5 REFACTOR; suite verde

## 5. Repositorio: edición atómica con ajuste por diferencia — spec `edicion-ordenes` (design D2, D3, D5)

- [x] 5.1 RED (`tests/test_sqlite_orden_edicion.py`, nuevo): `A-01` stock 5, orden `OT-0043` con `A-01` x 2 → `editar("OT-0043", fecha, [("A-01", 4, None)], ...)` → orden con x 4, stock 3, `ajustes` = `(AjusteStock("A-01", …, 2, 4, 3, False),)`; verificar rojo
- [x] 5.2 GREEN: `OrdenRepository.editar(numero, fecha, items, procesos, servicio, datos, chequeo_final, conservar_servicio)` en una `_transaccion`: buscar orden (404), anteriores, productos por código sin filtrar `activo`, deltas, ausentes y faltantes antes de escribir, `UPDATE ordenes`, reemplazo de ítems/procesos/servicio/chequeo, `_SQL_RESTAR` con guarda `rowcount` y `_SQL_SUMAR_Y_ACTIVAR` para deltas negativos. Verificar verde
- [x] 5.3 TRIANGULATE (stock): reducir (x4 → x1, stock 5 → 8); quitar uno y agregar otro; solo precios (stock igual, `ajustes` vacío); usar stock + lo ya descontado (stock 1, x2 → x3 → stock 0); edición idéntica → sin ajustes; líneas consolidadas llegan ya sumadas. Verificar verde
- [x] 5.4 TRIANGULATE (inactivos e inexistentes): inactivo con misma cantidad → sigue inactivo con su stock; inactivo quitado → activo con stock + cantidad (`reactivado=True`); inactivo aumentado → `ProductosNoEncontrados(["C-99"])`; código inexistente → `ProductosNoEncontrados`; ausentes y faltantes juntos → gana ausentes. Verificar verde
- [x] 5.5 TRIANGULATE (faltantes y atomicidad): faltante con `disponible`=stock y `solicitado`=delta; varios faltantes juntos; faltante + reintegro → nada cambia (stock del reintegrado igual); falla inyectada al escribir el chequeo (CHECK violado) → orden, líneas, procesos, servicio, datos y **todos** los stocks como antes; orden inexistente → `OrdenNoEncontrada` sin cambios; dos ediciones seguidas (x4 y luego x1 → stock 6). Verificar verde
- [x] 5.6 TRIANGULATE (servicio y contenido): `conservar_servicio=True` con precio nuevo conserva nombre y chequeos aunque el catálogo lo haya borrado; `conservar_servicio=True` sin servicio → `DatosInvalidos("La orden no tiene un servicio general para conservar.")` sin cambios; servicio `None` lo quita; reemplazo completo deja datos/procesos/chequeo vacíos si no vienen; número, id, usuario y `created_at` intactos; sin filas en `movimientos`. Verificar verde
- [x] 5.7 REFACTOR (helpers compartidos con `crear` y `borrar`: guardado de líneas/procesos/servicio/chequeo y búsqueda de productos); suite verde

## 6. Service: validación compartida y edición — specs `edicion-ordenes`, `chequeo-final-ordenes` (design D4, D5, D6)

- [x] 6.1 RED (`tests/test_orden_service.py`): `editar("  ot-0043 ", fecha="2026-11-28", componentes=[("A-01", 2, 1300000)], chequeo_final=[{"clave": " Entrega ", "precio": 500000}])` → repo real con la orden editada y el chequeo normalizado; verificar rojo
- [x] 6.2 GREEN: extraer `_validar_contenido(...)` de `crear` (sin cambiar sus mensajes ni su prioridad) y agregar `_resolver_chequeo_final` y `editar`. Verificar verde y que todos los tests de `crear` siguen verdes
- [x] 6.3 TRIANGULATE (chequeo, también en `crear`): clave inexistente → "El ítem de chequeo final 'lavado' no existe."; repetida (`Entrega`, `entrega`) → "Chequeo final 2: 'entrega' está repetido."; precio -1 en posición 2 → "Chequeo final 2: El precio debe ser…"; `"combustible"` como texto suelto en vez de lista → "El campo chequeo_final debe ser una lista de claves."; objeto con otras claves → mismo mensaje; `None`/ausente → sin chequeo. Verificar verde
- [x] 6.4 TRIANGULATE (edición): `numero` en el cuerpo → "El número de la orden no se puede cambiar."; `conservar_servicio` con `servicio` → "No se puede elegir un servicio general y conservar el actual a la vez."; `conservar_servicio` `"si"` → "El campo conservar_servicio debe ser true o false."; `conservar_servicio=True` + `precio_servicio` sin servicio elegido → válido; componentes vacíos, egreso < ingreso y líneas repetidas como en el alta. Verificar verde
- [x] 6.5 RED→GREEN (prioridad, design D4): número en blanco + fecha inválida → número; `numero` en cuerpo + fecha inválida → número en cuerpo; fecha inválida en orden inexistente → fecha (422 antes del 404); chequeo inválido + producto inexistente → chequeo; producto inexistente + stock insuficiente → producto; escenarios de prioridad del alta (C-06f/g/h) siguen verdes; `api/dependencies.py` sin cambios de constructor
- [x] 6.6 REFACTOR; suite verde

## 7. API — specs `api-http`, `consulta-ordenes` (design D1)

- [x] 7.1 RED (`tests/test_api_ordenes_edicion.py`, nuevo, `TestClient`): escenario "Edición con ajustes" con diccionario exacto (`orden` + `ajustes`) y movimientos sin cambios; verificar rojo
- [x] 7.2 GREEN: `OrdenEdicionRequest`, `ChequeoFinalOut`, `AjusteOut`, `EdicionOrdenOut`, `chequeo_final` en `OrdenRequest`/`OrdenOut`/`orden_out`; ruta `PUT /api/ordenes/{numero:path}` con `responses` 404/409/422 documentados. Verificar verde
- [x] 7.3 TRIANGULATE: conservar servicio; número con `/` (`OT/12`); 409 con `faltantes` (`solicitado` = adicional) sin cambios; 404 orden inexistente; 404 productos con `codigos`; 422 `numero` en cuerpo; 422 conservar sin servicio; 401 sin sesión; alta con y sin `chequeo_final` (201, `"chequeo_final": []`); ítem inexistente 422 sin tocar stock. Verificar verde
- [x] 7.4 TRIANGULATE (compatibilidad): actualizar los diccionarios exactos de alta, listado y borrado con `"chequeo_final": []` (sin cambiar su intención); OpenAPI sigue con 21 rutas y `/api/ordenes/{numero}` tiene `put` y `delete`; `tests/test_api_csrf.py` suma `PUT /api/ordenes/{numero}` con `text/plain` → 422 sin efectos. Verificar verde
- [x] 7.5 REFACTOR; suite verde

## 8. JS puro — spec `interfaz-web` (Chequeo final en el formulario de edición, Resumen) (design D6, D7)

- [x] 8.1 RED (`tests/test_chequeo_final_js.py`, nuevo, Node): `static/js/chequeo-final.js` expone `ITEMS` igual a `CHEQUEO_FINAL` de Python (el test lee la constante) y `leer([{clave, marcado, importe}])` → `{valores: [{clave, precio}], errores}` (solo marcados; importe vacío → `null`; `12.5` → "Ingresá un importe válido (ej. 12.500,50)."); verificar rojo
- [x] 8.2 GREEN: `chequeo-final.js` (sin DOM al cargar, `window.ChequeoFinal`, usa `Precios.parsear`). Verificar verde
- [x] 8.3 RED→GREEN (`tests/test_precios_js.py`): `Precios.resumen({..., chequeo_final: [800000, null]})` suma al subtotal de servicios, con la misma tabla de casos que 3.1/3.3; sin `chequeo_final` → igual que hoy
- [x] 8.4 REFACTOR; suite verde

## 9. Formulario de orden compartido (refactor sin cambio de comportamiento) (design D7)

- [x] 9.1 Safety net: correr las guardas de "Nueva orden" (`tests/test_frontend_estatico.py`, `test_frontend_categorias.py`, `test_frontend_procesos.py`, `test_frontend_servicios.py`, `test_frontend_precios.py`, `test_frontend_filtro_modificar.py`) y anotar el conteo
- [x] 9.2 RED (guarda, `tests/test_frontend_ordenes_edicion.py`, nuevo): existe `static/js/orden-form.js` con `window.OrdenForm` (sin DOM al cargar), `index.html` lo carga antes de `inventario.js` y `inventario.js` ya no define la lógica de líneas/procesos/servicio/datos/resumen de la orden; verificar rojo
- [x] 9.3 GREEN: mover la lógica del formulario a `orden-form.js` (`montar(raiz, {modo, …})`, IDs con prefijo por instancia); "Nueva orden" usa `OrdenForm` en modo `"nueva"`. Todas las guardas de 9.1 verdes sin tocar sus aserciones (salvo rutas de archivo, anotadas). Verificar verde
- [x] 9.4 REFACTOR; suite verde. Si el refactor no cierra en esta tarea, aplicar el plan B de design (Risks) y anotarlo como desvío

## 10. Modal "Editar orden" — spec `interfaz-web` (Botón Editar, Modal de edición, Stock disponible, Chequeo final en el formulario, Resultado de la edición) (mockups E1 y E2 aprobados = criterio de aceptación) (design D5, D7)

- [x] 10.1 RED (guardas en `tests/test_frontend_ordenes_edicion.py`): `ordenes.html` tiene `#modal-editar` (`role="dialog"`, `aria-modal`, título con el número, fieldset "Chequeo final" con seis casillas + importe con `aria-label`, botón "Guardar cambios") y carga `precios.js`, `datos-orden.js`, `procesos.js`, `busqueda.js`, `chequeo-final.js`, `orden-form.js` antes de `ordenes.js`; `ordenes.js` agrega `data-editar` con `aria-label` "Editar orden X" y clase `no-print`, usa `Api` con `PUT` y `encodeURIComponent` del número, sin `innerHTML`; verificar rojo
- [x] 10.2 GREEN (E1): botón "Editar"; modal con `OrdenForm` en modo `"editar"` precargado desde el objeto de la lista (importes con `Precios.formatear` sin `$`), servicio "(actual)" → `conservar_servicio`, procesos borrados del catálogo como personalizados, etiqueta "(stock N + M en esta orden)", inactivos de la orden "(dado de baja)" solo en su línea, fieldset de chequeo con importe deshabilitado si no está marcado y resumen con chequeo. Verificar verde
- [x] 10.3 GREEN (resultado y errores, E2): envío sin duplicar; éxito → cierra, recarga con filtros vigentes y aviso "Orden X actualizada." con ajustes ("−N descontada", "+N devuelta", "reactivado") o "Sin cambios de stock."; 409 bajo cada línea ("Disponible X, solicitado Y"); 404 productos en su línea; 404 orden → mensaje y recarga al cerrar; 422 en la alerta general o en la línea. Verificar verde
- [x] 10.4 REFACTOR; guardas de `/ordenes` de C-06c/f/g/h verdes

## 11. Chequeo en `/ordenes` y en el PDF — spec `interfaz-web` (Chequeo final en pantalla y en el PDF) (mockups L1 y P1 aprobados = criterio de aceptación) (design D7)

- [x] 11.1 RED (guardas): `ordenes.js` arma la fila "Chequeo final:" solo si hay ítems, chips "Nombre · $ …"/"—" con `Precios.formatear`, después de "Servicios adicionales:"; la sección impresa "Chequeo final" lista **los seis** ítems de `ChequeoFinal.ITEMS` en orden: hechos con "[✓]", "Hecho" y precio, no hechos con "[ ]" y "No se hizo" sin precio, también si la orden no tiene ninguno (design D11); la marca es texto, no solo color; resumen sigue tomando los valores de la API. Verificar rojo
- [x] 11.2 GREEN (pantalla, L1) y (impresión, P1): estructura y CSS en `app.css` con tokens existentes; en papel, sección "Chequeo final" con los seis ítems uno por línea (hecho: `[✓]` + "Hecho" + precio a la derecha; no hecho: `[ ]` + "No se hizo", gris de papel solo como refuerzo), antes del resumen; en pantalla solo los hechos; "Editar" no se imprime. Verificar verde
- [x] 11.3 REFACTOR; suite verde

## 12. Documentación, suite y migración sobre una copia

- [x] 12.1 `README.md`: edición de órdenes (`PUT`, reemplazo completo, ajuste por diferencia sin movimientos, `conservar_servicio`, ejemplo de cuerpo), `chequeo_final` (claves fijas, precios en centavos), nota de migración con **backup `dev-local.bak-5i.db`**. Verificar contra `/openapi.json`
- [x] 12.2 Suite completa verde (baseline + nuevos, cero fallas) y `openspec validate paso-5i-modificar-ordenes-checkeo --strict` sin errores
- [x] 12.3 Copiar `dev-local.db` al scratchpad y arrancar con `INVENTARIO_DB_PATH` apuntando a la copia: conteos de todas las tablas iguales antes y después; `orden_chequeo_final` vacía; cada orden con `"chequeo_final": []` en la API; log de migración una sola vez; segundo arranque sin cambios; `PRAGMA integrity_check` = `ok` y `PRAGMA foreign_key_check` vacío. El original no se toca

## 13. Verify en `/docs` y navegador (sobre la copia)

- [x] 13.1 `/docs` sobre la copia: `PUT` con aumento, reducción, quitar/agregar y chequeo (stock verificado en `/api/inventario` antes y después), 409 sin cambios, 404, 422 de `numero` en cuerpo, `GET /api/movimientos` sin cambios
- [x] 13.2 Playwright contra la app real (uvicorn sobre la copia, puerto libre) a 390x844 y 1440x900, comparando con L1, E1 y E2: abrir "Editar", precarga, servicio "(actual)", marcar/desmarcar chequeo con resumen en vivo, guardar con ajustes y aviso, provocar 409 (otra pestaña/API baja el stock) y ver el error en la línea, cancelar sin efectos; "Nueva orden" sigue igual que el mockup N1 de C-06h; capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos inesperados
- [x] 13.3 Impresión: `print` emulado y `page.pdf` (A4) de una orden con chequeo parcial y otra sin ninguno, comparando con P1: los seis ítems con `[✓]`/"Hecho" y `[ ]`/"No se hizo"; verificar también con `emulateMedia` + filtro de escala de grises que la marca se distingue sin color
- [x] 13.4 Detener uvicorn (solo el PID propio; confirmar con `netstat` que el puerto quedó libre) y cerrar Playwright; registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar la KB 02, 04, 05 (RN-OR-10 reemplazada), 06 y 07 (ver design § Decisions) y `CHANGES.md` (C-06i `[x]` con fecha; paridad C-07 de design D9).
- Esperar "Continuar" del usuario antes de proponer C-06j (`paso-5j-impresion-ordenes`).
