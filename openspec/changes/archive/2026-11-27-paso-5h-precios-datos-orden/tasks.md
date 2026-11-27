# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario revise las decisiones 1-19 de `design.md` (y responda o acepte las ★ de Q1-Q5) y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)` para N1, L1 y P1. Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). JS puro con Node desde `unittest` (patrón de `tests/test_procesos_js.py`, se omite sin Node); resto del frontend con guardas estáticas (patrón de `tests/test_frontend_servicios.py`); el navegador se verifica en el grupo 12 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorios, services y migración con SQLite real (`:memory:` o archivo temporal) (regla dura 4).
> - Sin dependencias nuevas; sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - Alta de orden con datos y precios y la migración en una transacción, todo o nada (regla dura 3). Datos, fechas e importes validados en el navegador Y en el backend. Nunca `float` para dinero (centavos enteros).
> - `tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css`. En JS: datos solo con `textContent`/`createElement`, sin `innerHTML`.
> - **Nunca** migrar ni borrar `dev-local.db` real durante el apply (solo se copia en 1.3); tests con bases temporales y verify sobre una copia. Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear solo los mockups necesarios en `openspec/changes/paso-5h-precios-datos-orden/mockups/` (`nueva-orden.html` N1, `ordenes.html` L1 y P1, `README.md` con estados, omisiones justificadas y `Approval: pending`) y verificar que abren localmente
- [x] 0.2 Renderizar a 390x844 y 1440x900 en `mockups/previews/`; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir el JS puro en el verify con `browser_evaluate`)
- [x] 1.3 Backup: copiar `dev-local.db` a `dev-local.bak-5h.db` en la raíz (copia de archivo, sin abrirlo con SQLite) y verificar con `git status` que no aparece y que ambos archivos tienen el mismo tamaño

## 2. Migración y esquema — spec `inicializacion-base-datos` (design D1, D7, D8, D9)

- [x] 2.1 RED (`tests/test_sqlite_migracion_precios.py`, nuevo): DDL de C-06g **copiado literal** (doce tablas) con dos órdenes con ítems, procesos y servicio, productos con categoría y movimientos → `inicializar_esquema` agrega `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso`, `fecha_egreso` a `ordenes` (con `fecha` intacta) y `precio_centavos` a `orden_items`, `orden_procesos`, `orden_servicio`, todas en `NULL`; verificar rojo
- [x] 2.2 GREEN: `_COLUMNAS_NUEVAS` y `_migrar_datos_precios_orden(conn, loguear)` (solo columnas faltantes, `_transaccion`, verificación de conteos, log) llamada tras `_crear_servicios_generales` y antes de `NORMALIZAR_FECHAS_SQL`. **Confirmar acá que SQLite acepta el CHECK `fecha_egreso >= fecha_ingreso` en `ADD COLUMN`**; si no, aplicar el plan B de design D9 y anotar el desvío. Verificar verde
- [x] 2.3 TRIANGULATE: filas existentes idénticas (todas las tablas); tres arranques sin cambios y una orden con datos/precios los conserva; base a medio migrar (falta solo una columna) → agrega solo esa; falla inyectada en la cuarta columna → ninguna columna nueva y la excepción sube; log solo si la base existía. Verificar verde
- [x] 2.4 RED→GREEN (`tests/test_sqlite_schema.py`): base nueva con las columnas; la base rechaza `precio_centavos` -1, 1.5, `'10'` y 100000000000 y acepta `NULL`/0/99999999999; `cliente` `'  '`/81 caracteres; `casco`/`motor`/`trailer` 61; `celular` de 5 o 21; `fecha_ingreso`/`fecha_egreso` `'2026-02-30'`; egreso anterior al ingreso; y acepta egreso sin ingreso y fechas anteriores o posteriores a `fecha`. Verificar verde
- [x] 2.5 REFACTOR (CHECK de precio como constante compartida); suite verde

