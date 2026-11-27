"""Migracion de `productos` para agregar la categoria (C-06e, design D1/D2)."""
import os
import shutil
import sqlite3
import tempfile
import unittest

from inventario.repositories.sqlite_repo import conectar, inicializar_esquema

# DDL de C-06b (pre-5e), copiado literal: la migracion se prueba contra el esquema viejo real.
BASE_SIN_MOVIMIENTOS = """
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
CREATE TABLE ordenes (
    id INTEGER PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    fecha TEXT NOT NULL CHECK (date(fecha) IS NOT NULL AND fecha = date(fecha)),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE orden_items (
    orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    PRIMARY KEY (orden_id, producto_id)
);
"""

MOVIMIENTOS_6B = """
CREATE TABLE movimientos (
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
);
"""

MOVIMIENTOS_LEGADO = """
CREATE TABLE movimientos (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    cantidad INTEGER NOT NULL
        CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
);
"""

INDICES = """
CREATE INDEX idx_ordenes_fecha ON ordenes (fecha);
CREATE INDEX idx_orden_items_producto ON orden_items (producto_id);
CREATE INDEX idx_movimientos_producto ON movimientos (producto_id);
CREATE INDEX idx_movimientos_fecha ON movimientos (fecha);
"""

F1 = "2026-11-18T09:00:00-03:00"
F2 = "2026-11-19T10:00:00-03:00"


def base_vieja(ruta=":memory:", antes_de_datos=""):
    conn = conectar(ruta)
    conn.executescript(BASE_SIN_MOVIMIENTOS + MOVIMIENTOS_6B + INDICES + antes_de_datos)
    conn.execute("INSERT INTO usuarios (id, username, password_hash, salt) VALUES (1,'u','h','s')")
    conn.executemany(
        "INSERT INTO productos (id, codigo, nombre, stock, activo) VALUES (?,?,?,?,?)",
        [(1, "A-01", "Tornillo", 14, 1), (2, "B-02", "Tuerca", 2, 1), (3, "C-03", "Arandela", 0, 0)],
    )
    conn.execute("INSERT INTO ordenes (id, numero, fecha, usuario_id) VALUES (1,'OT-1','2026-11-19',1)")
    conn.executemany(
        "INSERT INTO orden_items (orden_id, producto_id, cantidad) VALUES (?,?,?)",
        [(1, 1, 2), (1, 2, 1)],
    )
    conn.executemany(
        "INSERT INTO movimientos (id, fecha, producto_id, tipo, cantidad, usuario_id,"
        " stock_anterior, stock_nuevo) VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, F1, 1, "ingreso", 10, 1, None, None),
            (2, F1, 2, "ingreso", 3, 1, None, None),
            (3, F2, 1, "egreso", 2, 1, None, None),
            (4, F2, 2, "ajuste", 1, 1, 3, 2),
        ],
    )
    conn.commit()
    return conn


def productos(conn):
    return [tuple(f) for f in conn.execute(
        "SELECT id, codigo, nombre, stock, activo FROM productos ORDER BY id")]


def tabla(conn, nombre):
    from tests.test_sqlite_migracion_procesos import filas

    return filas(conn, nombre)


def categorias(conn):
    return [tuple(f) for f in conn.execute("SELECT clave, nombre FROM categorias ORDER BY id")]


def columnas_productos(conn):
    return {f["name"] for f in conn.execute("PRAGMA table_info(productos)")}


class MigracionCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_vieja()
        self.addCleanup(self.conn.close)

    def test_agrega_categoria_id_nulo_y_conserva_las_demas_columnas(self):
        antes = productos(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(productos(self.conn), antes)
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT id, categoria_id FROM productos ORDER BY id")],
            [(1, None), (2, None), (3, None)],
        )

    def test_ordenes_items_y_movimientos_quedan_intactos(self):
        previos = {t: tabla(self.conn, t) for t in ("ordenes", "orden_items", "movimientos")}
        inicializar_esquema(self.conn)
        for t, filas in previos.items():
            self.assertEqual(tabla(self.conn, t), filas, t)

    def test_siembra_motor_aceite_filtro(self):
        inicializar_esquema(self.conn)
        self.assertEqual(
            sorted(categorias(self.conn)),
            [("aceite", "Aceite"), ("filtro", "Filtro"), ("motor", "Motor")],
        )

    def test_tres_arranques_seguidos_no_cambian_ni_duplican(self):
        inicializar_esquema(self.conn)
        snapshot = (categorias(self.conn), tabla(self.conn, "productos"))
        inicializar_esquema(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual((categorias(self.conn), tabla(self.conn, "productos")), snapshot)

    def test_categoria_asignada_despues_se_conserva(self):
        inicializar_esquema(self.conn)
        self.conn.execute(
            "UPDATE productos SET categoria_id = (SELECT id FROM categorias WHERE clave='motor')"
            " WHERE id = 1"
        )
        self.conn.commit()
        inicializar_esquema(self.conn)
        fila = self.conn.execute(
            "SELECT c.clave FROM productos p JOIN categorias c ON c.id = p.categoria_id WHERE p.id=1"
        ).fetchone()
        self.assertEqual(fila["clave"], "motor")

    def test_catalogo_editado_no_se_resiembra(self):
        inicializar_esquema(self.conn)
        self.conn.execute("UPDATE categorias SET nombre = 'Motor y transmision' WHERE clave='motor'")
        self.conn.execute("INSERT INTO categorias (clave, nombre) VALUES ('frenos', 'Frenos')")
        self.conn.commit()
        antes = categorias(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(categorias(self.conn), antes)

    def test_columna_ya_migrada_con_catalogo_vaciado_no_se_resiembra(self):
        # C-06f D2: se siembra solo al crear la tabla; lo borrado a proposito no resucita.
        inicializar_esquema(self.conn)
        self.conn.execute("DELETE FROM categorias")
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(categorias(self.conn), [])

    def test_base_con_movimientos_legados_migra_ambas_cosas(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(BASE_SIN_MOVIMIENTOS + MOVIMIENTOS_LEGADO)
        conn.execute("INSERT INTO usuarios (id, username, password_hash, salt) VALUES (1,'u','h','s')")
        conn.execute("INSERT INTO productos (id, codigo, nombre, stock) VALUES (1,'A','Tornillo',5)")
        conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id)"
            " VALUES ('2026-11-19 18:30:00', 1, 'ingreso', 5, 1)"
        )
        conn.commit()
        inicializar_esquema(conn)
        cols = {f["name"] for f in conn.execute("PRAGMA table_info(movimientos)")}
        self.assertIn("stock_anterior", cols)
        self.assertIn("categoria_id", columnas_productos(conn))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 1)
        self.assertEqual(len(categorias(conn)), 3)

    def test_clave_foranea_se_hace_cumplir_tras_migrar(self):
        inicializar_esquema(self.conn)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE productos SET categoria_id = 999 WHERE id = 1")

    def test_loguea_la_cantidad_de_productos_conservados(self):
        with self.assertLogs("inventario", level="INFO") as cm:
            inicializar_esquema(self.conn)
        self.assertTrue(any("3 producto(s)" in m for m in cm.output))


class MigracionCategoriaFallaTest(unittest.TestCase):
    def test_falla_en_la_siembra_revierte_el_alter_y_sube(self):
        # `categorias` preexistente con un trigger real que rechaza insertar: la siembra
        # falla DESPUES del ALTER; todo debe revertirse.
        conn = base_vieja(antes_de_datos="""
CREATE TABLE categorias (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TRIGGER rechaza BEFORE INSERT ON categorias
BEGIN SELECT RAISE(ABORT, 'siembra rota'); END;
""")
        self.addCleanup(conn.close)
        with self.assertRaisesRegex(sqlite3.DatabaseError, "siembra rota"):
            inicializar_esquema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertNotIn("categoria_id", columnas_productos(conn))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0], 0)
        self.assertEqual(len(productos(conn)), 3)


class MigracionCategoriaArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "vieja.db")
        conn = base_vieja(ruta)
        antes = productos(conn)
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertEqual(productos(conn), antes)
        self.assertEqual(len(categorias(conn)), 3)
        inicializar_esquema(conn)
        self.assertEqual(len(categorias(conn)), 3)


if __name__ == "__main__":
    unittest.main()
