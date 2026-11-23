import ast
import pathlib
import unittest
from datetime import datetime

from inventario.domain.errors import (
    DatosInvalidos,
    NombreRequerido,
    ProductoNoEncontrado,
    StockInsuficiente,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteStockRepository
from inventario.services.stock_service import StockService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
TEXTO_FECHA = "2026-11-19T15:30:00-03:00"
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


class ServiceBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.conn.commit()
        self.llamadas = 0
        self.service = StockService(SqliteStockRepository(self.conn), ahora=self._reloj)

    def _reloj(self):
        self.llamadas += 1
        return FECHA_FIJA

    def stock(self, codigo):
        fila = self.conn.execute(
            "SELECT stock FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()
        return None if fila is None else fila[0]

    def productos(self):
        return self.conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]


class IngresoServiceTest(ServiceBase):
    def test_codigo_con_espacios_suma_sobre_el_existente(self):
        r = self.service.ingresar("  A-01  ", 2, None, self.uid)
        self.assertEqual(r.producto.stock, 7)
        self.assertEqual(self.productos(), 1)
        self.assertEqual(
            movimientos(self.conn), [("ingreso", 2, "A-01", self.uid, TEXTO_FECHA)]
        )

    def test_minusculas_crean_en_mayusculas_y_luego_suman(self):
        r1 = self.service.ingresar("rd-6204", 4, "Rodamiento 6204", self.uid)
        r2 = self.service.ingresar("Rd-6204", 2, None, self.uid)
        self.assertEqual(r1.producto.codigo, "RD-6204")
        self.assertTrue(r1.creado)
        self.assertEqual(r2.producto.stock, 6)
        self.assertEqual(self.stock("RD-6204"), 6)
        self.assertEqual(self.productos(), 2)
        self.assertEqual(len(movimientos(self.conn)), 2)

    def test_cantidad_maxima_aceptada(self):
        r = self.service.ingresar("A-01", 10_000, None, self.uid)
        self.assertEqual(r.producto.stock, 10_005)

    def test_cantidades_invalidas_se_rechazan_sin_escribir(self):
        for cantidad in (0, -1, 2.5, "5", True, 10_001, None):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.ingresar("A-01", cantidad, None, self.uid)
                self.assertEqual(str(ctx.exception), MSG_CANTIDAD)
        self.assertEqual(self.stock("A-01"), 5)
        self.assertEqual(movimientos(self.conn), [])

    def test_codigo_invalido(self):
        for codigo in ("   ", "", None, 5):
            with self.subTest(codigo=codigo):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.ingresar(codigo, 1, "N", self.uid)
                self.assertEqual(str(ctx.exception), "El campo codigo es obligatorio.")
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.ingresar("x" * 51, 1, "N", self.uid)
        self.assertEqual(str(ctx.exception), "El campo codigo admite hasta 50 caracteres.")
        self.service.ingresar("x" * 50, 1, "N", self.uid)  # limite aceptado
        self.assertEqual(self.stock("X" * 50), 1)

    def test_nombre_se_recorta_en_el_alta(self):
        r = self.service.ingresar("N-01", 1, "  Buje  ", self.uid)
        self.assertEqual(r.producto.nombre, "Buje")

    def test_nombre_vacio_en_codigo_nuevo_pide_nombre(self):
        for nombre in ("   ", "", None):
            with self.subTest(nombre=nombre):
                with self.assertRaises(NombreRequerido):
                    self.service.ingresar("n-02", 1, nombre, self.uid)
        self.assertEqual(self.productos(), 1)

    def test_nombre_vacio_en_codigo_existente_se_ignora(self):
        r = self.service.ingresar("A-01", 1, "   ", self.uid)
        self.assertEqual(r.producto.stock, 6)

    def test_nombre_demasiado_largo(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.ingresar("N-01", 1, "n" * 121, self.uid)
        self.assertEqual(str(ctx.exception), "El campo nombre admite hasta 120 caracteres.")
        self.service.ingresar("N-01", 1, "n" * 120, self.uid)

    def test_nombre_no_texto(self):
        with self.assertRaises(DatosInvalidos):
            self.service.ingresar("N-01", 1, 5, self.uid)


class EgresoServiceTest(ServiceBase):
    def test_codigo_en_minusculas_con_espacios(self):
        p = self.service.egresar(" a-01 ", 1, self.uid)
        self.assertEqual(p.stock, 4)
        self.assertIsNone(self.stock("a-01"))
        self.assertEqual(
            movimientos(self.conn), [("egreso", 1, "A-01", self.uid, TEXTO_FECHA)]
        )

    def test_errores_muestran_codigo_en_mayusculas(self):
        with self.assertRaises(ProductoNoEncontrado) as ctx:
            self.service.egresar("x-00", 1, self.uid)
        self.assertEqual(str(ctx.exception), "No existe un producto activo con código 'X-00'.")
        with self.assertRaises(StockInsuficiente) as ctx:
            self.service.egresar("a-01", 6, self.uid)
        self.assertEqual(
            str(ctx.exception), "Stock insuficiente para 'A-01': disponible 5, solicitado 6."
        )

    def test_cantidades_invalidas(self):
        for cantidad in (0, -1, 2.5, "5", True, 10_001):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.egresar("A-01", cantidad, self.uid)
                self.assertEqual(str(ctx.exception), MSG_CANTIDAD)
        self.assertEqual(self.stock("A-01"), 5)
        self.assertEqual(movimientos(self.conn), [])

    def test_codigo_invalido(self):
        with self.assertRaises(DatosInvalidos):
            self.service.egresar("  ", 1, self.uid)


class RelojTest(ServiceBase):
    def test_una_llamada_por_operacion_aceptada(self):
        self.service.ingresar("A-01", 1, None, self.uid)
        self.service.egresar("A-01", 1, self.uid)
        self.assertEqual(self.llamadas, 2)

    def test_ninguna_llamada_si_la_validacion_falla(self):
        with self.assertRaises(DatosInvalidos):
            self.service.ingresar("A-01", 0, None, self.uid)
        with self.assertRaises(DatosInvalidos):
            self.service.egresar("", 1, self.uid)
        self.assertEqual(self.llamadas, 0)

    def test_reloj_por_defecto_usa_offset_argentina(self):
        service = StockService(SqliteStockRepository(self.conn))
        service.ingresar("A-01", 1, None, self.uid)
        self.assertTrue(movimientos(self.conn)[0][4].endswith("-03:00"))


class AltaServiceTest(ServiceBase):
    def test_normaliza_codigo_y_nombre_y_usa_el_reloj_inyectado(self):
        r = self.service.dar_de_alta("  rd-6204 ", "  Rodamiento 6204  ", 4, self.uid)
        self.assertTrue(r.creado)
        self.assertEqual(
            (r.producto.codigo, r.producto.nombre, r.producto.stock),
            ("RD-6204", "Rodamiento 6204", 4),
        )
        self.assertEqual(
            movimientos(self.conn), [("ingreso", 4, "RD-6204", self.uid, TEXTO_FECHA)]
        )
        self.assertEqual(self.llamadas, 1)

    def test_stock_cero_y_maximo(self):
        self.assertEqual(self.service.dar_de_alta("N-02", "Buje", 0, self.uid).producto.stock, 0)
        r = self.service.dar_de_alta("N-03", "Junta", 10_000, self.uid)
        self.assertEqual(r.producto.stock, 10_000)

    def test_nombre_obligatorio(self):
        for nombre in (None, "", "   "):
            with self.subTest(nombre=nombre):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.dar_de_alta("N-01", nombre, 1, self.uid)
                self.assertEqual(str(ctx.exception), "El campo nombre es obligatorio.")
        self.assertEqual(self.productos(), 1)

    def test_nombre_largo_o_no_texto(self):
        for nombre in ("x" * 121, 5):
            with self.subTest(nombre=nombre):
                with self.assertRaises(DatosInvalidos):
                    self.service.dar_de_alta("N-01", nombre, 1, self.uid)

    def test_stock_invalido_no_escribe(self):
        for stock in (-1, 10_001, 2.5, "5", None, True):
            with self.subTest(stock=stock):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.dar_de_alta("N-01", "Pieza", stock, self.uid)
                self.assertEqual(
                    str(ctx.exception), "El stock debe ser un entero entre 0 y 10.000."
                )
        self.assertEqual(self.productos(), 1)

    def test_codigo_invalido(self):
        for codigo in ("  ", None, "x" * 51):
            with self.subTest(codigo=codigo):
                with self.assertRaises(DatosInvalidos):
                    self.service.dar_de_alta(codigo, "Pieza", 1, self.uid)


class SinDependenciasDeInfraestructuraTest(unittest.TestCase):
    def test_services_no_importan_sqlite_ni_fastapi_ni_pydantic(self):
        raiz = pathlib.Path(__file__).resolve().parent.parent / "inventario" / "services"
        prohibidos = {"sqlite3", "fastapi", "pydantic"}
        for archivo in raiz.glob("*.py"):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    nombres = {a.name.split(".")[0] for a in nodo.names}
                elif isinstance(nodo, ast.ImportFrom):
                    nombres = {(nodo.module or "").split(".")[0]}
                else:
                    continue
                self.assertFalse(
                    nombres & prohibidos, f"{archivo.name} importa {nombres & prohibidos}"
                )


if __name__ == "__main__":
    unittest.main()
