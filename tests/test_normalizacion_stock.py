import unittest

from inventario.domain.entities import (
    LineaModificacion,
    Movimiento,
    ResultadoModificacion,
)
from inventario.domain.errors import (
    DatosInvalidos,
    InventarioError,
    ProductoDuplicado,
    ProductosInexistentes,
)
from inventario.services.normalizacion import validar_stock

MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000."


class ValidarStockTest(unittest.TestCase):
    def test_acepta_bordes_y_valores_intermedios(self):
        for valor in (0, 1, 5, 10_000):
            with self.subTest(valor=valor):
                self.assertEqual(validar_stock(valor), valor)

    def test_rechaza_fuera_de_rango_y_tipos_incorrectos(self):
        for valor in (-1, 10_001, 2.5, "5", True, None, False):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    validar_stock(valor)
                self.assertEqual(str(ctx.exception), MSG_STOCK)


class ErroresNuevosTest(unittest.TestCase):
    def test_producto_duplicado(self):
        e = ProductoDuplicado("A-01")
        self.assertIsInstance(e, InventarioError)
        self.assertEqual(str(e), "Ya existe un producto con código 'A-01'.")
        self.assertEqual(e.codigo, "A-01")

    def test_productos_inexistentes_uno(self):
        e = ProductosInexistentes(["Z-01"])
        self.assertEqual(str(e), "No existe un producto con código 'Z-01'.")
        self.assertEqual(e.codigos, ("Z-01",))

    def test_productos_inexistentes_varios(self):
        e = ProductosInexistentes(["Z-01", "Z-02"])
        self.assertEqual(str(e), "No existen productos con código: 'Z-01', 'Z-02'.")
        self.assertEqual(e.codigos, ("Z-01", "Z-02"))


class EntidadesNuevasTest(unittest.TestCase):
    def test_linea_modificacion(self):
        linea = LineaModificacion("A-01", "fijar", 5, None)
        self.assertEqual((linea.codigo, linea.modo, linea.valor, linea.nombre), ("A-01", "fijar", 5, None))

    def test_resultado_modificacion_sin_stock(self):
        for stock, esperado in ((0, True), (3, False)):
            with self.subTest(stock=stock):
                r = ResultadoModificacion(
                    codigo="A-01", nombre="T", stock=stock, modo="fijar",
                    stock_anterior=1, nombre_anterior="T", reactivado=False,
                )
                self.assertIs(r.sin_stock, esperado)

    def test_movimiento_anterior_y_nuevo_son_opcionales(self):
        base = dict(fecha=None, codigo="A", nombre="N", tipo="ingreso", cantidad=1, usuario="u")
        m = Movimiento(**base)
        self.assertEqual((m.stock_anterior, m.stock_nuevo), (None, None))
        m = Movimiento(**base, stock_anterior=7, stock_nuevo=4)
        self.assertEqual((m.stock_anterior, m.stock_nuevo), (7, 4))


if __name__ == "__main__":
    unittest.main()
