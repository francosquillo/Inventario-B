# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario confirme las sub-decisiones 2.1-2.8 de `design.md` § D11 (la 2.6, borrado, está abierta; las decisiones 1-25 ya fueron revisadas el 2026-11-24: ver § Decisiones revisadas por el usuario) y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`. Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). Funciones puras de JS con Node desde `unittest` (patrón de `tests/test_busqueda_js.py`, se omiten sin Node); el resto del frontend con guardas estáticas (`tests/test_frontend_estatico.py`); el comportamiento en el navegador se verifica en el grupo 12 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorios, services y migración con SQLite real (`:memory:` o archivo temporal) (regla dura 4).
> - Sin dependencias nuevas; `requirements*.txt` intactos; sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - Escrituras multi-tabla y la migración en una transacción, todo o nada (regla dura 3). Categoría validada en el navegador (opciones cerradas) Y en el backend.
> - `tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css`. En JS: datos solo con `textContent`/`createElement`, sin `innerHTML`.
> - **Nunca** abrir, migrar ni borrar `dev-local.db` real durante el apply: los tests usan bases temporales y el verify usa una copia. Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups en `openspec/changes/paso-5e-categorias-productos/mockups/` (`inventario.html` con los modales, importando `design-system/tokens.css` y `ui.css`, cabecera de texto "Inventario" con pestañas, tema oscuro único, README con estados y `Approval: pending`) cubriendo I1-I6, A1-A2, M1-M2, O1-O2 y P1, más `reportes.html` con R10 y P2 (design § UI Mockups). Hecho cuando el README lista cada estado con su archivo
- [x] 0.2 Renderizar a 390x844 y 1440x900 (P1 y P2 con `print` emulado y PDF A4) con Playwright; guardar en `mockups/previews/`, inspeccionar (sin scroll horizontal de página a 390 px) y registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir el JS puro en el verify con `browser_evaluate`)
- [x] 1.3 Recordar al usuario hacer backup de `dev-local.db` (`dev-local.db.bak`) antes del primer arranque con este change; el apply no toca ese archivo

## 2. Esquema y migración — specs `inicializacion-base-datos`, `categorias-productos` (design D1, D2)

- [x] 2.1 RED (`tests/test_sqlite_migracion_categorias.py`, nuevo): DDL de `productos` **viejo copiado literal** + `usuarios`, `ordenes`, `orden_items`, `movimientos` vigentes; tres productos (uno inactivo), una orden con dos ítems y cuatro movimientos → `inicializar_esquema` deja `categoria_id` en `productos` con `NULL` en las tres filas y las demás columnas idénticas; verificar rojo
- [x] 2.2 GREEN: `categorias` en `_ESQUEMA_PLANTILLA` (antes de `productos`; clave con CHECK de formato, nombre `UNIQUE COLLATE NOCASE` 1-40), `categoria_id` en el DDL nuevo de `productos`, `_migrar_productos_categoria` (`ALTER TABLE ADD COLUMN` + siembra solo si el catálogo está vacío, en `_transaccion`, verificación de conteos y `foreign_key_check`, log) llamada tras `_migrar_movimientos` y antes de `NORMALIZAR_FECHAS_SQL`. Verificar verde
- [x] 2.3 TRIANGULATE: órdenes, ítems y movimientos intactos (ids y datos); siembra `motor`/`aceite`/`filtro`; tres arranques seguidos sin cambios ni duplicados; categoría asignada después se conserva en arranques siguientes; catálogo con `motor` renombrado y `frenos` creado no se resiembra ni cambia; base vieja con movimientos legados (sin `ajuste`) migra ambas cosas en el mismo arranque; falla inyectada después del `ALTER` → `productos` sin la columna, sin siembra parcial y la excepción sube
- [x] 2.4 RED→GREEN (`tests/test_sqlite_schema.py`): base nueva con seis tablas; `UNIQUE(clave)`; nombre único sin distinguir mayúsculas (`Aceite`/`ACEITE`); CHECK de clave (mayúsculas, espacios, `_`, guion en los bordes, vacía, > 30 rechazadas); nombre vacío o > 40 rechazado; producto con `categoria_id` inexistente rechazado por FK
- [x] 2.5 REFACTOR; suite verde

