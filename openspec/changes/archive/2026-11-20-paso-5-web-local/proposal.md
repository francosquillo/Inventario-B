# Proposal — paso-5-web-local (C-06)

## Why

La API de C-01..C-05 está completa pero solo se opera desde la Swagger UI (`/docs`), que no es una herramienta para el taller. US-010 pide operar todo desde el navegador (login, inventario, ingreso/egreso, órdenes y borrados) y la KB (11, decisión del usuario 2026-11-20) ordena hacerlo primero en local sobre SQLite, antes de migrar a Supabase (C-07), para cazar bugs sin internet ni claves. Es el primer change con UI: aplica la política `system-and-mockups` con el design system (Revision 2: tema oscuro único, pendiente de aprobación; Revision 1 aprobada 2026-11-19).

Governance **ALTO**: toca la sesión (cookie, vigencia, CSRF) y agrega páginas públicas a la misma app que sirve la API.

## What Changes

- **Frontend estático** en `static/` servido por la misma app FastAPI (uvicorn en http://localhost:8000), HTML + Tailwind CDN + JS vanilla con `fetch` a `/api/...`, sin Jinja2 ni `templates/`:
  - `GET /` → página de login (con sesión válida redirige a `/inventario`).
  - `GET /inventario` → inventario primero: tabla con `sin_stock` resaltado, estado vacío y barra de acciones; ingreso, egreso, nueva orden y baja de producto como **modales**.
  - `GET /ordenes` → pantalla aparte con filtros Desde/Hasta/Número, lista con componentes, cartel "No hay órdenes en ese período" cuando la API devuelve `[]`, el `detail` del 404 cuando el número no existe y modal de borrado con la casilla **"Devolver stock" marcada por defecto** (botón "Borrar y devolver stock" / "Borrar sin devolver stock"; siempre envía `reintegrar=true|false` y el número con `encodeURIComponent`).
  - `/static/*` con `StaticFiles` (CSS del design system, JS).
  - Las páginas sin sesión redirigen al login; ante un 401 de la API el JS vuelve al login con aviso de sesión expirada.
- **Validación en el frontend** (regla dura 3, RN-VA-04): cantidades enteras 1..10.000, obligatorios, fechas `AAAA-MM-DD` reales, longitudes (número 30, código 50, nombre 120); el backend sigue siendo la autoridad y su `detail` se muestra tal cual (422/404/409, incluido el detalle por fila de los `faltantes` del 409 de órdenes).
- **Endurecimiento de la sesión**: se confirma y fija por test HttpOnly, SameSite=Lax, `Secure` según `SESSION_HTTPS_ONLY` y `SECRET_KEY` obligatoria (ya existentes); se agrega una **vigencia de 12 h** (decisión 7, revisa la decisión 7 de C-01) y cabeceras de seguridad en las páginas HTML.
- **Revisión CSRF de login/logout y del resto de escrituras** (observación del verify de C-01): se documenta el análisis y se fija por tests la defensa elegida (SameSite=Lax + cuerpos solo JSON + sin CORS), sin cambiar respuestas de `/api`.
- **Contrato `/api/...` sin cambios**: mismos endpoints, códigos, cuerpos y mensajes; las rutas de página no aparecen en OpenAPI y `/docs` sigue disponible. Services y repositorios no se tocan.
- Instrucciones de ejecución local (credenciales del `admin`, `SECRET_KEY`, `INVENTARIO_DB_PATH`) en un `README.md` mínimo (decisión 20).
- Mockups del change (gate) en `openspec/changes/paso-5-web-local/mockups/`, aprobados por el usuario **antes** del apply.

Fuera de alcance (decisiones 14 y 15): búsqueda en el inventario, UI de movimientos (KB 03: fuera de v1), paginación (PA-08), cambio de contraseña / alta de usuarios (PA-03), migración a Supabase (C-07), despliegue (C-08), umbral de "stock bajo" (TBD del design system).

## Capabilities

### New Capabilities

- `interfaz-web`: la interfaz de navegador: pantallas (login, inventario, órdenes), modales, estados (cargando, vacío, error, éxito), validación del lado del cliente, presentación de errores de la API, manejo de sesión expirada, accesibilidad básica y uso del design system.

### Modified Capabilities

- `api-http`: se agregan requisitos de servicio de páginas y estáticos (rutas `/`, `/inventario`, `/ordenes`, `/static/*`, redirecciones por sesión, sin pisar `/api/*` ni aparecer en OpenAPI), vigencia de la sesión, cabeceras de las páginas y la defensa CSRF fijada por tests. Ningún requisito existente de `/api` cambia.

## Impact

- **Código nuevo**: `static/` (`login.html`, `index.html`, `ordenes.html`, `css/tokens.css`, `css/ui.css`, `js/*.js`); rutas de página en `inventario/api/` (router nuevo `paginas.py`), montaje de `StaticFiles` y `max_age` en `app.py`; helper de sesión opcional en `dependencies.py` (sin cambiar `get_current_user`).
- **Tests nuevos** (`unittest` + `TestClient`, SQLite real): páginas y redirecciones, estáticos (incluida la travesía de rutas), cookie y vigencia, CSRF, cabeceras, OpenAPI sin cambios y guardas estáticas del frontend. Suite actual: 419 tests, que deben seguir verdes.
- **Sin dependencias nuevas** (`StaticFiles`/`FileResponse` son de Starlette). Tailwind se carga por CDN con versión fijada: el estilo de layout requiere internet (decisión 5).
- **Documentación**: `README.md` mínimo (correr en local); al archivar, actualizar KB 02/06/07 (rutas de página y nombres de endpoints desactualizados).
