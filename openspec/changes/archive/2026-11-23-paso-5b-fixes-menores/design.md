# Design — paso-5b-fixes-menores (C-06b)

## Context

Ver `proposal.md` (Why). Estado actual observado (C-01..C-06 archivados):

- **Esquema SQLite** (`inventario/repositories/sqlite_repo.py`, `ESQUEMA_SQL`): `movimientos(id, fecha, producto_id, tipo CHECK IN ('ingreso','egreso'), cantidad CHECK > 0, usuario_id)`; `productos.stock CHECK >= 0`. `inicializar_esquema` hace `executescript(ESQUEMA_SQL)` (todo `IF NOT EXISTS`, así que una tabla vieja **no** se actualiza) y luego normaliza fechas legadas. `dev-local.db` y cualquier base de C-01..C-06 tiene el CHECK viejo.
- **Stock** (`SqliteStockRepository`): `registrar_ingreso` (suma, alta con nombre o reactivación sumando) y `registrar_egreso`, cada uno en `_transaccion` (`BEGIN IMMEDIATE`, rollback ante cualquier excepción). `StockService` valida con `normalizar_codigo`, `validar_cantidad` (1..10.000) y `_normalizar_nombre` (recorte, ≤120, vacío → `None`).
- **Productos**: `ProductoRepository.listar_activos` (sin `ORDER BY`: orden de inserción) y `dar_de_baja`. Router `/api/productos/{codigo:path}` solo con `DELETE`.
- **Errores** (`app.py`): mapa excepción de dominio → status (`DatosInvalidos`/`NombreRequerido` 422, `ProductoNoEncontrado`/`ProductosNoEncontrados`/`OrdenNoEncontrada` 404, `StockInsuficiente`/`OrdenDuplicada` 409) y handler especial del 409 de órdenes con `faltantes`. `errores_validacion.py` traduce los 422 de Pydantic; prefija "Componente N: " cuando el `loc` cae en `componentes`.
- **Movimientos**: `MovimientoOut` con exactamente `fecha, codigo, nombre, tipo, cantidad, usuario`; el nombre sale del JOIN con `productos` (nombre **actual**).
- **Web** (`static/index.html`, `static/js/inventario.js`, `validacion.js`): modales `modal-ingreso`, `modal-egreso`, `modal-orden`, `modal-baja`; la nueva orden ya resuelve multi-línea (`nuevaLinea`, `renumerar`, `marcarLinea`, `mapearErrorOrden`). Guardas en `tests/test_frontend_estatico.py` fijan hoy los botones "Ingreso/Egreso de stock" y el uso de `/api/stock/ingreso|egreso` (tests `test_cabecera_y_acciones`, `test_aviso_de_codigo_nuevo_no_bloqueante`, `test_js_usa_los_endpoints_y_codifica_codigos`, `test_cuatro_modales_accesibles`).
- **OpenAPI**: `tests/test_api_app.py::DocsTest` y el test de C-06 fijan **diez** rutas `/api`.

## Goals / Non-Goals

**Goals:**
- Alta explícita con stock inicial >= 0 y modificación de stock en lote todo o nada, incluidas reactivaciones.
- Bitácora que distingue un **ajuste** (stock fijado) de un ingreso/egreso, sin romper los lectores existentes (`cantidad > 0` sigue valiendo para todas las filas).
- Migración de bases existentes sin pérdida, idempotente y atómica.
- Cero cambios en `POST /api/stock/ingreso|egreso`, órdenes, baja y login (sus tests no cambian aserciones).

**Non-Goals:**
- UI de movimientos, auditoría de cambios de nombre, control de concurrencia optimista, paridad Postgres implementada (va en C-07).
- Borrado físico de productos.

## Decisions

### D1 — Endpoints y contratos (decisiones 1, 2, 3)

| Método | Ruta | Cuerpo | Éxito | Errores |
|--------|------|--------|-------|---------|
| POST | `/api/productos` | `{codigo, nombre, stock}` | **201** `IngresoOut` (`codigo, nombre, stock, sin_stock, creado, reactivado`) | 409 código activo; 422 |
| GET | `/api/productos/inactivos` | — | 200 `list[ProductoOut]` ordenada por código | 401 |
| POST | `/api/stock/modificaciones` | `{lineas: [Linea]}` | 200 `{lineas: [LineaModificadaOut]}` | 404 `{detail, codigos}`; 422 |
| GET | `/api/movimientos` | — | + `stock_anterior`, `stock_nuevo` (null salvo `ajuste`) | igual |

