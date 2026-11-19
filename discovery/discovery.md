# Discovery — Inventario-B

**Fecha**: 2026-11-19
**Fuentes investigadas**: ninguna URL de competidores. Fuente principal: el prompt/consigna del proyecto provisto por el usuario, más una ronda de Q&A.

## 1. Problema que resuelve

Un taller o pyme chica lleva el control de stock de piezas y de órdenes de trabajo
de forma manual (planillas/papel), sin saber con certeza qué piezas tiene ni qué
consumió cada orden. Inventario-B centraliza inventario, órdenes de trabajo y
control de acceso en una app web en la nube.

## 2. Usuarios / roles

- **Usuario (operario/admin)**: pocos usuarios, todos con los mismos permisos. Se
  loguea, consulta inventario, ingresa stock, crea, lista y borra órdenes.
- Existe un usuario `admin` creado por defecto al inicializar la base.
- Sin roles diferenciados en la v1.

## 3. Casos de uso

1. Como usuario, quiero loguearme con usuario y contraseña para acceder al sistema.
2. Como usuario, quiero ver el inventario general para saber qué piezas y cantidades tengo.
3. Como usuario, quiero ingresar stock por código interno (suma si existe; si es
   nuevo pide nombre y lo registra) para mantener el inventario al día.
4. Como usuario, quiero descontar unidades de un producto sin crear una orden
   (rotura, pérdida, consumo interno) para que el stock refleje la realidad.
5. Como usuario, quiero crear una orden de trabajo con número y componentes, para
   que el stock se descuente automáticamente.
6. Como usuario, quiero listar órdenes (todas o por rango de fechas `YYYY-MM-DD`)
   para consultar el historial.
7. Como usuario, quiero borrar órdenes y productos para corregir errores de carga.

## 4. Competidores / soluciones existentes

No se analizaron competidores. Hoy el problema se resuelve con planillas o papel
(supuesto, no verificado).

## 5. Funcionalidades necesarias

Plan por pasos (un paso a la vez, ciclo OpenSpec propose → apply → verify → archive, con pausa entre pasos):

**Fase 1 — Lógica de negocio y CLI** (solo stdlib; patrón Repositorio/DAO, lógica desacoplada de la consola)
- **Paso 1**: SQLite local, tablas `usuarios`, `productos`, `ordenes`, `movimientos`; login por terminal con `admin` por defecto (contraseña hasheada); menú principal; visualización de inventario.
- **Paso 2 — Movimientos de stock**: ingreso por código interno (suma o alta con nombre) y egreso manual (descuenta unidades sin orden).
- **Paso 3**: creación de órdenes (número + componentes) validando y descontando stock.
- **Paso 4**: listado de órdenes, todas o por rango de fechas.
- **Paso 4b**: borrado de órdenes y productos (con confirmación).

**Fase 2 — Supabase + web**
- **Paso 5**: `schema.sql` para PostgreSQL/Supabase con `admin` inicial; capa de datos adaptada al cliente `supabase` vía `SUPABASE_URL`/`SUPABASE_KEY`; API en **FastAPI** (ASGI) preparada para serverless con validación Pydantic; frontend HTML estático + Tailwind (CDN) + JS que consume la API JSON con login (contraseña oculta), dashboard con tabla de inventario y modales para pasos 2, 3, 4 y 4b.

**Fase 3 — Despliegue en Vercel**
- **Paso 6**: estructura `api/index.py`, `static/` (sin `templates/`); `vercel.json`, `requirements.txt`, `.env.example`, `.gitignore`; `README.md` con guía paso a paso (Supabase, schema.sql, GitHub, Vercel, variables de entorno, verificación).

## 6. Funcionalidades opcionales (backlog)

- Roles diferenciados (admin vs operario).
- Edición de órdenes y productos.
- Alertas de stock bajo.
- Motivo en los movimientos de stock.

## 7. Reglas de negocio

- Cantidades: enteros > 0, validadas en frontend y backend.
- Campos obligatorios no pueden estar vacíos.
- Fechas en formato `YYYY-MM-DD`; el filtro por rango es inclusivo en ambos extremos (supuesto).
- Código interno de producto único. Número de orden único.
- **Crear orden**: se valida el stock de todos los componentes; si alguno no alcanza se rechaza la orden completa; si alcanza se descuenta todo de forma atómica.
- **Egreso manual de stock**: cantidad entera > 0 y ≤ stock actual; si excede se rechaza (el stock nunca queda negativo). Si llega a 0 el producto sigue existiendo. El egreso queda registrado en `movimientos`.
- **Registro de movimientos**: todo ingreso y todo egreso manual de stock se registra en la tabla `movimientos` (fecha, producto, tipo `ingreso`/`egreso`, cantidad, usuario) **sin pedir motivo**.
- **Borrar orden**: el sistema pregunta cada vez si reintegrar al inventario el stock descontado; si se reintegra, es atómico.
- **Borrar producto**: borrado lógico (`activo = 0`); desaparece del inventario y de la selección para nuevas órdenes, pero las órdenes históricas lo siguen mostrando.
- Todo borrado requiere confirmación (CLI `s/n`, web modal).
- Contraseñas: SHA-256 con salt aleatorio por usuario vía PBKDF2-HMAC-SHA256 (`hashlib.pbkdf2_hmac`), nunca en texto plano.

## 8. Integraciones

- **Supabase** (PostgreSQL gestionado) vía cliente oficial `supabase` de Python.
- **Vercel** (Serverless Functions, runtime Python).
- **GitHub** como origen del despliegue.

## 9. Restricciones

- Fase 1: exclusivamente biblioteca estándar (`sqlite3`, `hashlib`, `datetime`, `os`).
- Fases 2-3: `fastapi`, `uvicorn`, `supabase`, `python-dotenv`, `itsdangerous` declaradas en `requirements.txt`.
- Prohibido hardcodear URLs, claves API o contraseñas: todo vía `os.environ`.
- Backend desacoplado de la interfaz para reutilizarlo desde CLI y API.
- Metodología OpenSpec estricta, un paso por vez con pausa hasta "Continuar".

## 10. Riesgos

- **Atomicidad en Supabase**: el cliente REST no maneja transacciones multi-tabla; descontar/reintegrar stock en bloque probablemente requiera funciones RPC en Postgres definidas en `schema.sql`.
- **Sesión en serverless**: sin estado entre requests; el login web necesita sesión firmada (cookie) o JWT con `SECRET_KEY` en variable de entorno.
- **Exposición de la clave de Supabase**: `SUPABASE_KEY` debe usarse solo en backend (service role) o anon key con RLS — decidir en el Paso 5.
- **Paridad SQLite ↔ Postgres**: diferencias de tipos/booleanos/fechas pueden romper la reutilización de la capa de datos si la interfaz del repositorio no está bien abstraída.
- **Supuesto sin probar**: que el problema actual se resuelve con planillas/papel.

## 11. Preguntas abiertas

- Ingresar stock con el código de un producto borrado lógicamente: ¿lo reactiva y suma? (supuesto: sí, para mantener el código único). Confirmar en Paso 2 / 4b.
- ¿Las órdenes guardan fecha automática de creación o la ingresa el usuario?
- ¿Qué tipo de clave de Supabase usa el backend (service role vs anon + RLS)?
- Mecanismo de sesión web: cookie firmada (Starlette `SessionMiddleware`) vs JWT.

> Cambio de Flask a FastAPI decidido por el usuario 2026-11-19 (ver DD-03 en la KB). Frontend: HTML estático + API JSON, sin Jinja2/`templates/`.
