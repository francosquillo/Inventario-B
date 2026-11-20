# Design — paso-4-listado-ordenes (C-04)

## Context

Ver `proposal.md` (Why). Estado actual relevante:

- `ordenes` (`id INTEGER PRIMARY KEY`, `numero TEXT UNIQUE`, `fecha TEXT` con `CHECK` de fecha real `YYYY-MM-DD`, `usuario_id`, `created_at` ISO `-03:00`) y `orden_items` (PK `(orden_id, producto_id)`, `ON DELETE CASCADE`) existen desde C-01; hay índice `idx_ordenes_fecha` y el `UNIQUE` de `numero` da índice implícito. Sin DDL en este change.
- C-03 dejó `SqliteOrdenRepository.crear` + `_leer_orden(orden_id)` (dos `SELECT`: cabecera con `JOIN usuarios` e ítems con `JOIN productos ORDER BY p.codigo`), las entidades `Orden`/`ItemOrden`, el schema `OrdenOut`/`ComponenteOut` y `orden_out()`; el router `/api/ordenes` solo tiene `POST`.
- `OrdenService._normalizar_numero` ya implementa recorte + MAYÚSCULAS + 1..30 con los mensajes del alta.
- `MovimientosService` tiene el patrón de filtros a reflejar: `_parsear_fecha(nombre, valor)` (vacío/`None` → sin límite; mensajes con el nombre del parámetro) y el chequeo `desde > hasta`, sobre `services/fechas.parsear_fecha`.
- `get_current_user` consulta `usuarios` por id con la misma conexión del request y responde 401 "No autenticado." si no existe (W-2 de C-03); el handler de 422 da un único `detail` en español.
- Solo opera `admin`; todo endpoint salvo login exige sesión (03_actores_y_roles).

## Goals / Non-Goals

**Goals:**
- Un único `GET /api/ordenes` que cubre US-007 completa (todas, rango, número) con la forma de orden ya publicada por el alta.
- Sin N+1: una sola consulta SQL por listado, independiente de la cantidad de órdenes.
- Mensajes de error de fechas idénticos a C-02, desde una sola implementación compartida.

**Non-Goals:**
- Paginación, ordenamiento configurable, búsqueda parcial o por producto (no los pide US-007).
- Exponer `created_at` o el estado `activo` del producto (decisiones 7 y 9).
- Endpoint de detalle `GET /api/ordenes/{...}` (decisión 1).
- Cualquier escritura: borrado y reintegro son C-05.

## Decisions

### D1 — Contrato `OrdenRepository.listar`

```python
@abstractmethod
def listar(self, numero: "str | None", desde: "date | None", hasta: "date | None") -> "list[Orden]":
    """Ordenes (mas nueva primero) con sus items ordenados por codigo.
    Recibe filtros ya validados y normalizados; None = sin filtro. Incluye productos inactivos."""
```

Mismo estilo que `MovimientoRepository.listar`. El service valida; el repositorio solo traduce a SQL. En C-06 se mapea a un `select` de PostgREST con relaciones embebidas (`ordenes(id, numero, fecha, usuarios(username), orden_items(cantidad, productos(codigo, nombre)))`) o a una vista de lectura; el service no cambia.

### D2 — Una sola consulta con JOIN (decisión 11)

```sql
SELECT o.id, o.numero, o.fecha, u.username, p.codigo, p.nombre, i.cantidad
FROM ordenes o
JOIN usuarios u ON u.id = o.usuario_id
LEFT JOIN orden_items i ON i.orden_id = o.id
LEFT JOIN productos p ON p.id = i.producto_id
[WHERE o.numero = ? AND o.fecha >= ? AND o.fecha <= ?]   -- solo las condiciones presentes
ORDER BY o.fecha DESC, o.id DESC, p.codigo
```