- **`POST /api/productos`** en el router de productos (prefijo ya existente), reutiliza la forma `IngresoOut` (mismos campos que el ingreso: el cliente ya sabe leerla). 201 siempre, también al reactivar (★ decisión 2): el recurso "producto activo" se crea desde el punto de vista del inventario; `creado`/`reactivado` distinguen el caso.
- **`GET /api/productos/inactivos`** (★ decisión 3) en lugar de `GET /api/inventario?incluir_inactivos=true`: no toca el contrato ni la spec de `consulta-inventario` (que lista "exactamente" activos con la misma forma), no agrega un campo `activo` a una respuesta existente y es una consulta de una línea (`WHERE activo = 0 ORDER BY codigo`). La ruta GET se declara **antes** del `DELETE /{codigo:path}` del mismo router (con `:path` Starlette haría match parcial; declararla primero evita depender de eso). Un código literal `INACTIVOS` sigue pudiendo darse de baja: el `DELETE` no compite con un `GET`.
- **`POST /api/stock/modificaciones`** en el router de stock. Línea = unión discriminada por `modo` (Pydantic `Field(discriminator="modo")`, compact rule pydantic):
  - `LineaFijar {codigo: str 1..50 (strip), modo: Literal["fijar"], stock: int strict 0..10.000, nombre: str|None ≤120 (strip)}`
  - `LineaSumar {codigo, modo: Literal["sumar"], cantidad: Cantidad (1..10.000), nombre}`
  - `ModificacionRequest {lineas: List[Linea] 1..100}`; `strict=True`, `extra` por defecto (ignorado), igual que los modelos actuales.
  - Nombres de campo distintos (`stock` vs `cantidad`) para que el mensaje del 422 dependa del campo y no del modo, y para que "Sumar" se lea igual que en ingreso/orden.
- **`LineaModificadaOut`**: `codigo, nombre, stock, sin_stock, modo, stock_anterior, nombre_anterior, reactivado` (en el orden recibido). `nombre_anterior` siempre presente (igual a `nombre` si no cambió) → el cliente compara para el resumen.
- **404 de la modificación**: excepción nueva `ProductosInexistentes(codigos)` (no se reutiliza `ProductosNoEncontrados` porque su texto dice "activo", falso aquí): "No existe un producto con código 'X'." / "No existen productos con código: 'X', 'Y'." + handler que agrega `codigos` al cuerpo (mismo patrón que `faltantes`). El cliente marca líneas por `codigos`, sin parsear comillas (más robusto que el mapeo de la orden). Con el selector de la web este 404 es prácticamente inalcanzable (no hay borrado físico); es defensa para `/docs` y clientes futuros.
- **409 del alta**: excepción nueva `ProductoDuplicado(codigo)` → "Ya existe un producto con código 'X'." (comillas simples como el resto de los mensajes) mapeada a 409 en `app.py`.

### D2 — Reglas de la modificación (decisiones 4-9)

Validación en `StockService.modificar(lineas, usuario_id)` (el service mantiene su propia validación, como `OrdenService._consolidar`; la recibe como lista de `LineaModificacion(codigo, modo, valor, nombre)` del dominio; el router convierte desde Pydantic):

1. Lista: `None`/no lista/vacía → "La modificación requiere al menos una línea."; > 100 → "La modificación admite hasta 100 líneas." (★ decisión 6: mismo tope que la orden).
2. Por línea, en orden, con prefijo `"Línea N: "` (N desde 1): código (`normalizar_codigo`), modo ∈ {fijar, sumar} ("El campo modo debe ser fijar o sumar."), valor (`fijar`: `validar_stock` 0..10.000 → "El stock debe ser un entero entre 0 y 10.000."; `sumar`: `validar_cantidad`), nombre (`_normalizar_nombre`).
3. Repetidos tras normalizar (★ decisión 5): "Línea N: el producto 'X' ya está en la línea M." — se rechaza en lugar de consolidar porque "fijar 3 + sumar 2" depende del orden y "fijar 3 + fijar 5" es ambiguo; la web además deshabilita en cada selector los productos ya elegidos.
4. Repositorio (`StockRepository.modificar`, una transacción `BEGIN IMMEDIATE`): lee todos los productos por código (activos e inactivos); si falta alguno → `ProductosInexistentes` con todos los faltantes en orden de aparición; luego aplica cada línea.