## 3. Dominio: entidades y totales — spec `precios-ordenes` (Subtotales y total) (design D2, D10)

- [x] 3.1 RED (`tests/test_orden_totales.py`, nuevo): `Orden` con servicio 4500000, adicionales 1500000 y 800000, ítems 1200000 y 350000 → `subtotal_servicios` 6800000, `subtotal_items` 1550000, `total` 8350000; verificar rojo
- [x] 3.2 GREEN: `precio` (default `None`) en `ItemOrden`, `ProcesoOrden`, `ServicioOrden`; `DatosOrden` y `Orden.datos`; propiedades `subtotal_servicios`, `subtotal_items`, `total`. Verificar verde
- [x] 3.3 TRIANGULATE (tabla de casos que se replica en 7.3): precios vacíos cuentan 0 (servicio sin precio + adicional 1500000 + adicional vacío + ítems 1200000 y vacío → 1500000 / 1200000 / 2700000); sin servicio ni procesos; sin ningún precio → 0/0/0; precio 0; tope 99999999999 en un ítem
- [x] 3.4 REFACTOR; suite verde (constructores existentes intactos gracias a los defaults)

## 4. Repositorio — specs `precios-ordenes`, `datos-cliente-ordenes`, `consulta-ordenes` (design D10)

- [x] 4.1 RED (`tests/test_sqlite_orden_repository.py`): `crear(..., items=[("A-01", 2, 1200000)], procesos=(ProcesoOrden("Limpieza", False, 1500000),), servicio=ServicioOrden(..., precio=4500000), datos=DatosOrden(cliente="Juan Pérez", fecha_ingreso=date(2026, 11, 26), fecha_egreso=date(2026, 11, 29), ...))` → la orden devuelta trae todo; verificar rojo
- [x] 4.2 GREEN: `OrdenRepository.crear` con `items` `(codigo, cantidad, precio)` y `datos`; INSERTs con columnas nuevas; lecturas (`_SQL_LISTAR_ORDENES`, procesos y servicios por lote) con datos y precios. Verificar verde
- [x] 4.3 TRIANGULATE: sin datos ni precios → `None` en todo; dos procesos con precios distintos y uno vacío; `listar` con filtros por `fecha` (no por ingreso/egreso) y `_buscar_orden_por_numero` traen datos y precios sin multiplicar filas; `borrar` devuelve la orden con datos y precios
- [x] 4.4 RED→GREEN (atomicidad): falla inyectada al guardar el servicio con precio (p. ej. precio que viola el CHECK) → no existe la orden, ni ítems, ni procesos, ni servicio, y el stock no cambió
- [x] 4.5 REFACTOR; suite verde (actualizar llamadas existentes a `crear` con tuplas de 2 si hace falta, sin cambiar su intención)

## 5. Service: validación — specs `precios-ordenes`, `datos-cliente-ordenes`, `ordenes-trabajo` (Orden de prioridad) (design D3, D4, D5, D7, D8, D11)