## 3. Repositorios — specs `categorias-productos`, `consulta-inventario`, `alta-productos`, `modificacion-stock` (design D3)

- [x] 3.1 RED (`tests/test_sqlite_categoria_repository.py`, nuevo): `SqliteCategoriaRepository(conn).listar()` → `[Categoria("aceite","Aceite"), Categoria("filtro","Filtro"), Categoria("motor","Motor")]`; verificar rojo
- [x] 3.2 GREEN: `Categoria` en `domain/entities.py`, `CategoriaRepository` en `base.py`, implementación SQL. Verificar verde
- [x] 3.3 RED→GREEN (`tests/test_sqlite_producto_repository.py`, `test_sqlite_repositories.py`): `Producto.categoria` (default `None`); `listar_activos` y `listar_inactivos` devuelven la clave o `None` (proyección común `p … LEFT JOIN categorias c`)
- [x] 3.4 RED→GREEN (`tests/test_sqlite_stock_repository.py`): `dar_de_alta(..., categoria="aceite", ...)` crea con la categoría; con `None` sin categoría; reactivación reemplaza la categoría (a otra y a `None`); 409 (`ProductoDuplicado`) igual con cualquier categoría; atomicidad intacta
- [x] 3.5 RED→GREEN: `modificar` con `LineaModificacion(cambia_categoria=True, categoria="motor")` asigna; `cambia_categoria=True, categoria=None` quita; `cambia_categoria=False` no toca; solo categoría sobre activo → sin movimiento; solo categoría sobre dado de baja → sigue inactivo, `reactivado=False`; `ResultadoModificacion.categoria`/`categoria_anterior`; misma categoría → sin `UPDATE` de categoría; egreso, baja y reintegro devuelven la categoría sin cambiarla
- [x] 3.6 RED→GREEN (`tests/test_sqlite_categoria_repository.py`): `crear(clave, nombre)` (devuelve la categoría; clave o nombre repetidos → `CategoriaDuplicada` traducida desde el `IntegrityError`, sin filas nuevas), `obtener(clave)` (`None` si no existe), `renombrar(clave, nombre)` (cambia solo el nombre; productos conservan `categoria_id`; inexistente → `CategoriaNoEncontrada`; nombre de otra → `CategoriaDuplicada`); escrituras en `_transaccion`
- [x] 3.7 RED→GREEN (`tests/test_sqlite_reporte_repository.py`): `productos_en_ordenes` devuelve `ProductoEnOrdenes.categoria` (clave o `None`, categoría **actual**), incluido un dado de baja; el orden y los totales no cambian; `productos_usados` sin cambios
- [x] 3.8 REFACTOR (una sola proyección de producto); suite verde

## 4. Services — specs `categorias-productos`, `alta-productos`, `modificacion-stock` (design D3)

- [x] 4.1 RED (`tests/test_normalizacion_stock.py` o nuevo): `normalizar_categoria("  Filtro ")` → `"filtro"`; `"   "` y `None` → `None`; `3` → `DatosInvalidos("El campo categoria debe ser texto.")`; verificar rojo
- [x] 4.2 GREEN: `normalizar_categoria` en `services/normalizacion.py`. Verificar verde
- [x] 4.3 RED→GREEN (`tests/test_stock_service.py`, SQLite real): `StockService(stock_repo, categoria_repo, ahora=…)`; `dar_de_alta(..., categoria="encendido")` → "La categoría 'encendido' no existe." sin crear nada; `"Aceite"` → crea con `aceite`; clave de 31+ caracteres → mensaje recortado. Actualizar los constructores de `StockService` en tests y en `api/dependencies.py`
- [x] 4.4 RED→GREEN (`tests/test_modificacion_service.py`): línea 2 con `"frenos"` → "Línea 2: La categoría 'frenos' no existe." y nada cambia; prioridad: categoría inválida en línea 3 + repetido en línea 2 → gana la primera línea inválida según el orden actual de validación; `cambia_categoria` se propaga
- [x] 4.5 RED→GREEN: `CategoriaService.listar()` (`services/categoria_service.py`, nuevo)
- [x] 4.6 RED→GREEN (`tests/test_categoria_service.py`, nuevo, SQLite real): `clave_desde_texto("  Tren delantero ")` → `tren-delantero`; `"Encendido / Bujías"` → `encendido-bujias`; `"***"` → `DatosInvalidos` de formato; recorte a 30 sin guion final; `crear("Tren delantero")` deriva la clave; `crear("Sistema de frenos", " Frenos ")` → `frenos`; clave `"fre nos!"` → 422 de formato; `crear("Motor diésel", "MOTOR")` → `CategoriaDuplicada` por clave; `crear("ACEITE", "lubricante")` → por nombre (`casefold`, también con tildes/Ñ); nombre vacío → "El campo nombre es obligatorio."; 41 caracteres → "El nombre de la categoría admite hasta 40 caracteres."
- [x] 4.7 RED→GREEN: `renombrar("MOTOR", "Motor y transmisión")` normaliza la clave de la ruta; mismo nombre → sin error; solo mayúsculas (`aceite` → "ACEITE") permitido; nombre de otra → `CategoriaDuplicada`; inexistente → `CategoriaNoEncontrada`
- [x] 4.8 REFACTOR; suite verde

