"""Catalogo de procesos y procesos de ordenes en los repositorios SQLite (C-06f, grupo 3)."""
import sqlite3
import unittest
from datetime import date, datetime

from inventario.domain.entities import Proceso, ProcesoOrden
from inventario.domain.errors import ProcesoDuplicado, ProcesoNoEncontrado
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteOrdenRepository, SqliteProcesoRepository
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario

FECHA = datetime(2026, 11, 24, 10, 0, tzinfo=ZONA_AR)
DIA = date(2026, 11, 24)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.repo = SqliteProcesoRepository(self.conn)

    def filas(self):
        return [tuple(f) for f in self.conn.execute("SELECT clave, nombre FROM procesos ORDER BY id")]


class ListarTest(Base):
    def test_listar_ordenado_por_nombre(self):
        self.assertEqual(
            self.repo.listar(),
            [
                Proceso("cambio-filtro", "Cambio filtro"),
                Proceso("cambio-motor", "Cambio motor"),
                Proceso("limpieza", "Limpieza"),
            ],
        )

    def test_listar_sigue_el_nombre_no_la_clave(self):
        self.conn.execute("UPDATE procesos SET nombre = 'Zeta' WHERE clave = 'cambio-filtro'")
        self.conn.commit()
        self.assertEqual(
            [p.clave for p in self.repo.listar()], ["cambio-motor", "limpieza", "cambio-filtro"]
        )


class CrearTest(Base):
    def test_crea_y_devuelve_el_proceso(self):
        self.assertEqual(self.repo.crear("pintura", "Pintura"), Proceso("pintura", "Pintura"))
        self.assertEqual(self.repo.obtener("pintura"), Proceso("pintura", "Pintura"))

    def test_clave_duplicada(self):
        antes = self.filas()
        with self.assertRaises(ProcesoDuplicado) as cm:
            self.repo.crear("limpieza", "Otro")
        self.assertEqual((cm.exception.campo, cm.exception.valor), ("clave", "limpieza"))
        self.assertEqual(self.filas(), antes)
        self.assertFalse(self.conn.in_transaction)

    def test_nombre_duplicado_sin_distinguir_mayusculas(self):
        antes = self.filas()
        with self.assertRaises(ProcesoDuplicado) as cm:
            self.repo.crear("otra", "LIMPIEZA")
        self.assertEqual((cm.exception.campo, cm.exception.valor), ("nombre", "LIMPIEZA"))
        self.assertEqual(self.filas(), antes)

    def test_obtener_inexistente_es_none(self):
        self.assertIsNone(self.repo.obtener("nada"))


class RenombrarTest(Base):
    def test_renombra_y_conserva_la_clave(self):
        self.assertEqual(
            self.repo.renombrar("limpieza", "Limpieza total"), Proceso("limpieza", "Limpieza total")
        )
        self.assertEqual(self.repo.obtener("limpieza").nombre, "Limpieza total")

    def test_inexistente(self):
        with self.assertRaises(ProcesoNoEncontrado) as cm:
            self.repo.renombrar("nada", "X")
        self.assertEqual(cm.exception.clave, "nada")

    def test_nombre_de_otro_proceso(self):
        with self.assertRaises(ProcesoDuplicado) as cm:
            self.repo.renombrar("limpieza", "cambio motor")
        self.assertEqual(cm.exception.campo, "nombre")
        self.assertEqual(self.repo.obtener("limpieza").nombre, "Limpieza")
        self.assertFalse(self.conn.in_transaction)


class BorrarTest(Base):
    def test_borra_y_devuelve_lo_borrado(self):
        self.assertEqual(self.repo.borrar("limpieza"), Proceso("limpieza", "Limpieza"))
        self.assertIsNone(self.repo.obtener("limpieza"))
        self.assertEqual(len(self.repo.listar()), 2)

    def test_inexistente(self):
        with self.assertRaises(ProcesoNoEncontrado):
            self.repo.borrar("nada")
        self.assertEqual(len(self.repo.listar()), 3)
        self.assertFalse(self.conn.in_transaction)


class ProcesosDeOrdenBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        insertar_producto(self.conn, "B-02", "Tuerca", 50)
        self.ordenes = SqliteOrdenRepository(self.conn)
        self.catalogo = SqliteProcesoRepository(self.conn)

    def crear(self, numero="OT-1", procesos=(), items=(("A-01", 2), ("B-02", 1))):
        return self.ordenes.crear(numero, DIA, list(items), self.uid, FECHA, procesos=procesos)

    def cuenta(self, tabla):
        return self.conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


