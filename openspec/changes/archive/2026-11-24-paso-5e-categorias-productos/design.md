# Design — paso-5e-categorias-productos (C-06e)

## Context

Ver `proposal.md` (Why). Estado actual observado (C-01..C-06d archivados):

- **Esquema** (`inventario/repositories/sqlite_repo.py`, `_ESQUEMA_PLANTILLA`): `productos(id, codigo UNIQUE, nombre CHECK no vacío, stock CHECK entero >= 0, activo 0/1)`, referenciada por `orden_items.producto_id` y `movimientos.producto_id` (FK, `PRAGMA foreign_keys = ON` en `conectar`). `inicializar_esquema` corre `executescript(ESQUEMA_SQL)` (todo `IF NOT EXISTS`), luego `_migrar_movimientos` (patrón de C-06b: detecta por `PRAGMA table_info`, reconstruye en `_transaccion` con `BEGIN IMMEDIATE`, verifica conteo y `foreign_key_check`, rollback y excepción si algo falla), luego `NORMALIZAR_FECHAS_SQL` y `commit`.
- **Lecturas de producto**: varias constantes SQL (`_SQL_PRODUCTO_POR_CODIGO`, `_POR_ID`, `listar_activos`, `listar_inactivos`, `_SQL_PRODUCTOS_POR_CODIGOS_TODOS`) seleccionan `id, codigo, nombre, stock, activo` y `_a_producto` arma `Producto`. Escrituras: `_SQL_ALTA`/`_SQL_ALTA_ACTIVO`, `_SQL_REACTIVAR_ALTA`, `_SQL_ACTUALIZAR_LINEA`.
- **Services**: `StockService` (`ingresar`, `dar_de_alta`, `modificar` con `_validar_lineas` → `LineaModificacion(codigo, modo, valor, nombre)`, errores "Línea N: …"), `InventarioService.listar` (orden por código en Python), `ProductoService` (inactivos, baja).
- **API**: `ProductoOut(codigo, nombre, stock, sin_stock)` es la forma común de producto (inventario, inactivos, egreso, baja) y base de `IngresoOut` y `LineaModificadaOut`. Routers finos. OpenAPI: 15 rutas `/api/...` (C-06d).
- **Web** (`static/index.html`, `static/js/inventario.js`, `static/js/busqueda.js`): tabla Código/Nombre/Stock/acción; buscador cliente puro (`Busqueda.filtrar`, `Busqueda.conteo`); cartel sin coincidencias con "Limpiar búsqueda"; `exportarInventario` imprime `visibles`. "Nuevo ingreso" = alta (`POST /api/productos`), con aviso de código dado de baja. "Modificar stock" con `<template id="tpl-mline">`, selector con `optgroup` "Activos"/"Dados de baja". "Nueva orden": líneas creadas en JS (`nuevaLinea`) con un `<select>` lleno por `llenarSelect` desde `productos` (activos).
- **Datos reales**: `dev-local.db` (ruta de `INVENTARIO_DB_PATH`, `*.db` en `.gitignore`) con productos, órdenes y movimientos que deben sobrevivir.

## Goals / Non-Goals

**Goals:**
- Categoría opcional por producto, extensible sin migrar otra vez, con 3 categorías sembradas.
- Migración al arrancar **sin reconstruir `productos`** (evita desactivar FKs con tablas hijas), idempotente y todo-o-nada.
- Filtro cliente combinable con el buscador de C-06c, exportación coherente con lo visible.
- Categoría en "Nuevo ingreso" y "Modificar stock"; filtro por categoría al elegir componentes de "Nueva orden" (decisión del usuario).

**Non-Goals:**
- Pantalla web para administrar categorías (la administración es solo por API, decisión 2), borrado de categorías (sub-decisión 2.6: no se incluye, decidido por el usuario 2026-11-24) y colores por categoría.
- Varias categorías por producto, subcategorías.
- Categoría en `/ordenes`, en el PDF de una orden o en movimientos; filtro de categoría en `/reportes` (solo columna, decisión 24).
- Filtro por categoría en el selector de "Modificar stock" (no pedido; se puede sumar si el usuario lo quiere).
- Cambiar el endpoint legado `POST /api/stock/ingreso` (sigue creando productos sin categoría).

## Decisions

### D1 — Modelo: tabla `categorias` + FK opcional (decisiones 1, 3, 4, 13)

```sql
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE
        CHECK (length(clave) BETWEEN 1 AND 30 AND clave NOT GLOB '*[^a-z0-9-]*'
               AND clave NOT GLOB '-*' AND clave NOT GLOB '*-'),
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 40)
);
-- en productos (base nueva):
    categoria_id INTEGER REFERENCES categorias(id)   -- NULL = Sin categoría
```

