"""Catalogo de servicios generales y servicio de ordenes en los repositorios SQLite (C-06g, grupo 3)."""
import sqlite3
import unittest
from datetime import date, datetime
from unittest import mock

from inventario.domain.entities import ProcesoOrden, ServicioGeneral, ServicioOrden
from inventario.domain.errors import ServicioGeneralDuplicado, ServicioGeneralNoEncontrado
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories import sqlite_repo
from inventario.repositories.sqlite_repo import (
    SqliteOrdenRepository,
    SqliteServicioGeneralRepository,
)
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario

FECHA = datetime(2026, 11, 24, 10, 0, tzinfo=ZONA_AR)
DIA = date(2026, 11, 24)
CHEQUEOS_20 = ("Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico")
VEINTE = ServicioGeneral("servicio-20-hs", "Servicio 20 hs", CHEQUEOS_20)
SERVICIO = ServicioOrden("Servicio 20 hs", CHEQUEOS_20)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.repo = SqliteServicioGeneralRepository(self.conn)

    def cuenta(self, tabla):
        return self.conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def filas(self):
        return (
            [tuple(f) for f in self.conn.execute(
                "SELECT clave, nombre FROM servicios_generales ORDER BY id")],
            [tuple(f) for f in self.conn.execute(
                "SELECT servicio_id, posicion, nombre FROM servicio_chequeos ORDER BY 1, 2")],
        )


class ListarTest(Base):
    def test_lista_el_servicio_sembrado_con_sus_chequeos_en_orden(self):
        self.assertEqual(self.repo.listar(), [VEINTE])

    def test_ordenado_por_nombre_sin_distinguir_mayusculas(self):
        self.repo.crear("servicio-100-hs", "Servicio 100 hs", ("A",))
        self.repo.crear("alfa", "alfa", ("B", "C"))
        self.assertEqual(
            [(s.clave, s.chequeos) for s in self.repo.listar()],
            [("alfa", ("B", "C")), ("servicio-100-hs", ("A",)), ("servicio-20-hs", CHEQUEOS_20)],
        )


class CrearTest(Base):
    def test_crea_con_posiciones_y_devuelve_el_servicio(self):
        creado = self.repo.crear(
            "servicio-100-hs", "Servicio 100 hs", ("Cambio de aceite", "Zeta", "Alfa")
        )
        self.assertEqual(creado.chequeos, ("Cambio de aceite", "Zeta", "Alfa"))
        self.assertEqual(self.repo.obtener("servicio-100-hs"), creado)
        posiciones = [tuple(f) for f in self.conn.execute(
            "SELECT posicion, c.nombre FROM servicio_chequeos c JOIN servicios_generales s "
            "ON s.id = c.servicio_id WHERE s.clave = 'servicio-100-hs' ORDER BY posicion")]
        self.assertEqual(posiciones, [(1, "Cambio de aceite"), (2, "Zeta"), (3, "Alfa")])

    def test_clave_duplicada(self):
        antes = self.filas()
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.repo.crear("servicio-20-hs", "Otro", ("A",))
        self.assertEqual((cm.exception.campo, cm.exception.valor), ("clave", "servicio-20-hs"))
        self.assertEqual(self.filas(), antes)
        self.assertFalse(self.conn.in_transaction)

    def test_nombre_duplicado_sin_distinguir_mayusculas_no_deja_chequeos_huerfanos(self):
        antes = self.filas()
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.repo.crear("otra", "SERVICIO 20 HS", ("A",))
        self.assertEqual((cm.exception.campo, cm.exception.valor), ("nombre", "SERVICIO 20 HS"))
        self.assertEqual(self.filas(), antes)

    def test_obtener_inexistente_es_none(self):
        self.assertIsNone(self.repo.obtener("nada"))