- [x] 5.1 RED (`tests/test_orden_service.py`): `crear(..., componentes=[("A-01", 2, 1200000)], datos={"cliente": "  Juan  Pérez "}, ...)` → cliente "Juan  Pérez" y precio 1200000; verificar rojo
- [x] 5.2 GREEN: `validar_precio(valor, prefijo)`, normalización de textos opcionales, `validar_celular`, fechas de ingreso y egreso opcionales con `parsear_fecha` y comparación entre ellas (nunca con `fecha`); `_consolidar` con importe sumado. Verificar verde
- [x] 5.3 TRIANGULATE (datos, todos opcionales): todo ausente/`None`/`"   "` → orden creada sin datos; cliente 81 → "El cliente admite hasta 80 caracteres."; cliente `3` → "El campo cliente debe ser texto."; casco/motor/trailer 61 → "El campo motor admite hasta 60 caracteres." (y los otros); celular válidos (`11 5555-1234`, `+54 9 11 5555-1234`, `(011) 4555-1234`) e inválidos (`11-abc`, `12345`, `11+5555 1234`, 21 caracteres, `(((---)))` con menos de 6 dígitos); solo `fecha` (sin ingreso ni egreso) ok; ingreso + egreso igual/posterior ok; solo egreso ok; ingreso/egreso anteriores o posteriores a `fecha` ok; egreso anterior al ingreso → 422; `2026-02-30`/`30/11/2026` en ingreso y en egreso con sus mensajes
- [x] 5.4 TRIANGULATE (precios): -1, 10.5, `"1500"`, `True`, 100000000000 → "Componente 2: El precio debe ser…"; 0 y `None` válidos; repetidos `A-01` x2 1000 + `a-01` x1 sin precio + `A-01` x1 500 → x4 con 1500; todos sin precio → `None`; `precio_servicio` sin servicio → "No se puede indicar el precio del servicio general sin elegir uno."; `precio_servicio` -5 → "El precio del servicio general debe ser…"; procesos `{"clave": "limpieza", "precio": 1500000}` + `"cambio-filtro"` + personalizado `{"nombre": "Pulido", "precio": 800000}` → orden y precios; clave repetida con precios 1000 y 2000 → primera con 1000; `{"clave": "cambio-motor", "precio": -1}` en posición 2 → "Proceso 2: …"; `{"nombre": "Pulido", "precio": "mil"}` → "Proceso personalizado 1: …"; objeto sin `clave` o con `clave` no texto → mensaje de tipo existente
- [x] 5.5 RED→GREEN (prioridad, design D11): fecha inválida + ingreso inválido → fecha; cliente 81 + componentes vacíos → cliente; egreso anterior al ingreso + cliente 81 → egreso; precio de componente inválido + servicio inexistente → componente; precio de proceso inválido + número duplicado → precio; escenarios de prioridad de C-06f/C-06g siguen verdes; `api/dependencies.py` sin cambios de constructor
- [x] 5.6 REFACTOR; suite verde

## 6. API — specs `api-http`, `consulta-ordenes` (design D12)

- [x] 6.1 RED (`tests/test_api_ordenes.py`): alta del escenario "Orden con datos y precios" → 201 con el diccionario exacto (datos, `precio` por línea, `servicio.precio`, `subtotal_servicios` 6000000, `subtotal_items` 1200000, `total` 7200000); verificar rojo
- [x] 6.2 GREEN: `ComponenteRequest.precio`, campos nuevos de `OrdenRequest`, `OrdenOut`/`ComponenteOut`/`ProcesoOrdenOut`/`ServicioOrdenOut` con precio, datos, subtotales y total; router pasa `datos` y `precio_servicio`. Verificar verde
- [x] 6.3 RED→GREEN: alta **sin** campos nuevos (cuerpo de C-06g) → 201 con `fecha` igual que hoy, datos (incluidas `fecha_ingreso`/`fecha_egreso`) `null`, precios `null` y totales 0 (compatibilidad); datos vacíos (`"  "`, `""`, `null`) → `null`; solo `fecha_egreso` → 201; 422 de cliente largo, egreso anterior al ingreso, precio no entero (1500.5), `precio_servicio` sin servicio, celular inválido, sin tocar stock; actualizar los diccionarios exactos de alta, listado y borrado
- [x] 6.4 RED→GREEN: `GET /api/ordenes` con subtotales usando precios vacíos (4500000 / 1200000 / 5700000); orden anterior a la migración (insertada con SQL antes de migrar) → datos `null`, precios `null`, totales 0; renombrar `limpieza` no cambia nombre ni precio en la orden; filtros `desde`/`hasta` siguen sobre `fecha` (no sobre ingreso/egreso); `DELETE` devuelve la orden con datos, precios y totales
- [x] 6.5 RED→GREEN: OpenAPI sigue con 21 rutas; `/api/ordenes` POST documenta los campos nuevos (centavos, `fecha_ingreso`/`fecha_egreso` opcionales)
- [x] 6.6 REFACTOR; suite completa verde