Semántica por línea (sobre el producto leído dentro de la transacción):

| Caso | Producto | Movimiento |
|------|----------|------------|
| `fijar` con stock distinto | `stock = valor` | `ajuste` (`stock_anterior`, `stock_nuevo`, `cantidad = |nuevo − anterior|`) |
| `fijar` con el mismo stock (★ decisión 4) | sin cambio de stock | ninguno |
| `sumar` | `stock = stock + valor` | `ingreso` con `cantidad = valor` (★ decisión 7) |
| nombre distinto del actual | `nombre = nuevo` | ninguno (★ decisión 8) |
| producto inactivo | `activo = 1` solo si el stock cambia y queda > 0 (decisión 9, del usuario: `fijar 0`, mismo stock o solo renombrar lo dejan dado de baja) | (el del stock, si hay) |

- **Línea sin cambios** (activo, mismo stock, sin nombre nuevo): se acepta como no-op (★ decisión 4); el resultado muestra `stock_anterior == stock`. Rechazarla obligaría al usuario a quitar líneas que, al proponerse el stock actual (D5), aparecen solas cuando solo cambia el nombre de otra; y un 422 por "nada que hacer" no protege ningún dato. Fijar el mismo stock no registra `ajuste` porque la bitácora es de cambios de stock (y `cantidad` sería 0).
- **"Sumar" como `ingreso`** (★ decisión 7): mismo efecto y misma semántica que `POST /api/stock/ingreso`; los reportes que suman ingresos siguen siendo correctos sin conocer el modo. Alternativa descartada: `ajuste` con anterior/nuevo (duplica información y mezcla correcciones con entradas de mercadería).
- **Cambio de nombre sin registro** (★ decisión 8): `movimientos` es la bitácora de stock (RN-ST); no hay tabla de auditoría en v1. Consecuencia documentada: órdenes y movimientos muestran el nombre **actual** (JOIN), así que renombrar cambia cómo se ven los registros históricos (ver Riesgos).
- **Reactivación solo si el stock cambia y queda > 0** (decisión 9, **decisión del usuario 2026-11-20**, reemplaza la propuesta ★ "toda línea aceptada reactiva"): un dado de baja se reactiva únicamente con `sumar` o con `fijar` en un valor distinto del actual y mayor que 0 (`reactivado = true`). `fijar 0`, fijar el mismo stock o solo renombrar cambian lo que corresponda (stock/nombre, con `ajuste` si el stock cambió) pero lo dejan dado de baja (`reactivado = false`) y siguen en "Dados de baja". Evita sacar de la baja un producto solo porque se lo tocó. La web avisa por línea qué va a pasar.
- La reactivación nunca registra movimiento (coherente con la baja, que tampoco lo hace).
- Concurrencia: dentro de `BEGIN IMMEDIATE` no hay carreras entre lotes; "fijar" es absoluto, así que gana el último lote confirmado (ver Riesgos).

### D3 — Alta (decisión 1)

`StockService.dar_de_alta(codigo, nombre, stock, usuario_id)`: `normalizar_codigo`; nombre obligatorio (`None`, no texto o vacío tras recortar → "El campo nombre es obligatorio."; > 120 → mensaje actual); `validar_stock` (nueva en `normalizacion.py`, `type(x) is int` y 0..10.000, mensaje "El stock debe ser un entero entre 0 y 10.000."). `StockRepository.dar_de_alta` en una transacción:

- no existe → `INSERT` (`activo = 1`); si `stock > 0`, movimiento `ingreso` por el stock (igual que el alta vía ingreso de C-02); si `stock = 0`, ninguno.
- existe activo → `ProductoDuplicado` (409).
- existe inactivo → `UPDATE nombre, stock, activo = 1`; si el stock cambió, `ajuste` (conservado → nuevo); si no, ninguno. `reactivado = True`.
- Carrera de dos altas: `BEGIN IMMEDIATE` serializa; respaldo: `IntegrityError` del `UNIQUE(codigo)` → `ProductoDuplicado`.

Resultado: `ResultadoIngreso(producto, creado, reactivado)` (entidad existente).

### D4 — Esquema y migración (decisiones 10, 11)

