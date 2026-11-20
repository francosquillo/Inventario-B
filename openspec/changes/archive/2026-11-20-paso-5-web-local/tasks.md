# Tasks

> **GATE: el apply NO empieza hasta que `design.md` § UI Mockups diga `Approval: approved (<fecha>, by user)`** y el usuario haya revisado las 20 "Decisiones a confirmar por el usuario" (governance ALTO). Si una decisión cambia, actualizar specs, design y estas tareas antes del apply.
>
> **Strict TDD**: en cada comportamiento de servidor, RED (test que falla por la razón correcta, ejecutado y visto en rojo) → GREEN (mínimo código) → TRIANGULATE (cada caso nuevo se escribe y ejecuta primero; si pasa sin cambios de código, anotar por qué) → REFACTOR (verde tras cada paso). Para el frontend, el RED de `unittest` son las guardas estáticas (design D8); el comportamiento en el navegador se verifica en el grupo 12 contra los escenarios de `specs/interfaz-web` y los mockups aprobados.
>
> **Comando** (desde la raíz): `.venv/Scripts/python -m unittest discover -s tests -t .`; un módulo: `.venv/Scripts/python -m unittest tests.test_<modulo> -v`.
>
> **Reglas duras**:
> - `unittest` solamente, SQLite real (archivo temporal vía `tests/helpers.app_de_test`), sin mocks de base (regla dura 4).
> - Sin dependencias nuevas: `StaticFiles`, `FileResponse` y `RedirectResponse` son de Starlette/FastAPI (regla dura 1). FastAPI solo en `inventario/api/`.
> - Ningún cambio en services, repositorios ni en las respuestas de `/api/...`; los tests existentes no cambian sus aserciones.
> - Nunca leer ni escribir `.env`; sin commits (reglas duras 2 y 6).
> - En JS: datos solo con `textContent`/`createElement`; nada de `innerHTML` (design D4).

## 0. Mockups (gate, lo hace el orquestador)

- [x] 0.1 Crear los mockups en `openspec/changes/paso-5-web-local/mockups/` (HTML local que importa `design-system/tokens.css` y `ui.css`, cabecera de texto "Inventario", README con pantallas y `Approval: pending`) cubriendo todo el checklist de `design.md` § UI Mockups (L1-L5, I1-I5, MI1-MI4, ME1-ME3, MO1-MO7, MB1-MB2, O1-O6, MD1-MD4, T1-T3); verificar que cada ítem del checklist tiene su estado en algún HTML
- [x] 0.2 Renderizar cada mockup a 390x844 y 1440x900 con Playwright, guardar las capturas en `mockups/previews/`, inspeccionarlas y corregir defectos; registrar `Preview: rendered (<fecha>)` en `design.md`
- [x] 0.3 Presentar capturas y enlaces al usuario y obtener su aprobación explícita; registrar `Approval: approved (<fecha>, by user)` en `design.md` y en `mockups/README.md`, y enlazar los mockups aprobados como criterio de aceptación de los grupos 7-10 y del verify 12.2

## 1. Red de seguridad

- [x] 1.1 Correr la suite completa antes de tocar nada y anotar el baseline (esperado `Ran 419 tests ... OK`); si algo falla, detenerse y reportarlo como falla preexistente

## 2. Páginas y redirecciones por sesión — spec `api-http` (design D1)

En `tests/test_api_paginas.py`.

- [x] 2.1 RED: `GET /` sin sesión → 200 `text/html` con un `<form` de login; verificar que falla (hoy 404)
- [x] 2.2 GREEN: crear `static/login.html` mínimo (esqueleto con el formulario; se completa en el grupo 8) y `inventario/api/routers/paginas.py` con `GET /` (`FileResponse`, `include_in_schema=False`), incluido en `crear_app`; resolver `static/` desde el paquete (`Path(__file__).resolve().parents[2]`). Verificar verde
- [x] 2.3 RED→GREEN: `GET /inventario` y `GET /ordenes` sin sesión → 303 `Location: /` (cliente con `follow_redirects=False`); con sesión → 200 `text/html`. Crear esqueletos `static/index.html` y `static/ordenes.html`. Verificar rojo y luego verde
- [x] 2.4 REFACTOR: extraer `usuario_de_sesion(request, conn)` de `get_current_user` en `dependencies.py` (devuelve `None` sin sesión o con usuario inexistente, limpiando la sesión en ese caso) y usarlo en `get_current_user` y en las páginas. Verificar que la suite completa sigue verde (incluido `test_api_sesion_inexistente.py`)
- [x] 2.5 RED→GREEN: `GET /` con sesión válida → 303 `Location: /inventario`; con cookie firmada de un `usuario_id` inexistente → 200 login y `/inventario` → 303 `/`. Verificar
- [x] 2.6 TRIANGULATE: con `A-01` "Tornillo" sembrado, el HTML de `/inventario` no contiene `A-01` ni `Tornillo`; `GET /ordenes` devuelve HTML y `GET /api/ordenes` la lista JSON; `GET /no-existe` y `GET /api/no-existe` → 404 `{"detail": "Not Found"}`; `GET /docs` → 200. Verificar (anotar cuáles pasan sin código nuevo y por qué)
- [x] 2.7 TRIANGULATE OpenAPI: el test existente de las diez rutas (`tests/test_api_app.py::DocsTest`) sigue verde sin cambios y un test nuevo confirma que `/`, `/inventario`, `/ordenes` y `/static` no están en `paths`. Verificar

