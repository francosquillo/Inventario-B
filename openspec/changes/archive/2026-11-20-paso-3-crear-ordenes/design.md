# Design — paso-3-crear-ordenes (C-03)

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: `specs/ordenes-trabajo/spec.md` y `specs/api-http/spec.md`.

Estado actual (C-01 y C-02 archivados; ver `openspec/changes/archive/2026-11-20-paso-2-movimientos-stock/design.md` D1–D10 y "Ajustes post-verify"):

- Capas: `domain/` (dataclasses frozen, errores `InventarioError`, `tiempo.py` con `ZONA_AR` y `ahora_argentina`), `repositories/` (ABCs en `base.py`, SQLite en `sqlite_repo.py`), `services/` (sin `sqlite3` ni FastAPI; `normalizacion.normalizar_codigo`), `api/` (único lugar con FastAPI/Pydantic).
- **DDL ya existente** (C-01): `ordenes(id, numero TEXT NOT NULL UNIQUE, fecha TEXT NOT NULL CHECK (date(fecha) IS NOT NULL AND fecha = date(fecha)), usuario_id FK NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)`, `orden_items(orden_id FK ON DELETE CASCADE, producto_id FK, cantidad INTEGER CHECK (typeof = 'integer' AND > 0), PRIMARY KEY (orden_id, producto_id))`, índices `idx_ordenes_fecha` e `idx_orden_items_producto`. La PK compuesta obliga a consolidar antes de insertar (RN-OR-11, SU-05). **No hay cambios de DDL.**
- Patrón atómico de C-02: `_transaccion(conn)` con `BEGIN IMMEDIATE` + `UPDATE ... WHERE stock >= ?` + `rowcount`; errores de dominio lanzados dentro del bloque → rollback. Hoy `_transaccion` hace `commit()` si `conn.in_transaction` (sugerencia S-2 del verify de C-02). Los tests de repositorio siembran con helpers sin `commit` y dependen de ese commit implícito.
- Validación: Pydantic estricto en la capa HTTP + validación propia en el service (Regla dura 3). 422 con un único `detail` en español vía `mensaje_validacion` (primer error). Handlers de dominio en `app.py` responden `{"detail": str(exc)}`.
- Endpoints `def` (threadpool), conexión SQLite por request (`get_conexion`), sesión con `usuario_id` y `username`.
- Python 3.14 en `.venv`; `sqlite3` con `isolation_level` por defecto (el BEGIN implícito solo ocurre antes de DML; los SELECT no abren transacción).

## Goals / Non-Goals

**Goals:**
- Crear una orden es **una** operación de repositorio todo o nada que en C-06 se reemplaza 1:1 por una función RPC `crear_orden` sin tocar service ni API.
- Informar en un solo rechazo **todos** los faltantes de stock y **todos** los productos inexistentes (US-006: "el mensaje indica cuáles").
- Reutilizar sin duplicar: `normalizar_codigo`, la validación de cantidad, la validación de fechas de C-02 y el formato de error.

**Non-Goals:**
- `GET /api/ordenes` (C-04): ni siquiera un `GET /api/ordenes/{id}`; la respuesta 201 alcanza para verificar en `/docs`, y el estado se comprueba con `GET /api/inventario` y `GET /api/movimientos`.
- Borrado/reintegro (C-05), edición (RN-OR-10), frontend (C-06).
- Cambios de DDL o migración de `ordenes.created_at` legado (la tabla está vacía en datos reales).

## Decisions

### D1 — Contrato `OrdenRepository.crear` (una unidad de trabajo)

En `repositories/base.py`:

```python
class OrdenRepository(ABC):
    @abstractmethod
    def crear(self, numero: str, fecha: date, items: "list[tuple[str, int]]",
              usuario_id: int, creada_en: datetime) -> Orden: ...
```

