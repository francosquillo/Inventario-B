# Design — paso-2-movimientos-stock (C-02)

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: `specs/movimientos-stock/spec.md`, `specs/consulta-movimientos/spec.md` y `specs/api-http/spec.md`.

Estado actual (C-01 archivado, `openspec/changes/archive/2026-11-19-paso-1-base-cli/design.md` D1–D12):

- Paquete `inventario/` en capas: `domain/` (dataclasses `Producto` con `sin_stock`, `Usuario`, `UsuarioAutenticado`; errores `InventarioError`/`CredencialesInvalidas`), `repositories/` (ABCs en `base.py`, implementación en `sqlite_repo.py`), `services/` (sin `sqlite3` ni FastAPI), `api/` (único lugar con FastAPI/Pydantic: `app.py` factory + handlers, `dependencies.py` con conexión por request y `get_current_user`, `routers/`, `schemas.py`).
- La tabla `movimientos` ya existe en `ESQUEMA_SQL`: `fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP` (sin CHECK de formato), `producto_id` FK, `tipo CHECK IN ('ingreso','egreso')`, `cantidad CHECK (typeof = 'integer' AND > 0)`, `usuario_id` FK, índices `idx_movimientos_producto` e `idx_movimientos_fecha`. `productos.stock CHECK (>= 0)`, `codigo UNIQUE` (sin CHECK de mayúsculas), `nombre CHECK (length(trim) > 0)`. `PRAGMA foreign_keys = ON` en cada conexión. **No hay cambios de DDL** (ver D6).
- Conexión SQLite por request (`get_conexion`), endpoints `def` (threadpool). La sesión guarda `usuario_id` y `username`; `get_current_user` devuelve `UsuarioAutenticado` o 401.
- SQLite convierte `'5'` a `5` antes del CHECK (D2 de C-01): la defensa contra tipos es Pydantic estricto + el service.
- C-01 no tiene seed de productos ni ningún camino de código que escriba `movimientos`: en datos reales la tabla está vacía y los productos existentes (si alguien los insertó a mano) se asumen con código en mayúsculas.

## Goals / Non-Goals

**Goals:**
- Cada ingreso/egreso es una única operación atómica de repositorio que en C-06 se reemplaza 1:1 por una función RPC de Postgres, sin tocar el service ni la API.
- Sin carreras: dos egresos simultáneos nunca dejan stock negativo ni dos altas del mismo código.
- Consulta de la bitácora con filtros simples (código, rango de fechas locales).
- Fechas deterministas en tests (reloj inyectable) y en un único formato con offset.
- Services libres de `sqlite3`; FastAPI solo en `api/` (Regla dura 1). Doble validación (Regla dura 3).

**Non-Goals:**
- Paginación o límite del listado de movimientos (PA-08).
- Renombrar productos, ajustar stock a un valor absoluto, deshacer movimientos.
- Cambiar el DDL o manejar zonas con horario de verano.

## Decisions

### D1 — Contrato `StockRepository` con dos operaciones atómicas

En `repositories/base.py`:

```python
class StockRepository(ABC):
    @abstractmethod
    def registrar_ingreso(self, codigo: str, cantidad: int, nombre: "str | None",
                          usuario_id: int, fecha: datetime) -> ResultadoIngreso: ...
    @abstractmethod
    def registrar_egreso(self, codigo: str, cantidad: int,
                         usuario_id: int, fecha: datetime) -> Producto: ...
```

Cada método es **una unidad de trabajo completa**: lee el producto, decide (sumar / reactivar / crear / rechazar), actualiza el stock e inserta el movimiento con la `fecha` recibida, todo dentro de la misma transacción. Recibe datos ya validados y normalizados por el service (código ya en mayúsculas). Errores de negocio que detecta dentro de la transacción (no existe y no hay nombre; no existe/inactivo; stock insuficiente) se lanzan como errores de dominio (D4) después del rollback.

`ResultadoIngreso` es un dataclass frozen nuevo en `domain/entities.py`: `producto: Producto`, `creado: bool`, `reactivado: bool`.