- **Tabla** (★) en vez de valores fijos con `CHECK (categoria IN (...))`: agregar una categoría es un `INSERT` (siembra o, a futuro, un ABM), no otra reconstrucción de `productos`; FK real; mismo modelo en Postgres. Alternativa descartada: columna de texto con CHECK (cada categoría nueva = migración de `productos`, que es la tabla más referenciada).
- **Clave + nombre** (★): la clave (`motor`, minúsculas, ASCII) es lo que viaja por la API y lo que se compara; el nombre (`Motor`) es solo para mostrar. Renombrar en el futuro no rompe nada.
- **Opcional** (★, `NULL` = "Sin categoría"): la columna se puede agregar con `ALTER TABLE ADD COLUMN` (SQLite exige que una columna nueva con `REFERENCES` tenga default `NULL` cuando las FKs están activas, y no admite `NOT NULL` sin default); los productos existentes no tienen dato del que inferir la categoría; el endpoint legado de ingreso sigue funcionando. Alternativa descartada: obligatoria con una categoría "otros" asignada a los existentes (obliga a reconstruir `productos` o a un default no nulo con FK, y suma una categoría ficticia).
- Siembra: `INSERT INTO categorias (clave, nombre) VALUES ('motor','Motor'), ('aceite','Aceite'), ('filtro','Filtro')` **solo si `categorias` está vacía** (`SELECT COUNT(*)`), dentro de la misma transacción. Con la administración por API (decisión 2) esto evita pisar renombres y, si algún día se agrega el borrado, no resucita categorías borradas. Idempotente igual (un catálogo con filas nunca se resiembra). Refina la decisión 14 ("siembra idempotente en cada arranque") sin cambiar su intención.
- Unicidad del nombre: `UNIQUE COLLATE NOCASE` (SQLite pliega solo ASCII) + chequeo en el service con `casefold()` (cubre "Ñ"/tildes); en Postgres, índice único sobre `lower(nombre)`.
- Sin índice sobre `productos.categoria_id` (el filtro es en el navegador y el volumen es chico).

### D2 — Migración idempotente sin reconstruir `productos` (decisiones 4, 14)

`_migrar_productos_categoria(conn)` en `sqlite_repo.py`, llamada en `inicializar_esquema` **después de `_migrar_movimientos` y antes de `NORMALIZAR_FECHAS_SQL`** (ese `UPDATE` abre una transacción implícita y `_transaccion` exige conexión sin transacción pendiente):

1. `columnas = PRAGMA table_info(productos)`; si ya está `categoria_id`, solo sembrar si el catálogo está vacío (en su propia `_transaccion`) y salir.
2. En una `_transaccion` (`BEGIN IMMEDIATE`; el DDL de SQLite es transaccional): contar filas de `productos`, `orden_items`, `movimientos`; `ALTER TABLE productos ADD COLUMN categoria_id INTEGER REFERENCES categorias(id)`; sembrar si el catálogo está vacío; verificar `PRAGMA foreign_key_check(productos)` vacío y conteos iguales; si no, `IntegrityError` → rollback y la excepción sube (el arranque falla con el error, como C-06b).
3. `log.info("Agregada la categoría a productos (%d producto(s) conservados).", n)`.

`categorias` ya existe en ese momento porque `ESQUEMA_SQL` la crea con `IF NOT EXISTS` (va antes de `productos` en la plantilla). En una base nueva, `productos` ya nace con `categoria_id` y el paso 1 solo siembra.

**Por qué `ADD COLUMN` y no reconstrucción** (★): `productos` es padre de `orden_items` y `movimientos`; reconstruirla exige `PRAGMA foreign_keys = OFF` **fuera** de la transacción, `legacy_alter_table` o recrear también las hijas: más riesgo sobre los datos reales para nada (no necesitamos `NOT NULL` ni CHECK nuevos en `productos`). `ADD COLUMN` no reescribe filas.

Prueba de falla: inyectar el error después del `ALTER` (por ejemplo, una siembra que viola el CHECK con un parche del SQL de siembra en el test, o un hook de prueba) y comprobar que `productos` sigue sin la columna.

### D3 — Dominio, repositorios y services (decisiones 5, 6, 9, 10, 15)

