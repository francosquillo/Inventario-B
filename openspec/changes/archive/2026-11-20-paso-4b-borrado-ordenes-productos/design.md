# Design — paso-4b-borrado-ordenes-productos (C-05)

## Context

Ver `proposal.md` (Why). Estado actual relevante (C-01..C-04 archivados):

- **DDL** (sin cambios en este change):
  - `ordenes(id INTEGER PRIMARY KEY, numero UNIQUE, ...)` **sin `AUTOINCREMENT`**: SQLite reutiliza el `id` máximo tras borrar. Por eso el borrado se hace por `numero` (único, elegido por el usuario y normalizado), no por `id` (decisión 1).
  - `orden_items(orden_id REFERENCES ordenes(id) ON DELETE CASCADE, producto_id REFERENCES productos(id), ...)`: `producto_id` sin acción → `NO ACTION`. Con `PRAGMA foreign_keys = ON`, que `conectar()` activa en cada conexión, un producto con líneas no se puede borrar físicamente.
  - `productos.activo INTEGER CHECK (activo IN (0, 1))`; `movimientos.tipo CHECK IN ('ingreso','egreso')`.
- **Patrón atómico**: `_transaccion(conn)` abre `BEGIN IMMEDIATE` antes de leer, hace rollback ante cualquier excepción y lanza `RuntimeError` si la conexión ya tiene una transacción pendiente (endurecimiento de C-03). Cada endpoint usa su propia conexión (`get_conexion`), así que cada escritura abre su propia transacción.
- **Reutilizable**:
  - `_SQL_SUMAR_Y_ACTIVAR` (`stock = stock + ?, activo = 1`) de la reactivación por ingreso (C-02);
  - `_SQL_LISTAR_ORDENES` + `_a_ordenes` (forma única de `Orden`, incluye productos inactivos), que `_leer_orden` usa con `WHERE o.id = ?` (el borrado agrega la variante `WHERE o.numero = ?`);
  - `OrdenOut`/`orden_out`, `ProductoOut`/`producto_out`, `ErrorOut`;
  - `normalizar_codigo`;
  - `_normalizar_numero` de `services/orden_service.py` (recorte + MAYÚSCULAS, obligatorio, máximo 30; mensajes "El campo numero es obligatorio." y "El campo numero admite hasta 30 caracteres.") y `OrdenNoEncontrada(numero)` → 404 "No existe una orden con número 'X'." (C-04);
  - `ProductoNoEncontrado` → 404 "No existe un producto activo con código 'X'.";
  - el handler 422 en español (`mensaje_validacion`): un parámetro faltante da "El campo X es obligatorio." y un tipo inválido "El campo X no es válido.".
- **Reglas de dominio**: DD-09/RN-ST-06 (los descuentos por orden y el reintegro no van a `movimientos`), RN-OR-12/SU-06 (el reintegro reactiva), RN-PR-03/04/06, US-009 ("el stock y el historial se conservan"), Flujo 7 ("inexistente o ya inactivo → mensaje claro").
- Opera solo `admin`; todo endpoint salvo el login exige sesión (`get_current_user`, que también confirma que el usuario existe).

## Goals / Non-Goals

**Goals:**
- Cada borrado es **una** operación de repositorio todo o nada, que en C-06 se reemplaza 1:1 por una función RPC sin tocar el service ni la API.
- Ningún camino deja estado parcial. Ningún doble borrado reintegra dos veces.
- La respuesta del borrado de orden es el único registro de lo borrado y debe alcanzar para reconstruirlo a mano.
- Mensajes y códigos HTTP coherentes con C-02..C-04, reutilizando los textos existentes.

**Non-Goals:**
- Papelera, deshacer o auditoría de borrados (no los pide la KB; ver Riesgos).
- Migrar `ordenes.id` a `AUTOINCREMENT` (innecesario: el borrado es por número, decisión 1).
- Confirmación en la API (IN-02: es del modal de C-06).
- Borrado físico de productos.

## Decisions

### D1 — Contratos de repositorio (unidades de trabajo)