## 7. JS puro — spec `interfaz-web` (Importes, Resumen, Datos del cliente, Procesos en la nueva orden) (design D1, D2, D13)

- [x] 7.1 RED (`tests/test_precios_js.py`, nuevo, Node): `Precios.parsear("12.500,50")` → `{centavos: 1250050, error: null}`; verificar rojo
- [x] 7.2 GREEN: `static/js/precios.js` (sin DOM al cargar, `window.Precios`, sin `parseFloat`). Verificar verde
- [x] 7.3 TRIANGULATE: `"12500"`, `"12.500"`, `"12500,5"`, `"$ 12.500"`, `" 0 "` válidos; `""`/espacios → `{centavos: null, error: null}`; `"12.5"`, `"1.23.456"`, `"-100"`, `"1,234"`, `"abc"`, `"12,"` → "Ingresá un importe válido (ej. 12.500,50)."; `"1.000.000.000"` → "El importe admite hasta $ 999.999.999,99."; `formatear(1250050)` → `"$ 12.500,50"`, `formatear(0)` → `"$ 0,00"`, `formatear(null)` → `"—"`, tope; `resumen(...)` con **la misma tabla de casos de 3.3** (vacío = 0)
- [x] 7.4 RED→GREEN (`tests/test_datos_orden_js.py`, nuevo): `DatosOrden.validar` — todo vacío → valores `null` sin errores; recortes; cliente 81; casco/motor/trailer 61; celulares válidos/inválidos de 5.3; ingreso/egreso vacíos, solo egreso, egreso anterior al ingreso; mismos textos que el backend
- [x] 7.5 RED→GREEN (`tests/test_procesos_js.py`): dos líneas con la misma clave del catálogo → error "Ya está en otra línea." en la segunda; armado de `procesos`/`procesos_personalizados` como objetos `{clave|nombre, precio}`; tests de C-06f actualizados a la forma objeto
- [x] 7.6 REFACTOR

## 8. "Nueva orden" — spec `interfaz-web` (Modal de nueva orden, Datos del cliente, Importes, Resumen, Procesos en la nueva orden, Procesos personalizados) (mockup N1 aprobado = criterio de aceptación) (design D6, D13)

- [x] 8.1 RED (guardas, `tests/test_frontend_precios.py` nuevo): `index.html` conserva `#ord-fecha` "Fecha (AAAA-MM-DD)" junto al número; fieldset "Cliente y embarcación" con cliente/celular/casco/motor/trailer/`#ord-ingreso`/`#ord-egreso` **sin `required` ni asterisco**; `#ord-servicio-precio`; plantilla de línea de componente con importe; legend "Servicios adicionales", botón "Agregar servicio adicional"; resumen con "Subtotal servicios", "Subtotal ítems", "Total" y `aria-live`; carga `precios.js` y `datos-orden.js`; `inventario.js` envía `cliente`, `fecha_ingreso`, `fecha_egreso`, `precio`, `precio_servicio` y objetos de procesos; sin `innerHTML`. Verificar rojo
- [x] 8.2 GREEN (HTML + layout según N1, modal 44rem, móvil apilado): campos, cajas de importe con `aria-label` por línea, resumen. Verificar verde
- [x] 8.3 GREEN (JS): resumen recalculado en cada `input`/agregar/quitar línea/cambio de servicio; caja de precio del servicio deshabilitada y vacía con "Sin servicio general"; validación antes de enviar (`DatosOrden.validar`, `Precios.parsear` por caja, repetidos de servicios adicionales) con errores junto a cada campo (`aria-invalid`, `aria-describedby`); envío con `null` en vacíos. Verificar verde
- [x] 8.4 GREEN (textos renombrados, design D6): "Servicio adicional personalizado", "Una orden admite hasta 10 servicios adicionales personalizados.", "No se pudo cargar la lista de servicios adicionales.". Guardas de C-06e/f/g de "Nueva orden" verdes (actualizar solo los textos renombrados)
- [x] 8.5 REFACTOR