- Las filas se agrupan en Python por `o.id` (`itertools.groupby`, posible porque el `ORDER BY` deja contiguas las filas de cada orden) y se convierten a `Orden`/`ItemOrden`. Una orden sin ítems (no debería existir: el alta es atómica y exige ≥ 1) aparecería con `items=()` en vez de desaparecer: `LEFT JOIN` para no ocultar historia.
- **Sin filtro por `p.activo`** (RN-PR-04): el `JOIN` a `productos` es solo para código y nombre. Como el borrado de producto de C-05 es lógico (`activo = 0`) y `orden_items.producto_id` no tiene cascade, el nombre siempre está disponible.
- Filtros como parámetros `?` (nunca interpolados). `fecha` se guarda como texto `YYYY-MM-DD` validado por `CHECK`, así que la comparación de texto es comparación de fechas y es inclusiva con `>=`/`<=` (a diferencia de movimientos, que compara instantes y usa `< hasta + 1 día`).
- Usa `idx_ordenes_fecha` para el rango y el índice único de `numero` para la búsqueda.
- **Por qué no dos consultas** (cabeceras + `WHERE orden_id IN (...)`): sin paginación, la lista `IN` crecería con el historial y obliga a partir en lotes por el límite de variables; el JOIN devuelve todo en un viaje con el mismo costo de transferencia (cabecera repetida por línea, despreciable en un taller).
- REFACTOR: `_leer_orden(orden_id)` del alta pasa a usar la misma consulta con `WHERE o.id = ?` y el mismo mapeo, para que alta y listado no puedan divergir en forma ni en orden de componentes.

### D3 — Orden del listado (decisión 6)

`ORDER BY o.fecha DESC, o.id DESC`. El filtro y el orden operan sobre `ordenes.fecha` (fecha de negocio ingresada por el usuario, DD-08), no sobre `created_at`. Desempate por `id` descendente = última cargada primero: `id` es `INTEGER PRIMARY KEY` y SQLite asigna `max(id) + 1`, así que entre las filas existentes refleja el orden de alta aunque C-05 borre órdenes; no depende del reloj. Dentro de cada orden, componentes por código (como el 201).

### D4 — `OrdenService.listar(numero=None, desde=None, hasta=None)`

En el mismo `OrdenService` (comparte `_normalizar_numero` y el repositorio; la dependencia `get_orden_service` ya existe). Orden de validación, primer error gana (igual que movimientos: identificador primero, después fechas):

1. `numero`: `None`, `""` o solo espacios → sin filtro; si no, `_normalizar_numero` (recorte + MAYÚSCULAS; > 30 → "El campo numero admite hasta 30 caracteres.").
2. `desde`, `hasta`: `parsear_filtro_fecha("desde"|"hasta", valor)`.
3. `validar_rango(...)`: `desde > hasta` → "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."
4. `ordenes = self._repo.listar(numero, f_desde, f_hasta)`.
5. Si `ordenes` está vacía **y** hay `numero` **y** `not self._repo.existe_numero(numero)` → `OrdenNoEncontrada(numero)` (mensaje fijo "No existe una orden con número 'X'.", X normalizado). Una sola consulta extra (`SELECT 1 FROM ordenes WHERE numero = ?`) y solo cuando el resultado es vacío; si el número existe pero quedó fuera del rango → `[]`. La validación (pasos 1-3) siempre precede al 404.
6. Devuelve `ordenes`.

`OrdenNoEncontrada(InventarioError)` en `domain/errors.py` y `existe_numero(numero) -> bool` en el contrato `OrdenRepository` y en `SqliteOrdenRepository`. `api/app.py` la mapea a 404 con `detail` de texto, como `ProductoNoEncontrado`. En C-06 `existe_numero` es un `select` por `numero` en Supabase.

No usa el reloj inyectado (lectura pura).

### D5 — Filtros de fecha compartidos en `services/fechas.py` (decisión 10)

Se mueven desde `movimientos_service.py`, sin cambiar textos:

- `parsear_filtro_fecha(nombre, valor)`: `None`/`""` → `None`; si no, `parsear_fecha(valor, "La fecha '{nombre}' debe tener formato AAAA-MM-DD.", "La fecha '{nombre}' ({valor}) no es una fecha válida.")`. Sin recorte (W-1 de C-03: `" 2026-11-20"` → error de formato).
- `validar_rango(desde_texto, hasta_texto, f_desde, f_hasta)`: si ambos presentes y `f_desde > f_hasta` lanza `DatosInvalidos` con el mensaje de rango (usa el texto recibido, como hoy).

