import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, datetime

from inventario.domain.entities import Faltante, Orden
from inventario.domain.errors import (
    OrdenDuplicada,
    ProductosNoEncontrados,
    StockInsuficienteOrden,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    _SQL_ORDEN_EXISTE,
    SqliteOrdenRepository,
    conectar,
    inicializar_esquema,
)
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
FECHA_ORDEN = date(2026, 11, 20)


class RepoBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteOrdenRepository(self.conn)

    def stocks(self):
        filas = self.conn.execute(
            "SELECT codigo, stock FROM productos ORDER BY codigo"
        ).fetchall()
        return {f["codigo"]: f["stock"] for f in filas}

    def cuenta(self, tabla):
        return self.conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def sembrar_basico(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 10)

    def crear(self, numero="OT-0001", items=(("A-01", 2), ("B-02", 10)), uid=None, cuando=FECHA_FIJA):
        return self.repo.crear(numero, FECHA_ORDEN, list(items), uid or self.uid, cuando)

    def assertSinEscritura(self, stocks_esperados):
        self.assertEqual(self.cuenta("ordenes"), 0)
        self.assertEqual(self.cuenta("orden_items"), 0)
        self.assertEqual(self.stocks(), stocks_esperados)


class AltaTest(RepoBase):
    def test_crea_orden_devuelve_entidad_y_descuenta_stock(self):
        self.sembrar_basico()
        orden = self.crear(items=(("B-02", 10), ("A-01", 2)))
        self.assertIsInstance(orden, Orden)
        self.assertEqual((orden.numero, orden.fecha, orden.usuario), ("OT-0001", FECHA_ORDEN, "admin"))
        self.assertEqual(
            [(i.codigo, i.nombre, i.cantidad) for i in orden.items],
            [("A-01", "Tornillo", 2), ("B-02", "Tuerca", 10)],
        )
        self.assertEqual(self.stocks(), {"A-01": 3, "B-02": 0})

    def test_filas_persistidas_y_created_at_explicito(self):
        self.sembrar_basico()
        orden = self.crear()
        fila = self.conn.execute(
            "SELECT id, numero, fecha, usuario_id, created_at FROM ordenes"
        ).fetchone()
        self.assertEqual(
            tuple(fila), (orden.id, "OT-0001", "2026-11-20", self.uid, "2026-11-19T15:30:00-03:00")
        )
        lineas = self.conn.execute(
            "SELECT p.codigo, i.cantidad FROM orden_items i JOIN productos p ON p.id = i.producto_id "
            "WHERE i.orden_id = ? ORDER BY p.codigo",
            (orden.id,),
        ).fetchall()
        self.assertEqual([tuple(x) for x in lineas], [("A-01", 2), ("B-02", 10)])

    def test_stock_en_cero_sigue_activo_y_no_hay_movimientos(self):
        self.sembrar_basico()
        self.crear()
        activo = self.conn.execute("SELECT activo FROM productos WHERE codigo = 'B-02'").fetchone()[0]
        self.assertEqual(activo, 1)
        self.assertEqual(movimientos(self.conn), [])

    def test_orden_con_un_solo_componente(self):
        self.sembrar_basico()
        orden = self.crear("OT-0002", (("A-01", 5),))
        self.assertEqual(len(orden.items), 1)
        self.assertEqual(self.stocks(), {"A-01": 0, "B-02": 10})