## 5. API — spec `api-http` (design D4)

- [x] 5.1 RED (`tests/test_api_categorias.py`, nuevo): `GET /api/categorias` sin sesión → 401; con sesión → 200 con la lista exacta ordenada por nombre; verificar rojo
- [x] 5.2 GREEN: `CategoriaOut`, `get_categoria_service`, router `api/routers/categorias.py`, `include_router` en `api/app.py`. Verificar verde
- [x] 5.3 RED→GREEN (`tests/test_api_inventario.py`, `test_api_productos.py`): `categoria` en `GET /api/inventario` y `GET /api/productos/inactivos` (`null` y clave); actualizar las aserciones de diccionario exacto de `ProductoOut` en egreso, baja y alta
- [x] 5.4 RED→GREEN (`tests/test_api_alta_productos.py`): alta con `"categoria": "Aceite"` → 201 `categoria: "aceite"`; sin categoría → `null`; reactivación sin categoría → `null`; 422 "La categoría 'encendido' no existe."; `"categoria": 3` → 422 "El campo categoria debe ser texto."; 409 con categoría válida
- [x] 5.5 RED→GREEN (`tests/test_api_modificaciones.py`): respuesta con `categoria` y `categoria_anterior`; `categoria` ausente → no cambia; `null` → quita; `"frenos"` en línea 2 → 422 con prefijo y sin cambios; `"categoria": 3` → 422 "Línea 1: El campo categoria debe ser texto."
- [x] 5.6 RED→GREEN (`tests/test_api_categorias.py`): `POST /api/categorias` → 201 con clave derivada y luego visible en `GET`; 409 clave/nombre repetidos con los `detail` exactos; 422 nombre faltante/vacío/largo y clave inválida; 401 sin sesión sin crear; `CategoriaDuplicada` → 409 y `CategoriaNoEncontrada` → 404 registrados en `api/app.py`
- [x] 5.7 RED→GREEN: `PATCH /api/categorias/{clave}` → 200 `{clave, nombre}` (con `MOTOR` en la ruta); productos conservan la categoría; 404 inexistente; 409 nombre de otra; 422 si el cuerpo trae `clave` ("La clave de una categoría no se puede cambiar."); 401 sin sesión
- [x] 5.8 RED→GREEN (`tests/test_api_csrf.py`): `POST /api/categorias` y `PATCH /api/categorias/motor` con `text/plain`, formulario y multipart → 422 y catálogo sin cambios
- [x] 5.9 RED→GREEN (`tests/test_api_reportes.py`): cada fila de `GET /api/reportes/productos-en-ordenes` trae `categoria` (`null` y clave; dado de baja incluido); actualizar las aserciones de diccionario exacto; sin parámetro de categoría en el OpenAPI
- [x] 5.10 RED→GREEN (`tests/test_api_app.py` y donde se cuenten rutas): OpenAPI con 17 rutas; `/api/categorias` con `GET` y `POST`, `/api/categorias/{clave}` solo `PATCH`; ninguna ruta de página
- [x] 5.11 REFACTOR; suite completa verde

