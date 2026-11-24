# Design — paso-5d-reporte-ordenes-fechas (C-06d)

## Context

Ver `proposal.md` (Why). Estado actual observado (C-01..C-06c archivados):

- **Datos**: `ordenes(id, numero UNIQUE, fecha TEXT 'AAAA-MM-DD', usuario_id, created_at)`, `orden_items(orden_id, producto_id, cantidad > 0, PK(orden_id, producto_id))` y `productos(id, codigo UNIQUE, nombre, stock, activo 0/1)`. Las líneas de una orden ya llegan consolidadas (RN-OR-11), así que un producto aparece **a lo sumo una vez por orden**: `COUNT(*)` por producto = cantidad de órdenes. La baja de producto es lógica (`activo = 0`): el producto sigue existiendo y sus `orden_items` también.
- **Patrón backend**: router fino (`inventario/api/routers/*.py`) → service (valida y normaliza; sin FastAPI) → repositorio (`repositories/base.py` ABC + `sqlite_repo.py`). `DatosInvalidos` → 422 por el manejador de `api/app.py` con el formato uniforme de C-06b (`errores_validacion.py`). Fechas: `services/fechas.py` (`parsear_fecha`, `parsear_filtro_fecha`, `validar_rango`); código: `services/normalizacion.normalizar_codigo` (recorte + mayúsculas, máx. 50). `GET /api/movimientos` es el análogo más cercano (filtros `codigo/desde/hasta` como query, código inexistente → `[]`).
- **Páginas**: `api/routers/paginas.py` sirve `/inventario` y `/ordenes` con `usuario_de_sesion` (303 a `/` sin sesión) y `CABECERAS_PAGINA`; la navegación es `<nav aria-label="Secciones">` con `a.navlink` y `aria-current="page"` en `index.html` y `ordenes.html`.
- **No existe `GET /api/productos`** de activos: los activos salen de `GET /api/inventario` y los dados de baja de `GET /api/productos/inactivos`.
- **PDF (C-06c)**: `static/js/exportar.js` expone `Exportar.fecha`, `Exportar.nombreArchivo(base, date)` (base saneada `[^A-Za-z0-9]+ → -` + `-AAAA-MM-DD` de hoy) e `Exportar.imprimir({titulo, linea, base, modo, alRestaurar})`, que llena `#print-head`, pone `body[data-exportando]`, cambia y restaura `document.title` y llama a `window.print()`. `static/css/app.css` ya tiene el bloque `@media print` (papel claro; oculta `.no-print`, `.btn`, `input`, `select`, overlays; `#print-head` solo con `data-exportando`).
- **Validación JS**: `static/js/validacion.js` (`requerido`, `fecha`, `rango`) ya la usa `/ordenes`.
- **Hallazgo**: las deltas de C-06c no estaban sincronizadas en `openspec/specs/` al proponer; luego se sincronizaron en el árbol de trabajo (ver Open Questions).

## Goals / Non-Goals

**Goals:**
- Un endpoint de solo lectura, agregado en SQL, portable a Postgres/Supabase en C-07.
- Pantalla `/reportes` simple, coherente con `/ordenes` (filtros arriba, tabla, estados) y con el design system Revision 2.
- Reutilizar el PDF de C-06c con una extensión mínima (nombre de archivo explícito).

**Non-Goals:**
- Otros reportes (movimientos, stock valorizado, consumo por usuario), gráficos, totales en unidades mezcladas, exportación CSV/Excel.
- Paginación del reporte, comparación entre períodos, agrupación por semana/mes.
- Cambios de esquema o índices nuevos (el volumen de un taller chico no lo pide; ver Risks).

## Decisions

### D1 — Endpoints y forma de la respuesta (decisiones 1, 2, 4, 9, 10)

`GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=` (`desde` obligatorio; `hasta` opcional = hoy en Argentina; decisión 2) en un router nuevo `inventario/api/routers/reportes.py` (`prefix="/api/reportes"`, `tags=["reportes"]`, `dependencies=[Depends(get_current_user)]` como movimientos, así el 401 gana al 422). Parámetros declarados `Optional[str] = None` en FastAPI para que la obligatoriedad de `desde` la valide el service con mensajes propios en español (FastAPI daría su 422 genérico). Respuesta `List[ProductoEnOrdenesOut]` con `codigo`, `nombre`, `activo`, `cantidad`, `ordenes`. Lista JSON plana (sin envoltorio `{desde, hasta, filas}`): igual que las demás consultas; el rango ya lo conoce quien pregunta (con `hasta` vacío, la web muestra su fecha local de hoy; ver Risks).

