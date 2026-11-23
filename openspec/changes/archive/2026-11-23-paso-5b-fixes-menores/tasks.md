# Tasks

> **GATE: el apply NO empieza hasta que `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`** y el usuario haya revisado las 15 "Decisiones a confirmar por el usuario" (governance MEDIO/ALTO). Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). Para el frontend, el RED de `unittest` son las guardas estáticas (design D6); el comportamiento en el navegador se verifica en el grupo 12 contra los escenarios de `specs/interfaz-web` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente, SQLite real (`:memory:` o archivo temporal vía `tests/helpers`), sin mocks de base; los fallos a mitad de transacción se provocan con triggers SQLite creados en el test (regla dura 4).
> - Sin dependencias nuevas; FastAPI y Pydantic solo en `inventario/api/` (regla dura 1).
> - Alta y modificación en una transacción, todo o nada (regla dura 3); validación en frontend **y** backend.
> - `POST /api/stock/ingreso|egreso`, órdenes, baja y login no cambian ni cambian sus tests. Solo cambian aserciones existentes donde la spec lo modifica: cantidad de rutas OpenAPI (10 → 13), campos de `GET /api/movimientos`, CHECK de `tipo` en el esquema y las guardas de los modales de ingreso/egreso del frontend.
> - Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).
> - En JS: datos solo con `textContent`/`createElement`; nada de `innerHTML` (design D5).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups en `openspec/changes/paso-5b-fixes-menores/mockups/` (`inventario.html` que importa `design-system/tokens.css` y `ui.css`, cabecera de texto "Inventario", tema oscuro único, README con estados y `Approval: pending`) cubriendo I1, I2, NI1-NI6, MS1-MS8, T1, T1b y T2
- [x] 0.2 Renderizar cada estado a 390x844 y 1440x900 con Playwright, guardar en `mockups/previews/`, inspeccionar y corregir defectos; registrar `Preview: rendered (2026-11-20)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita (y la revisión de las 15 decisiones); registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Copiar `dev-local.db` (si existe) a un respaldo fuera del repo antes de arrancar la app con código nuevo; no tocar `.env`
- [x] 1.2 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`); si algo falla, detenerse y reportarlo como falla preexistente

## 2. Esquema y migración de `movimientos` — specs `inicializacion-base-datos` (design D4)

- [x] 2.1 RED (`tests/test_sqlite_schema.py`): en una base nueva, un movimiento `ajuste` con `stock_anterior` 7, `stock_nuevo` 4, `cantidad` 3 se acepta; verificar rojo (CHECK viejo)
- [x] 2.2 GREEN: actualizar `ESQUEMA_SQL` con el DDL de design D4. Verificar verde y que el resto de `test_sqlite_schema` sigue verde
- [x] 2.3 TRIANGULATE: se rechazan `ajuste` sin anterior o sin nuevo, con ambos iguales, con negativos, con `cantidad` distinta de la diferencia; `ingreso`/`egreso` con `stock_anterior` o `stock_nuevo`; `tipo` fuera de los tres valores (actualizar el test de tipo inválido según la spec modificada)
- [x] 2.4 RED (`tests/test_sqlite_migracion.py`): crear una base con el DDL **viejo** de `movimientos` (literal en el test) y tres filas; `inicializar_esquema` → la tabla tiene `stock_anterior`/`stock_nuevo` y admite `ajuste`; mismos ids, fechas, tipos, cantidades y usuarios; stock de productos sin cambios. Verificar rojo
- [x] 2.5 GREEN: `_migrar_movimientos(conn)` en `sqlite_repo.py` (detección por `PRAGMA table_info`, `BEGIN IMMEDIATE`, crear/copiar/borrar/renombrar, recrear índices, `foreign_key_check`, conteo), llamada entre `executescript` y la normalización de fechas. Verificar verde
- [x] 2.6 TRIANGULATE: segunda y tercera inicialización no cambian nada (idempotente); fallo provocado a mitad (p. ej. trigger `BEFORE INSERT` en la tabla nueva vía tabla `movimientos_nueva` preexistente con trigger, o conteo distinto) → `ROLLBACK`, esquema viejo y filas intactos, la excepción sube; filas con fecha legada se normalizan después de migrar; índices presentes
- [x] 2.7 REFACTOR: constantes SQL nombradas; suite completa verde

## 3. Dominio y validación compartida (design D2, D3)