## 6. JS puro del filtro — spec `interfaz-web` (Filtro por categoría, Conteo, Sin coincidencias) (design D5)

- [x] 6.1 RED (`tests/test_busqueda_js.py`): `Busqueda.filtrar(productos, "", "aceite")` → solo los de `aceite` en orden; verificar rojo
- [x] 6.2 GREEN: tercer parámetro opcional `categoria` en `filtrar` (`""` = todas; `"__sin__"` = sin categoría); sin él, comportamiento de C-06c idéntico. Verificar verde
- [x] 6.3 TRIANGULATE: combinado texto + categoría (AND); `"__sin__"`; categoría sin productos → `[]`; texto sin tildes + categoría; `conteo` con filtro de categoría ("3 de 12 productos", V = T → "12 productos"); `mensajeSinCoincidencias(texto, nombreCategoria)` con las tres variantes de la spec y texto literal
- [x] 6.4 RED→GREEN: función pura para la nueva orden (`Busqueda.porCategoria(productos, categoria)` o equivalente en un módulo puro) + "conservar o resetear" (`productoSigueVisible(codigo, productos, categoria)`)
- [x] 6.5 REFACTOR; tests de C-06c verdes sin cambios

## 7. Inventario: columna, filtro, conteo, sin coincidencias, recarga — spec `interfaz-web` (mockups I1-I6) (design D5)

- [x] 7.1 RED (guardas): `index.html` con `<th>` "Categoría" entre Nombre y Stock, `#inv-categoria` `<select>` con `label` y opción "Todas las categorías", botón `#inv-limpiar` "Limpiar filtros"; `inventario.js` llama a `/api/categorias` y usa `Busqueda.filtrar` con la categoría; sin `innerHTML`. Verificar rojo
- [x] 7.2 GREEN: HTML según I1/I6 y JS: carga paralela del catálogo (falla tolerada: clave cruda y solo "Todas"), columna con nombre o "Sin categoría" atenuado, filtro combinado, conteo, cartel con las tres variantes, "Limpiar filtros" (limpia ambos, foco en "Buscar"), Escape limpia solo el texto, filtro conservado al recargar. Verificar verde
- [x] 7.3 REFACTOR; guardas globales verdes

## 8. "Nuevo ingreso" — spec `interfaz-web` (Modal de nuevo ingreso) (mockups A1-A2) (design D6)

- [x] 8.1 RED (guardas): `#nu-categoria` `<select>` con `label` y opción "Sin categoría"; el aviso de baja dice "…con el nombre, el stock y la categoría que indiques."; el cuerpo de `POST /api/productos` incluye `categoria`. Verificar rojo
- [x] 8.2 GREEN: selector lleno desde el catálogo, por defecto "Sin categoría" (`null`), reinicio al abrir el modal. Verificar verde

## 9. "Modificar stock" — spec `interfaz-web` (Modal de modificar stock, Resumen) (mockups M1-M2) (design D6)

- [x] 9.1 RED (guardas + JS puro del resumen si se extrae): `tpl-mline` con `select[data-categoria]` etiquetado; cada línea envía `categoria`; el resumen contiene "categoría: ". Verificar rojo
- [x] 9.2 GREEN: selector por línea, precarga con la categoría del producto elegido (activo o dado de baja), envío de la clave o `null`, resumen "categoría: Filtro → Aceite" cuando cambia. Verificar verde

## 10. "Nueva orden" — spec `interfaz-web` (Modal de nueva orden, Filtro por categoría en la nueva orden) (mockups O1-O2) (design D7)

- [x] 10.1 RED (guardas): cada línea creada por `nuevaLinea` tiene un `select` de categoría etiquetado ("Categoría de la línea N") con "Todas", antes del de producto; ayuda "No hay productos en esta categoría."; el cuerpo de `POST /api/ordenes` no incluye `categoria`. Verificar rojo
- [x] 10.2 GREEN: `llenarSelect` con filtro por categoría; cambio de categoría conserva o resetea el producto (función pura del grupo 6); refrescos tras recarga respetan la categoría de cada línea; layout según O1 (desktop y 390 px). Verificar verde
- [x] 10.3 REFACTOR; suite completa verde