- `domain/entities.py`: `Categoria(clave, nombre)`; `Producto` gana `categoria: "str | None" = None` (clave; default para no romper constructores existentes); `LineaModificacion` gana `cambia_categoria: bool = False` y `categoria: "str | None" = None`; `ResultadoModificacion` gana `categoria` y `categoria_anterior` (default `None`).
- `repositories/base.py`: `CategoriaRepository.listar() -> list[Categoria]` (orden por nombre). `StockRepository.dar_de_alta(codigo, nombre, stock, categoria, usuario_id, fecha)` (firma ampliada).
- `sqlite_repo.py`:
  - Una sola proyección de producto: `_COLUMNAS_PRODUCTO = "p.id, p.codigo, p.nombre, p.stock, p.activo, c.clave AS categoria"` y `_DESDE_PRODUCTO = "FROM productos p LEFT JOIN categorias c ON c.id = p.categoria_id"`; todas las lecturas de producto la usan; `_a_producto` lee `categoria`.
  - Escrituras con subconsulta por clave: `categoria_id = (SELECT id FROM categorias WHERE clave = ?)` (con `None` queda `NULL`). Alta nueva y reactivación (`_SQL_REACTIVAR_ALTA` reemplaza la categoría, decisión 8). `_aplicar_linea`: si `linea.cambia_categoria` y la clave difiere de la actual, se incluye en el `UPDATE`; el cambio de categoría **no** escribe movimientos ni cuenta para la reactivación (decisión 9).
  - `SqliteCategoriaRepository.listar()` → `SELECT clave, nombre FROM categorias ORDER BY nombre, clave`.
- `services/categoria_service.py` (nuevo): `CategoriaService.listar()`.
- `services/normalizacion.py`: `normalizar_categoria(valor)` → `None` si `None` o blanco; `DatosInvalidos("El campo categoria debe ser texto.")` si no es `str`; si no, `strip().lower()` (decisión 15). Más de 30 caracteres → "La categoría '…' no existe." con la clave recortada a 30 + "…" para no ecoar textos enormes.
- `StockService(stock_repo, categoria_repo, ahora=ahora_argentina)`: `dar_de_alta(codigo, nombre, stock, usuario_id, categoria=None)` normaliza y valida contra `categoria_repo.listar()` → `DatosInvalidos("La categoría 'x' no existe.")`; `_validar_linea` hace lo mismo con prefijo "Línea N: " y marca `cambia_categoria` (la validación de categoría queda dentro de la fase "validación de datos": antes de repetidos e inexistentes). Las categorías no se borran desde la app, así que validar fuera de la transacción es seguro; la FK es la red final. Los constructores existentes de `StockService` en tests y `api/dependencies.py` se actualizan (cambio mecánico).
- La categoría **no** influye en el 409 de alta ni en la reactivación (decisión 10).

### D4 — API (decisiones 11, 12)

- `ProductoOut` gana `categoria: Optional[str]` → aparece en inventario, inactivos, egreso, baja, alta (`IngresoOut`) y líneas de modificación (una sola forma de producto, ★). `LineaModificadaOut` gana `categoria_anterior: Optional[str]`. Los tests con diccionarios exactos se actualizan.
- `AltaProductoRequest.categoria: Optional[str] = None` — se declara `Optional[Any]`/sin tipo estricto y lo valida el service, para que `3` dé "El campo categoria debe ser texto." (no el 422 genérico de Pydantic).
- `_LineaBase.categoria`: igual; el router pasa `cambia_categoria = "categoria" in linea.model_fields_set` (ausente = no cambia; `null` = quitar).
- `GET /api/categorias` en `api/routers/categorias.py` (`prefix="/api/categorias"`, `tags=["categorias"]`, `dependencies=[Depends(get_current_user)]`) → `List[CategoriaOut(clave, nombre)]`; en el mismo router, `POST` y `PATCH /{clave}` (D11).
- Sin filtro de categoría en `GET /api/inventario` (★ el filtro es cliente, como el buscador; YAGNI hasta C-07 si hiciera falta).
- Reporte: `ProductoEnOrdenesOut` gana `categoria: Optional[str]` (D8b). `ProductoUsadoOut` no cambia.
- Administración de categorías: ver D11. OpenAPI: 17 rutas (`/api/categorias` con `GET` y `POST`, `/api/categorias/{clave}` con `PATCH`).

### D5 — Inventario: columna, filtro combinado, conteo, sin coincidencias (decisiones 16-19)