`MovimientosService` pasa a usarlas; sus tests existentes deben seguir verdes sin tocar aserciones.

### D6 — Endpoint y schema

```python
@router.get("", response_model=List[OrdenOut],
            responses={404: {"model": ErrorOut, "description": "No existe una orden con ese número"},
                       422: {"model": ErrorOut, "description": "Filtros inválidos (mensaje en español)"}})
def listar_ordenes(_: Usuario, ordenes: Servicio,
                   numero: Optional[str] = None, desde: Optional[str] = None, hasta: Optional[str] = None):
    return [orden_out(o) for o in ordenes.listar(numero, desde, hasta)]
```

- `def` plano (SQLite síncrono, como el resto). `get_current_user` y el service comparten la conexión del request (FastAPI cachea `get_conexion`).
- Reusa `OrdenOut`/`orden_out` sin cambios: misma forma que el 201 (`id`, `numero`, `fecha`, `usuario`, `componentes[{codigo, nombre, cantidad}]`). Lista sin envolver, como `/api/inventario` y `/api/movimientos` (decisión 7).
- Los parámetros son `str` opcionales: Pydantic no produce 422 propios; todo 422 sale del service por el handler de `DatosInvalidos` existente. Un parámetro repetido (`?numero=a&numero=b`) toma el último (comportamiento de FastAPI, sin tratamiento especial).
- El esquema OpenAPI sigue con ocho rutas: `GET` y `POST` comparten `/api/ordenes`.

### D7 — Tests (Strict TDD, `unittest`, SQLite real, sin mocks)

- Repositorio (`tests/test_sqlite_orden_repository.py`, `:memory:`): las órdenes se siembran con `SqliteOrdenRepository.crear` (con `creada_en` distintos para probar que ordena por `fecha` y no por `created_at`); baja lógica con `UPDATE productos SET activo = 0` + `commit` (C-05 aún no existe). **Sin N+1 verificable sin mocks**: `conn.set_trace_callback` cuenta las sentencias `SELECT` ejecutadas al listar tres órdenes de dos componentes → exactamente 1.
- Service (`tests/test_orden_service.py`): normalización, vacío = sin filtro, mensajes exactos, prioridad de errores.
- `tests/test_fechas.py`: las dos funciones nuevas.
- API (`tests/test_api_ordenes.py`, `TestClient`, archivo temporal): cuerpo exacto, `id` igual al del alta, filtros, 422, 401; `tests/test_api_sesion_inexistente.py` suma `GET /api/ordenes`; OpenAPI.

### Tabla de endpoints del change

| Método | Ruta | Sesión | Respuestas |
|--------|------|--------|-----------|
| GET | `/api/ordenes?numero=&desde=&hasta=` | sí | 200 lista (posiblemente `[]`), 401, 404 (`numero` inexistente), 422 |

## UI Mockups

- Design system revision: 1
- Decision: no (no UI) (2026-11-20) — change solo de API; la pantalla de órdenes (`/ordenes`) se diseña con mockups en C-06.

## Risks / Trade-offs

- [Sin paginación, el listado crece con el historial] → aceptable para un taller (decenas a pocos miles de órdenes); se puede filtrar por rango; PA-08 queda abierta para C-06, donde agregar `limit`/`offset` es compatible hacia atrás.
- [Cabecera repetida por cada línea en el JOIN] → costo despreciable frente a un viaje por orden; una sola consulta.
- [Reuso de `id` tras borrar la última orden (sin `AUTOINCREMENT`)] → no afecta el orden de este listado; es un riesgo para C-05 (un `DELETE /api/ordenes/{id}` con un id viejo podría apuntar a una orden nueva): anotarlo para el propose de C-05.
- [Refactor de `_leer_orden` y de los filtros de movimientos] → cubierto por los tests existentes de alta y de movimientos, que no cambian sus aserciones.
- [Sin `activo` por componente, la UI de C-06 no puede marcar "dado de baja"] → agregar un campo es aditivo y no rompe clientes; se decide con los mockups de C-06 (decisión 9).

