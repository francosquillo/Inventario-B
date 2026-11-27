"""Migracion aditiva de datos del cliente y precios de ordenes (C-06h, design D1/D7/D8/D9)."""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from inventario.repositories import sqlite_repo
from inventario.repositories.sqlite_repo import conectar, inicializar_esquema
from tests.test_sqlite_migracion_procesos import TABLAS_EXISTENTES, base_5e, filas
from tests.test_sqlite_migracion_servicios import (
    ESQUEMA_5F_EXTRA,
    TABLAS_5F,
)

# DDL de C-06g (servicios generales de ordenes), copiado literal.
ESQUEMA_5G_EXTRA = """
CREATE TABLE servicios_generales (
    id INTEGER PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE CHECK (
        length(clave) BETWEEN 1 AND 30
        AND clave NOT GLOB '*[^a-z0-9-]*'
        AND clave NOT GLOB '-*' AND clave NOT GLOB '*-' AND clave NOT GLOB '*--*'),
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE servicio_chequeos (
    servicio_id INTEGER NOT NULL REFERENCES servicios_generales(id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    PRIMARY KEY (servicio_id, posicion),
    UNIQUE (servicio_id, nombre COLLATE NOCASE)
);
CREATE TABLE orden_servicio (
    orden_id INTEGER PRIMARY KEY REFERENCES ordenes(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60)
);
CREATE TABLE orden_servicio_chequeos (
    orden_id INTEGER NOT NULL REFERENCES orden_servicio(orden_id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (typeof(posicion) = 'integer' AND posicion >= 1),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) BETWEEN 1 AND 60),
    PRIMARY KEY (orden_id, posicion),
    UNIQUE (orden_id, nombre COLLATE NOCASE)
);
"""
TABLAS_5G = TABLAS_5F + (
    "servicios_generales", "servicio_chequeos", "orden_servicio", "orden_servicio_chequeos",
)
COLUMNAS_NUEVAS = {
    "ordenes": (
        "cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso",
    ),
    "orden_items": ("precio_centavos",),
    "orden_procesos": ("precio_centavos",),
    "orden_servicio": ("precio_centavos",),
}


def base_5g(ruta=":memory:"):
    conn = base_5e(ruta)
    conn.executescript(ESQUEMA_5F_EXTRA + ESQUEMA_5G_EXTRA)
    conn.executemany(
        "INSERT INTO procesos (id, clave, nombre) VALUES (?,?,?)",
        [(1, "cambio-motor", "Cambio motor"), (2, "limpieza", "Limpieza")],
    )
    conn.executemany(
        "INSERT INTO orden_procesos (orden_id, posicion, nombre, personalizado) VALUES (?,?,?,?)",
        [(1, 1, "Limpieza", 0), (1, 2, "Pulido", 1), (2, 1, "Cambio motor", 0)],
    )
    conn.execute("INSERT INTO servicios_generales (id, clave, nombre) VALUES (1, 's20', 'Servicio 20 hs')")
    conn.execute("INSERT INTO servicio_chequeos (servicio_id, posicion, nombre) VALUES (1, 1, 'Motor')")
    conn.execute("INSERT INTO orden_servicio (orden_id, nombre) VALUES (1, 'Servicio 20 hs')")
    conn.execute("INSERT INTO orden_servicio_chequeos (orden_id, posicion, nombre) VALUES (1, 1, 'Motor')")
    conn.commit()
    return conn


def columnas(conn, tabla):
    return [f["name"] for f in conn.execute(f"PRAGMA table_info({tabla})")]


def originales(conn, tabla):
    """Filas de `tabla` sin las columnas que agrega C-06h."""
    nuevas = set(COLUMNAS_NUEVAS.get(tabla, ()))
    cols = [c for c in columnas(conn, tabla) if c not in nuevas]
    return [tuple(f) for f in conn.execute(f"SELECT {', '.join(cols)} FROM {tabla} ORDER BY 1, 2")]


def snapshot(conn):
    return {t: originales(conn, t) for t in TABLAS_5G}


