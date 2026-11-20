import ast
import pathlib
import unittest

from inventario.domain.entities import Producto
from inventario.domain.errors import (
    MENSAJE_CREDENCIALES_INVALIDAS,
    CredencialesInvalidas,
    InventarioError,
)
from inventario.repositories.base import ProductoRepository, UsuarioRepository

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "inventario"


class ProductoTest(unittest.TestCase):
    def test_sin_stock(self):
        for stock, esperado in ((0, True), (5, False)):
            with self.subTest(stock=stock):
                p = Producto(id=1, codigo="P", nombre="N", stock=stock, activo=True)
                self.assertIs(p.sin_stock, esperado)


class ErroresTest(unittest.TestCase):
    def test_credenciales_invalidas(self):
        self.assertEqual(MENSAJE_CREDENCIALES_INVALIDAS, "Usuario o contraseña incorrectos.")
        self.assertTrue(issubclass(CredencialesInvalidas, InventarioError))
        self.assertEqual(str(CredencialesInvalidas()), MENSAJE_CREDENCIALES_INVALIDAS)


class InterfacesTest(unittest.TestCase):
    def test_abcs_no_instanciables(self):
        for abc_cls in (UsuarioRepository, ProductoRepository):
            with self.subTest(abc=abc_cls.__name__):
                with self.assertRaises(TypeError):
                    abc_cls()

    def test_domain_y_services_no_importan_sqlite3(self):
        archivos = list((RAIZ / "domain").glob("*.py")) + list((RAIZ / "services").glob("*.py"))
        self.assertTrue(archivos)
        for archivo in archivos:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    modulos = [a.name for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom):
                    modulos = [nodo.module or ""]
                else:
                    continue
                for m in modulos:
                    with self.subTest(archivo=archivo.name, modulo=m):
                        self.assertNotEqual(m.split(".")[0], "sqlite3")

    def test_capas_internas_no_importan_frameworks_web(self):
        prohibidos = {"fastapi", "starlette", "pydantic", "uvicorn", "dotenv"}
        archivos = []
        for capa in ("domain", "services", "repositories"):
            archivos += list((RAIZ / capa).glob("*.py"))
        self.assertTrue(archivos)
        for archivo in archivos:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    modulos = [a.name for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom):
                    modulos = [nodo.module or ""]
                else:
                    continue
                for m in modulos:
                    with self.subTest(archivo=archivo.name, modulo=m):
                        self.assertNotIn(m.split(".")[0], prohibidos)


class EntidadesDeStockTest(unittest.TestCase):
    def test_resultado_ingreso_y_movimiento_son_inmutables(self):
        import dataclasses
        from datetime import datetime

        from inventario.domain.entities import Movimiento, ResultadoIngreso
        from inventario.domain.tiempo import ZONA_AR

        p = Producto(id=1, codigo="A-01", nombre="N", stock=1, activo=True)
        r = ResultadoIngreso(producto=p, creado=False, reactivado=True)
        m = Movimiento(
            fecha=datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR),
            codigo="A-01", nombre="N", tipo="ingreso", cantidad=2, usuario="admin",
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.creado = True
        with self.assertRaises(dataclasses.FrozenInstanceError):
            m.cantidad = 9
        self.assertTrue(r.reactivado)
        self.assertEqual(m.usuario, "admin")


class ErroresDeStockTest(unittest.TestCase):
    def test_heredan_de_inventario_error(self):
        from inventario.domain.errors import (
            DatosInvalidos, NombreRequerido, ProductoNoEncontrado, StockInsuficiente,
        )

        for cls in (DatosInvalidos, NombreRequerido, ProductoNoEncontrado, StockInsuficiente):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, InventarioError))

    def test_mensajes_y_atributos(self):
        from inventario.domain.errors import (
            DatosInvalidos, NombreRequerido, ProductoNoEncontrado, StockInsuficiente,
        )

        n = NombreRequerido("N-02")
        self.assertEqual(
            str(n), "El producto 'N-02' no existe: indicá un nombre para crearlo."
        )
        self.assertEqual(n.codigo, "N-02")
        p = ProductoNoEncontrado("X-00")
        self.assertEqual(str(p), "No existe un producto activo con código 'X-00'.")
        self.assertEqual(p.codigo, "X-00")
        s = StockInsuficiente("A-01", disponible=5, solicitado=6)
        self.assertEqual(
            str(s), "Stock insuficiente para 'A-01': disponible 5, solicitado 6."
        )
        self.assertEqual((s.codigo, s.disponible, s.solicitado), ("A-01", 5, 6))
        self.assertEqual(str(DatosInvalidos("msg")), "msg")
        self.assertEqual(str(NombreRequerido("Z-9")),
                         "El producto 'Z-9' no existe: indicá un nombre para crearlo.")