`GET /api/reportes/productos-usados` (decisión 4, mismo router y misma protección): sin parámetros; respuesta `List[ProductoUsadoOut]` con `codigo`, `nombre`, `activo`, ordenada por código. Alimenta el selector de producto con **solo** los productos que aparecen en al menos una orden (de cualquier fecha), activos y dados de baja. Es el enfoque más simple: una consulta `DISTINCT` sin parámetros, sin acoplar el selector al rango (reutilizar el endpoint del reporte sin rango obligaría a hacer `desde` opcional o a usar una fecha centinela, y devolvería agregados que el selector no necesita).

**Alternativa descartada**: `GET /api/ordenes/reporte` (choca con `DELETE /api/ordenes/{numero:path}` y mezcla recursos) o un envoltorio con totales (sumar unidades de productos distintos no tiene sentido).

### D2 — Dominio, repositorio y service

- `domain/entities.py`: `@dataclass(frozen=True) class ProductoEnOrdenes: codigo, nombre, activo, cantidad, ordenes` y `@dataclass(frozen=True) class ProductoUsado: codigo, nombre, activo`.
- `repositories/base.py`: método nuevo en `OrdenRepository` (mismas tablas):
  `productos_en_ordenes(desde: date, hasta: date, codigo: str | None) -> list[ProductoEnOrdenes]` — fechas ya validadas (`hasta` ya resuelto), código ya normalizado; y
  `productos_usados() -> list[ProductoUsado]`.
- `sqlite_repo.py`:
  ```sql
  SELECT p.codigo, p.nombre, p.activo,
         SUM(i.cantidad) AS cantidad, COUNT(*) AS ordenes
  FROM orden_items i
  JOIN ordenes o   ON o.id = i.orden_id
  JOIN productos p ON p.id = i.producto_id
  WHERE o.fecha >= ? AND o.fecha <= ? [AND p.codigo = ?]
  GROUP BY p.id, p.codigo, p.nombre, p.activo
  ORDER BY cantidad DESC, p.codigo
  ```
  ```sql
  SELECT DISTINCT p.codigo, p.nombre, p.activo
  FROM orden_items i JOIN productos p ON p.id = i.producto_id
  ORDER BY p.codigo
  ```
  (la segunda, para `productos_usados`; al borrar una orden se borran sus `orden_items`, así que un producto solo usado en órdenes borradas deja de figurar). Comparación de texto `AAAA-MM-DD` (el `CHECK` de `ordenes.fecha` garantiza el formato), igual que `listar`. Solo placeholders `?`. `COUNT(*)` vale como cantidad de órdenes por la PK `(orden_id, producto_id)`; se documenta en el docstring (en Postgres se escribe `COUNT(DISTINCT o.id)` por claridad, mismo resultado).
- `services/reporte_service.py` (nuevo, `ReporteService(orden_repo, ahora=ahora_argentina)`, fuente de tiempo inyectable como `OrdenService`/`StockService`): `productos_en_ordenes(desde, hasta=None, codigo=None)`:
  1. `desde` obligatorio: `None` o `""` (tras `strip`) → `DatosInvalidos("La fecha 'desde' es obligatoria.")`.
  2. `parsear_filtro_fecha` para ambos (mismos mensajes de formato/inexistente). `hasta` ausente o vacío → `self._ahora().date()` (hoy en UTC-03:00; decisión 2); el texto usado en el mensaje de rango es entonces esa fecha ISO.
  3. `validar_rango(desde, texto_hasta_efectivo, f_desde, f_hasta)` → "La fecha 'desde' (2026-12-01) no puede ser posterior a 'hasta' (2026-11-24)."
  4. `codigo`: `None`/blanco → sin filtro; si no, `normalizar_codigo` (incluye el 422 por largo > 50).
  5. Delega al repositorio. Sin chequeo de existencia del código (decisión 10).
  - `productos_usados()`: delega al repositorio (sin validaciones).
