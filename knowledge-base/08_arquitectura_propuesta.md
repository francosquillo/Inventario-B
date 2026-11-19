# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Repositorio / DAO | Interfaces por agregado con implementación SQLite y Supabase | Desacopla la lógica del motor de datos; la Fase 2 solo agrega una implementación |
| Capa de servicios (dominio) | Reglas de negocio y validaciones | Una única implementación, independiente de FastAPI, reutilizada sin cambios al pasar de SQLite a Supabase |
| Adaptador delgado | Rutas FastAPI | Solo traducen entrada/salida; cero reglas de negocio |
| Unidad de trabajo atómica | `crear_con_descuento`, `borrar_con_reintegro`, `registrar_movimiento` en el repositorio | Todo-o-nada: transacción en SQLite, función RPC en Postgres |
| Inyección de dependencias manual | Los services reciben el repositorio por constructor | Testeable con repos en memoria y permite TDD estricto |
| Borrado lógico | `productos.activo` | Preserva historial de órdenes |
| Application factory + dependencias | `create_app()` de FastAPI y `Depends(...)` | Facilita tests (`TestClient`) y entrada serverless |
| Validación en el borde HTTP | Modelos Pydantic (cantidad `int` con `Field(gt=0)`, strings `min_length=1` con strip, fechas `datetime.date` desde YYYY-MM-DD) | Guard de la capa HTTP; los services mantienen su validación (autoridad de dominio, independiente de HTTP) |

## Estructura de directorios

```
Inventario-B/
├── api/
│   └── index.py              # entrada Vercel (expone `app` FastAPI, ASGI)  [Fase 3]
├── inventario/
│   ├── domain/               # entidades, errores, validadores puros
│   ├── services/             # auth, stock, productos, ordenes
│   ├── repositories/
│   │   ├── base.py           # interfaces abstractas
│   │   ├── sqlite_repo.py    # Fase 1
│   │   └── supabase_repo.py  # Fase 2 (RPC para operaciones atómicas)
│   ├── security.py           # hash PBKDF2, verificación
│   └── api/                  # app FastAPI (adaptador HTTP): routers, modelos Pydantic, auth de sesión, lifespan (init DB + seed) — desde Fase 1
├── .venv/                    # entorno virtual local (gitignored)
├── requirements.txt          # runtime: fastapi, uvicorn, python-dotenv, itsdangerous (+ supabase en Paso 5)
├── requirements-dev.txt      # test: httpx
├── static/                   # login.html, index.html (inventario), ordenes.html, js/, css/ (tokens.css, ui.css)
├── db/
│   └── schema.sql            # tablas + funciones RPC (Fase 2)
├── tests/
├── vercel.json
├── .env.example
├── .gitignore
├── knowledge-base/
├── openspec/
└── README.md                 # guía de despliegue (Paso 6)
```

La estructura es orientativa; el change de cada paso fija los nombres exactos. Se debe respetar que `domain/`, `services/` y `repositories/` (contratos) no importen `fastapi`; `domain/` y `services/` tampoco `sqlite3` ni `supabase`. FastAPI vive solo en `inventario/api/` (y `api/index.py` en Fase 3). `static/` se agrega en el Paso 5.

## Seguridad

- **Autenticación**: usuario + contraseña; PBKDF2-HMAC-SHA256 con salt aleatorio por usuario (cantidad de iteraciones alta y configurable); comparación con `hmac.compare_digest`.
- **Sesión web**: cookie de sesión firmada con Starlette `SessionMiddleware` (requiere `itsdangerous`; `SECRET_KEY`), HttpOnly, SameSite=Lax, `https_only` en producción. Se eligió sobre JWT por simplicidad (DD-04).
- **Autorización**: un único nivel (usuario autenticado); dependencia `Depends(get_current_user)` (401 sin sesión) en todas las rutas `/api` salvo login.
- **Validación de input**: doble capa (frontend UX + backend autoridad: Pydantic en HTTP + services); consultas parametrizadas; escape de salida en el DOM (evitar `innerHTML` con datos de usuario).
- **Secrets management**: `os.environ`; `.env` local con `python-dotenv` (gitignored); variables de entorno de Vercel en producción. `SUPABASE_KEY` es la clave `service_role`, usada solo en el backend; sin RLS porque el navegador nunca accede a Supabase (DD-05).
- **Atomicidad**: funciones PL/pgSQL (`crear_orden`, `borrar_orden`, `ingresar_stock`, `egresar_stock`) llamadas vía RPC, definidas en `schema.sql`.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | URL del proyecto Supabase | `https://xxxx.supabase.co` | N (no commitear igualmente) |
| `SUPABASE_KEY` | Clave `service_role` de Supabase (solo backend) | `eyJ...` | Y |
| `SECRET_KEY` | Clave de firma de la cookie de sesión (`SessionMiddleware`) | cadena aleatoria larga | Y |
| `SESSION_HTTPS_ONLY` | Si la cookie de sesión exige HTTPS (`true` en producción/Vercel, `false` en local) | `false` | N |
| `ADMIN_DEFAULT_PASSWORD` | Contraseña inicial del `admin` para el seed | definir localmente | Y |
| `INVENTARIO_DB_PATH` | Ruta del archivo SQLite (opcional, pasos 1-4b) | `./inventario.db` | N |

`.env.example` contiene solo los nombres, nunca valores reales.
