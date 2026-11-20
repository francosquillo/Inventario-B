# Visión y Objetivos

## Propósito del sistema

Inventario-B es un sistema de control de inventario y órdenes de trabajo para un taller o pyme chica. Centraliza el stock de piezas, las órdenes de trabajo que lo consumen y el control de acceso en una aplicación que nace como backend API local (FastAPI + SQLite, verificado en `/docs`, sin CLI) y evoluciona a una app web en la nube.

Hoy el problema se resuelve (supuesto, no verificado: SU-01) con planillas o papel, sin certeza de qué piezas hay ni qué consumió cada orden. El sistema reemplaza ese circuito manual con una única fuente de verdad, con reglas que impiden estados inconsistentes (stock negativo, órdenes sin stock suficiente).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|--------------------|-----------------------|
| Usuario (operario/admin) | Saber en todo momento qué piezas y cantidades hay en stock | Registrar ingresos y egresos manuales; crear órdenes que descuenten stock automáticamente; consultar historial de órdenes por fecha; corregir errores de carga (borrados) |
| Responsable del taller (admin por defecto) | Confiar en que el stock refleja la realidad | Control de acceso con usuario y contraseña; trazabilidad de movimientos manuales |

## Alcance v1

- Login con usuario y contraseña (contraseñas hasheadas con PBKDF2-HMAC-SHA256 + salt).
- Visualización del inventario general (solo productos activos).
- Ingreso de stock por código interno (suma, alta con nombre o reactivación de producto dado de baja).
- Egreso manual de stock sin orden, con validación contra stock actual.
- Creación de órdenes de trabajo (número único, fecha ingresada a mano, componentes) con validación y descuento atómico de stock.
- Listado de órdenes, todas o por rango de fechas `YYYY-MM-DD` inclusivo.
- Borrado de órdenes (con opción de reintegrar stock) y borrado lógico de productos, siempre con confirmación.
- Registro en `movimientos` de todo ingreso y egreso manual (sin motivo).
- Fase 1: backend API local (FastAPI + SQLite), verificado en la Swagger UI `/docs` y con tests. Fase 2: frontend web local (HTML estático/Tailwind CDN/JS sobre SQLite). Fase 3: migración a Supabase (repositorios Supabase). Fase 4: despliegue en Vercel.
- Cambio de alcance (2026-11-19, decisión del usuario): se elimina la CLI; no hay menú de consola. Ver DD-12.

## Fuera de alcance

- Roles diferenciados (todos los usuarios tienen los mismos permisos).
- Edición de órdenes y de productos ya creados.
- Alertas de stock bajo.
- Motivo en los movimientos de stock.
- Vista/listado del historial de `movimientos` en la UI (se registra, pero no se consulta en v1; ver pregunta abierta PA-04).
- Alta/gestión de usuarios desde la UI (solo `admin` inicial).
- Acceso directo del navegador a Supabase.

## Métricas de éxito

- El stock en el sistema coincide con el conteo físico tras una semana de uso.
- Ninguna orden se crea con stock insuficiente; el stock nunca queda negativo.
- Crear una orden de varios componentes toma una sola operación y deja el inventario consistente (todo o nada).
- Cero secretos (claves, URLs, contraseñas) en el repositorio.
- Cada paso del plan se entrega y archiva con su ciclo OpenSpec completo.
