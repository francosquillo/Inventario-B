# Tasks

> **GATE: el apply NO empieza hasta que `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`** (las decisiones 1-14 ya fueron revisadas por el usuario el 2026-11-24: ver `design.md` § Decisiones revisadas por el usuario). Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). Las funciones puras de JS se prueban con Node desde `unittest` (patrón de `tests/test_validacion_js.py`, se omiten sin Node); el resto del frontend tiene guardas estáticas; el comportamiento en el navegador se verifica en el grupo 10 contra los escenarios de `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorio y service con SQLite real `:memory:` (regla dura 4).
> - Sin dependencias nuevas; `requirements.txt` y `requirements-dev.txt` intactos (regla dura 1).
> - Sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - Fechas validadas en frontend Y backend (regla dura 3); sin cambios de esquema.
> - `tokens.css` y `ui.css` intactos (copias del design system); CSS nuevo, si hiciera falta, solo en `static/css/app.css`.
> - En JS: datos solo con `textContent`/`createElement`; nada de `innerHTML`.
> - Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups en `openspec/changes/paso-5d-reporte-ordenes-fechas/mockups/` (`reportes.html` que importa `design-system/tokens.css` y `ui.css`, cabecera de texto "Inventario" con las tres pestañas, tema oscuro único, README con estados y `Approval: pending`) cubriendo R0, N1, R1-R9, P4 y P5 (design § UI Mockups). Hecho cuando el README lista cada estado con su archivo
- [x] 0.2 Renderizar los estados de pantalla a 390x844 y 1440x900 y los de impresión (P4-P5) con `print` emulado y como PDF A4 de muestra, con Playwright; guardar en `mockups/previews/`, inspeccionar (sin scroll horizontal a 390 px) y registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar que `node` está disponible (si no, los tests de JS puro se omiten: avisarlo y cubrir esos casos en el verify con `browser_evaluate`)

## 2. Repositorio — spec `reporte-ordenes` (design D2)

- [x] 2.1 RED (`tests/test_sqlite_reporte_repository.py`, nuevo, SQLite `:memory:` con `inicializar_esquema`): dos órdenes en noviembre con `A-01` x3 + `B-02` x1 y `A-01` x2 → `productos_en_ordenes(date(2026,11,1), date(2026,11,30), None)` devuelve `ProductoEnOrdenes("A-01", "Tornillo", True, 5, 2)` y `("B-02", …, 1, 1)`; verificar rojo (no existe el método ni la entidad)
- [x] 2.2 GREEN: `ProductoEnOrdenes` en `domain/entities.py`, método abstracto en `OrdenRepository` (`repositories/base.py`, docstring con la nota de `COUNT(*)` = órdenes por la PK) e implementación SQL en `SqliteOrdenRepository` (JOIN + `GROUP BY` + `ORDER BY cantidad DESC, p.codigo`, solo placeholders). Verificar verde
- [x] 2.3 TRIANGULATE: bordes inclusivos (1 y 30 entran, 1 de diciembre no); un solo día; orden por cantidad desc y empate por código; filtro por código; código sin uso o inexistente → `[]`; sin órdenes → `[]`; producto dado de baja → `activo=False` con su total; filtro por el código de un dado de baja → solo su fila con el total del rango; orden sin componentes de otros productos no suma. Cada caso visto en rojo o anotado por qué pasa
- [x] 2.4 RED→GREEN→TRIANGULATE `productos_usados()` (`ProductoUsado` en `domain/entities.py`, método abstracto + SQL `SELECT DISTINCT … ORDER BY p.codigo`): `A-01` activo usado en dos órdenes y `C-99` dado de baja usado → `[A-01 (True), C-99 (False)]` sin duplicados; `B-02` nunca usado excluido; sin órdenes → `[]`; producto solo de una orden borrada excluido
- [x] 2.5 TRIANGULATE: solo lectura — conteos y contenido de `productos`, `ordenes`, `orden_items` y `movimientos` idénticos antes y después de consultar el reporte y los productos usados
- [x] 2.6 REFACTOR; suite verde

## 3. Service — spec `reporte-ordenes` (Validación de fechas, Filtro por un producto) (design D2)

- [x] 3.1 RED (`tests/test_reporte_service.py`, nuevo, con `SqliteOrdenRepository` sobre `:memory:`): `ReporteService(repo, ahora=<fijo 2026-11-24T10:00-03:00>).productos_en_ordenes(None, "2026-11-30")` lanza `DatosInvalidos("La fecha 'desde' es obligatoria.")`; verificar rojo
- [x] 3.2 GREEN: `inventario/services/reporte_service.py` (sin FastAPI) con `ahora` inyectable (`ahora_argentina` por defecto), obligatoriedad de `desde`, `parsear_filtro_fecha`, `validar_rango`, `normalizar_codigo` y delegación al repositorio. Verificar verde
- [x] 3.3 TRIANGULATE: `desde` en blanco → obligatoria; `hasta` ausente y en blanco → se consulta hasta hoy (`ahora` fijo: órdenes del 2026-11-24 entran, del 2026-11-25 no); `desde` `2026-12-01` sin `hasta` → "La fecha 'desde' (2026-12-01) no puede ser posterior a 'hasta' (2026-11-24)."; `hasta` `2026-02-30` inválido; formato `01/11/2026`; `2026-02-30`; rango invertido con el mensaje exacto; rango 2020-01-01..2026-12-31 aceptado; ` a-01 ` → filtra `A-01`; `"   "` → sin filtro; código de 51 caracteres → `DatosInvalidos` con el mensaje de largo; `productos_usados()` delega al repositorio
- [x] 3.4 REFACTOR; suite verde

## 4. API — spec `api-http` (Reporte por API, Errores, Documentación) (design D1)

- [x] 4.1 RED (`tests/test_api_reportes.py`, nuevo, `TestClient` + `sembrar`): sin sesión `GET /api/reportes/productos-en-ordenes?desde=2026-11-01&hasta=2026-11-30` → 401; con sesión y dos órdenes → 200 con la lista exacta (`codigo`, `nombre`, `activo`, `cantidad`, `ordenes`); verificar rojo (404)
- [x] 4.2 GREEN: `ProductoEnOrdenesOut` + `producto_en_ordenes_out` en `api/schemas.py`, `get_reporte_service` en `api/dependencies.py`, router `inventario/api/routers/reportes.py` (`dependencies=[Depends(get_current_user)]`, parámetros `Optional[str]`, `responses={422: ErrorOut}`) e `include_router` en `api/app.py`. Verificar verde
- [x] 4.3 TRIANGULATE: sin sesión y sin parámetros → 401 (no 422); `codigo=b-02` → solo `B-02`; dado de baja con `activo: false`; `codigo=c-99` (dado de baja) → solo su fila; `[]` sin órdenes; `codigo=ZZ-99` → `[]`; sin `hasta` → mismo resultado que con `hasta` = hoy; 422 con `detail` en español (falta `desde`, formato, invertido, `desde` futuro sin `hasta`); la base no cambia tras consultar
- [x] 4.4 RED→GREEN `GET /api/reportes/productos-usados`: 401 sin sesión; 200 con `[{"codigo", "nombre", "activo"}]` ordenado por código (activo y dado de baja usados, nunca usado excluido); `[]` sin órdenes; `ProductoUsadoOut` + `producto_usado_out`
- [x] 4.5 RED→GREEN: OpenAPI con las 15 rutas, `GET` único con `desde`, `hasta`, `codigo` en `/api/reportes/productos-en-ordenes` y `GET` único en `/api/reportes/productos-usados` (actualizar las aserciones de 13 rutas en `tests/test_api_app.py` y donde se cuenten); ninguna ruta de página en el esquema
- [x] 4.6 RED→GREEN (`tests/test_api_paginas.py`): `GET /reportes` 200 `text/html` con sesión, 303 a `/` sin sesión, cabeceras de seguridad, HTML sin `A-01`/`Tornillo`; ruta en `api/routers/paginas.py` sirviendo `static/reportes.html` (crear el archivo mínimo aquí)
- [x] 4.7 REFACTOR; suite completa verde

## 5. JS puro del reporte y nombre de archivo — specs `interfaz-web`, `exportacion-pdf` (design D3, D4)

- [x] 5.1 RED (`tests/test_reportes_js.py`, nuevo, Node): `Reporte.rangoPorDefecto(new Date(2026, 10, 24))` → `{desde: "2026-11-01", hasta: "2026-11-24"}`; verificar rojo (no existe `static/js/reportes.js`)
- [x] 5.2 GREEN: funciones puras de `static/js/reportes.js` en `window.Reporte` sin tocar el DOM al cargarse. Verificar verde
- [x] 5.3 TRIANGULATE: `rangoPorDefecto` el 1 de enero y el 31 de diciembre; `parametros` sin `hasta` ni `codigo` vacíos; `hastaEfectivo("", new Date(2026, 10, 24))` → `2026-11-24` y `hastaEfectivo("2026-10-31", …)` → `2026-10-31`; `gruposProductos(productosUsados)` separa por `activo` en "Activos" y "Dados de baja", ordena por código y omite el grupo vacío; `etiquetaProducto` encuentra un código de cualquiera de los dos grupos; `lineaEncabezado` ("· 5 productos", "· 1 producto", con "A-01 · Tornillo · " delante); `mensajeVacio` con y sin producto (con el `hasta` efectivo); `nombreArchivo` → `reporte-2026-11-01_2026-11-24`, `reporte-A-01-2026-11-01_2026-11-24` (desde `A/01`)
- [x] 5.4 RED (`tests/test_exportar_js.py`): `Exportar.limpiarArchivo("reporte-A-01-2026-11-01_2026-11-24")` conserva `_`; caracteres raros → `-` colapsado; `nombreArchivo("inventario", …)` sigue igual; guarda estática: `imprimir` usa `opciones.archivo` si viene. Verificar rojo
- [x] 5.5 GREEN: `limpiarArchivo` y el parámetro opcional `archivo` en `Exportar.imprimir` (compatible: sin `archivo` el comportamiento de C-06c no cambia). Verificar verde; REFACTOR

## 6. Navegación — spec `interfaz-web` (Cabecera y cierre de sesión) (mockup N1) (design D3)

- [x] 6.1 RED (guardas en `tests/test_frontend_estatico.py`): `index.html`, `ordenes.html` y `reportes.html` tienen `a.navlink[href="/reportes"]` "Reportes" y exactamente una `aria-current="page"` (la propia). Verificar rojo
- [x] 6.2 GREEN: pestaña "Reportes" en las tres páginas según N1. Verificar verde y que las guardas existentes de cabecera siguen verdes

## 7. Pantalla `/reportes` — spec `interfaz-web` (Pantalla, Estado inicial, Selector, Estados, Validación) (mockups R0-R9) (design D3)

- [x] 7.1 RED (guardas): `reportes.html` carga `validacion.js`, `api.js`, `ui.js`, `sesion.js`, `exportar.js`, `reportes.js`; tiene `#print-head` `print-only`, `#r-desde`/`#r-hasta` `type="date"` y `#r-producto` con `label` asociado, "Generar", `#btn-exportar-rep` "Exportar PDF", `#rep-inicial` visible con "Elegí el período y pulsá «Generar» para ver el reporte.", "Exportar PDF" `disabled` de inicio, `#rep-cargando`, `#rep-error` con "Reintentar", `#rep-vacio` oculto y la tabla `tbl`; `reportes.js` crea `optgroup` con "Activos" y "Dados de baja"; `reportes.js` sin `innerHTML`, usa `/api/reportes/productos-en-ordenes`, `/api/reportes/productos-usados` (y no `/api/inventario` ni `/api/productos/inactivos`), `Validacion.rango`, y contiene "No hay productos usados en órdenes entre" y "Generando reporte". Verificar rojo
- [x] 7.2 GREEN: HTML completo según R1 (responsive como el mockup) y JS: campos precompletados con el mes en curso y estado inicial sin generar (decisión 3: no se llama al reporte hasta "Generar"), selector desde `GET /api/reportes/productos-usados` con `<optgroup>` "Activos" y "Dados de baja" (decisión 4; fallo tolerado: solo "Todos los productos"), validación en el navegador (Desde obligatorio, Hasta opcional, rango contra el `hasta` efectivo) con error bajo el campo y foco, envío sin `hasta` cuando está vacío, estados inicial/cargando/error/vacío/datos, tabla con "dado de baja", resumen y último reporte generado como estado. Verificar verde
- [x] 7.3 REFACTOR; suite completa verde (guardas globales: sin `innerHTML`, campos etiquetados, CSS idéntico al design system)

