"""Implementación SQLite del esquema y de los repositorios."""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from inventario.domain.entities import Movimiento, Producto, ResultadoIngreso, Usuario
from inventario.domain.errors import NombreRequerido, ProductoNoEncontrado, StockInsuficiente
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.base import (
    MovimientoRepository,
    ProductoRepository,
    StockRepository,
    UsuarioRepository,
)

log = logging.getLogger("inventario")

ESQUEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_ordenes_fecha ON ordenes (fecha);
CREATE INDEX IF NOT EXISTS idx_orden_items_producto ON orden_items (producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos (producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos (fecha);
"""


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


def inicializar_esquema(conn):
    conn.executescript(ESQUEMA_SQL)
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


# --- Stock atomico (D1/D2) ---
_SQL_PRODUCTO_POR_CODIGO = "SELECT id, codigo, nombre, stock, activo FROM productos WHERE codigo = ?"
_SQL_PRODUCTO_POR_ID = "SELECT id, codigo, nombre, stock, activo FROM productos WHERE id = ?"
_SQL_SUMAR_Y_ACTIVAR = "UPDATE productos SET stock = stock + ?, activo = 1 WHERE id = ?"
_SQL_ALTA = "INSERT INTO productos (codigo, nombre, stock, activo) VALUES (?, ?, ?, 1)"
_SQL_RESTAR = (
    "UPDATE productos SET stock = stock - ? WHERE id = ? AND activo = 1 AND stock >= ?"
)
_SQL_MOVIMIENTO = (
    "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
    "VALUES (?, ?, ?, ?, ?)"
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
        conn.commit()  # cierra escrituras previas pendientes de la misma conexion
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


# --- Consulta de movimientos (D9) ---
_SQL_MOVIMIENTOS = (
    "SELECT m.id, m.fecha, p.codigo, p.nombre, m.tipo, m.cantidad, u.username "
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
