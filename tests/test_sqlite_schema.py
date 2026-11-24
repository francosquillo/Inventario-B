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

    def test_crea_la_tabla_categorias(self):
        self.assertIn("categorias", self.nombres("table"))

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
            " VALUES (?, 'otro', 1, ?)",
            (self.pid, self.uid),
        )

    def insertar_mov(self, tipo, cantidad, anterior=None, nuevo=None):
        return self.conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id,"
            " stock_anterior, stock_nuevo) VALUES (?, ?, ?, ?, ?, ?)",
            (self.pid, tipo, cantidad, self.uid, anterior, nuevo),
        )

    def test_ajuste_con_anterior_y_nuevo_se_acepta(self):
        self.insertar_mov("ajuste", 3, 7, 4)
        fila = self.conn.execute(
            "SELECT tipo, cantidad, stock_anterior, stock_nuevo FROM movimientos"
        ).fetchone()
        self.assertEqual(tuple(fila), ("ajuste", 3, 7, 4))

    def test_ajuste_hacia_arriba_y_hacia_cero_se_aceptan(self):
        self.insertar_mov("ajuste", 5, 0, 5)
        self.insertar_mov("ajuste", 5, 5, 0)

    def test_ajuste_incoherente_se_rechaza(self):
        casos = {
            "sin anterior": (3, None, 4),
            "sin nuevo": (3, 7, None),
            "iguales": (1, 4, 4),
            "anterior negativo": (4, -1, 3),
            "nuevo negativo": (4, 3, -1),
            "cantidad distinta de la diferencia": (2, 7, 4),
        }
        for nombre, (cantidad, anterior, nuevo) in casos.items():
            with self.subTest(nombre):
                self.assertRechaza(
                    "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id,"
                    " stock_anterior, stock_nuevo) VALUES (?, 'ajuste', ?, ?, ?, ?)",
                    (self.pid, cantidad, self.uid, anterior, nuevo),
                )

    def test_ingreso_y_egreso_no_admiten_anterior_ni_nuevo(self):
        for tipo in ("ingreso", "egreso"):
            for anterior, nuevo in ((1, None), (None, 2), (1, 2)):
                with self.subTest(tipo=tipo, anterior=anterior, nuevo=nuevo):
                    self.assertRechaza(
                        "INSERT INTO movimientos (producto_id, tipo, cantidad, usuario_id,"
                        " stock_anterior, stock_nuevo) VALUES (?, ?, 1, ?, ?, ?)",
                        (self.pid, tipo, self.uid, anterior, nuevo),
                    )

    def test_ingreso_y_egreso_sin_anterior_ni_nuevo_se_aceptan(self):
        self.insertar_mov("ingreso", 2)
        self.insertar_mov("egreso", 1)

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


class NormalizacionFechasLegadasTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.pid = insertar_producto(self.conn, "A-01", "Tornillo", 5)

    def sembrar_fecha(self, fecha):
        self.conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
            "VALUES (?, ?, 'ingreso', 1, ?)",
            (fecha, self.pid, self.uid),
        )
        self.conn.commit()

    def fechas(self):
        return [f[0] for f in self.conn.execute("SELECT fecha FROM movimientos ORDER BY id")]

    def test_fecha_legada_utc_pasa_a_hora_local_con_offset(self):
        self.sembrar_fecha("2026-11-19 18:30:00")
        inicializar_esquema(self.conn)
        self.assertEqual(self.fechas(), ["2026-11-19T15:30:00-03:00"])

    def test_legada_cruzando_medianoche(self):
        self.sembrar_fecha("2026-11-20 01:15:00")
        inicializar_esquema(self.conn)
        self.assertEqual(self.fechas(), ["2026-11-19T22:15:00-03:00"])

    def test_fila_ya_normalizada_no_cambia(self):
        self.sembrar_fecha("2026-11-18T09:00:00-03:00")
        inicializar_esquema(self.conn)
        self.assertEqual(self.fechas(), ["2026-11-18T09:00:00-03:00"])

    def test_es_idempotente(self):
        self.sembrar_fecha("2026-11-19 18:30:00")
        self.sembrar_fecha("2026-11-18T09:00:00-03:00")
        for _ in range(3):
            inicializar_esquema(self.conn)
        self.assertEqual(
            self.fechas(), ["2026-11-19T15:30:00-03:00", "2026-11-18T09:00:00-03:00"]
        )

    def test_base_sin_movimientos_no_falla(self):
        conn = conexion_inicializada()
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 0)

    def test_fecha_no_parseable_no_rompe_el_arranque_y_se_deja_intacta(self):
        self.sembrar_fecha("basura")
        self.sembrar_fecha("2026-11-19 18:30:00")
        with self.assertLogs("inventario", level="WARNING") as logs:
            inicializar_esquema(self.conn)
        self.assertEqual(self.fechas(), ["basura", "2026-11-19T15:30:00-03:00"])
        self.assertIn("1", logs.output[0])

    def test_sin_filas_no_parseables_no_loguea_advertencia(self):
        self.sembrar_fecha("2026-11-19 18:30:00")
        with self.assertNoLogs("inventario", level="WARNING"):
            inicializar_esquema(self.conn)

    def test_fila_no_parseable_sigue_intacta_en_arranques_repetidos(self):
        self.sembrar_fecha("basura")
        with self.assertLogs("inventario", level="WARNING"):
            for _ in range(2):
                inicializar_esquema(self.conn)
        self.assertEqual(self.fechas(), ["basura"])



class CategoriasConstraintsTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.conn.execute("DELETE FROM categorias")

    def insertar(self, clave, nombre):
        return self.conn.execute(
            "INSERT INTO categorias (clave, nombre) VALUES (?, ?)", (clave, nombre)
        )

    def assertRechaza(self, clave, nombre):
        with self.assertRaises(sqlite3.IntegrityError):
            self.insertar(clave, nombre)

    def test_clave_valida(self):
        for clave in ("motor", "tren-delantero", "a1", "x" * 30):
            with self.subTest(clave=clave):
                self.insertar(clave, "N" + clave)

    def test_clave_duplicada(self):
        self.insertar("motor", "Motor")
        self.assertRechaza("motor", "Otro")

    def test_nombre_unico_sin_distinguir_mayusculas(self):
        self.insertar("aceite", "Aceite")
        self.assertRechaza("lubricante", "ACEITE")

    def test_clave_con_formato_invalido(self):
        for clave in ("Motor", "mo tor", "mo_tor", "-motor", "motor-", "mo--tor", "", "x" * 31):
            with self.subTest(clave=clave):
                self.assertRechaza(clave, "N")

    def test_nombre_vacio_o_largo(self):
        for nombre in ("", "   ", "x" * 41):
            with self.subTest(nombre=len(nombre)):
                self.assertRechaza("ok", nombre)

    def test_producto_con_categoria_inexistente(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO productos (codigo, nombre, stock, categoria_id) VALUES ('Z','Z',1,999)"
            )

    def test_producto_con_categoria_existente(self):
        cid = self.insertar("motor", "Motor").lastrowid
        self.conn.execute(
            "INSERT INTO productos (codigo, nombre, stock, categoria_id) VALUES ('Z','Z',1,?)",
            (cid,),
        )
