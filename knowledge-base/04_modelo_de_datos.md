# Modelo de Datos

## Dominios

- **Acceso**: `usuarios`.
- **Catálogo/Stock**: `categorias` (catálogo de categorías, C-06e), `productos` (stock actual por producto) y `movimientos` (bitácora de ingresos/egresos manuales).
- **Órdenes de trabajo**: `ordenes` y `orden_items` (detalle de componentes).

## ERD

```
usuarios 1 ────< ordenes 1 ────< orden_items >──── 1 productos >──── 0..1 categorias
    │                                                    │
    └────────────────< movimientos >─────────────────────┘
```

- Un usuario crea muchas órdenes y muchos movimientos.
- Una orden tiene 1..N ítems; cada ítem referencia un producto.
- Un producto aparece en muchos ítems y muchos movimientos.
- Un producto tiene 0 o 1 categoría (`categoria_id` nulo = "Sin categoría"); una categoría agrupa muchos productos.

## Entidades

### usuarios
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK autoincremental (SQLite INTEGER / PG BIGSERIAL o identity) | |
| username | TEXT, UNIQUE, NOT NULL | |
| password_hash | TEXT, NOT NULL | PBKDF2-HMAC-SHA256 (hex) |
| salt | TEXT, NOT NULL | aleatorio por usuario |
| created_at | TIMESTAMP, NOT NULL | default now |

### categorias (C-06e)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| clave | TEXT, UNIQUE, NOT NULL | identificador estable que viaja por la API: minúsculas, `a-z`, `0-9` y guiones (sin guion al inicio/fin), 1 a 30; inmutable |
| nombre | TEXT, NOT NULL, UNIQUE (NOCASE) | nombre para mostrar, 1 a 40; único sin distinguir mayúsculas (el service compara con `casefold()` para cubrir tildes/Ñ) |

Sin borrado de categorías. Seed: `motor` ("Motor"), `aceite` ("Aceite"), `filtro` ("Filtro") solo cuando el catálogo está vacío (no pisa renombres).

### productos
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| codigo | TEXT, UNIQUE, NOT NULL | código interno |
| nombre | TEXT, NOT NULL | |
| stock | INTEGER, NOT NULL, CHECK (stock >= 0) | nunca negativo; el alta explícita admite stock inicial 0 (RN-PR-08) |
| activo | BOOLEAN, NOT NULL, default true | borrado lógico (SQLite: INTEGER 0/1) |
| categoria_id | FK → categorias(id), NULL | categoría opcional (C-06e); NULL = "Sin categoría" |

Índice: UNIQUE(codigo). Índice parcial opcional sobre `activo`. Sin índice sobre `categoria_id` (el filtro es en el navegador).

**Migración (SQLite, C-06e)**: idempotente al arrancar; si `productos` no tiene `categoria_id` se agrega con `ALTER TABLE productos ADD COLUMN categoria_id INTEGER REFERENCES categorias(id)` (sin reconstruir la tabla, por ser padre de `orden_items` y `movimientos`), dentro de una transacción que verifica conteos y `foreign_key_check` y hace rollback ante cualquier falla. Los productos existentes quedan sin categoría. Se ejecuta después de la migración de `movimientos` y antes de la normalización de fechas.

### ordenes
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | El borrado es por `numero`, no por `id`: el reuso de ids en SQLite no tiene impacto funcional. Postgres (identity, C-07) tampoco reutiliza ids. |
| numero | TEXT, UNIQUE, NOT NULL | alfanumérico; se guarda sin espacios sobrantes y en mayúsculas (`"  ot-0003 "` → `OT-0003`), de 1 a 30 caracteres; unicidad sobre el valor normalizado (PA-06, resuelta en C-03) |
| fecha | DATE (`YYYY-MM-DD`), NOT NULL | ingresada a mano por el usuario |
| usuario_id | FK → usuarios.id, NOT NULL | quién la cargó |
| created_at | TIMESTAMP, NOT NULL | default now; la app lo escribe como ISO 8601 con offset -03:00 (mismo formato que `movimientos`) |