class RechazosTest(RepoBase):
    def setUp(self):
        super().setUp()
        self.sembrar_basico()
        insertar_producto(self.conn, "C-99", "Inactivo", 4, activo=0)
        insertar_producto(self.conn, "D-04", "Arandela", 9)
        self.base = {"A-01": 5, "B-02": 10, "C-99": 4, "D-04": 9}

    def test_numero_duplicado(self):
        self.crear("OT-0001", (("A-01", 1),))
        with self.assertRaises(OrdenDuplicada) as ctx:
            self.crear("OT-0001", (("B-02", 1),))
        self.assertEqual(ctx.exception.numero, "OT-0001")
        self.assertEqual(self.cuenta("ordenes"), 1)
        self.assertEqual(self.cuenta("orden_items"), 1)
        self.assertEqual(self.stocks()["B-02"], 10)

    def test_producto_inexistente(self):
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.crear(items=(("A-01", 1), ("X-00", 1)))
        self.assertEqual(ctx.exception.codigos, ("X-00",))
        self.assertSinEscritura(self.base)

    def test_inexistente_e_inactivo_en_orden_de_aparicion(self):
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.crear(items=(("X-00", 1), ("A-01", 1), ("C-99", 1)))
        self.assertEqual(ctx.exception.codigos, ("X-00", "C-99"))
        self.assertSinEscritura(self.base)
        self.assertEqual(
            self.conn.execute("SELECT activo FROM productos WHERE codigo='C-99'").fetchone()[0], 0
        )

    def test_un_faltante(self):
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.crear(items=(("A-01", 6), ("B-02", 1)))
        self.assertEqual(ctx.exception.faltantes, (Faltante("A-01", 5, 6),))
        self.assertSinEscritura(self.base)

    def test_varios_faltantes_en_orden_de_aparicion(self):
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.crear(items=(("A-01", 6), ("D-04", 1), ("B-02", 11)))
        self.assertEqual(
            ctx.exception.faltantes, (Faltante("A-01", 5, 6), Faltante("B-02", 10, 11))
        )
        self.assertSinEscritura(self.base)

    def test_stock_cero_cuenta_como_faltante(self):
        self.crear("OT-0001", (("B-02", 10),))
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.crear("OT-0002", (("B-02", 1),))
        self.assertEqual(ctx.exception.faltantes, (Faltante("B-02", 0, 1),))

    def test_prioridad_duplicado_sobre_stock(self):
        self.crear("OT-0001", (("A-01", 1),))
        with self.assertRaises(OrdenDuplicada):
            self.crear("OT-0001", (("A-01", 999),))

    def test_prioridad_inexistente_sobre_stock(self):
        with self.assertRaises(ProductosNoEncontrados):
            self.crear(items=(("A-01", 999), ("X-00", 1)))

    def test_prioridad_duplicado_sobre_inexistente(self):
        self.crear("OT-0001", (("A-01", 1),))
        with self.assertRaises(OrdenDuplicada):
            self.crear("OT-0001", (("X-00", 1),))