Recibe datos ya validados, normalizados y **consolidados** por el service (`items` = `(codigo, cantidad_total)` en orden de primera aparición, códigos únicos). Dentro de una sola transacción: verifica el número, resuelve los productos, valida el stock de todos, inserta `ordenes`, inserta `orden_items` y descuenta. Devuelve `Orden` (entidad frozen nueva: `id`, `numero`, `fecha: date`, `usuario: str`, `items: tuple[ItemOrden, ...]`; `ItemOrden(codigo, nombre, cantidad)` ordenados por código).

*Alternativas descartadas:* el service orquestando lecturas y escrituras finas (carrera entre leer y escribir; en Supabase no hay transacción entre llamadas HTTP); reusar `StockRepository.registrar_egreso` N veces (N transacciones, sin todo o nada, y escribiría `movimientos`, violando RN-ST-06).

### D2 — Transacción SQLite de `crear` y orden de pasos

`SqliteOrdenRepository(conn).crear(...)` dentro de `_transaccion(conn)` (`BEGIN IMMEDIATE`):

1. `SELECT 1 FROM ordenes WHERE numero = ?` → si existe, `OrdenDuplicada(numero)`.
2. `SELECT id, codigo, nombre, stock, activo FROM productos WHERE codigo IN (?, ?, ...)` (un placeholder por item; máx. 100, ver decisión 5). Códigos ausentes o con `activo = 0` → `ProductosNoEncontrados(codigos)` en orden de aparición.
3. Faltantes: `stock < cantidad` para cada item → `StockInsuficienteOrden(faltantes)` con **todos** los faltantes (`Faltante(codigo, disponible, solicitado)`) en orden de aparición.
4. `INSERT INTO ordenes (numero, fecha, usuario_id, created_at) VALUES (?, ?, ?, ?)` con `fecha.isoformat()` y `created_at` explícito (D7).
5. Por item: `INSERT INTO orden_items (orden_id, producto_id, cantidad)` y `UPDATE productos SET stock = stock - ? WHERE id = ? AND activo = 1 AND stock >= ?`; `rowcount != 1` → `StockInsuficienteOrden` (defensa en profundidad; con `BEGIN IMMEDIATE` no debería ocurrir). El CHECK `stock >= 0` es la última barrera.
6. Se arma `Orden` con un `SELECT` de las líneas JOIN productos `ORDER BY p.codigo` y el username (JOIN `usuarios`) antes del commit.

Pasos 1–3 son **lecturas** dentro del lock de escritura: los rechazos de negocio no escriben nada, y el rollback los cubre igual. Cualquier excepción (dominio, `sqlite3.IntegrityError` por FK de `usuario_id`, etc.) → rollback y re-lanzar. Como respaldo del paso 1, un `sqlite3.IntegrityError` por `UNIQUE constraint failed: ordenes.numero` se traduce a `OrdenDuplicada`. Todas las consultas parametrizadas; la lista `IN` se arma solo con placeholders `?`.

No se escribe nada en `movimientos` (RN-ST-06).

*Mapeo a C-06 (no se implementa ahora):* `crear_orden(p_numero text, p_fecha date, p_items jsonb, p_usuario_id bigint, p_creada_en timestamptz)` en PL/pgSQL con `SELECT ... FOR UPDATE` de los productos ordenados por id (evita deadlocks) y `RAISE` con SQLSTATE propios (`P0001`-style con `DETAIL` JSON de faltantes) que el repositorio Supabase traduce a los mismos errores de dominio.

### D3 — Endurecimiento de `_transaccion` (sugerencia S-2 de C-02)

Recomendado (decisión 11): `_transaccion` **deja de confirmar en silencio** trabajo pendiente y lanza `RuntimeError("La conexión tiene una transacción pendiente; no se puede iniciar una operación atómica.")` si `conn.in_transaction` es verdadero. Motivo: con órdenes (N productos) y borrados (C-05), un DML previo en la misma conexión quedaría confirmado aunque la orden falle, rompiendo el todo o nada sin que ningún test lo note. En producción no cambia nada (conexión por request, sin DML previo). Costo: los helpers de siembra de `tests/helpers.py` (`insertar_producto`, `insertar_usuario`, `insertar_movimiento`) pasan a hacer `conn.commit()`; un test nuevo verifica que con un `INSERT` sin confirmar la operación lanza `RuntimeError` y el `INSERT` previo se puede revertir. La suite de C-02 debe seguir verde.

