import os
import tempfile
import threading
import unittest
from datetime import date, datetime

from inventario.domain.entities import Producto
from inventario.domain.errors import (
    ProductoNoEncontrado,
    ProductosNoEncontrados,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteOrdenRepository,
    SqliteProductoRepository,
    SqliteStockRepository,
    conectar,
    inicializar_esquema,
)
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
MSG_A01 = "No existe un producto activo con código 'A-01'."


class BajaBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteProductoRepository(self.conn)

    def fila(self, codigo):
        f = self.conn.execute(
            "SELECT nombre, stock, activo FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()
        return tuple(f) if f else None


class DarDeBajaTest(BajaBase):
    def test_baja_conserva_stock_y_nombre(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        producto = self.repo.dar_de_baja("A-01")
        self.assertIsInstance(producto, Producto)
        self.assertEqual((producto.codigo, producto.nombre, producto.stock), ("A-01", "Tornillo", 7))
        self.assertIs(producto.activo, False)
        self.assertEqual(self.fila("A-01"), ("Tornillo", 7, 0))
        self.assertEqual(self.repo.listar_activos(), [])
        self.assertFalse(self.conn.in_transaction)

    def test_stock_cero_queda_inactivo_con_cero(self):
        insertar_producto(self.conn, "B-02", "Tuerca", 0)
        producto = self.repo.dar_de_baja("B-02")
        self.assertEqual((producto.stock, producto.activo), (0, False))
        self.assertEqual(self.fila("B-02"), ("Tuerca", 0, 0))

    def test_solo_baja_el_producto_pedido(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        insertar_producto(self.conn, "B-02", "Tuerca", 3)
        self.repo.dar_de_baja("A-01")
        self.assertEqual([p.codigo for p in self.repo.listar_activos()], ["B-02"])

    def test_inexistente(self):
        with self.assertRaises(ProductoNoEncontrado) as ctx:
            self.repo.dar_de_baja("Z-99")
        self.assertEqual(str(ctx.exception), "No existe un producto activo con código 'Z-99'.")
        self.assertFalse(self.conn.in_transaction)

    def test_ya_inactivo_no_cambia_nada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7, activo=0)
        with self.assertRaises(ProductoNoEncontrado) as ctx:
            self.repo.dar_de_baja("A-01")
        self.assertEqual(str(ctx.exception), MSG_A01)
        self.assertEqual(self.fila("A-01"), ("Tornillo", 7, 0))
        self.assertFalse(self.conn.in_transaction)

    def test_segunda_baja_seguida_falla(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        self.repo.dar_de_baja("A-01")
        with self.assertRaises(ProductoNoEncontrado):
            self.repo.dar_de_baja("A-01")
        self.assertEqual(self.fila("A-01"), ("Tornillo", 7, 0))

    def test_no_toca_movimientos(self):
        pid = insertar_producto(self.conn, "A-01", "Tornillo", 7)
        self.conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
            "VALUES ('2026-11-19T10:00:00-03:00', ?, 'ingreso', 7, ?)",
            (pid, self.uid),
        )
        self.conn.commit()
        antes = movimientos(self.conn)
        self.repo.dar_de_baja("A-01")
        with self.assertRaises(ProductoNoEncontrado):
            self.repo.dar_de_baja("A-01")
        self.assertEqual(movimientos(self.conn), antes)


class EfectosCruzadosTest(BajaBase):
    def setUp(self):
        super().setUp()
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        insertar_producto(self.conn, "B-02", "Tuerca", 5)
        self.ordenes = SqliteOrdenRepository(self.conn)
        self.stock = SqliteStockRepository(self.conn)
        self.ordenes.crear("OT-0001", date(2026, 11, 20), [("A-01", 2)], self.uid, FECHA)
        self.repo.dar_de_baja("A-01")

    def test_egreso_rechazado(self):
        with self.assertRaises(ProductoNoEncontrado):
            self.stock.registrar_egreso("A-01", 1, self.uid, FECHA)

    def test_alta_de_orden_rechazada(self):
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.ordenes.crear("OT-0002", date(2026, 11, 20), [("A-01", 1)], self.uid, FECHA)
        self.assertEqual(str(ctx.exception), MSG_A01)
        self.assertEqual(self.fila("A-01")[1], 5)

    def test_orden_previa_sigue_mostrando_el_componente(self):
        (orden,) = self.ordenes.listar(None, None, None)
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("A-01", 2)])

    def test_ingreso_reactiva_y_suma_al_stock_conservado(self):
        res = self.stock.registrar_ingreso("A-01", 3, None, self.uid, FECHA)
        self.assertIs(res.reactivado, True)
        self.assertEqual((res.producto.stock, res.producto.activo), (8, True))
        self.assertIn("A-01", [p.codigo for p in self.repo.listar_activos()])


class ConcurrenciaBajaTest(unittest.TestCase):
    def test_dos_bajas_simultaneas_solo_una_gana(self):
        for ronda in range(5):
            with self.subTest(ronda=ronda):
                with tempfile.TemporaryDirectory() as tmp:
                    ruta = os.path.join(tmp, "c.db")
                    prep = conectar(ruta)
                    inicializar_esquema(prep)
                    insertar_producto(prep, "A-01", "Tornillo", 5)
                    prep.close()

                    barrera = threading.Barrier(2)
                    resultados = []

                    def trabajar():
                        conn = conectar(ruta)
                        try:
                            repo = SqliteProductoRepository(conn)
                            barrera.wait()
                            try:
                                repo.dar_de_baja("A-01")
                                resultados.append("ok")
                            except ProductoNoEncontrado:
                                resultados.append("inexistente")
                        finally:
                            conn.close()

                    hilos = [threading.Thread(target=trabajar) for _ in range(2)]
                    for h in hilos:
                        h.start()
                    for h in hilos:
                        h.join()
                    self.assertEqual(sorted(resultados), ["inexistente", "ok"])