```python
class OrdenRepository(ABC):
    @abstractmethod
    def borrar(self, numero: str, reintegrar: bool) -> ResultadoBorradoOrden:
        """Borra la orden y sus lineas (numero ya normalizado); si `reintegrar`, devuelve el stock
        y reactiva. Todo o nada. No escribe en `movimientos` (DD-09). Lanza OrdenNoEncontrada."""

class ProductoRepository(ABC):
    @abstractmethod
    def dar_de_baja(self, codigo: str) -> Producto:
        """activo = 0 sobre un producto activo (codigo ya normalizado). Conserva el stock.
        Lanza ProductoNoEncontrado si no existe o ya esta inactivo."""
```

Entidades nuevas (frozen) en `domain/entities.py`:
- `Reintegro(codigo, nombre, cantidad, stock, reactivado)`;
- `ResultadoBorradoOrden(orden: Orden, reintegrado: bool, reintegros: tuple[Reintegro, ...])`.

Sin errores nuevos: el borrado reutiliza `OrdenNoEncontrada(numero)` de C-04 (404 "No existe una orden con número 'X'.", ya mapeado en `app.py`), que no se toca.

En C-06 estos contratos pasan a ser:
- la RPC `borrar_orden(p_numero text, p_reintegrar boolean)` (PL/pgSQL, una transacción);
- un `update ... where codigo = ? and activo returning *` para la baja.

### D2 — `SqliteOrdenRepository.borrar` (todo dentro de un único `_transaccion`)

1. `BEGIN IMMEDIATE`: toma el lock de escritura antes de leer, así dos borrados simultáneos se serializan.
2. Lee la orden por número normalizado con `_SQL_LISTAR_ORDENES + " WHERE o.numero = ?"`. Si no hay filas, lanza `OrdenNoEncontrada(numero)`.
   - Se agrega `_buscar_orden_por_numero(numero) -> Orden | None`; `_leer_orden` (por id, usado por el alta) no cambia.
   - El `id` de la orden leída se usa en los pasos 3 y 4 (`orden_items.orden_id`, `ordenes.id`), todo dentro de la misma transacción.
   - El segundo de dos borrados concurrentes llega aquí después del commit del primero, no encuentra el número y responde 404.
3. Si `reintegrar`:
   - Lee las líneas con `SELECT i.cantidad, p.id, p.codigo, p.nombre, p.stock, p.activo FROM orden_items i LEFT JOIN productos p ON p.id = i.producto_id WHERE i.orden_id = ? ORDER BY p.codigo` (con el `id` de la orden leída).
   - Una línea sin producto (`p.id IS NULL`, solo posible con manipulación externa con FKs apagadas) aborta todo con `RuntimeError`: rollback y 500 (decisión 4).
   - Por cada línea, en orden de código, ejecuta `_SQL_SUMAR_Y_ACTIVAR (cantidad, producto_id)`, exige `rowcount == 1` y arma `Reintegro(stock = stock_previo + cantidad, reactivado = not activo)`.
4. Borra explícitamente `DELETE FROM orden_items WHERE orden_id = ?` y luego `DELETE FROM ordenes WHERE id = ?`, exigiendo `rowcount == 1` (ambos con el `id` leído en el paso 2).
   - El borrado explícito no depende de que el `PRAGMA foreign_keys` esté activo; el `ON DELETE CASCADE` queda como respaldo. La RPC de C-06 hará lo mismo.
5. El commit lo hace `_transaccion`. Cualquier excepción en 2-4 hace rollback completo (RN-OR-09).

Sin escrituras en `movimientos` (decisión 3). El `stock` resultante se calcula dentro del lock, así que es exacto.

### D3 — `SqliteProductoRepository.dar_de_baja`

Dentro de `_transaccion`:
1. `UPDATE productos SET activo = 0 WHERE codigo = ? AND activo = 1`. Si `rowcount == 0`, lanza `ProductoNoEncontrado(codigo)` (inexistente o ya inactivo, decisión 6).
2. Lee el producto con `_SQL_PRODUCTO_POR_CODIGO` y lo devuelve.