- Carga: `GET /api/categorias` en paralelo con el inventario, una vez al abrir; mapa `clave → nombre`. Si falla, se muestra la clave cruda y el filtro solo con "Todas las categorías" (sin bloquear la tabla).
- Tabla: columna **"Categoría"** entre Nombre y Stock (★ columna de texto: se imprime igual en el PDF y no depende del color; "Sin categoría" con `text-muted`). Alternativa: tag/badge dentro de la celda del nombre (más compacto en móvil, pero mezcla datos al imprimir). A 390 px la tabla ya tiene scroll horizontal propio (`overflow-x-auto`); el mockup decide si la columna se mantiene o se apila.
- Filtro: `<select id="inv-categoria">` con `label` accesible (`sr-only` "Categoría"), opciones "Todas las categorías" (`""`), las categorías por nombre y "Sin categoría" (valor centinela `"__sin__"`). ★ `<select>` en vez de chips/pestañas: escala si el catálogo crece, ocupa una sola celda en la barra móvil y es nativo y accesible. Ubicación: en la barra del panel junto al buscador (a 390 px, en la fila del buscador o debajo; lo fija el mockup).
- `busqueda.js` (puro, testeable con Node): `filtrar(productos, texto, categoria)` aplica ambos criterios (AND); `conteo(visibles, total, hayFiltro)` sin cambios de firma (el llamador pasa `hayBusqueda || hayCategoria`); `mensajeSinCoincidencias(texto, nombreCategoria)` devuelve las tres variantes de la spec.
- "Limpiar filtros" (★ un solo botón que limpia ambos; renombra "Limpiar búsqueda") devuelve el foco a "Buscar". Escape en "Buscar" limpia solo el texto.
- Recarga tras acciones: se conservan texto y categoría (variables en memoria; no `localStorage`).

### D6 — "Nuevo ingreso" y "Modificar stock" (decisiones 7, 8, 9, 20)

- "Nuevo ingreso": `<select id="nu-categoria">` con "Sin categoría" (por defecto, valor `""`) + categorías. ★ opcional (no se obliga a clasificar para dar de alta). Se envía `categoria` (clave o `null`). El aviso de código dado de baja pasa a "…con el nombre, el stock y la categoría que indiques." y, al detectarlo, **no** se precarga la categoría anterior (la reactivación reemplaza; mantener el formulario simple).
- "Modificar stock": cada línea del `tpl-mline` suma un `<select data-categoria>` ("Sin categoría" + categorías) en el cuerpo de la línea, junto a "Nuevo nombre". Al elegir producto (activo **o dado de baja**, ★ mismo tratamiento) se precarga su categoría. El JS envía siempre `categoria` (clave o `null`) por línea; el backend compara y solo escribe si cambió. El resumen agrega "categoría: Filtro → Aceite" cuando `categoria_anterior != categoria`.
- El selector de producto de "Modificar stock" **no** se filtra por categoría (non-goal; se puede pedir).

### D7 — "Nueva orden": filtro por categoría por línea (decisiones 21, 22)

Decidido por el usuario (2026-11-24): el selector de producto de la orden permite elegir entre todos o filtrar por categoría. Forma recomendada:

- ★ **Un `<select>` de categoría por línea**, antes del producto: "Todas" (por defecto), categorías, "Sin categoría". `llenarSelect(select, conservar, categoria)` filtra `productos` por esa categoría. Una orden típica de taller mezcla categorías (aceite + filtro + piezas de motor), así que un filtro único de modal obligaría a cambiarlo entre línea y línea. Alternativa: un filtro único arriba de "Componentes" que afecta a todas las líneas (más simple visualmente; las líneas ya elegidas fuera del filtro conservan su producto). El mockup O1 muestra la recomendada; si el usuario prefiere el filtro único, se ajusta spec y mockup antes del apply.
- ★ Al cambiar la categoría: si el producto elegido pertenece, se conserva; si no, la línea vuelve a "Elegí un producto…" (no queda oculto un valor que el selector no muestra). Categoría sin activos → ayuda "No hay productos en esta categoría.".
- Layout de línea: en desktop `[n] [Categoría ▾] [Producto ▾] [Cant.] [Quitar]`; a 390 px la categoría y el producto van en una fila y cantidad + Quitar en otra (lo fija el mockup O1).
- Nada cambia en el cuerpo enviado a `POST /api/ordenes`.

### D8 — PDF del inventario (decisión 23)

`exportarInventario` sigue imprimiendo `visibles` (búsqueda + categoría) con la nueva columna. ★ Con una categoría elegida, la línea del encabezado es "Aceite · 3 productos · 2026-11-24" (la categoría da contexto al papel; el texto de búsqueda sigue sin imprimirse, decisión de C-06c). Nombre de archivo sin cambios (`inventario-AAAA-MM-DD`). El PDF de una orden no muestra categoría (decisión 24).

### D8b — Categoría en `/reportes` (decisión 24, cambiada por el usuario)