## 3. Archivos estáticos — spec `api-http` (design D1)

En `tests/test_api_static.py`.

- [x] 3.1 RED: `GET /static/css/tokens.css` sin sesión → 200 `text/css`; verificar que falla (404)
- [x] 3.2 GREEN: copiar `design-system/tokens.css` y `ui.css` a `static/css/` sin cambios y montar `StaticFiles` en `/static` después de los routers. Verificar verde
- [x] 3.3 TRIANGULATE: `GET /static/js/api.js` (crear el archivo vacío con un comentario) → 200 con `Content-Type` de JavaScript; `GET /static/..%2Finventario.db`, `GET /static/..%2F..%2Frequirements.txt`, `GET /static/` y `GET /static/js/` → 404 sin contenido del archivo; `GET /static/no-existe.css` → 404. Verificar y anotar qué cubre Starlette sin código propio

## 4. Cabeceras de seguridad de las páginas — spec `api-http` (design D1-h)

- [x] 4.1 RED: en `tests/test_api_paginas.py`, `GET /` sin sesión incluye `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` y `Cache-Control: no-store`; verificar rojo
- [x] 4.2 GREEN: agregar las cabeceras en las respuestas HTML del router de páginas (no como middleware global). Verificar verde
- [x] 4.3 TRIANGULATE: las mismas cabeceras en `/inventario` y `/ordenes` con sesión; `GET /api/me` y `GET /api/inventario` no tienen `X-Frame-Options` (las respuestas de `/api` no cambian). Verificar

## 5. Vigencia de la sesión — spec `api-http` "Vigencia de la sesión" (design D2)

En `tests/test_api_sesion_vigencia.py`.

- [x] 5.1 RED: el `Set-Cookie` de `POST /api/login` válido incluye `Max-Age=43200`, `httponly` y `samesite=lax`; verificar rojo (hoy sin `Max-Age`)
- [x] 5.2 GREEN: constante `SESSION_MAX_AGE = 12 * 60 * 60` en `app.py` y `max_age=SESSION_MAX_AGE` en `SessionMiddleware`. Verificar verde y que `tests/test_api_auth.py` sigue verde
- [x] 5.3 TRIANGULATE: construir con `itsdangerous.TimestampSigner(SECRET_KEY)` (subclase con `get_timestamp` fijo) la cookie `{"usuario_id": <id admin>, "username": "admin"}` en base64, como la firma Starlette: firmada hace 13 h → `GET /api/me` 401 y `GET /` muestra el login; hace 11 h → 200 `admin`. Verificar que el caso de 13 h falla con `max_age=None` (mutación anotada y revertida)

## 6. Defensa CSRF fijada por tests — spec `api-http` (design D3)

En `tests/test_api_csrf.py`. Son tests de caracterización: se espera que pasen sin código nuevo (comportamiento sondeado en design § Context); verificar cada uno con una mutación temporal que lo haga fallar y anotarla.

- [x] 6.1 `POST /api/login` con `text/plain`, `application/x-www-form-urlencoded` y `multipart/form-data` y cuerpo JSON de credenciales válidas → 422 "El cuerpo de la petición debe ser un objeto JSON." sin `Set-Cookie`. Verificar
- [x] 6.2 Con sesión: `POST /api/stock/ingreso`, `POST /api/stock/egreso` y `POST /api/ordenes` con `text/plain` → 422; stock, `helpers.movimientos` y órdenes iguales que antes. Verificar
- [x] 6.3 `OPTIONS /api/ordenes/OT-0001` con `Origin: http://evil.example` y `Access-Control-Request-Method: DELETE` → no 2xx y sin `Access-Control-Allow-Origin`; `GET /api/inventario` con sesión y `Origin` ajeno → sin `Access-Control-Allow-*`. Verificar (mutación: agregar `CORSMiddleware(allow_origins=["*"])` temporalmente y ver rojo)

## 7. Base del frontend — specs `interfaz-web` (design D4-D7)

