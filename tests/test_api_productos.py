import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/productos"
PRODUCTOS = [("A-01", "Tornillo", 7, 1), ("B-02", "Tuerca", 3, 1), ("CAJA/10", "Caja", 0, 1)]
MSG_A01 = "No existe un producto activo con código 'A-01'."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


class BajaSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_y_el_producto_sigue_activo(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, PRODUCTOS)
        r = client.delete(f"{URL}/A-01")
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))
        self.assertEqual(consultar(ruta, "SELECT activo FROM productos WHERE codigo='A-01'"), [(1,)])

    def test_tras_logout_vuelve_a_401(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, PRODUCTOS)
        login(client)
        client.post("/api/logout")
        self.assertEqual(client.delete(f"{URL}/A-01").status_code, 401)
        self.assertEqual(consultar(ruta, "SELECT activo FROM productos WHERE codigo='A-01'"), [(1,)])


class BajaBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, PRODUCTOS)
        self.assertEqual(login(self.client).status_code, 200)

    def estado(self):
        return consultar(self.ruta, "SELECT codigo, stock, activo FROM productos ORDER BY codigo")

    def codigos_inventario(self):
        return [p["codigo"] for p in self.client.get("/api/inventario").json()]


class BajaExitoTest(BajaBase):
    def test_baja_normalizada_cuerpo_exacto(self):
        r = self.client.delete(f"{URL}/a-01")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(), {"codigo": "A-01", "nombre": "Tornillo", "stock": 7, "sin_stock": False, "categoria": None}
        )
        self.assertNotIn("A-01", self.codigos_inventario())
        self.assertIn("B-02", self.codigos_inventario())

    def test_codigo_con_barra(self):
        r = self.client.delete(f"{URL}/CAJA/10")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(), {"codigo": "CAJA/10", "nombre": "Caja", "stock": 0, "sin_stock": True, "categoria": None}
        )
        self.assertNotIn("CAJA/10", self.codigos_inventario())

    def test_no_escribe_movimientos(self):
        antes = self.client.get("/api/movimientos").json()
        self.assertEqual(self.client.delete(f"{URL}/A-01").status_code, 200)
        self.assertEqual(self.client.get("/api/movimientos").json(), antes)


class BajaEfectosCruzadosTest(BajaBase):
    def test_orden_previa_egreso_alta_y_reingreso(self):
        orden = {
            "numero": "OT-0001",
            "fecha": "2026-11-20",
            "componentes": [{"codigo": "A-01", "cantidad": 2}],
        }
        self.assertEqual(self.client.post("/api/ordenes", json=orden).status_code, 201)
        self.assertEqual(self.client.delete(f"{URL}/A-01").status_code, 200)
        (listada,) = self.client.get("/api/ordenes").json()
        self.assertEqual(
            listada["componentes"], [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": None}]
        )
        egreso = self.client.post("/api/stock/egreso", json={"codigo": "A-01", "cantidad": 1})
        self.assertEqual((egreso.status_code, egreso.json()), (404, {"detail": MSG_A01}))
        otra = dict(orden, numero="OT-0002", componentes=[{"codigo": "A-01", "cantidad": 1}])
        alta = self.client.post("/api/ordenes", json=otra)
        self.assertEqual((alta.status_code, alta.json()), (404, {"detail": MSG_A01}))
        self.assertEqual(consultar(self.ruta, "SELECT stock FROM productos WHERE codigo='A-01'"), [(5,)])
        ingreso = self.client.post("/api/stock/ingreso", json={"codigo": "A-01", "cantidad": 3})
        self.assertEqual(ingreso.status_code, 200)
        self.assertEqual((ingreso.json()["stock"], ingreso.json()["reactivado"]), (8, True))
        self.assertIn("A-01", self.codigos_inventario())

    def test_reingreso_suma_al_stock_conservado(self):
        self.client.delete(f"{URL}/A-01")
        r = self.client.post("/api/stock/ingreso", json={"codigo": "A-01", "cantidad": 3})
        self.assertEqual((r.json()["stock"], r.json()["reactivado"]), (10, True))

    def test_movimientos_previos_siguen_consultables(self):
        self.client.post("/api/stock/ingreso", json={"codigo": "A-01", "cantidad": 1})
        self.client.delete(f"{URL}/A-01")
        movs = self.client.get("/api/movimientos?codigo=A-01").json()
        self.assertEqual([(m["codigo"], m["tipo"]) for m in movs], [("A-01", "ingreso")])


class BajaErroresTest(BajaBase):
    def assertRechazo(self, url, status, detalle):
        antes = self.estado()
        r = self.client.delete(url)
        self.assertEqual((r.status_code, r.json()), (status, {"detail": detalle}))
        self.assertEqual(self.estado(), antes)

    def test_inexistente(self):
        self.assertRechazo(f"{URL}/z-99", 404, "No existe un producto activo con código 'Z-99'.")

    def test_segunda_baja(self):
        self.assertEqual(self.client.delete(f"{URL}/A-01").status_code, 200)
        self.assertRechazo(f"{URL}/A-01", 404, MSG_A01)

    def test_codigo_en_blanco_y_largo(self):
        self.assertRechazo(f"{URL}/%20%20", 422, "El campo codigo es obligatorio.")
        self.assertRechazo(f"{URL}/{'X' * 51}", 422, "El campo codigo admite hasta 50 caracteres.")


if __name__ == "__main__":
    unittest.main()