*Alternativas descartadas:*
- **Service orquesta (leer → decidir → llamar a `sumar`/`crear`) con transacción a nivel service** (unit of work explícito): exigiría que el service maneje `begin/commit` y abre una ventana de carrera entre la lectura y la escritura; en Supabase no existe transacción entre llamadas HTTP separadas.
- **Métodos finos (`obtener_por_codigo`, `sumar_stock`, `insertar_movimiento`)**: no son atómicos por separado.
- Costo aceptado: la decisión sumar/reactivar/crear vive en el repositorio (en C-06, dentro de la función PL/pgSQL). El service conserva validación, normalización y la fuente de tiempo; la regla queda cubierta por tests de contrato del repositorio reutilizables contra Supabase.

### D2 — Transacción SQLite `BEGIN IMMEDIATE` y orden de escritura

`SqliteStockRepository(conn)` usa un context manager privado `_transaccion(conn)` en `sqlite_repo.py`: `conn.execute("BEGIN IMMEDIATE")` → `yield` → `conn.commit()`; ante cualquier excepción `conn.rollback()` y re-lanza.

- `BEGIN IMMEDIATE` toma el lock de escritura **antes de leer**: el segundo egreso concurrente espera (timeout por defecto de `sqlite3.connect`, 5 s), lee el stock ya descontado y se rechaza. Con `BEGIN` diferido, dos conexiones podrían leer el mismo stock.
- Defensa adicional en el egreso: `UPDATE productos SET stock = stock - ? WHERE id = ? AND activo = 1 AND stock >= ?` y verificación de `rowcount == 1` (si no, `StockInsuficiente`). El CHECK `stock >= 0` queda como última barrera.
- Orden: primero productos (UPDATE o INSERT), después `INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id)` con la fecha **explícita** (D6). Si el insert del movimiento falla (p. ej. FK de `usuario_id`), el rollback deshace también el stock/alta → atomicidad testeable **sin mocks** (Regla dura 4).
- Ingreso: `SELECT id, nombre, stock, activo FROM productos WHERE codigo = ?` → si existe: `UPDATE productos SET stock = stock + ?, activo = 1 WHERE id = ?` (`reactivado = not activo`); si no existe y `nombre is None` → `NombreRequerido` (sin escribir); si no existe → `INSERT INTO productos (codigo, nombre, stock, activo) VALUES (?, ?, ?, 1)` (`creado = True`). Luego el movimiento `ingreso` y se relee el producto.
- Egreso: `SELECT ...` → inexistente o `activo = 0` → `ProductoNoEncontrado`; `stock < cantidad` → `StockInsuficiente(disponible=stock)`; si no, UPDATE condicional + movimiento `egreso`.
- Todas las consultas parametrizadas (RN-SE-05). El contexto requiere `conn.in_transaction` falso; las conexiones por request cumplen.

*Mapeo a C-06 (no se implementa ahora):* `registrar_ingreso(p_codigo, p_cantidad, p_nombre, p_usuario_id, p_fecha timestamptz)` y `registrar_egreso(p_codigo, p_cantidad, p_usuario_id, p_fecha timestamptz)` en PL/pgSQL, con `SELECT ... FOR UPDATE` y `RAISE` con SQLSTATE propios que el repo Supabase traduce a los mismos errores de dominio.

### D3 — `StockService` (validación, normalización y reloj)

`services/stock_service.py`, `StockService(stock_repo, ahora: Callable[[], datetime] = ahora_argentina)`:

- `ingresar(codigo, cantidad, nombre, usuario_id) -> ResultadoIngreso`
- `egresar(codigo, cantidad, usuario_id) -> Producto`

Validación propia (independiente de Pydantic, Regla dura 3), lanza `DatosInvalidos(mensaje)`:
- `codigo`: `normalizar_codigo(codigo)` de `services/normalizacion.py` (compartida con D9): debe ser `str`; `strip()` y luego `upper()`; vacío → "El campo codigo es obligatorio."; > 50 caracteres (medido **después** de `upper()`, que puede alargar casos raros como `ß` → `SS`) → error.
- `cantidad`: `type(cantidad) is int` (rechaza `bool`, `float`, `str`) y `1 <= cantidad <= CANTIDAD_MAX` con `CANTIDAD_MAX = 10_000`.
- `nombre` (solo ingreso): `None` o `str`; se recorta (sin cambiar mayúsculas); vacío tras recortar → `None` (si el código no existe, el repo lanza `NombreRequerido`; si existe, se ignora); > 120 caracteres → error.
- `fecha`: el service llama a `self._ahora()` **una vez por operación que pasó la validación** y la pasa al repositorio. El reloj por defecto vive en `domain/tiempo.py` (D6); los tests inyectan `lambda: datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)`.
- `usuario_id` llega del adaptador (sesión).

