# Inventario-B — Base de Conocimiento

Base de conocimiento generada a partir del discovery del proyecto (`discovery/discovery.md`) y las decisiones finales acordadas con el usuario.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos, alcance v1, fuera de alcance, métricas |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack por fase, arquitectura general, integraciones, API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, permisos (sin roles en v1), rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Tablas, ERD, constraints, paridad SQLite/Postgres, seed |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas RN-AU, RN-PR, RN-ST, RN-OR, RN-VA, RN-SE |
| [06_funcionalidades.md](06_funcionalidades.md) | Épicas y user stories US-001..US-011 con criterios |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo y casos de error |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, estructura de directorios, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones DD-01..DD-10 y supuestos SU-01..SU-07 |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias y preguntas abiertas priorizadas |
| [11_plan_de_pasos_y_despliegue.md](11_plan_de_pasos_y_despliegue.md) | Fases, pasos 1-6 y ciclo OpenSpec con pausa |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md), [11](11_plan_de_pasos_y_despliegue.md)
6. Antes de codificar → [09](09_decisiones_y_supuestos.md), [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

Inventario-B controla stock de piezas y órdenes de trabajo de un taller o pyme chica. Arranca como CLI en Python stdlib con SQLite (Fase 1), evoluciona a una app web FastAPI + Supabase PostgreSQL con frontend HTML estático/Tailwind (Fase 2) y se despliega en Vercel (Fase 3). La lógica de negocio vive en services desacoplados con repositorios intercambiables; las operaciones compuestas son atómicas y no hay secretos en el repositorio. Se construye paso a paso con OpenSpec y TDD estricto.
