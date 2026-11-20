# Design — paso-5-web-local (C-06)

## Context

Ver `proposal.md` (Why). Estado actual observado (C-01..C-05 archivados, suite de 419 tests):

- **App** (`inventario/api/app.py`, `crear_app(*, ruta_db, secret_key, password_admin, https_only)`): lifespan que inicializa base y admin; `SessionMiddleware(secret_key, session_cookie="inventario_session", max_age=None, same_site="lax", https_only)`; seis routers bajo `/api`; handlers de errores de dominio y 422 en español. `GET /` hoy responde 404.
- **Cookie**: Starlette emite siempre `httponly; samesite=lax` (`security_flags` fijo) y `secure` solo con `https_only`. `tests/test_api_auth.py` ya fija HttpOnly, SameSite=Lax y `Secure` con `SESSION_HTTPS_ONLY`. Con `max_age=None` la cookie es de sesión del navegador y **la firma no vence**: una cookie copiada vale para siempre, aun después del logout (que solo borra la copia del navegador).
- **`SECRET_KEY`**: `crear_app` ya falla con un mensaje que nombra la variable si falta o está vacía (requisito "Clave de firma de sesión obligatoria"). No hay clave generada por defecto.
- **Cuerpos JSON**: sondeado contra la app real (FastAPI 0.165, Starlette 1.10): `POST /api/login` con `Content-Type` `text/plain`, `application/x-www-form-urlencoded`, `multipart/form-data` o sin `Content-Type`, con un cuerpo JSON válido, responde **422 "El cuerpo de la petición debe ser un objeto JSON."** sin cookie. No hay `CORSMiddleware`.
- **Sesión**: `get_current_user` (dependencies.py) exige `usuario_id`/`username` en la sesión y confirma que el usuario existe (si no, limpia la sesión → 401).
- **Design system** (`design-system/`, Revision 2 pendiente de aprobación — tema oscuro único; Revision 1 aprobada 2026-11-19 —, `Mode: system-and-mockups`): `tokens.css` (fuente de verdad visual), `ui.css` (`.btn`, `.field`, `.tbl`, `.modal`, `.overlay`, `.badge`…), `ui.js` (abrir/cerrar modales, trampa de foco, Escape, agregar/quitar filas, mostrar contraseña), `components.html` (inventario + modales + login) y `ordenes.html`. Sin logo ni `brand.js` (decisión del usuario): cabecera de texto "Inventario".
- **Contrato fijo**: los 10 paths `/api/...` y sus respuestas (specs principales). `tests/test_api_app.py::DocsTest` y los tests de OpenAPI de movimientos/órdenes fijan el esquema.

## Goals / Non-Goals

**Goals:**
- Cero cambios observables en `/api/...` y `/docs`: la suite actual pasa sin tocar sus aserciones.
- Las páginas no contienen datos: todo dato llega por `fetch` autenticado; las páginas solo deciden a dónde redirigir.
- Una sola fuente visual: `tokens.css`; Tailwind solo aporta utilidades de layout mapeadas a los tokens.
- Toda la lógica del navegador que se puede expresar como función pura vive en un módulo sin DOM (`validacion.js`), verificable en el navegador con una tabla de casos.

**Non-Goals:**
- Plantillas del lado del servidor (Jinja2), build de frontend, bundler o `node_modules`.
- Cambiar mensajes, códigos o cuerpos de la API, o agregar endpoints.
- Middleware CSRF, CORS o rate limiting de login (ver decisión 8 y Riesgos).
- Funcionalidades fuera de la KB (decisiones 14 y 15).

## Decisions

### D1 — Rutas y servicio de archivos (decisiones 1, 2, 3, 9)

- Router nuevo `inventario/api/routers/paginas.py` (sin prefijo, `include_in_schema=False` en cada ruta):
  - `GET /` → `FileResponse(static/login.html)`; con sesión válida → `RedirectResponse("/inventario", 303)`.
  - `GET /inventario` → `static/index.html`; `GET /ordenes` → `static/ordenes.html`; sin sesión válida → `RedirectResponse("/", 303)`.
  - Cabeceras de D1-h en las tres respuestas HTML (no en las redirecciones ni en `/api`).