*Por qué el reloj en el service y no en el repositorio:* una sola fuente de tiempo para SQLite y Supabase (la RPC recibe `p_fecha`), los tests de repositorio pasan la fecha explícita sin necesitar reloj, y el service sigue sin `sqlite3` ni FastAPI (el reloj es stdlib `datetime`).

### D4 — Errores de dominio nuevos (`domain/errors.py`)

| Error | Cuándo | HTTP |
|---|---|---|
| `DatosInvalidos(mensaje)` | validación de los services (stock y movimientos) | 422 |
| `NombreRequerido(codigo)` | ingreso de código inexistente sin nombre: "El producto 'N-02' no existe: indicá un nombre para crearlo." | 422 |
| `ProductoNoEncontrado(codigo)` | egreso de código inexistente o inactivo: "No existe un producto activo con código 'X-00'." | 404 |
| `StockInsuficiente(codigo, disponible, solicitado)` | egreso > stock: "Stock insuficiente para 'A-01': disponible 5, solicitado 6." | 409 |

Los mensajes muestran el código ya normalizado. Todos heredan de `InventarioError`. Handlers en `api/app.py` devuelven `{"detail": "<mensaje>"}` (texto). Los 422 de Pydantic también se devuelven como `{"detail": "<mensaje en español>"}` (D10): el cliente recibe **un único formato** de error.

Mensajes de `DatosInvalidos` con la misma familia de redacción que D10: "El campo codigo es obligatorio.", "El campo codigo admite hasta 50 caracteres.", "El campo nombre admite hasta 120 caracteres.", "La cantidad debe ser un entero entre 1 y 10.000.", "La fecha 'desde' debe tener formato AAAA-MM-DD.", "La fecha 'desde' (2026-02-30) no es una fecha válida.", "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19)."

*Alternativas:* 400 para nombre faltante → se elige 422 (mismo código que cualquier dato inválido). Inactivo → 409 → descartado: para el usuario un producto dado de baja "no existe" (RN-PR-03). Exceso → 422 → se elige 409 (el cuerpo es válido; choca con el estado actual), dentro de lo que admite US-005.

### D5 — Schemas Pydantic y endpoints de stock

En `api/schemas.py` (convención D10 de C-01):

```python
Cantidad = Annotated[int, Field(strict=True, gt=0, le=10_000)]

class IngresoRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad
    nombre: "str | None" = Field(default=None, max_length=120)

class EgresoRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad

class IngresoOut(ProductoOut):
    creado: bool
    reactivado: bool
```

No se usa `str_strip_whitespace` ni transformaciones en Pydantic: recorte, mayúsculas y "solo espacios" los hace el service (→ 422 con `detail` texto). `nombre: null` se acepta como ausente. Los 422 de estos modelos salen en español por el handler de D10.

Router `api/routers/stock.py` (`APIRouter(prefix="/api/stock", tags=["stock"])`), endpoints `def`, siempre **200** (también en el alta; `creado: true` lo informa). El usuario se obtiene con `usuario = Depends(get_current_user)`; la dependencia se resuelve antes que el cuerpo → sin sesión responde 401 aunque el cuerpo sea inválido. `get_stock_service(conn=Depends(get_conexion))` → `StockService(SqliteStockRepository(conn))`. Sin `id` ni `activo` en la salida.

### D6 — Fecha y usuario del movimiento (hora local de Argentina, offset fijo)