El `WHERE activo = 1` más `BEGIN IMMEDIATE` hacen que de dos bajas simultáneas solo una afecte la fila; la otra recibe 404. Ni stock ni `movimientos` cambian (decisiones 3 y 7).

### D4 — Services

**`OrdenService.borrar(numero, reintegrar)`.** Valida en este orden y el primer error gana:
1. `reintegrar` (decisión 2): `None` o `""` → `DatosInvalidos("El campo reintegrar es obligatorio.")`; `"true"` → `True`; `"false"` → `False`; un `bool` de Python pasa tal cual (para callers internos); cualquier otro valor → `DatosInvalidos("El campo reintegrar debe ser true o false.")`.
2. `numero` con `_normalizar_numero` (el mismo del alta y del filtro de C-04): `None`, vacío o solo espacios → `DatosInvalidos("El campo numero es obligatorio.")`; más de 30 caracteres tras normalizar → `DatosInvalidos("El campo numero admite hasta 30 caracteres.")` (decisión 10, reinterpretada: 422 antes que 404).
3. Llama a `self._repo.borrar(numero_normalizado, valor)`; si el número no existe, el repo lanza `OrdenNoEncontrada` → 404.

**`ProductoService.dar_de_baja(codigo)`** vive en un módulo nuevo, `services/producto_service.py` (el Flujo 7 lo nombra así). Hace `normalizar_codigo(codigo)`, con sus mensajes existentes para vacío y más de 50 caracteres, y llama a `self._repo.dar_de_baja(...)`. Se agrega `get_producto_service` en `dependencies.py`.

### D5 — Endpoints y schemas

**`DELETE /api/ordenes/{numero:path}`.** Va en `api/routers/ordenes.py`, `def` plano.
- `numero: str` (path) con el convertidor `path`, igual que `productos` (decisión 9): acepta números con `/` (por ejemplo `OT/2026/01`). OpenAPI lo publica como `/api/ordenes/{numero}`. No hay error de tipo posible: cualquier texto llega al service, que normaliza (recorte + MAYÚSCULAS) y valida.
- Los clientes deben codificar en la URL los caracteres `?` y `#` del número (el navegador, `encodeURIComponent` y Swagger lo hacen); un `?` sin codificar corta el path y el resto se lee como query. La `/` no necesita codificarse. Se documenta en la descripción del endpoint.
- `reintegrar: Annotated[str, Query(json_schema_extra={"enum": ["true", "false"]})]`, obligatorio:
  - si falta, el 422 del handler dice "El campo reintegrar es obligatorio.";
  - en Swagger es un desplegable `true`/`false`;
  - el valor llega como texto al service, que es la autoridad (vacío o inválido → 422 del service).
- `response_model=BorradoOrdenOut`:
  - `orden: OrdenOut`;
  - `reintegrado: bool`;
  - `reintegros: List[ReintegroOut]`, donde `ReintegroOut` tiene `codigo`, `nombre`, `cantidad`, `stock` y `reactivado`.
- `responses`: 404 y 422 con `ErrorOut`.

**`DELETE /api/productos/{codigo:path}`.** Va en un router nuevo, `api/routers/productos.py` (prefijo `/api/productos`).
- El convertidor `path` acepta códigos con `/` (decisión 9). OpenAPI lo publica como `/api/productos/{codigo}`. Un código vacío llega como `""` y el service responde "obligatorio".
- `response_model=ProductoOut`, vía `producto_out` (decisión 8). `responses`: 404 y 422 con `ErrorOut`.

En `app.py`: `include_router(productos.router)` y nada más en la tabla de handlers: `OrdenNoEncontrada` y `ProductoNoEncontrado` ya están mapeados a 404. El esquema pasa de 8 a 10 rutas.

**Precedencia de errores.** 401 (sesión) → 422 (query de FastAPI, luego service: `reintegrar`, después `numero`) → 404 (no existe). Es la misma regla que C-04: la validación tiene prioridad. Si falta `reintegrar` gana el 422 de FastAPI aunque el número no exista.

### D6 — Tests (Strict TDD, `unittest`, SQLite real, sin mocks)