## 9. `/ordenes` y PDF — spec `interfaz-web` (Pantalla de órdenes, Datos y precios de cada orden en pantalla, Exportar una orden a PDF) (mockups L1 y P1 aprobados = criterio de aceptación) (design D14, D15)

- [x] 9.1 RED (guardas, `tests/test_frontend_ordenes_precios.py` nuevo): `ordenes.js` mantiene la fecha en la cabecera, fila de datos (con "Ingreso:"/"Egreso:") solo si hay alguno, precio del servicio, chips "Nombre · $ …", columna "Importe", resumen con `subtotal_servicios`/`subtotal_items`/`total` de la API (sin recalcular), etiqueta "Servicios adicionales:" / impresa "Servicios adicionales"; `#print-head` sin cambios ("Fecha: … · N componentes"); usa `Precios.formatear`; sin `innerHTML`. Verificar rojo
- [x] 9.2 GREEN (pantalla, L1): estructura y CSS en `app.css` con tokens existentes; envuelve a 390 px; orden vieja con "—" y resumen en $ 0,00. Verificar verde
- [x] 9.3 GREEN (impresión, P1): CSS de impresión: datos (con ingreso/egreso) en dos columnas tras el encabezado, servicio con precio, tabla con "Importe", "Servicios adicionales" con precio a la derecha, resumen al final con línea superior; omitir lo vacío. Verificar verde
- [x] 9.4 REFACTOR; guardas de `/ordenes` de C-06c/f/g verdes (actualizar solo "Procesos:"/"Procesos realizados")

## 10. Documentación y suite

- [x] 10.1 `README.md`: datos del cliente (opcionales, con `fecha_ingreso`/`fecha_egreso` aparte de `fecha`), precios en centavos en la API (ejemplo de cuerpo), subtotales/total calculados, "Servicios adicionales" = procesos, nota de migración con **backup `dev-local.bak-5h.db`**. Verificar contra `/openapi.json`
- [x] 10.2 Suite completa verde (baseline + nuevos, cero fallas) y `openspec validate paso-5h-precios-datos-orden --strict` sin errores

## 11. Migración sobre una copia

- [x] 11.1 Copiar `dev-local.db` al scratchpad y arrancar con `INVENTARIO_DB_PATH` apuntando a la copia: conteos de todas las tablas iguales antes y después; columnas nuevas presentes y en `NULL`; cada orden con datos `null`, precios `null` y totales 0 en la API; log de migración una sola vez; segundo arranque sin cambios; `PRAGMA integrity_check` = `ok` y `PRAGMA foreign_key_check` vacío. El original no se toca

## 12. Verify en `/docs` y navegador

- [x] 12.1 `/docs` sobre la copia: alta con datos y precios (centavos), alta sin campos nuevos, 422 de egreso/celular/precio, listado con subtotales y total
- [x] 12.2 Playwright contra la app real (uvicorn sobre la copia) a 390x844 y 1440x900, comparando con N1 y L1: resumen en vivo al tipear y al quitar líneas, importes con miles/centavos y errores, servicio general con/sin precio, servicios adicionales con un precio por línea (uno vacío) y repetido, todos los datos del cliente vacíos, solo egreso, egreso anterior al ingreso, "Fecha" igual que hoy; `/ordenes` con orden nueva y vieja; capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos inesperados
- [x] 12.3 Impresión: `print` emulado y `page.pdf` (A4) de una orden con datos y precios y otra vieja, comparando con P1
- [x] 12.4 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar la KB 02, 04, 05, 06 y 07 (ver design § Open Questions) y `CHANGES.md` (C-06h `[x]` con fecha; paridad C-07 de design D16).
- Esperar "Continuar" del usuario antes de proponer C-06i (`paso-5i-modificar-ordenes-checkeo`).