- **Zona**: `domain/tiempo.py` define `ZONA_AR = timezone(timedelta(hours=-3), "ART")` y `ahora_argentina() -> datetime` = `datetime.now(ZONA_AR).replace(microsecond=0)`. Argentina no tiene horario de verano; se evita `zoneinfo` porque en Windows exige el paquete `tzdata` (Regla dura 1: sin dependencias nuevas).
- **Generación**: la fecha la genera la **aplicación** (D3), no `CURRENT_TIMESTAMP`. El cliente no la envía ni la puede fijar.
- **Serialización** (repositorio): `fecha.astimezone(ZONA_AR).isoformat(timespec="seconds")` → `2026-11-19T15:30:00-03:00`. Convertir a `ZONA_AR` antes de formatear garantiza un único offset en todas las filas aunque se pase un `datetime` en otra zona; así el orden y los rangos textuales (D9) son correctos. Un `datetime` naive se rechaza con `ValueError` (error de programación, no de usuario).
- **Esquema**: la columna `fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP` no tiene CHECK que choque con el nuevo formato, y el default deja de usarse porque el INSERT siempre envía la fecha. **No se modifica el DDL**: cambiar default/CHECK en SQLite exige reconstruir la tabla y no aporta, dado que el único escritor es el repositorio. El default queda documentado como inerte.
- **Migración idempotente de filas legadas**: `inicializar_esquema(conn)` agrega, después del `executescript`, `UPDATE movimientos SET fecha = strftime('%Y-%m-%dT%H:%M:%S', fecha, '-3 hours') || '-03:00' WHERE fecha NOT LIKE '____-__-__T__:__:__-03:00'` y `commit`. Convierte filas `YYYY-MM-DD HH:MM:SS` (UTC de `CURRENT_TIMESTAMP`, insertadas a mano en una base existente como `prueba.db`) a hora local con offset; las filas ya normalizadas no cumplen el `WHERE`, así que correrlo N veces no cambia nada. En la práctica la tabla está vacía (C-01 no escribe movimientos); el costo es un UPDATE sin filas por arranque.
- **Postgres (C-06)**: `fecha timestamptz NOT NULL DEFAULT now()`; el texto ISO con offset se parsea tal cual (`'2026-11-19T15:30:00-03:00'::timestamptz`). Postgres devuelve `timestamptz` en la zona de la sesión (UTC en Supabase): el repo Supabase convierte a `ZONA_AR` antes de devolver. Los filtros por fecha local se expresan como rango `fecha >= '<desde>T00:00:00-03:00' AND fecha < '<hasta+1>T00:00:00-03:00'` (no `AT TIME ZONE '-03:00'`, cuyo signo POSIX está invertido).
- `usuario_id`: el de la sesión (`UsuarioAutenticado.id`), nunca del cuerpo.
- El alta vía ingreso **también** registra un movimiento `ingreso` con la cantidad inicial (RN-ST-03).
- Fuera de alcance: `created_at` de `usuarios`/`ordenes` sigue en `CURRENT_TIMESTAMP` UTC (no se expone).

### D7 — Normalización de código en MAYÚSCULAS

- `normalizar_codigo` (D3) es la **única** puerta de entrada del código: ingreso, egreso y filtro de movimientos. El repositorio recibe el código ya normalizado y no transforma (los tests de repo usan códigos en mayúsculas).
- `'rd-6204'`, `' Rd-6204 '` y `'RD-6204'` son el mismo producto `RD-6204`; un ingreso en minúsculas de un código nuevo crea el producto en mayúsculas.
- **Datos existentes**: no hay migración. Se asume que las filas de `productos` existentes tienen el código en mayúsculas (C-01 no crea productos; solo podrían existir por inserción manual). Como toda búsqueda pasa el input a mayúsculas, una fila insertada a mano en minúsculas seguiría listándose en `GET /api/inventario` pero sería inalcanzable por ingreso/egreso (un ingreso de ese código crearía otra fila en mayúsculas). Se documenta como riesgo; no se agrega CHECK (requiere reconstruir la tabla).
- Postgres (C-06): misma regla en el service; opcionalmente `CHECK (codigo = upper(codigo))` al crear la tabla nueva.

### D8 — Tests (Strict TDD, `unittest`, sin mocks de base)

