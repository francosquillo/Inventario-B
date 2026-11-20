import unittest

from inventario.domain.errors import DatosInvalidos, ProductoNoEncontrado
from inventario.repositories.sqlite_repo import SqliteProductoRepository
from inventario.services.producto_service import ProductoService
from tests.helpers import conexion_inicializada, insertar_producto


class ProductoServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        insertar_producto(self.conn, "B-02", "Tuerca", 3)
        self.service = ProductoService(SqliteProductoRepository(self.conn))

    def activo(self, codigo):
        return self.conn.execute(
            "SELECT activo FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()[0]

    def test_normaliza_y_da_de_baja(self):
        producto = self.service.dar_de_baja("  a-01 ")
        self.assertEqual((producto.codigo, producto.stock, producto.activo), ("A-01", 7, False))
        self.assertEqual((self.activo("A-01"), self.activo("B-02")), (0, 1))

    def test_codigo_vacio_o_en_blanco(self):
        for valor in ("", "   ", None):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.dar_de_baja(valor)
                self.assertEqual(str(ctx.exception), "El campo codigo es obligatorio.")
        self.assertEqual(self.activo("A-01"), 1)

    def test_codigo_largo(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.dar_de_baja("X" * 51)
        self.assertEqual(str(ctx.exception), "El campo codigo admite hasta 50 caracteres.")

    def test_inexistente_lleva_el_codigo_normalizado(self):
        with self.assertRaises(ProductoNoEncontrado) as ctx:
            self.service.dar_de_baja("z-99")
        self.assertEqual(str(ctx.exception), "No existe un producto activo con código 'Z-99'.")