class ModificarTest(Base):
    def test_solo_nombre_conserva_los_chequeos(self):
        r = self.repo.modificar("servicio-20-hs", nombre="Service 20 horas")
        self.assertEqual(r, ServicioGeneral("servicio-20-hs", "Service 20 horas", CHEQUEOS_20))

    def test_solo_chequeos_reemplaza_la_lista_completa(self):
        r = self.repo.modificar(
            "servicio-20-hs", chequeos=("Chequeo de motor", "Chequeo de batería")
        )
        self.assertEqual(
            r,
            ServicioGeneral(
                "servicio-20-hs", "Servicio 20 hs", ("Chequeo de motor", "Chequeo de batería")
            ),
        )
        self.assertEqual(self.cuenta("servicio_chequeos"), 2)

    def test_ambos(self):
        r = self.repo.modificar("servicio-20-hs", nombre="Nuevo", chequeos=("Uno",))
        self.assertEqual(r, ServicioGeneral("servicio-20-hs", "Nuevo", ("Uno",)))

    def test_inexistente(self):
        with self.assertRaises(ServicioGeneralNoEncontrado) as cm:
            self.repo.modificar("nada", nombre="X")
        self.assertEqual(cm.exception.clave, "nada")
        self.assertFalse(self.conn.in_transaction)

    def test_nombre_de_otro_servicio_no_cambia_nada(self):
        self.repo.crear("servicio-100-hs", "Servicio 100 hs", ("A",))
        antes = self.filas()
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.repo.modificar("servicio-20-hs", nombre="servicio 100 HS", chequeos=("Z",))
        self.assertEqual(cm.exception.campo, "nombre")
        self.assertEqual(self.filas(), antes)
        self.assertFalse(self.conn.in_transaction)

    def test_el_mismo_nombre_no_es_duplicado(self):
        self.repo.modificar("servicio-20-hs", nombre="Servicio 20 hs", chequeos=("Z",))
        self.assertEqual(self.repo.obtener("servicio-20-hs").chequeos, ("Z",))

    def test_falla_al_insertar_chequeos_deja_nombre_y_chequeos_anteriores(self):
        antes = self.filas()
        with self.assertRaises(sqlite3.IntegrityError):
            # El service valida repetidos; la BD es la red (UNIQUE NOCASE por servicio).
            self.repo.modificar("servicio-20-hs", nombre="Cambiado", chequeos=("A", "a"))
        self.assertEqual(self.filas(), antes)
        self.assertFalse(self.conn.in_transaction)


class BorrarTest(Base):
    def test_devuelve_lo_borrado_con_chequeos_y_no_deja_filas(self):
        self.assertEqual(self.repo.borrar("servicio-20-hs"), VEINTE)
        self.assertIsNone(self.repo.obtener("servicio-20-hs"))
        self.assertEqual(self.cuenta("servicio_chequeos"), 0)

    def test_inexistente(self):
        with self.assertRaises(ServicioGeneralNoEncontrado):
            self.repo.borrar("nada")
        self.assertEqual(self.repo.listar(), [VEINTE])
        self.assertFalse(self.conn.in_transaction)


class OrdenesBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        insertar_producto(self.conn, "B-02", "Tuerca", 50)
        self.ordenes = SqliteOrdenRepository(self.conn)
        self.catalogo = SqliteServicioGeneralRepository(self.conn)

    def crear(self, numero="OT-1", servicio=None, procesos=(), items=(("A-01", 2), ("B-02", 1))):
        return self.ordenes.crear(
            numero, DIA, list(items), self.uid, FECHA, procesos=procesos, servicio=servicio
        )

    def cuenta(self, tabla):
        return self.conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def stock(self):
        return [tuple(f) for f in self.conn.execute("SELECT codigo, stock FROM productos")]


class AltaConServicioTest(OrdenesBase):
    def test_guarda_servicio_y_chequeos_en_orden_y_la_orden_lo_trae(self):
        orden = self.crear(servicio=SERVICIO)
        self.assertEqual(orden.servicio, SERVICIO)
        self.assertEqual(
            [tuple(f) for f in self.conn.execute("SELECT nombre FROM orden_servicio")],
            [("Servicio 20 hs",)],
        )
        self.assertEqual(
            [tuple(f) for f in self.conn.execute(
                "SELECT posicion, nombre FROM orden_servicio_chequeos ORDER BY posicion")],
            [(1, "Chequeo de motor"), (2, "Chequeo de combustible"), (3, "Chequeo eléctrico")],
        )

    def test_el_orden_de_los_chequeos_se_conserva_aunque_no_sea_alfabetico(self):
        servicio = ServicioOrden("S", ("Zeta", "Alfa"))
        self.assertEqual(self.crear(servicio=servicio).servicio, servicio)

    def test_sin_servicio_es_none_y_no_guarda_filas(self):
        self.assertIsNone(self.crear().servicio)
        self.assertEqual(self.cuenta("orden_servicio"), 0)
        self.assertEqual(self.cuenta("orden_servicio_chequeos"), 0)

    def test_servicio_y_procesos_juntos(self):
        procesos = (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True))
        orden = self.crear(servicio=SERVICIO, procesos=procesos)
        self.assertEqual((orden.servicio, orden.procesos, len(orden.items)), (SERVICIO, procesos, 2))

    def test_falla_al_insertar_los_chequeos_deja_todo_como_estaba(self):
        stock_antes = self.stock()
        repetidos = ServicioOrden("S", ("Pulido", "PULIDO"))  # viola el UNIQUE NOCASE
        with self.assertRaises(sqlite3.IntegrityError):
            self.crear(servicio=repetidos, procesos=(ProcesoOrden("Limpieza", False),))
        for tabla in (
            "ordenes", "orden_items", "orden_procesos", "orden_servicio", "orden_servicio_chequeos",
        ):
            self.assertEqual(self.cuenta(tabla), 0, tabla)
        self.assertEqual(self.stock(), stock_antes)
        self.assertFalse(self.conn.in_transaction)


