import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone

from inventario.domain.entities import ResultadoIngreso
from inventario.domain.errors import NombreRequerido, ProductoNoEncontrado, StockInsuficiente
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteStockRepository,
    conectar,
    inicializar_esquema,
)
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
TEXTO_FECHA = "2026-11-19T15:30:00-03:00"


class RepoBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteStockRepository(self.conn)

    def fila_de(self, codigo):
        fila = self.conn.execute(
            "SELECT stock, activo, nombre FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()
        return None if fila is None else tuple(fila)

    def cantidad_productos(self, codigo):
        return self.conn.execute(
            "SELECT COUNT(*) FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()[0]


class IngresoTest(RepoBase):
    def test_suma_a_producto_existente(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        r = self.repo.registrar_ingreso("A-01", 3, None, self.uid, FECHA_FIJA)
        self.assertIsInstance(r, ResultadoIngreso)
        self.assertFalse(r.creado)
        self.assertFalse(r.reactivado)
        self.assertEqual(r.producto.stock, 8)
        self.assertEqual(self.fila_de("A-01")[0], 8)

    def test_suma_desde_stock_cero(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 0)
        r = self.repo.registrar_ingreso("A-01", 4, None, self.uid, FECHA_FIJA)
        self.assertEqual(r.producto.stock, 4)

    def test_nombre_distinto_en_codigo_existente_se_ignora(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        r = self.repo.registrar_ingreso("A-01", 1, "Otro nombre", self.uid, FECHA_FIJA)
        self.assertEqual(r.producto.nombre, "Tornillo")
        self.assertEqual(self.fila_de("A-01")[2], "Tornillo")

    def test_alta_de_codigo_nuevo(self):
        r = self.repo.registrar_ingreso("N-01", 10, "Arandela 6mm", self.uid, FECHA_FIJA)
        self.assertTrue(r.creado)
        self.assertFalse(r.reactivado)
        self.assertEqual(
            (r.producto.codigo, r.producto.nombre, r.producto.stock),
            ("N-01", "Arandela 6mm", 10),
        )
        self.assertEqual(self.fila_de("N-01"), (10, 1, "Arandela 6mm"))

    def test_reactivacion_de_inactivo(self):
        insertar_producto(self.conn, "C-99", "Viejo", 2, activo=0)
        r = self.repo.registrar_ingreso("C-99", 3, "Nombre nuevo", self.uid, FECHA_FIJA)
        self.assertTrue(r.reactivado)
        self.assertFalse(r.creado)
        self.assertEqual(self.fila_de("C-99"), (5, 1, "Viejo"))
        self.assertEqual(self.cantidad_productos("C-99"), 1)

    def test_codigo_inexistente_sin_nombre_no_escribe(self):
        with self.assertRaises(NombreRequerido) as ctx:
            self.repo.registrar_ingreso("N-02", 3, None, self.uid, FECHA_FIJA)
        self.assertEqual(ctx.exception.codigo, "N-02")
        self.assertEqual(self.cantidad_productos("N-02"), 0)
        self.assertEqual(movimientos(self.conn), [])


class FechaMovimientoTest(RepoBase):
    def test_suma_y_alta_registran_un_movimiento_con_fecha(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.repo.registrar_ingreso("A-01", 3, None, self.uid, FECHA_FIJA)
        self.repo.registrar_ingreso("N-01", 7, "Nuevo", self.uid, FECHA_FIJA)
        self.assertEqual(
            movimientos(self.conn),
            [
                ("ingreso", 3, "A-01", self.uid, TEXTO_FECHA),
                ("ingreso", 7, "N-01", self.uid, TEXTO_FECHA),
            ],
        )

    def test_fecha_en_otra_zona_se_convierte_a_menos_tres(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        utc = datetime(2026, 11, 19, 18, 30, tzinfo=timezone.utc)
        self.repo.registrar_ingreso("A-01", 1, None, self.uid, utc)
        self.assertEqual(movimientos(self.conn)[0][4], TEXTO_FECHA)

    def test_fecha_naive_lanza_value_error_sin_escribir(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.conn.commit()
        with self.assertRaises(ValueError):
            self.repo.registrar_ingreso(
                "A-01", 1, None, self.uid, datetime(2026, 11, 19, 15, 30)
            )
        self.assertEqual(self.fila_de("A-01")[0], 5)
        self.assertEqual(movimientos(self.conn), [])


class EgresoTest(RepoBase):
    def test_egreso_parcial_registra_movimiento(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 8)
        p = self.repo.registrar_egreso("A-01", 3, self.uid, FECHA_FIJA)
        self.assertEqual(p.stock, 5)
        self.assertEqual(
            movimientos(self.conn), [("egreso", 3, "A-01", self.uid, TEXTO_FECHA)]
        )

    def test_egreso_de_todo_deja_cero_y_activo(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        p = self.repo.registrar_egreso("A-01", 5, self.uid, FECHA_FIJA)
        self.assertEqual(p.stock, 0)
        self.assertTrue(p.activo)
        self.assertEqual(self.fila_de("A-01")[:2], (0, 1))

    def test_exceso_informa_disponible_y_no_cambia_nada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        with self.assertRaises(StockInsuficiente) as ctx:
            self.repo.registrar_egreso("A-01", 6, self.uid, FECHA_FIJA)
        self.assertEqual((ctx.exception.disponible, ctx.exception.solicitado), (5, 6))
        self.assertEqual(self.fila_de("A-01")[0], 5)
        self.assertEqual(movimientos(self.conn), [])

    def test_stock_cero_se_rechaza(self):
        insertar_producto(self.conn, "B-10", "Tuerca", 0)
        with self.assertRaises(StockInsuficiente):
            self.repo.registrar_egreso("B-10", 1, self.uid, FECHA_FIJA)

    def test_inexistente_e_inactivo_no_se_encuentran(self):
        insertar_producto(self.conn, "C-99", "Viejo", 3, activo=0)
        for codigo in ("X-00", "C-99"):
            with self.subTest(codigo=codigo):
                with self.assertRaises(ProductoNoEncontrado):
                    self.repo.registrar_egreso(codigo, 1, self.uid, FECHA_FIJA)
        self.assertEqual(self.fila_de("C-99")[0], 3)
        self.assertEqual(movimientos(self.conn), [])


class AtomicidadTest(RepoBase):
    """Un usuario_id inexistente rompe el INSERT del movimiento: debe revertir todo."""

    def test_ingreso_suma_se_revierte(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar_ingreso("A-01", 3, None, 999, FECHA_FIJA)
        self.assertEqual(self.fila_de("A-01")[0], 5)
        self.assertEqual(movimientos(self.conn), [])

    def test_alta_se_revierte(self):
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar_ingreso("N-05", 3, "Nuevo", 999, FECHA_FIJA)
        self.assertEqual(self.cantidad_productos("N-05"), 0)
        self.assertEqual(movimientos(self.conn), [])

    def test_egreso_se_revierte(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar_egreso("A-01", 2, 999, FECHA_FIJA)
        self.assertEqual(self.fila_de("A-01")[0], 5)
        self.assertEqual(movimientos(self.conn), [])


class TransaccionPendienteTest(RepoBase):
    """S-2: una escritura sin confirmar no se confirma en silencio."""

    def test_egreso_con_insert_pendiente_lanza_runtimeerror(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.conn.execute(
            "INSERT INTO productos (codigo, nombre, stock) VALUES ('P-01', 'Pendiente', 1)"
        )
        with self.assertRaises(RuntimeError):
            self.repo.registrar_egreso("A-01", 1, self.uid, FECHA_FIJA)
        self.conn.rollback()
        self.assertEqual(self.cantidad_productos("P-01"), 0)
        self.assertEqual(self.fila_de("A-01")[0], 5)

    def test_ingreso_con_insert_pendiente_lanza_runtimeerror(self):
        self.conn.execute(
            "INSERT INTO productos (codigo, nombre, stock) VALUES ('P-02', 'Pendiente', 1)"
        )
        with self.assertRaises(RuntimeError):
            self.repo.registrar_ingreso("N-09", 1, "Nuevo", self.uid, FECHA_FIJA)
        self.conn.rollback()
        self.assertEqual(self.cantidad_productos("P-02"), 0)
        self.assertEqual(self.cantidad_productos("N-09"), 0)


class ConcurrenciaTest(unittest.TestCase):
    """Archivo temporal: dos conexiones reales (no es un mock; ver D8)."""

    def test_dos_egresos_simultaneos_solo_uno_pasa(self):
        for ronda in range(5):
            with self.subTest(ronda=ronda):
                self._una_ronda()

    def _una_ronda(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "c.db")
            prep = conectar(ruta)
            inicializar_esquema(prep)
            uid = insertar_usuario(prep)
            insertar_producto(prep, "A-01", "Tornillo", 5)
            prep.commit()
            prep.close()

            barrera = threading.Barrier(2)
            resultados = []

            def egresar():
                conn = conectar(ruta)
                try:
                    repo = SqliteStockRepository(conn)
                    barrera.wait()
                    try:
                        repo.registrar_egreso("A-01", 3, uid, FECHA_FIJA)
                        resultados.append("ok")
                    except StockInsuficiente:
                        resultados.append("insuficiente")
                finally:
                    conn.close()

            hilos = [threading.Thread(target=egresar) for _ in range(2)]
            for h in hilos:
                h.start()
            for h in hilos:
                h.join()

            self.assertEqual(sorted(resultados), ["insuficiente", "ok"])
            conn = conectar(ruta)
            try:
                stock = conn.execute(
                    "SELECT stock FROM productos WHERE codigo = 'A-01'"
                ).fetchone()[0]
                self.assertEqual(stock, 2)
                self.assertEqual(len(movimientos(conn)), 1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
