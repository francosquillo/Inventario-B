import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, datetime

from inventario.domain.entities import (
    Faltante,
    ItemOrden,
    Orden,
    Reintegro,
    ResultadoBorradoOrden,
)
from inventario.domain.errors import (
    OrdenDuplicada,
    OrdenNoEncontrada,
    ProductosNoEncontrados,
    StockInsuficienteOrden,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    _SQL_ORDEN_EXISTE,
    SqliteOrdenRepository,
    SqliteProductoRepository,
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


class ListarTest(RepoBase):
    def sembrar_orden(self, numero, fecha, items=(("A-01", 1),), cuando=FECHA_FIJA):
        return self.repo.crear(numero, fecha, list(items), self.uid, cuando)

    def numeros(self, **filtros):
        args = {"numero": None, "desde": None, "hasta": None, **filtros}
        return [o.numero for o in self.repo.listar(args["numero"], args["desde"], args["hasta"])]

    def test_sin_filtros_devuelve_ordenes_de_la_mas_nueva_a_la_mas_vieja(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        self.sembrar_orden("OT-1", date(2026, 11, 18))
        self.sembrar_orden("OT-2", date(2026, 11, 20))
        self.sembrar_orden("OT-3", date(2026, 11, 17))
        ordenes = self.repo.listar(None, None, None)
        self.assertEqual([o.numero for o in ordenes], ["OT-2", "OT-1", "OT-3"])
        primera = ordenes[0]
        self.assertIsInstance(primera, Orden)
        self.assertEqual(primera.fecha, date(2026, 11, 20))
        self.assertEqual(primera.usuario, "admin")
        self.assertEqual(primera.items, (ItemOrden("A-01", "Tornillo", 1),))

    def test_desempata_por_id_descendente_y_ordena_por_fecha_no_por_created_at(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        antes = datetime(2026, 11, 1, 8, 0, tzinfo=ZONA_AR)
        despues = datetime(2026, 11, 30, 8, 0, tzinfo=ZONA_AR)
        self.sembrar_orden("OT-NUEVA", date(2026, 11, 19), cuando=antes)
        self.sembrar_orden("OT-VIEJA", date(2025, 1, 15), cuando=despues)
        self.sembrar_orden("OT-A", date(2026, 11, 19))
        self.sembrar_orden("OT-B", date(2026, 11, 19))
        self.assertEqual(self.numeros(), ["OT-B", "OT-A", "OT-NUEVA", "OT-VIEJA"])

    def test_componentes_ordenados_por_codigo_con_nombre_y_cantidad(self):
        self.sembrar_basico()
        self.sembrar_orden("OT-1", FECHA_ORDEN, items=(("B-02", 5), ("A-01", 2)))
        (orden,) = self.repo.listar(None, None, None)
        self.assertEqual(
            orden.items, (ItemOrden("A-01", "Tornillo", 2), ItemOrden("B-02", "Tuerca", 5))
        )

    def test_sin_ordenes_devuelve_lista_vacia(self):
        self.assertEqual(self.repo.listar(None, None, None), [])

    def test_producto_dado_de_baja_sigue_en_los_componentes(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "C-99", "Viejo", 5)
        self.sembrar_orden("OT-1", FECHA_ORDEN, items=(("A-01", 1), ("C-99", 3)))
        self.conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'C-99'")
        self.conn.commit()
        (orden,) = self.repo.listar(None, None, None)
        self.assertEqual(
            orden.items, (ItemOrden("A-01", "Tornillo", 1), ItemOrden("C-99", "Viejo", 3))
        )

    def insertar_orden_sin_items(self, numero, fecha):
        self.conn.execute(
            "INSERT INTO ordenes (numero, fecha, usuario_id, created_at) VALUES (?, ?, ?, ?)",
            (numero, fecha.isoformat(), self.uid, "2026-11-19T15:30:00-03:00"),
        )
        self.conn.commit()

    def test_orden_sin_items_aparece_con_componentes_vacios(self):
        self.insertar_orden_sin_items("OT-VACIA", date(2026, 11, 20))
        (orden,) = self.repo.listar(None, None, None)
        self.assertEqual(orden.numero, "OT-VACIA")
        self.assertEqual(orden.items, ())
        self.assertEqual(self.numeros(numero="OT-VACIA"), ["OT-VACIA"])

    def test_orden_sin_items_convive_con_ordenes_normales_agrupadas_y_ordenadas(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        insertar_producto(self.conn, "B-02", "Tuerca", 50)
        self.sembrar_orden("OT-1", date(2026, 11, 18), items=(("B-02", 5), ("A-01", 2)))
        self.insertar_orden_sin_items("OT-VACIA", date(2026, 11, 19))
        self.sembrar_orden("OT-3", date(2026, 11, 20), items=(("A-01", 1),))
        ordenes = self.repo.listar(None, None, None)
        self.assertEqual([o.numero for o in ordenes], ["OT-3", "OT-VACIA", "OT-1"])
        self.assertEqual(ordenes[0].items, (ItemOrden("A-01", "Tornillo", 1),))
        self.assertEqual(ordenes[1].items, ())
        self.assertEqual(
            ordenes[2].items, (ItemOrden("A-01", "Tornillo", 2), ItemOrden("B-02", "Tuerca", 5))
        )

    def test_orden_con_todos_los_productos_dados_de_baja_sigue_listada_con_sus_items(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 5)
        self.sembrar_orden("OT-1", FECHA_ORDEN, items=(("A-01", 1), ("B-02", 3)))
        self.conn.execute("UPDATE productos SET activo = 0")
        self.conn.commit()
        (orden,) = self.repo.listar(None, None, None)
        self.assertEqual(
            orden.items, (ItemOrden("A-01", "Tornillo", 1), ItemOrden("B-02", "Tuerca", 3))
        )

    def sembrar_cuatro_dias(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        for dia in (17, 18, 19, 20):
            self.sembrar_orden(f"OT-{dia}", date(2026, 11, dia))

    def test_rango_inclusivo_en_ambos_bordes(self):
        self.sembrar_cuatro_dias()
        self.assertEqual(
            self.numeros(desde=date(2026, 11, 18), hasta=date(2026, 11, 19)), ["OT-19", "OT-18"]
        )
        self.assertEqual(
            self.numeros(desde=date(2026, 11, 19), hasta=date(2026, 11, 19)), ["OT-19"]
        )

    def test_rangos_abiertos_y_rango_sin_resultados(self):
        self.sembrar_cuatro_dias()
        self.assertEqual(self.numeros(desde=date(2026, 11, 18)), ["OT-20", "OT-19", "OT-18"])
        self.assertEqual(self.numeros(hasta=date(2026, 11, 18)), ["OT-18", "OT-17"])
        self.assertEqual(
            self.numeros(desde=date(2026, 12, 1), hasta=date(2026, 12, 31)), []
        )

    def test_numero_exacto_devuelve_solo_esa_orden_con_sus_items(self):
        self.sembrar_basico()
        self.sembrar_orden("OT-0001", date(2026, 11, 17))
        self.sembrar_orden("OT-0002", date(2026, 11, 20), items=(("B-02", 5), ("A-01", 2)))
        (orden,) = self.repo.listar("OT-0002", None, None)
        self.assertEqual(orden.numero, "OT-0002")
        self.assertEqual(
            orden.items, (ItemOrden("A-01", "Tornillo", 2), ItemOrden("B-02", "Tuerca", 5))
        )

    def test_numero_no_es_prefijo_ni_parcial(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        self.sembrar_orden("OT-1", FECHA_ORDEN)
        self.sembrar_orden("OT-10", FECHA_ORDEN)
        self.assertEqual(self.numeros(numero="OT-1"), ["OT-1"])

    def test_numero_se_combina_con_fechas_por_and(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        self.sembrar_orden("OT-0001", date(2026, 11, 17))
        self.assertEqual(self.numeros(numero="OT-0001", desde=date(2026, 11, 18)), [])
        self.assertEqual(self.numeros(numero="OT-0001", desde=date(2026, 11, 17)), ["OT-0001"])

    def test_existe_numero_es_exacto(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 50)
        self.sembrar_orden("OT-0001", FECHA_ORDEN)
        self.sembrar_orden("OT-10", FECHA_ORDEN)
        self.assertTrue(self.repo.existe_numero("OT-0001"))
        self.assertFalse(self.repo.existe_numero("OT-9999"))
        self.assertFalse(self.repo.existe_numero("OT-1"))

    def test_listar_ejecuta_tres_selects_sin_importar_cuantas_ordenes_hay(self):
        self.sembrar_basico()
        for n in ("OT-1", "OT-2", "OT-3"):
            self.sembrar_orden(n, FECHA_ORDEN, items=(("A-01", 1), ("B-02", 1)))
        sentencias = []
        self.conn.set_trace_callback(sentencias.append)
        ordenes = self.repo.listar(None, None, None)
        self.conn.set_trace_callback(None)
        self.assertEqual(len(ordenes), 3)
        # Ordenes+componentes y, por lote, procesos (C-06f D5) y servicio (C-06g D5): no crece
        # con las ordenes.
        self.assertEqual(sum(1 for s in sentencias if s.lstrip().upper().startswith("SELECT")), 3)
        self.assertEqual(len(sentencias), 3)


class BorrarBase(RepoBase):
    """Siembra: A-01 (5) -> orden x2 deja 3; B-02 (5) -> orden x5 deja 0."""

    def setUp(self):
        super().setUp()
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 5)
        self.orden = self.crear(items=(("A-01", 2), ("B-02", 5)))

    def numeros(self):
        return [o.numero for o in self.repo.listar(None, None, None)]

    def activos(self):
        filas = self.conn.execute("SELECT codigo, activo FROM productos ORDER BY codigo")
        return [tuple(f) for f in filas]


class BorrarSinReintegroTest(BorrarBase):
    def test_borra_orden_y_lineas_sin_tocar_stock(self):
        res = self.repo.borrar("OT-0001", False)
        self.assertIsInstance(res, ResultadoBorradoOrden)
        self.assertEqual(res.orden, self.orden)
        self.assertEqual(res.orden.id, self.orden.id)
        self.assertIs(res.reintegrado, False)
        self.assertEqual(res.reintegros, ())
        self.assertEqual(self.cuenta("ordenes"), 0)
        self.assertEqual(self.cuenta("orden_items"), 0)
        self.assertEqual(self.stocks(), {"A-01": 3, "B-02": 0})
        self.assertFalse(self.conn.in_transaction)


class BorrarConReintegroTest(BorrarBase):
    def test_devuelve_stock_y_detalla_los_reintegros(self):
        res = self.repo.borrar("OT-0001", True)
        self.assertIs(res.reintegrado, True)
        self.assertEqual(
            res.reintegros,
            (
                Reintegro("A-01", "Tornillo", 2, 5, False),
                Reintegro("B-02", "Tuerca", 5, 5, False),
            ),
        )
        self.assertEqual(self.stocks(), {"A-01": 5, "B-02": 5})
        self.assertEqual((self.cuenta("ordenes"), self.cuenta("orden_items")), (0, 0))
        self.assertFalse(self.conn.in_transaction)

    def test_reintegros_ordenados_por_codigo(self):
        insertar_producto(self.conn, "Z-1", "Zeta", 1)
        insertar_producto(self.conn, "C-1", "Ce", 1)
        self.crear("OT-0002", (("Z-1", 1), ("C-1", 1)))
        res = self.repo.borrar("OT-0002", True)
        self.assertEqual([r.codigo for r in res.reintegros], ["C-1", "Z-1"])

    def _orden_con_producto_dado_de_baja(self):
        insertar_producto(self.conn, "C-99", "Viejo", 5)
        self.crear("OT-0002", (("C-99", 4),))
        self.conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'C-99'")
        self.conn.commit()

    def test_reactiva_producto_dado_de_baja(self):
        self._orden_con_producto_dado_de_baja()
        res = self.repo.borrar("OT-0002", True)
        self.assertEqual(res.reintegros, (Reintegro("C-99", "Viejo", 4, 5, True),))
        self.assertEqual(self.stocks()["C-99"], 5)
        codigos = [p.codigo for p in SqliteProductoRepository(self.conn).listar_activos()]
        self.assertIn("C-99", codigos)

    def test_sin_reintegro_no_reactiva(self):
        self._orden_con_producto_dado_de_baja()
        res = self.repo.borrar("OT-0002", False)
        self.assertEqual(res.reintegros, ())
        fila = self.conn.execute("SELECT stock, activo FROM productos WHERE codigo='C-99'").fetchone()
        self.assertEqual(tuple(fila), (1, 0))

    def test_aislamiento_solo_devuelve_lo_de_la_orden_borrada(self):
        self.crear("OT-0002", (("A-01", 1),))
        self.assertEqual(self.stocks()["A-01"], 2)
        res = self.repo.borrar("OT-0001", True)
        self.assertEqual(self.stocks()["A-01"], 4)
        self.assertEqual(res.reintegros[0], Reintegro("A-01", "Tornillo", 2, 4, False))
        restantes = self.repo.listar(None, None, None)
        self.assertEqual(
            [(o.numero, [(i.codigo, i.cantidad) for i in o.items]) for o in restantes],
            [("OT-0002", [("A-01", 1)])],
        )


class BorrarInexistenteTest(BorrarBase):
    def test_inexistente_con_y_sin_reintegro(self):
        for reintegrar in (True, False):
            with self.subTest(reintegrar=reintegrar):
                with self.assertRaises(OrdenNoEncontrada) as ctx:
                    self.repo.borrar("OT-0999", reintegrar)
                self.assertEqual(str(ctx.exception), "No existe una orden con número 'OT-0999'.")
                self.assertFalse(self.conn.in_transaction)
        self.assertEqual(self.stocks(), {"A-01": 3, "B-02": 0})
        self.assertEqual(self.numeros(), ["OT-0001"])

    def test_segundo_borrado_del_mismo_numero_no_reintegra_otra_vez(self):
        self.repo.borrar("OT-0001", True)
        with self.assertRaises(OrdenNoEncontrada):
            self.repo.borrar("OT-0001", True)
        self.assertEqual(self.stocks(), {"A-01": 5, "B-02": 5})
        self.assertFalse(self.conn.in_transaction)

    def test_numero_con_barras_borra_solo_esa(self):
        self.crear("OT/2026/01", (("A-01", 1),))
        self.repo.borrar("OT/2026/01", True)
        self.assertEqual(self.numeros(), ["OT-0001"])
        self.assertEqual(self.stocks()["A-01"], 3)

    def test_no_escribe_movimientos(self):
        self.conn.execute(
            "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
            "VALUES ('2026-11-19T10:00:00-03:00', 1, 'ingreso', 5, ?)",
            (self.uid,),
        )
        self.conn.commit()
        antes = movimientos(self.conn)
        self.repo.borrar("OT-0001", True)
        self.crear("OT-0002", (("A-01", 1),))
        self.repo.borrar("OT-0002", False)
        self.assertEqual(movimientos(self.conn), antes)


class BorrarAtomicidadTest(BorrarBase):
    def estado(self):
        return (self.stocks(), self.activos(), self.numeros(), self.cuenta("orden_items"))

    def test_falla_a_mitad_del_reintegro_revierte_todo(self):
        antes = self.estado()
        self.conn.execute(
            "CREATE TEMP TRIGGER falla BEFORE UPDATE OF stock ON productos "
            "WHEN OLD.codigo = 'B-02' BEGIN SELECT RAISE(ABORT, 'falla forzada'); END"
        )
        with self.assertRaises(sqlite3.DatabaseError):
            self.repo.borrar("OT-0001", True)
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.stocks(), {"A-01": 3, "B-02": 0})
        self.assertEqual(self.cuenta("orden_items"), 2)
        self.assertFalse(self.conn.in_transaction)

    def test_falla_al_borrar_revierte_reintegro_y_reactivacion(self):
        insertar_producto(self.conn, "C-99", "Viejo", 5)
        self.crear("OT-0002", (("C-99", 4),))
        self.conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'C-99'")
        self.conn.commit()
        antes = self.estado()
        self.conn.execute(
            "CREATE TEMP TRIGGER falla BEFORE DELETE ON ordenes "
            "BEGIN SELECT RAISE(ABORT, 'falla forzada'); END"
        )
        for numero in ("OT-0001", "OT-0002"):
            with self.subTest(numero=numero):
                with self.assertRaises(sqlite3.DatabaseError):
                    self.repo.borrar(numero, True)
                self.assertEqual(self.estado(), antes)
                self.assertFalse(self.conn.in_transaction)

    def test_linea_huerfana_aborta_el_reintegro(self):
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute("DELETE FROM productos WHERE codigo = 'B-02'")
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(RuntimeError):
            self.repo.borrar("OT-0001", True)
        self.assertEqual(self.numeros(), ["OT-0001"])
        self.assertEqual(self.stocks(), {"A-01": 3})
        self.assertFalse(self.conn.in_transaction)
        # Sin reintegro la orden (aun con la linea huerfana) se puede borrar.
        res = self.repo.borrar("OT-0001", False)
        self.assertEqual(res.reintegros, ())
        self.assertEqual(self.numeros(), [])


class BorrarConcurrenciaTest(unittest.TestCase):
    def test_dos_borrados_simultaneos_de_la_misma_orden_solo_uno_gana(self):
        for ronda in range(5):
            with self.subTest(ronda=ronda):
                with tempfile.TemporaryDirectory() as tmp:
                    ruta = os.path.join(tmp, "c.db")
                    prep = conectar(ruta)
                    inicializar_esquema(prep)
                    uid = insertar_usuario(prep)
                    insertar_producto(prep, "A-01", "Tornillo", 5)
                    SqliteOrdenRepository(prep).crear(
                        "OT-0001", FECHA_ORDEN, [("A-01", 2)], uid, FECHA_FIJA
                    )
                    prep.close()

                    barrera = threading.Barrier(2)
                    resultados = []

                    def trabajar():
                        conn = conectar(ruta)
                        try:
                            repo = SqliteOrdenRepository(conn)
                            barrera.wait()
                            try:
                                repo.borrar("OT-0001", True)
                                resultados.append("ok")
                            except OrdenNoEncontrada:
                                resultados.append("inexistente")
                        finally:
                            conn.close()

                    hilos = [threading.Thread(target=trabajar) for _ in range(2)]
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
                    self.assertEqual(sorted(resultados), ["inexistente", "ok"])
                    self.assertEqual((final, ordenes), (5, 0))