- [x] 3.1 RED (`tests/test_domain.py`, `tests/test_normalizacion` donde corresponda): `validar_stock` acepta 0 y 10.000 y rechaza -1, 10.001, 2.5, `"5"`, `True` con "El stock debe ser un entero entre 0 y 10.000."; `ProductoDuplicado('A-01')` → "Ya existe un producto con código 'A-01'."; `ProductosInexistentes(['Z-01'])` / `(['Z-01','Z-02'])` → mensajes de la spec y `codigos`
- [x] 3.2 GREEN: `validar_stock` en `services/normalizacion.py`; `ProductoDuplicado`, `ProductosInexistentes` en `domain/errors.py`; entidades `LineaModificacion` y `ResultadoModificacion` (`codigo, nombre, stock, modo, stock_anterior, nombre_anterior, reactivado`, `sin_stock`) en `domain/entities.py`; extender `Movimiento` con `stock_anterior`/`stock_nuevo` opcionales (default `None`). Verificar verde

## 4. Alta de producto — spec `alta-productos` (design D3)

- [x] 4.1 RED (`tests/test_sqlite_stock_repository.py`): `dar_de_alta('N-01','Arandela 6mm',10,...)` crea activo con stock 10 y un `ingreso` de 10; verificar rojo
- [x] 4.2 GREEN: método abstracto en `StockRepository` y `SqliteStockRepository.dar_de_alta` en `_transaccion`. Verificar verde
- [x] 4.3 TRIANGULATE: stock 0 → sin movimiento; código activo → `ProductoDuplicado` sin cambios; inactivo con stock 2 → activo, nombre y stock nuevos (6), `ajuste` 2→6, `reactivado=True`; inactivo con mismo stock → sin movimiento; `IntegrityError` del UNIQUE → `ProductoDuplicado`; fallo del movimiento (trigger) → no existe el producto
- [x] 4.4 RED→GREEN (`tests/test_stock_service.py`): `StockService.dar_de_alta` normaliza código y nombre, exige nombre ("El campo nombre es obligatorio." para `None`, `""`, `"   "`), valida stock con `validar_stock`, usa el reloj inyectado
- [x] 4.5 REFACTOR; suite verde

## 5. Modificación en lote — spec `modificacion-stock` (design D2)

- [x] 5.1 RED (`tests/test_sqlite_stock_repository.py`): `modificar` con `A-01` fijar 12 (de 5) y `B-10` sumar 4 (de 0) → stocks 12 y 4, un `ajuste` 5→12 cantidad 7 y un `ingreso` 4, resultados en orden; verificar rojo
- [x] 5.2 GREEN: método abstracto y `SqliteStockRepository.modificar` (lectura de todos los códigos activos e inactivos, `ProductosInexistentes`, aplicación por línea) en una transacción. Verificar verde
- [x] 5.3 TRIANGULATE: fijar mismo stock → sin movimiento ni cambio; nombre nuevo → renombra sin movimiento; mismo nombre → sin cambio; inactivo con sumar → reactivado y `ingreso`; inactivo con fijar valor distinto > 0 → reactivado y `ajuste`; inactivo con fijar 0 (distinto del actual) → sigue inactivo con stock 0, `ajuste` registrado y `reactivado=False`; inactivo con fijar el mismo stock → sigue inactivo, sin movimiento; inactivo solo renombrado → sigue inactivo, nombre nuevo, sin movimiento; en los tres casos que no reactivan el producto sigue en `listar_inactivos` y fuera del inventario; códigos inexistentes (varios) → excepción con todos y nada aplicado; fallo del segundo movimiento (trigger) → nada aplicado
- [x] 5.4 RED (`tests/test_modificacion_service.py`): `StockService.modificar` — lista vacía/`None`/101 líneas; "Línea N: " + código vacío/largo, modo inválido ("El campo modo debe ser fijar o sumar."), stock fuera de 0..10.000, cantidad fuera de 1..10.000, nombre > 120; repetido tras normalizar → "Línea 3: el producto 'A-01' ya está en la línea 1."; la primera línea inválida gana; validación antes que inexistencia. Verificar rojo
- [x] 5.5 GREEN: implementar la validación en el service (patrón de `_consolidar`). Verificar verde
- [x] 5.6 TRIANGULATE: bordes 0, 10.000, 1, 100 líneas aceptados; nombre `"  X  "` recortado; nombre en blanco = sin cambio
- [x] 5.7 REFACTOR; suite verde