- `api/dependencies.py`: `get_reporte_service(conn)` → `ReporteService(SqliteOrdenRepository(conn))`. `api/schemas.py`: `ProductoEnOrdenesOut` + `producto_en_ordenes_out`, `ProductoUsadoOut` + `producto_usado_out`. `api/app.py`: `include_router(reportes.router)`.

### D3 — Pantalla `/reportes` (decisiones 1-8, 11)

- `paginas.py`: `GET /reportes` igual que `/ordenes` → `static/reportes.html`.
- Navegación: pestaña "Reportes" (`a.navlink href="/reportes"`) en `index.html`, `ordenes.html` y `reportes.html` (en esta con `aria-current="page"`). A 390 px las tres pestañas entran en la fila de navegación existente (`order-last w-full`).
- `reportes.html` (estructura como `ordenes.html`): cabecera común, `#print-head`, `<h1>Reportes</h1>`, sección "Productos usados en órdenes" con `form#form-reporte` (`novalidate`): `#r-desde` (obligatorio), `#r-hasta` (opcional, ayuda "Vacío = hoy") (`type="date"`, `label` asociados; rótulos "Desde (obligatorio)" y "Hasta (opcional)", decidido por el usuario al aprobar mockups, 2026-11-24), `#r-producto` (`<select>`: primera opción "Todos los productos" con valor vacío; luego, con los datos de `GET /api/reportes/productos-usados` (solo productos usados en alguna orden; decisión 4), `<optgroup label="Activos">` y `<optgroup label="Dados de baja">`, cada opción "CÓDIGO · Nombre" ordenada por código dentro de su grupo — mismo patrón que el selector de "Modificar stock" de C-06b, sin el stock porque no aporta al reporte; un grupo vacío no se muestra), botones "Generar" (`btn-primary`, submit) y "Exportar PDF" (`btn-secondary`, `#btn-exportar-rep`). Debajo: línea de resumen `#rep-resumen` (mismo formato que el PDF: "AAAA-MM-DD a AAAA-MM-DD · N productos", con "CÓDIGO · Nombre · " delante si se filtró; decidido por el usuario al aprobar mockups, 2026-11-24; el mockup R1/R9 muestra el orden inverso y queda superado), estados `#rep-inicial` (cartel neutro "Elegí el período y pulsá «Generar» para ver el reporte.", visible al abrir; decisión 3), `#rep-cargando` ("Generando reporte…"), `#rep-error` (con "Reintentar"), `#rep-vacio` y la tabla `table.tbl-rep` (Código, Nombre, Cantidad, Órdenes, en ese orden por decisión del usuario al aprobar mockups, 2026-11-24; números alineados a la derecha con `num`). Marca de baja: `<span class="badge">dado de baja</span>` en la celda del nombre (texto, no solo color) — mismo patrón visual que el resto de la app para productos dados de baja.
- `static/js/reportes.js`:
  - Funciones **puras** expuestas en `window.Reporte` (testeables con Node): `rangoPorDefecto(date)` → `{desde: "AAAA-MM-01", hasta: "AAAA-MM-DD"}`; `parametros(desde, hasta, codigo)` → `URLSearchParams` sin `hasta` ni `codigo` vacíos; `hastaEfectivo(hasta, date)` → `hasta` o la fecha local de hoy; `gruposProductos(productosUsados)` → separa por `activo` en `[{grupo: "Activos", opciones}, {grupo: "Dados de baja", opciones}]` ordenados por código, sin grupos vacíos, cada opción `{codigo, etiqueta: "CÓDIGO · Nombre"}`; `etiquetaProducto(codigo, grupos)` para el encabezado y el cartel vacío; `lineaEncabezado(filas, desde, hasta, productoEtiqueta)` → "2026-11-01 a 2026-11-24 · 5 productos" / "A-01 · Tornillo · … · 1 producto"; `mensajeVacio(desde, hasta, productoEtiqueta)`; `nombreArchivo(desde, hasta, codigo)` → `reporte-[<codigo>-]AAAA-MM-DD_AAAA-MM-DD`.
  - Arranque: rango por defecto en los campos (Desde = día 1 del mes, Hasta = hoy), estado `inicial` (cartel neutro, sin tabla, "Exportar PDF" deshabilitado) y **no** se pide el reporte (decisión 3). Solo `GET /api/reportes/productos-usados` para el selector (si falla, queda solo "Todos los productos" y un aviso discreto; el reporte se genera igual).
  - "Generar": valida Desde con `Validacion.requerido(valor, "La fecha")` y `Validacion.fecha`; Hasta con `Validacion.fecha` solo si no está vacío; el rango con `Validacion.rango(desde, hastaEfectivo(hasta, new Date()))` (error bajo Hasta, o bajo Desde si Hasta está vacío) (`UI.errorBajoCampo`, `aria-invalid`, foco), y pide el reporte sin `hasta` cuando está vacío. Guarda el **último reporte generado** (`{desde, hasta: hastaEfectivo, codigo, etiqueta, filas}`); el resumen, el cartel vacío y la exportación usan ese estado, no los campos (decisión 11).
  - Datos con `textContent`/`createElement` (sin `innerHTML`). 401 → `/?sesion=expirada` vía `api.js` como el resto.