### D4 — `OrdenService` (validación, normalización, consolidación, reloj)

`services/orden_service.py`: `OrdenService(orden_repo, ahora=ahora_argentina).crear(numero, fecha, componentes, usuario_id) -> Orden`. Orden de validación (el primer error gana, como en C-02):

1. `numero`: `str` no vacío tras `strip()`, `.upper()`, ≤ 30 (decisión 1) → `DatosInvalidos("El campo numero es obligatorio." | "El campo numero admite hasta 30 caracteres." | "El campo numero debe ser texto.")`.
2. `fecha`: `parsear_fecha_obligatoria(valor)` de `services/fechas.py` (D5).
3. `componentes`: lista (no `str`/dict) con 1..100 elementos (decisión 5); cada línea es un mapeo con `codigo` (vía `normalizar_codigo`) y `cantidad` (vía la validación estricta de cantidad de C-02: `_validar_cantidad` de `stock_service.py` se mueve a `services/normalizacion.py` como `validar_cantidad`, y `StockService` la importa sin cambiar su comportamiento). Error de línea → `DatosInvalidos("Componente N: <mensaje>")` (decisión 6).
4. Consolidación por código normalizado preservando el orden de primera aparición (`dict`). El tope 1..10.000 rige solo por línea (paso 3); el total consolidado no tiene tope (decisión 4, opción B) y solo lo limita el stock (409). Sin riesgo de desborde: máx. 100 líneas x 10.000 = 1.000.000, muy por debajo del rango de INTEGER de SQLite (64 bits).
5. `repo.crear(numero, fecha, items, usuario_id, self._ahora())`.

El service recibe los componentes como secuencia de pares `(codigo, cantidad)` (no Pydantic): el router convierte `ComponenteRequest` a tuplas. Sin `sqlite3` ni FastAPI.

### D5 — Fechas compartidas (`services/fechas.py`)

Se extrae de `movimientos_service._parsear_fecha` una función pura reutilizable con el mismo regex `[0-9]{4}-[0-9]{2}-[0-9]{2}` + `fullmatch` + `date.fromisoformat`, parametrizada por los mensajes. Movimientos conserva **exactamente** sus mensajes actuales (`"La fecha 'desde' debe tener formato AAAA-MM-DD."`, etc.; sus tests no cambian). Para la orden (campo único, sin rango): faltante/vacía → "El campo fecha es obligatorio."; formato → "La fecha debe tener formato AAAA-MM-DD." (mismo texto que `MENSAJE_FECHA` del handler); inexistente → "La fecha (2026-02-30) no es una fecha válida.". Se acepta cualquier fecha real, pasada o futura (decisión 3, DD-08). En la API `fecha` es `str` (no `date` de Pydantic, que en modo lax acepta otros formatos), como en C-02.

### D6 — Errores de dominio y contrato HTTP

Nuevos en `domain/errors.py` (heredan de `InventarioError`):

| Error | Atributos | Mensaje | HTTP |
|---|---|---|---|
| `OrdenDuplicada(numero)` | `numero` | "Ya existe una orden con número 'OT-0001'." | 409 |
| `ProductosNoEncontrados(codigos)` | `codigos: tuple` | 1: "No existe un producto activo con código 'X-00'." (mismo texto que C-02); N: "No existen productos activos con código: 'X-00', 'C-99'." | 404 |
| `StockInsuficienteOrden(faltantes)` | `faltantes: tuple[Faltante]` | "Stock insuficiente para la orden: 'A-01' (disponible 1, solicitado 2); 'B-02' (disponible 0, solicitado 1)." | 409 + `faltantes` |

