"""Migracion aditiva de procesos de ordenes y siembra solo al crear (C-06f, design D2/D4)."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from inventario.repositories import sqlite_repo
from inventario.repositories.sqlite_repo import conectar, inicializar_esquema

# DDL de C-06e (seis tablas, categoria_id incluida), copiado literal.
ESQUEMA_5E = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categorias (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE CHECK (
        length(clave) BETWEEN 1 AND 30
        AND clave NOT GLOB '*[^a-z0-9-]*'
        AND clave NOT GLOB '-*' AND clave NOT GLOB '*-' AND clave NOT GLOB '*--*'),
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 40)
);
CREATE TABLE productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    stock INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(stock) = 'integer' AND stock >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    categoria_id INTEGER REFERENCES categorias(id)
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
CREATE INDEX idx_ordenes_fecha ON ordenes (fecha);
CREATE INDEX idx_orden_items_producto ON orden_items (producto_id);
CREATE INDEX idx_movimientos_producto ON movimientos (producto_id);
CREATE INDEX idx_movimientos_fecha ON movimientos (fecha);
"""

TABLAS_EXISTENTES = (
    "usuarios", "categorias", "productos", "ordenes", "orden_items", "movimientos",
)


def base_5e(ruta=":memory:", categorias=True):
    conn = conectar(ruta)
    conn.executescript(ESQUEMA_5E)
    conn.execute("INSERT INTO usuarios (id, username, password_hash, salt) VALUES (1,'u','h','s')")
    if categorias:
        conn.executemany(
            "INSERT INTO categorias (id, clave, nombre) VALUES (?,?,?)",
            [(1, "motor", "Motor"), (2, "aceite", "Aceite"), (3, "filtro", "Filtro")],
        )
    conn.executemany(
        "INSERT INTO productos (id, codigo, nombre, stock, activo, categoria_id) VALUES (?,?,?,?,?,?)",
        [
            (1, "A-01", "Tornillo", 14, 1, 1 if categorias else None),
            (2, "B-02", "Tuerca", 2, 1, None),
            (3, "C-03", "Arandela", 0, 0, 3 if categorias else None),
        ],
    )
    conn.executemany(
        "INSERT INTO ordenes (id, numero, fecha, usuario_id) VALUES (?,?,?,1)",
        [(1, "OT-1", "2026-11-19"), (2, "OT-2", "2026-11-20")],
    )
    conn.executemany(
        "INSERT INTO orden_items (orden_id, producto_id, cantidad) VALUES (?,?,?)",
        [(1, 1, 2), (1, 2, 1), (2, 1, 1)],
    )
    conn.executemany(
        "INSERT INTO movimientos (id, fecha, producto_id, tipo, cantidad, usuario_id) "
        "VALUES (?,?,?,?,?,1)",
        [
            (1, "2026-11-18T09:00:00-03:00", 1, "ingreso", 10),
            (2, "2026-11-19T10:00:00-03:00", 2, "egreso", 1),
        ],
    )
    conn.commit()
    return conn