## 11. PDF del inventario y documentación — spec `interfaz-web` (Exportar el inventario a PDF) (mockup P1) (design D8)

- [x] 11.1 RED (guardas / JS puro): la línea del encabezado con categoría elegida es "<Categoría> · N productos · AAAA-MM-DD"; sin categoría, igual que C-06c. Verificar rojo
- [x] 11.2 GREEN: `exportarInventario` con la categoría; la columna Categoría se imprime (CSS de impresión solo si hace falta, en `app.css`). Verificar verde
- [x] 11.3 RED (guardas `tests/test_frontend_estatico.py` + JS puro `tests/test_reportes_js.py` si se extrae la etiqueta): `reportes.html` con `<th>` "Categoría" entre Nombre y Cantidad; `reportes.js` llama a `/api/categorias` (falla tolerada) y muestra el nombre o "Sin categoría"; sin `<select>` de categoría en `/reportes`; sin `innerHTML`. Verificar rojo (mockups R10, P2; design D8b)
- [x] 11.4 GREEN: columna en la tabla del reporte y en su PDF; resumen, encabezado y nombre de archivo sin cambios. Verificar verde; REFACTOR
- [x] 11.5 `README.md`: categorías (catálogo sembrado, opcional, administración solo por API desde `/docs`: crear y renombrar, clave inmutable), filtro del inventario, categoría en los modales y en el reporte, `GET`/`POST /api/categorias` y `PATCH /api/categorias/{clave}`, y nota de migración con **backup de `dev-local.db` antes del primer arranque** (como C-06b)

## 12. Verify

- [x] 12.1 Suite completa verde (baseline + nuevos); `openspec validate paso-5e-categorias-productos --strict` sin errores
- [x] 12.2 Migración sobre una **copia** de `dev-local.db` (por ejemplo `scratch/dev-local-copia.db`, con `INVENTARIO_DB_PATH` apuntando a la copia): conteos de `productos`, `ordenes`, `orden_items` y `movimientos` iguales antes y después, todos los productos "Sin categoría", log de migración una sola vez, segundo arranque sin cambios, `PRAGMA integrity_check` = `ok`. El archivo original no se toca
- [x] 12.3 `/docs`: `GET /api/categorias`, crear una categoría (clave derivada), renombrarla, 409 por nombre repetido, reporte con `categoria`, alta de producto con categoría, modificación asignando y quitando categoría, 422 de categoría inexistente, con la cookie de sesión
- [x] 12.4 Playwright contra la app real (uvicorn sobre la copia migrada + algunos productos clasificados) a 390x844 y 1440x900, comparando con I1-I6, A1-A2, M1-M2, O1-O2 y R10: filtro + búsqueda, reporte con la columna Categoría, categoría creada en `/docs` visible tras recargar, conteo, "Limpiar filtros", recarga conservando filtros, alta con categoría, modificación con cambio de categoría de un dado de baja, orden con líneas filtradas; capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos
- [x] 12.5 Impresión: con `print` emulado y `page.pdf` (A4) comparar con P1 (columna Categoría, encabezado con la categoría, sin filtros ni nav) y P2 (reporte con columna Categoría)
- [x] 12.6 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar la KB 04 (tabla `categorias` con clave y nombre únicos, `productos.categoria_id`, siembra solo si vacía, migración), 05 (RN-PR de categoría: opcional, clave normalizada e inmutable, unicidad, reactivación reemplaza, cambio sin movimiento ni reactivación; administración solo por API), 06 (US-004/US-005 con categoría, US-006 con filtro por categoría en componentes, inventario filtrable, reporte con columna Categoría, alta/renombre de categorías por API) y 07 (flujos con categoría y filtro).
- En `CHANGES.md`: marcar `[x]` C-06e con la fecha y anotar en C-07 la paridad (tabla `categorias` con índice único en `lower(nombre)`, FK nullable, siembra solo si vacía, alta/renombre como operaciones directas con 23505 → 409, `p_categoria` en las RPC de alta y modificación, `categoria` en la RPC `productos_en_ordenes`).
- Esperar "Continuar" del usuario antes de proponer C-06f (`paso-5f-procesos-ordenes`).
