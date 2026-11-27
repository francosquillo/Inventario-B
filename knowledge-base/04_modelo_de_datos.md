# Modelo de Datos

## Dominios

- **Acceso**: `usuarios`.
- **Catálogo/Stock**: `categorias` (catálogo de categorías, C-06e), `productos` (stock actual por producto) y `movimientos` (bitácora de ingresos/egresos manuales).
- **Órdenes de trabajo**: `ordenes`, `orden_items` (detalle de componentes), `procesos` (catálogo de procesos, C-06f) y `orden_procesos` (procesos registrados en cada orden).
- **Servicios generales (C-06g)**: `servicios_generales` y `servicio_chequeos` (catálogo con sus chequeos) y `orden_servicio` y `orden_servicio_chequeos` (snapshot del servicio de cada orden).

## ERD

```
usuarios 1 ────< ordenes 1 ────< orden_items >──── 1 productos >──── 0..1 categorias
    │                                                    │
    │                 └────< orden_procesos   (sin FK al catálogo `procesos`)
    └────────────────< movimientos >─────────────────────┘
```

- Un usuario crea muchas órdenes y muchos movimientos.
- Una orden tiene 1..N ítems; cada ítem referencia un producto.
- Un producto aparece en muchos ítems y muchos movimientos.
- Una orden tiene 0..N procesos registrados (`orden_procesos`); cada uno guarda su nombre como snapshot y no referencia al catálogo `procesos`.
- Un producto tiene 0 o 1 categoría (`categoria_id` nulo = "Sin categoría"); una categoría agrupa muchos productos.
- Una orden tiene 0 o 1 servicio general (`orden_servicio`, PK `orden_id`); el servicio guarda su nombre y sus chequeos (`orden_servicio_chequeos`) como snapshot, sin FK al catálogo `servicios_generales`. Un servicio del catálogo tiene 1..N chequeos (`servicio_chequeos`).

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

Borrado desde C-06f (solo API): se rechaza con 409 si algún producto, activo o dado de baja, la usa. Seed: `motor` ("Motor"), `aceite` ("Aceite"), `filtro` ("Filtro") solo en el momento en que la tabla `categorias` se crea (C-06f reemplaza el "sembrar si está vacío" de C-06e): no pisa renombres ni vuelve a sembrar un catálogo vaciado a propósito.

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

### procesos (C-06f)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| clave | TEXT, UNIQUE, NOT NULL | mismo formato que `categorias.clave` (hasta 30); inmutable |
| nombre | TEXT, NOT NULL, UNIQUE (NOCASE) | 1 a 60; único sin distinguir mayúsculas (el service compara con `casefold()`) |

Catálogo administrado solo por la API (alta, renombrar, borrar). Seed: `cambio-motor` ("Cambio motor"), `cambio-filtro` ("Cambio filtro"), `limpieza` ("Limpieza"), solo en el momento en que la tabla se crea.

### orden_procesos (C-06f)
| Campo | Tipo | Notas |
|-------|------|-------|
| orden_id | FK → ordenes.id, NOT NULL, ON DELETE CASCADE | borrar la orden borra sus procesos |
| nombre | TEXT, NOT NULL | snapshot del nombre al crear la orden (renombrar o borrar el proceso del catálogo no lo altera) |
| personalizado | BOOLEAN, NOT NULL | true = texto libre de esa orden; false = del catálogo (SQLite: INTEGER 0/1) |
| position | INTEGER, NOT NULL | orden de carga: primero los del catálogo, luego los personalizados |

Sin FK a `procesos`: por eso se puede borrar un proceso usado. La unicidad de nombre por orden, sin distinguir mayúsculas, la valida el service.

### servicios_generales (C-06g)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| clave | TEXT, UNIQUE, NOT NULL | mismo formato que `procesos.clave` (hasta 30, CHECK `_CLAVE_CHECK`); inmutable |
| nombre | TEXT, NOT NULL, UNIQUE (NOCASE) | 1 a 60; único sin distinguir mayúsculas |

Catálogo administrado desde `/ordenes` y por API. Seed: `servicio-20-hs` ("Servicio 20 hs") solo al crear la tabla.