`Faltante(codigo, disponible, solicitado)` es un dataclass frozen en `domain/entities.py`. El handler de `StockInsuficienteOrden` responde `{"detail": str(exc), "faltantes": [{codigo, disponible, solicitado}, ...]}` (decisión 7); los demás usan el `_responder` existente. `StockInsuficiente` y `ProductoNoEncontrado` de C-02 no cambian. Prioridad de rechazos: 422 → duplicado → inexistentes → stock (decisión 8), que se obtiene naturalmente del orden service → pasos 1–3 de D2.

### D7 — `created_at` explícito con el reloj inyectado

El DDL tiene `DEFAULT CURRENT_TIMESTAMP` (UTC, `YYYY-MM-DD HH:MM:SS`), el mismo problema que C-02 corrigió en `movimientos` (D6 de C-02). Recomendado (decisión 10): el repositorio escribe `created_at` con `_fecha_a_texto(creada_en)` (ISO 8601 con offset `-03:00`), recibido del reloj inyectado del service. Sin DDL ni normalización (no hay órdenes en datos reales). `created_at` no se expone en la respuesta de C-03 (C-04 decide si lo muestra).

### D8 — Schemas y endpoint

`api/schemas.py`:

```python
class ComponenteRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad

class OrdenRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    numero: str = Field(min_length=1, max_length=30)
    fecha: str = Field(min_length=1)
    componentes: List[ComponenteRequest] = Field(min_length=1, max_length=100)

class ComponenteOut(BaseModel): codigo: str; nombre: str; cantidad: int
class OrdenOut(BaseModel): id: int; numero: str; fecha: date; usuario: str; componentes: List[ComponenteOut]
class FaltanteOut(BaseModel): codigo: str; disponible: int; solicitado: int
class StockInsuficienteOut(BaseModel): detail: str; faltantes: Optional[List[FaltanteOut]] = None
```

`api/routers/ordenes.py`: `APIRouter(prefix="/api/ordenes", tags=["ordenes"])`, `@router.post("", status_code=201, response_model=OrdenOut, responses={404: ErrorOut, 409: StockInsuficienteOut, 422: ErrorOut})`, `def` con `get_current_user` (401) y `get_orden_service` (`OrdenService(SqliteOrdenRepository(conn))`). `fecha` se serializa `"2026-11-20"`. La respuesta 409 documentada cubre duplicado (sin `faltantes`) y stock (con `faltantes`).

### D9 — Mensajes 422 de Pydantic para órdenes (`errores_validacion.py`)

- `loc` de una línea: `("body", "componentes", 1, "cantidad")` → el índice entero `1` produce el prefijo "Componente 2: " y el mensaje del campo (`cantidad` → mensaje de cantidad; `codigo` → obligatorio/largo/texto).
- `componentes`: `too_short` → "La orden requiere al menos un componente."; `too_long` → "La orden admite hasta 100 componentes."; `list_type` → "El campo componentes debe ser una lista."; `missing` → "El campo componentes es obligatorio."; línea que no es objeto (`model_type`/`dict_type` con índice) → "Componente N: debe ser un objeto con codigo y cantidad.".
- `fecha`: `missing`/`string_too_short` → "El campo fecha es obligatorio."; `string_type` → "El campo fecha debe ser texto.". Se **corrige** el orden de evaluación para que en `desde`/`hasta`/`fecha` el faltante no caiga en el mensaje de formato (hoy `desde`/`hasta` son opcionales, así que no cambia nada observable en C-02).
- `numero`: cubierto por las reglas genéricas existentes (obligatorio, largo con `max_length` 30, texto).
- Los mismos textos se usan en el service (D4) para que el usuario vea lo mismo venga de Pydantic o del dominio.

### D10 — Tests (Strict TDD, `unittest`, sin mocks de base)