## Migration Plan

Sin DDL ni datos nuevos: las bases locales existentes sirven tal cual. Rollback = revertir el código; no hay estado que deshacer.

## Decisiones a confirmar por el usuario

Governance BAJO (solo lectura). Cada decisión se puede revisar por separado; specs y tareas están escritas con la opción ★. Si una cambia, se ajustan antes del apply.

> **Revisión del usuario (2026-11-20): las 11 decisiones fueron aprobadas con la opción ★**, revisadas una por una (la decisión 3 se cambió brevemente a búsqueda parcial y se revirtió a la opción A, exacta). **Ajuste a la decisión 1**: número inexistente → 404 "No existe una orden con número 'X'."; existente pero fuera del rango → 200 `[]` (el usuario probó un 404 con el rango en el mensaje y lo anuló el mismo día). Specs y tareas ya lo reflejan.

1. **Forma de la búsqueda por número.** — **Aprobada con ajuste del usuario (2026-11-20): 404 "No existe una orden con número ..." si el número no existe**.
   - A ★ Solo el filtro `GET /api/ordenes?numero=X` en el mismo listado: devuelve `[orden]`, o 404 "No existe una orden con número 'X'." (X normalizado) si el número no existe (ajuste del usuario); combinable con fechas; si el número existe pero queda fuera del rango → 200 `[]` (404 solo si el número no existe; el usuario probó un 404 con el rango y lo anuló el mismo día); número vacío = sin filtro, nunca 404.
   - B Solo `GET /api/ordenes/{numero}`: 200 con la orden (objeto) o 404 "No existe una orden con número 'X'.".
   - C Ambas (A y B).
   - D Filtro `?numero=` más `GET /api/ordenes/{id}` (detalle por id, como lista hoy la KB en `02_descripcion_general.md`).
   - Por qué A: un solo endpoint y un solo render en la pantalla de órdenes (la búsqueda es otra forma de filtrar la tabla); "no encontrada" se informa explícitamente con 404 (ajuste del usuario, mismo estilo de mensaje que C-02). B/C además chocan con C-05, que borra por `DELETE /api/ordenes/{id}`: la misma ruta tendría `{numero}` en GET y `{id}` en DELETE (`/api/ordenes/123` sería ambiguo si un número es `123`). Agregar un detalle más adelante no rompe nada.

2. **`desde` / `hasta` opcionales por separado.** — **Aprobada (2026-11-20)**.
   - A ★ Cada uno opcional: solo `desde` = de esa fecha en adelante, solo `hasta` = hasta esa fecha, ninguno = todas; parámetro vacío (`?desde=`) = sin filtro. Mismo criterio que `GET /api/movimientos` (C-02).
   - B Los dos o ninguno: uno solo → 422 "Indicá ambas fechas, 'desde' y 'hasta'.".
   - Por qué A: lo pide US-007 (actualizada 2026-11-20), es coherente con movimientos y el frontend puede dejar un campo en blanco sin manejo especial.

3. **Coincidencia del número.** — **Aprobada (2026-11-20): opción A (exacta). El usuario probó la opción B (parcial) y la anuló el mismo día.**
   - A ★ Exacta sobre el valor normalizado (`ot-1` encuentra `OT-1`, no `OT-10`).
   - B Parcial ("contiene", `LIKE %X%` con escape de `%`/`_`): `0003` encuentra `OT-0003`.
   - Por qué A: el número es único (RN-OR-01) y US-007 pide "buscar una por su número"; igual que el filtro por código de movimientos. Para hojear, están los rangos de fecha.

4. **Número combinado con fechas.** — **Aprobada (2026-11-20)**.
   - A ★ Se combinan con Y: `?numero=OT-1&desde=2026-11-18` devuelve `[]` si `OT-1` es anterior (existe, pero fuera del rango).
   - B Si viene `numero`, se ignoran las fechas.
   - C `numero` junto con fechas → 422.
   - Por qué A: mismo comportamiento que `codigo` + fechas en movimientos; regla sin excepciones.

