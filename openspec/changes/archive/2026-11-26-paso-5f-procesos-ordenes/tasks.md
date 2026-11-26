# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario revise las decisiones 1-26 de `design.md` § "Decisiones para revisión del usuario" y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`. Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). JS puro con Node desde `unittest` (patrón de `tests/test_busqueda_js.py`, se omite sin Node); resto del frontend con guardas estáticas (`tests/test_frontend_estatico.py`); el navegador se verifica en el grupo 13 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorios, services y migración con SQLite real (`:memory:` o archivo temporal) (regla dura 4).
> - Sin dependencias nuevas; sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - Alta y borrado de orden (con procesos) y la migración en una transacción, todo o nada (regla dura 3). Procesos validados en el navegador Y en el backend.
> - `tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css`. En JS: datos solo con `textContent`/`createElement`, sin `innerHTML`.
> - **Nunca** migrar ni borrar `dev-local.db` real durante el apply (solo se copia en 1.3); tests con bases temporales y verify sobre una copia. Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups LITE en `openspec/changes/paso-5f-procesos-ordenes/mockups/` (`nueva-orden.html` N1-N2, `ordenes.html` L1-P1, `README.md` con estados y `Approval: pending`; reutilizan los de C-06e y C-06c)
- [x] 0.2 Renderizado a 390x844 y 1440x900 (P1 con `print` emulado, sin PDF A4) en `mockups/previews/`; `Preview: rendered (2026-11-24)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir el JS puro en el verify con `browser_evaluate`)
- [x] 1.3 Backup: copiar `dev-local.db` a `dev-local.bak-5f.db` en la raíz (copia de archivo, sin abrirlo con SQLite; `*.db` está en `.gitignore`) y confirmar con `git status` que no aparece; verificar que ambos archivos tienen el mismo tamaño

## 2. Esquema, siembra y migración — specs `inicializacion-base-datos`, `procesos-ordenes`, `categorias-productos` (design D1, D2, D4)

- [x] 2.1 RED (`tests/test_sqlite_migracion_procesos.py`, nuevo): DDL de C-06e **copiado literal** (seis tablas) con dos órdenes con ítems, productos con categoría y movimientos → `inicializar_esquema` crea `procesos` (con `cambio-motor`, `cambio-filtro`, `limpieza`) y `orden_procesos` vacía; verificar rojo
- [x] 2.2 GREEN: `_crear_procesos(conn)` (DDL de D1 + siembra en `_transaccion`, verificación de conteos, log) llamada tras `_migrar_productos_categoria` y antes de `NORMALIZAR_FECHAS_SQL`. Verificar verde
- [x] 2.3 TRIANGULATE: filas existentes idénticas (ordenes, orden_items, productos, categorias, movimientos); tres arranques sin duplicar; procesos renombrados/creados/borrados se conservan; catálogo de procesos vaciado no se resiembra; falla inyectada en la siembra → no existen `procesos` ni `orden_procesos` y la excepción sube
- [x] 2.4 RED→GREEN (siembra de categorías, D2): base nueva siembra; base con `categorias` existente y vacía (las tres borradas) → reinicio sin resiembra; base pre-C-06e (sin `categorias`) sigue migrando y sembrando. Ajustar `_sembrar_categorias`/`_migrar_productos_categoria` para sembrar solo si la tabla no existía antes del `executescript`; actualizar el test de C-06e que asumía "vacía → siembra" si existe
- [x] 2.5 RED→GREEN (`tests/test_sqlite_schema.py`): base nueva con ocho tablas; `procesos` con clave única y CHECK de formato, nombre único sin distinguir mayúsculas y 1-60; `orden_procesos` rechaza nombre vacío/61, `personalizado` fuera de 0/1, `posicion` < 1, orden inexistente (FK) y nombre repetido (NOCASE) en la misma orden; borrar una categoría usada por un producto lo rechaza la FK
- [x] 2.6 REFACTOR; suite verde

## 3. Repositorios — specs `procesos-ordenes`, `ordenes-trabajo`, `consulta-ordenes`, `categorias-productos` (design D5, D6)

- [x] 3.1 RED (`tests/test_sqlite_proceso_repository.py`, nuevo): `listar()` → `[Proceso("cambio-filtro","Cambio filtro"), Proceso("cambio-motor","Cambio motor"), Proceso("limpieza","Limpieza")]`; verificar rojo
- [x] 3.2 GREEN: `Proceso`, `ProcesoOrden` y `Orden.procesos` (default `()`) en `domain/entities.py`; `ProcesoRepository` en `base.py`; `SqliteProcesoRepository`. Verificar verde
- [x] 3.3 RED→GREEN: `crear` (duplicado de clave o nombre → `ProcesoDuplicado` sin filas nuevas), `obtener`, `renombrar` (inexistente → `ProcesoNoEncontrado`; nombre de otro → `ProcesoDuplicado`), `borrar` (devuelve el borrado; inexistente → `ProcesoNoEncontrado`); escrituras en `_transaccion`
- [x] 3.4 RED→GREEN (`tests/test_sqlite_orden_repository.py` o el módulo vigente de órdenes): `crear(..., procesos=(ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True)))` guarda con `posicion` 1..n y la orden devuelta los trae en orden; sin procesos → `()`
- [x] 3.5 RED→GREEN (atomicidad): falla inyectada al insertar procesos (por ejemplo, nombres repetidos que violan el UNIQUE) → no existe la orden, ni ítems, ni procesos, y el stock no cambió
- [x] 3.6 RED→GREEN: `listar` (con y sin filtros) y `_buscar_orden_por_numero` traen los procesos de cada orden por lote, sin multiplicar componentes; renombrar o borrar del catálogo no cambia los procesos leídos
- [x] 3.7 RED→GREEN: `borrar` (con y sin reintegro) elimina los procesos de esa orden en la misma transacción, la orden devuelta los incluye y otra orden con "Limpieza" queda intacta; falla inyectada tras borrar procesos → todo revertido
- [x] 3.8 RED→GREEN (`tests/test_sqlite_categoria_repository.py`): `borrar(clave)` sin productos → devuelve la categoría y la quita; usada por un activo y un dado de baja → `CategoriaEnUso(clave, 2)` sin cambios; inexistente → `CategoriaNoEncontrada`
- [x] 3.9 REFACTOR (lectura de órdenes compartida); suite verde

## 4. Services — specs `procesos-ordenes`, `categorias-productos` (design D3, D6, D7)

- [x] 4.1 RED (`tests/test_proceso_service.py`, nuevo, SQLite real): `crear("  Pintura del casco ")` → `pintura-del-casco`; verificar rojo
- [x] 4.2 GREEN: `services/proceso_service.py` (`listar`, `crear`, `renombrar`, `borrar`) y normalización generalizada en `services/normalizacion.py` (nombre 1-60 con "El nombre del proceso admite hasta 60 caracteres.", clave con "La clave del proceso admite solo…"); categorías siguen con sus mensajes. Verificar verde
- [x] 4.3 TRIANGULATE: clave indicada/normalizada, clave inválida, nombre repetido con `casefold` (también con tildes), clave repetida, nombre vacío/61; `renombrar("LIMPIEZA", …)`, mismo nombre sin error, nombre de otro, inexistente; `borrar(" Limpieza ")` normaliza; tests de categorías de C-06e verdes sin cambios
- [x] 4.4 RED→GREEN (`tests/test_orden_service.py`): `crear(..., procesos=["Limpieza", "cambio-filtro", "limpieza"])` → `ProcesoOrden("Limpieza", False), ProcesoOrden("Cambio filtro", False)`; `None`/ausentes → `()`; clave inexistente → "El proceso 'pintura' no existe." sin tocar stock; `"limpieza"` o `[3]` → "El campo procesos debe ser una lista de textos."
- [x] 4.5 RED→GREEN: personalizados recortados y en orden tras los del catálogo; vacío → "Proceso personalizado 2: El nombre es obligatorio."; 61 → "…admite hasta 60 caracteres."; 11 → "La orden admite hasta 10 procesos personalizados."; igual al catálogo (aunque no esté marcado) → "Proceso personalizado 1: 'limpieza' ya está en la lista de procesos; marcalo ahí."; repetidos → "Proceso personalizado 2: 'PULIDO' está repetido."; tipo inválido → mensaje de lista; personalizado no aparece en `ProcesoService.listar()`
- [x] 4.6 RED→GREEN (prioridad): componentes vacíos + proceso inexistente → gana "La orden requiere al menos un componente."; proceso inexistente + número duplicado → gana el 422 del proceso; constructores de `OrdenService` actualizados en tests y `api/dependencies.py` (recibe `proceso_repo`)
- [x] 4.7 RED→GREEN (`tests/test_categoria_service.py`): `borrar("MOTOR")` normaliza y delega; en uso → `CategoriaEnUso` con mensaje "La categoría 'filtro' está asignada a 2 producto(s)."; vacía → 422
- [x] 4.8 REFACTOR; suite verde

## 5. API — spec `api-http` (design D7)

- [x] 5.1 RED (`tests/test_api_procesos.py`, nuevo): `GET /api/procesos` sin sesión → 401; con sesión → 200 con la lista exacta; verificar rojo
- [x] 5.2 GREEN: `ProcesoOut`, `ProcesoAltaRequest`, `ProcesoRenombreRequest`, `get_proceso_service`, router `api/routers/procesos.py`, `include_router`, handlers `ProcesoDuplicado` 409 y `ProcesoNoEncontrado` 404 en `api/app.py`. Verificar verde
- [x] 5.3 RED→GREEN: `POST` 201 (clave derivada, visible en `GET`), 409 clave/nombre con `detail` exacto, 422 nombre faltante/largo y clave inválida, 401 sin crear; `PATCH` 200 con `LIMPIEZA` en la ruta, 404, 409, 422 con `clave` en el cuerpo, 401; `DELETE` 200 con el borrado (y `GET /api/ordenes` sigue mostrando el nombre en una orden que lo usaba), 404, 401
- [x] 5.4 RED→GREEN (`tests/test_api_ordenes.py`): alta con `procesos`/`procesos_personalizados` → 201 con `procesos` exacto; sin ellos → `procesos: []`; 422 de proceso inexistente, personalizado vacío y tipo inválido sin tocar stock; actualizar los diccionarios exactos de alta, listado y borrado con `procesos`
- [x] 5.5 RED→GREEN: `GET /api/ordenes` trae `procesos` con el nombre snapshot tras renombrar el proceso; `DELETE /api/ordenes/{numero}` devuelve la orden con sus procesos y luego no quedan filas en `orden_procesos` para ella
- [x] 5.6 RED→GREEN (`tests/test_api_categorias.py`): `DELETE /api/categorias/Motor` → 200 `{clave, nombre}` y fuera del `GET`; en uso → 409 con `detail` exacto y sin cambios; inexistente → 404; sin sesión → 401; handler `CategoriaEnUso` 409
- [x] 5.7 RED→GREEN (`tests/test_api_csrf.py`): `POST /api/procesos` y `PATCH /api/procesos/limpieza` con `text/plain`, formulario y multipart → 422 y catálogo sin cambios; `POST /api/ordenes` con procesos y `text/plain` → 422 sin orden
- [x] 5.8 RED→GREEN (`tests/test_api_app.py` y donde se cuenten rutas): OpenAPI con 19 rutas; `/api/procesos` con `GET` y `POST`; `/api/procesos/{clave}` y `/api/categorias/{clave}` con `PATCH` y `DELETE`; ninguna ruta de página
- [x] 5.9 REFACTOR; suite completa verde

## 6. JS puro de procesos — spec `interfaz-web` (Validación de procesos en la nueva orden) (design D8)

- [x] 6.1 RED (`tests/test_procesos_js.py`, nuevo, Node): `Procesos.armar([{valor:"limpieza"},{valor:"cambio-motor"}], catalogo)` → `{procesos: ["limpieza","cambio-motor"], procesos_personalizados: [], errores: []}`; verificar rojo
- [x] 6.2 GREEN: `static/js/procesos.js` (sin DOM al cargar, `window.Procesos`). Verificar verde
- [x] 6.3 TRIANGULATE: línea de catálogo con texto residual → texto no enviado; mismo proceso en dos líneas → una vez; textos recortados; vacío → error en su índice "El nombre es obligatorio."; 61 → "El nombre admite hasta 60 caracteres."; igual al catálogo (casefold, con tildes) → "'x' ya está en la lista de procesos; marcalo ahí."; repetidos → "'x' está repetido." en el segundo; más de 10 no se generan (tope del botón) pero `armar` también lo rechaza
- [x] 6.4 REFACTOR

## 7. "Nueva orden": procesos — spec `interfaz-web` (Modal de nueva orden, Procesos en la nueva orden, Procesos personalizados, Validación) (mockups N1-N2) (design D8)

- [x] 7.1 RED (guardas `tests/test_frontend_estatico.py` o `tests/test_frontend_procesos.py`): `index.html` con bloque "Procesos" después de "Componentes", contenedor de líneas y botón "Agregar proceso" con ayuda del tope; `index.html` carga `procesos.js`; `inventario.js` llama a `/api/procesos` y envía `procesos` y `procesos_personalizados`; sin `innerHTML`. Verificar rojo
- [x] 7.2 GREEN: HTML según N1-N2 y JS: líneas con `select` (catálogo por nombre + "Personalizado", cero líneas al abrir), "Personalizado" muestra/oculta su caja (texto conservado mientras la línea exista), "Agregar proceso", "Quitar", tope de 10 personalizados, validación con `Procesos.armar` y errores junto al campo (`aria-invalid`, `aria-describedby`), envío de ambos campos. Verificar verde
- [x] 7.3 GREEN (errores): catálogo que falla → aviso y solo "Personalizado"; 422 "Proceso personalizado N: …" marca la N-ésima línea personalizada; 422 "El proceso 'x' no existe." → mensaje bajo el bloque, recarga del catálogo y modal abierto con los datos
- [x] 7.4 REFACTOR; tests de C-06e de "Nueva orden" (filtro por categoría) verdes

## 8. `/ordenes`: fila de procesos — spec `interfaz-web` (Pantalla de órdenes) (mockup L1) (design D9)

- [x] 8.1 RED (guardas): `ordenes.js` arma la fila "Procesos:" con una lista (`ul`/`li`) solo si `o.procesos.length > 0`, con `textContent`; sin `innerHTML`. Verificar rojo
- [x] 8.2 GREEN: fila de chips bajo la cabecera del `article` según L1 (envuelve a 390 px); CSS de chips en `app.css` con tokens existentes. Verificar verde

## 9. PDF de una orden — spec `interfaz-web` (Exportar una orden a PDF) (mockup P1) (design D9)

- [x] 9.1 RED (guardas / JS puro si se extrae): el bloque de procesos del artículo, debajo de la tabla de componentes, tiene la etiqueta de impresión "Procesos realizados" y la de pantalla "Procesos:"; `exportarOrden` no cambia `titulo` ni `linea` (C-06c). Verificar rojo
- [x] 9.2 GREEN: CSS de impresión en `app.css` (lista uno por línea, sin fondo de chip, papel claro, sin cortar la lista del encabezado); orden sin procesos sin bloque. Verificar verde; REFACTOR

## 10. Documentación

- [x] 10.1 `README.md`: procesos de órdenes (catálogo sembrado, "Personalizado" solo en la orden, administración solo por API desde `/docs`: `GET`/`POST /api/procesos`, `PATCH`/`DELETE /api/procesos/{clave}`), `procesos`/`procesos_personalizados` en `POST /api/ordenes`, `DELETE /api/categorias/{clave}` (409 si está en uso), siembra solo al crear cada catálogo, y nota de migración con **backup `dev-local.bak-5f.db` antes del primer arranque**. Verificar que los endpoints documentados coinciden con `/openapi.json`

## 11. Suite completa

- [x] 11.1 Suite completa verde (baseline + nuevos, cero fallas); `openspec validate paso-5f-procesos-ordenes --strict` sin errores

## 12. Migración sobre una copia

- [x] 12.1 Copiar `dev-local.db` a `scratch/dev-local-copia-5f.db` (o al scratchpad), arrancar con `INVENTARIO_DB_PATH` apuntando a la copia: conteos de `productos`, `categorias`, `ordenes`, `orden_items` y `movimientos` iguales antes y después, `procesos` con 3 filas, `orden_procesos` vacía, cada orden con `procesos: []` en la API, log de migración una sola vez, segundo arranque sin cambios, `PRAGMA integrity_check` = `ok` y `PRAGMA foreign_key_check` vacío. El original no se toca

## 13. Verify en `/docs` y navegador

- [x] 13.1 `/docs` sobre la copia: `GET`/`POST`/`PATCH`/`DELETE` de procesos (incluido borrar uno usado por una orden y ver el nombre conservado), alta de orden con procesos y personalizados, 422 de proceso inexistente, `DELETE /api/categorias` 200 / 409 en uso / 404, con la cookie de sesión (NO ejecutada en navegador: cubierta por tests de API con TestClient; verificación manual en /docs omitida al archivar)
- [x] 13.2 Playwright contra la app real (uvicorn sobre la copia) a 390x844 y 1440x900, comparando con N1-N2 y L1: marcar procesos, personalizados con agregar/quitar/tope, errores del navegador, catálogo caído (bloqueando `/api/procesos`), 422 por proceso borrado en `/docs` con el modal abierto, lista de `/ordenes` con y sin procesos; capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos inesperados (OMITIDA al archivar: sin captura de 10 personalizados ni 422 con modal abierto en navegador; Visual verify passed 2026-11-26 en design.md)
- [x] 13.3 Impresión: `print` emulado y `page.pdf` (A4) de una orden con procesos y otra sin, comparando con P1 (encabezado intacto, bloque "Procesos realizados", sin nav ni botones)
- [x] 13.4 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar la KB 02 (endpoints de procesos, `DELETE /api/categorias/{clave}`, 19 rutas), 04 (tablas `procesos` y `orden_procesos`, snapshot del nombre, siembra solo al crear cada catálogo), 05 (RN-OR nuevas de procesos: opcionales, catálogo + personalizados, límites, sin repetir, snapshot, atomicidad y borrado con la orden; RN-PR de borrado de categoría con 409 si está en uso), 06 (US-006 con procesos, US-007 listado y PDF con procesos, administración de procesos y borrado de categorías por API) y 07 (flujos de alta de orden con procesos, listado/PDF, borrado de proceso y de categoría en `/docs`).
- En `CHANGES.md`: marcar `[x]` C-06f con la fecha y anotar en C-07 la paridad de design D10 (tablas `procesos`/`orden_procesos` con índices únicos en `lower(nombre)`, RPC `crear_orden` con `p_procesos`, borrado de orden con procesos, CRUD directo de procesos y borrado de categorías con 23505/23503 → 409).
- Esperar "Continuar" del usuario antes de proponer C-07 (`paso-6-migracion-supabase`).