Índice: `fecha` (filtro por rango).

### orden_items
| Campo | Tipo | Notas |
|-------|------|-------|
| orden_id | FK → ordenes.id, NOT NULL, ON DELETE CASCADE | |
| producto_id | FK → productos.id, NOT NULL | sin cascade: el producto nunca se borra físicamente |
| cantidad | INTEGER, NOT NULL, CHECK (cantidad > 0) | |

PK compuesta (orden_id, producto_id): un producto aparece una sola vez por orden (SU-05).

### movimientos
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| fecha | TIMESTAMP, NOT NULL | momento del movimiento |
| producto_id | FK → productos.id, NOT NULL | |
| tipo | TEXT, NOT NULL, CHECK IN ('ingreso','egreso','ajuste') | `ajuste` lo genera "Fijar en" (RN-ST-08) y la reactivación por alta (RN-PR-10) |
| cantidad | INTEGER, NOT NULL, CHECK (cantidad > 0) | en un `ajuste` es la diferencia absoluta entre stock anterior y nuevo |
| stock_anterior | INTEGER, NULL | solo en `ajuste`; NULL en `ingreso`/`egreso` |
| stock_nuevo | INTEGER, NULL | solo en `ajuste`; NULL en `ingreso`/`egreso` |
| usuario_id | FK → usuarios.id, NOT NULL | |

CHECK de coherencia: `((tipo = 'ajuste') = (stock_anterior IS NOT NULL)) AND ((tipo = 'ajuste') = (stock_nuevo IS NOT NULL))` (ambos campos presentes si y solo si el tipo es `ajuste`).

**Migración (C-06b, SQLite)**: al arrancar, si `movimientos` no admite `ajuste`, la inicialización reconstruye la tabla en una sola transacción (copia las filas conservando id, fecha, producto, tipo, cantidad y usuario; stock anterior/nuevo quedan NULL). Es idempotente y, si falla, la base queda como estaba. En Supabase (C-07) el `schema.sql` debe replicar el CHECK de `tipo` y el de coherencia.

Índice: `producto_id`, `fecha`. No incluye motivo (RN-ST-05). Los descuentos por órdenes NO se registran aquí: viven en `orden_items` (RN-ST-06).

## Notas de paridad SQLite ↔ PostgreSQL

- Booleano: SQLite usa 0/1; PostgreSQL `boolean`. Los repositorios normalizan a `bool` de Python.
- Fechas: se manejan como strings `YYYY-MM-DD` en la capa de servicios; cada repositorio convierte.
- Categorías (C-06e): en Postgres `categorias.id` identity, `clave` con CHECK `^[a-z0-9]+(-[a-z0-9]+)*$` y largo <= 30, índice único sobre `lower(nombre)` (equivale al NOCASE) y `productos.categoria_id bigint null references categorias(id)`; RLS como `productos`. Crear y renombrar categorías son operaciones de una sola fila (sin RPC; violación `23505` → 409). Las RPC de alta y modificación de productos reciben `p_categoria` (clave) y la de reporte devuelve `categoria`.
- Operaciones multi-tabla atómicas: SQLite con transacción; Supabase con funciones PL/pgSQL vía RPC definidas en `schema.sql` (ver 08 y R-01).

## Seed data inicial

- Un usuario `admin` con contraseña hasheada (PBKDF2 + salt). La contraseña inicial NO se hardcodea: proviene de `ADMIN_DEFAULT_PASSWORD` (ver DD-07).
- En Supabase, PostgreSQL no calcula PBKDF2-SHA256 de forma nativa, por lo que el hash del admin se genera con un script Python de inicialización (misma función de hashing que usa la app) y no con SQL puro en `schema.sql`.
- Categorías de ejemplo `motor`, `aceite`, `filtro` (solo con catálogo vacío).
- Sin productos ni órdenes de ejemplo.