- `app.mount("/static", StaticFiles(directory=<raíz>/static), name="static")`, **después** de incluir los routers `/api` y de páginas. Starlette ya devuelve 404 a directorios (sin `html=True`) y a rutas que salen del directorio.
- La ruta de `static/` se resuelve desde el paquete (`Path(__file__).resolve().parents[2] / "static"`), no desde el directorio actual, para que uvicorn funcione desde cualquier carpeta. `crear_app` no recibe parámetro nuevo (los tests usan el `static/` real).
- **Sesión opcional sin excepción**: se extrae de `get_current_user` un helper `usuario_de_sesion(request, conn) -> UsuarioAutenticado | None` (misma lógica, incluida la limpieza de la sesión si el usuario ya no existe). `get_current_user` lo usa y sigue lanzando 401: comportamiento idéntico, cubierto por los tests existentes. Las páginas usan el helper con `Depends(get_conexion)`.
- 404 desconocido: el JSON por defecto de FastAPI (`{"detail": "Not Found"}`) para páginas y `/api` (decisión 3).
- `static/index.html` y `static/ordenes.html` también son accesibles en `/static/...` sin sesión: no contienen datos (spec "La página no embebe datos") y el JS redirige ante el 401 de `/api/me`. Aceptado.

**D1-h — Cabeceras de las páginas** (decisión 9): `X-Frame-Options: DENY` (clickjacking de los botones de borrado), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cache-Control: no-store` (tras el logout, "Atrás" no muestra una página cacheada; además el JS revalida con `/api/me` en `pageshow`). Sin CSP: el Play CDN de Tailwind exige `'unsafe-inline'` y `'unsafe-eval'`, así que una CSP aportaría poco y rompería fácil.

### D2 — Sesión (decisiones 6, 7)

- `SECRET_KEY` sigue obligatoria (sin fallback de desarrollo): el arranque falla con el mensaje y el comando para generarla, que ya existen. Se documenta en el README local (D9).
- `max_age = 12 * 60 * 60` (constante `SESSION_MAX_AGE` en `app.py`). Efectos en Starlette:
  - la cookie se emite con `Max-Age=43200` (pasa a ser persistente por 12 h: sobrevive a cerrar el navegador dentro de ese plazo);
  - `TimestampSigner.unsign(max_age=...)` rechaza firmas de más de 12 h → la sesión queda vacía → 401 / login;
  - Starlette **reemite** la cookie en cada respuesta mientras la sesión tenga datos, así que es una vigencia **deslizante**: 12 h desde la última petición, no desde el login.
- El logout sigue igual (`session.clear()` → Starlette borra la cookie). Una cookie robada sigue siendo válida hasta 12 h (no hay lista de revocación; ver Riesgos).

### D3 — CSRF (decisión 8)

Análisis por vector, con SameSite=Lax, sin CORS y cuerpos solo JSON:

| Vector | ¿El navegador manda la cookie? | ¿Tiene efecto? |
|--------|-------------------------------|----------------|
| `<form method=post>` cross-site a `/api/login` (login CSRF) | No (Lax no envía en POST cross-site). Además el cuerpo sería `x-www-form-urlencoded` o `multipart` | No: 422, sin cookie |
| `fetch` cross-site `text/plain` con JSON (petición "simple", sin preflight) | No (Lax no envía en subrecursos cross-site) | No: 422 por tipo de contenido |
| `fetch` cross-site con `Content-Type: application/json` o método `DELETE` | Requiere preflight `OPTIONS` | No: el preflight responde 405 sin `Access-Control-Allow-*`; el navegador no envía la petición real |
| `fetch(..., {mode: "no-cors"})` | El navegador descarta `Content-Type: application/json` y prohíbe `DELETE` | No: 422 / la petición no sale |
| Navegación GET cross-site de nivel superior (Lax **sí** envía la cookie) | Sí | No: los GET no tienen efectos y la respuesta no es legible por el atacante |
| **Mismo sitio** (otra app en `localhost:3000`: puertos distintos son *same-site*, Lax no protege) | Sí | Las escrituras siguen bloqueadas por JSON + preflight. **Solo `POST /api/logout`** (sin cuerpo) se puede forzar con un `text/plain`: cierra la sesión (molestia, sin daño) |

Decisión ★: **apoyarse en SameSite=Lax + cuerpos solo JSON + sin CORS, fijado por tests** (spec api-http "Escrituras solo con cuerpo JSON" y "Sin acceso entre orígenes"). No cambia ninguna respuesta de `/api`. Si en el futuro se habilita CORS o se acepta un cuerpo no JSON, este análisis se cae y hay que agregar un chequeo de `Origin` (registrado en Riesgos y para C-08).

### D4 — Estructura del frontend

```
static/
├── login.html        index.html (inventario)        ordenes.html
├── css/tokens.css    css/ui.css          # copias idénticas de design-system/ (decisión 4)
└── js/
    ├── tailwind-config.js   # tailwind.config con colores/fuentes/radios -> var(--token) (decisión 5)
    ├── validacion.js        # funciones puras, sin DOM ni fetch (window.Validacion)
    ├── api.js               # wrapper de fetch (D5)
    ├── ui.js                # modales, foco, Escape, alertas, filas (evolución de design-system/ui.js)
    ├── sesion.js            # /api/me en la cabecera, "Cerrar sesión", revalidación en pageshow
    ├── login.js   inventario.js   ordenes.js
