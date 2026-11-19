# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Fase 1 solo con biblioteca estándar (REEMPLAZADA por DD-12, 2026-11-19)
**Decisión original**: la Fase 1 (CLI + SQLite) usaba únicamente biblioteca estándar. Ya no aplica: desde el Paso 1 se permiten dependencias declaradas (FastAPI, etc.). Se conserva como registro histórico; la lógica de negocio sigue usando solo stdlib más SQLite.
**Contexto**: restricción de la consigna original.
**Alternativas consideradas**: usar un ORM o librería de CLI.
**Justificación**: cero dependencias, arranque inmediato, foco en lógica de negocio.
**Trade-offs aceptados**: más código manual de menú y SQL.

### DD-02 — Repositorio/DAO + services; FastAPI como adaptador
**Decisión**: separación estricta entre dominio/services, interfaces de repositorio con implementaciones SQLite y Supabase, y un adaptador HTTP delgado (FastAPI).
**Contexto**: la misma lógica y API deben migrar de SQLite a Postgres sin reescritura (la CLI ya no existe, ver DD-12).
**Alternativas consideradas**: lógica dentro de las rutas y reescritura en Fase 2.
**Justificación**: reutilización y testabilidad (TDD estricto).
**Trade-offs aceptados**: más archivos e indirección desde el inicio.

### DD-03 — FastAPI como framework web (cambio decidido por el usuario 2026-11-19)
**Decisión**: backend web en FastAPI (ASGI), con `uvicorn` en desarrollo local y `api/index.py` exportando `app` en el runtime Python de Vercel. Validación HTTP con modelos Pydantic.
**Contexto**: cambio de Flask a FastAPI decidido por el usuario el 2026-11-19, antes de escribir código de la Fase 2.
**Alternativas consideradas**: Flask (decisión original; WSGI, plantillas Jinja2).
**Justificación**: validación automática por esquema (Pydantic), inyección de dependencias para la auth, docs OpenAPI de serie, tipado; el frontend estático + API JSON encaja naturalmente.
**Trade-offs aceptados**: más dependencias; el cliente `supabase` es síncrono, por lo que los endpoints que lo usen se declaran `def` (threadpool) y no `async def`; la validación Pydantic no reemplaza a la de los services (independientes de HTTP); los tests de API requieren `httpx` (solo test).

### DD-11 — Frontend estático + API JSON, sin templates (2026-11-19)
**Decisión**: páginas HTML estáticas en `static/` (`login.html`, `index.html` = inventario, `ordenes.html`) con `static/js/` y `static/css/` (`tokens.css`, `ui.css` del design-system); todos los datos vía `fetch` a `/api/...`; ante 401 el JS redirige al login. No se usa Jinja2 ni carpeta `templates/`.
**Contexto**: el brief mencionó `templates/` solo como ejemplo ("ej."), no como requisito. FastAPI sirve estáticos con `StaticFiles` y/o el ruteo estático de Vercel (a definir en el Paso 6).
**Alternativas consideradas**: render server-side con Jinja2 y `templates/`.
**Justificación**: separación clara frontend/backend, API reutilizable, menos acoplamiento.
**Trade-offs aceptados**: la protección de las páginas depende del JS y de los 401 de la API (los datos nunca se exponen sin sesión); posible parpadeo previo a la redirección.

