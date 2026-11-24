import unittest

from tests.helpers import cliente_de_test, login, sembrar


class InventarioSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_sin_productos(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        r = client.get("/api/inventario")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("A-01", r.text)


class InventarioConSesionTest(unittest.TestCase):
    def test_lista_activos_ordenados_con_claves_exactas(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("B-10", "Tuerca", 0, 1), ("A-01", "Tornillo", 5, 1), ("C-99", "Viejo", 3, 0)])
        login(client)
        r = client.get("/api/inventario")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            [
                {"codigo": "A-01", "nombre": "Tornillo", "stock": 5, "sin_stock": False, "categoria": None},
                {"codigo": "B-10", "nombre": "Tuerca", "stock": 0, "sin_stock": True, "categoria": None},
            ],
        )

    def test_vacio_devuelve_lista_vacia(self):
        client, _ = cliente_de_test(self.addCleanup)
        login(client)
        r = client.get("/api/inventario")
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_tras_logout_401(self):
        client, _ = cliente_de_test(self.addCleanup)
        login(client)
        self.assertEqual(client.get("/api/inventario").status_code, 200)
        client.post("/api/logout")
        self.assertEqual(client.get("/api/inventario").status_code, 401)