```

- Scripts clásicos con `defer` (sin módulos ES ni build); cada archivo expone un único objeto global (`Validacion`, `Api`, `UI`).
- Inserción de datos solo con `textContent`, `createElement` y `setAttribute` (spec "Datos mostrados como texto"; KB 08). Prohibidos `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` y `eval` (guarda en tests, D8).
- Códigos en URL siempre con `encodeURIComponent` (`DELETE /api/productos/{codigo}`, `DELETE /api/ordenes/{numero}`); los filtros con `URLSearchParams`, omitiendo los vacíos.
- Selección de producto en egreso y nueva orden: `<select>` con los activos del último `GET /api/inventario` ("CÓDIGO · Nombre (stock N)", p. ej. "A-01 · Tornillo M8 (stock 7)") (decisión 11). Los productos nuevos se crean solo desde el modal de ingreso (código en texto libre con `<datalist>` de los códigos activos); egreso y nueva orden usan el desplegable. **Nombre en el ingreso** (decisión 12): el navegador no puede distinguir un código nuevo de uno dado de baja (el inventario solo lista activos), así que decide el backend y la API no cambia. El campo Nombre nunca se bloquea en el cliente; si el código no está en el inventario cargado se muestra el aviso no bloqueante "Código nuevo o dado de baja: si es nuevo, indicá un nombre.". Si la API responde 422 con `detail` "El producto 'X' no existe: indicá un nombre para crearlo.", el modal queda abierto, muestra ese `detail` solo en la alerta superior del modal (no se repite bajo el campo), marca Nombre como inválido (`aria-invalid="true"`, enlazado a la alerta con `aria-describedby`) y enfoca Nombre. Un producto inactivo sin nombre lo reactiva el backend y la alerta de éxito dice que fue reactivado.
- Tras cada escritura exitosa se recarga `GET /api/inventario` (no se recalcula el stock en el cliente).

### D5 — Wrapper `Api` (decisiones 10, 16)

- `Api.pedir(metodo, url, cuerpo?)`: `credentials: "same-origin"`, `Accept: application/json`, y si hay cuerpo `Content-Type: application/json` + `JSON.stringify`.
- Resultado: resuelve con el JSON (o `null` en 204); rechaza con `ApiError {status, detail, faltantes?}`:
  - 401 en cualquier URL distinta de `/api/login` → `location.assign("/?sesion=expirada")` (y la promesa no resuelve, para que nadie pinte un error encima).
  - 4xx con `detail` string → se usa tal cual.
  - 5xx o sin `detail` → "Ocurrió un error inesperado. Probá de nuevo." (status conservado).
  - `TypeError` de red → `status: 0`, "No se pudo conectar con el servidor. Revisá que esté en marcha y probá de nuevo.".
- Los errores de un modal se muestran en una alerta `role="alert"` arriba del formulario, el modal queda abierto con los datos (decisión 16). Mapeo por línea de la nueva orden: `faltantes[].codigo` → todas las líneas con ese código (la API consolida líneas repetidas); 404 de productos → líneas cuyo código aparece entre comillas en el `detail`; 422 `^Componente (\d+):` → esa línea; 409 de número duplicado → campo número. **Un `detail` de la API se muestra solo en la alerta superior** (decisión del usuario, 2026-11-20): si afecta a un único campo (Nombre en el 422 del ingreso, número en el 409 de orden duplicada), ese campo queda `aria-invalid="true"`, con `aria-describedby` apuntando al `id` de la alerta y con el foco, sin repetir el texto debajo. Los errores de validación del navegador sí van bajo su campo, y las marcas por línea de la nueva orden ("Disponible D, solicitado S", 404 de código, "Componente N") llevan su propio texto en la línea.

### D6 — Validación en el navegador (decisión 13)

`validacion.js` (puro, cada función devuelve `null` o el mensaje):
- `requerido(valor, etiqueta)` → recorta; "El código es obligatorio." / "El nombre…" / "La contraseña es obligatoria."…
- `cantidad(texto)` → `/^\d+$/` y 1..10.000 → "La cantidad debe ser un entero entre 1 y 10.000." (mismo texto que el backend).
- `largo(valor, max, etiqueta)` → "El código admite hasta 50 caracteres." (número 30, código 50, nombre 120, usuario 64, contraseña 128).
- `fecha(texto)` → `/^\d{4}-\d{2}-\d{2}$/` + fecha real (round-trip por `Date.UTC`) → "La fecha debe ser una fecha real con formato AAAA-MM-DD.".
- `rango(desde, hasta)` → "Desde no puede ser posterior a Hasta.".
- `componentes(lineas)` → 1..100 líneas, cada una con producto y cantidad válidos; devuelve errores por índice.

Los mensajes del navegador usan la etiqueta visible ("El código…"); los del backend ("El campo codigo…") se muestran tal cual cuando llegan. El backend sigue siendo la autoridad (RN-VA-04).

### D7 — Tailwind CDN y tokens (decisión 5)

- `tokens.css` es la única fuente de color, tipografía, radios, sombras, foco y movimiento. `tailwind-config.js` solo mapea nombres (`bg-surface`, `text-ink`, `border-line`, `text-accent-text`, `bg-danger-subtle`…) a `var(--token)`, igual que `components.html`.
- Tailwind aporta layout (flex, grid, gap, padding, breakpoints `sm:`), nunca colores de su paleta (`bg-gray-100`, `text-red-600`…): guarda en tests (D8). Los modificadores de opacidad (`/50`) no funcionan con variables hex; se usan los tokens `*-subtle`.
- Script del Play CDN con versión exacta (`https://cdn.tailwindcss.com/3.4.<x>`, la versión se fija en el apply comprobando que la URL responda). Sin internet, `tokens.css` + `ui.css` siguen dando estilo a botones, campos, tablas y modales, pero se pierde el layout de utilidades (aceptado; ver Riesgos).