5. **Validación del parámetro `numero`.** — **Aprobada (2026-11-20)**.
   - A ★ Normalizado como en el alta (recorte + MAYÚSCULAS); vacío o solo espacios = sin filtro; más de 30 caracteres → 422 "El campo numero admite hasta 30 caracteres." (mismo mensaje del alta).
   - B Más de 30 caracteres → `[]` (no puede existir, se responde vacío sin error).
   - Por qué A: reutiliza la misma función del alta y avisa de un error de tipeo en vez de "no encontrada"; igual que el código > 50 en movimientos.

6. **Orden del listado y desempate.** — **Aprobada (2026-11-20)**.
   - A ★ Por fecha de la orden descendente (más nueva primero) y, a igual fecha, `id` descendente (la última cargada primero); componentes por código.
   - B Igual, pero desempate por `created_at` descendente.
   - C Fecha ascendente (cronológico).
   - Por qué A: igual que movimientos (lo reciente arriba); `id` refleja el orden de carga sin depender del reloj y no se repite entre filas existentes.

7. **Forma de la respuesta.** — **Aprobada (2026-11-20)**.
   - A ★ Lista sin envolver con la misma forma que el 201 del alta: `[{id, numero, fecha, usuario, componentes: [{codigo, nombre, cantidad}]}]`; sin `created_at`.
   - B Envuelta: `{"ordenes": [...], "total": N}`.
   - C Como A más `created_at` (momento real de carga, ISO `-03:00`).
   - Por qué A: coherente con `/api/inventario` y `/api/movimientos`; un solo schema (`OrdenOut`) para alta y listado; el `id` es lo que necesita el borrado de C-05. `created_at` se puede agregar si C-06 lo muestra.

8. **Paginación.** — **Aprobada (2026-11-20)**.
   - A ★ Sin paginación ni tope en v1 (PA-08 sigue abierta para C-06).
   - B Tope fijo (p. ej. las 500 más nuevas) sin parámetros.
   - C `limit`/`offset` desde ahora.
   - Por qué A: taller chico (03/PA-08), mismo criterio que movimientos; un tope fijo ocultaría órdenes en silencio; agregar `limit`/`offset` después no rompe clientes.

9. **Marcar componentes de productos dados de baja.** — **Aprobada (2026-11-20)**.
   - A ★ No marcar en C-04: se muestran código, nombre y cantidad como cualquier otro (RN-PR-04 solo pide que se muestren).
   - B Agregar `activo: bool` a cada componente en el listado y en el 201 (cambia la forma publicada del alta y un test de C-03).
   - C Agregar `activo` solo en el listado (schema de componente aparte).
   - Por qué A: YAGNI; el uso de esa marca lo definen los mockups de C-06 y agregar el campo entonces es aditivo. Si se prefiere tenerlo ya, B es barata (el JOIN ya lee `productos`).

10. **Mensajes de error de fechas.** — **Aprobada (2026-11-20)**.
    - A ★ Idénticos a movimientos ("La fecha 'desde' debe tener formato AAAA-MM-DD.", "La fecha 'hasta' (2026-02-30) no es una fecha válida.", "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).") desde una función compartida en `services/fechas.py` (refactor de `MovimientosService`, sin cambiar sus textos).
    - B Mismos textos, pero copiados en `OrdenService` sin tocar movimientos.
    - Por qué A: un solo lugar para los mensajes de filtro; el refactor queda cubierto por los tests de movimientos existentes.

11. **Consulta del repositorio.** — **Aprobada (2026-11-20)**.
    - A ★ Una sola consulta con `JOIN` (órdenes + usuario + ítems + productos) agrupada en Python; el alta reutiliza el mismo mapeo.
    - B Dos consultas: cabeceras filtradas y luego ítems con `WHERE orden_id IN (...)` (lotes por el límite de variables de SQLite).
    - C Una consulta de ítems por orden (N+1).
    - Por qué A: un viaje por listado sin importar la cantidad de órdenes, sin listas `IN` que crecen con el historial; un test cuenta las sentencias con `set_trace_callback` (sin mocks).