### DD-12 — Se elimina la CLI; backend FastAPI desde el Paso 1 verificado en /docs (2026-11-19)
**Decisión**: no hay CLI. Los pasos 1 a 4b se construyen como backend FastAPI + SQLite local, verificado con la Swagger UI (`/docs`) y tests `unittest` (`TestClient`, requiere `httpx` solo en `requirements-dev.txt`). El Paso 5 cambia la implementación del repositorio a Supabase sin tocar los services y agrega el frontend; el Paso 6 despliega. Se permiten dependencias desde el Paso 1, declaradas en `requirements.txt`/`requirements-dev.txt`, dentro de `.venv`. La lógica (`domain/`, `services/`, `repositories/`) no depende de FastAPI. Auth con cookie de sesión firmada (`SessionMiddleware`, `SECRET_KEY`), que funciona en `/docs` por ser same-origin; init de DB y seed del admin en el lifespan de FastAPI.
**Contexto**: cambio de alcance pedido por el usuario el 2026-11-19; se aparta del brief original, que exigía CLI con solo biblioteca estándar en la Fase 1.
**Alternativas consideradas**: CLI con stdlib según el brief (menú de consola, `getpass`).
**Justificación**: evita escribir y descartar una interfaz de consola; la API ya queda lista para el frontend; `/docs` da verificación manual inmediata.
**Trade-offs aceptados**: se aparta del brief; dependencias externas desde el Paso 1 (entorno virtual y `requirements*.txt`); la contraseña de `/docs` no se enmascara; la contraseña aleatoria del admin queda en el log del servidor.

### DD-04 — Sesión por cookie firmada (Starlette `SessionMiddleware`)
**Decisión**: sesión con cookie firmada con `SECRET_KEY` mediante `SessionMiddleware` (requiere `itsdangerous`); HttpOnly, SameSite=Lax, `https_only` en producción. La dependencia `get_current_user` devuelve 401 sin sesión.
**Contexto**: serverless sin estado entre requests.
**Alternativas consideradas**: JWT.
**Justificación**: el estado vive en la cookie firmada, sin infraestructura extra; menos superficie que manejar JWT a mano.
**Trade-offs aceptados**: no hay revocación individual de sesiones; rotar `SECRET_KEY` invalida todas.

### DD-05 — Clave `service_role` solo en backend, sin RLS
**Decisión**: `SUPABASE_KEY` = `service_role`, usada únicamente por el backend FastAPI; el navegador nunca habla con Supabase; no se configura RLS.
**Contexto**: riesgo de exposición de clave.
**Alternativas consideradas**: anon key + RLS con políticas por usuario.
**Justificación**: la autenticación es propia (tabla `usuarios`), no Supabase Auth; RLS no aportaría control real.
**Trade-offs aceptados**: la clave es muy poderosa; si se filtra compromete toda la base. Debe vivir solo en `.env` local (gitignored) y en variables de Vercel. Mitigación opcional: habilitar RLS sin políticas para bloquear la anon key.

### DD-06 — Atomicidad vía funciones RPC en Postgres
**Decisión**: crear orden, borrar orden con reintegro e ingreso/egreso con movimiento se implementan como funciones PL/pgSQL en `schema.sql`, invocadas por RPC.
**Contexto**: el cliente REST de Supabase no soporta transacciones multi-tabla.
**Alternativas consideradas**: llamadas secuenciales con compensación manual; conexión directa psycopg.
**Justificación**: garantiza todo-o-nada con bloqueo de filas.
**Trade-offs aceptados**: lógica de negocio duplicada en SQL (validación de stock) además de los services; hay que mantener paridad con la implementación SQLite y testearla.

### DD-07 — Contraseña inicial del admin desde variable de entorno (confirmada por el usuario 2026-11-19)
**Decisión**: la contraseña inicial de `admin` se lee de `ADMIN_DEFAULT_PASSWORD`. Si no está definida, en el backend local (SQLite) se genera una contraseña aleatoria que se imprime UNA sola vez en la consola del servidor (log de uvicorn) durante la primera inicialización (lifespan de FastAPI) (nunca se hardcodea ni se guarda en texto plano). En Supabase/Vercel la variable es obligatoria para el script de seed.
**Contexto**: la consigna pide `admin` por defecto con contraseña hasheada, pero prohíbe secretos en el código.
**Alternativas consideradas**: constante `admin/admin` documentada (descartada: insegura y contradice RN-SE-01); pedirla por consola en el primer arranque (descartada además por la eliminación de la CLI).
**Justificación**: cumple RN-SE-01 y no deja credenciales conocidas.
**Trade-offs aceptados**: un paso extra de setup; hay que anotar la contraseña generada. Se recomienda cambiarla (cambio de contraseña queda en backlog).

