import unittest

from inventario.repositories.sqlite_repo import SqliteProductoRepository
from inventario.services.inventario_service import InventarioService
from tests.helpers import conexion_inicializada, insertar_producto


class ListarTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.servicio = InventarioService(SqliteProductoRepository(self.conn))

    def codigos(self):
        return [p.codigo for p in self.servicio.listar()]

    def test_solo_activos(self):
        insertar_producto(self.conn, "P-001", "Uno", 1, 1)
        insertar_producto(self.conn, "P-002", "Dos", 1, 0)
        insertar_producto(self.conn, "P-003", "Tres", 1, 1)
        self.assertEqual(self.codigos(), ["P-001", "P-003"])

    def test_orden_por_codigo(self):
        for codigo in ("B-10", "A-01", "C-05"):
            insertar_producto(self.conn, codigo, "N", 1)
        self.assertEqual(self.codigos(), ["A-01", "B-10", "C-05"])

    def test_sin_stock(self):
        insertar_producto(self.conn, "P-001", "Cero", 0)
        insertar_producto(self.conn, "P-002", "Cinco", 5)
        por_codigo = {p.codigo: p for p in self.servicio.listar()}
        self.assertTrue(por_codigo["P-001"].sin_stock)
        self.assertFalse(por_codigo["P-002"].sin_stock)

    def test_vacio_y_solo_inactivos(self):
        self.assertEqual(self.servicio.listar(), [])
        insertar_producto(self.conn, "P-001", "Uno", 1, 0)
        self.assertEqual(self.servicio.listar(), [])