- `tests/test_domain.py`: `Orden`, `ItemOrden`, `Faltante` inmutables; mensajes y atributos de los tres errores nuevos (1 y N códigos; N faltantes).
- `tests/test_fechas.py`: función compartida (formato, fecha inexistente, vacía, `\n` final, dígitos Unicode); `tests/test_movimientos_service.py` sigue verde sin cambios.
- `tests/test_sqlite_orden_repository.py` (`:memory:`, reloj fijo `FECHA_FIJA`): alta con 2 componentes (orden, líneas, stock, `created_at == "2026-11-19T15:30:00-03:00"`, username); stock a 0 sigue activo; duplicado sin escritura; inexistente / inactivo / varios en orden de aparición; un faltante y varios faltantes con stock intacto en **todos** los productos; prioridad duplicado > inexistente > stock; cero filas en `movimientos`; **atomicidad sin mocks**: `usuario_id` inexistente (FK) → `IntegrityError`, ni orden ni líneas y stock intacto en todos los productos; respaldo del UNIQUE (orden insertada en otra conexión… cubierto por concurrencia).
- **Concurrencia** (archivo SQLite temporal, dos conexiones, `threading.Barrier`, repetido 5 veces): (a) dos órdenes distintas `A-01` x 3 sobre stock 5 → exactamente un `StockInsuficienteOrden`, stock 2, una orden; (b) mismo número `OT-0009` → exactamente un `OrdenDuplicada`, stock 9, una orden. Justificación igual que D8 de C-02 (archivo real, no mock).
- `_transaccion` endurecida (D3): `INSERT` sin commit + `crear` → `RuntimeError`, sin orden creada, el `INSERT` previo sigue revertible.
- `tests/test_orden_service.py` (`:memory:` + repo real + reloj fijo): normalización de número y códigos, fechas, 0/101 líneas, error de línea con prefijo, tipos (`True`, `2.5`, `"5"`), consolidación (`A-01` x 2 + `a-01` x 1 → una línea x 3), consolidado que excede stock, total consolidado > 10.000 aceptado con stock suficiente y 409 con `solicitado` consolidado si falta; una validación fallida no escribe nada.
- `tests/test_errores_validacion.py`: errores reales de `OrdenRequest` (vía `ValidationError.errors()`) → prefijo de línea, `componentes` vacío/largo/no lista, `fecha` faltante.
- `tests/test_api_ordenes.py` (`TestClient`, archivo temporal): 201 con forma exacta y `componentes` ordenados por código; inventario actualizado; `GET /api/movimientos` vacío; 401 sin sesión sin cambios; 409 stock con `faltantes` exacto; 409 duplicado sin `faltantes`; 404; 422 por cada familia de mensaje; OpenAPI con ocho endpoints, 422 → `ErrorOut`, 409 → `StockInsuficienteOut`.
- Comando: `.venv/Scripts/python -m unittest discover -s tests -t .`.

### Tabla de endpoints del change

| Método y ruta | Auth | Body | Éxito | Errores |
|---|---|---|---|---|
| `POST /api/ordenes` | sesión | `{numero, fecha, componentes: [{codigo, cantidad}]}` | 201 `{id, numero, fecha, usuario, componentes: [{codigo, nombre, cantidad}]}` | 401; 404 `ProductosNoEncontrados`; 409 `OrdenDuplicada` `{detail}`; 409 `StockInsuficienteOrden` `{detail, faltantes}`; 422 `{detail}` |

## UI Mockups

- Design system revision: 1 (no aplica)
- Decision: no (no UI) — 2026-11-20. Change de backend/API; `/docs` es tooling de verificación. El modal de nueva orden llega en C-06 con mockup gate.
- Mockups: —
- Approval: —
- Preview: —
- Visual verify: —

## Risks / Trade-offs

