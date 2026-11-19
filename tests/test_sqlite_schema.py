import sqlite3
import unittest

from inventario.repositories.sqlite_repo import conectar, inicializar_esquema
from tests.helpers import conexion_inicializada, insertar_producto


def insertar_usuario(conn, username="u1"):
    cur = conn.execute(
        "INSERT INTO usuarios (username, password_hash, salt) VALUES (?, 'h', 's')",
        (username,),
    )
    return cur.lastrowid


class EsquemaTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)

    def nombres(self, tipo):
        filas = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", (tipo,)
        ).fetchall()
        return {f["name"] for f in filas}

    def test_crea_las_cinco_tablas(self):
        esperadas = {"usuarios", "productos", "ordenes", "orden_items", "movimientos"}
        self.assertTrue(esperadas <= self.nombres("table"))

    def test_crea_los_indices(self):
        esperados = {
            "idx_ordenes_fecha",
            "idx_orden_items_producto",
            "idx_movimientos_producto",
            "idx_movimientos_fecha",
        }
        self.assertTrue(esperados <= self.nombres("index"))

    def test_claves_foraneas_activas(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


class ConstraintsTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.pid = insertar_producto(self.conn, "P-001", "Tornillo", 5)

    def assertRechaza(self, sql, params=()):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(sql, params)

    def test_stock_numerico_en_texto_se_normaliza_a_entero(self):
        self.conn.execute(
            "INSERT INTO productos (codigo, nombre, stock) VALUES ('N', 'N', '7')"
        )
        fila = self.conn.execute(
            "SELECT stock, typeof(stock) AS t FROM productos WHERE codigo = 'N'"
        ).fetchone()
        self.assertEqual((fila["stock"], fila["t"]), (7, "integer"))

    def test_codigo_duplicado(self):
        self.assertRechaza(
            "INSERT INTO productos (codigo, nombre, stock) VALUES ('P-001', 'Otro', 1)"
        )

    def test_stock_negativo_o_no_entero(self):
        # '5' no se prueba: la afinidad INTEGER de SQLite lo convierte a 5 (valido).
        for stock in (-1, 5.5, "abc"):
            with self.subTest(stock=stock):
                self.assertRechaza(
                    "INSERT INTO productos (codigo, nombre, stock) VALUES ('X', 'N', ?)",
                    (stock,),
                )

    def test_nombre_vacio_o_espacios(self):
        for nombre in ("", "   "):
            with self.subTest(nombre=nombre):
                self.assertRechaza(
                    "INSERT INTO productos (codigo, nombre, stock) VALUES ('X', ?, 1)",
                    (nombre,),
                )

    def test_cantidad_cero_en_item_y_movimiento(self):
        self.conn.execute(
            "INSERT INTO ordenes (numero, fecha, usuario_id) VALUES ('1', '2026-01-01', ?)",
            (self.uid,),
        )
        oid = self.conn.execute("SELECT id FROM ordenes").fetchone()["id"]
        self.assertRechaza(
            "INSERT INTO orden_items (orden_id, producto_id, cantidad) VALUES (?, ?, 0)",
            (oid, self.pid),
        )
        self.assertRechaza(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id)"
            " VALUES (?, 'ingreso', 0, ?)",
            (self.pid, self.uid),
        )

    def test_tipo_de_movimiento_invalido(self):
        self.assertRechaza(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id)"
            " VALUES (?, 'ajuste', 1, ?)",
            (self.pid, self.uid),
        )

    def test_movimiento_con_producto_inexistente(self):
        self.assertRechaza(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id)"
            " VALUES (999, 'ingreso', 1, ?)",
            (self.uid,),
        )

    def test_fecha_de_orden_invalida(self):
        for fecha in ("2026-02-30", "2026/01/01"):
            with self.subTest(fecha=fecha):
                self.assertRechaza(
                    "INSERT INTO ordenes (numero, fecha, usuario_id) VALUES ('9', ?, ?)",
                    (fecha, self.uid),
                )

    def test_fecha_de_orden_valida(self):
        self.conn.execute(
            "INSERT INTO ordenes (numero, fecha, usuario_id) VALUES ('9', '2026-02-28', ?)",
            (self.uid,),
        )

    def test_username_duplicado(self):
        self.assertRechaza(
            "INSERT INTO usuarios (username, password_hash, salt) VALUES ('u1', 'h', 's')"
        )

    def test_cascade_borra_items_al_borrar_orden(self):
        self.conn.execute(
            "INSERT INTO ordenes (numero, fecha, usuario_id) VALUES ('1', '2026-01-01', ?)",
            (self.uid,),
        )
        oid = self.conn.execute("SELECT id FROM ordenes").fetchone()["id"]
        self.conn.execute(
            "INSERT INTO orden_items (orden_id, producto_id, cantidad) VALUES (?, ?, 2)",
            (oid, self.pid),
        )
        self.conn.execute("DELETE FROM ordenes WHERE id = ?", (oid,))
        n = self.conn.execute("SELECT COUNT(*) FROM orden_items").fetchone()[0]
        self.assertEqual(n, 0)


class IdempotenciaTest(unittest.TestCase):
    def test_reinicializar_no_pierde_datos(self):
        conn = conexion_inicializada()
        self.addCleanup(conn.close)
        insertar_producto(conn, "P-001", "Tornillo", 5)
        inicializar_esquema(conn)
        fila = conn.execute("SELECT codigo, stock FROM productos").fetchall()
        self.assertEqual([(f["codigo"], f["stock"]) for f in fila], [("P-001", 5)])

    def test_conectar_devuelve_row_factory(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        self.assertIs(conn.row_factory, sqlite3.Row)