**Repositorio** (`:memory:`): `tests/test_sqlite_orden_repository.py` y `tests/test_sqlite_repositories.py`, o un archivo nuevo `tests/test_sqlite_producto_repository.py`.
- Siembra con los helpers y `SqliteOrdenRepository.crear`. La baja previa se hace con `UPDATE ... activo = 0`.
- **Atomicidad con fallas reales** (sin mocks):
  - `CREATE TEMP TRIGGER ... BEFORE UPDATE OF stock ON productos WHEN OLD.codigo = 'B-02' BEGIN SELECT RAISE(ABORT, 'falla forzada'); END` hace fallar el reintegro después de sumar `A-01`;
  - un trigger `BEFORE DELETE ON ordenes` hace fallar el borrado después del reintegro completo;
  - una fila de producto borrada con `PRAGMA foreign_keys = OFF` simula la línea huérfana.
  - En los tres casos, después del fallo: la orden y sus líneas siguen, el stock y `activo` no cambian y `conn.in_transaction` es `False`.
- **Concurrencia** (archivo temporal, dos conexiones, `threading.Barrier`, con el patrón de `test_dos_egresos_simultaneos_solo_uno_pasa`): dos `borrar(..., True)` de la misma orden → uno devuelve el resultado y el otro lanza `OrdenNoEncontrada`; el stock se suma una sola vez. Lo mismo para dos `dar_de_baja`.

**Service**: `tests/test_orden_service.py` y un archivo nuevo `tests/test_producto_service.py`, con repositorio real en `:memory:`. Cubren parseo de `reintegrar`, normalización y límites del número, normalización del código y prioridad de errores.

**API**: `tests/test_api_ordenes.py` y un archivo nuevo `tests/test_api_productos.py`, con `TestClient` y archivo temporal. Cubren:
- cuerpos exactos y 401/404/422;
- efectos cruzados (inventario, listado de órdenes, egreso y alta con producto dado de baja, reingreso);
- `GET /api/movimientos` sin cambios.

Además se extiende `tests/test_api_sesion_inexistente.py` y se actualizan los tests de OpenAPI: se agregan las rutas nuevas a las tuplas y se renombra `test_siete_endpoints_...` solo si la aserción cambia.

### Tabla de endpoints del change

| Método | Ruta | Sesión | Respuestas |
|--------|------|--------|-----------|
| DELETE | `/api/ordenes/{numero}?reintegrar=true\|false` | sí | 200 `{orden, reintegrado, reintegros}`, 401, 404, 422 |
| DELETE | `/api/productos/{codigo}` | sí | 200 `ProductoOut`, 401, 404, 422 |

## UI Mockups

- Design system revision: 1
- Decision: no (no UI) (2026-11-20) — change solo de API; los modales de borrado de orden y de producto se diseñan con mockups en C-06.

## Riesgos de datos y mitigación

Governance ALTO: el borrado de orden es **físico e irreversible** y el reintegro toca varios productos.