class LecturaConServicioTest(OrdenesBase):
    def test_listar_trae_el_servicio_de_cada_orden_sin_multiplicar_filas(self):
        procesos = (ProcesoOrden("Limpieza", False), ProcesoOrden("Pulido", True))
        self.crear("OT-1", SERVICIO, procesos=procesos)
        self.crear("OT-2", None, items=(("A-01", 1),))
        por_numero = {o.numero: o for o in self.ordenes.listar(None, None, None)}
        self.assertEqual(por_numero["OT-1"].servicio, SERVICIO)
        self.assertEqual(len(por_numero["OT-1"].items), 2)
        self.assertEqual(len(por_numero["OT-1"].procesos), 2)
        self.assertIsNone(por_numero["OT-2"].servicio)

    def test_listar_con_filtros_tambien_trae_el_servicio(self):
        self.crear("OT-1", SERVICIO)
        self.crear("OT-2", ServicioOrden("Otro", ("X",)))
        self.assertEqual(
            [o.servicio for o in self.ordenes.listar("OT-2", DIA, DIA)],
            [ServicioOrden("Otro", ("X",))],
        )

    def test_modificar_o_borrar_el_catalogo_no_cambia_lo_leido(self):
        self.crear("OT-1", SERVICIO)
        self.catalogo.modificar("servicio-20-hs", nombre="Renombrado", chequeos=("Uno",))
        self.assertEqual(self.ordenes.listar(None, None, None)[0].servicio, SERVICIO)
        self.catalogo.borrar("servicio-20-hs")
        self.assertEqual(self.ordenes.listar(None, None, None)[0].servicio, SERVICIO)


class BorradoConServicioTest(OrdenesBase):
    def setUp(self):
        super().setUp()
        self.crear("OT-1", SERVICIO)
        self.crear("OT-2", SERVICIO, items=(("A-01", 1),))

    def test_borrar_con_y_sin_reintegro_elimina_servicio_y_chequeos_de_esa_orden(self):
        for reintegrar, numero in ((True, "OT-1"), (False, "OT-2")):
            with self.subTest(reintegrar=reintegrar):
                resultado = self.ordenes.borrar(numero, reintegrar)
                self.assertEqual(resultado.orden.servicio, SERVICIO)
        self.assertEqual(self.cuenta("orden_servicio"), 0)
        self.assertEqual(self.cuenta("orden_servicio_chequeos"), 0)

    def test_la_otra_orden_con_el_mismo_servicio_queda_intacta(self):
        self.ordenes.borrar("OT-1", True)
        self.assertEqual(self.cuenta("orden_servicio"), 1)
        self.assertEqual(self.cuenta("orden_servicio_chequeos"), 3)
        self.assertEqual(self.ordenes.listar("OT-2", None, None)[0].servicio, SERVICIO)

    def test_falla_tras_borrar_el_servicio_revierte_todo(self):
        stock_antes = self.stock()
        with mock.patch.object(sqlite_repo, "_SQL_BORRAR_ORDEN", "DELETE FROM tabla_que_no_existe"):
            with self.assertRaises(sqlite3.OperationalError):
                self.ordenes.borrar("OT-1", True)
        self.assertEqual(self.cuenta("ordenes"), 2)
        self.assertEqual(self.cuenta("orden_servicio"), 2)
        self.assertEqual(self.cuenta("orden_servicio_chequeos"), 6)
        self.assertEqual(self.stock(), stock_antes)
        self.assertFalse(self.conn.in_transaction)


if __name__ == "__main__":
    unittest.main()
