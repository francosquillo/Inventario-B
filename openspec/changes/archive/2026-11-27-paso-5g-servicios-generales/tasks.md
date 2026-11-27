# Tasks

> **GATE: el apply NO empieza hasta que** (a) el usuario revise las decisiones 1-21 de `design.md` (Q1-Q5 ya resueltas el 2026-11-27) y (b) `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`. Si una decisión cambia, actualizar specs, design, mockups y estas tareas antes del apply.
>
> **Strict TDD**: RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo primero; si pasa sin código nuevo, anotar por qué) → REFACTOR (verde tras cada paso). JS puro con Node desde `unittest` (patrón de `tests/test_procesos_js.py`, se omite sin Node); resto del frontend con guardas estáticas (patrón de `tests/test_frontend_procesos.py`); el navegador se verifica en el grupo 13 contra `specs/` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente; sin pytest ni mocks de base: repositorios, services y migración con SQLite real (`:memory:` o archivo temporal) (regla dura 4).
> - Sin dependencias nuevas; sin imports de FastAPI en `domain/`, `services/` ni `repositories/` (regla dura 1).
> - Alta y borrado de orden (con servicio y chequeos), modificación de un servicio del catálogo y la migración en una transacción, todo o nada (regla dura 3). Servicio validado en el navegador Y en el backend.
> - `tokens.css` y `ui.css` intactos; CSS nuevo solo en `static/css/app.css`. En JS: datos solo con `textContent`/`createElement`, sin `innerHTML`.
> - **Nunca** migrar ni borrar `dev-local.db` real durante el apply (solo se copia en 1.3); tests con bases temporales y verify sobre una copia. Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear solo los mockups necesarios en `openspec/changes/paso-5g-servicios-generales/mockups/` (`nueva-orden.html` S1, `ordenes.html` L2, C1 y C2, `README.md` con estados, omisiones justificadas y `Approval: pending`; reutilizan los aprobados de C-06f) y verificar que abren localmente
- [x] 0.2 Renderizar a 390x844 y 1440x900 en `mockups/previews/`; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`

## 1. Red de seguridad

- [x] 1.1 (baseline: 969 tests OK, 0 omitidos; Node v24 disponible) Correr la suite completa y anotar el baseline (`Ran N tests ... OK`, cuántos se omiten por Node); si algo falla, detenerse y reportarlo como falla preexistente
- [x] 1.2 Confirmar `node` disponible (si no, cubrir el JS puro en el verify con `browser_evaluate`)
- [x] 1.3 Backup: copiar `dev-local.db` a `dev-local.bak-5g.db` en la raíz (copia de archivo, sin abrirlo con SQLite) y verificar con `git status` que no aparece y que ambos archivos tienen el mismo tamaño

## 2. Esquema, siembra y migración — specs `inicializacion-base-datos`, `servicios-generales` (design D1, D3, D4)

- [x] 2.1 RED (`tests/test_sqlite_migracion_servicios.py`, nuevo): DDL de C-06f **copiado literal** (ocho tablas, procesos sembrados) con dos órdenes con ítems y procesos, productos con categoría y movimientos → `inicializar_esquema` crea `servicios_generales` (`servicio-20-hs` "Servicio 20 hs"), `servicio_chequeos` (los tres chequeos en orden), `orden_servicio` y `orden_servicio_chequeos` vacías; verificar rojo
- [x] 2.2 GREEN: `_crear_servicios_generales(conn, loguear)` (DDL de D1 + siembra en `_transaccion`, verificación de conteos incluyendo `procesos`/`orden_procesos`, log) llamada tras `_crear_procesos` y antes de `NORMALIZAR_FECHAS_SQL`; verificar verde
- [x] 2.3 TRIANGULATE: filas existentes idénticas (órdenes, ítems, procesos de órdenes, productos, categorías, movimientos); tres arranques sin duplicar; catálogo vaciado o con chequeos reemplazados no se resiembra; falla inyectada en la siembra → no existe ninguna de las cuatro tablas y la excepción sube; log solo si la base existía. Verificar verde
- [x] 2.4 RED→GREEN (`tests/test_sqlite_schema.py`): base nueva con doce tablas y siembra; `servicios_generales` con clave única + CHECK y nombre único NOCASE 1-60; `servicio_chequeos` rechaza vacío/61, repetido NOCASE en el mismo servicio, `posicion` < 1 y servicio inexistente; `orden_servicio` rechaza un segundo servicio para la misma orden y orden inexistente; `orden_servicio_chequeos` rechaza vacío/61, repetido y orden sin servicio. Verificar verde
- [x] 2.5 REFACTOR (constantes de DDL compartidas con procesos si aplica); suite verde

## 3. Repositorios — specs `servicios-generales`, `ordenes-trabajo`, `consulta-ordenes` (design D5)

- [x] 3.1 RED (`tests/test_sqlite_servicio_general_repository.py`, nuevo): `listar()` → `[ServicioGeneral("servicio-20-hs", "Servicio 20 hs", ("Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"))]`; verificar rojo
- [x] 3.2 GREEN: `ServicioGeneral`, `ServicioOrden` y `Orden.servicio` (default `None`) en `domain/entities.py`; `ServicioGeneralRepository` en `base.py`; `SqliteServicioGeneralRepository.listar`. Verificar verde
- [x] 3.3 RED→GREEN: `listar` ordenado por nombre con dos servicios; `crear` (chequeos con posición 1..n; duplicado de clave o nombre → `ServicioGeneralDuplicado` sin filas nuevas), `obtener` (con chequeos; inexistente → `None`), `modificar` (solo nombre; solo chequeos reemplazando la lista; ambos; inexistente → `ServicioGeneralNoEncontrado`; nombre de otro → `ServicioGeneralDuplicado`; falla inyectada al insertar chequeos → nombre y chequeos anteriores intactos), `borrar` (devuelve el borrado con chequeos y no quedan filas en `servicio_chequeos`; inexistente → `ServicioGeneralNoEncontrado`)
- [x] 3.4 RED→GREEN (`tests/test_sqlite_orden_repository.py`): `crear(..., servicio=ServicioOrden("Servicio 20 hs", (...)))` guarda `orden_servicio` + chequeos en orden y la orden devuelta lo trae; sin servicio → `None`; con servicio y procesos juntos
- [x] 3.5 RED→GREEN (atomicidad): falla inyectada al insertar los chequeos de la orden (por ejemplo, chequeos repetidos que violan el UNIQUE) → no existe la orden, ni ítems, ni procesos, ni servicio, y el stock no cambió
- [x] 3.6 RED→GREEN: `listar` (con y sin filtros) y `_buscar_orden_por_numero` traen el servicio de cada orden por lote, sin multiplicar componentes ni procesos; modificar o borrar del catálogo no cambia el servicio leído
- [x] 3.7 RED→GREEN: `borrar` (con y sin reintegro) elimina servicio y chequeos de esa orden en la misma transacción, la orden devuelta los incluye y otra orden con el mismo servicio queda intacta; falla inyectada tras borrar el servicio → todo revertido
- [x] 3.8 REFACTOR (lectura de órdenes compartida); suite verde

## 4. Services — spec `servicios-generales` (design D2, D6, D7)

- [x] 4.1 RED (`tests/test_servicio_general_service.py`, nuevo, SQLite real): `crear("  Servicio 100 hs ", ["Cambio de aceite"])` → `servicio-100-hs`; verificar rojo
- [x] 4.2 GREEN: `services/servicio_general_service.py` (`listar`, `crear`, `modificar`, `borrar`), `normalizar_chequeos` y mensajes de clave/nombre de servicio en `services/normalizacion.py` reutilizando la normalización generalizada; errores `ServicioGeneralDuplicado`/`ServicioGeneralNoEncontrado` en `domain/errors.py`. Verificar verde
- [x] 4.3 TRIANGULATE (chequeos): recortados y en orden; lista vacía/ausente → "El servicio general requiere al menos un chequeo."; 31 → "…admite hasta 30 chequeos."; vacío/61 en posición 2 → "Chequeo 2: …"; repetido casefold (también con tildes) → "Chequeo 2: 'X' está repetido."; texto o `[3]` → "El campo chequeos debe ser una lista de textos."
- [x] 4.4 TRIANGULATE (catálogo): clave indicada/normalizada, clave inválida (mensaje del servicio general), nombre repetido casefold, clave repetida, nombre vacío/61; `modificar("SERVICIO-20-HS", nombre=…)`, mismo nombre sin error, solo chequeos, chequeos inválidos con nombre válido → nada cambia, sin nombre ni chequeos → "Indicá el nombre o los chequeos a modificar.", inexistente; `borrar(" Servicio-20-HS ")` normaliza; tests de procesos y categorías verdes sin cambios
- [x] 4.5 RED→GREEN (`tests/test_orden_service.py`): `crear(..., servicio=" Servicio-20-HS ")` → `ServicioOrden("Servicio 20 hs", (3 chequeos))`; `None`/ausente/`"  "` → sin servicio; inexistente → "El servicio general 'servicio-500-hs' no existe." sin tocar stock; `["x"]`/`3` → "El campo servicio debe ser texto."; clave larga recortada a 30 + "…"
- [x] 4.6 RED→GREEN (prioridad, design D6): componentes vacíos + servicio inexistente → gana componentes; servicio inexistente + proceso inexistente → gana servicio; servicio inexistente + número duplicado → gana servicio; actualizar constructores de `OrdenService` en tests y en `api/dependencies.py` (recibe `servicio_repo`)
- [x] 4.7 REFACTOR; suite verde

## 5. API — spec `api-http` (design D7)

- [x] 5.1 RED (`tests/test_api_servicios_generales.py`, nuevo): `GET /api/servicios-generales` sin sesión → 401; con sesión → 200 con la lista exacta del servicio sembrado; verificar rojo
- [x] 5.2 GREEN: `ServicioGeneralOut`, `ServicioGeneralAltaRequest`, `ServicioGeneralCambioRequest`, `get_servicio_general_service`, router `api/routers/servicios_generales.py`, `include_router`, handlers 409/404 en `api/app.py`. Verificar verde
- [x] 5.3 RED→GREEN: `POST` 201 (clave derivada, chequeos recortados, visible en `GET`), 409 clave/nombre con `detail` exacto, 422 nombre faltante/largo, clave inválida y chequeos inválidos, 401 sin crear; `PATCH` 200 solo chequeos / solo nombre con la clave en mayúsculas en la ruta, 422 `{}` y con `clave` en el cuerpo, 404, 409, 401; `DELETE` 200 con lo borrado (y `GET /api/ordenes` sigue mostrando el servicio en una orden que lo usaba), 404, 401
- [x] 5.4 RED→GREEN (`tests/test_api_ordenes.py`): alta con `servicio` → 201 con `servicio` exacto; sin él, `null` o `"  "` → `servicio: null`; 422 inexistente y tipo inválido sin tocar stock; actualizar los diccionarios exactos de alta, listado y borrado con `servicio`
- [x] 5.5 RED→GREEN: `GET /api/ordenes` trae el servicio snapshot tras renombrar y reemplazar chequeos del catálogo; `DELETE /api/ordenes/{numero}` devuelve la orden con su servicio, luego no quedan filas en `orden_servicio`/`orden_servicio_chequeos` para ella y el catálogo sigue intacto
- [x] 5.6 RED→GREEN (`tests/test_api_csrf.py`): `POST /api/servicios-generales` y `PATCH /api/servicios-generales/servicio-20-hs` con `text/plain`, formulario y multipart → 422 y catálogo sin cambios
- [x] 5.7 RED→GREEN (`tests/test_api_app.py` y donde se cuenten rutas): OpenAPI con 21 rutas; `/api/servicios-generales` con solo `GET` y `POST`; `/api/servicios-generales/{clave}` con solo `PATCH` y `DELETE`; ninguna ruta de página
- [x] 5.8 REFACTOR; suite completa verde

## 6. JS puro del servicio — spec `interfaz-web` (Servicio general en la nueva orden, Errores del servicio general) (design D8)

- [x] 6.1 RED (`tests/test_servicios_js.py`, nuevo, Node): `Servicios.armar("servicio-20-hs", catalogo)` → `{servicio: "servicio-20-hs", error: null}`; verificar rojo
- [x] 6.2 GREEN: `static/js/servicios.js` (sin DOM al cargar, `window.Servicios`). Verificar verde
- [x] 6.3 TRIANGULATE: `""`/`null` → `{servicio: null, error: null}`; clave fuera del catálogo → error "El servicio general elegido ya no está disponible."; catálogo vacío (caído) con `""` → sin error; `Servicios.chequeosDe(clave, catalogo)` → chequeos en orden y `[]` para `""` o clave desconocida
- [x] 6.4 RED→GREEN (`Servicios.validarFormulario`, design D12): datos válidos → nombre y chequeos recortados, sin errores; nombre vacío → "El campo nombre es obligatorio."; 61 → "El nombre del servicio general admite hasta 60 caracteres."; nombre de otro servicio (casefold, con tildes) → "Ya existe un servicio general con nombre 'X'."; el mismo nombre del servicio editado (`claveActual`) → sin error; sin chequeos → error general "El servicio general requiere al menos un chequeo."; 31 → "…admite hasta 30 chequeos."; chequeo vacío/61/repetido → error en su índice ("El nombre es obligatorio.", "El nombre admite hasta 60 caracteres.", "'X' está repetido." en el segundo)
- [x] 6.5 REFACTOR

## 7. "Nueva orden": bloque "Servicio general" — spec `interfaz-web` (Modal de nueva orden, Servicio general en la nueva orden, Errores del servicio general) (mockups S1-S2 aprobados = criterio de aceptación) (design D8)

- [x] 7.1 RED (guardas, `tests/test_frontend_servicios.py` nuevo): `index.html` con `fieldset` "Servicio general" entre la fecha y "Componentes", `select#ord-servicio` con opción "Sin servicio general" (`value=""`), contenedor de chequeos "Incluye:" y aviso; `index.html` carga `servicios.js`; `inventario.js` llama a `/api/servicios-generales` y envía `servicio`; sin `innerHTML`. Verificar rojo
- [x] 7.2 GREEN: HTML según S1-S2 y JS: opciones por nombre, lista de chequeos de solo lectura al elegir (oculta con "Sin servicio general"), reinicio al abrir el modal, validación con `Servicios.armar` antes de enviar, envío de `servicio` (`null` si no hay). Verificar verde
- [x] 7.3 GREEN (errores): catálogo que falla → "No se pudo cargar la lista de servicios generales." y solo "Sin servicio general"; 422 del servicio → mensaje junto al bloque (`aria-describedby`), recarga del catálogo, selector a "Sin servicio general", modal abierto con los datos. Verificar con guardas
- [x] 7.4 REFACTOR; guardas de C-06e/C-06f de "Nueva orden" (filtro por categoría, procesos) verdes