| # | Riesgo | Mitigación |
|---|--------|------------|
| R1 | **Pérdida irreversible de la orden.** No hay papelera ni auditoría, y por DD-09 el reintegro no queda en `movimientos`. Una orden borrada solo sobrevive en la respuesta del `DELETE`. | La respuesta 200 devuelve la orden completa (número, fecha, usuario, componentes) y el detalle del reintegro (decisión 5), suficiente para recargarla a mano. `reintegrar` es obligatorio y sin default. El modal de confirmación llega en C-06. Recomendación operativa: copiar `inventario.db` antes de probar borrados en `/docs` con datos reales (tarea 7.4). |
| R2 | **Reintegro parcial** (falla entre productos o entre el reintegro y el borrado). | Un único `_transaccion` con `BEGIN IMMEDIATE`; `rowcount` exigido en cada `UPDATE`/`DELETE`; tests con fallas reales forzadas por triggers y por una línea huérfana que verifican rollback total y `in_transaction == False`. |
| R3 | **Doble reintegro** (doble clic, reintento o dos pestañas). | El lock de escritura se toma antes de leer la orden: el segundo borrado ya no encuentra el número → 404, sin tocar stock. Test de concurrencia con hilos. |
| R4 | **Reuso de `id`** (sin `AUTOINCREMENT`): con borrado por id, un `DELETE` viejo podría borrar una orden nueva que heredó el id. | **No aplica** (decisión 1, resuelta por el usuario el 2026-11-20): el borrado es por `numero`, único y elegido por el usuario. Residual: si se borra `OT-0001` y luego se crea otra con el mismo número, repetir el `DELETE` borraría la nueva; es el número que el usuario escribió y la respuesta muestra `id`, `fecha` y componentes. Sin DDL. |
| R5 | **`reintegrar=false` por error**: el stock descontado se pierde. | Es la semántica pedida (RN-OR-09). La respuesta dice `"reintegrado": false` y lista los componentes con sus cantidades, que se pueden reingresar con `POST /api/stock/ingreso` (eso sí deja movimientos). |
| R6 | **Reactivación inesperada** (SU-06): un producto dado de baja reaparece en el inventario tras reintegrar. | Regla confirmada por el usuario (RN-OR-12). La respuesta marca `"reactivado": true` por producto para que la UI de C-06 lo informe. |
| R7 | **Stock inflado** si las piezas ya se usaron físicamente y se elige reintegrar. | Es una decisión del usuario en cada borrado; la API no puede saberlo. El modal de C-06 hace la pregunta explícita. |
| R8 | **Línea huérfana** (producto borrado físicamente fuera de la app con FKs apagadas). | Reintegro abortado con 500 y rollback (decisión 4), sin estado parcial. No puede ocurrir por la app: no hay borrado físico de productos y la FK está activa. |
| R9 | **Base bloqueada** por otra escritura larga. | `sqlite3` espera 5 s (timeout por defecto) y luego falla con `OperationalError` → 500 con rollback. No queda nada a medias. |
| R10 | **Baja con stock > 0** (decisión 7): ese stock deja de verse en el inventario. | US-009 pide conservarlo. Reaparece al reingresar o al reintegrar una orden. El stock sigue en la base y en la respuesta de la baja. |

## Risks / Trade-offs

- [Sin auditoría de borrados] → aceptado por DD-09; si hiciera falta, una tabla `ordenes_borradas` es aditiva (fuera de v1).
- [Reutiliza `_SQL_SUMAR_Y_ACTIVAR` del ingreso] → la reactivación por reintegro y la reactivación por ingreso no pueden divergir.
- [`reintegrar` como texto validado en el service, no `bool` de Pydantic] → la regla vive en el service (autoridad, Regla dura 3) y es portable a C-06. La alternativa `bool` aceptaría `1`, `yes`, `on`, etc. (decisión 2).
- [Router de productos nuevo con una sola ruta] → C-06 puede sumar ahí otras operaciones de producto sin mover nada.

## Migration Plan

Sin DDL ni datos nuevos: las bases locales existentes sirven tal cual. Rollback = revertir el código. Las órdenes ya borradas no se recuperan (R1).

## Open Questions

- Ninguna bloqueante. Al archivar, actualizar la KB: `02_descripcion_general.md` dice `DELETE /api/productos/<id>` y `GET /api/productos`; el Flujo 6 dice "por cascade"; `08_arquitectura_propuesta.md` nombra el método `borrar_con_reintegro`.

## Decisiones del usuario (revisadas el 2026-11-20)

> **Nota de revisión (2026-11-20):** el usuario revisó las 10 decisiones. Cambios: (1) el borrado de orden pasa a ser **por número de orden, no por id**; (10) se reinterpreta para el número; (2) se aprueba con un ajuste para C-06. Las decisiones 3 a 9 se aprobaron con ★. Specs, tareas y propuesta ya reflejan estas resoluciones, así que el change queda listo para el apply (la revisión humana exigida por governance ALTO ya se hizo).