- [La lógica de validación de stock vive en el repositorio (y en C-06 en PL/pgSQL)] → tests de contrato del repositorio reutilizables contra Supabase; el service conserva validación, normalización, consolidación y reloj (DD-06).
- [El 409 tiene dos formas (con y sin `faltantes`)] → `faltantes` opcional en un único schema; el frontend siempre muestra `detail` y, si viene, marca las líneas.
- [`BEGIN IMMEDIATE` serializa altas; lock > 5 s → `OperationalError` → 500] → taller chico (SU-04); Postgres en C-06.
- [Endurecer `_transaccion` puede romper tests de C-02 que siembran sin commit] → los helpers pasan a confirmar; tarea dedicada con la suite completa como red de seguridad.
- [Número alfanumérico libre permite formatos inconsistentes (`OT-1`, `OT-0001`)] → se normaliza mayúsculas/espacios; el formato es responsabilidad del usuario (PA-06).
- [Fecha futura o muy vieja por error de tipeo] → se valida formato, no razonabilidad (DD-08).
- [Cookie de un usuario inexistente → FK falla → 500] → sin baja de usuarios en v1 (PA-03), igual que C-02.
- [El `numero` normalizado a MAYÚSCULAS cambia lo que tipeó el usuario] → la respuesta 201 devuelve el número guardado.

## Migration Plan

Sin DDL. Bases locales existentes siguen sirviendo; las órdenes que alguien hubiera insertado a mano conservan su `created_at` original. Despliegue = código nuevo + tests. Rollback = quitar router, service, repositorio, entidades, errores, schemas y tests nuevos y revertir `_transaccion` y los helpers; las filas de `ordenes`/`orden_items` creadas quedan válidas para cualquier versión.

## Decisiones a confirmar por el usuario

Governance MEDIO. Revisadas por el usuario el 2026-11-20: las decisiones 1-3 y 5-13 fueron **aprobadas** como recomendadas (★); la 4 fue **cambiada** a la opción B. Specs y tareas reflejan el resultado.

1. **Tipo y formato del número de orden (resuelve PA-06).** **Resultado: Aprobada (2026-11-20).** Resuelve PA-06 (número alfanumérico en MAYÚSCULAS, 1–30).
   - A ★ Texto alfanumérico, recorte + MAYÚSCULAS, 1–30 caracteres, cualquier carácter imprimible (`" ot-0001 "` → `OT-0001`; unicidad sobre el valor normalizado).
   - B Texto recortado sin cambiar mayúsculas (`ot-1` y `OT-1` serían órdenes distintas).
   - C Solo entero positivo (columna TEXT igual; se validaría `^[0-9]+$`).
   - D Número autogenerado por el sistema (contradice US-006, que lo pide como dato del usuario).
   - Por qué A: mismo criterio que el código de producto (C-02), evita duplicados por mayúsculas y admite `OT-0001` o `1234`.

2. **Forma del cuerpo.** **Resultado: Aprobada (2026-11-20).**
   - A ★ `{"numero", "fecha", "componentes": [{"codigo", "cantidad"}]}` con componentes por **código** (como ingreso/egreso).
   - B Componentes por `id` de producto (el frontend necesitaría ids que hoy la API no expone).
   - Por qué A: el inventario expone `codigo`, no `id`; coherente con C-02.

3. **Fecha: rango permitido.** **Resultado: Aprobada (2026-11-20).**
   - A ★ Cualquier fecha real `YYYY-MM-DD`, pasada o futura (DD-08: se valida formato, no razonabilidad).
   - B Rechazar fechas futuras (respecto de hoy en Argentina).
   - C Acotar a una ventana (p. ej. no anterior a 2000 ni posterior a hoy + 1 año).
   - Mensajes (todas las opciones): "El campo fecha es obligatorio.", "La fecha debe tener formato AAAA-MM-DD.", "La fecha (2026-02-30) no es una fecha válida." (misma familia que C-02, sin el nombre entre comillas porque hay un solo campo).

4. **Total consolidado mayor a 10.000 para un mismo producto.** **Resultado: Cambiada por el usuario (2026-11-20): opción B.**
   - A (descartada) 422 por total consolidado > 10.000.
   - B ★ elegida: Permitirlo: el tope de 10.000 aplica solo a cada línea (misma validación estricta de C-02); tras consolidar, el total puede superar 10.000 y solo lo limita el stock (409 con `solicitado` consolidado). Sin 422 por total.
   - Por qué B: una orden puede legítimamente consumir más de 10.000 unidades de un componente; el tope de C-02 acota errores de tipeo por operación, no consumos reales.