Tabla nueva (en `ESQUEMA_SQL` para bases nuevas y como destino de la migración):

```sql
CREATE TABLE movimientos (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso', 'ajuste')),
    cantidad INTEGER NOT NULL CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    stock_anterior INTEGER CHECK (stock_anterior IS NULL OR (typeof(stock_anterior) = 'integer' AND stock_anterior >= 0)),
    stock_nuevo    INTEGER CHECK (stock_nuevo    IS NULL OR (typeof(stock_nuevo)    = 'integer' AND stock_nuevo    >= 0)),
    CHECK (((tipo = 'ajuste') = (stock_anterior IS NOT NULL)) AND ((tipo = 'ajuste') = (stock_nuevo IS NOT NULL))),
    CHECK (tipo <> 'ajuste' OR (stock_nuevo <> stock_anterior AND cantidad = abs(stock_nuevo - stock_anterior)))
);
```

- **Por qué columnas `stock_anterior`/`stock_nuevo` y `cantidad = |diferencia|`** (★ decisión 10): el ajuste es absoluto, así que lo que importa auditar es el antes y el después; la `cantidad` sigue siendo > 0 para **todas** las filas (invariante y CHECK existentes, lectores y reportes intactos) y el sentido se deduce de anterior/nuevo. Las columnas son nulas en `ingreso`/`egreso` (filas viejas incluidas, sin backfill). Alternativas: guardar el ajuste como `ingreso`/`egreso` de la diferencia (pierde la intención, pedido explícito del usuario); `cantidad` con signo (rompe el CHECK y a los lectores); tabla aparte de ajustes (dos fuentes para la bitácora y la consulta).
- **Migración** (`_migrar_movimientos(conn)`, llamada desde `inicializar_esquema` **después** de `executescript` y **antes** de normalizar fechas):
  1. Si `PRAGMA table_info(movimientos)` ya tiene `stock_anterior` → no hace nada (idempotente).
  2. `BEGIN IMMEDIATE`; `CREATE TABLE movimientos_nueva (...)` (DDL de arriba); `INSERT INTO movimientos_nueva (id, fecha, producto_id, tipo, cantidad, usuario_id) SELECT id, fecha, producto_id, tipo, cantidad, usuario_id FROM movimientos`; `DROP TABLE movimientos`; `ALTER TABLE movimientos_nueva RENAME TO movimientos`; recrear `idx_movimientos_producto` e `idx_movimientos_fecha`; `PRAGMA foreign_key_check(movimientos)` vacío o error; comparar `COUNT(*)` antes/después; `COMMIT`. Cualquier error → `ROLLBACK` y el arranque falla con el error (la base queda como estaba).
  3. SQLite permite DDL dentro de la transacción y ninguna tabla referencia a `movimientos`, así que no hace falta `PRAGMA foreign_keys = OFF` (el procedimiento de 12 pasos de SQLite solo lo exige cuando otras tablas apuntan a la reconstruida). Se conservan los `id` (la bitácora ordena por `id` ante igual fecha).
  4. Antes del primer arranque con este change se recomienda copiar `dev-local.db` (README, sección "Correr en local").
- **Paridad Postgres (C-07, no se implementa aquí)**: mismo CHECK de `tipo` y columnas `stock_anterior`/`stock_nuevo` con los CHECK equivalentes en `schema.sql`; funciones RPC `crear_producto(p_codigo, p_nombre, p_stock, p_usuario_id)` y `modificar_stock(p_lineas jsonb, p_usuario_id)` con `SELECT ... FOR UPDATE` en orden de código; `listar_inactivos` como consulta simple. Anotado en el scope de C-07 en `CHANGES.md`.

### D5 — Frontend (decisiones 12-15)