class ConexionQueNoVeDuplicados:
    """Conexion SQLite real salvo en el chequeo previo de numero: lo da por libre.

    Reproduce la carrera "otro proceso inserto el numero entre el chequeo y el
    INSERT": el UNIQUE de la base real es lo que dispara el respaldo.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *args):
        if sql == _SQL_ORDEN_EXISTE:
            return self._conn.execute("SELECT 1 WHERE 0")
        return self._conn.execute(sql, *args)

    def __getattr__(self, nombre):
        return getattr(self._conn, nombre)


class RespaldoUniqueNumeroTest(RepoBase):
    def setUp(self):
        super().setUp()
        self.sembrar_basico()
        self.repo = SqliteOrdenRepository(ConexionQueNoVeDuplicados(self.conn))

    def test_unique_de_numero_se_traduce_a_orden_duplicada(self):
        self.crear(numero="OT-0001", items=(("A-01", 1),))
        with self.assertRaises(OrdenDuplicada) as ctx:
            self.crear(numero="OT-0001", items=(("A-01", 2), ("B-02", 3)))
        self.assertEqual(ctx.exception.numero, "OT-0001")
        self.assertEqual(self.cuenta("ordenes"), 1)
        self.assertEqual(self.cuenta("orden_items"), 1)
        self.assertEqual(self.stocks(), {"A-01": 4, "B-02": 10})
        self.assertFalse(self.conn.in_transaction)

    def test_otro_numero_no_dispara_el_respaldo(self):
        self.crear(numero="OT-0001", items=(("A-01", 1),))
        orden = self.crear(numero="OT-0002", items=(("B-02", 3),))
        self.assertEqual(orden.numero, "OT-0002")
        self.assertEqual(self.cuenta("ordenes"), 2)

    def test_otro_integrity_error_se_propaga_sin_traducir(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.crear(numero="OT-0009", items=(("A-01", 1),), uid=999)
        self.assertEqual(self.cuenta("ordenes"), 0)
        self.assertEqual(self.stocks(), {"A-01": 5, "B-02": 10})


class AtomicidadTest(RepoBase):
    def test_usuario_inexistente_revierte_todo(self):
        self.sembrar_basico()
        with self.assertRaises(sqlite3.IntegrityError):
            self.crear(items=(("A-01", 2), ("B-02", 3)), uid=999)
        self.assertSinEscritura({"A-01": 5, "B-02": 10})

    def test_fecha_naive_no_escribe(self):
        self.sembrar_basico()
        with self.assertRaises(ValueError):
            self.crear(cuando=datetime(2026, 11, 19, 15, 30))
        self.assertSinEscritura({"A-01": 5, "B-02": 10})

    def test_transaccion_pendiente_lanza_runtimeerror(self):
        self.sembrar_basico()
        self.conn.execute("INSERT INTO productos (codigo, nombre) VALUES ('P-01', 'Pend')")
        with self.assertRaises(RuntimeError):
            self.crear()
        self.conn.rollback()
        self.assertSinEscritura({"A-01": 5, "B-02": 10})


class ConcurrenciaTest(unittest.TestCase):
    """Archivo temporal: dos conexiones reales (no es un mock)."""

    def _ejecutar(self, stock, pedidos):
        """pedidos: lista de (numero, items). Devuelve (resultados, stock_final, ordenes)."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "c.db")
            prep = conectar(ruta)
            inicializar_esquema(prep)
            uid = insertar_usuario(prep)
            insertar_producto(prep, "A-01", "Tornillo", stock)
            prep.close()

            barrera = threading.Barrier(len(pedidos))
            resultados = []

            def trabajar(numero, items):
                conn = conectar(ruta)
                try:
                    repo = SqliteOrdenRepository(conn)
                    barrera.wait()
                    try:
                        repo.crear(numero, FECHA_ORDEN, items, uid, FECHA_FIJA)
                        resultados.append("ok")
                    except StockInsuficienteOrden:
                        resultados.append("stock")
                    except OrdenDuplicada:
                        resultados.append("duplicada")
                finally:
                    conn.close()

            hilos = [threading.Thread(target=trabajar, args=p) for p in pedidos]
            for h in hilos:
                h.start()
            for h in hilos:
                h.join()

            conn = conectar(ruta)
            try:
                final = conn.execute("SELECT stock FROM productos").fetchone()[0]
                ordenes = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
            finally:
                conn.close()
            return sorted(resultados), final, ordenes

    def test_stock_compartido_una_orden_gana(self):
        for ronda in range(5):
            with self.subTest(ronda=ronda):
                res, final, ordenes = self._ejecutar(
                    5, [("OT-1", [("A-01", 3)]), ("OT-2", [("A-01", 3)])]
                )
                self.assertEqual(res, ["ok", "stock"])
                self.assertEqual((final, ordenes), (2, 1))

    def test_mismo_numero_una_orden_gana(self):
        for ronda in range(5):
            with self.subTest(ronda=ronda):
                res, final, ordenes = self._ejecutar(
                    10, [("OT-0009", [("A-01", 1)]), ("OT-0009", [("A-01", 1)])]
                )
                self.assertEqual(res, ["duplicada", "ok"])
                self.assertEqual((final, ordenes), (9, 1))