5. **Cantidad de líneas por orden.** **Resultado: Aprobada (2026-11-20).**
   - A ★ 1 a 100 líneas (antes de consolidar); 0 → "La orden requiere al menos un componente."; 101 → "La orden admite hasta 100 componentes.".
   - B Sin máximo (solo ≥ 1).
   - C Otro máximo (p. ej. 50 o 500).
   - Por qué A: acota el cuerpo y la consulta `IN (...)` (límite de variables de SQLite holgado) sin limitar un uso real de taller.

6. **Errores dentro de una línea: ¿indicar el número de línea?** **Resultado: Aprobada (2026-11-20).**
   - A ★ Prefijo "Componente N: " (N desde 1, posición en el cuerpo enviado), p. ej. "Componente 2: La cantidad debe ser un entero entre 1 y 10.000.".
   - B Mismo mensaje que C-02 sin indicar la línea.
   - Por qué A: con varias líneas el usuario necesita saber cuál corregir; sigue siendo un único `detail` (primer error).

7. **Forma del 409 por stock insuficiente.** **Resultado: Aprobada (2026-11-20).**
   - A ★ `{"detail": "Stock insuficiente para la orden: 'A-01' (disponible 1, solicitado 2); 'B-02' (disponible 0, solicitado 1).", "faltantes": [{"codigo", "disponible", "solicitado"}, ...]}` con **todos** los faltantes, en orden de aparición.
   - B Solo `detail` con todos los faltantes en el texto (sin lista estructurada).
   - C Solo el primer faltante (como el egreso de C-02).
   - Por qué A: US-006 pide indicar cuáles; `detail` mantiene el contrato uniforme y `faltantes` permite al modal de C-06 marcar las líneas sin parsear texto.

8. **Duplicado, inexistentes y prioridad de rechazos.** **Resultado: Aprobada (2026-11-20).**
   - Número duplicado → A ★ 409 "Ya existe una orden con número 'OT-0001'." / B 422.
   - Producto inexistente o inactivo → A ★ 404 listando **todos** los códigos (1: mismo texto que C-02; N: "No existen productos activos con código: 'X-00', 'C-99'.") / B 422 / C 404 solo con el primero.
   - Prioridad → ★ datos inválidos (422) → número duplicado (409) → inexistentes (404) → stock (409); se informa uno solo.
   - Por qué: coherente con C-02 (404 inexistente/inactivo, 409 conflicto con el estado actual); el duplicado es conflicto con datos existentes, no un dato malformado.

9. **Respuesta del alta.** **Resultado: Aprobada (2026-11-20).**
   - A ★ 201 `{id, numero, fecha, usuario, componentes: [{codigo, nombre, cantidad}]}` con las líneas consolidadas ordenadas por código, sin stock restante (forma reutilizable por el listado de C-04).
   - B Igual que A más `stock_restante` por componente.
   - C 200 en lugar de 201.
   - D 201 solo con `{id, numero}`.
   - Por qué A: 201 es lo correcto para un alta; el frontend refresca el inventario con `GET /api/inventario` como hace tras ingreso/egreso, y la misma forma sirve para C-04.

10. **`created_at` de la orden.** **Resultado: Aprobada (2026-11-20).**
    - A ★ Escribirlo explícitamente con el reloj inyectado en ISO 8601 `-03:00` (como `movimientos.fecha` en C-02); no se expone en la respuesta de C-03.
    - B Dejar el `DEFAULT CURRENT_TIMESTAMP` (UTC, otro formato) y resolverlo en C-04 o C-06.
    - Por qué A: un solo formato de instante en toda la base, tests deterministas, sin DDL.

11. **Sugerencia S-2 de C-02: commit implícito en `_transaccion`.** **Resultado: Aprobada (2026-11-20).**
    - A ★ Endurecer: si la conexión tiene una transacción pendiente, lanzar `RuntimeError` en lugar de confirmarla; los helpers de siembra de tests pasan a hacer `commit()`; test que lo verifica.
    - B Mantener el commit implícito y solo documentarlo con un comentario explícito.
    - C Mantenerlo y agregar solo una aserción en tests.
    - Por qué A: con órdenes de N productos y borrados con reintegro (C-05), confirmar en silencio trabajo previo rompería el todo o nada sin que nada lo detecte; en producción no cambia el comportamiento.

