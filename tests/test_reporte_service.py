"""ReporteService (spec reporte-ordenes): validacion de fechas y filtro, con SQLite real en memoria."""
import unittest
from datetime import date, datetime

from inventario.domain.entities import ProductoEnOrdenes, ProductoUsado
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteOrdenRepository
from inventario.services.reporte_service import ReporteService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario

HOY = datetime(2026, 11, 24, 10, 0, tzinfo=ZONA_AR)


class ReporteServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteOrdenRepository(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 1000)
        insertar_producto(self.conn, "B-02", "Tuerca", 1000)
        self.svc = ReporteService(self.repo, ahora=lambda: HOY)

    def orden(self, numero, fecha, items):
        self.repo.crear(numero, date.fromisoformat(fecha), items, self.uid, HOY)

    def assertInvalido(self, mensaje, *args, **kwargs):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.svc.productos_en_ordenes(*args, **kwargs)
        self.assertEqual(str(ctx.exception), mensaje)

    def test_desde_obligatorio(self):
        self.assertInvalido("La fecha 'desde' es obligatoria.", None, "2026-11-30")

    def test_desde_en_blanco_es_obligatorio(self):
        self.assertInvalido("La fecha 'desde' es obligatoria.", "", "2026-11-30")
        self.assertInvalido("La fecha 'desde' es obligatoria.", "   ", None)

    def test_rango_con_resultado(self):
        self.orden("OT-1", "2026-11-05", [("A-01", 3)])
        self.assertEqual(
            self.svc.productos_en_ordenes("2026-11-01", "2026-11-30"),
            [ProductoEnOrdenes("A-01", "Tornillo", True, 3, 1)],
        )

    def test_hasta_ausente_o_vacio_es_hoy(self):
        self.orden("OT-1", "2026-11-24", [("A-01", 1)])
        self.orden("OT-2", "2026-11-25", [("B-02", 1)])
        esperado = [ProductoEnOrdenes("A-01", "Tornillo", True, 1, 1)]
        self.assertEqual(self.svc.productos_en_ordenes("2026-11-01"), esperado)
        self.assertEqual(self.svc.productos_en_ordenes("2026-11-01", ""), esperado)
        self.assertEqual(self.svc.productos_en_ordenes("2026-11-01", None), esperado)

    def test_desde_futuro_sin_hasta(self):
        self.assertInvalido(
            "La fecha 'desde' (2026-12-01) no puede ser posterior a 'hasta' (2026-11-24).",
            "2026-12-01",
        )

    def test_formato_y_fechas_inexistentes(self):
        self.assertInvalido("La fecha 'desde' debe tener formato AAAA-MM-DD.", "01/11/2026")
        self.assertInvalido("La fecha 'desde' (2026-02-30) no es una fecha válida.", "2026-02-30")
        self.assertInvalido(
            "La fecha 'hasta' (2026-02-30) no es una fecha válida.", "2026-01-01", "2026-02-30"
        )
        self.assertInvalido("La fecha 'hasta' debe tener formato AAAA-MM-DD.", "2026-01-01", "x")

    def test_rango_invertido(self):
        self.assertInvalido(
            "La fecha 'desde' (2026-11-30) no puede ser posterior a 'hasta' (2026-11-01).",
            "2026-11-30", "2026-11-01",
        )

    def test_rango_de_anios_aceptado(self):
        self.assertEqual(self.svc.productos_en_ordenes("2020-01-01", "2026-12-31"), [])

    def test_codigo_normalizado(self):
        self.orden("OT-1", "2026-11-05", [("A-01", 3), ("B-02", 1)])
        res = self.svc.productos_en_ordenes("2026-11-01", "2026-11-30", " a-01 ")
        self.assertEqual([f.codigo for f in res], ["A-01"])

    def test_codigo_en_blanco_sin_filtro(self):
        self.orden("OT-1", "2026-11-05", [("A-01", 3), ("B-02", 1)])
        res = self.svc.productos_en_ordenes("2026-11-01", "2026-11-30", "   ")
        self.assertEqual(len(res), 2)

    def test_codigo_demasiado_largo(self):
        with self.assertRaises(DatosInvalidos):
            self.svc.productos_en_ordenes("2026-11-01", "2026-11-30", "A" * 51)

    def test_productos_usados_delega(self):
        self.orden("OT-1", "2026-11-05", [("A-01", 3)])
        self.assertEqual(self.svc.productos_usados(), [ProductoUsado("A-01", "Tornillo", True)])


if __name__ == "__main__":
    unittest.main()