- `tests/test_tiempo.py`: `ahora_argentina()` es aware, `utcoffset() == timedelta(hours=-3)`, `microsecond == 0`.
- `tests/test_sqlite_stock_repository.py` (`:memory:`, fecha explícita fija): suma, alta, reactivación, nombre requerido sin escritura, egreso parcial/total, exceso con `disponible`, inexistente/inactivo, movimientos registrados con `fecha == '2026-11-19T15:30:00-03:00'`, conversión de un `datetime` UTC a `-03:00`, rechazo de `datetime` naive, atomicidad por FK de `usuario_id` inexistente.
- Concurrencia: clase aparte sobre **archivo SQLite temporal** (dos conexiones, dos hilos con `threading.Barrier`), egreso de 3 sobre stock 5 → exactamente un `StockInsuficiente`, stock final 2, un movimiento. Excepción a `:memory:` justificada igual que D12 de C-01 (no es un mock).
- Migración de fechas legadas: `:memory:` con una fila insertada como `2026-11-19 18:30:00` → tras `inicializar_esquema` queda `2026-11-19T15:30:00-03:00`; una segunda llamada no cambia nada; una fila ya normalizada no se toca.
- `tests/test_stock_service.py` (`:memory:` + repo real + reloj fijo): recorte y mayúsculas (`'rd-6204'` crea `RD-6204`; `' a-01 '` encuentra `A-01`; `'rd-6204'` + `'Rd-6204'` → un solo producto), cantidades (`10_000` ok; `10_001`/`0`/`-1`/`2.5`/`"5"`/`True` → `DatosInvalidos`), textos, fecha del reloj inyectado en el movimiento, una validación fallida no escribe nada.
- `tests/test_sqlite_movimiento_repository.py` y `tests/test_movimientos_service.py` (`:memory:`): ver D9.
- `tests/test_errores_validacion.py`: `mensaje_validacion` con listas de errores de Pydantic reales (obtenidas validando los modelos con `ValidationError.errors()`, sin construir dicts a mano) → mensaje en español esperado por caso de D10, primer error si hay varios, fallback genérico. Los tests HTTP de login, stock y movimientos verifican `detail` string en español.
- `tests/test_api_stock.py` y `tests/test_api_movimientos.py` (`TestClient`, archivo temporal vía `tests/helpers.py`): códigos de estado, claves exactas, 401 sin sesión, OpenAPI con los siete endpoints.
- `tests/helpers.py`: `insertar_usuario(conn, username)`, `movimientos(conn)` (filas `tipo, cantidad, codigo, usuario_id, fecha` vía JOIN), `insertar_movimiento(conn, fecha, producto_id, tipo, cantidad, usuario_id)` para sembrar la bitácora, y `sembrar(ruta, productos)` movido desde `test_api_inventario.py`.
- Comando: `.venv/Scripts/python -m unittest discover -s tests -t .`. Costo PBKDF2: logins mínimos por test (igual que C-01).

### D9 — Consulta de movimientos (`GET /api/movimientos`) — resuelve PA-04

**Capability separada `consulta-movimientos`** (no dentro de `movimientos-stock`): es lectura pura sin efectos, con reglas propias (filtros, orden, datos expuestos), igual que `consulta-inventario` está separada de la escritura de stock; además `movimientos-stock` va a crecer con C-03/C-05 (órdenes y borrados) y conviene no mezclar escritura con consulta.

- **Entidad** `Movimiento` (frozen, `domain/entities.py`): `fecha: datetime` (aware, `-03:00`), `codigo`, `nombre`, `tipo`, `cantidad`, `usuario` (username).
- **Contrato** `MovimientoRepository.listar(codigo: "str | None", desde: "date | None", hasta: "date | None") -> list[Movimiento]` en `base.py`, separado de `StockRepository` (lectura vs. escritura atómica, como `ProductoRepository`).
- **SQLite** `SqliteMovimientoRepository(conn)`: `SELECT m.id, m.fecha, p.codigo, p.nombre, m.tipo, m.cantidad, u.username FROM movimientos m JOIN productos p ON p.id = m.producto_id JOIN usuarios u ON u.id = m.usuario_id` + condiciones opcionales `p.codigo = ?`, `m.fecha >= ?` (`desde.isoformat()`), `m.fecha < ?` (`(hasta + 1 día).isoformat()`) + `ORDER BY m.fecha DESC, m.id DESC`. Como todas las fechas comparten formato y offset (D6), la comparación textual equivale a comparar la fecha local y aprovecha `idx_movimientos_fecha`. **Sin filtro por `activo`**: es historia, incluye productos inactivos. Parseo con `datetime.fromisoformat`.
- **Service** `MovimientosService(movimiento_repo).listar(codigo=None, desde=None, hasta=None)` en `services/movimientos_service.py`:
  - `codigo`: `None`, vacío o solo espacios → sin filtro; si no, `normalizar_codigo` (D7; > 50 → `DatosInvalidos`). Coincidencia exacta, no parcial.
  - `desde`/`hasta`: `None` o vacío → sin límite; si no, si no cumplen `^\d{4}-\d{2}-\d{2}$` → `DatosInvalidos("La fecha 'desde' debe tener formato AAAA-MM-DD.")`; si cumplen el formato pero `date.fromisoformat` falla (p. ej. `2026-02-30`) → `DatosInvalidos("La fecha 'desde' (2026-02-30) no es una fecha válida.")` (mensaje distinto, decisión del usuario 2026-11-19); `desde > hasta` → `DatosInvalidos("La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).")`. Ambos inclusivos.
