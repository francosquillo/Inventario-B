"""Migracion aditiva del chequeo final de ordenes (C-06i, design D6/D8)."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from inventario.repositories import sqlite_repo
from inventario.repositories.sqlite_repo import conectar, inicializar_esquema
from tests.test_sqlite_migracion_precios import TABLAS_5G, base_5g

# DDL de C-06h (datos del cliente y precios), copiado literal: ALTER TABLE por columna.
_PRECIO = (
    "INTEGER CHECK (precio_centavos IS NULL OR (typeof(precio_centavos) = 'integer' "
    "AND precio_centavos BETWEEN 0 AND 99999999999))"
)
ALTERS_5H = (
    "ALTER TABLE ordenes ADD COLUMN cliente TEXT CHECK (cliente IS NULL OR length(trim(cliente)) BETWEEN 1 AND 80)",
    "ALTER TABLE ordenes ADD COLUMN celular TEXT CHECK (celular IS NULL OR length(celular) BETWEEN 6 AND 20)",
    "ALTER TABLE ordenes ADD COLUMN casco TEXT CHECK (casco IS NULL OR length(trim(casco)) BETWEEN 1 AND 60)",
    "ALTER TABLE ordenes ADD COLUMN motor TEXT CHECK (motor IS NULL OR length(trim(motor)) BETWEEN 1 AND 60)",
    "ALTER TABLE ordenes ADD COLUMN trailer TEXT CHECK (trailer IS NULL OR length(trim(trailer)) BETWEEN 1 AND 60)",
    "ALTER TABLE ordenes ADD COLUMN fecha_ingreso TEXT CHECK (fecha_ingreso IS NULL OR "
    "(date(fecha_ingreso) IS NOT NULL AND fecha_ingreso = date(fecha_ingreso)))",
    "ALTER TABLE ordenes ADD COLUMN fecha_egreso TEXT CHECK (fecha_egreso IS NULL OR "
    "(date(fecha_egreso) IS NOT NULL AND fecha_egreso = date(fecha_egreso) "
    "AND (fecha_ingreso IS NULL OR fecha_egreso >= fecha_ingreso)))",
    f"ALTER TABLE orden_items ADD COLUMN precio_centavos {_PRECIO}",
    f"ALTER TABLE orden_procesos ADD COLUMN precio_centavos {_PRECIO}",
    f"ALTER TABLE orden_servicio ADD COLUMN precio_centavos {_PRECIO}",
)


def base_5h(ruta=":memory:"):
    conn = base_5g(ruta)
    for sql in ALTERS_5H:
        conn.execute(sql)
    conn.execute("UPDATE ordenes SET cliente = 'Juan Pérez', fecha_ingreso = '2026-11-26' WHERE id = 1")
    conn.execute("UPDATE orden_items SET precio_centavos = 1200000 WHERE orden_id = 1")
    conn.execute("UPDATE orden_procesos SET precio_centavos = 1500000 WHERE orden_id = 1 AND posicion = 1")
    conn.execute("UPDATE orden_servicio SET precio_centavos = 4500000 WHERE orden_id = 1")
    conn.commit()
    return conn


def contenido(conn):
    """Todas las filas de todas las tablas de la base C-06h (todas las columnas)."""
    return {
        t: [tuple(f) for f in conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in TABLAS_5G
    }


def existe(conn, tabla):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone() is not None


class MigracionChequeoFinalTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_5h()
        self.addCleanup(self.conn.close)

    def test_crea_la_tabla_vacia_y_las_ordenes_quedan_sin_chequeo(self):
        self.assertFalse(existe(self.conn, "orden_chequeo_final"))
        inicializar_esquema(self.conn)
        self.assertTrue(existe(self.conn, "orden_chequeo_final"))
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM orden_chequeo_final").fetchone()[0], 0
        )
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0], 2)

    def test_filas_existentes_quedan_identicas_en_todas_las_tablas(self):
        antes = contenido(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(contenido(self.conn), antes)

    def test_tres_arranques_conservan_una_orden_con_chequeo(self):
        inicializar_esquema(self.conn)
        self.conn.execute(
            "INSERT INTO orden_chequeo_final (orden_id, clave, precio_centavos) "
            "VALUES (1, 'combustible', 800000)"
        )
        self.conn.commit()
        antes = contenido(self.conn)
        inicializar_esquema(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(contenido(self.conn), antes)
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT * FROM orden_chequeo_final")],
            [(1, "combustible", 800000)],
        )

    def test_loguea_una_sola_vez_si_la_base_existia(self):
        with self.assertLogs("inventario", level="INFO") as cm:
            inicializar_esquema(self.conn)
        self.assertEqual(
            sum("chequeo final" in m and "2 orden(es)" in m for m in cm.output), 1
        )
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(self.conn)

    def test_integridad_referencial_sin_violaciones(self):
        inicializar_esquema(self.conn)
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")


class MigracionChequeoFinalFallaTest(unittest.TestCase):
    def test_falla_en_el_create_no_deja_la_tabla_y_la_excepcion_sube(self):
        conn = base_5h()
        self.addCleanup(conn.close)
        antes = contenido(conn)
        with mock.patch.object(
            sqlite_repo, "_CREAR_CHEQUEO_FINAL_SQL", "CREATE TABLE orden_chequeo_final ("
        ):
            with self.assertRaises(sqlite3.OperationalError):
                inicializar_esquema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertFalse(existe(conn, "orden_chequeo_final"))
        self.assertEqual(contenido(conn), antes)
        inicializar_esquema(conn)  # el reintento posterior funciona
        self.assertTrue(existe(conn, "orden_chequeo_final"))


class BaseNuevaChequeoFinalTest(unittest.TestCase):
    def test_base_nueva_tiene_la_tabla_y_no_loguea_migracion(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(conn)
        self.assertTrue(existe(conn, "orden_chequeo_final"))


class MigracionChequeoFinalArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "5h.db")
        conn = base_5h(ruta)
        antes = contenido(conn)
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertTrue(existe(conn, "orden_chequeo_final"))
        self.assertEqual(contenido(conn), antes)


if __name__ == "__main__":
    unittest.main()