## 8. `/ordenes`: fila de servicio — spec `interfaz-web` (Pantalla de órdenes) (mockup L2 aprobado = criterio de aceptación) (design D9)

- [x] 8.1 RED (guardas): `ordenes.js` arma la fila "Servicio general:" (nombre + `ul`/`li` de chequeos) solo si `o.servicio`, antes de la fila "Procesos:", con `textContent`; sin `innerHTML`. Verificar rojo
- [x] 8.2 GREEN: fila según L2 (envuelve a 390 px), reutilizando chips de C-06f; CSS nuevo, si hace falta, en `app.css` con tokens existentes. Verificar verde

## 8b. `/ordenes`: administración del catálogo — spec `interfaz-web` (Pantalla de órdenes, Catálogo de servicios generales en la web, Formulario, Validación, Borrado) (mockups C1-C2 aprobados = criterio de aceptación) (design D12)

- [x] 8b.1 RED (guardas, `tests/test_frontend_servicios_admin.py` nuevo): `ordenes.html` con botón "Servicios generales" junto al `h1` (clase `no-print`), `#modal-servicios` con las tres vistas (lista, formulario con "Nombre", fieldset "Chequeos", "Agregar chequeo", "Volver"/"Guardar", y confirmación con "Eliminar servicio" `btn-danger`), carga `servicios.js` y `servicios-admin.js`; `servicios-admin.js` usa `/api/servicios-generales` con `GET`, `POST`, `PATCH` y `DELETE`, valida con `Servicios.validarFormulario` y no usa `innerHTML`. Verificar rojo
- [x] 8b.2 GREEN (vista lista, C1): carga al abrir, tarjetas por servicio con chips de chequeos y "Editar"/"Eliminar" con nombre accesible, "Nuevo servicio", estados vacío ("No hay servicios generales.") y error con "Reintentar". Verificar verde
- [x] 8b.3 GREEN (vista formulario, C2): nuevo/editar, líneas numeradas con "Quitar" (deshabilitado con una sola), "Agregar chequeo" con tope 30 y ayuda, contador, validación en el navegador con errores junto a cada campo (`aria-invalid`, `aria-describedby`), envío `POST`/`PATCH` con `nombre` y `chequeos`, éxito → lista + "Servicio general X guardado."; "Volver" sin petición; 409/422 "Chequeo N: …"/404 según design D12. Verificar verde
- [x] 8b.4 GREEN (confirmación de borrado): texto "¿Eliminar el servicio general X? Las órdenes que ya lo tienen lo conservan.", "Cancelar" sin petición, "Eliminar servicio" → `DELETE`, lista + "Servicio general X eliminado."; foco al título de cada vista y `Esc` cierra. Verificar verde
- [x] 8b.5 REFACTOR; guardas de `/ordenes` de C-06c/C-06f verdes