- `static/index.html`: barra "Nuevo ingreso" (`btn-nuevo`) / "Modificar stock" (`btn-modificar`) / "Nueva orden" / "Ver órdenes"; se quitan `modal-ingreso` y `modal-egreso` y se agregan `modal-nuevo` y `modal-modificar` tal como los mockups aprobados (estados NI*, MS*). Cartel vacío: "Creá el primero con Nuevo ingreso.".
- `static/js/inventario.js`:
  - Nuevo ingreso: valida Código, Nombre y Stock (`Validacion.requerido`, `largo`, `stock`); al escribir el código, si coincide con un inactivo cargado, aviso no bloqueante (NI4). 409 → `detail` solo en la alerta superior, Código `aria-invalid` + `aria-describedby` → alerta + foco (mismo patrón que el 409 de número de orden). Éxito → "Producto creado: …" / "Producto reactivado: …".
  - Modificar stock: al abrir carga `GET /api/inventario` y `GET /api/productos/inactivos` en paralelo; `<select>` con `<optgroup label="Activos">` y `<optgroup label="Dados de baja">`, opciones "CÓDIGO · Nombre (stock N)"; deshabilita en cada selector los códigos elegidos en otras líneas; aviso en la línea de un dado de baja: "Dado de baja: se va a reactivar al guardar." si el stock cambia y queda > 0, o "Dado de baja: sigue dado de baja (sin cambio de stock)" / "(stock 0)" si no. Modo con radios reales en un `fieldset` (`aria-label="Modo de la línea N"`), valor numérico con `aria-label` según el modo, resultado "Stock actual A → B" en vivo (o "· sin cambios"), "Nuevo nombre (opcional)" con placeholder "Sin cambios (Nombre actual)". Al elegir un producto en modo "Fijar en" el valor se propone en su stock actual (★ decisión 12: renombrar sin tocar el stock no exige teclear el stock). El nombre se envía solo si no está vacío.
  - Reutiliza la mecánica de líneas de la orden (agregar/quitar/renumerar, 1..100, "Agregar producto" deshabilitado en 100).
  - Errores: 422 `^Línea (\d+):` → esa línea; 404 `codigos` → líneas con ese código + "Este producto ya no existe: elegí otro o quitá la línea." + recarga de selectores; red/5xx → mensajes de `Api`. Botón "Guardar cambios" → "Guardando…" deshabilitado durante el envío.
  - Éxito: cierra, recarga el inventario y muestra la alerta persistente "Stock modificado (N productos)" con un `<li>` por línea (MS8), construida con `createElement`/`textContent`.
  - Se eliminan `abrirIngreso`, `enviarIngreso`, `abrirEgreso`, `enviarEgreso` y `hintCodigoNuevo`; ningún script llama a `/api/stock/ingreso|egreso` (guarda en tests).
- `static/js/validacion.js` (puro): `stock(texto)` (`/^\d+$/`, 0..10.000, "El stock debe ser un entero entre 0 y 10.000."), `lineasModificacion(lineas)` → errores por índice ("Elegí un producto.", repetido "Este producto ya está en la línea M.", valor según modo, nombre ≤ 120) y error general (0 o > 100 líneas).
- Sin `innerHTML` ni equivalentes (guarda existente); colores solo por tokens. Piezas nuevas de CSS (`.mline`, `.seg`, `.delta`, `.tag-baja`, `.tag-react`, `.sum-list`): ★ decisión 13 — van a `static/css/app.css` (específico de la app, ya existe) y **no** a `ui.css`, para no subir la Revision del design system ni romper el test de igualdad byte a byte `static/css/ui.css` == `design-system/ui.css`.

### D6 — Tests (Strict TDD, `unittest`, SQLite real)

