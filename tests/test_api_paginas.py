"""Paginas HTML servidas por FastAPI con redireccion segun sesion (C-06, D1)."""
import sqlite3
import unittest

from tests.helpers import cliente_de_test, login, sembrar


def cliente_sin_redirecciones(testcase):
    client, ruta = cliente_de_test(testcase.addCleanup)
    client.follow_redirects = False
    return client, ruta


class PaginasTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_sin_redirecciones(self)

    def test_login_sin_sesion_devuelve_html_con_formulario(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("text/html"))
        self.assertIn("<form", r.text)

    def test_inventario_y_ordenes_sin_sesion_redirigen_al_login(self):
        for ruta in ("/inventario", "/ordenes", "/reportes"):
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers["location"], "/")

    def test_inventario_y_ordenes_con_sesion_devuelven_html(self):
        login(self.client)
        for ruta in ("/inventario", "/ordenes", "/reportes"):
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.headers["content-type"].startswith("text/html"))

    def test_login_con_sesion_redirige_a_inventario(self):
        login(self.client)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/inventario")

    def test_cookie_de_usuario_inexistente_muestra_login_y_redirige(self):
        login(self.client)
        conn = sqlite3.connect(self.ruta)
        conn.execute("DELETE FROM usuarios")
        conn.commit()
        conn.close()
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<form", r.text)
        r = self.client.get("/inventario")
        self.assertEqual(r.status_code, 303)
        self.assertEqual(r.headers["location"], "/")

    def test_el_html_no_contiene_datos(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        r = self.client.get("/inventario")
        self.assertNotIn("A-01", r.text)
        self.assertNotIn("Tornillo", r.text)

    def test_reportes_html_sin_datos(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        r = self.client.get("/reportes")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("text/html"))
        self.assertNotIn("A-01", r.text)
        self.assertNotIn("Tornillo", r.text)

    def test_ordenes_html_y_api_json(self):
        login(self.client)
        self.assertTrue(self.client.get("/ordenes").headers["content-type"].startswith("text/html"))
        r = self.client.get("/api/ordenes")
        self.assertEqual(r.json(), [])

    def test_rutas_inexistentes_404_json(self):
        for ruta in ("/no-existe", "/api/no-existe"):
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 404)
                self.assertEqual(r.json(), {"detail": "Not Found"})

    def test_docs_sigue_disponible(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)

    def test_paginas_y_static_fuera_de_openapi(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for ruta in ("/", "/inventario", "/ordenes", "/reportes", "/static"):
            self.assertNotIn(ruta, paths)
        self.assertFalse([p for p in paths if p.startswith("/static")])


class CabecerasPaginasTest(unittest.TestCase):
    ESPERADAS = {
        "x-frame-options": "DENY",
        "x-content-type-options": "nosniff",
        "referrer-policy": "same-origin",
        "cache-control": "no-store",
    }

    def setUp(self):
        self.client, _ = cliente_sin_redirecciones(self)

    def assertCabeceras(self, r):
        for nombre, valor in self.ESPERADAS.items():
            self.assertEqual(r.headers.get(nombre), valor, nombre)

    def test_login_incluye_cabeceras(self):
        self.assertCabeceras(self.client.get("/"))

    def test_inventario_y_ordenes_con_sesion_incluyen_cabeceras(self):
        login(self.client)
        for ruta in ("/inventario", "/ordenes", "/reportes"):
            with self.subTest(ruta=ruta):
                self.assertCabeceras(self.client.get(ruta))

    def test_api_no_lleva_x_frame_options(self):
        login(self.client)
        for ruta in ("/api/me", "/api/inventario"):
            with self.subTest(ruta=ruta):
                self.assertNotIn("x-frame-options", self.client.get(ruta).headers)


if __name__ == "__main__":
    unittest.main()
