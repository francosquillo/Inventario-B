"""Edicion atomica de ordenes con ajuste de stock por diferencia (C-06i, design D2/D3/D5)."""
import sqlite3
import unittest
from datetime import date, datetime

from inventario.domain.entities import (
    AjusteStock,
    ChequeoFinal,
    DatosOrden,
    Faltante,
    ProcesoOrden,
    ServicioOrden,
)
from inventario.domain.errors import (
    DatosInvalidos,
    OrdenNoEncontrada,
    ProductosNoEncontrados,
    StockInsuficienteOrden,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteOrdenRepository
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

CREADA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
FECHA = date(2026, 11, 27)


class EdicionBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.repo = SqliteOrdenRepository(self.conn)

    def stocks(self):
        return {
            f["codigo"]: (f["stock"], f["activo"])
            for f in self.conn.execute("SELECT codigo, stock, activo FROM productos ORDER BY codigo")
        }

    def stock(self, codigo):
        return self.stocks()[codigo][0]

    def orden(self, numero="OT-0043", items=(("A-01", 2, None),), **extra):
        """Alta real por el repo (descuenta stock como en produccion)."""
        return self.repo.crear(numero, FECHA, list(items), self.uid, CREADA, **extra)

    def editar(self, numero="OT-0043", fecha=FECHA, items=(("A-01", 2, None),), procesos=(),
               servicio=None, datos=DatosOrden(), chequeo_final=(), conservar_servicio=False):
        return self.repo.editar(
            numero, fecha, list(items), procesos, servicio, datos, chequeo_final, conservar_servicio
        )

    def lineas(self, numero="OT-0043"):
        (orden,) = self.repo.listar(numero, None, None)
        return [(i.codigo, i.cantidad, i.precio) for i in orden.items]

    def foto(self):
        """Estado completo observable: ordenes, lineas, procesos, servicio, chequeo y stocks."""
        tablas = (
            "ordenes", "orden_items", "orden_procesos", "orden_servicio",
            "orden_servicio_chequeos", "orden_chequeo_final", "productos", "movimientos",
        )
        return {
            t: [tuple(f) for f in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")]
            for t in tablas
        }


class AjusteDeStockTest(EdicionBase):
    def test_aumentar_la_cantidad_descuenta_la_diferencia_y_informa_el_ajuste(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.orden()  # x 2 -> stock 3
        self.conn.execute("UPDATE productos SET stock = 5")  # estado del escenario: stock 5
        self.conn.commit()
        resultado = self.editar(items=(("A-01", 4, None),))
        self.assertEqual(self.lineas(), [("A-01", 4, None)])
        self.assertEqual(self.stock("A-01"), 3)
        self.assertEqual(
            resultado.ajustes, (AjusteStock("A-01", "Tornillo", 2, 4, 3, False),)
        )
        self.assertEqual(resultado.orden.items[0].cantidad, 4)

    def test_reducir_la_cantidad_reintegra_la_diferencia(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 9)
        self.orden(items=(("A-01", 4, None),))  # stock 5
        resultado = self.editar(items=(("A-01", 1, None),))
        self.assertEqual(self.stock("A-01"), 8)
        self.assertEqual(resultado.ajustes, (AjusteStock("A-01", "Tornillo", 4, 1, 8, False),))

    def test_quitar_un_producto_y_agregar_otro(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 3)
        self.orden()  # A-01 stock 3
        self.conn.execute("UPDATE productos SET stock = 5 WHERE codigo = 'A-01'")
        self.conn.commit()
        resultado = self.editar(items=(("B-02", 3, None),))
        self.assertEqual(self.lineas(), [("B-02", 3, None)])
        self.assertEqual((self.stock("A-01"), self.stock("B-02")), (7, 0))
        self.assertEqual(
            resultado.ajustes,
            (
                AjusteStock("A-01", "Tornillo", 2, 0, 7, False),
                AjusteStock("B-02", "Tuerca", 0, 3, 0, False),
            ),
        )

    def test_solo_cambian_precios_no_toca_el_stock_ni_informa_ajustes(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        self.orden()  # stock 5
        resultado = self.editar(items=(("A-01", 2, 1200000),))
        self.assertEqual(self.lineas(), [("A-01", 2, 1200000)])
        self.assertEqual(self.stock("A-01"), 5)
        self.assertEqual(resultado.ajustes, ())

    def test_usar_todo_el_stock_mas_lo_ya_descontado(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 3)
        self.orden()  # x2 -> stock 1
        self.editar(items=(("A-01", 3, None),))
        self.assertEqual(self.stock("A-01"), 0)

    def test_edicion_identica_no_cambia_nada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        self.orden()
        antes = self.foto()
        resultado = self.editar()
        self.assertEqual(self.foto(), antes)
        self.assertEqual(resultado.ajustes, ())

    def test_ajustes_ordenados_por_codigo_solo_con_delta(self):
        insertar_producto(self.conn, "B-02", "Tuerca", 5)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "C-03", "Arandela", 5)
        self.orden(items=(("B-02", 1, None), ("A-01", 1, None), ("C-03", 1, None)))
        resultado = self.editar(
            items=(("C-03", 2, None), ("B-02", 1, None), ("A-01", 3, None))
        )
        self.assertEqual([a.codigo for a in resultado.ajustes], ["A-01", "C-03"])

    def test_no_escribe_movimientos(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 9)
        self.orden()
        antes = movimientos(self.conn)
        self.editar(items=(("A-01", 5, None),))
        self.assertEqual(movimientos(self.conn), antes)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 0)

    def test_dos_ediciones_seguidas(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 7)
        self.orden()  # stock 5
        self.editar(items=(("A-01", 4, None),))
        self.editar(items=(("A-01", 1, None),))
        self.assertEqual(self.lineas(), [("A-01", 1, None)])
        self.assertEqual(self.stock("A-01"), 6)


class InactivosEInexistentesTest(EdicionBase):
    def sembrar_inactivo(self, stock_despues_del_alta):
        insertar_producto(self.conn, "C-99", "Chapa", 2)
        self.orden(items=(("C-99", 2, None),))
        self.conn.execute(
            "UPDATE productos SET activo = 0, stock = ? WHERE codigo = 'C-99'",
            (stock_despues_del_alta,),
        )
        self.conn.commit()

    def test_inactivo_con_la_misma_cantidad_sigue_inactivo_con_su_stock(self):
        self.sembrar_inactivo(1)
        resultado = self.editar(items=(("C-99", 2, 500),))
        self.assertEqual(self.stocks()["C-99"], (1, 0))
        self.assertEqual(resultado.ajustes, ())

    def test_inactivo_quitado_se_reactiva_con_el_stock_reintegrado(self):
        self.sembrar_inactivo(1)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        resultado = self.editar(items=(("A-01", 1, None),))
        self.assertEqual(self.stocks()["C-99"], (3, 1))
        self.assertEqual(
            resultado.ajustes,
            (
                AjusteStock("A-01", "Tornillo", 0, 1, 4, False),
                AjusteStock("C-99", "Chapa", 2, 0, 3, True),
            ),
        )

    def test_inactivo_reducido_tambien_se_reactiva(self):
        self.sembrar_inactivo(0)
        resultado = self.editar(items=(("C-99", 1, None),))
        self.assertEqual(self.stocks()["C-99"], (1, 1))
        self.assertTrue(resultado.ajustes[0].reactivado)

    def test_inactivo_aumentado_rechaza_todo_sin_cambios(self):
        self.sembrar_inactivo(5)
        antes = self.foto()
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.editar(items=(("C-99", 3, None),))
        self.assertEqual(ctx.exception.codigos, ("C-99",))
        self.assertEqual(self.foto(), antes)

    def test_codigo_inexistente_rechaza_todo_sin_cambios(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.orden(items=(("A-01", 1, None),))
        antes = self.foto()
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.editar(items=(("A-01", 1, None), ("ZZ-99", 1, None)))
        self.assertEqual(ctx.exception.codigos, ("ZZ-99",))
        self.assertEqual(self.foto(), antes)

    def test_ausentes_y_faltantes_juntos_gana_ausentes(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 1)
        self.orden(items=(("A-01", 1, None),))  # stock 0
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.editar(items=(("A-01", 5, None), ("ZZ-99", 1, None)))
        self.assertEqual(ctx.exception.codigos, ("ZZ-99",))

    def test_varios_ausentes_se_informan_juntos(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.orden(items=(("A-01", 1, None),))
        with self.assertRaises(ProductosNoEncontrados) as ctx:
            self.editar(items=(("A-01", 1, None), ("Z-1", 1, None), ("Z-2", 1, None)))
        self.assertEqual(ctx.exception.codigos, ("Z-1", "Z-2"))


class FaltantesYAtomicidadTest(EdicionBase):
    def test_faltante_informa_disponible_y_adicional_sin_cambios(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 3)
        insertar_producto(self.conn, "B-02", "Tuerca", 10)
        self.orden(items=(("A-01", 2, None), ("B-02", 1, None)))  # A 1, B 9
        antes = self.foto()
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.editar(items=(("A-01", 5, None), ("B-02", 4, None)))
        self.assertEqual(ctx.exception.faltantes, (Faltante("A-01", 1, 3),))
        self.assertEqual(self.foto(), antes)

    def test_varios_faltantes_juntos(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 3)
        insertar_producto(self.conn, "B-02", "Tuerca", 2)
        self.orden(items=(("A-01", 2, None), ("B-02", 1, None)))  # A 1, B 1
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.editar(items=(("A-01", 9, None), ("B-02", 9, None)))
        self.assertEqual(
            ctx.exception.faltantes, (Faltante("A-01", 1, 7), Faltante("B-02", 1, 8))
        )
        with self.assertRaises(StockInsuficienteOrden) as ctx:  # el orden es el de las lineas
            self.editar(items=(("B-02", 9, None), ("A-01", 9, None)))
        self.assertEqual([f.codigo for f in ctx.exception.faltantes], ["B-02", "A-01"])

    def test_faltante_junto_a_un_reintegro_no_aplica_ninguno(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 3)
        insertar_producto(self.conn, "B-02", "Tuerca", 0)
        self.orden(items=(("A-01", 3, None),))  # A 0
        antes = self.foto()
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.editar(items=(("A-01", 1, None), ("B-02", 2, None)))
        self.assertEqual(ctx.exception.faltantes, (Faltante("B-02", 0, 2),))
        self.assertEqual(self.stock("A-01"), 0)
        self.assertEqual(self.foto(), antes)

    def test_falla_al_escribir_el_chequeo_deja_todo_como_estaba(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 5)
        self.orden(
            items=(("A-01", 2, 100),),
            procesos=(ProcesoOrden("Limpieza", False, 5),),
            servicio=ServicioOrden("Servicio 20 hs", ("Motor",), 7),
            datos=DatosOrden(cliente="Ana"),
            chequeo_final=(ChequeoFinal("entrega", "Entrega", 9),),
        )
        antes = self.foto()
        malo = ChequeoFinal("combustible", "Combustible", -1)  # viola el CHECK de precio
        with self.assertRaises(sqlite3.IntegrityError):
            self.editar(
                items=(("A-01", 4, None), ("B-02", 3, None)),
                datos=DatosOrden(cliente="Otro"),
                chequeo_final=(malo,),
            )
        self.assertEqual(self.foto(), antes)
        self.assertFalse(self.conn.in_transaction)

    def test_orden_inexistente_no_cambia_nada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        antes = self.foto()
        with self.assertRaises(OrdenNoEncontrada) as ctx:
            self.editar(numero="OT-9999")
        self.assertEqual(ctx.exception.numero, "OT-9999")
        self.assertEqual(self.foto(), antes)

    def test_editar_una_orden_recien_borrada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.orden()
        self.repo.borrar("OT-0043", True)
        with self.assertRaises(OrdenNoEncontrada):
            self.editar()
        self.assertEqual(self.stock("A-01"), 5)

    def test_transaccion_pendiente_lanza_runtimeerror_sin_confirmar(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.orden()
        self.conn.execute("INSERT INTO productos (codigo, nombre) VALUES ('P-01', 'Pend')")
        with self.assertRaises(RuntimeError):
            self.editar(items=(("A-01", 3, None),))
        self.conn.rollback()
        self.assertEqual(self.lineas(), [("A-01", 2, None)])


class ServicioYContenidoTest(EdicionBase):
    def setUp(self):
        super().setUp()
        insertar_producto(self.conn, "A-01", "Tornillo", 9)

    def test_conservar_servicio_con_precio_nuevo_conserva_nombre_y_chequeos(self):
        self.orden(servicio=ServicioOrden("Servicio 20 hs", ("Motor", "Eléctrico"), None))
        resultado = self.editar(
            servicio=ServicioOrden("", (), 4500000), conservar_servicio=True
        )
        self.assertEqual(
            resultado.orden.servicio,
            ServicioOrden("Servicio 20 hs", ("Motor", "Eléctrico"), 4500000),
        )

    def test_conservar_servicio_sin_precio_deja_el_precio_vacio(self):
        self.orden(servicio=ServicioOrden("Servicio 20 hs", ("Motor",), 100))
        resultado = self.editar(servicio=ServicioOrden("", (), None), conservar_servicio=True)
        self.assertEqual(
            resultado.orden.servicio, ServicioOrden("Servicio 20 hs", ("Motor",), None)
        )

    def test_conservar_sin_servicio_en_la_orden_rechaza_sin_cambios(self):
        self.orden()
        antes = self.foto()
        with self.assertRaises(DatosInvalidos) as ctx:
            self.editar(servicio=ServicioOrden("", (), 5), conservar_servicio=True)
        self.assertEqual(
            str(ctx.exception), "La orden no tiene un servicio general para conservar."
        )
        self.assertEqual(self.foto(), antes)

    def test_servicio_none_lo_quita_y_uno_nuevo_lo_reemplaza(self):
        self.orden(servicio=ServicioOrden("Servicio 20 hs", ("Motor",), 100))
        self.assertIsNone(self.editar().orden.servicio)
        resultado = self.editar(servicio=ServicioOrden("Servicio 50 hs", ("A", "B"), 7))
        self.assertEqual(resultado.orden.servicio, ServicioOrden("Servicio 50 hs", ("A", "B"), 7))

    def test_reemplazo_completo_deja_vacio_lo_que_no_viene(self):
        self.orden(
            procesos=(ProcesoOrden("Limpieza", False, 5),),
            datos=DatosOrden(cliente="Ana", celular="11 5555-1234"),
            chequeo_final=(ChequeoFinal("entrega", "Entrega", None),),
        )
        orden = self.editar().orden
        self.assertEqual(orden.procesos, ())
        self.assertEqual(orden.datos, DatosOrden())
        self.assertEqual(orden.chequeo_final, ())

    def test_cambia_fecha_datos_procesos_y_chequeo_y_conserva_identidad(self):
        original = self.orden()
        resultado = self.editar(
            fecha=date(2026, 11, 28),
            procesos=(ProcesoOrden("Cambio filtro", False, None),),
            datos=DatosOrden(cliente="Juan", fecha_ingreso=date(2026, 11, 26)),
            chequeo_final=(
                ChequeoFinal("entrega", "Entrega", 500000),
                ChequeoFinal("combustible", "Combustible", None),
            ),
        )
        orden = resultado.orden
        self.assertEqual((orden.id, orden.numero, orden.usuario), (original.id, "OT-0043", "admin"))
        self.assertEqual(orden.fecha, date(2026, 11, 28))
        self.assertEqual(orden.datos.cliente, "Juan")
        self.assertEqual(orden.procesos, (ProcesoOrden("Cambio filtro", False, None),))
        self.assertEqual([c.clave for c in orden.chequeo_final], ["combustible", "entrega"])
        creada = self.conn.execute("SELECT created_at FROM ordenes").fetchone()[0]
        self.assertEqual(creada, "2026-11-19T15:30:00-03:00")

    def test_editar_no_afecta_a_otra_orden(self):
        self.orden(
            "OT-1", items=(("A-01", 1, 10),),
            chequeo_final=(ChequeoFinal("entrega", "Entrega", 3),),
        )
        self.orden("OT-2", items=(("A-01", 1, 20),))
        self.editar(numero="OT-2", items=(("A-01", 3, 30),))
        self.assertEqual(self.lineas("OT-1"), [("A-01", 1, 10)])
        (otra,) = self.repo.listar("OT-1", None, None)
        self.assertEqual(otra.chequeo_final[0].precio, 3)


if __name__ == "__main__":
    unittest.main()
