# Modelo de Datos

## Dominios

- **Acceso**: `usuarios`.
- **Catálogo/Stock**: `productos` (stock actual por producto) y `movimientos` (bitácora de ingresos/egresos manuales).
- **Órdenes de trabajo**: `ordenes` y `orden_items` (detalle de componentes).

## ERD

```
usuarios 1 ────< ordenes 1 ────< orden_items >──── 1 productos
    │                                                    │
    └────────────────< movimientos >─────────────────────┘
```

- Un usuario crea muchas órdenes y muchos movimientos.
- Una orden tiene 1..N ítems; cada ítem referencia un producto.
- Un producto aparece en muchos ítems y muchos movimientos.

## Entidades

### usuarios
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK autoincremental (SQLite INTEGER / PG BIGSERIAL o identity) | |
| username | TEXT, UNIQUE, NOT NULL | |
| password_hash | TEXT, NOT NULL | PBKDF2-HMAC-SHA256 (hex) |
| salt | TEXT, NOT NULL | aleatorio por usuario |
| created_at | TIMESTAMP, NOT NULL | default now |

### productos
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| codigo | TEXT, UNIQUE, NOT NULL | código interno |
| nombre | TEXT, NOT NULL | |
| stock | INTEGER, NOT NULL, CHECK (stock >= 0) | nunca negativo |
| activo | BOOLEAN, NOT NULL, default true | borrado lógico (SQLite: INTEGER 0/1) |

Índice: UNIQUE(codigo). Índice parcial opcional sobre `activo`.

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
| tipo | TEXT, NOT NULL, CHECK IN ('ingreso','egreso') | |
| cantidad | INTEGER, NOT NULL, CHECK (cantidad > 0) | |
| usuario_id | FK → usuarios.id, NOT NULL | |

Índice: `producto_id`, `fecha`. No incluye motivo (RN-ST-05). Los descuentos por órdenes NO se registran aquí: viven en `orden_items` (RN-ST-06).

## Notas de paridad SQLite ↔ PostgreSQL

- Booleano: SQLite usa 0/1; PostgreSQL `boolean`. Los repositorios normalizan a `bool` de Python.
- Fechas: se manejan como strings `YYYY-MM-DD` en la capa de servicios; cada repositorio convierte.
- Operaciones multi-tabla atómicas: SQLite con transacción; Supabase con funciones PL/pgSQL vía RPC definidas en `schema.sql` (ver 08 y R-01).

## Seed data inicial

- Un usuario `admin` con contraseña hasheada (PBKDF2 + salt). La contraseña inicial NO se hardcodea: proviene de `ADMIN_DEFAULT_PASSWORD` (ver DD-07).
- En Supabase, PostgreSQL no calcula PBKDF2-SHA256 de forma nativa, por lo que el hash del admin se genera con un script Python de inicialización (misma función de hashing que usa la app) y no con SQL puro en `schema.sql`.
- Sin productos ni órdenes de ejemplo.
