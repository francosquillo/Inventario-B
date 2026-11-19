# Plan de Pasos y Despliegue

## Metodología

Cada paso se ejecuta de forma estricta y aislada con el ciclo OpenSpec:

```
propose → apply (TDD estricto) → verify → archive → PAUSA
```

Al terminar un paso se archiva el change y se pausa hasta que el usuario indique "Continuar". No se avanza al paso siguiente sin esa orden. Cada paso depende de los anteriores.

## Fase 1 — Lógica de negocio y CLI (solo stdlib)

| Paso | Contenido | Historias | Reglas clave |
|------|-----------|-----------|--------------|
| 1 | SQLite, tablas, seed de `admin` con hash, login CLI, menú, ver inventario, estructura repositorio/services | US-001, US-002, US-003 | RN-AU, RN-PR-05, RN-SE-01 |
| 2 | Movimientos de stock: ingreso (suma/alta/reactiva) y egreso manual, con registro en `movimientos` | US-004, US-005 | RN-ST, RN-PR-06 |
| 3 | Crear orden: validación de stock de todos los componentes y descuento atómico | US-006 | RN-OR-01..06 |
| 4 | Listar órdenes, todas o por rango de fechas | US-007 | RN-OR-07 |
| 4b | Borrar orden (con reintegro opcional) y borrar producto (lógico) con confirmación | US-008, US-009 | RN-OR-08/09, RN-PR-03, RN-VA-05 |

## Fase 2 — Supabase + web

| Paso | Contenido | Historias |
|------|-----------|-----------|
| 5 | `schema.sql` (tablas + funciones RPC), repositorio Supabase, API FastAPI serverless-ready (Pydantic, `SessionMiddleware`), frontend HTML estático (`static/`) + Tailwind CDN + JS vanilla con `fetch` a `/api/...` (login, inventario, modales de ingreso/egreso, órdenes, listado, borrados), script de seed del admin | US-010 (y reexposición web de US-001 a US-009) |

Nota de diseño visual: el Paso 5 incluye UI nueva, por lo que aplica la política de design-system/mockups del proyecto antes de `apply`.

## Fase 3 — Despliegue en Vercel

| Paso | Contenido | Historias |
|------|-----------|-----------|
| 6 | `api/index.py` (exporta `app` FastAPI), `static/` (definir `StaticFiles` y/o ruteo estático en `vercel.json`), `vercel.json`, `requirements.txt` (`fastapi`, `uvicorn`, `supabase`, `python-dotenv`, `itsdangerous`; versiones fijadas aquí; `httpx` solo test), `.env.example`, `.gitignore`, README con guía (Supabase, schema.sql, GitHub, Vercel, variables de entorno, verificación) | US-011 |

## Dependencias entre pasos

```
1 → 2 → 3 → 4 → 4b → 5 → 6
```

El Paso 5 reutiliza los services de los pasos 1-4b sin modificarlos; solo agrega la implementación Supabase del repositorio y los adaptadores web.

## Notas de TDD

Modo TDD estricto: cada tarea sigue safety net → RED → GREEN → TRIANGULATE → REFACTOR. Los services se testean con repositorios en memoria o SQLite `:memory:`; la implementación Supabase se valida con tests de contrato compartidos con la de SQLite.