- **Sin límite de rango** (decisión 8): un rango de años es una sola consulta agregada que devuelve, como mucho, una fila por producto.

### D4 — Exportación a PDF (decisión 12)

- `exportar.js`: `imprimir` acepta opcionalmente `archivo` (nombre completo ya armado). Si viene, `document.title = limpiarArchivo(archivo)`; si no, sigue `nombreArchivo(base, new Date())` (inventario y orden sin cambios). Función pura nueva `limpiarArchivo(texto)`: `[^A-Za-z0-9_-]+ → -`, guiones repetidos colapsados, sin `-` en los bordes. El código de producto se sanea antes con la regla de C-06c (`[^A-Za-z0-9]+ → -`) dentro de `Reporte.nombreArchivo`, así `A/01` → `A-01` y el `_` solo aparece como separador del rango.
- `reportes.js` → `Exportar.imprimir({ titulo: "Reporte de productos en órdenes", linea: Reporte.lineaEncabezado(...), archivo: Reporte.nombreArchivo(...), modo: "reporte" })`. Encabezado mínimo como el aprobado en C-06c: título + una línea; sin usuario, hora ni "Creada por".
- `app.css`: el `@media print` existente ya oculta filtros (`input`, `select`, `.btn`, `.no-print`), navegación y cabecera, y sus reglas de tabla son genéricas sobre `.tbl` (`thead` repetido, `tr` sin partir, `.badge` en texto negro), así que la tabla del reporte usa `class="tbl tbl-rep"` y **no necesita CSS nuevo**; el resumen `#rep-resumen` lleva `no-print` (ya va en el encabezado). Solo se agrega CSS si el verify muestra un defecto.
- La línea del encabezado y el nombre de archivo usan el `hasta` efectivo guardado del último reporte (hoy si quedó vacío).
- "Exportar PDF" deshabilitado en el estado inicial, cargando, error y 0 filas (requisito de C-06c "Exportación deshabilitada sin datos").

### D5 — Paridad Supabase (C-07) (decisión 13)

La consulta de D2 es SQL estándar (JOIN + GROUP BY + ORDER BY), portable tal cual a PostgreSQL. PostgREST no expone `GROUP BY`/`SUM` sin habilitar agregados, así que en C-07 se implementa como **función RPC** `productos_en_ordenes(p_desde date, p_hasta date, p_codigo text default null)` `returns table(codigo, nombre, activo, cantidad, ordenes)` `language sql stable`, con `SECURITY INVOKER` y las mismas reglas de RLS que el resto. Ídem `productos_usados()` `returns table(codigo, nombre, activo)` (`SELECT DISTINCT … ORDER BY codigo`; alternativa equivalente: una vista o el embebido `productos?select=codigo,nombre,activo,orden_items!inner(producto_id)`, a elegir en C-07). El `hasta` efectivo se resuelve en el service (Python), no en SQL, así la RPC recibe siempre ambas fechas. El repositorio Supabase llama `rpc("productos_en_ordenes", …)` y `rpc("productos_usados")`; el service y los tests de API no cambian. Se anotan ambas RPC en `CHANGES.md` § C-07 al archivar.

### D6 — Tests (Strict TDD, `unittest`, SQLite real)