1. **Identificador del borrado de orden. Resuelta por el usuario (2026-11-20): el borrado se hace por número de orden (no por id); el riesgo de reutilización de id deja de aplicar.**
   - Endpoint `DELETE /api/ordenes/{numero}?reintegrar=true|false`. El número se normaliza como en el alta y el filtro de C-04 (recorte + MAYÚSCULAS) y la ruta usa el convertidor `path` (acepta `/`). Los clientes codifican `?` y `#`, como hace Swagger.
   - Reemplaza a las opciones originales (aceptar el reuso de id, `AUTOINCREMENT`, id más número de guarda). No hay DDL.
   - La respuesta (decisión 5) sigue incluyendo la orden completa con su `id`.

2. **Valores de `reintegrar`. Aprobada con ajuste del usuario (2026-11-20): casilla marcada por defecto en C-06.**
   - Solo `true` o `false` exactos, en minúsculas. Si falta o viene vacío → 422 "El campo reintegrar es obligatorio."; cualquier otro valor (`TRUE`, `1`, `si`) → 422 "El campo reintegrar debe ser true o false.". Swagger muestra un desplegable.
   - **Nota para C-06**: el modal de borrar orden tiene una casilla "Devolver stock" **marcada por defecto**, y el texto del botón de confirmar dice el resultado ("Borrar y devolver stock" / "Borrar sin devolver stock"). La API sigue sin valor por defecto: el frontend siempre envía `true` o `false`. Registrado también en `CHANGES.md` § C-06.

3. **Reintegro y baja no escriben en `movimientos`. Aprobada (2026-11-20).**
   - Ninguno de los dos (DD-09, simétrico con RN-ST-06). La baja no mueve stock.

4. **Línea de orden cuyo producto ya no existe. Aprobada (2026-11-20).**
   - Abortar todo el borrado (500, rollback, la orden sigue intacta; RN-OR-09).

5. **Respuesta del borrado de orden. Aprobada (2026-11-20).**
   - 200 con `{"orden": <OrdenOut>, "reintegrado": bool, "reintegros": [{codigo, nombre, cantidad, stock, reactivado}]}` (vacía sin reintegro). Es el único rastro de lo borrado (R1).

6. **Baja de un producto ya inactivo. Aprobada (2026-11-20).**
   - 404 con "No existe un producto activo con código 'X'." (el mismo que egreso y alta de orden).

7. **Baja de un producto con stock > 0. Aprobada (2026-11-20).**
   - Se permite y el stock se conserva (US-009); un reingreso o reintegro lo reactivan sumando (C-02).

8. **Respuesta de la baja de producto. Aprobada (2026-11-20).**
   - 200 con `ProductoOut` (`codigo`, `nombre`, `stock`, `sin_stock`), igual que el egreso.

9. **Códigos de producto con `/`. Aprobada (2026-11-20).**
   - Ruta con convertidor `path` (`/api/productos/{codigo:path}`). La misma técnica se usa para el número de orden (decisión 1).

10. **Validación del identificador de orden. Aprobada (2026-11-20), reinterpretada para el número (opción 1 adaptada).**
    - 422 primero, 404 después: número vacío o solo espacios → 422 "El campo numero es obligatorio."; más de 30 caracteres tras normalizar → 422 "El campo numero admite hasta 30 caracteres."; número válido que no existe → 404 "No existe una orden con número 'X'." (X normalizado; exactamente el mensaje de C-04, vía `OrdenNoEncontrada`).
    - Desaparece la lógica de ids enteros y el `OverflowError` de SQLite.

## Ajustes post-verify (2026-11-20)

- **`reintegrar` repetido (SUGGESTION 2 del verify). Aprobado.** `DELETE /api/ordenes/{numero}` responde 422 "El campo reintegrar debe enviarse una sola vez." si el parámetro aparece más de una vez, aunque con valores iguales. Es una comprobación de la capa HTTP (`request.query_params.getlist("reintegrar")` en el router); dominio, services y repositorios no cambian. Precedencia: 401 (sesión) → 422 repetido → 422 valor/número (service) → 404. Se evalúa antes que el valor y el número porque con un borrado irreversible la petición es ambigua y no debe interpretarse. El esquema OpenAPI no cambia (enum `true`/`false`, obligatorio).