### D8 — Tests (decisión 19)

Strict TDD, `unittest` + `TestClient`, SQLite real en archivo temporal (`tests/helpers.app_de_test`), sin mocks de base:
- `tests/test_api_paginas.py`: `/` sin sesión, con sesión (303), con sesión de usuario borrado; `/inventario` y `/ordenes` con y sin sesión; HTML sin datos; cabeceras; `/ordenes` vs `/api/ordenes`; 404 de página y de `/api`; `/docs` 200.
- `tests/test_api_static.py`: CSS/JS con su `Content-Type`; travesía (`..%2F`), directorios; acceso sin sesión.
- `tests/test_api_sesion_vigencia.py`: `Max-Age=43200` en el login; cookie firmada hace 13 h → 401 y hace 11 h → 200, construida con `itsdangerous.TimestampSigner` (subclase con `get_timestamp` fijo; es la clave real, no un mock de la app).
- `tests/test_api_csrf.py`: login/ingreso/egreso/orden con `text/plain`, `x-www-form-urlencoded`, `multipart/form-data` → 422 sin efectos (stock, movimientos, órdenes, cookie); preflight `OPTIONS` → no 2xx sin `Access-Control-Allow-Origin`; GET con `Origin` ajeno sin cabeceras CORS.
- `tests/test_frontend_estatico.py` (guardas sobre los archivos, no sobre el comportamiento del navegador): las tres páginas existen, `lang="es"`, cargan `/static/css/tokens.css`, `/static/css/ui.css`, `tailwind-config.js` y el Tailwind con versión exacta, y todo `src`/`href` local resuelve con 200; `static/css/tokens.css` y `ui.css` son idénticos a `design-system/`; ningún `.js` usa `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`document.write`/`eval(`; ningún HTML usa colores de la paleta de Tailwind; el campo de contraseña es `type="password"`; la casilla "Devolver stock" está `checked` en el HTML.
- OpenAPI: el test existente de las diez rutas sigue igual (prueba que las páginas no aparecen).
- **Comportamiento del navegador** (validación, modales, mapeo de errores, `encodeURIComponent`, sesión expirada): en el verify con Playwright contra los mockups aprobados. `validacion.js` se ejercita con `browser_evaluate` sobre una tabla de casos (tarea 12.3). No hay runner de JS: Node no es dependencia declarada (regla dura 1) y la regla dura 4 fija `unittest`.

### D9 — Ejecución local (decisión 20)

`README.md` mínimo, sección "Correr en local" (C-08 lo amplía con el despliegue):
1. `python -m venv .venv` y `.venv/Scripts/python -m pip install -r requirements-dev.txt`.
2. Crear **su propio** `.env` a partir de `.env.example` con `SECRET_KEY` (generada con `python -c "import secrets; print(secrets.token_urlsafe(32))"`), `SESSION_HTTPS_ONLY=false`, `INVENTARIO_DB_PATH=dev-local.db` y, opcionalmente, `ADMIN_DEFAULT_PASSWORD`.
3. `.venv/Scripts/python -m uvicorn inventario.api.main:app --reload` y abrir http://localhost:8000.
4. Credenciales: usuario `admin`; contraseña = `ADMIN_DEFAULT_PASSWORD` si se definió **antes del primer arranque sobre esa base**, o la generada que aparece **una sola vez** en el log de uvicorn. Si se perdió: apuntar `INVENTARIO_DB_PATH` a un archivo nuevo (o borrar el `.db` de desarrollo) y arrancar de nuevo. El `.db` está en `.gitignore` (`*.db`).

Los agentes nunca leen ni escriben `.env`; `.env.example` ya lista los nombres (se verifica en el apply que incluya `SECRET_KEY`, `SESSION_HTTPS_ONLY`, `ADMIN_DEFAULT_PASSWORD` e `INVENTARIO_DB_PATH`, sin valores).

### Tabla de rutas del change

| Método | Ruta | Sesión | Respuesta |
|--------|------|--------|-----------|
| GET | `/` | no | 200 HTML login; 303 → `/inventario` si hay sesión válida |
| GET | `/inventario` | sí | 200 HTML; 303 → `/` sin sesión |
| GET | `/ordenes` | sí | 200 HTML; 303 → `/` sin sesión |
| GET | `/static/{ruta}` | no | 200 archivo; 404 inexistente/directorio/travesía |
| * | `/api/...` | igual que hoy | sin cambios |

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-20)
- Mockups: openspec/changes/paso-5-web-local/mockups/
- Approval: approved (2026-11-20, by user)
- Preview: rendered (2026-11-20, re-render con design system Revision 2 — tema oscuro único — y SO emulado en modo claro: `mockups/previews/` 46 estados × 390x844 y 1440x900; `design-system/previews/ds-*.png`; fondo oscuro verificado en todos, sin scroll horizontal ni desbordes)
- Visual verify: differences (2026-11-20, Playwright 390x844 y 1440x900, 80 capturas en `mockups/verify/`; 0 blockers, 0 majors, 4 minors; 2 defectos hallados y corregidos durante el verify: `hidden` pisado por `flex` y conexion SQLite entre hilos; ver informe)
- E2E localhost (2026-11-20, agente a pedido del usuario, tarea 12.4): recorrido real por la UI (login erroneo/correcto, ingresos, egresos, ordenes, filtros, borrados con y sin reintegro, baja, reactivacion, logout, acceso sin sesion) con base temporal; 0 defectos nuevos; 14 capturas en `mockups/verify/e2e/`

**Tema**: siempre oscuro (decisión del usuario 2026-11-20); sin selector de tema; `color-scheme: dark`. `tokens.css` (Revision 2) define solo la paleta oscura en `:root` y no sigue `prefers-color-scheme`.

**Detalles de mockup resueltos por el usuario (2026-11-20)** — se implementan tal como se ven en los mockups:
1. **MO4 (404 de una línea en nueva orden)**: alerta con el `detail` de la API arriba + la línea marcada en rojo con el texto de ayuda debajo "Este producto ya no está activo: elegí otro o quitá la línea." (es una indicación de qué hacer, no repite el mensaje de la API); el desplegable se refresca con los productos activos.
2. **MB2 (baja de un producto ya inactivo, 404)**: alerta con el `detail`, texto "El inventario se actualizó.", la lista de fondo ya refrescada y un único botón "Cerrar" con foco (se quitan "Cancelar"/"Eliminar").
3. **Stock bajo**: fuera de alcance; solo se resalta `stock = 0` (`sin_stock`), coherente con la decisión 15.

Base: `design-system/components.html` y `ordenes.html`, importando `design-system/tokens.css` y `ui.css`; cabecera de texto "Inventario" (sin logo). Cada mockup se renderiza a **390x844** y **1440x900**; los estados de un mismo modal pueden ir en un HTML con selector de estado. Cambios respecto del design system aprobado que los mockups deben reflejar: casilla "Devolver stock" (no radios "¿Reintegrar stock?"), cartel "No hay órdenes en ese período" (no "rango"), filtro Número en `/ordenes`, selector de producto en egreso.

Checklist de pantallas y estados:

- **Login** (`/`)
  - [ ] L1 vacío
  - [ ] L2 error 401 "Usuario o contraseña incorrectos." (contraseña vaciada)
  - [ ] L3 validación de campos vacíos
  - [ ] L4 enviando ("Ingresando…", deshabilitado)
  - [ ] L5 aviso "Tu sesión expiró. Ingresá de nuevo."
- **Inventario** (`/inventario`)
  - [ ] I1 con datos: cabecera (Inventario, Usuario: admin, Cerrar sesión), barra de acciones, conteo, stock 0 resaltado, acción "Eliminar"
  - [ ] I2 vacío "Todavía no hay productos"
  - [ ] I3 cargando
  - [ ] I4 error de red con "Reintentar"
  - [ ] I5 alerta de éxito tras una operación
- **Modal Ingreso**
  - [ ] MI1 vacío (nombre opcional, nunca bloqueado en el cliente)
  - [ ] MI2 aviso no bloqueante "Código nuevo o dado de baja: si es nuevo, indicá un nombre."
  - [ ] MI3 error de validación de cantidad
  - [ ] MI4 422 de la API: `detail` solo en la alerta superior; Nombre inválido, enlazado a la alerta y con foco
- **Modal Egreso**
  - [ ] ME1 selector de producto con stock actual
  - [ ] ME2 409 "disponible 4, solicitado 10"
  - [ ] ME3 404 producto ya no activo
- **Modal Nueva orden**
  - [ ] MO1 varias líneas, fecha de hoy
  - [ ] MO2 validación del navegador por línea
  - [ ] MO3 409 con faltantes marcados por línea
  - [ ] MO4 404 código inexistente
  - [ ] MO5 422 "Componente N: …"
  - [ ] MO6 409 número duplicado: `detail` solo en la alerta superior; campo número inválido, enlazado a la alerta y con foco
  - [ ] MO7 enviando (botón deshabilitado); 100 líneas con "Agregar componente" deshabilitado
- **Modal Baja de producto**
  - [ ] MB1 confirmación
  - [ ] MB2 404
- **Órdenes** (`/ordenes`)
  - [ ] O1 filtros Desde/Hasta/Número + lista con componentes (código, nombre, cantidad)
  - [ ] O2 "No hay órdenes en ese período"
  - [ ] O3 404 "No existe una orden con número 'X'."
  - [ ] O4 422 de fechas (rango invertido del navegador y error de la API)
  - [ ] O5 cargando
  - [ ] O6 error de red
- **Modal Borrar orden**
  - [ ] MD1 casilla "Devolver stock" marcada → "Borrar y devolver stock"
  - [ ] MD2 desmarcada → "Borrar sin devolver stock"
  - [ ] MD3 resumen de éxito con reintegro (lista, un ítem por producto: `+cantidad (stock N)`, "reactivado" donde aplica) y sin reintegro
  - [ ] MD4 404 orden ya borrada
- **Transversal**
  - [ ] T1 foco visible en botón, campo y modal
  - [ ] T2 tema oscuro único: I1 y O1 con el SO en modo claro (`prefers-color-scheme: light`) se ven oscuros
  - [ ] T3 sin scroll horizontal de página a 390x844

## Risks / Trade-offs

- [Cookie robada válida hasta 12 h, también tras el logout] → vigencia de 12 h (antes: para siempre). Revocación real (lista de sesiones) queda fuera de v1; `SECRET_KEY` nueva invalida todas.
- [Cookie persistente: sobrevive a cerrar el navegador dentro de las 12 h] → trade-off aceptado frente a una firma sin vencimiento; en equipos compartidos, "Cerrar sesión".
- [Defensa CSRF implícita: depende de que ningún endpoint acepte cuerpos no JSON ni se habilite CORS] → fijada por tests (`test_api_csrf.py`); si C-07/C-08 agregan CORS o formularios, agregar chequeo de `Origin`.
- [Logout forzable desde otra app en `localhost`] → solo cierra la sesión; aceptado.
- [Sin rate limiting del login] → app local de un usuario; fuera de alcance, a revisar en C-08 (Vercel).
- [Tailwind Play CDN: requiere internet, no apto para producción según Tailwind y bloquea una CSP útil] → versión fijada; sin internet la UI queda usable con `ui.css`; para C-08 se puede reemplazar por CSS precompilado sin tocar los HTML (las clases son las mismas).
- [Copias de `tokens.css`/`ui.css` en `static/css`] → test de igualdad byte a byte con `design-system/`: cambiar un token exige actualizar ambos (y subir la Revision).
- [Lógica JS sin tests unitarios automatizados] → la parte pura está aislada en `validacion.js` y se ejercita en el verify con Playwright; las guardas estáticas cubren las reglas de seguridad.
- [Estado desactualizado entre pestañas] → cada escritura recarga el inventario; los 404/409 muestran el `detail` y recargan la lista.

## Migration Plan

Sin DDL ni cambios de datos. Las bases locales existentes sirven tal cual. Al desplegar, las cookies emitidas antes de este change (sin vencimiento) siguen siendo válidas hasta que el navegador las borre o la firma supere 12 h (la firma lleva timestamp desde C-01, así que también vencen). Rollback: revertir el código; `/api` no cambió.

## Open Questions

- Versión exacta del Play CDN de Tailwind 3.4.x (se fija en el apply verificando que la URL responda; no cambia specs ni tareas).
- Al archivar, actualizar la KB: 02 (`POST /api/movimientos/ingreso|egreso` → `/api/stock/...`; `GET /dashboard` → `/inventario`), 06 (US-007 "modal de listado" → pantalla `/ordenes`; "el Paso 5 migra a Supabase" → C-07), 07 Flujo 1 (`static/index.html` → `/inventario`) y Flujo 6 ("¿Reintegrar el stock?" → casilla "Devolver stock"), 03 (rutas públicas: sumar la redirección de `/inventario` y `/ordenes`).

## Decisiones a confirmar por el usuario

> Governance ALTO: el apply no empieza hasta que el usuario revise estas decisiones **y** apruebe los mockups. ★ = recomendada.
>
> **Revisión del usuario (2026-11-20):** las decisiones 1-11 y 13-20 se aprobaron con la opción ★; la 12 se aprobó con un ajuste (ver abajo). Falta la aprobación de los mockups.

1. **URL de las pantallas.**
 **Aprobada (2026-11-20).**
   - A ★ `/` login, `/inventario` inventario, `/ordenes` órdenes (respeta KB 03: `GET /` es el login).
   - B `/` inventario y `/login` login.
   - C las páginas directas de KB 07 (`/static/index.html`), sin rutas propias.

2. **Quién protege las páginas.**
 **Aprobada (2026-11-20).**
   - A ★ El servidor redirige (303) `/inventario` y `/ordenes` a `/` sin sesión, y `/` a `/inventario` con sesión; el JS además maneja el 401 de cualquier llamada. Sin parpadeo de una pantalla vacía.
   - B Solo el JS: la página carga siempre y redirige tras el 401 de `/api/me`.

3. **404 de páginas desconocidas.**
 **Aprobada (2026-11-20).**
   - A ★ El JSON por defecto `{"detail": "Not Found"}`, igual que `/api` (cero código nuevo).
   - B Una página HTML 404 con enlace al inventario.

4. **CSS y JS del design system en la app.**
 **Aprobada (2026-11-20).**
   - A ★ Copiar `tokens.css` y `ui.css` a `static/css/` con un test que exige que sean idénticos a `design-system/`; `ui.js` evoluciona a `static/js/ui.js`.
   - B Servir también `design-system/` (otra montura pública).
   - C Mover los archivos a `static/` y que `design-system/` apunte ahí.

5. **Tailwind CDN y fuente de verdad visual.**
 **Aprobada (2026-11-20).**
   - A ★ `tokens.css` manda; Tailwind solo layout, con colores mapeados a tokens; Play CDN con versión exacta; test que prohíbe colores de la paleta de Tailwind. Sin internet se pierde el layout de utilidades.
   - B Igual que A pero con la URL sin versión, como en el design system.
   - C Sin Tailwind: todo en `ui.css` (contradice el stack de la KB).

6. **`SECRET_KEY` ausente.**
 **Aprobada (2026-11-20).**
   - A ★ Mantener que el arranque falle con el mensaje y el comando para generarla (ya implementado y en spec). Un paso más la primera vez, cero riesgo de llegar a producción sin clave.
   - B Fallback de desarrollo: clave aleatoria por proceso con advertencia en el log (cada reinicio o `--reload` cierra la sesión; riesgo de desplegar así).

7. **Vigencia de la sesión.** (Revisa la decisión 7 de C-01, que dejó la cookie sin vencimiento.)
 **Aprobada (2026-11-20).**
   - A ★ 12 h deslizantes (`Max-Age=43200`; la firma vence a las 12 h de la última petición). La cookie sobrevive a cerrar el navegador dentro de ese plazo.
   - B 8 h deslizantes (una jornada).
   - C Sin vencimiento (como hoy): se borra al cerrar el navegador, pero una cookie copiada vale para siempre.

8. **Defensa CSRF.**
 **Aprobada (2026-11-20).**
   - A ★ SameSite=Lax + cuerpos solo JSON + sin CORS, fijado por tests. No cambia ninguna respuesta de `/api`. Único hueco: forzar un logout desde otra app en `localhost` (molestia).
   - B A + chequeo de `Origin`/`Referer` en métodos de escritura (403 nuevo: cambia el contrato de `/api`, hay que cuidar `/docs` y `TestClient`).
   - C Token CSRF (doble envío o sincronizado): más código en front y back sin vector real que cubrir hoy.

9. **Cabeceras de seguridad en las páginas HTML.**
 **Aprobada (2026-11-20).**
   - A ★ `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cache-Control: no-store`, solo en `/`, `/inventario` y `/ordenes`.
   - B Ninguna.
   - C A + Content-Security-Policy (con el Play CDN exige `'unsafe-inline'` y `'unsafe-eval'`: poco valor).

10. **Aviso de sesión expirada.**
 **Aprobada (2026-11-20).**
    - A ★ Ante un 401, ir a `/?sesion=expirada` y mostrar "Tu sesión expiró. Ingresá de nuevo.".
    - B Volver al login sin aviso.

11. **Cómo se elige el producto en egreso y nueva orden.**
 **Aprobada (2026-11-20).**
    - A ★ Desplegable con los productos activos ("CÓDIGO · Nombre (stock N)", p. ej. "A-01 · Tornillo M8 (stock 7)") (US-006: "solo productos activos seleccionables"); evita códigos mal tipeados. Aclaración: los productos nuevos se crean solo desde el modal de ingreso (código en texto libre); egreso y nueva orden usan siempre el desplegable de activos con su stock.
    - B Texto libre con sugerencias (`datalist`), como el ingreso.

12. **Nombre en el ingreso.**
 **Aprobada con ajuste del usuario (2026-11-20).**
    - A ★ (original) Siempre visible y opcional; aviso "Código nuevo" sin bloquear; decide el backend (422).
    - B Exigir el nombre en el navegador cuando el código no está en el inventario (obliga a escribir un nombre también para reactivar).
    - **Ajuste aprobado:** el nombre es obligatorio solo si el producto es nuevo y NO lo es si está dado de baja (reactivación). Como el navegador no distingue ambos casos, decide el backend y la API no cambia: (1) el modal no bloquea Nombre en el cliente; (2) si el código no está en el inventario activo, aviso no bloqueante "Código nuevo o dado de baja: si es nuevo, indicá un nombre"; (3) ante el 422 "El producto 'X' no existe: indicá un nombre para crearlo." el modal muestra el mensaje en su alerta superior, marca Nombre como inválido (`aria-invalid`, enlazado a la alerta con `aria-describedby`, sin repetir el texto bajo el campo), sigue abierto y enfoca Nombre; (4) un inactivo sin nombre se reactiva y la alerta de éxito lo indica.

13. **Texto de los errores del navegador.**
 **Aprobada (2026-11-20).**
    - A ★ Con la etiqueta visible ("El código es obligatorio."); la cantidad usa el mismo texto que el backend. Los `detail` de la API se muestran tal cual.
    - B Copiar exactamente los textos del backend ("El campo codigo es obligatorio.").

14. **Búsqueda en el inventario.**
 **Aprobada (2026-11-20).**
    - A ★ Fuera de alcance (no está en la KB ni en el design system).
    - B Filtro en el navegador por código o nombre sobre la tabla (sin cambios de API).

15. **Otros fuera de alcance** (confirmar la lista completa).
 **Aprobada (2026-11-20).**
    - A ★ Sin UI de movimientos (KB 03: fuera de v1), sin paginación (PA-08: volumen chico), sin cambio de contraseña ni alta de usuarios (PA-03), sin umbral de "stock bajo" (solo stock 0).
    - B Indicar cuáles de estos entran.

16. **Dónde se muestran los errores de la API en los modales.**
 **Aprobada (2026-11-20).**
    - A ★ Alerta arriba del formulario con el `detail`, el modal sigue abierto con los datos y, en nueva orden, las líneas afectadas marcadas (faltantes "Disponible D, solicitado S", 404 de código, "Componente N").
    - B Solo la alerta general, sin marcar líneas.
    - **Precisión del usuario (2026-11-20):** el `detail` aparece solo en la alerta superior; un campo único afectado (Nombre en MI4, número en MO6) queda inválido, enlazado a la alerta por `aria-describedby` y con el foco, sin repetir el texto. Las marcas por línea de la nueva orden se mantienen.

17. **Aviso de éxito.**
 **Aprobada (2026-11-20).**
    - A ★ Alerta `role="status"` sobre la tabla, que queda hasta la próxima acción; en el borrado de orden, resumen por producto (cantidad devuelta, stock final, "reactivado").
    - B Aviso temporal (toast) de unos segundos, sin detalle del reintegro.
    - **Precisión del usuario (2026-11-20):** el resumen del borrado con reintegro es una lista, un ítem por producto (`A-01 +2 (stock 5)`, `C-99 +4 (stock 5, reactivado)`), como en el mockup MD3. Navegación: se mantienen el enlace "← Inventario" y la navegación de la cabecera.

18. **Fecha propuesta en nueva orden.**
 **Aprobada (2026-11-20).**
    - A ★ Hoy (fecha local del navegador), editable; la API sigue exigiéndola explícita (DD-08).
    - B Vacía: el usuario la escribe siempre.

19. **Pruebas de la lógica del navegador.**
 **Aprobada (2026-11-20).**
    - A ★ `unittest` cubre servidor y guardas estáticas; `validacion.js` (puro) y el comportamiento de las pantallas se prueban en el verify con Playwright contra los mockups aprobados.
    - B Ejecutar JS con Node desde `unittest` (dependencia no declarada: viola la regla dura 1).
    - C Duplicar la validación en Python para testearla (no prueba el JS real).

20. **Instrucciones para correr en local.**
 **Aprobada (2026-11-20).**
    - A ★ `README.md` mínimo con "Correr en local" (venv, `.env` propio, `SECRET_KEY`, `INVENTARIO_DB_PATH=dev-local.db`, uvicorn, credenciales del admin y qué hacer si se perdió la contraseña generada); C-08 lo amplía.
    - B Solo en este `design.md` y en las tareas.