Guardas en `tests/test_frontend_estatico.py` (RED primero). Criterio visual: mockups aprobados (0.3).

- [x] 7.1 RED: guardas: `static/css/tokens.css` y `ui.css` idénticos byte a byte a `design-system/`; las tres páginas con `lang="es"`, `<meta name="viewport">`, `/static/css/tokens.css`, `/static/css/ui.css`, `/static/js/tailwind-config.js` y el script de Tailwind con versión exacta (`cdn.tailwindcss.com/3.4.`); todo `src`/`href` local de las páginas responde 200 vía `TestClient`; ningún `.js` de `static/js/` contiene `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` ni `eval(`; ningún HTML usa clases de la paleta de Tailwind (`(bg|text|border|ring)-(gray|slate|zinc|neutral|stone|red|amber|yellow|green|blue|…)-\d{2,3}`). Verificar rojo
- [x] 7.2 GREEN: `static/js/tailwind-config.js` (mapa de tokens de `components.html`), fijar la versión exacta del Play CDN 3.4.x comprobando que la URL responda, y cabecera común de las páginas protegidas (título "Inventario", usuario, "Cerrar sesión") según los mockups. Verificar guardas verdes
- [x] 7.3 `static/js/validacion.js` (`window.Validacion`, puro, sin DOM ni `fetch`): `requerido`, `cantidad`, `largo`, `fecha`, `rango`, `componentes` con los mensajes de design D6. Verificar guardas verdes y dejar en `openspec/changes/paso-5-web-local/verify/casos-validacion.md` la tabla de casos (entrada → mensaje) que usa 12.3, cubriendo cada escenario de "Validación en el navegador"
- [x] 7.4 `static/js/api.js` (`window.Api`, design D5): JSON + `credentials: "same-origin"`, 401 → `/?sesion=expirada` salvo en `/api/login`, `ApiError {status, detail, faltantes}`, mensajes de red y 5xx. Verificar guardas verdes
- [x] 7.5 `static/js/ui.js` a partir de `design-system/ui.js`: abrir/cerrar modal (Cancelar, X, Escape, fondo), foco al primer campo, trampa de Tab, retorno del foco, alertas `role="alert"`/`role="status"`, estado "enviando" de botones (deshabilitado + texto). `static/js/sesion.js`: `GET /api/me` en la cabecera, "Cerrar sesión" → `POST /api/logout` → `/`, revalidación en `pageshow`. Verificar guardas verdes

## 8. Login — spec `interfaz-web` (Formulario, Errores del login, Sesión expirada)

- [x] 8.1 Completar `static/login.html` + `static/js/login.js` según mockups L1-L5: contraseña `type="password"` con "Mostrar"/"Ocultar", validación de vacíos, "Ingresando…", 401 (conserva usuario, vacía contraseña, foco), aviso con `?sesion=expirada`, éxito → `/inventario`. Guarda nueva: `type="password"` y `autocomplete="current-password"` en el HTML. Verificar guardas verdes y suite completa verde

## 9. Inventario y modales — spec `interfaz-web` (Tabla, Inventario vacío, Ingreso, Egreso, Nueva orden, Errores por línea, Baja de producto)

- [x] 9.1 `static/index.html` + `static/js/inventario.js`: tabla de `GET /api/inventario` (stock 0 resaltado, conteo), estados cargando/vacío/error con "Reintentar", alerta de éxito persistente (decisión 17), según mockups I1-I5. Verificar guardas verdes
- [x] 9.2 Modal Ingreso (MI1-MI4): código libre con `datalist`, Nombre nunca bloqueado en el cliente, aviso no bloqueante "Código nuevo o dado de baja: si es nuevo, indicá un nombre." (decisión 12 ajustada), validación; ante el 422 "…indicá un nombre para crearlo." mostrar el `detail` solo en la alerta superior del modal, marcar Nombre `aria-invalid` con `aria-describedby` apuntando al `id` de la alerta (sin repetir el texto bajo el campo), dejar el modal abierto y enfocar Nombre; mensaje de éxito con creado/reactivado; recarga del inventario. Verificar guardas verdes
- [x] 9.3 Modal Egreso (ME1-ME3): desplegable de activos con stock (decisión 11), 409/404 con `detail`, recarga de la lista ante 404. Verificar guardas verdes
- [x] 9.4 Modal Nueva orden (MO1-MO7): número, fecha de hoy editable (decisión 18), 1..100 líneas con agregar/quitar, validación por línea, mapeo de 409 `faltantes`/404/422 "Componente N"/409 duplicada a líneas o campos (design D5; en el 409 duplicada el `detail` va solo en la alerta y el campo número queda `aria-invalid`, enlazado a la alerta y con foco), sin doble envío, éxito "Orden X creada." con enlace a `/ordenes`. Verificar guardas verdes
- [x] 9.5 Modal Baja de producto (MB1-MB2): confirmación con código y nombre, `DELETE /api/productos/${encodeURIComponent(codigo)}`, 404 con `detail`. Verificar guardas verdes y suite completa verde

