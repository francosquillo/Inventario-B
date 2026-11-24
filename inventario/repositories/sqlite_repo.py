"""Implementación SQLite del esquema y de los repositorios."""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from itertools import groupby

from inventario.domain.entities import (
    Faltante,
    ItemOrden,
    Movimiento,
    Orden,
    Producto,
    ProductoEnOrdenes,
    ProductoUsado,
    Reintegro,
    ResultadoBorradoOrden,
    ResultadoIngreso,
    ResultadoModificacion,
    Usuario,
)
from inventario.domain.errors import (
    NombreRequerido,
    OrdenDuplicada,
    OrdenNoEncontrada,
    ProductoDuplicado,
    ProductoNoEncontrado,
    ProductosInexistentes,
    ProductosNoEncontrados,
    StockInsuficiente,
    StockInsuficienteOrden,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.base import (
    MovimientoRepository,
    OrdenRepository,
    ProductoRepository,
    StockRepository,
    UsuarioRepository,
)

log = logging.getLogger("inventario")

# Columnas de `movimientos` (D4). Se comparte entre el esquema y la tabla destino de la
# migracion, para que ambos no diverjan.
_MOVIMIENTOS_COLUMNAS = """
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso', 'ajuste')),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    stock_anterior INTEGER CHECK (
        stock_anterior IS NULL
        OR (typeof(stock_anterior) = 'integer' AND stock_anterior >= 0)),
    stock_nuevo INTEGER CHECK (
        stock_nuevo IS NULL
        OR (typeof(stock_nuevo) = 'integer' AND stock_nuevo >= 0)),
    CHECK (((tipo = 'ajuste') = (stock_anterior IS NOT NULL))
           AND ((tipo = 'ajuste') = (stock_nuevo IS NOT NULL))),
    CHECK (tipo <> 'ajuste'
           OR (stock_nuevo <> stock_anterior
               AND cantidad = abs(stock_nuevo - stock_anterior)))
"""

_ESQUEMA_PLANTILLA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    stock INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(stock) = 'integer' AND stock >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ordenes (
    id INTEGER PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    fecha TEXT NOT NULL CHECK (date(fecha) IS NOT NULL AND fecha = date(fecha)),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orden_items (
    orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    PRIMARY KEY (orden_id, producto_id)
);

{movimientos}

CREATE INDEX IF NOT EXISTS idx_ordenes_fecha ON ordenes (fecha);
CREATE INDEX IF NOT EXISTS idx_orden_items_producto ON orden_items (producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos (producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos (fecha);
"""

CREAR_MOVIMIENTOS_SQL = "CREATE TABLE movimientos (" + _MOVIMIENTOS_COLUMNAS + ")"
ESQUEMA_SQL = _ESQUEMA_PLANTILLA.replace(
    "{movimientos}", CREAR_MOVIMIENTOS_SQL.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS") + ";"
)


# Filas legadas (CURRENT_TIMESTAMP, UTC, 'YYYY-MM-DD HH:MM:SS') pasan a hora local con
# offset. Las ya normalizadas no cumplen el WHERE, asi que es idempotente (D6).
# Las filas cuya fecha strftime no puede interpretar se dejan intactas (se avisa al arrancar).
_FECHA_LOCAL = "strftime('%Y-%m-%dT%H:%M:%S', fecha, '-3 hours')"
_NO_NORMALIZADA = "fecha NOT LIKE '____-__-__T__:__:__-03:00'"
NORMALIZAR_FECHAS_SQL = (
    "UPDATE movimientos "
    f"SET fecha = {_FECHA_LOCAL} || '-03:00' "
    f"WHERE {_NO_NORMALIZADA} AND {_FECHA_LOCAL} IS NOT NULL"
)
CONTAR_FECHAS_NO_PARSEABLES_SQL = (
    f"SELECT COUNT(*) FROM movimientos WHERE {_NO_NORMALIZADA} AND {_FECHA_LOCAL} IS NULL"
)


def conectar(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Migracion de `movimientos` de C-01..C-06 (sin ajuste ni stock_anterior/stock_nuevo), D4.
_COLUMNAS_COPIADAS = "id, fecha, producto_id, tipo, cantidad, usuario_id"
_SQL_COPIAR_MOVIMIENTOS = (
    f"INSERT INTO movimientos_nueva ({_COLUMNAS_COPIADAS}) "
    f"SELECT {_COLUMNAS_COPIADAS} FROM movimientos"
)
_SQL_INDICES_MOVIMIENTOS = (
    "CREATE INDEX idx_movimientos_producto ON movimientos (producto_id)",
    "CREATE INDEX idx_movimientos_fecha ON movimientos (fecha)",
)


def _migrar_movimientos(conn):
    """Reconstruye `movimientos` con el CHECK de `tipo` ampliado y las columnas nuevas.

    Idempotente: no hace nada si la tabla ya tiene `stock_anterior`. Todo en una
    transaccion: ante cualquier error se revierte y la excepcion sube (la base queda
    como estaba). Ninguna tabla referencia a `movimientos`, asi que no hace falta
    desactivar las claves foraneas.
    """
    columnas = {f["name"] for f in conn.execute("PRAGMA table_info(movimientos)")}
    if "stock_anterior" in columnas:
        return
    with _transaccion(conn):
        antes = conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
        conn.execute(CREAR_MOVIMIENTOS_SQL.replace("movimientos", "movimientos_nueva", 1))
        conn.execute(_SQL_COPIAR_MOVIMIENTOS)
        conn.execute("DROP TABLE movimientos")
        conn.execute("ALTER TABLE movimientos_nueva RENAME TO movimientos")
        for sql in _SQL_INDICES_MOVIMIENTOS:
            conn.execute(sql)
        if conn.execute("PRAGMA foreign_key_check(movimientos)").fetchall():
            raise sqlite3.IntegrityError("La migracion de movimientos viola claves foraneas.")
        despues = conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0]
        if despues != antes:
            raise sqlite3.IntegrityError(
                f"La migracion de movimientos perdio filas ({antes} antes, {despues} despues)."
            )
    log.info("Migrada la tabla movimientos (%d fila(s) conservadas).", antes)


def inicializar_esquema(conn):
    conn.executescript(ESQUEMA_SQL)
    _migrar_movimientos(conn)
    conn.execute(NORMALIZAR_FECHAS_SQL)
    sin_parsear = conn.execute(CONTAR_FECHAS_NO_PARSEABLES_SQL).fetchone()[0]
    if sin_parsear:
        log.warning(
            "%d movimiento(s) con fecha no interpretable quedaron sin normalizar.", sin_parsear
        )
    conn.commit()


def _a_usuario(fila):
    return Usuario(
        id=fila["id"],
        username=fila["username"],
        password_hash=fila["password_hash"],
        salt=fila["salt"],
    )


def _a_producto(fila):
    return Producto(
        id=fila["id"],
        codigo=fila["codigo"],
        nombre=fila["nombre"],
        stock=fila["stock"],
        activo=bool(fila["activo"]),
    )


class SqliteUsuarioRepository(UsuarioRepository):
    def __init__(self, conn):
        self._conn = conn

    def obtener_por_username(self, username):
        fila = self._conn.execute(
            "SELECT id, username, password_hash, salt FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()
        return _a_usuario(fila) if fila else None

    def obtener_por_id(self, usuario_id):
        fila = self._conn.execute(
            "SELECT id, username, password_hash, salt FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        return _a_usuario(fila) if fila else None

    def crear(self, username, password_hash, salt):
        cur = self._conn.execute(
            "INSERT INTO usuarios (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt),
        )
        self._conn.commit()
        return Usuario(cur.lastrowid, username, password_hash, salt)


class SqliteProductoRepository(ProductoRepository):
    def __init__(self, conn):
        self._conn = conn

    def listar_activos(self):
        filas = self._conn.execute(
            "SELECT id, codigo, nombre, stock, activo FROM productos WHERE activo = 1"
        ).fetchall()
        return [_a_producto(f) for f in filas]

    def listar_inactivos(self):
        filas = self._conn.execute(
            "SELECT id, codigo, nombre, stock, activo FROM productos "
            "WHERE activo = 0 ORDER BY codigo"
        ).fetchall()
        return [_a_producto(f) for f in filas]

    def dar_de_baja(self, codigo):
        with _transaccion(self._conn):
            cur = self._conn.execute(_SQL_BAJA_PRODUCTO, (codigo,))
            if cur.rowcount != 1:  # inexistente o ya inactivo
                raise ProductoNoEncontrado(codigo)
            fila = self._conn.execute(_SQL_PRODUCTO_POR_CODIGO, (codigo,)).fetchone()
        return _a_producto(fila)


# --- Stock atomico (D1/D2) ---
_SQL_PRODUCTO_POR_CODIGO = "SELECT id, codigo, nombre, stock, activo FROM productos WHERE codigo = ?"
_SQL_PRODUCTO_POR_ID = "SELECT id, codigo, nombre, stock, activo FROM productos WHERE id = ?"
_SQL_BAJA_PRODUCTO = "UPDATE productos SET activo = 0 WHERE codigo = ? AND activo = 1"
_SQL_SUMAR_Y_ACTIVAR = "UPDATE productos SET stock = stock + ?, activo = 1 WHERE id = ?"
_SQL_ALTA = "INSERT INTO productos (codigo, nombre, stock, activo) VALUES (?, ?, ?, 1)"
_SQL_ALTA_ACTIVO = "INSERT INTO productos (codigo, nombre, stock, activo) VALUES (?, ?, ?, 1)"
_SQL_REACTIVAR_ALTA = "UPDATE productos SET nombre = ?, stock = ?, activo = 1 WHERE id = ?"
_SQL_PRODUCTOS_POR_CODIGOS_TODOS = (
    "SELECT id, codigo, nombre, stock, activo FROM productos WHERE codigo IN ({})"
)
_SQL_ACTUALIZAR_LINEA = "UPDATE productos SET nombre = ?, stock = ?, activo = ? WHERE id = ?"
_SQL_RESTAR = (
    "UPDATE productos SET stock = stock - ? WHERE id = ? AND activo = 1 AND stock >= ?"
)
_SQL_MOVIMIENTO = (
    "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
    "VALUES (?, ?, ?, ?, ?)"
)
_SQL_MOVIMIENTO_AJUSTE = (
    "INSERT INTO movimientos "
    "(fecha, producto_id, tipo, cantidad, usuario_id, stock_anterior, stock_nuevo) "
    "VALUES (?, ?, 'ajuste', ?, ?, ?, ?)"
)


def _registrar_ajuste(conn, texto_fecha, producto_id, anterior, nuevo, usuario_id):
    conn.execute(
        _SQL_MOVIMIENTO_AJUSTE,
        (texto_fecha, producto_id, abs(nuevo - anterior), usuario_id, anterior, nuevo),
    )


def _fecha_a_texto(fecha):
    """ISO 8601 con segundos y offset -03:00 (un unico formato en toda la tabla)."""
    if fecha.tzinfo is None:
        raise ValueError("La fecha del movimiento debe tener zona horaria.")
    return fecha.astimezone(ZONA_AR).isoformat(timespec="seconds")


@contextmanager
def _transaccion(conn):
    """BEGIN IMMEDIATE: toma el lock de escritura antes de leer (sin carreras de stock)."""
    if conn.in_transaction:
        # No se confirma en silencio: un DML previo de la misma conexion quedaria
        # confirmado aunque esta operacion falle, rompiendo el todo o nada.
        raise RuntimeError(
            "La conexión tiene una transacción pendiente; "
            "no se puede iniciar una operación atómica."
        )
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


class SqliteStockRepository(StockRepository):
    def __init__(self, conn):
        self._conn = conn

    def registrar_ingreso(self, codigo, cantidad, nombre, usuario_id, fecha):
        texto_fecha = _fecha_a_texto(fecha)
        with _transaccion(self._conn):
            fila = self._conn.execute(_SQL_PRODUCTO_POR_CODIGO, (codigo,)).fetchone()
            creado = reactivado = False
            if fila is not None:
                producto_id = fila["id"]
                reactivado = not fila["activo"]
                self._conn.execute(_SQL_SUMAR_Y_ACTIVAR, (cantidad, producto_id))
            elif nombre is None:
                raise NombreRequerido(codigo)
            else:
                creado = True
                producto_id = self._conn.execute(
                    _SQL_ALTA, (codigo, nombre, cantidad)
                ).lastrowid
            self._conn.execute(
                _SQL_MOVIMIENTO, (texto_fecha, producto_id, "ingreso", cantidad, usuario_id)
            )
            producto = _a_producto(self._conn.execute(_SQL_PRODUCTO_POR_ID, (producto_id,)).fetchone())
        return ResultadoIngreso(producto=producto, creado=creado, reactivado=reactivado)

    def registrar_egreso(self, codigo, cantidad, usuario_id, fecha):
        texto_fecha = _fecha_a_texto(fecha)
        with _transaccion(self._conn):
            fila = self._conn.execute(_SQL_PRODUCTO_POR_CODIGO, (codigo,)).fetchone()
            if fila is None or not fila["activo"]:
                raise ProductoNoEncontrado(codigo)
            if fila["stock"] < cantidad:
                raise StockInsuficiente(codigo, fila["stock"], cantidad)
            cur = self._conn.execute(_SQL_RESTAR, (cantidad, fila["id"], cantidad))
            if cur.rowcount != 1:
                raise StockInsuficiente(codigo, fila["stock"], cantidad)
            self._conn.execute(
                _SQL_MOVIMIENTO, (texto_fecha, fila["id"], "egreso", cantidad, usuario_id)
            )
            producto = _a_producto(self._conn.execute(_SQL_PRODUCTO_POR_ID, (fila["id"],)).fetchone())
        return producto

    def dar_de_alta(self, codigo, nombre, stock, usuario_id, fecha):
        texto_fecha = _fecha_a_texto(fecha)
        with _transaccion(self._conn):
            fila = self._conn.execute(_SQL_PRODUCTO_POR_CODIGO, (codigo,)).fetchone()
            creado = fila is None
            if creado:
                try:
                    producto_id = self._conn.execute(
                        _SQL_ALTA_ACTIVO, (codigo, nombre, stock)
                    ).lastrowid
                except sqlite3.IntegrityError:  # UNIQUE(codigo): respaldo ante una carrera
                    raise ProductoDuplicado(codigo) from None
                if stock > 0:
                    self._conn.execute(
                        _SQL_MOVIMIENTO, (texto_fecha, producto_id, "ingreso", stock, usuario_id)
                    )
            elif fila["activo"]:
                raise ProductoDuplicado(codigo)
            else:
                producto_id = fila["id"]
                self._conn.execute(_SQL_REACTIVAR_ALTA, (nombre, stock, producto_id))
                if stock != fila["stock"]:
                    _registrar_ajuste(
                        self._conn, texto_fecha, producto_id, fila["stock"], stock, usuario_id
                    )
            producto = _a_producto(
                self._conn.execute(_SQL_PRODUCTO_POR_ID, (producto_id,)).fetchone()
            )
        return ResultadoIngreso(producto=producto, creado=creado, reactivado=not creado)

    def modificar(self, lineas, usuario_id, fecha):
        texto_fecha = _fecha_a_texto(fecha)
        with _transaccion(self._conn):
            filas = self._leer_por_codigos([linea.codigo for linea in lineas])
            faltantes = [linea.codigo for linea in lineas if linea.codigo not in filas]
            if faltantes:
                raise ProductosInexistentes(faltantes)
            resultados = [
                self._aplicar_linea(linea, filas[linea.codigo], usuario_id, texto_fecha)
                for linea in lineas
            ]
        return resultados

    def _leer_por_codigos(self, codigos):
        marcas = ",".join("?" * len(codigos))
        filas = self._conn.execute(_SQL_PRODUCTOS_POR_CODIGOS_TODOS.format(marcas), codigos)
        return {f["codigo"]: f for f in filas}

    def _aplicar_linea(self, linea, fila, usuario_id, texto_fecha):
        anterior = fila["stock"]
        nuevo = linea.valor if linea.modo == "fijar" else anterior + linea.valor
        nombre = linea.nombre if linea.nombre and linea.nombre != fila["nombre"] else fila["nombre"]
        cambia_stock = nuevo != anterior
        # Un dado de baja solo se reactiva si el stock cambia y queda > 0 (decision 9).
        reactivado = (not fila["activo"]) and cambia_stock and nuevo > 0
        if cambia_stock or nombre != fila["nombre"] or reactivado:
            self._conn.execute(
                _SQL_ACTUALIZAR_LINEA, (nombre, nuevo, 1 if (fila["activo"] or reactivado) else 0, fila["id"])
            )
        if cambia_stock:
            if linea.modo == "sumar":
                self._conn.execute(
                    _SQL_MOVIMIENTO, (texto_fecha, fila["id"], "ingreso", linea.valor, usuario_id)
                )
            else:
                _registrar_ajuste(self._conn, texto_fecha, fila["id"], anterior, nuevo, usuario_id)
        return ResultadoModificacion(
            codigo=fila["codigo"],
            nombre=nombre,
            stock=nuevo,
            modo=linea.modo,
            stock_anterior=anterior,
            nombre_anterior=fila["nombre"],
            reactivado=reactivado,
        )


# --- Consulta de movimientos (D9) ---
_SQL_MOVIMIENTOS = (
    "SELECT m.id, m.fecha, p.codigo, p.nombre, m.tipo, m.cantidad, u.username, "
    "m.stock_anterior, m.stock_nuevo "
    "FROM movimientos m "
    "JOIN productos p ON p.id = m.producto_id "
    "JOIN usuarios u ON u.id = m.usuario_id"
)
_ORDEN_MOVIMIENTOS = " ORDER BY m.fecha DESC, m.id DESC"


def _a_movimiento(fila):
    return Movimiento(
        fecha=datetime.fromisoformat(fila["fecha"]),
        codigo=fila["codigo"],
        nombre=fila["nombre"],
        tipo=fila["tipo"],
        cantidad=fila["cantidad"],
        usuario=fila["username"],
        stock_anterior=fila["stock_anterior"],
        stock_nuevo=fila["stock_nuevo"],
    )


class SqliteMovimientoRepository(MovimientoRepository):
    def __init__(self, conn):
        self._conn = conn

    def listar(self, codigo, desde, hasta):
        """Mas nuevo primero. Fechas locales inclusivas; texto ISO con offset unico."""
        condiciones, parametros = [], []
        if codigo is not None:
            condiciones.append("p.codigo = ?")
            parametros.append(codigo)
        if desde is not None:
            condiciones.append("m.fecha >= ?")
            parametros.append(desde.isoformat())
        if hasta is not None:
            condiciones.append("m.fecha < ?")
            parametros.append((hasta + timedelta(days=1)).isoformat())
        sql = _SQL_MOVIMIENTOS
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        filas = self._conn.execute(sql + _ORDEN_MOVIMIENTOS, parametros).fetchall()
        movimientos = []
        for fila in filas:
            try:
                movimientos.append(_a_movimiento(fila))
            except ValueError:
                log.warning(
                    "Movimiento %s omitido del listado: fecha no interpretable (%r).",
                    fila["id"],
                    fila["fecha"],
                )
        return movimientos


# --- Alta de ordenes (D1/D2) ---
_SQL_ORDEN_EXISTE = "SELECT 1 FROM ordenes WHERE numero = ?"
_SQL_PRODUCTOS_POR_CODIGOS = (
    "SELECT id, codigo, stock FROM productos WHERE activo = 1 AND codigo IN ({})"
)
_SQL_ALTA_ORDEN = "INSERT INTO ordenes (numero, fecha, usuario_id, created_at) VALUES (?, ?, ?, ?)"
_SQL_ALTA_ITEM = "INSERT INTO orden_items (orden_id, producto_id, cantidad) VALUES (?, ?, ?)"

_SQL_LISTAR_ORDENES = (
    "SELECT o.id, o.numero, o.fecha, u.username, p.codigo, p.nombre, i.cantidad "
    "FROM ordenes o "
    "JOIN usuarios u ON u.id = o.usuario_id "
    "LEFT JOIN orden_items i ON i.orden_id = o.id "
    "LEFT JOIN productos p ON p.id = i.producto_id"
)
_ORDEN_LISTAR_ORDENES = " ORDER BY o.fecha DESC, o.id DESC, p.codigo"

# --- Borrado de ordenes (D2) ---
_SQL_LINEAS_ORDEN = (
    "SELECT i.cantidad, p.id, p.codigo, p.nombre, p.stock, p.activo "
    "FROM orden_items i LEFT JOIN productos p ON p.id = i.producto_id "
    "WHERE i.orden_id = ? ORDER BY p.codigo"
)
_SQL_BORRAR_ITEMS = "DELETE FROM orden_items WHERE orden_id = ?"
_SQL_BORRAR_ORDEN = "DELETE FROM ordenes WHERE id = ?"


def _a_ordenes(filas):
    """Agrupa las filas del JOIN (contiguas por orden) en entidades `Orden`."""
    ordenes = []
    for _, grupo in groupby(filas, key=lambda f: f["id"]):
        lineas = list(grupo)
        cabecera = lineas[0]
        ordenes.append(
            Orden(
                id=cabecera["id"],
                numero=cabecera["numero"],
                fecha=date.fromisoformat(cabecera["fecha"]),
                usuario=cabecera["username"],
                items=tuple(
                    ItemOrden(f["codigo"], f["nombre"], f["cantidad"])
                    for f in lineas
                    if f["codigo"] is not None
                ),
            )
        )
    return ordenes


# Reporte: COUNT(*) = ordenes por producto (la PK (orden_id, producto_id) garantiza una linea por orden).
_SQL_REPORTE_EN_ORDENES = (
    "SELECT p.codigo, p.nombre, p.activo, SUM(i.cantidad) AS cantidad, COUNT(*) AS ordenes "
    "FROM orden_items i JOIN ordenes o ON o.id = i.orden_id "
    "JOIN productos p ON p.id = i.producto_id "
    "WHERE o.fecha >= ? AND o.fecha <= ?"
)
_GRUPO_REPORTE_EN_ORDENES = (
    " GROUP BY p.id, p.codigo, p.nombre, p.activo ORDER BY cantidad DESC, p.codigo"
)
_SQL_PRODUCTOS_USADOS = (
    "SELECT DISTINCT p.codigo, p.nombre, p.activo "
    "FROM orden_items i JOIN productos p ON p.id = i.producto_id ORDER BY p.codigo"
)


class SqliteOrdenRepository(OrdenRepository):
    def __init__(self, conn):
        self._conn = conn

    def crear(self, numero, fecha, items, usuario_id, creada_en):
        texto_creada = _fecha_a_texto(creada_en)
        try:
            with _transaccion(self._conn):
                orden_id = self._crear_en_transaccion(
                    numero, fecha, items, usuario_id, texto_creada
                )
                return self._leer_orden(orden_id)
        except sqlite3.IntegrityError as exc:
            # Respaldo del paso 1: el UNIQUE de ordenes.numero ante una carrera.
            if "ordenes.numero" in str(exc):
                raise OrdenDuplicada(numero) from exc
            raise

    def _crear_en_transaccion(self, numero, fecha, items, usuario_id, texto_creada):
        conn = self._conn
        if conn.execute(_SQL_ORDEN_EXISTE, (numero,)).fetchone() is not None:
            raise OrdenDuplicada(numero)
        codigos = [codigo for codigo, _ in items]
        # Solo placeholders "?": los codigos viajan como parametros, nunca en el SQL.
        sql = _SQL_PRODUCTOS_POR_CODIGOS.format(", ".join("?" * len(codigos)))
        productos = {f["codigo"]: f for f in conn.execute(sql, codigos).fetchall()}
        ausentes = [c for c in codigos if c not in productos]
        if ausentes:
            raise ProductosNoEncontrados(ausentes)
        faltantes = [
            Faltante(codigo, productos[codigo]["stock"], cantidad)
            for codigo, cantidad in items
            if productos[codigo]["stock"] < cantidad
        ]
        if faltantes:
            raise StockInsuficienteOrden(faltantes)
        orden_id = conn.execute(
            _SQL_ALTA_ORDEN, (numero, fecha.isoformat(), usuario_id, texto_creada)
        ).lastrowid
        for codigo, cantidad in items:
            producto_id = productos[codigo]["id"]
            conn.execute(_SQL_ALTA_ITEM, (orden_id, producto_id, cantidad))
            cur = conn.execute(_SQL_RESTAR, (cantidad, producto_id, cantidad))
            if cur.rowcount != 1:  # defensa en profundidad; BEGIN IMMEDIATE lo evita
                raise StockInsuficienteOrden(
                    [Faltante(codigo, productos[codigo]["stock"], cantidad)]
                )
        return orden_id

    def listar(self, numero, desde, hasta):
        condiciones, parametros = [], []
        if numero is not None:
            condiciones.append("o.numero = ?")
            parametros.append(numero)
        if desde is not None:
            condiciones.append("o.fecha >= ?")
            parametros.append(desde.isoformat())
        if hasta is not None:
            condiciones.append("o.fecha <= ?")
            parametros.append(hasta.isoformat())
        sql = _SQL_LISTAR_ORDENES
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        filas = self._conn.execute(sql + _ORDEN_LISTAR_ORDENES, parametros).fetchall()
        return _a_ordenes(filas)

    def productos_en_ordenes(self, desde, hasta, codigo):
        sql = _SQL_REPORTE_EN_ORDENES
        parametros = [desde.isoformat(), hasta.isoformat()]
        if codigo is not None:
            sql += " AND p.codigo = ?"
            parametros.append(codigo)
        filas = self._conn.execute(sql + _GRUPO_REPORTE_EN_ORDENES, parametros).fetchall()
        return [
            ProductoEnOrdenes(f["codigo"], f["nombre"], bool(f["activo"]), f["cantidad"], f["ordenes"])
            for f in filas
        ]

    def productos_usados(self):
        filas = self._conn.execute(_SQL_PRODUCTOS_USADOS).fetchall()
        return [ProductoUsado(f["codigo"], f["nombre"], bool(f["activo"])) for f in filas]

    def existe_numero(self, numero):
        return self._conn.execute(_SQL_ORDEN_EXISTE, (numero,)).fetchone() is not None

    def borrar(self, numero, reintegrar):
        with _transaccion(self._conn):
            orden = self._buscar_orden_por_numero(numero)
            if orden is None:
                raise OrdenNoEncontrada(numero)
            reintegros = self._reintegrar(orden.id) if reintegrar else ()
            self._conn.execute(_SQL_BORRAR_ITEMS, (orden.id,))
            cur = self._conn.execute(_SQL_BORRAR_ORDEN, (orden.id,))
            if cur.rowcount != 1:  # defensa en profundidad; BEGIN IMMEDIATE lo evita
                raise RuntimeError("No se pudo borrar la orden.")
        return ResultadoBorradoOrden(orden=orden, reintegrado=reintegrar, reintegros=reintegros)

    def _reintegrar(self, orden_id):
        """Suma cada cantidad al stock y reactiva; devuelve el detalle (dentro de la transaccion)."""
        reintegros = []
        for linea in self._conn.execute(_SQL_LINEAS_ORDEN, (orden_id,)).fetchall():
            if linea["id"] is None:
                raise RuntimeError("La orden tiene una línea cuyo producto ya no existe.")
            cur = self._conn.execute(_SQL_SUMAR_Y_ACTIVAR, (linea["cantidad"], linea["id"]))
            if cur.rowcount != 1:
                raise RuntimeError(f"No se pudo reintegrar el stock de '{linea['codigo']}'.")
            reintegros.append(
                Reintegro(
                    codigo=linea["codigo"],
                    nombre=linea["nombre"],
                    cantidad=linea["cantidad"],
                    stock=linea["stock"] + linea["cantidad"],
                    reactivado=not linea["activo"],
                )
            )
        return tuple(reintegros)

    def _buscar_orden_por_numero(self, numero):
        filas = self._conn.execute(
            _SQL_LISTAR_ORDENES + " WHERE o.numero = ?" + _ORDEN_LISTAR_ORDENES, (numero,)
        ).fetchall()
        return _a_ordenes(filas)[0] if filas else None

    def _leer_orden(self, orden_id):
        filas = self._conn.execute(
            _SQL_LISTAR_ORDENES + " WHERE o.id = ?" + _ORDEN_LISTAR_ORDENES, (orden_id,)
        ).fetchall()
        return _a_ordenes(filas)[0]