- `tests/test_sqlite_reporte_repository.py` (nuevo, `:memory:`): suma de varias órdenes, conteo de órdenes, bordes inclusivos, un día, fuera de rango excluido, orden cantidad desc + código, empate por código, filtro por código, código sin uso → `[]`, sin órdenes → `[]`, producto dado de baja con `activo=False` (y filtrado por su código), orden sin efectos (conteos de tablas idénticos antes/después); `productos_usados`: activos y dados de baja usados una sola vez cada uno, orden por código, nunca usados excluidos, sin órdenes → `[]`, producto de una orden borrada excluido.
- `tests/test_reporte_service.py` (nuevo, con repositorio SQLite real en memoria): `desde` faltante o en blanco, `hasta` ausente o vacío = hoy (con `ahora` fijo inyectado), `desde` futuro sin `hasta` → mensaje con la fecha de hoy, formato, fecha inexistente, rango invertido, rango de años aceptado, código normalizado (` a-01 ` → `A-01`), código en blanco → sin filtro, código > 50 → `DatosInvalidos`.
- `tests/test_api_reportes.py` (nuevo, `TestClient`): 401 sin sesión (con y sin parámetros), 200 con forma exacta de cada objeto, filtro, `[]`, sin `hasta` = hoy, 422 con `detail` en español (falta `desde`, formato, invertido, `desde` futuro sin `hasta`); `GET /api/reportes/productos-usados` (401, forma exacta, `[]`), sin cambios en la base; `GET /reportes` con y sin sesión (`test_api_paginas.py`), HTML sin datos; OpenAPI con 15 rutas y `GET` único en cada ruta nueva (`test_api_app.py`).
- `tests/test_reportes_js.py` (nuevo, Node, se omite sin Node): `rangoPorDefecto` (1 de enero, 31 de diciembre, relleno de ceros), `parametros` (sin `hasta` vacío), `hastaEfectivo`, `gruposProductos` (grupos "Activos"/"Dados de baja", orden por código, grupo vacío omitido), `lineaEncabezado` (singular/plural, con producto), `mensajeVacio`, `nombreArchivo` (con y sin código, `A/01`). `tests/test_exportar_js.py`: `limpiarArchivo` conserva `_`; `nombreArchivo` de C-06c intacto.
- `tests/test_frontend_estatico.py` (guardas): `reportes.html` existe, carga `validacion.js`, `api.js`, `ui.js`, `sesion.js`, `exportar.js` y `reportes.js`, tiene `#print-head`, campos etiquetados, botón "Exportar PDF"; las tres páginas protegidas tienen la pestaña "Reportes" y solo una `aria-current`; `#rep-inicial` visible y "Exportar PDF" `disabled` en el HTML inicial; `reportes.js` sin `innerHTML`, usa `/api/reportes/productos-en-ordenes` y `/api/reportes/productos-usados` (y no `/api/inventario` ni `/api/productos/inactivos`), `Exportar.imprimir` y `Validacion.rango`; `exportar.js` sigue sin `fetch`.
- Comportamiento en navegador: verify con Playwright (estados, móvil, impresión con `print` emulado y `window.print` stubeado).

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-24)
- Mockups: openspec/changes/paso-5d-reporte-ordenes-fechas/mockups/ (`reportes.html`, README, previews/)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24, 390x844 y 1440x900 + PDF A4 de P4-P5; previews/)
- Visual verify: passed (2026-11-24) — capturas en `mockups/verify/` (390x844 y 1440x900; estados R0-R9 y N1 en las 3 páginas; PDFs P4/P5 verificados por texto con pdftotext, sin render visual). Diferencia intencional: resumen "AAAA-MM-DD a AAAA-MM-DD · N productos" (decisión del usuario).

Base: mockups aprobados de C-06c (`openspec/changes/archive/2026-11-24-paso-5c-buscador-pdf/mockups/`) y de C-06 para la cabecera y los filtros de órdenes, mismos tokens (`design-system/tokens.css`, `ui.css`), cabecera de texto "Inventario", tema oscuro único. Estados previstos:

