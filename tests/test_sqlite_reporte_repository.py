"""Reporte de productos en ordenes (spec reporte-ordenes): SQLite real en memoria."""
import unittest
from datetime import date, datetime

from inventario.domain.entities import ProductoEnOrdenes, ProductoUsado
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteOrdenRepository
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario

CREADA = datetime(2026, 11, 1, 9, 0, tzinfo=ZONA_AR)
NOV = (date(2026, 11, 1), date(2026, 11, 30))


class ReporteRepoBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteOrdenRepository(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 1000)
        insertar_producto(self.conn, "B-02", "Tuerca", 1000)
        insertar_producto(self.conn, "C-99", "Viejo", 1000)

    def orden(self, numero, fecha, items):
        self.repo.crear(numero, fecha, list(items), self.uid, CREADA)

    def baja(self, codigo):
        self.conn.execute("UPDATE productos SET activo = 0 WHERE codigo = ?", (codigo,))
        self.conn.commit()

    def reporte(self, desde=NOV[0], hasta=NOV[1], codigo=None):
        return self.repo.productos_en_ordenes(desde, hasta, codigo)

    def estado(self):
        return {
            t: [tuple(f) for f in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()]
            for t in ("productos", "ordenes", "orden_items", "movimientos")
        }


class ProductosEnOrdenesTest(ReporteRepoBase):
    def test_suma_cantidades_y_cuenta_ordenes(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 3), ("B-02", 1)])
        self.orden("OT-2", date(2026, 11, 6), [("A-01", 2)])
        self.assertEqual(self.reporte(), [
            ProductoEnOrdenes("A-01", "Tornillo", True, 5, 2),
            ProductoEnOrdenes("B-02", "Tuerca", True, 1, 1),
        ])

    def test_bordes_inclusivos_y_fuera_de_rango(self):
        self.orden("OT-1", date(2026, 11, 1), [("A-01", 1)])
        self.orden("OT-2", date(2026, 11, 30), [("A-01", 2)])
        self.orden("OT-3", date(2026, 12, 1), [("A-01", 100)])
        self.orden("OT-4", date(2026, 10, 31), [("A-01", 200)])
        self.assertEqual(self.reporte(), [ProductoEnOrdenes("A-01", "Tornillo", True, 3, 2)])

    def test_un_solo_dia(self):
        self.orden("OT-1", date(2026, 11, 10), [("A-01", 4)])
        self.orden("OT-2", date(2026, 11, 11), [("A-01", 9)])
        dia = date(2026, 11, 10)
        self.assertEqual(self.reporte(dia, dia), [ProductoEnOrdenes("A-01", "Tornillo", True, 4, 1)])

    def test_orden_por_cantidad_desc_y_empate_por_codigo(self):
        self.orden("OT-1", date(2026, 11, 5), [("B-02", 5), ("A-01", 5), ("C-99", 9)])
        self.assertEqual([f.codigo for f in self.reporte()], ["C-99", "A-01", "B-02"])

    def test_filtro_por_codigo(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 3), ("B-02", 1)])
        self.assertEqual(self.reporte(codigo="B-02"), [ProductoEnOrdenes("B-02", "Tuerca", True, 1, 1)])

    def test_codigo_sin_uso_o_inexistente_devuelve_vacio(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 3)])
        self.assertEqual(self.reporte(codigo="B-02"), [])
        self.assertEqual(self.reporte(codigo="ZZ-99"), [])

    def test_sin_ordenes_devuelve_vacio(self):
        self.assertEqual(self.reporte(), [])

    def test_producto_dado_de_baja_conserva_su_total(self):
        self.orden("OT-1", date(2026, 11, 5), [("C-99", 4), ("A-01", 1)])
        self.baja("C-99")
        self.assertEqual(self.reporte(), [
            ProductoEnOrdenes("C-99", "Viejo", False, 4, 1),
            ProductoEnOrdenes("A-01", "Tornillo", True, 1, 1),
        ])
        self.assertEqual(self.reporte(codigo="C-99"), [ProductoEnOrdenes("C-99", "Viejo", False, 4, 1)])

    def test_orden_de_otro_producto_no_suma(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 3)])
        self.orden("OT-2", date(2026, 11, 6), [("B-02", 7)])
        self.assertEqual(self.reporte(codigo="A-01"), [ProductoEnOrdenes("A-01", "Tornillo", True, 3, 1)])

    def test_solo_lectura(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 3), ("C-99", 1)])
        self.baja("C-99")
        antes = self.estado()
        self.reporte()
        self.reporte(codigo="A-01")
        self.repo.productos_usados()
        self.assertEqual(self.estado(), antes)


class ProductosUsadosTest(ReporteRepoBase):
    def test_activos_y_dados_de_baja_sin_duplicados(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 1), ("C-99", 1)])
        self.orden("OT-2", date(2026, 10, 5), [("A-01", 2)])
        self.baja("C-99")
        self.assertEqual(self.repo.productos_usados(), [
            ProductoUsado("A-01", "Tornillo", True),
            ProductoUsado("C-99", "Viejo", False),
        ])

    def test_nunca_usado_excluido_y_orden_por_codigo(self):
        self.orden("OT-1", date(2026, 11, 5), [("C-99", 1), ("A-01", 1)])
        self.assertEqual([p.codigo for p in self.repo.productos_usados()], ["A-01", "C-99"])

    def test_sin_ordenes_devuelve_vacio(self):
        self.assertEqual(self.repo.productos_usados(), [])

    def test_producto_de_orden_borrada_excluido(self):
        self.orden("OT-1", date(2026, 11, 5), [("A-01", 1)])
        self.orden("OT-2", date(2026, 11, 6), [("B-02", 1)])
        self.repo.borrar("OT-2", reintegrar=True)
        self.assertEqual([p.codigo for p in self.repo.productos_usados()], ["A-01"])


if __name__ == "__main__":
    unittest.main()
