"""Subtotales y total de una orden (C-06h, design D2). La tabla de casos se replica en test_precios_js."""
import unittest
from datetime import date

from inventario.domain.entities import (
    AjusteStock,
    ChequeoFinal,
    DatosOrden,
    ItemOrden,
    Orden,
    ProcesoOrden,
    ResultadoEdicionOrden,
    ServicioOrden,
)

# (descripcion, servicio, adicionales, items, subtotal_servicios, subtotal_items, total)
CASOS = (
    ("todos los precios", 4500000, (1500000, 800000), (1200000, 350000), 6800000, 1550000, 8350000),
    ("precios vacios cuentan 0", None, (1500000, None), (1200000, None), 1500000, 1200000, 2700000),
    ("sin servicio ni procesos", None, (), (99999999999,), 0, 99999999999, 99999999999),
    ("sin ningun precio", None, (None,), (None, None), 0, 0, 0),
    ("precio cero", 0, (0,), (0,), 0, 0, 0),
)

# (descripcion, servicio, adicionales, items, chequeo, subtotal_servicios, subtotal_items, total)
CASOS_CHEQUEO = (
    ("chequeo con y sin precio", 4500000, (1500000,), (1200000,), (800000, None), 6800000, 1200000, 8000000),
    ("chequeo solo con precios vacios", None, (), (500,), (None, None), 0, 500, 500),
    ("chequeo con el tope", None, (), (), (99999999999,), 99999999999, 0, 99999999999),
    ("sin chequeo igual que antes", 4500000, (1500000, 800000), (1200000, 350000), (), 6800000, 1550000, 8350000),
)


def armar(servicio, adicionales, items, chequeo=()):
    return Orden(
        id=1,
        numero="OT-1",
        fecha=date(2026, 11, 27),
        usuario="admin",
        items=tuple(ItemOrden(f"A-{i}", "Pieza", 1, precio) for i, precio in enumerate(items)),
        procesos=tuple(ProcesoOrden(f"P{i}", False, precio) for i, precio in enumerate(adicionales)),
        servicio=ServicioOrden("Servicio 20 hs", (), servicio) if servicio is not None else None,
        chequeo_final=tuple(ChequeoFinal(f"c{i}", f"Item {i}", precio) for i, precio in enumerate(chequeo)),
    )


class TotalesTest(unittest.TestCase):
    def test_subtotales_y_total_segun_la_tabla_de_casos(self):
        for descripcion, servicio, adicionales, items, st_serv, st_items, total in CASOS:
            with self.subTest(descripcion):
                orden = armar(servicio, adicionales, items)
                self.assertEqual(orden.subtotal_servicios, st_serv)
                self.assertEqual(orden.subtotal_items, st_items)
                self.assertEqual(orden.total, total)

    def test_servicio_sin_precio_no_suma_pero_el_adicional_si(self):
        orden = Orden(
            1, "OT-1", date(2026, 11, 27), "admin", (),
            procesos=(ProcesoOrden("Limpieza", False, 1500000),),
            servicio=ServicioOrden("Servicio 20 hs", ("Motor",)),
        )
        self.assertEqual(orden.subtotal_servicios, 1500000)

    def test_constructores_existentes_siguen_validos_sin_precios_ni_datos(self):
        orden = Orden(1, "OT-1", date(2026, 11, 27), "admin", (ItemOrden("A-01", "Tornillo", 2),))
        self.assertIsNone(orden.items[0].precio)
        self.assertEqual(orden.datos, DatosOrden())
        self.assertEqual((orden.subtotal_servicios, orden.subtotal_items, orden.total), (0, 0, 0))

    def test_chequeo_final_segun_la_tabla_de_casos(self):
        for descripcion, servicio, adicionales, items, chequeo, st_serv, st_items, total in CASOS_CHEQUEO:
            with self.subTest(descripcion):
                orden = armar(servicio, adicionales, items, chequeo)
                self.assertEqual(orden.subtotal_servicios, st_serv)
                self.assertEqual(orden.subtotal_items, st_items)
                self.assertEqual(orden.total, total)

    def test_ajuste_de_stock_y_resultado_de_edicion_son_valores_inmutables(self):
        orden = armar(None, (), (1,))
        ajuste = AjusteStock("A-01", "Tornillo", 2, 4, 3, False)
        resultado = ResultadoEdicionOrden(orden, (ajuste,))
        self.assertEqual((resultado.orden, resultado.ajustes[0].stock), (orden, 3))
        with self.assertRaises(Exception):
            ajuste.stock = 9


if __name__ == "__main__":
    unittest.main()