### servicio_chequeos (C-06g)
| Campo | Tipo | Notas |
|-------|------|-------|
| servicio_id | FK → servicios_generales.id, NOT NULL, ON DELETE CASCADE | |
| posicion | INTEGER, NOT NULL, >= 1 | orden de carga; PK (servicio_id, posicion) |
| nombre | TEXT, NOT NULL, 1 a 60 | UNIQUE (servicio_id, nombre NOCASE); de 1 a 30 chequeos por servicio |

Seed del servicio de ejemplo: "Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico".

### orden_servicio (C-06g)
| Campo | Tipo | Notas |
|-------|------|-------|
| orden_id | PK y FK → ordenes.id, NOT NULL, ON DELETE CASCADE | una sola fila por orden: cero o un servicio general |
| nombre | TEXT, NOT NULL, 1 a 60 | snapshot del nombre al crear la orden |

### orden_servicio_chequeos (C-06g)
| Campo | Tipo | Notas |
|-------|------|-------|
| orden_id | FK → orden_servicio.orden_id, NOT NULL, ON DELETE CASCADE | no puede haber chequeos de una orden sin servicio |
| posicion | INTEGER, NOT NULL, >= 1 | PK (orden_id, posicion) |
| nombre | TEXT, NOT NULL, 1 a 60 | snapshot; UNIQUE (orden_id, nombre NOCASE) |

Sin FK al catálogo: renombrar, cambiar chequeos o borrar el servicio no altera órdenes pasadas (todos los chequeos se copian al crear la orden).

**Migración (C-06g, SQLite)**: aditiva y sin `ALTER`. Al arrancar, si `servicios_generales` no existe, se crean las cuatro tablas y se siembra el ejemplo en una sola transacción, verificando que los conteos de órdenes, ítems, productos, categorías, movimientos y procesos no cambien; ante error no queda ninguna tabla nueva. Las órdenes existentes quedan sin servicio. Si la tabla ya existe, no resiembra.

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
- Procesos (C-06f): en Postgres `procesos` (identity, `clave` con el mismo CHECK que `categorias`, índice único sobre `lower(nombre)`) y `orden_procesos (orden_id bigint references ordenes(id) on delete cascade, nombre text, personalizado boolean, position int)`; RLS como las demás. La RPC `crear_orden` recibe `p_procesos` (claves) y `p_procesos_personalizados` y registra los procesos en la misma transacción. Alta, renombrar y borrar de procesos y el borrado de categorías son operaciones directas (sin RPC; `23505` → 409; `23503` en categorías en uso → 409). El seed de `procesos` y `categorias` ocurre solo al crear cada tabla en `schema.sql`.
- Servicios generales (C-06g): en Postgres `servicios_generales` (identity, `clave` con el mismo CHECK, índice único sobre `lower(nombre)`), `servicio_chequeos` (`servicio_id` on delete cascade, `posicion`, PK compuesta, índice único `(servicio_id, lower(nombre))`), `orden_servicio (orden_id bigint primary key references ordenes(id) on delete cascade, nombre text)` y `orden_servicio_chequeos` (mismo patrón que `orden_procesos`). La RPC `crear_orden` recibe `p_servicio` (`{nombre, chequeos}` o `null`, ya validado) en la misma transacción. Alta y modificación de servicio (catálogo y chequeos) son multi-tabla y van por RPC transaccional; borrar es una fila (cascade).
- Operaciones multi-tabla atómicas: SQLite con transacción; Supabase con funciones PL/pgSQL vía RPC definidas en `schema.sql` (ver 08 y R-01).

## Seed data inicial

- Un usuario `admin` con contraseña hasheada (PBKDF2 + salt). La contraseña inicial NO se hardcodea: proviene de `ADMIN_DEFAULT_PASSWORD` (ver DD-07).
- En Supabase, PostgreSQL no calcula PBKDF2-SHA256 de forma nativa, por lo que el hash del admin se genera con un script Python de inicialización (misma función de hashing que usa la app) y no con SQL puro en `schema.sql`.
- Categorías de ejemplo `motor`, `aceite`, `filtro` y procesos de ejemplo `cambio-motor`, `cambio-filtro`, `limpieza` (cada catálogo se siembra solo al crear su tabla).
- Servicio general de ejemplo `servicio-20-hs` ("Servicio 20 hs") con tres chequeos; se siembra solo al crear sus tablas.
- Sin productos ni órdenes de ejemplo.