- `tests/test_stock_service.py` / nuevo `tests/test_modificacion_service.py`: validación del alta y de las líneas (mensajes exactos con "Línea N: "), repetidos, límites 0/10.000/1/100/101, orden de prioridad de rechazos; repositorio real en `:memory:` (sin mocks).
- `tests/test_sqlite_stock_repository.py`: alta (nuevo con/sin stock, activo → `ProductoDuplicado`, inactivo → reactivación con/sin `ajuste`), modificación (fijar, sumar, mismo stock, nombre, reactivación, inexistentes, atomicidad forzando un fallo del segundo movimiento con un trigger SQLite `RAISE(ABORT)` creado en el test — base real, no mock).
- `tests/test_sqlite_schema.py` / nuevo `tests/test_sqlite_migracion.py`: base creada con el DDL **viejo** (copiado como literal en el test) + filas → `inicializar_esquema` → columnas nuevas, mismos ids/datos, `ajuste` aceptado, CHECK de coherencia; segunda inicialización no cambia nada; fallo a mitad (trigger o tabla `movimientos_nueva` preexistente) → esquema viejo intacto.
- `tests/test_api_productos.py`, `tests/test_api_stock.py`, `tests/test_api_movimientos.py`: endpoints con `TestClient` (201/409/422/401, 200/404 con `codigos`/422, campos nuevos de movimientos), `tests/test_api_csrf.py` para los dos POST nuevos.
- `tests/test_api_app.py::DocsTest` y el test de rutas de C-06: diez → trece rutas (cambio de aserción justificado por la spec `api-http` modificada).
- `tests/test_frontend_estatico.py`: las guardas de los modales de ingreso/egreso se reemplazan por las de los modales nuevos (spec `interfaz-web`: requisitos REMOVED/ADDED); nueva guarda "ningún JS referencia `/api/stock/ingreso` ni `/api/stock/egreso`".
- Comportamiento del navegador: verify con Playwright contra los mockups aprobados; `validacion.js` con `browser_evaluate` sobre una tabla de casos (como C-06).

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-20)
- Mockups: openspec/changes/paso-5b-fixes-menores/mockups/ (`inventario.html`, `README.md`, `assets/`)
- Approval: approved (2026-11-20, by user)
- Preview: rendered (2026-11-20, Playwright: 19 estados × 390x844 y 1440x900 = 38 capturas en `mockups/previews/inventario-<ID>-{mobile,desktop}.png`; sin scroll horizontal de página; fondo oscuro en todos, T2 con SO claro emulado)
- Visual verify: passed (2026-11-23) — Playwright contra uvicorn real (puerto 8791, base temporal), 19 estados x 390x844 y 1440x900 en `mockups/verify/`; MS5 (422), MS6 (404 con `codigos`) e I2 (inventario vacío) con respuesta simulada por `page.route`; sin errores de consola salvo los 4xx esperados; sin scroll horizontal. Diferencias solo de datos/posición del modal (menores).

Base: mockup aprobado de C-06 (`openspec/changes/archive/2026-11-20-paso-5-web-local/mockups/inventario.html`), mismos tokens (`design-system/tokens.css`, `ui.css`), cabecera de texto "Inventario", tema oscuro único. Estados: I1, I2, NI1-NI6, MS1-MS8, T1, T1b, T2 (detalle en `mockups/README.md`). Estos mockups son criterio de aceptación de los grupos 9-10 de `tasks.md` y del verify.

## Risks / Trade-offs

- [Migración sobre datos reales del usuario] → transacción única, conteo antes/después, `foreign_key_check`, test con DDL viejo; recomendación de copiar `dev-local.db` antes del primer arranque.
- ["Fijar en" pisa cambios concurrentes: dos pestañas fijan el mismo producto y gana la última] → app de un usuario; el resumen muestra anterior → nuevo; control optimista (`stock_esperado` por línea → 409) queda como mejora futura.
- [Renombrar cambia el nombre mostrado en órdenes y movimientos pasados (JOIN al nombre actual)] → aceptado en v1 (decisión 8); si hace falta historia, guardar el nombre en `orden_items`/`movimientos` en otro change.
- [Stock > 10.000 (alcanzable con varios ingresos) no se puede "fijar" a sí mismo] → la web propone el stock actual en "Fijar en"; si supera 10.000, la validación lo marca y el usuario cambia el modo a "Sumar"… que exige > 0. Para renombrar un producto así habría que ampliar el tope (decisión 14). Caso raro en un taller chico.
- [La regla de reactivación depende del stock resultante y puede no ser obvia] → aviso por línea antes de guardar ("se va a reactivar" / "sigue dado de baja") y marca "reactivado" en el resumen solo cuando ocurrió.
- [API con dos formas de sumar (`/api/stock/ingreso` y `sumar`)] → ambas registran `ingreso`; se conservan por compatibilidad y `/docs`.
- [Guardas de frontend existentes cambian] → cambio pedido por el usuario y reflejado en specs (REMOVED/ADDED); el resto de la suite no cambia aserciones.

## Migration Plan

1. Respaldo manual de `dev-local.db` (recomendado).
2. Primer arranque: `inicializar_esquema` migra `movimientos` (log `INFO` con la cantidad de filas migradas). Arranques siguientes: no-op.
3. Rollback: restaurar la copia del `.db` y revertir el código (el código viejo no acepta filas `ajuste` ni conoce las columnas nuevas; una base migrada sin ajustes sigue funcionando con el código viejo porque los INSERT de C-02 no nombran las columnas nuevas y los CHECK aceptan las filas viejas).

## Open Questions