## 6. Consulta de movimientos con ajuste — specs `consulta-movimientos`, `api-http` (design D1)

- [x] 6.1 RED: `SqliteMovimientoRepository.listar` devuelve `stock_anterior`/`stock_nuevo` (enteros en `ajuste`, `None` en el resto); `GET /api/movimientos` incluye ambas claves (`null` en ingresos/egresos); verificar rojo
- [x] 6.2 GREEN: SELECT, `_a_movimiento`, `MovimientoOut` y `movimiento_out`. Actualizar las aserciones de forma exacta existentes en `tests/test_api_movimientos.py` según la spec modificada. Verificar verde
- [x] 6.3 TRIANGULATE: movimientos previos a la migración se listan sin anterior/nuevo; filtro por código incluye el `ajuste`

## 7. API — spec `api-http` (design D1)

- [x] 7.1 RED (`tests/test_api_productos.py`): `POST /api/productos` `{"codigo":"n-01","nombre":"Arandela 6mm","stock":0}` → 201 con el cuerpo exacto de la spec; verificar rojo
- [x] 7.2 GREEN: `AltaProductoRequest` (strict, strip) e `ingreso_out` reutilizado; ruta `POST ""` con `status_code=201`; `get_stock_service` en el router de productos; `ProductoDuplicado` → 409 en `app.py`. Verificar verde
- [x] 7.3 TRIANGULATE: reactivación 201 `reactivado:true`; 409 código activo; 422 nombre faltante/blanco, stock -1/10001/`"5"`, stock faltante ("El campo stock es obligatorio."); 401 sin sesión; mapear en `errores_validacion.py` el campo `stock` a "El stock debe ser un entero entre 0 y 10.000." (salvo `missing`)
- [x] 7.4 RED→GREEN: `GET /api/productos/inactivos` (declarado antes del `DELETE /{codigo:path}`): orden por código, `[]`, 401; `ProductoRepository.listar_inactivos` + `ProductoService.listar_inactivos`; `DELETE /api/productos/INACTIVOS` sigue llegando al handler de baja (404 si no existe)
- [x] 7.5 RED (`tests/test_api_stock.py`): `POST /api/stock/modificaciones` con el cuerpo del escenario "Fijar y sumar" → 200 con `lineas` exactas; verificar rojo
- [x] 7.6 GREEN: `LineaFijar`/`LineaSumar` con `Field(discriminator="modo")`, `ModificacionRequest` (1..100), `LineaModificadaOut`; ruta en el router de stock; handler de `ProductosInexistentes` → 404 `{detail, codigos}`. Verificar verde
- [x] 7.7 TRIANGULATE: reactivación con fijar valor > 0 (`reactivado:true`) y con sumar; fijar 0 en inactivo → 200 `stock:0`, `reactivado:false`, sigue en `/api/productos/inactivos` y fuera de `/api/inventario`; fijar mismo stock y solo renombrar en inactivo → `reactivado:false`; 404 con `codigos`; 422 "Línea 1: El campo modo debe ser fijar o sumar." (modo inválido y faltante: `union_tag_invalid`/`union_tag_not_found`), "Línea 2: El campo stock es obligatorio.", "Línea 2: La cantidad debe ser un entero entre 1 y 10.000.", repetido, lista vacía/101; 401. Extender `errores_validacion._linea` para `lineas` → "Línea N" (sin romper "Componente N") e ignorar el segmento del discriminador en `loc`
- [x] 7.8 TRIANGULATE CSRF (`tests/test_api_csrf.py`): los dos POST nuevos con `text/plain`, `x-www-form-urlencoded` y `multipart/form-data` → 422 sin efectos
- [x] 7.9 OpenAPI: actualizar `DocsTest` y el test de rutas de C-06 a las trece rutas y operaciones de la spec; las rutas de página siguen fuera. Verificar
- [x] 7.10 REFACTOR; suite completa verde (los tests de `/api/stock/ingreso|egreso`, órdenes y baja sin cambios)

## 8. Validación del navegador — spec `interfaz-web` (design D5)

- [x] 8.1 RED (`tests/test_frontend_estatico.py`): `validacion.js` expone `stock` y `lineasModificacion` y contiene los mensajes "El stock debe ser un entero entre 0 y 10.000.", "Elegí un producto." y "ya está en la línea"; verificar rojo
- [x] 8.2 GREEN: implementar ambas funciones puras (sin DOM ni `fetch`). Verificar verde