## 10. Órdenes — spec `interfaz-web` (Pantalla, Estados, Borrado, Resultado)

- [x] 10.1 `static/ordenes.html` + `static/js/ordenes.js` (O1-O6): "← Inventario", filtros Desde/Hasta/Número con `URLSearchParams` omitiendo vacíos, "Filtrar"/"Ver todas", lista con componentes, cartel "No hay órdenes en ese período" ante `[]`, `detail` del 404 y del 422, cargando y error de red. Verificar guardas verdes
- [x] 10.2 Modal Borrar orden (MD1-MD4): casilla "Devolver stock" `checked` en el HTML (guarda), texto del botón según la casilla, `DELETE /api/ordenes/${encodeURIComponent(numero)}?reintegrar=true|false`, resumen de éxito con reintegro como lista, un ítem por producto (`A-01 +2 (stock 5)`, `C-99 +4 (stock 5, reactivado)`), o "Orden X borrada sin devolver stock.", 404 con `detail` y recarga. Verificar guardas verdes y suite completa verde

## 11. Ejecución local — design D9 (decisión 20)

- [x] 11.1 `README.md` mínimo "Correr en local" (venv, `.env` propio desde `.env.example`, `SECRET_KEY`, `SESSION_HTTPS_ONLY=false`, `INVENTARIO_DB_PATH=dev-local.db`, uvicorn, credenciales del `admin` y qué hacer si se perdió la contraseña generada) y comprobar que `.env.example` lista `SECRET_KEY`, `SESSION_HTTPS_ONLY`, `ADMIN_DEFAULT_PASSWORD` e `INVENTARIO_DB_PATH` sin valores (sin leer `.env`). Verificar siguiendo el README tal cual en una terminal limpia con un `INVENTARIO_DB_PATH` nuevo: arranca en http://localhost:8000 y el login del `admin` funciona

## 12. Verificación integral

- [x] 12.1 Suite completa verde: `Ran 419 + N tests ... OK`, sin cambios en las aserciones de los tests previos
- [x] 12.2 (orquestador) Verify visual con Playwright: levantar uvicorn sobre una base temporal, recorrer cada escenario de `specs/interfaz-web` y cada ítem del checklist de mockups a 390x844 y 1440x900, guardar capturas en `mockups/verify/`, revisar consola y peticiones fallidas (sin errores), emular un SO en modo claro (`emulateMedia({ colorScheme: 'light' })`) y confirmar que `/`, `/inventario`, `/ordenes` y un modal se ven oscuros (fondo de `body`, tarjeta, modal y campos según `tokens.css` Revision 2), confirmar en las peticiones de red `reintegrar=true|false` y `OT%2F2026%231`, comprobar el resumen MD3 como lista (un `li` por producto con `+cantidad (stock N)` y "reactivado" donde aplica) y el 409 de orden duplicada con el `detail` solo en la alerta y el campo número `aria-invalid`, probar el ingreso con (a) código nuevo sin nombre (422: `detail` solo en la alerta superior, Nombre `aria-invalid` con `aria-describedby` al `id` de la alerta, foco en Nombre, sin texto repetido bajo el campo, nada creado), (b) código nuevo con nombre (creado), (c) código dado de baja sin nombre (reactivado, alerta lo menciona) y (d) el aviso no bloqueante de código fuera del inventario, y reportar diferencias (blocker/major/minor); registrar `Visual verify` en `design.md`; detener el servidor
- [x] 12.3 (orquestador) Con `browser_evaluate` sobre `/inventario`, ejecutar la tabla de `verify/casos-validacion.md` contra `window.Validacion` y confirmar que todos los casos dan el mensaje esperado
- [x] 12.4 Prueba manual del usuario en http://localhost:8000 (ejecutado por el agente a pedido del usuario, 2026-11-20; capturas en `mockups/verify/e2e/`): login, ingreso, egreso, orden, listado, borrado de orden (con y sin devolver stock) y baja de producto; anotar cualquier diferencia
- [x] 12.5 `openspec validate paso-5-web-local --strict` sin errores

## Workflow follow-up

- Archivar con `/opsx:archive paso-5-web-local` tras el verify y marcar `[x]` C-06 en `CHANGES.md`.
- Actualizar la KB según `design.md` § Open Questions (02, 03, 06, 07) y anotar en `design-system/README.md` las diferencias aprobadas en los mockups (casilla "Devolver stock", filtro Número, cartel "período").
- Esperar "Continuar" del usuario antes de C-07.
