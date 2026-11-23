"""Migracion de `movimientos` desde el esquema de C-01..C-06 (design D4)."""
import os
import shutil
import sqlite3
import tempfile
import unittest

from inventario.repositories.sqlite_repo import conectar, inicializar_esquema

# DDL de C-01..C-06, copiado literal: la migracion se prueba contra el esquema viejo real.
MOVIMIENTOS_VIEJO = """
CREATE TABLE movimientos (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
);
CREATE INDEX idx_movimientos_producto ON movimientos (producto_id);
CREATE INDEX idx_movimientos_fecha ON movimientos (fecha);
"""

BASE_VIEJA = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    stock INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(stock) = 'integer' AND stock >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
"""

FILAS = [
    (7, "2026-11-18T09:00:00-03:00", 1, "ingreso", 10, 1),
    (9, "2026-11-19 18:30:00", 2, "egreso", 3, 1),
    (12, "2026-11-19T10:00:00-03:00", 1, "ingreso", 4, 1),
]


def base_vieja(ruta=":memory:", movimientos_ddl=MOVIMIENTOS_VIEJO):
    conn = conectar(ruta)
    conn.executescript(BASE_VIEJA + movimientos_ddl)
    conn.execute(
        "INSERT INTO usuarios (id, username, password_hash, salt) VALUES (1, 'u', 'h', 's')"
    )
    conn.execute(
        "INSERT INTO productos (id, codigo, nombre, stock) VALUES (1, 'A-01', 'Tornillo', 14)"
    )
    conn.execute(
        "INSERT INTO productos (id, codigo, nombre, stock) VALUES (2, 'B-02', 'Tuerca', 2)"
    )
    conn.executemany(
        "INSERT INTO movimientos (id, fecha, producto_id, tipo, cantidad, usuario_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        FILAS,
    )
    conn.commit()
    return conn


def columnas(conn):
    return [f["name"] for f in conn.execute("PRAGMA table_info(movimientos)")]


def filas_basicas(conn):
    sql = (
        "SELECT id, fecha, producto_id, tipo, cantidad, usuario_id "
        "FROM movimientos ORDER BY id"
    )
    return [tuple(f) for f in conn.execute(sql)]


def sql_de_movimientos(conn):
    return conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'movimientos'"
    ).fetchone()[0]


def indices(conn):
    return {
        f["name"]
        for f in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'movimientos'"
        )
    }


class MigracionMovimientosTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_vieja()
        self.addCleanup(self.conn.close)

    def test_agrega_columnas_y_admite_ajuste(self):
        inicializar_esquema(self.conn)
        self.assertIn("stock_anterior", columnas(self.conn))
        self.assertIn("stock_nuevo", columnas(self.conn))
        self.conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id,"
            " stock_anterior, stock_nuevo) VALUES (1, 'ajuste', 3, 1, 7, 4)"
        )

    def test_conserva_ids_tipos_cantidades_y_usuarios(self):
        inicializar_esquema(self.conn)
        # La fecha legada (sin offset) se normaliza despues; el resto queda igual.
        esperado = [
            (7, "2026-11-18T09:00:00-03:00", 1, "ingreso", 10, 1),
            (9, "2026-11-19T15:30:00-03:00", 2, "egreso", 3, 1),
            (12, "2026-11-19T10:00:00-03:00", 1, "ingreso", 4, 1),
        ]
        self.assertEqual(filas_basicas(self.conn), esperado)

    def test_filas_viejas_quedan_sin_anterior_ni_nuevo(self):
        inicializar_esquema(self.conn)
        nulos = self.conn.execute(
            "SELECT COUNT(*) FROM movimientos"
            " WHERE stock_anterior IS NULL AND stock_nuevo IS NULL"
        ).fetchone()[0]
        self.assertEqual(nulos, 3)

    def test_no_modifica_el_stock_de_productos(self):
        inicializar_esquema(self.conn)
        stocks = [
            tuple(f) for f in self.conn.execute("SELECT codigo, stock FROM productos ORDER BY id")
        ]
        self.assertEqual(stocks, [("A-01", 14), ("B-02", 2)])

    def test_recrea_los_indices(self):
        inicializar_esquema(self.conn)
        self.assertEqual(indices(self.conn), {"idx_movimientos_producto", "idx_movimientos_fecha"})

    def test_el_esquema_nuevo_aplica_los_check_de_coherencia(self):
        inicializar_esquema(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id)"
                " VALUES (1, 'ajuste', 3, 1)"
            )

    def test_no_deja_la_conexion_en_transaccion(self):
        inicializar_esquema(self.conn)
        self.assertFalse(self.conn.in_transaction)

    def test_base_vieja_sin_filas(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(BASE_VIEJA + MOVIMIENTOS_VIEJO)
        inicializar_esquema(conn)
        self.assertIn("stock_nuevo", columnas(conn))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 0)

    def test_loguea_la_cantidad_de_filas_migradas(self):
        with self.assertLogs("inventario", level="INFO") as logs:
            inicializar_esquema(self.conn)
        self.assertTrue(any("3" in linea and "movimientos" in linea for linea in logs.output))


class IdempotenciaMigracionTest(unittest.TestCase):
    def test_inicializaciones_repetidas_no_cambian_nada(self):
        conn = base_vieja()
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id,"
            " stock_anterior, stock_nuevo)"
            " VALUES ('2026-11-20T10:00:00-03:00', 1, 'ajuste', 3, 1, 7, 4)"
        )
        conn.commit()
        antes = [tuple(f) for f in conn.execute("SELECT * FROM movimientos ORDER BY id")]
        sql_antes = sql_de_movimientos(conn)
        for _ in range(2):
            inicializar_esquema(conn)
        despues = [tuple(f) for f in conn.execute("SELECT * FROM movimientos ORDER BY id")]
        self.assertEqual(antes, despues)
        self.assertEqual(sql_antes, sql_de_movimientos(conn))

    def test_base_nueva_no_dispara_la_migracion(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(conn)
            inicializar_esquema(conn)


class FalloMigracionTest(unittest.TestCase):
    """Una base danada (sin CHECK, con cantidad 0) hace fallar la copia a mitad de camino."""

    DDL_SIN_CHECK = """
    CREATE TABLE movimientos (
        id INTEGER PRIMARY KEY,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        producto_id INTEGER NOT NULL REFERENCES productos(id),
        tipo TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
    );
    CREATE INDEX idx_movimientos_producto ON movimientos (producto_id);
    """

    def setUp(self):
        self.conn = base_vieja(movimientos_ddl=self.DDL_SIN_CHECK)
        self.addCleanup(self.conn.close)
        self.conn.execute(
            "INSERT INTO movimientos (id, fecha, producto_id, tipo, cantidad, usuario_id)"
            " VALUES (20, '2026-11-20T10:00:00-03:00', 1, 'ingreso', 0, 1)"
        )
        self.conn.commit()
        self.sql_viejo = sql_de_movimientos(self.conn)

    def test_el_error_sube_y_la_base_queda_como_estaba(self):
        with self.assertRaises(sqlite3.IntegrityError):
            inicializar_esquema(self.conn)
        self.assertFalse(self.conn.in_transaction)
        self.assertNotIn("stock_anterior", columnas(self.conn))
        self.assertEqual(sql_de_movimientos(self.conn), self.sql_viejo)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 4)

    def test_no_deja_la_tabla_temporal(self):
        with self.assertRaises(sqlite3.IntegrityError):
            inicializar_esquema(self.conn)
        existe = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'movimientos_nueva'"
        ).fetchone()[0]
        self.assertEqual(existe, 0)

    def test_tabla_temporal_preexistente_aborta_sin_tocar_datos(self):
        conn = base_vieja()
        self.addCleanup(conn.close)
        conn.execute("CREATE TABLE movimientos_nueva (x INTEGER)")
        conn.commit()
        with self.assertRaises(sqlite3.OperationalError):
            inicializar_esquema(conn)
        self.assertEqual(len(filas_basicas(conn)), 3)
        self.assertNotIn("stock_anterior", columnas(conn))


class MigracionBaseEnArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "vieja.db")
        base_vieja(ruta).close()
        conn = conectar(ruta)
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertIn("stock_nuevo", columnas(conn))
        self.assertEqual(len(filas_basicas(conn)), 3)


if __name__ == "__main__":
    unittest.main()