### DD-08 — Fecha de orden ingresada a mano
**Decisión**: `ordenes.fecha` es un DATE que ingresa el usuario; `created_at` registra el momento real de carga.
**Contexto**: permite cargar órdenes con fecha pasada.
**Alternativas consideradas**: fecha automática.
**Justificación**: decisión del usuario; el filtro por rango opera sobre `fecha`.
**Trade-offs aceptados**: posibles errores de tipeo (se valida el formato, no la razonabilidad).

### DD-09 — Movimientos solo para ingresos y egresos manuales
**Decisión**: `movimientos` registra ingresos y egresos manuales; los descuentos por orden viven en `orden_items`. Sin motivo.
**Contexto**: evitar duplicar información de las órdenes.
**Alternativas consideradas**: registrar también los descuentos de órdenes.
**Justificación**: simplicidad; la orden ya es el registro.
**Trade-offs aceptados**: no hay una bitácora única de todo cambio de stock; el reintegro por borrado de orden tampoco se registra.

### DD-10 — Ciclo OpenSpec estricto, un paso por vez
**Decisión**: cada paso pasa por propose → apply → verify → archive y se pausa hasta que el usuario diga "Continuar".
**Contexto**: consigna del proyecto.
**Justificación**: control incremental y trazabilidad.
**Trade-offs aceptados**: ritmo más lento.

## Supuestos inferidos

### SU-01 — Hoy se usan planillas o papel
**Supuesto**: el problema actual se resuelve con planillas/papel.
**Origen**: discovery; no se analizaron competidores.
**Riesgo si es falso**: el diseño podría ignorar un flujo existente (p. ej. otro sistema).
**Cómo validar**: confirmarlo con el usuario antes de la puesta en producción.

### SU-02 — Rango de fechas inclusivo
**Supuesto**: el filtro incluye ambos extremos.
**Origen**: discovery (marcado como supuesto).
**Riesgo si es falso**: órdenes faltantes o sobrantes en el listado.
**Cómo validar**: confirmado en las decisiones finales; verificar en tests del Paso 4.

### SU-03 — Ingreso sobre producto inactivo lo reactiva
**Supuesto**: reactiva y suma (mantiene código único).
**Origen**: decisión final del usuario.
**Riesgo si es falso**: choque con la unicidad del código.
**Cómo validar**: test en el Paso 2.

### SU-04 — Pocos usuarios sin concurrencia alta
**Supuesto**: uso concurrente bajo.
**Origen**: escala `team`.
**Riesgo si es falso**: condiciones de carrera en stock (mitigadas por RPC y `WHERE stock >= n`).
**Cómo validar**: pruebas de doble envío simultáneo en el Paso 5.

### SU-05 — Un producto aparece una vez por orden (resuelto)
**Supuesto**: cada producto aparece una sola línea por orden; si el usuario lo repite, las cantidades se suman (RN-OR-11, confirmado por el usuario 2026-11-19).
**Origen**: PK compuesta en `orden_items`.
**Riesgo si es falso**: necesidad de múltiples líneas por producto.
**Cómo validar**: tests del Paso 3.

### SU-06 — Reintegrar a un producto inactivo lo reactiva (resuelto)
**Supuesto**: al reintegrar stock por borrado de orden, un producto inactivo se reactiva y recibe las unidades (RN-OR-12, confirmado por el usuario 2026-11-19).
**Origen**: decisión del usuario.
**Riesgo si es falso**: productos borrados reaparecen sin que el usuario lo espere.
**Cómo validar**: tests del Paso 4b.

### SU-07 — Sin cambio de contraseña ni alta de usuarios en v1
**Supuesto**: usuarios adicionales se crean fuera de la UI (script/seed).
**Origen**: consigna no los menciona.
**Riesgo si es falso**: dependencia del desarrollador para altas.
**Cómo validar**: preguntar al usuario (PA-03).