## 8. Exportación del reporte — spec `interfaz-web` (Exportar el reporte), `exportacion-pdf` (mockups P4-P5) (design D4)

- [x] 8.1 RED (guardas): `reportes.js` llama a `Exportar.imprimir` con `titulo` "Reporte de productos en órdenes", `archivo` y `modo: "reporte"`; `#rep-resumen` con `no-print`; "Exportar PDF" se deshabilita en inicial/cargando/error/0 filas. Verificar rojo
- [x] 8.2 GREEN: botón conectado al último reporte generado (`lineaEncabezado`, `nombreArchivo`, ambos con el `hasta` efectivo); sin CSS nuevo salvo defecto visto en el verify. Verificar verde

## 9. Documentación local

- [x] 9.1 `README.md`: sección "Reporte de productos en órdenes" (pantalla `/reportes`, Desde obligatorio y Hasta opcional = hoy, mes precompletado y "Generar", filtro por producto usado, exportar a PDF) y los dos endpoints nuevos en la lista de la API. Hecho cuando el README lo describe

## 10. Verify

- [x] 10.1 Suite completa verde (baseline + tests nuevos); `openspec validate paso-5d-reporte-ordenes-fechas --strict` sin errores
- [x] 10.2 `/docs`: ejecutar el reporte con y sin `codigo` y sin `hasta`, `productos-usados`, y un 422 de rango invertido, con la cookie de sesión
- [x] 10.3 Playwright contra la app real (uvicorn + base temporal con ~15 productos, uno dado de baja con consumo, ~10 órdenes en dos meses) a 390x844 y 1440x900, comparando con R0, N1 y R1-R9 (apertura sin pedido del reporte, selector solo con usados, filtrar por el producto dado de baja y ver su total, Hasta vacío): capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos, pedidos a la API con los parámetros esperados
- [x] 10.4 Impresión: con `window.print` stubeado comprobar título `reporte-AAAA-MM-DD_AAAA-MM-DD` (también con Hasta vacío → hoy) y restauración tras `afterprint`; con `print` emulado y `page.pdf` (A4) comparar con P4-P5 (hoja clara, sin filtros ni nav, encabezado mínimo, encabezado de tabla repetido)
- [x] 10.5 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Confirmar que la sincronización de C-06c a `openspec/specs/` (`exportacion-pdf`, `interfaz-web`, hoy en el árbol de trabajo) sigue en su lugar antes de archivar esta change (design § Open Questions).
- Al archivar: actualizar la KB 06 (US-014 Reporte de productos usados en órdenes) y 07 (flujo del reporte y su exportación); en `CHANGES.md` marcar `[x]` C-06d con la fecha y anotar en C-07 las funciones RPC `productos_en_ordenes(p_desde, p_hasta, p_codigo)` y `productos_usados()`.
- Esperar "Continuar" del usuario antes de proponer C-06e (`paso-5e-categorias-productos`).
