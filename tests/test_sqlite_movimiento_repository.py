import unittest
from datetime import date, timedelta

from inventario.domain.entities import Movimiento
from inventario.repositories.sqlite_repo import SqliteMovimientoRepository
from tests.helpers import (
    conexion_inicializada,
    insertar_movimiento,
    insertar_producto,
    insertar_usuario,
)


class RepoMovimientosBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn, "admin")
        self.a01 = insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.b10 = insertar_producto(self.conn, "B-10", "Tuerca", 0)
        self.repo = SqliteMovimientoRepository(self.conn)

    def sembrar(self, fecha, producto=None, tipo="ingreso", cantidad=1):
        return insertar_movimiento(
            self.conn, fecha, producto or self.a01, tipo, cantidad, self.uid
        )


class OrdenYMapeoTest(RepoMovimientosBase):
    def test_devuelve_del_mas_nuevo_al_mas_viejo_con_campos_mapeados(self):
        self.sembrar("2026-11-18T10:00:00-03:00", cantidad=2)
        self.sembrar("2026-11-19T10:00:00-03:00", tipo="egreso", cantidad=3)
        self.sembrar("2026-11-17T10:00:00-03:00", cantidad=4)
        lista = self.repo.listar(None, None, None)
        self.assertEqual(
            [m.fecha.day for m in lista], [19, 18, 17]
        )
        primero = lista[0]
        self.assertIsInstance(primero, Movimiento)
        self.assertEqual(primero.fecha.utcoffset(), timedelta(hours=-3))
        self.assertEqual(
            (primero.codigo, primero.nombre, primero.tipo, primero.cantidad, primero.usuario),
            ("A-01", "Tornillo", "egreso", 3, "admin"),
        )

    def test_misma_fecha_desempata_por_id_mayor_primero(self):
        self.sembrar("2026-11-19T10:00:00-03:00", cantidad=1)
        self.sembrar("2026-11-19T10:00:00-03:00", cantidad=2)
        self.assertEqual([m.cantidad for m in self.repo.listar(None, None, None)], [2, 1])

    def test_sin_movimientos_devuelve_lista_vacia(self):
        self.assertEqual(self.repo.listar(None, None, None), [])

    def test_incluye_movimientos_de_productos_inactivos(self):
        self.conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (self.a01,))
        self.sembrar("2026-11-19T10:00:00-03:00")
        self.assertEqual(len(self.repo.listar(None, None, None)), 1)


class FiltroCodigoTest(RepoMovimientosBase):
    def test_filtra_por_codigo_exacto(self):
        self.sembrar("2026-11-19T10:00:00-03:00", self.a01)
        self.sembrar("2026-11-19T11:00:00-03:00", self.b10)
        self.assertEqual([m.codigo for m in self.repo.listar("A-01", None, None)], ["A-01"])
        self.assertEqual([m.codigo for m in self.repo.listar("B-10", None, None)], ["B-10"])

    def test_codigo_inexistente_devuelve_vacio(self):
        self.sembrar("2026-11-19T10:00:00-03:00")
        self.assertEqual(self.repo.listar("X-00", None, None), [])


class FiltroFechasTest(RepoMovimientosBase):
    def setUp(self):
        super().setUp()
        for fecha in (
            "2026-11-17T23:59:59-03:00",
            "2026-11-18T00:00:00-03:00",
            "2026-11-19T23:59:59-03:00",
            "2026-11-20T00:00:00-03:00",
        ):
            self.sembrar(fecha)

    def dias(self, desde, hasta, codigo=None):
        return sorted(
            m.fecha.isoformat() for m in self.repo.listar(codigo, desde, hasta)
        )

    def test_rango_inclusivo_en_fecha_local(self):
        self.assertEqual(
            self.dias(date(2026, 11, 18), date(2026, 11, 19)),
            ["2026-11-18T00:00:00-03:00", "2026-11-19T23:59:59-03:00"],
        )

    def test_solo_desde(self):
        self.assertEqual(len(self.repo.listar(None, date(2026, 11, 19), None)), 2)

    def test_solo_hasta(self):
        self.assertEqual(len(self.repo.listar(None, None, date(2026, 11, 17))), 1)

    def test_un_solo_dia(self):
        self.assertEqual(
            self.dias(date(2026, 11, 20), date(2026, 11, 20)), ["2026-11-20T00:00:00-03:00"]
        )

    def test_codigo_y_fechas_combinados(self):
        self.sembrar("2026-11-18T12:00:00-03:00", self.b10)
        lista = self.repo.listar("B-10", date(2026, 11, 18), date(2026, 11, 18))
        self.assertEqual([m.codigo for m in lista], ["B-10"])
        self.assertEqual(self.repo.listar("B-10", date(2026, 11, 19), None), [])


if __name__ == "__main__":
    unittest.main()


class FechaLegadaNoParseableTest(RepoMovimientosBase):
    def test_listado_omite_la_fila_no_parseable_y_avisa(self):
        self.sembrar("2026-11-19T10:00:00-03:00", cantidad=1)
        self.sembrar("basura", cantidad=2)
        with self.assertLogs("inventario", level="WARNING") as logs:
            movimientos = self.repo.listar(None, None, None)
        self.assertEqual([m.cantidad for m in movimientos], [1])
        self.assertIn("basura", logs.output[0])

    def test_se_omite_con_filtros_de_codigo_y_solo_desde(self):
        self.sembrar("2026-11-19T10:00:00-03:00", cantidad=1)
        self.sembrar("basura", cantidad=2)
        with self.assertLogs("inventario", level="WARNING"):
            movimientos = self.repo.listar("A-01", date(2026, 11, 19), None)
        self.assertEqual([m.cantidad for m in movimientos], [1])

    def test_con_rango_cerrado_la_fila_no_aparece_y_no_falla(self):
        self.sembrar("2026-11-19T10:00:00-03:00", cantidad=1)
        self.sembrar("basura", cantidad=2)
        movimientos = self.repo.listar(None, date(2026, 11, 19), date(2026, 11, 19))
        self.assertEqual([m.cantidad for m in movimientos], [1])


class AjusteTest(RepoMovimientosBase):
    def sembrar_ajuste(self, fecha, producto, anterior, nuevo):
        self.conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id,"
            " stock_anterior, stock_nuevo) VALUES (?, ?, 'ajuste', ?, ?, ?, ?)",
            (fecha, producto, abs(nuevo - anterior), self.uid, anterior, nuevo),
        )
        self.conn.commit()

    def test_ajuste_devuelve_anterior_y_nuevo_y_el_resto_none(self):
        self.sembrar("2026-11-18T10:00:00-03:00", cantidad=2)
        self.sembrar("2026-11-18T11:00:00-03:00", tipo="egreso", cantidad=1)
        self.sembrar_ajuste("2026-11-19T10:00:00-03:00", self.a01, 7, 4)
        lista = self.repo.listar(None, None, None)
        self.assertEqual(
            [(m.tipo, m.cantidad, m.stock_anterior, m.stock_nuevo) for m in lista],
            [("ajuste", 3, 7, 4), ("egreso", 1, None, None), ("ingreso", 2, None, None)],
        )

    def test_filtro_por_codigo_incluye_el_ajuste(self):
        self.sembrar_ajuste("2026-11-19T10:00:00-03:00", self.a01, 0, 5)
        self.sembrar_ajuste("2026-11-19T11:00:00-03:00", self.b10, 5, 1)
        lista = self.repo.listar("A-01", None, None)
        self.assertEqual([(m.codigo, m.tipo) for m in lista], [("A-01", "ajuste")])
