"""Implementación SQLite del esquema y de los repositorios."""
import sqlite3

from inventario.domain.entities import Producto, Usuario
from inventario.repositories.base import ProductoRepository, UsuarioRepository

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


def conectar(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_esquema(conn):
    conn.executescript(ESQUEMA_SQL)
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