- Repositorio: `_SQL_REPORTE_EN_ORDENES` agrega `LEFT JOIN categorias c ON c.id = p.categoria_id`, `c.clave AS categoria` en el `SELECT` y en el `GROUP BY`; `ProductoEnOrdenes` gana `categoria` (default `None`). Es la categoría **actual** del producto (como el nombre: los ítems no guardan historia). Sin parámetro de categoría.
- `reportes.js`: carga `GET /api/categorias` junto con `productos-usados` (falla tolerada: muestra la clave); columna **"Categoría" entre Nombre y Cantidad** (★ textos juntos a la izquierda, números juntos a la derecha; mismo lugar que en el inventario). "Sin categoría" atenuado en pantalla y en texto en el papel. La marca "dado de baja" sigue en la celda del nombre.
- PDF del reporte: mismas cinco columnas; encabezado y nombre de archivo sin cambios. A 390 px la tabla ya hace scroll horizontal propio; el mockup R10 lo confirma.

### D9 — Paridad Supabase (C-07) (decisión 25)

`categorias(id bigint generated always as identity primary key, clave text not null unique check (clave ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and length(clave) <= 30), nombre text not null check (length(btrim(nombre)) between 1 and 40))` + `create unique index on categorias (lower(nombre))`; siembra solo si la tabla está vacía; `productos.categoria_id bigint null references categorias(id)`; RLS como `productos`. Alta y renombre de categorías: operaciones directas de una sola fila desde el repositorio (`insert` / `update … where clave = ?`), sin RPC (no tocan varias tablas); la violación de unicidad (`23505`) se traduce a `CategoriaDuplicada` → 409. Las RPC de alta y modificación de productos aceptan `p_categoria text` (clave) y resuelven el id dentro de la función; la RPC `productos_en_ordenes` devuelve `categoria`. Anotar en `CHANGES.md` § C-07 al archivar.

### D11 — Administración de categorías por API (decisión 2, cambiada por el usuario)

Sin pantalla web; se usa desde `/docs` con la cookie de sesión. Mismas protecciones que las demás escrituras: sesión obligatoria (401), cuerpo solo JSON (modelo Pydantic en el cuerpo → `text/plain`/formularios dan 422, defensa CSRF de C-06), cookie `SameSite=Lax`, sin CORS.

- `POST /api/categorias` con `CategoriaAltaRequest {nombre, clave?}` → 201 `CategoriaOut {clave, nombre}`.
- `PATCH /api/categorias/{clave}` con `CategoriaRenombreRequest {nombre}` (con `clave` presente en el cuerpo → 422 "La clave de una categoría no se puede cambiar.") → 200 `CategoriaOut`. `{clave}` se normaliza (recorte + minúsculas) antes de buscar.
- Errores de dominio nuevos: `CategoriaDuplicada(campo, valor)` → 409 ("Ya existe una categoría con clave 'x'." / "…con nombre 'X'."), `CategoriaNoEncontrada(clave)` → 404 ("No existe una categoría con clave 'x'."). Validación → `DatosInvalidos` 422.
- `CategoriaService(categoria_repo)`: `listar()`, `crear(nombre, clave=None)`, `renombrar(clave, nombre)`. Normalización pura en `services/normalizacion.py`: `normalizar_nombre_categoria` (recorte, 1-40) y `clave_desde_texto` (NFKD sin marcas combinantes → minúsculas → `[^a-z0-9]+` → `-` → recorte de `-` → máx. 30 → si queda vacía, 422). Unicidad de nombre por `casefold()` contra el catálogo + `UNIQUE COLLATE NOCASE` como red (el `IntegrityError` en carrera se traduce a 409).
- Repositorio: `SqliteCategoriaRepository.crear(clave, nombre)`, `renombrar(clave, nombre)`, `obtener(clave)`; cada escritura en `_transaccion`.
- El frontend no cambia por esto: toma el catálogo al abrir cada página (una categoría creada en `/docs` aparece al recargar).

**Sub-decisiones** — 2.1-2.8 aprobadas por el usuario (2026-11-24), todas como la ★; el nombre se puede renombrar, la clave no:

