# Inventario-B — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

Inventario-B controla stock de piezas y órdenes de trabajo de un taller o pyme chica. Arranca como backend API local FastAPI + SQLite, verificado en la Swagger UI (`/docs`) y con tests (Fase 1); evoluciona migrando a Supabase PostgreSQL y agregando el frontend HTML estático/Tailwind (Fase 2) y se despliega en Vercel (Fase 3). No hay CLI (decisión del usuario, 2026-11-19). Se construye paso a paso con OpenSpec y TDD estricto.

---

## Stack Tecnológico

| Capa | Tecnologías | Versión mínima |
|------|-------------|----------------|
| Fase 1 — backend API local | FastAPI + `uvicorn`, Pydantic, `python-dotenv`, `itsdangerous` (sesión); lógica con `sqlite3`, `hashlib`, `hmac`, `datetime`, `os`; `.venv` local | Python 3.10+; versiones en `requirements.txt` |
| Fase 1 — persistencia | SQLite (archivo local, ruta opcional `INVENTARIO_DB_PATH`) | sqlite 3.x (incluido en Python) |
| Fase 1 — verificación | Swagger UI en `/docs` + `unittest` con `TestClient` de FastAPI | `httpx` en `requirements-dev.txt` (solo test) |
| Fase 2 — backend | Mismo FastAPI; se agrega el cliente `supabase` (Python, síncrono) y repositorios Supabase que reemplazan a SQLite sin tocar los services | Versiones a fijar en el Paso 6 |
| Fase 2 — base de datos | Supabase (PostgreSQL gestionado) + funciones PL/pgSQL vía RPC | PostgreSQL 15+ |
| Fase 2 — frontend | HTML5 + Tailwind CSS vía CDN + JavaScript vanilla | Navegadores modernos |
| Fase 3 — despliegue | Vercel (Serverless Functions, runtime Python), GitHub como origen | — |

Las versiones exactas se fijan en `requirements.txt` durante el Paso 5/6.

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

**Diseño visual**: política `system-and-mockups`, design system Revision 1 aprobado el 2026-11-19 (`design-system/README.md`). Sin logo ni marca por decisión del usuario (cabecera con el texto "Inventario"). Layout acordado: inventario primero; ingreso, egreso, nueva orden y borrados como modales; órdenes en pantalla aparte (`/ordenes`).

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [README.md](knowledge-base/README.md) | Índice y resumen ejecutivo |
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack por fase, arquitectura general, API |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, permisos, rutas públicas |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Tablas, constraints, paridad SQLite/Postgres, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario (US-001..US-011) |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E y casos de error |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, seguridad, env vars |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-XX y supuestos SU-XX |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Inconsistencias y preguntas abiertas |
| [11_plan_de_pasos_y_despliegue.md](knowledge-base/11_plan_de_pasos_y_despliegue.md) | Fases, pasos 1-6 y ciclo OpenSpec con pausa |

> Estado de `10_preguntas_abiertas.md`: no quedan preguntas de prioridad **Alta** abiertas (quedan PA-03/PA-04 Media y PA-06/07/08 Baja). Revisar la columna "Bloquea" antes de cada change.

---

## Skills Disponibles

<!-- Fuente de verdad: .atl/skill-registry.md -->

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend dominio / API local** | Services, repositorios, adaptador FastAPI, tests `unittest` | `python-testing-patterns`, `test-driven-development`, `systematic-debugging` |
| **Datos / Supabase** | Schema Postgres, RLS, funciones RPC | `supabase`, `supabase-postgres-best-practices`, `postgres-patterns`, `postgresql-table-design` |
| **Backend web (API)** | FastAPI, modelos Pydantic, auth por sesión, tests con `TestClient` | `fastapi`, `pydantic`, `python-testing-patterns`, `test-driven-development` |
| **Frontend web** | HTML estático / Tailwind CDN / JS vanilla, mockups | `design-system`, `frontend-design`, `emil-design-eng`, `impeccable`, `ui-ux-pro-max`, `web-design-guidelines` |
| **QA / verify** | Pruebas de la web y capturas | `webapp-testing`, `playwright-cli` |
| **Orquestación** | Flujo OpenSpec | `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-sync-specs`, `openspec-update-change` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo).

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 7 changes (C-01..C-07), estrictamente secuenciales.
- **Camino crítico** (7): `C-01 paso-1-base-cli (nombre histórico; sin CLI) → C-02 paso-2-movimientos-stock → C-03 paso-3-crear-ordenes → C-04 paso-4-listado-ordenes → C-05 paso-4b-borrado-ordenes-productos → C-06 paso-5-supabase-api-web → C-07 paso-6-despliegue-vercel`.
- **Primer change**: `C-01` (`paso-1-base-cli`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto.

1. **Dependencias declaradas y lógica desacoplada**: NUNCA instalar paquetes fuera de `requirements.txt`/`requirements-dev.txt` ni importar FastAPI dentro de `domain/`, `services/` o `repositories/` → FastAPI es solo el adaptador HTTP; trabajar en `.venv`.
2. **Sin secretos en código**: NUNCA poner URLs, claves API ni contraseñas en el código o el repo → siempre `os.environ`; `.env` nunca se commitea, solo `.env.example` con los nombres de variables.
3. **Stock atómico + doble validación**: NUNCA operar sobre varios productos sin atomicidad (crear orden, borrar orden con reintegro) → transacción en SQLite / función RPC en Postgres, todo o nada. Cantidades enteras > 0, fechas `YYYY-MM-DD` y campos obligatorios se validan en frontend Y backend.
4. **Tests con `unittest`**: NUNCA usar pytest ni mockear la base de datos → tests con `unittest` (stdlib; endpoints con `TestClient`) y los tests de repositorio usan SQLite real en memoria (`:memory:`).
5. **Un paso a la vez**: NUNCA empezar el siguiente change de `CHANGES.md` sin que el usuario diga "Continuar" → cada paso cierra su ciclo propose → apply → verify → archive.
6. **Commits solo a pedido**: NUNCA hacer commit ni push sin pedido explícito del usuario → mensajes con Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar el orden secuencial
3. /opsx:propose <change>                        → proposal + design + specs + tasks
4. /opsx:apply <change>                          → implementar tasks (Strict TDD, cargando skills)
5. verify                                        → validar contra specs/design/tasks y probar los endpoints en /docs
6. /opsx:archive <change> + marcar [x]           → cerrar el change; esperar "Continuar"
```

Un change a la vez. Para `paso-5-supabase-api-web` (UI nueva) aplica el mockup gate: mockups aprobados por el usuario ANTES de `/opsx:apply`, respetando el design system Revision 1.

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