## 9. PDF de una orden — spec `interfaz-web` (Exportar una orden a PDF) (sin mockup propio: mismo estilo que "Procesos realizados" del P1 aprobado en C-06f; criterio = spec + design D9)

- [x] 9.1 RED (guardas): el bloque de servicio del artículo tiene la etiqueta de impresión "Servicio general" y va **antes de la tabla de componentes** (y por lo tanto antes de "Procesos realizados"); `exportarOrden` no cambia `titulo` ni `linea` (C-06c) y el botón "Servicios generales" es `no-print`. Verificar rojo
- [x] 9.2 GREEN: CSS de impresión en `app.css` (nombre + chequeos uno por línea, sin fondo de chip); orden sin servicio sin bloque. Verificar verde; REFACTOR

## 10. Documentación

- [x] 10.1 `README.md`: servicios generales (catálogo sembrado con "Servicio 20 hs", administración desde el botón "Servicios generales" de `/ordenes` y por API desde `/docs`: `GET`/`POST /api/servicios-generales`, `PATCH`/`DELETE /api/servicios-generales/{clave}` con reemplazo completo de chequeos), campo `servicio` en `POST /api/ordenes`, y nota de migración con **backup `dev-local.bak-5g.db` antes del primer arranque**. Verificar que los endpoints documentados coinciden con `/openapi.json`