| ID | Pantalla | Estado |
|----|----------|--------|
| R0 | Reportes | Estado inicial: Desde 2026-11-01 y Hasta 2026-11-24 precompletados, cartel neutro "Elegí el período y pulsá «Generar» para ver el reporte.", sin tabla, "Exportar PDF" deshabilitado |
| N1 | Navegación | Cabecera con pestañas Inventario / Órdenes / Reportes (Reportes actual), a 390 px y 1440 px |
| R1 | Reportes | Mes en curso generado: 5 productos, uno "dado de baja", resumen "5 productos · 2026-11-01 a 2026-11-24", "Exportar PDF" habilitado |
| R2 | Reportes | Filtrado por un producto (`A-01 · Tornillo`): una fila |
| R3 | Reportes | Vacío: "No hay productos usados en órdenes entre 2026-10-01 y 2026-10-31", "Exportar PDF" deshabilitado |
| R4 | Reportes | Validación: rango invertido con error bajo Hasta (y variante Desde vacío) |
| R9 | Reportes | Generado con Hasta vacío: resumen "… · 2026-11-01 a 2026-11-24" (hoy) |
| R5 | Reportes | Generando: "Generando reporte…", botones deshabilitados |
| R6 | Reportes | Error de servidor con "Reintentar" |
| R7 | Reportes | Selector de producto con solo productos usados, en grupos "Activos" y "Dados de baja" (decisión del usuario) |
| R8 | Reportes | Filtrado por un producto dado de baja (`C-99 · Viejo`): una fila con la marca "dado de baja" |
| P4 | Impresión | Reporte del mes: "Reporte de productos en órdenes" + "2026-11-01 a 2026-11-24 · 5 productos", tabla clara sin filtros ni nav |
| P5 | Impresión | Reporte largo (≈60 filas) con encabezado de tabla repetido en cada página |

Pantallas a 390x844 y 1440x900; P4-P5 con `print` emulado y como PDF A4 de muestra en `mockups/previews/`. Estos mockups son criterio de aceptación de los grupos 6-8 de `tasks.md` y del verify.

## Risks / Trade-offs

- [Sin índice en `ordenes.fecha` ni en `orden_items.producto_id`, un rango de años recorre todas las órdenes] → para un taller chico (miles de órdenes) es instantáneo en SQLite; si crece, un índice `ordenes(fecha)` es un change aparte (no se toca el esquema acá).
- [El nombre mostrado de un producto es el actual, no el que tenía cuando se usó] → igual que en `/ordenes` (los ítems no guardan nombre); aceptado y documentado.
- [Un producto borrado físicamente no existiría] → no aplica: la baja es lógica y `orden_items.producto_id` tiene FK; el `JOIN` interno es seguro. Si C-07 cambiara eso, revisar el JOIN.
- [El usuario cambia las fechas y exporta sin pulsar "Generar"] → la exportación y el resumen usan el último reporte generado y su rango, que es lo que se ve en la tabla (escenario explícito en la spec).
- [Fecha por defecto en el borde de mes (día 1): rango de un solo día] → válido; muestra lo usado hoy.
- [Con Hasta vacío, el servidor usa hoy en UTC-03:00 y la web muestra la fecha local del navegador] → en el uso previsto (Argentina) coinciden; un navegador en otra zona podría mostrar otra fecha cerca de la medianoche. Aceptado (mismo supuesto que el resto de la app).
- [Un producto usado solo en órdenes luego borradas desaparece del selector] → coherente: ya no hay consumo que reportar.
- [El selector se carga una vez al abrir; una orden creada en otra pestaña no lo actualiza] → recargar la página; aceptado.
- [Selector con cientos de productos] → `<select>` nativo permite saltar tecleando el código (mismo criterio que C-06c D5).
- [`limpiarArchivo` y `nombreArchivo` divergen] → tests de ambos; el de C-06c no cambia.

## Migration Plan

Sin cambios de esquema ni de datos. Desplegar = reiniciar uvicorn. Rollback: quitar el router `reportes`, la ruta `/reportes`, la pestaña y los archivos nuevos; revertir el parámetro `archivo` de `exportar.js` (compatible hacia atrás).

## Open Questions

- **Sincronización de C-06c**: al proponer faltaban en `openspec/specs/` las deltas de C-06c; ya figuran en el árbol de trabajo (`openspec/specs/exportacion-pdf/` creado e `interfaz-web` con el buscador), sin commit. Las deltas de esta change no chocan con esos requisitos (`exportacion-pdf` solo `ADDED` con nombres nuevos; `interfaz-web` modifica "Cabecera y cierre de sesión", que C-06c no tocó).
- Al archivar, actualizar la KB: 06 (US-014 "Reporte de productos usados en órdenes": Desde obligatorio, Hasta opcional = hoy, generación manual con el mes precompletado, selector con solo productos usados, filtro por producto, totales y órdenes por producto, dados de baja incluidos, exportación a PDF) y 07 (flujo "Reporte de productos en órdenes" con validación, vacío y exportación); en `CHANGES.md` § C-07 anotar las RPC `productos_en_ordenes` y `productos_usados`.