## 9. Modal "Nuevo ingreso" — spec `interfaz-web` (mockups NI1-NI6)

- [x] 9.1 RED (guardas): `index.html` tiene el botón "Nuevo ingreso", `modal-nuevo` con `aria-labelledby`, Código/Nombre/Stock con etiqueta, Stock con `inputmode="numeric"`; no hay "Ingreso de stock" ni `modal-ingreso`. Reemplazar las guardas viejas del ingreso (spec: requisito REMOVED). Verificar rojo
- [x] 9.2 GREEN: HTML del modal según NI1 y JS (`abrirNuevo`, validación, `POST /api/productos`, aviso de dado de baja con la lista de inactivos, 409 con alerta + `aria-invalid`/`aria-describedby`/foco en Código, alertas de éxito "Producto creado/reactivado: …"); quitar el código del ingreso viejo. CSS nuevo solo en `static/css/app.css`. Verificar verde

## 10. Modal "Modificar stock" — spec `interfaz-web` (mockups MS1-MS8)

- [x] 10.1 RED (guardas): botón "Modificar stock", `modal-modificar` con `aria-labelledby`, plantilla de línea con `fieldset` de radios "Fijar en"/"Sumar", "Agregar producto", "Guardar cambios"; no hay "Egreso de stock" ni `modal-egreso`; `inventario.js` usa `/api/stock/modificaciones` y `/api/productos/inactivos` y ningún JS menciona `/api/stock/ingreso` ni `/api/stock/egreso`. Verificar rojo
- [x] 10.2 GREEN: HTML y JS según MS1-MS8: carga paralela de activos e inactivos, `<optgroup>` "Activos"/"Dados de baja", deshabilitar elegidos, aviso por línea de un dado de baja ("se va a reactivar al guardar" solo si el stock cambia y queda > 0; si no, "sigue dado de baja (sin cambio de stock)" / "(stock 0)", según MS2/MS3), valor propuesto = stock actual en "Fijar en", "Stock actual A → B", nombre solo si no está vacío, 1..100 líneas, mapeo de 422 "Línea N" y 404 `codigos`, "Guardando…", resumen persistente con `createElement`/`textContent`; quitar el código del egreso viejo
- [x] 10.2b Guardas del JS (RED→GREEN): el aviso y la marca "reactivado" del resumen dependen de `reactivado` de la respuesta; el resumen no marca "reactivado" en un dado de baja que sigue dado de baja
- [x] 10.3 Cartel de inventario vacío: "Creá el primero con Nuevo ingreso." (guarda + HTML)
- [x] 10.4 REFACTOR: compartir la mecánica de líneas con la nueva orden sin cambiar su comportamiento; suite completa verde (guardas de `ordenes.html`, `login.html` y nueva orden intactas)

## 11. Documentación local

- [x] 11.1 `README.md` "Correr en local": copiar `dev-local.db` antes del primer arranque con este change (migración automática de `movimientos`)

## 12. Verify

- [x] 12.1 Suite completa verde; `openspec validate paso-5b-fixes-menores --strict`
- [x] 12.2 Playwright contra la app real (uvicorn + base temporal) a 390x844 y 1440x900, comparando con los mockups aprobados (NI*, MS*, I1, I2): capturas en `mockups/verify/`, consola sin errores, red sin fallos; `validacion.js` con `browser_evaluate` sobre una tabla de casos (stock 0/-1/2.5/10.000/10.001, líneas vacías y repetidas)
- [x] 12.3 Migración real: arrancar sobre una **copia** de `dev-local.db` y comprobar que los movimientos se conservan (`GET /api/movimientos` antes/después) y que un ajuste nuevo aparece con anterior/nuevo
- [x] 12.4 Probar en `/docs` los tres endpoints nuevos y que `/api/stock/ingreso|egreso` siguen funcionando (verificado vía `/openapi.json` y llamadas reales; Swagger UI no abierta a mano)
- [x] 12.5 Registrar `Visual verify:` en `design.md`

## 13. Cierre (archive)

- [x] 13.1 Actualizar la KB: 04, 05, 06 y 07 según `design.md` § Open Questions
- [x] 13.2 Marcar `[x]` C-06b en `CHANGES.md` y esperar "Continuar" del usuario antes de C-07