- **API** `api/routers/movimientos.py` (`APIRouter(prefix="/api/movimientos", tags=["movimientos"])`), `GET` `def`, query params `codigo`, `desde`, `hasta` como `str | None` (no `date` de Pydantic, que en modo lax acepta otros formatos): la validación de formato la hace el service → 422 con `detail` texto. `Depends(get_current_user)` → 401 sin sesión. Respuesta `list[MovimientoOut]` con `{fecha, codigo, nombre, tipo, cantidad, usuario}`; `fecha` como `datetime` serializa `2026-11-19T15:30:00-03:00`. Sin resultados → `200 []`. `get_movimientos_service(conn=Depends(get_conexion))` → `MovimientosService(SqliteMovimientoRepository(conn))`.
- **Sin paginación** en este paso: volumen chico de un taller; PA-08 queda abierta para cuando haga falta.
- **PA-04 queda resuelta** por esta decisión (consulta de movimientos con filtros por código y fechas). La actualización de `knowledge-base/10_preguntas_abiertas.md` se hace aparte (no se edita la KB en este change).

### D10 — Errores de validación en español con formato único

Decisión adicional del usuario (2026-11-19): **todo** 422 (Pydantic o dominio) responde `{"detail": "<mensaje en español>"}`, un único string legible, en lugar de la lista en inglés por defecto de FastAPI. Aplica a todos los endpoints con cuerpo o parámetros validados, incluido `POST /api/login` de C-01. El status sigue siendo 422.

- **Dónde**: solo en el adaptador (Regla dura 1). `inventario/api/errores_validacion.py` con una función pura `mensaje_validacion(errores: list[dict]) -> str` (recibe `exc.errors()`; testeable sin HTTP) y el handler `@app.exception_handler(RequestValidationError)` en `api/app.py` que devuelve `JSONResponse(status_code=422, content={"detail": mensaje_validacion(exc.errors())})`.
- **Nombre del campo**: el último elemento `str` de `loc` que no sea `body`/`query`, tal como aparece en la API (`codigo`, `nombre`, `cantidad`, `username`, `password`, `desde`, `hasta`).
- **Mapeo** (por `type` de Pydantic v2 y campo):

| Caso | Tipos Pydantic | Mensaje |
|---|---|---|
| JSON mal formado | `json_invalid` | "El cuerpo de la petición no es JSON válido." |
| Cuerpo ausente | `missing` con `loc == ("body",)` | "El cuerpo de la petición es obligatorio." |
| Cuerpo que no es objeto | `model_attributes_type`, `dict_type` | "El cuerpo de la petición debe ser un objeto JSON." |
| Cualquier error de `cantidad` (salvo faltante) | `int_type`, `int_from_float`, `greater_than`, `less_than_equal`, etc. | "La cantidad debe ser un entero entre 1 y 10.000." (misma familia que el mockup aprobado "La cantidad debe ser un entero mayor a 0.") |
| Campo faltante o vacío | `missing`, `string_too_short` | "El campo <campo> es obligatorio." |
| Texto demasiado largo | `string_too_long` (usa `ctx["max_length"]`) | "El campo <campo> admite hasta N caracteres." |
| Tipo de texto incorrecto | `string_type` | "El campo <campo> debe ser texto." |
| Fecha (`desde`/`hasta`) | cualquiera | "La fecha debe tener formato AAAA-MM-DD." (hoy las fechas llegan como `str` y las valida el service; el mapeo queda por si se tipan) |
| Otro | cualquiera | "El campo <campo> no es válido." o, sin campo, "Los datos enviados no son válidos." |