12. **Sin lectura en C-03.** **Resultado: Aprobada (2026-11-20).**
    - A ★ No agregar `GET /api/ordenes/{id}` ni listado; la verificación usa la respuesta 201, `GET /api/inventario` y `GET /api/movimientos`.
    - B Agregar un `GET /api/ordenes/{id}` mínimo ahora.
    - Por qué A: respeta el límite con C-04 (listado y búsqueda por número allí).

13. **Prueba de concurrencia.** **Resultado: Aprobada (2026-11-20).**
    - A ★ Dos casos sobre archivo SQLite temporal con dos hilos y `threading.Barrier`, repetidos 5 veces: stock compartido (una orden gana) y mismo número (una gana).
    - B Solo el caso de stock compartido.
    - Por qué A: cubre las dos carreras posibles del alta.

## Ajustes post-verify (2026-11-20)

Aprobados por el usuario tras el verify (W-1, W-2, S-1, S-2).

- **W-1 — `fecha` no se recorta en HTTP.** `schemas.py`: se quitó `str_strip_whitespace` del modelo y se aplica solo a `numero` y `codigo` (alias `TextoRecortado`); `fecha` llega tal cual al `OrdenService`, que la rechaza con "La fecha debe tener formato AAAA-MM-DD." (`" 2026-11-20 "`, `"2026-11-20\n"`, `"\t2026-11-20"` -> 422). Efecto lateral: una fecha solo de espacios ahora da el error de formato (antes "obligatorio"). Los filtros `desde`/`hasta` de movimientos ya pasaban por `fechas.py` sin recorte: se agregó un test que lo confirma.
- **W-2 — sesión de un usuario inexistente (todos los endpoints protegidos).** `get_current_user` ahora recibe la conexión del request (`Depends(get_conexion)`, la misma que usa el service) y consulta `UsuarioRepository.obtener_por_id` (método nuevo en `base.py` y `SqliteUsuarioRepository`). Si no existe: se limpia la sesión (`request.session.clear()`, descarta la cookie vieja) y se responde 401 con el mismo `detail` que sin sesión, "No autenticado." (no se introduce un mensaje nuevo: para el cliente es lo mismo, hay que volver a iniciar sesión). La identidad devuelta sale de la base (id y username), no de la cookie. Costo: un `SELECT` por id en cada request protegido. FastAPI sigue fuera de `domain/`, `services/` y `repositories/`. Cambia el comportamiento de C-01/C-02 (antes: 200 en lecturas y 500 en escrituras); se documenta como requisito ADDED en el delta de `api-http`.
- **S-1 — `null` en campos obligatorios = "obligatorio".** `errores_validacion.py`: un error `string_type` o `list_type` cuyo `input` es `None` produce "El campo X es obligatorio." (`fecha`, `numero`, `componentes`, `codigo` de línea y, en C-01/C-02, `username`, `password`, `codigo` de ingreso/egreso). Un tipo incorrecto distinto de `null` (`5`) sigue siendo "debe ser texto". `nombre: null` en ingreso sigue siendo "no enviado" (campo opcional). `cantidad: null` conserva el mensaje de cantidad inválida (comportamiento fijado por C-02). Se actualizó `test_api_auth` (`password: null` pasa de "debe ser texto" a "obligatorio"): es el único test previo modificado en su aserción.
- **S-2 — respaldo `IntegrityError` -> `OrdenDuplicada`.** Test con una conexión SQLite real que solo da por libre el chequeo previo de número (envoltorio mínimo dentro del test), de modo que el `UNIQUE` real dispara el respaldo; verifica el error de dominio, que no se escribe nada y que otro `IntegrityError` (FK) no se traduce. Se confirmó por mutación que el test falla si se rompe el respaldo.