## Decisiones revisadas por el usuario

> Governance MEDIO: las 14 decisiones fueron revisadas una por una por el usuario el 2026-11-24. El apply no empieza hasta que el usuario apruebe los mockups. ★ = la recomendada originalmente.

**Decidido por el usuario antes de la revisión (2026-11-24):** pantalla aparte (no una sección dentro de `/ordenes`); exportación a PDF reutilizando C-06c; el selector de producto incluye también los productos dados de baja (grupos "Activos" / "Dados de baja", como el selector de "Modificar stock" de C-06b) y en el resultado y el PDF un dado de baja lleva la marca de texto "dado de baja".

1. **Ruta y pestaña** — aprobada por el usuario (2026-11-24): ★ `/reportes`, pestaña "Reportes", sección "Productos usados en órdenes".
2. **Fechas** — **cambiada** por el usuario (2026-11-24): solo **Desde** es obligatorio; **Hasta** es opcional y vacío significa **hoy** (hora local de Argentina, UTC-03:00, como el resto de la app). La API acepta `hasta` opcional y responde 422 solo por `desde` faltante o inválido, `hasta` inválido o `desde` posterior al `hasta` efectivo. La web valida igual. El encabezado del PDF y el nombre de archivo usan el `hasta` efectivo. (Recomendación original: ambas obligatorias.)
3. **Valores por defecto** — **cambiada** por el usuario (2026-11-24): campos **precompletados** con el mes en curso (Desde = día 1, Hasta = hoy), pero el reporte **no** se genera al abrir: el usuario pulsa "Generar". Estado inicial: sin tabla, cartel neutro "Elegí el período y pulsá «Generar» para ver el reporte.", "Exportar PDF" deshabilitado (mockup R0). (Recomendación original: generar al abrir.)
4. **Selector de producto** — **cambiada** por el usuario (2026-11-24): lista **solo los productos usados en al menos una orden** (de cualquier fecha), incluidos los dados de baja, en grupos "Activos" / "Dados de baja" ordenados por código, sin grupos vacíos. Fuente: endpoint nuevo de solo lectura `GET /api/reportes/productos-usados` (D1/D2; C-07: RPC `productos_usados` o vista). (Recomendación original: todos los activos e inactivos.)
5. **Dados de baja en el resultado** — aprobada por el usuario (2026-11-24): ★ se incluyen con la marca "dado de baja".
6. **Orden de las filas** — aprobada por el usuario (2026-11-24): ★ cantidad total descendente, desempate por código.
7. **Columna "Órdenes"** — aprobada por el usuario (2026-11-24): ★ sí.
8. **Límite de rango** — aprobada por el usuario (2026-11-24): ★ sin límite.
9. **Semántica del rango** — aprobada por el usuario (2026-11-24): ★ inclusivo en ambos bordes sobre la fecha de la orden.
10. **`codigo` inexistente** — aprobada por el usuario (2026-11-24): ★ 200 con `[]`.
11. **Qué exporta el PDF** — aprobada por el usuario (2026-11-24): ★ el último reporte generado.
12. **Encabezado y nombre del PDF** — aprobada por el usuario (2026-11-24): ★ "Reporte de productos en órdenes" + "AAAA-MM-DD a AAAA-MM-DD · N productos" (con "CÓDIGO · Nombre · " si se filtró); archivo `reporte-AAAA-MM-DD_AAAA-MM-DD` / `reporte-<código>-AAAA-MM-DD_AAAA-MM-DD` (parámetro opcional `archivo` en `exportar.js`).
13. **Paridad C-07** — aprobada por el usuario (2026-11-24): ★ SQL estándar en el repositorio; RPC `productos_en_ordenes` (y `productos_usados`) en Supabase.
14. **Ubicación de la lógica** — aprobada por el usuario (2026-11-24): ★ métodos nuevos en `OrdenRepository` + `ReporteService` + router `/api/reportes`.
