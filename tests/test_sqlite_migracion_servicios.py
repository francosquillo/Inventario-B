"""Migracion aditiva de servicios generales y siembra solo al crear (C-06g, design D3/D4)."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from inventario.repositories import sqlite_repo
from inventario.repositories.sqlite_repo import conectar, inicializar_esquema
from tests.test_sqlite_migracion_procesos import TABLAS_EXISTENTES, base_5e, filas

# DDL de C-06f (procesos y orden_procesos), copiado literal.
ESQUEMA_5F_EXTRA = """
CREATE TABLE procesos (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE CHECK (
        length(clave) BETWEEN 1 AND 30
        AND clave NOT GLOB '*[^a-z0-9-]*'
        AND clave NOT GLOB '-*' AND clave NOT GLOB '*-' AND clave NOT GLOB '*--*'),
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE orden_procesos (
    orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    personalizado INTEGER NOT NULL CHECK (personalizado IN (0, 1)),
    PRIMARY KEY (orden_id, posicion),
    UNIQUE (orden_id, nombre COLLATE NOCASE)
);
"""
TABLAS_5F = TABLAS_EXISTENTES + ("procesos", "orden_procesos")
TABLAS_NUEVAS = (
    "servicios_generales", "servicio_chequeos", "orden_servicio", "orden_servicio_chequeos",
)
CHEQUEOS = [
    (1, "Chequeo de motor"),
    (2, "Chequeo de combustible"),
    (3, "Chequeo eléctrico"),
]


def base_5f(ruta=":memory:"):
    conn = base_5e(ruta)
    conn.executescript(ESQUEMA_5F_EXTRA)
    conn.executemany(
        "INSERT INTO procesos (id, clave, nombre) VALUES (?,?,?)",
        [(1, "cambio-motor", "Cambio motor"), (2, "limpieza", "Limpieza")],
    )
    conn.executemany(
        "INSERT INTO orden_procesos (orden_id, posicion, nombre, personalizado) VALUES (?,?,?,?)",
        [(1, 1, "Limpieza", 0), (1, 2, "Pulido", 1), (2, 1, "Cambio motor", 0)],
    )
    conn.commit()
    return conn


def tablas(conn):
    return {f["name"] for f in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def servicios(conn):
    return [tuple(f) for f in conn.execute("SELECT clave, nombre FROM servicios_generales ORDER BY id")]


def chequeos(conn):
    return [tuple(f) for f in conn.execute(
        "SELECT posicion, nombre FROM servicio_chequeos ORDER BY servicio_id, posicion"
    )]


class MigracionServiciosTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_5f()
        self.addCleanup(self.conn.close)

    def test_crea_el_catalogo_sembrado_y_las_tablas_de_ordenes_vacias(self):
        inicializar_esquema(self.conn)
        self.assertEqual(servicios(self.conn), [("servicio-20-hs", "Servicio 20 hs")])
        self.assertEqual(chequeos(self.conn), CHEQUEOS)
        self.assertEqual(filas(self.conn, "orden_servicio"), [])
        self.assertEqual(filas(self.conn, "orden_servicio_chequeos"), [])

    def test_las_ordenes_existentes_quedan_sin_servicio(self):
        inicializar_esquema(self.conn)
        total = self.conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
        self.assertEqual(total, 2)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orden_servicio").fetchone()[0], 0)

    def test_filas_existentes_quedan_identicas(self):
        antes = {t: filas(self.conn, t) for t in TABLAS_5F}
        inicializar_esquema(self.conn)
        for t, esperado in antes.items():
            self.assertEqual(filas(self.conn, t), esperado, t)

    def test_tres_arranques_no_duplican_ni_cambian(self):
        inicializar_esquema(self.conn)
        instantanea = (servicios(self.conn), chequeos(self.conn), filas(self.conn, "productos"))
        inicializar_esquema(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(
            (servicios(self.conn), chequeos(self.conn), filas(self.conn, "productos")), instantanea
        )

    def test_catalogo_vaciado_no_se_resiembra(self):
        inicializar_esquema(self.conn)
        self.conn.execute("DELETE FROM servicios_generales")
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(servicios(self.conn), [])
        self.assertEqual(chequeos(self.conn), [])

    def test_chequeos_reemplazados_no_se_resiembran(self):
        inicializar_esquema(self.conn)
        self.conn.execute("DELETE FROM servicio_chequeos")
        self.conn.execute(
            "INSERT INTO servicio_chequeos (servicio_id, posicion, nombre) "
            "SELECT id, 1, 'Chequeo de batería' FROM servicios_generales"
        )
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(chequeos(self.conn), [(1, "Chequeo de batería")])

    def test_loguea_las_ordenes_conservadas_una_sola_vez(self):
        with self.assertLogs("inventario", level="INFO") as cm:
            inicializar_esquema(self.conn)
        self.assertEqual(sum("servicios generales" in m and "2 orden(es)" in m for m in cm.output), 1)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(self.conn)

    def test_integridad_referencial_sin_violaciones(self):
        inicializar_esquema(self.conn)
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_orden_servicio_acepta_filas_y_sobrevive_a_otro_arranque(self):
        inicializar_esquema(self.conn)
        self.conn.execute("INSERT INTO orden_servicio (orden_id, nombre) VALUES (1, 'Servicio 20 hs')")
        self.conn.execute(
            "INSERT INTO orden_servicio_chequeos (orden_id, posicion, nombre) VALUES (1, 1, 'A')"
        )
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertEqual(filas(self.conn, "orden_servicio"), [(1, "Servicio 20 hs")])
        self.assertEqual(filas(self.conn, "orden_servicio_chequeos"), [(1, 1, "A")])


class MigracionServiciosFallaTest(unittest.TestCase):
    def test_falla_en_la_siembra_no_deja_tablas_nuevas_y_sube(self):
        conn = base_5f()
        self.addCleanup(conn.close)
        antes = {t: filas(conn, t) for t in TABLAS_5F}
        invalidos = (("Clave Mala", "Mala", ("A",)),)  # viola el CHECK de formato de clave
        with mock.patch.object(sqlite_repo, "_SERVICIOS_INICIALES", invalidos):
            with self.assertRaises(sqlite3.IntegrityError):
                inicializar_esquema(conn)
        self.assertFalse(conn.in_transaction)
        for t in TABLAS_NUEVAS:
            self.assertNotIn(t, tablas(conn))
        for t, esperado in antes.items():
            self.assertEqual(filas(conn, t), esperado, t)
        inicializar_esquema(conn)  # el reintento posterior funciona
        self.assertEqual(servicios(conn), [("servicio-20-hs", "Servicio 20 hs")])

    def test_falla_en_un_chequeo_revierte_las_cuatro_tablas(self):
        conn = base_5f()
        self.addCleanup(conn.close)
        repetidos = (("ok", "Ok", ("A", "a")),)  # viola UNIQUE (servicio_id, nombre NOCASE)
        with mock.patch.object(sqlite_repo, "_SERVICIOS_INICIALES", repetidos):
            with self.assertRaises(sqlite3.IntegrityError):
                inicializar_esquema(conn)
        for t in TABLAS_NUEVAS:
            self.assertNotIn(t, tablas(conn))


class SiembraSoloAlCrearTest(unittest.TestCase):
    def test_base_nueva_siembra_el_servicio(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        self.assertEqual(servicios(conn), [("servicio-20-hs", "Servicio 20 hs")])
        self.assertEqual(chequeos(conn), CHEQUEOS)

    def test_base_nueva_no_loguea_migracion(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(conn)

    def test_base_nueva_con_todo_borrado_no_resucita_al_reiniciar(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        inicializar_esquema(conn)
        conn.execute("DELETE FROM servicios_generales")
        conn.commit()
        inicializar_esquema(conn)
        self.assertEqual(servicios(conn), [])


class MigracionServiciosArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "5f.db")
        conn = base_5f(ruta)
        antes = {t: filas(conn, t) for t in TABLAS_5F}
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertEqual(servicios(conn), [("servicio-20-hs", "Servicio 20 hs")])
        for t, esperado in antes.items():
            self.assertEqual(filas(conn, t), esperado, t)
        inicializar_esquema(conn)
        self.assertEqual(servicios(conn), [("servicio-20-hs", "Servicio 20 hs")])


if __name__ == "__main__":
    unittest.main()