## 11. Suite completa

- [x] 11.1 Suite completa verde (baseline + nuevos, cero fallas) y `openspec validate paso-5g-servicios-generales --strict` sin errores

## 12. Migración sobre una copia

- [x] 12.1 Copiar `dev-local.db` al scratchpad y arrancar con `INVENTARIO_DB_PATH` apuntando a la copia: conteos de `productos`, `categorias`, `ordenes`, `orden_items`, `movimientos`, `procesos` y `orden_procesos` iguales antes y después; `servicios_generales` con 1 fila y `servicio_chequeos` con 3; `orden_servicio` vacía; cada orden con `servicio: null` en la API; log de migración una sola vez; segundo arranque sin cambios; `PRAGMA integrity_check` = `ok` y `PRAGMA foreign_key_check` vacío. El original no se toca

## 13. Verify en `/docs` y navegador

- [x] 13.1 `/docs` sobre la copia: `GET`/`POST`/`PATCH`/`DELETE` de servicios generales (incluido reemplazar chequeos y borrar uno usado por una orden y ver el snapshot conservado), alta de orden con servicio, 422 de servicio inexistente, con la cookie de sesión
- [x] 13.2 Playwright contra la app real (uvicorn sobre la copia) a 390x844 y 1440x900, comparando con S1, L2, C1 y C2: elegir/quitar servicio, lista "Incluye:", catálogo caído (bloqueando `/api/servicios-generales`), 422 por servicio borrado con el modal abierto, `/ordenes` con y sin servicio; modal "Servicios generales": crear, editar (agregar/quitar chequeos), errores del navegador y 409, eliminar con confirmación, teclado (`Tab`, `Esc`); capturas en `mockups/verify/`, consola sin errores, red sin pedidos fallidos inesperados
- [x] 13.3 Impresión: `print` emulado y `page.pdf` (A4) de una orden con servicio y procesos y otra sin, comparando con el P1 aprobado de C-06f más el bloque nuevo (encabezado intacto, luego "Servicio general", luego la tabla de componentes y después "Procesos realizados", sin nav ni botones)
- [x] 13.4 Registrar `Visual verify:` en `design.md` (passed / differences / manual)

## Workflow follow-up

- Al archivar: actualizar la KB 02 (endpoints de servicios generales, 21 rutas), 04 (tablas `servicios_generales`, `servicio_chequeos`, `orden_servicio`, `orden_servicio_chequeos`; snapshot; siembra solo al crear), 05 (RN-OR de servicio general: opcional, uno por orden, snapshot, atomicidad y borrado con la orden; reglas del catálogo y de chequeos), 06 (US-006 con servicio, US-007 listado y PDF con servicio, administración del catálogo desde `/ordenes` y por API) y 07 (flujos de alta de orden con servicio, listado/PDF, administración del catálogo en la web).
- Nota de ubicación de tests: parte de los tests de servicio en la orden (3.4-3.7 y 5.4-5.5) viven además en `tests/test_sqlite_servicio_general_repository.py` y `tests/test_api_servicios_generales.py`.
- En `CHANGES.md`: marcar `[x]` C-06g con la fecha y anotar en C-07 la paridad de design D10.
- Esperar "Continuar" del usuario antes de proponer C-06h (`paso-5h-precios-datos-orden`).