class AltaConProcesosTest(ProcesosDeOrdenBase):
    def test_guarda_con_posicion_y_devuelve_en_orden(self):
        procesos = (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True))
        orden = self.crear(procesos=procesos)
        self.assertEqual(orden.procesos, procesos)
        filas = [tuple(f) for f in self.conn.execute(
            "SELECT posicion, nombre, personalizado FROM orden_procesos ORDER BY posicion")]
        self.assertEqual(filas, [(1, "Limpieza", 0), (2, "Pulido", 1)])

    def test_sin_procesos_devuelve_tupla_vacia(self):
        self.assertEqual(self.crear().procesos, ())
        self.assertEqual(self.cuenta("orden_procesos"), 0)

    def test_el_orden_de_carga_se_conserva_aunque_no_sea_alfabetico(self):
        procesos = (ProcesoOrden("Zeta", True), ProcesoOrden("Alfa", False))
        self.assertEqual(self.crear(procesos=procesos).procesos, procesos)

    def test_falla_al_insertar_procesos_deja_todo_como_estaba(self):
        stock_antes = self.conn.execute("SELECT codigo, stock FROM productos").fetchall()
        repetidos = (ProcesoOrden("Pulido", True), ProcesoOrden("PULIDO", True))
        with self.assertRaises(sqlite3.IntegrityError):
            self.crear(procesos=repetidos)
        self.assertEqual(self.cuenta("ordenes"), 0)
        self.assertEqual(self.cuenta("orden_items"), 0)
        self.assertEqual(self.cuenta("orden_procesos"), 0)
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT codigo, stock FROM productos")],
            [tuple(f) for f in stock_antes],
        )
        self.assertFalse(self.conn.in_transaction)


class LecturaConProcesosTest(ProcesosDeOrdenBase):
    def test_listar_trae_los_procesos_de_cada_orden_sin_multiplicar_componentes(self):
        self.crear("OT-1", (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True)))
        self.crear("OT-2", (), items=(("A-01", 1),))
        por_numero = {o.numero: o for o in self.ordenes.listar(None, None, None)}
        self.assertEqual(
            por_numero["OT-1"].procesos, (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True))
        )
        self.assertEqual(len(por_numero["OT-1"].items), 2)
        self.assertEqual(por_numero["OT-2"].procesos, ())

    def test_listar_con_filtros_tambien_trae_procesos(self):
        self.crear("OT-1", (ProcesoOrden("Limpieza", False),))
        self.crear("OT-2", (ProcesoOrden("Pulido", True),))
        self.assertEqual(
            [o.procesos for o in self.ordenes.listar("OT-2", DIA, DIA)],
            [(ProcesoOrden("Pulido", True),)],
        )

    def test_listar_sin_ordenes_no_falla(self):
        self.assertEqual(self.ordenes.listar(None, None, None), [])

    def test_renombrar_o_borrar_del_catalogo_no_cambia_lo_leido(self):
        self.crear("OT-1", (ProcesoOrden("Limpieza", False),))
        self.catalogo.renombrar("limpieza", "Limpieza total")
        self.assertEqual(
            self.ordenes.listar(None, None, None)[0].procesos, (ProcesoOrden("Limpieza", False),)
        )
        self.catalogo.borrar("limpieza")
        self.assertEqual(
            self.ordenes.listar(None, None, None)[0].procesos, (ProcesoOrden("Limpieza", False),)
        )


class BorradoConProcesosTest(ProcesosDeOrdenBase):
    def setUp(self):
        super().setUp()
        self.crear("OT-1", (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True)))
        self.crear("OT-2", (ProcesoOrden("Limpieza", False),), items=(("A-01", 1),))

    def test_borrar_con_y_sin_reintegro_elimina_solo_los_procesos_de_esa_orden(self):
        for reintegrar, numero in ((True, "OT-1"), (False, "OT-2")):
            with self.subTest(reintegrar=reintegrar):
                resultado = self.ordenes.borrar(numero, reintegrar)
                self.assertTrue(resultado.orden.procesos)
        self.assertEqual(self.cuenta("orden_procesos"), 0)

    def test_la_orden_devuelta_incluye_los_procesos_y_la_otra_queda_intacta(self):
        resultado = self.ordenes.borrar("OT-1", True)
        self.assertEqual(
            resultado.orden.procesos, (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True))
        )
        restante = self.ordenes.listar(None, None, None)
        self.assertEqual([o.numero for o in restante], ["OT-2"])
        self.assertEqual(restante[0].procesos, (ProcesoOrden("Limpieza", False),))

    def test_falla_tras_borrar_los_procesos_revierte_todo(self):
        self.conn.execute(
            "CREATE TEMP TRIGGER falla BEFORE DELETE ON ordenes "
            "BEGIN SELECT RAISE(ABORT, 'falla forzada'); END"
        )
        with self.assertRaises(sqlite3.DatabaseError):
            self.ordenes.borrar("OT-1", True)
        self.assertEqual(self.cuenta("orden_procesos"), 3)
        self.assertEqual(self.cuenta("orden_items"), 3)
        self.assertEqual(
            self.conn.execute("SELECT stock FROM productos WHERE codigo='A-01'").fetchone()[0], 47
        )
        self.assertFalse(self.conn.in_transaction)


if __name__ == "__main__":
    unittest.main()