def filas(conn, tabla):
    return [tuple(f) for f in conn.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")]


def procesos(conn):
    return [tuple(f) for f in conn.execute("SELECT clave, nombre FROM procesos ORDER BY id")]


def categorias(conn):
    return [tuple(f) for f in conn.execute("SELECT clave, nombre FROM categorias ORDER BY id")]


def tablas(conn):
    return {f["name"] for f in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


SEMBRADOS = [
    ("cambio-motor", "Cambio motor"),
    ("cambio-filtro", "Cambio filtro"),
    ("limpieza", "Limpieza"),
]


class MigracionProcesosTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_5e()
        self.addCleanup(self.conn.close)

    def test_crea_procesos_sembrados_y_orden_procesos_vacia(self):
        inicializar_esquema(self.conn)
        self.assertEqual(procesos(self.conn), SEMBRADOS)
        self.assertEqual(filas(self.conn, "orden_procesos"), [])

    def test_filas_existentes_quedan_identicas(self):
        antes = {t: filas(self.conn, t) for t in TABLAS_EXISTENTES}
        inicializar_esquema(self.conn)
        for t, esperado in antes.items():
            self.assertEqual(filas(self.conn, t), esperado, t)

    def test_tres_arranques_no_duplican_ni_cambian(self):
        inicializar_esquema(self.conn)
        instantanea = (procesos(self.conn), filas(self.conn, "productos"))
        inicializar_esquema(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual((procesos(self.conn), filas(self.conn, "productos")), instantanea)

    def test_procesos_editados_se_conservan(self):
        inicializar_esquema(self.conn)
        self.conn.execute("UPDATE procesos SET nombre = 'Limpieza total' WHERE clave = 'limpieza'")
        self.conn.execute("DELETE FROM procesos WHERE clave = 'cambio-motor'")
        self.conn.execute("INSERT INTO procesos (clave, nombre) VALUES ('pintura', 'Pintura')")
        self.conn.commit()
        antes = procesos(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(procesos(self.conn), antes)

    def test_catalogo_vaciado_no_se_resiembra(self):
        inicializar_esquema(self.conn)
        self.conn.execute("DELETE FROM procesos")
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(procesos(self.conn), [])

    def test_loguea_las_ordenes_conservadas_una_sola_vez(self):
        with self.assertLogs("inventario", level="INFO") as cm:
            inicializar_esquema(self.conn)
        self.assertEqual(sum("procesos de ordenes (2 orden(es) conservadas" in m for m in cm.output), 1)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(self.conn)

    def test_orden_procesos_acepta_filas_y_sobrevive_a_otro_arranque(self):
        inicializar_esquema(self.conn)
        self.conn.execute(
            "INSERT INTO orden_procesos (orden_id, posicion, nombre, personalizado) "
            "VALUES (1, 1, 'Limpieza', 0)"
        )
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(filas(self.conn, "orden_procesos"), [(1, 1, "Limpieza", 0)])

    def test_integridad_referencial_sin_violaciones(self):
        inicializar_esquema(self.conn)
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")


class MigracionProcesosFallaTest(unittest.TestCase):
    def test_falla_en_la_siembra_no_deja_tablas_nuevas_y_sube(self):
        conn = base_5e()
        self.addCleanup(conn.close)
        antes = {t: filas(conn, t) for t in TABLAS_EXISTENTES}
        invalidos = (("Clave Mala", "Mala"),)  # viola el CHECK de formato de clave
        with mock.patch.object(sqlite_repo, "_PROCESOS_INICIALES", invalidos):
            with self.assertRaises(sqlite3.IntegrityError):
                inicializar_esquema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertNotIn("procesos", tablas(conn))
        self.assertNotIn("orden_procesos", tablas(conn))
        for t, esperado in antes.items():
            self.assertEqual(filas(conn, t), esperado, t)
        inicializar_esquema(conn)  # el reintento posterior funciona
        self.assertEqual(procesos(conn), SEMBRADOS)


class SiembraSoloAlCrearTest(unittest.TestCase):
    def test_base_nueva_siembra_categorias_y_procesos(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        self.assertEqual(
            sorted(categorias(conn)),
            [("aceite", "Aceite"), ("filtro", "Filtro"), ("motor", "Motor")],
        )
        self.assertEqual(procesos(conn), SEMBRADOS)

    def test_base_nueva_con_todo_borrado_no_resucita_al_reiniciar(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        conn.execute("DELETE FROM procesos")
        conn.execute("DELETE FROM categorias")
        conn.commit()
        inicializar_esquema(conn)
        self.assertEqual(procesos(conn), [])
        self.assertEqual(categorias(conn), [])

    def test_base_5e_con_categorias_vaciadas_no_se_resiembra(self):
        conn = base_5e(categorias=False)
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        self.assertEqual(categorias(conn), [])
        self.assertEqual(procesos(conn), SEMBRADOS)

    def test_base_5e_con_categorias_editadas_no_se_toca(self):
        conn = base_5e()
        self.addCleanup(conn.close)
        conn.execute("UPDATE categorias SET nombre = 'Motores' WHERE clave = 'motor'")
        conn.commit()
        antes = categorias(conn)
        inicializar_esquema(conn)
        self.assertEqual(categorias(conn), antes)


class MigracionProcesosArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "5e.db")
        conn = base_5e(ruta)
        antes = {t: filas(conn, t) for t in TABLAS_EXISTENTES}
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertEqual(procesos(conn), SEMBRADOS)
        for t, esperado in antes.items():
            self.assertEqual(filas(conn, t), esperado, t)
        inicializar_esquema(conn)
        self.assertEqual(procesos(conn), SEMBRADOS)


if __name__ == "__main__":
    unittest.main()