- **Varios errores → se devuelve solo el primero** de `exc.errors()` (Pydantic los ordena según la declaración de campos, así que es determinista). *Por qué no unirlos con " "*: el frontend muestra el mensaje en el modal junto al formulario; una sola frase accionable es más clara que una concatenación larga, y el usuario corrige campo por campo. El frontend igual valida todo antes de enviar (Regla dura 3), así que en uso normal el 422 es excepcional.
- **Mensajes de dominio** (`DatosInvalidos`, D4) usan la misma redacción, así el usuario ve el mismo texto venga de Pydantic o del service.
- **OpenAPI/Swagger**: schema `ErrorOut {detail: str}` en `api/schemas.py`; los routers de stock y movimientos y la ruta de login declaran `responses={422: {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"}}`. FastAPI solo agrega su `HTTPValidationError` por defecto cuando la ruta no declara 422, así que el schema publicado coincide con la respuesta real. Si en apply resultara que FastAPI igual lo agrega en alguna ruta, se documenta como limitación conocida (no afecta las respuestas reales) en vez de parchear `openapi()`.
- **Impacto en C-01**: los tests existentes de `tests/test_api_auth.py` (`test_422_por_cuerpo_invalido`, `test_422_por_longitud_excesiva`) solo verifican el status 422, no el formato de lista, así que siguen verdes; en apply se **extienden** para verificar el `detail` en español. El requirement "Rechazo de cuerpos malformados" de `api-http` se modifica (delta MODIFIED).

### Tabla de endpoints del change

| Método y ruta | Auth | Params / Body | 200 | Errores (todos `{"detail": "<texto en español>"}`) |
|---|---|---|---|---|
| `POST /api/stock/ingreso` | sesión | `IngresoRequest {codigo, cantidad, nombre?}` | `IngresoOut {codigo, nombre, stock, sin_stock, creado, reactivado}` | 401; 422 (Pydantic, `DatosInvalidos`, `NombreRequerido`) |
| `POST /api/stock/egreso` | sesión | `EgresoRequest {codigo, cantidad}` | `ProductoOut {codigo, nombre, stock, sin_stock}` | 401; 404 `ProductoNoEncontrado`; 409 `StockInsuficiente`; 422 |
| `GET /api/movimientos` | sesión | query `codigo?`, `desde?`, `hasta?` | `[{fecha, codigo, nombre, tipo, cantidad, usuario}]`, más nuevo primero | 401; 422 `DatosInvalidos` |
| `POST /api/login` (C-01, modificado) | pública | `{username, password}` | sin cambios | 422 ahora con `detail` en español (resto sin cambios) |

## UI Mockups

- Design system revision: 1 (no aplica)
- Decision: no (no UI) — 2026-11-19. Change de backend/API; `/docs` es tooling de verificación. Los modales de ingreso/egreso y la vista de movimientos llegan en C-06 con mockup gate.
- Mockups: —
- Approval: —
- Preview: —
- Visual verify: —

## Risks / Trade-offs

- [La lógica sumar/reactivar/crear vive en el repositorio] → tests de contrato del repositorio que en C-06 se reusan contra Supabase; el service mantiene validación y reloj.
- [Cookie válida de un usuario que ya no existe → FK falla → 500] → no hay baja de usuarios en v1 (PA-03).
- [`BEGIN IMMEDIATE` serializa escrituras; lock ocupado > 5 s → `sqlite3.OperationalError` → 500] → uso local de un taller chico; Postgres en C-06.
- [Overflow de `stock` en Postgres `integer` (2.147.483.647)] → tope de 10.000 por operación; harían falta > 214.000 ingresos máximos para desbordar. Aceptado.
- [Un 422 con varios errores informa solo el primero] → el usuario corrige y reintenta; el frontend valida todo antes de enviar (D10).
- [Un tipo de error de Pydantic no mapeado cae en el mensaje genérico] → fallback en español siempre presente; se agregan casos al mapeo cuando aparezcan.
- [Filas de `productos` insertadas a mano con código en minúsculas quedan inalcanzables por ingreso/egreso] → no existen en datos reales (C-01 no crea productos); documentado en D7.
- [Offset fijo `-03:00`: si Argentina volviera a adoptar horario de verano, las horas quedarían corridas] → cambio de una constante en `domain/tiempo.py`; las filas guardadas conservan su offset explícito.
- [Listado sin paginación crece sin límite] → volumen bajo; PA-08.
- [Nombre enviado para un código existente se ignora en silencio] → aprobado (decisión 3); evita renombrados accidentales.

