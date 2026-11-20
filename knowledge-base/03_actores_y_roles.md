# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Usuario `admin` | Único usuario del sistema, creado por el seed. Es el único que puede operar (stock, órdenes, consultas). No hay alta de otros usuarios | Fase 1: Swagger UI (`/docs`) y tests. Fase 2-3: navegador (login + dashboard con modales) |
| Sistema de persistencia | SQLite (Fase 1) / Supabase PostgreSQL (Fase 3) | Accedido solo por la capa de repositorios |
| Backend FastAPI | Único cliente de Supabase; guarda la sesión en cookie firmada | El navegador nunca habla con Supabase directamente |

## RBAC — Matriz de permisos

Decisión del usuario (2026-11-20): **solo el `admin` logueado puede hacer cosas; quien no se loguea solo puede loguearse**. El sistema es de un único usuario (`admin`, del seed) y no hay gestión de usuarios ni roles: no se planean roles diferenciados (se descarta el backlog de roles). Como `admin` es el único usuario que existe, "usuario autenticado" equivale a `admin`.

| Rol | Recurso | Permisos |
|-----|---------|----------|
| Usuario autenticado (incluye `admin`) | Productos / inventario | Leer (activos), crear/reactivar vía ingreso, borrado lógico |
| Usuario autenticado | Movimientos | Crear (ingreso/egreso). Lectura vía UI fuera de v1 |
| Usuario autenticado | Órdenes | Crear, leer/listar, borrar (con o sin reintegro). Sin edición |
| Usuario autenticado | Usuarios | Sin gestión en v1 (solo seed de `admin`) |
| Anónimo | Todo | Sin acceso, salvo login |

## Rutas públicas

- `GET /` (página de login) y los estáticos necesarios (`/static/*`).
- `POST /api/login`.
- Todo lo demás requiere sesión válida (RN-AU-03). En Fase 1 (sin CLI), los endpoints protegidos responden 401 sin sesión, también en `/docs`.