- Al archivar, actualizar la KB: 04 (`movimientos.tipo` con `ajuste`, columnas `stock_anterior`/`stock_nuevo`, CHECK de coherencia; stock inicial 0 en el alta), 05 (RN de cantidades: > 0 salvo stock inicial y ajuste >= 0; RN nuevas de alta explícita, ajuste, modificación en lote todo o nada, reactivación por modificación, nombre editable), 06 (US-004 → "Nuevo ingreso", US-005 → "Modificar stock"), 07 (flujos de alta y de modificación; el ingreso/egreso quedan solo por API).

## Decisiones a confirmar por el usuario

> Confirmadas por el usuario el 2026-11-20: decisiones 1-8 y 10-15 tal como están propuestas (★); la 9 fue modificada por el usuario (ver abajo).

> Governance MEDIO/ALTO: el apply no empieza hasta que el usuario revise estas decisiones **y** apruebe los mockups. ★ = recomendada. Las decisiones ya tomadas por el usuario el 2026-11-20 (alta con código activo → 409, dado de baja → reactivar con nombre y stock nuevos, tipo `ajuste` con stock anterior y nuevo, lote todo o nada, sin repetidos, endpoints viejos fuera de la web, stock >= 0 solo en alta y ajuste, modificar también dados de baja reactivándolos) no se repiten.

1. **Forma de la API.**
   - A ★ `POST /api/productos` (alta) + `POST /api/stock/modificaciones` (lote) con líneas `{codigo, modo: fijar|sumar, stock|cantidad, nombre?}`.
   - B Un único `POST /api/stock/modificaciones` que también da de alta (modo `crear`).
2. **Status del alta que reactiva.**
   - A ★ 201 siempre, con `creado`/`reactivado`.
   - B 201 al crear y 200 al reactivar.
3. **Lista de dados de baja para el selector.**
   - A ★ `GET /api/productos/inactivos` (endpoint nuevo, `/api/inventario` intacto).
   - B `GET /api/inventario?incluir_inactivos=true` agregando `activo` a cada producto.
4. **Línea sin cambios** (mismo stock, sin nombre nuevo, activo).
   - A ★ Se acepta sin efectos y el resumen dice "sin cambios".
   - B 422 "Línea N: no hay cambios para guardar.".
5. **Producto repetido en el lote.**
   - A ★ 422 "Línea N: el producto 'X' ya está en la línea M." y la web deshabilita los ya elegidos.
   - B Consolidar como la orden (solo posible para "Sumar").
6. **Máximo de líneas por lote.** A ★ 100 (igual que la orden). B Sin tope.
7. **Cómo se registra "Sumar".** A ★ Movimiento `ingreso`. B Movimiento `ajuste` con anterior/nuevo.
8. **Cambio de nombre.** A ★ Sin registro (la bitácora es de stock); los registros históricos muestran el nombre nuevo. B Registrar el nombre anterior en una tabla de auditoría (más alcance).
9. **"Fijar en 0" o solo renombrar un producto dado de baja.** Decisión del usuario 2026-11-20: B, solo se reactiva si el stock cambia y queda > 0 (fijar 0, mismo stock o solo renombrar lo dejan dado de baja). Opción descartada: A, toda línea aceptada reactiva.
10. **Columnas del ajuste.** A ★ `stock_anterior`, `stock_nuevo` + `cantidad = |diferencia|` (> 0 como hoy). B Solo `stock_nuevo` y `cantidad` con signo.
11. **Migración.** A ★ Automática al arrancar, en una transacción, con respaldo manual recomendado. B Script manual aparte.
12. **Valor propuesto en "Fijar en".** A ★ El stock actual del producto elegido. B Vacío.
13. **CSS de las piezas nuevas.** A ★ `static/css/app.css` (sin tocar el design system). B Subir el design system a Revision 3 y agregarlas a `ui.css`.
14. **Tope del stock absoluto** (alta y "Fijar en"). A ★ 0..10.000 (mismo tope que las cantidades). B 0..1.000.000.
15. **Etiquetas.** A ★ Botones "Nuevo ingreso" / "Modificar stock"; modales "Nuevo ingreso" (botón "Crear producto") y "Modificar stock" (modos "Fijar en" / "Sumar", botón "Guardar cambios", "Agregar producto"). B "Nuevo producto" en lugar de "Nuevo ingreso".