## Migration Plan

Sin cambios de DDL. Al arrancar, `inicializar_esquema` normaliza de forma idempotente las fechas legadas de `movimientos` (D6); con la tabla vacía no hace nada. Bases locales existentes (p. ej. `prueba.db`) siguen sirviendo. Despliegue = código nuevo + tests. Rollback = quitar routers, services, repositorios, entidades, errores, schemas y tests nuevos y la línea de normalización; las filas de `movimientos` creadas o normalizadas quedan en ISO 8601 con offset, legible por cualquier versión.

## Aprobación del usuario

Revisión una por una el 2026-11-19. **El change queda aprobado para apply** (governance MEDIO).

| # | Decisión | Resultado |
|---|---|---|
| 1 | Forma del ingreso: body `{codigo, cantidad, nombre?}`; siempre 200 con `{codigo, nombre, stock, sin_stock, creado, reactivado}` | Aprobada |
| 2 | Código | **Cambiada**: recorte + MAYÚSCULAS (`str.upper()`), máx. 50; normalización en el service compartida por ingreso, egreso y filtro de movimientos (D3, D7) |
| 3 | Nombre: recortado, máx. 120; obligatorio solo para código nuevo; se ignora si el código existe | Aprobada |
| 4 | Código nuevo sin nombre → 422 con `detail` texto | Aprobada |
| 5 | Egreso sobre inexistente o inactivo → 404 | Aprobada |
| 6 | Egreso que excede → 409 con disponible y solicitado | Aprobada |
| 7 | Tope de cantidad | **Cambiada**: `Field(strict=True, gt=0, le=10_000)` → 1..10.000 por operación (D3, D5) |
| 8 | Atomicidad: una operación de repositorio con `BEGIN IMMEDIATE` + `UPDATE ... WHERE stock >= ?` | Aprobada |
| 9 | Fecha del movimiento | **Cambiada**: hora local de Argentina con offset fijo `-03:00`, generada por la aplicación con reloj inyectable en el service, ISO 8601 con segundos; normalización idempotente de filas legadas; usuario desde la sesión (D3, D6) |
| 10 | El alta vía ingreso registra un movimiento `ingreso` | Aprobada |
| 11 | Consulta de movimientos | **Cambiada**: nuevo `GET /api/movimientos` protegido con filtros `codigo`, `desde`, `hasta`; capability `consulta-movimientos`; resuelve PA-04; sin paginación (PA-08) (D9) |
| 12 | Test de concurrencia sobre archivo SQLite temporal | Aprobada |
| 13 | Errores de validación (decisión adicional) | **Nueva**: todo 422 responde `{"detail": "<mensaje en español>"}` con handler de `RequestValidationError` en `api/`; primer error si hay varios; aplica también a `POST /api/login`; OpenAPI declara `ErrorOut` para 422 (D10) |

## Ajustes post-verify (2026-11-20)

- **Límites medidos tras normalizar (HTTP)**: `IngresoRequest`/`EgresoRequest` usan `str_strip_whitespace=True`; `max_length` de `codigo` (50) y `nombre` (120) y `min_length=1` se evalúan sobre el valor recortado, igual que en el service. Los mensajes 422 no cambian.
- **Fechas legadas no interpretables**: el arranque nunca falla por ellas. `NORMALIZAR_FECHAS_SQL` solo toca filas que `strftime` sabe interpretar; las demás quedan intactas y `inicializar_esquema` registra un `WARNING` (logger `inventario`) con la cantidad. El listado de movimientos **omite** esas filas (con `WARNING` por fila) en lugar de responder 500: `Movimiento.fecha` es `datetime` y `MovimientoOut.fecha` también, así que devolver el texto crudo exigiría ensanchar el tipo en domain y API; la corrección de datos queda como tarea manual del operador.
- **Filtros de fecha de `GET /api/movimientos`**: se validan con `re.fullmatch` y `[0-9]` (sin `
` final ni dígitos Unicode).