class MigracionPreciosTest(unittest.TestCase):
    def setUp(self):
        self.conn = base_5g()
        self.addCleanup(self.conn.close)

    def test_agrega_las_columnas_nuevas_en_null_y_conserva_la_fecha(self):
        fechas = [tuple(f) for f in self.conn.execute("SELECT id, fecha FROM ordenes ORDER BY id")]
        inicializar_esquema(self.conn)
        for tabla, nuevas in COLUMNAS_NUEVAS.items():
            for columna in nuevas:
                self.assertIn(columna, columnas(self.conn, tabla), f"{tabla}.{columna}")
                no_nulas = self.conn.execute(
                    f"SELECT COUNT(*) FROM {tabla} WHERE {columna} IS NOT NULL"
                ).fetchone()[0]
                self.assertEqual(no_nulas, 0, f"{tabla}.{columna}")
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT id, fecha FROM ordenes ORDER BY id")],
            fechas,
        )
        self.assertEqual(
            [f["name"] for f in self.conn.execute("PRAGMA table_info(ordenes)")][-7:],
            list(COLUMNAS_NUEVAS["ordenes"]),
        )

    def test_filas_existentes_quedan_identicas_en_todas_las_tablas(self):
        antes = snapshot(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(snapshot(self.conn), antes)

    def test_tres_arranques_con_datos_y_precios_los_conservan(self):
        inicializar_esquema(self.conn)
        self.conn.execute(
            "UPDATE ordenes SET cliente = 'Juan Pérez', fecha_ingreso = '2026-11-26', "
            "fecha_egreso = '2026-11-29' WHERE id = 1"
        )
        self.conn.execute("UPDATE orden_items SET precio_centavos = 1200000 WHERE orden_id = 1")
        self.conn.execute("UPDATE orden_servicio SET precio_centavos = 4500000")
        self.conn.commit()
        antes = [tuple(f) for f in self.conn.execute("SELECT * FROM ordenes ORDER BY id")]
        inicializar_esquema(self.conn)
        inicializar_esquema(self.conn)
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT * FROM ordenes ORDER BY id")], antes
        )
        self.assertEqual(
            self.conn.execute(
                "SELECT precio_centavos FROM orden_items WHERE orden_id = 1 ORDER BY producto_id"
            ).fetchall()[0][0],
            1200000,
        )
        self.assertEqual(self.conn.execute("SELECT precio_centavos FROM orden_servicio").fetchone()[0], 4500000)

    def test_base_a_medio_migrar_agrega_solo_la_columna_que_falta(self):
        inicializar_esquema(self.conn)
        # Reconstruye la tabla sin `trailer` para simular una migracion interrumpida.
        self.conn.execute("ALTER TABLE ordenes DROP COLUMN trailer")
        self.conn.execute("UPDATE ordenes SET cliente = 'Ana' WHERE id = 2")
        self.conn.commit()
        inicializar_esquema(self.conn)
        self.assertIn("trailer", columnas(self.conn, "ordenes"))
        self.assertEqual(columnas(self.conn, "ordenes").count("cliente"), 1)
        self.assertEqual(
            self.conn.execute("SELECT cliente FROM ordenes WHERE id = 2").fetchone()[0], "Ana"
        )

    def test_loguea_las_ordenes_conservadas_una_sola_vez(self):
        with self.assertLogs("inventario", level="INFO") as cm:
            inicializar_esquema(self.conn)
        self.assertEqual(
            sum("datos del cliente y precios" in m and "2 orden(es)" in m for m in cm.output), 1
        )
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(self.conn)

    def test_integridad_referencial_sin_violaciones(self):
        inicializar_esquema(self.conn)
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")


class MigracionPreciosFallaTest(unittest.TestCase):
    def test_falla_en_la_cuarta_columna_no_deja_ninguna_nueva_y_sube(self):
        conn = base_5g()
        self.addCleanup(conn.close)
        antes = snapshot(conn)
        columnas_antes = {t: columnas(conn, t) for t in COLUMNAS_NUEVAS}
        rota = list(sqlite_repo._COLUMNAS_NUEVAS)
        rota[3] = ("ordenes", "motor", "TEXT CHECK (")  # DDL invalido en la cuarta columna
        with mock.patch.object(sqlite_repo, "_COLUMNAS_NUEVAS", tuple(rota)):
            with self.assertRaises(sqlite3.OperationalError):
                inicializar_esquema(conn)
        self.assertFalse(conn.in_transaction)
        for t, cols in columnas_antes.items():
            self.assertEqual(columnas(conn, t), cols, t)
        self.assertEqual(snapshot(conn), antes)
        inicializar_esquema(conn)  # el reintento posterior funciona
        self.assertIn("motor", columnas(conn, "ordenes"))


class BaseNuevaTest(unittest.TestCase):
    def test_base_nueva_tiene_las_columnas_y_no_loguea_migracion(self):
        conn = conectar(":memory:")
        self.addCleanup(conn.close)
        with self.assertNoLogs("inventario", level="INFO"):
            inicializar_esquema(conn)
        for tabla, nuevas in COLUMNAS_NUEVAS.items():
            for columna in nuevas:
                self.assertIn(columna, columnas(conn, tabla))


class MigracionPreciosArchivoTest(unittest.TestCase):
    def test_migra_una_base_en_archivo_y_persiste(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        ruta = os.path.join(carpeta, "5g.db")
        conn = base_5g(ruta)
        antes = snapshot(conn)
        inicializar_esquema(conn)
        conn.close()
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        self.assertIn("fecha_egreso", columnas(conn, "ordenes"))
        self.assertEqual(snapshot(conn), antes)


if __name__ == "__main__":
    unittest.main()