- 2.1 Ruta y verbos — ★ `POST /api/categorias` y `PATCH /api/categorias/{clave}` (PATCH porque solo cambia el nombre). Alt.: `PUT`.
- 2.2 Clave en el alta — ★ opcional; si falta se deriva del nombre (minúsculas, sin tildes, guiones); si viene se normaliza; formato `[a-z0-9]` con guiones, hasta 30. Alt.: siempre derivada (sin campo `clave`).
- 2.3 Clave repetida — ★ 409 "Ya existe una categoría con clave 'x'." (sin sufijos automáticos tipo `motor-2`).
- 2.4 Nombre — ★ obligatorio, 1 a 40 caracteres, único sin distinguir mayúsculas (409). Alt.: nombres repetidos permitidos.
- 2.5 Clave inmutable — ★ sí: renombrar solo cambia el nombre; enviar `clave` en el PATCH → 422. (Los productos referencian por id, pero la clave es el identificador público de la API y del filtro.)
- 2.6 Borrado — **decidido por el usuario (2026-11-24): no se incluye**. ★ Recomendación: **no incluirlo** en este change (sin pantalla que lo pida, es destructivo y C-07 suma una ruta más que migrar). Alternativa si el usuario lo quiere: `DELETE /api/categorias/{clave}` solo si ningún producto (activo o dado de baja) la usa → 409 "La categoría 'x' está asignada a N producto(s)."; 404 si no existe; con la siembra "solo si vacía" no se resucita. Agregarla suma una ruta (18), specs y tareas.
- 2.7 Quién administra — ★ cualquier usuario con sesión (hoy solo existe `admin`; sin roles).
- 2.8 Paridad C-07 — ★ operaciones directas de una fila (sin RPC), unicidad por índices; 23505 → 409.

### D10 — Tests (Strict TDD, `unittest`, SQLite real)

- Migración: `tests/test_sqlite_migracion_categorias.py` con el DDL de `productos` **viejo copiado literal** (como `test_sqlite_migracion.py`), sobre archivo temporal y `:memory:`: conservación de filas (productos activos/inactivos, órdenes, ítems, movimientos), categoría `NULL`, siembra, idempotencia (3 arranques), asignación conservada, falla a mitad → rollback.
- Esquema nuevo (`test_sqlite_schema.py`): seis tablas, `UNIQUE(clave)`, CHECK de clave, FK de `categoria_id`.
- Repositorios, services y API como en los grupos de `tasks.md`; JS puro de `busqueda.js` con Node; guardas estáticas para HTML/JS; navegador en el verify con Playwright.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-24)
- Mockups: openspec/changes/paso-5e-categorias-productos/mockups/ (inventario.html, reportes.html, README.md)
- Approval: approved (2026-11-24, by user)
- Preview: rendered (2026-11-24, 390x844 y 1440x900 en mockups/previews/; P1 y P2 con print emulado y PDF A4)
- Visual verify: passed (2026-11-24; ver mockups/verify/; diferencias menores: en la hoja impresa a 1440 px la tabla queda con márgenes laterales y la columna Categoría es algo más angosta que en el mockup, PDF A4 generados pero no rasterizados)

Base: mockups aprobados de C-06c (inventario con buscador y PDF), C-06b (modales de alta y modificación) y C-06d (`/reportes`), mismos tokens (`design-system/tokens.css`, `ui.css`), cabecera de texto "Inventario" con pestañas Inventario / Órdenes / Reportes, tema oscuro único. Estados previstos:

| ID | Pantalla | Estado |
|----|----------|--------|
| I1 | Inventario | Tabla con columna "Categoría" (Motor / Aceite / Filtro / "Sin categoría" atenuado), filtro en "Todas las categorías", "12 productos" |
| I2 | Inventario | Filtro en "Aceite": 3 filas, conteo "3 de 12 productos" |
| I3 | Inventario | Búsqueda `aceite` + filtro "Filtro": 1 fila, "1 de 12 productos" |
| I4 | Inventario | Sin coincidencias por categoría ("Ningún producto en la categoría «Motor»") y combinada, con "Limpiar filtros" |
| I5 | Inventario | Filtro desplegado: Todas las categorías / Aceite / Filtro / Motor / Sin categoría |
| I6 | Inventario | Barra a 390 px: buscador + filtro + "Exportar PDF" sin scroll horizontal de página |
| A1 | Nuevo ingreso | Selector "Categoría" en "Sin categoría"; variante con "Aceite" elegido |
| A2 | Nuevo ingreso | Código dado de baja con el aviso "…con el nombre, el stock y la categoría que indiques." |
| M1 | Modificar stock | Dos líneas: activo con categoría precargada "Filtro" cambiada a "Aceite"; dado de baja con su categoría |
| M2 | Inventario | Resumen tras modificar con "categoría: Filtro → Aceite" |
| O1 | Nueva orden | Línea 1 con categoría "Todas" y producto elegido; línea 2 filtrada por "Filtro" con su lista corta (desktop y 390 px) |
| O2 | Nueva orden | Línea con categoría sin productos activos: "No hay productos en esta categoría." |
| P1 | Impresión | PDF del inventario filtrado por "Aceite": encabezado "Aceite · 3 productos · 2026-11-24", columnas Código / Nombre / Categoría / Stock |
| R10 | Reportes | Reporte del mes generado con columnas Código / Nombre / Categoría / Cantidad / Órdenes ("Sin categoría" atenuado, un dado de baja con su marca), sin filtro de categoría, a 1440 y 390 px |
| P2 | Impresión | PDF del reporte con la columna Categoría (texto "Sin categoría" en papel claro) |

