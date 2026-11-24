import unittest
from datetime import datetime

from inventario.domain.entities import LineaModificacion
from inventario.domain.errors import DatosInvalidos, ProductosInexistentes
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteCategoriaRepository,
    SqliteStockRepository,
)
from inventario.services.stock_service import StockService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000."
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def fijar(codigo, valor, nombre=None):
    return LineaModificacion(codigo, "fijar", valor, nombre)


def sumar(codigo, valor, nombre=None):
    return LineaModificacion(codigo, "sumar", valor, nombre)


class ModificacionServiceBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo M4", 5)
        insertar_producto(self.conn, "B-10", "Tuerca", 0)
        self.service = StockService(
            SqliteStockRepository(self.conn), SqliteCategoriaRepository(self.conn), ahora=lambda: FECHA_FIJA)

    def modificar(self, *lineas):
        return self.service.modificar(list(lineas), self.uid)

    def stock(self, codigo):
        fila = self.conn.execute("SELECT stock FROM productos WHERE codigo = ?", (codigo,))
        return fila.fetchone()[0]

    def assertRechaza(self, mensaje, *lineas):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.modificar(*lineas)
        self.assertEqual(str(ctx.exception), mensaje)
        self.assertEqual(self.stock("A-01"), 5)
        self.assertEqual(movimientos(self.conn), [])


class ListaTest(ModificacionServiceBase):
    def test_vacia_none_o_no_lista(self):
        for lineas in ([], None, "x"):
            with self.subTest(lineas=lineas):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.modificar(lineas, self.uid)
                self.assertEqual(str(ctx.exception), "La modificación requiere al menos una línea.")

    def test_mas_de_100_lineas(self):
        lineas = [sumar(f"X-{i}", 1) for i in range(101)]
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.modificar(lineas, self.uid)
        self.assertEqual(str(ctx.exception), "La modificación admite hasta 100 líneas.")

    def test_100_lineas_aceptadas(self):
        for i in range(100):
            insertar_producto(self.conn, f"X-{i}", "Pieza", 0)
        res = self.service.modificar([sumar(f"X-{i}", 1) for i in range(100)], self.uid)
        self.assertEqual(len(res), 100)


class ValidacionDeLineaTest(ModificacionServiceBase):
    def test_codigo_vacio_o_largo(self):
        self.assertRechaza("Línea 1: El campo codigo es obligatorio.", sumar("  ", 1))
        self.assertRechaza(
            "Línea 2: El campo codigo admite hasta 50 caracteres.",
            fijar("A-01", 1),
            sumar("x" * 51, 1),
        )

    def test_modo_invalido(self):
        self.assertRechaza(
            "Línea 1: El campo modo debe ser fijar o sumar.",
            LineaModificacion("A-01", "restar", 1, None),
        )

    def test_stock_fuera_de_rango_en_fijar(self):
        for valor in (-1, 10_001, 2.5):
            with self.subTest(valor=valor):
                self.assertRechaza(f"Línea 2: {MSG_STOCK}", sumar("B-10", 1), fijar("A-01", valor))

    def test_cantidad_fuera_de_rango_en_sumar(self):
        for valor in (0, -1, 10_001):
            with self.subTest(valor=valor):
                self.assertRechaza(f"Línea 1: {MSG_CANTIDAD}", sumar("A-01", valor))

    def test_nombre_largo(self):
        self.assertRechaza(
            "Línea 3: El campo nombre admite hasta 120 caracteres.",
            fijar("A-01", 1),
            sumar("B-10", 1),
            fijar("C-01", 1, "x" * 121),
        )

    def test_la_primera_linea_invalida_gana(self):
        self.assertRechaza(f"Línea 1: {MSG_CANTIDAD}", sumar("A-01", 0), fijar("B-10", -1))

    def test_repetido_tras_normalizar(self):
        self.assertRechaza(
            "Línea 3: el producto 'A-01' ya está en la línea 1.",
            fijar("A-01", 3),
            sumar("B-10", 1),
            sumar("a-01 ", 2),
        )

    def test_validacion_antes_que_repetido_y_que_inexistencia(self):
        self.assertRechaza(
            f"Línea 3: {MSG_CANTIDAD}", sumar("Z-01", 1), sumar("Z-01", 1), sumar("A-01", 0)
        )

    def test_repetido_antes_que_inexistencia(self):
        self.assertRechaza(
            "Línea 2: el producto 'Z-01' ya está en la línea 1.",
            sumar("Z-01", 1),
            sumar("z-01", 1),
        )


class AceptacionTest(ModificacionServiceBase):
    def test_bordes_aceptados(self):
        res = self.modificar(fijar("A-01", 10_000), sumar("B-10", 10_000))
        self.assertEqual([r.stock for r in res], [10_000, 10_000])
        res = self.modificar(fijar("A-01", 0), sumar("B-10", 1))
        self.assertEqual([r.stock for r in res], [0, 10_001])

    def test_normaliza_codigo_y_recorta_nombre(self):
        res = self.modificar(fijar(" a-01 ", 5, "  Tornillo M4 x 20  "))
        self.assertEqual((res[0].codigo, res[0].nombre), ("A-01", "Tornillo M4 x 20"))

    def test_nombre_en_blanco_es_sin_cambio(self):
        for nombre in ("", "   ", None):
            with self.subTest(nombre=nombre):
                res = self.modificar(fijar("A-01", 5, nombre))
                self.assertEqual(res[0].nombre, "Tornillo M4")

    def test_inexistentes_se_informan_todos(self):
        with self.assertRaises(ProductosInexistentes) as ctx:
            self.modificar(fijar("A-01", 9), sumar("Z-01", 1), sumar("Z-02", 1))
        self.assertEqual(str(ctx.exception), "No existen productos con código: 'Z-01', 'Z-02'.")
        self.assertEqual(self.stock("A-01"), 5)

    def test_usa_el_reloj_y_el_usuario(self):
        self.modificar(sumar("A-01", 2))
        self.assertEqual(
            movimientos(self.conn),
            [("ingreso", 2, "A-01", self.uid, "2026-11-19T15:30:00-03:00")],
        )


if __name__ == "__main__":
    unittest.main()