Pantallas a 390x844 y 1440x900; P1 y P2 con `print` emulado y PDF A4 de muestra en `mockups/previews/`. Una vez aprobados, son criterio de aceptación de los grupos de frontend de `tasks.md` y del verify.

## Risks / Trade-offs

- [Migración sobre `dev-local.db` real] → `ADD COLUMN` no reescribe filas; transacción con verificación de conteos y FKs; backup previo documentado (`dev-local.db.bak`) y verify sobre una **copia**. Rollback manual: restaurar el backup (el código viejo ignora la columna nueva, así que incluso sin backup una base migrada sigue funcionando con el código anterior).
- [`ALTER TABLE` dentro de `BEGIN IMMEDIATE`] → soportado por SQLite; se prueba el rollback explícitamente.
- [Orden en `inicializar_esquema`] → la migración debe ir antes de `NORMALIZAR_FECHAS_SQL` (transacción implícita); test de arranque sobre base vieja con movimientos legados cubre ambos pasos juntos.
- [`ProductoOut` con campo nuevo cambia respuestas existentes] → aditivo (los clientes ignoran campos extra); se actualizan los tests de diccionario exacto.
- [Distinguir "ausente" de `null` en las líneas] → `model_fields_set` de Pydantic, encapsulado en el router; tests de ambos casos.
- [La web siempre envía la categoría de cada línea] → una modificación concurrente de la categoría desde otra pestaña se pisaría; mismo comportamiento que el nombre/stock hoy (último gana). Aceptado.
- [Filtro por línea en "Nueva orden" agrega ruido visual en móvil] → mockup O1 a 390 px; alternativa de filtro único lista si el usuario la prefiere.
- [Catálogo cargado una vez] → categorías nuevas (solo por siembra en este change) aparecen al recargar; aceptado.
- [Valor centinela `"__sin__"` del filtro "Sin categoría"] → nunca es una clave válida (el CHECK y la normalización no admiten `_`); solo vive en el navegador.
- [Categorías creadas o renombradas por API mientras la web está abierta] → la web las ve al recargar; un producto con una clave que el catálogo cargado no conoce muestra la clave cruda. Aceptado.
- [Unicidad de nombre sin distinguir tildes] → "Filtro" y "Fíltro" serían distintos; aceptado (caso raro, se corrige renombrando).

## Migration Plan

1. Antes del primer arranque con este change: copiar `dev-local.db` a `dev-local.db.bak` (README).
2. Arrancar uvicorn: `inicializar_esquema` agrega `categoria_id`, crea y siembra `categorias`; log "Agregada la categoría a productos (N producto(s) conservados).".
3. Arranques siguientes: nada (el catálogo ya tiene filas, no se resiembra).
4. Rollback: volver al código anterior (ignora la columna) o restaurar `dev-local.db.bak`.

## Open Questions

- **Sub-decisión 2.6 (borrado de categorías)**: cerrada — no se incluye (usuario, 2026-11-24).
- Sub-decisiones 2.1-2.5, 2.7 y 2.8 (D11): aprobadas por el usuario (2026-11-24).
- Al archivar: KB 04 (tabla `categorias` con clave/nombre únicos, `productos.categoria_id`, siembra solo si vacía), 05 (RN-PR nuevas: categoría opcional, clave normalizada e inmutable, unicidad de clave y nombre, reactivación reemplaza, cambio de categoría sin movimiento ni reactivación), 06 (US-004/US-005 con categoría, US-006 con filtro por categoría en componentes, inventario filtrable, reporte con columna Categoría, administración de categorías por API), 07 (flujos de alta, modificación, orden, inventario filtrado y alta/renombre de categoría en `/docs`); `CHANGES.md` § C-07 con la paridad de D9.

## Decisiones revisadas por el usuario

> Governance MEDIO/ALTO: las 25 decisiones fueron revisadas una por una por el usuario el 2026-11-24. ★ = la recomendada originalmente. El apply no empieza hasta que el usuario apruebe los mockups.

**Decidido por el usuario antes de la revisión (2026-11-24):** categorías de ejemplo motor, aceite y filtro; migración sobre los productos existentes conservando los datos; categoría elegible en "Nuevo ingreso" y "Modificar stock"; filtro del inventario combinable con el buscador y PDF de lo visible; en "Nueva orden" el selector de producto permite elegir entre todos o filtrar por categoría.

1. **Modelo** — aprobada por el usuario (2026-11-24): ★ tabla `categorias` (clave + nombre) con FK desde `productos`.
2. **Administración de categorías** — **cambiada** por el usuario (2026-11-24): sin pantalla web, pero **sí administración solo por API** (usable desde `/docs`): `POST /api/categorias` (crear) y `PATCH /api/categorias/{clave}` (renombrar), protegidos como las demás escrituras. Reglas y sub-decisiones 2.1-2.8 en D11 (borrado: 2.6 no se incluye, aprobado). (Recomendación original: sin administración; solo siembra.)
3. **¿Obligatoria?** — aprobada por el usuario (2026-11-24): ★ opcional; "Sin categoría" = `NULL`.
4. **Productos existentes al migrar** — aprobada por el usuario (2026-11-24): ★ quedan "Sin categoría" y se clasifican a mano.
5. **Clave y nombre** — aprobada por el usuario (2026-11-24): ★ clave minúscula estable en API/BD + nombre para mostrar.
6. **Orden del catálogo** — aprobada por el usuario (2026-11-24): ★ alfabético por nombre; "Sin categoría" al final en los selectores.
7. **Categoría en "Nuevo ingreso"** — aprobada por el usuario (2026-11-24): ★ selector opcional, "Sin categoría" por defecto.
8. **Reactivación por alta** — aprobada por el usuario (2026-11-24): ★ reemplaza la categoría; no afecta el 409.
9. **Categoría en "Modificar stock"** — aprobada por el usuario (2026-11-24): ★ selector por línea precargado, también para dados de baja; solo categoría no reactiva ni registra movimiento.
10. **Semántica en la API de modificación** — aprobada por el usuario (2026-11-24): ★ ausente = no cambia, `null` = quitar, clave = asignar.
11. **Forma de las respuestas** — aprobada por el usuario (2026-11-24): ★ `categoria` en `ProductoOut` + `categoria_anterior` en las líneas de modificación.
12. **Endpoint del catálogo** — aprobada por el usuario (2026-11-24): ★ `GET /api/categorias`; sin `?categoria=` en `/api/inventario`.
13. **Normalización** — aprobada por el usuario (2026-11-24): ★ recorte + minúsculas; vacío = sin categoría; inexistente → 422.
14. **Migración** — aprobada por el usuario (2026-11-24): ★ `ALTER TABLE ADD COLUMN` en una transacción con verificación; siembra idempotente. Refinada por la decisión 2: la siembra ocurre solo si el catálogo está vacío (D1).
15. **Validación de la categoría** — aprobada por el usuario (2026-11-24): ★ en el service contra el catálogo + FK como red.
16. **Mostrar en la tabla** — aprobada por el usuario (2026-11-24): ★ columna "Categoría" de texto.
17. **UI del filtro** — aprobada por el usuario (2026-11-24): ★ `<select>` junto al buscador.
18. **Combinación y conteo** — aprobada por el usuario (2026-11-24): ★ AND con la búsqueda; "V de T productos"; se conserva al recargar.
19. **Sin coincidencias** — aprobada por el usuario (2026-11-24): ★ "Limpiar filtros" limpia ambos; Escape solo el texto.
20. **Opción "Sin categoría" en el filtro** — aprobada por el usuario (2026-11-24): ★ sí.
21. **Filtro en "Nueva orden"** — aprobada por el usuario (2026-11-24): ★ selector de categoría por línea.
22. **Cambiar la categoría de una línea** — aprobada por el usuario (2026-11-24): ★ conserva el producto si pertenece; si no, vuelve a "Elegí un producto…".
23. **PDF del inventario** — aprobada por el usuario (2026-11-24): ★ columna Categoría y nombre de la categoría filtrada en el encabezado.
24. **Órdenes, PDF de orden y reportes** — **cambiada** por el usuario (2026-11-24): la categoría **sí** aparece en `/reportes` como **columna** (tabla en pantalla y PDF del reporte; Código, Nombre, Categoría, Cantidad, Órdenes), **sin filtro** de categoría; `GET /api/reportes/productos-en-ordenes` agrega `categoria` a cada fila (D8b). `/ordenes` y el PDF de una orden siguen sin categoría. (Recomendación original: sin categoría en órdenes ni reportes.)
25. **Paridad C-07** — aprobada por el usuario (2026-11-24): ★ misma tabla y FK nullable en Postgres, RPC de alta/modificación con `p_categoria`; ampliada por las decisiones 2 y 24 (alta/renombre directos con índices únicos; `categoria` en la RPC del reporte) (D9).
