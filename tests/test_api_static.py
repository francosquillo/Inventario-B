"""Archivos estaticos bajo /static, publicos y sin escapar del directorio (C-06, D1)."""
import unittest

from tests.helpers import cliente_de_test


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.client, _ = cliente_de_test(self.addCleanup)

    def test_css_publico_sin_sesion(self):
        for nombre in ("tokens.css", "ui.css"):
            with self.subTest(nombre=nombre):
                r = self.client.get(f"/static/css/{nombre}")
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.headers["content-type"].startswith("text/css"))

    def test_js_con_content_type_de_javascript(self):
        r = self.client.get("/static/js/api.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("javascript", r.headers["content-type"])

    def test_recorrido_de_directorios_no_expone_archivos(self):
        for ruta in (
            "/static/..%2Finventario.db",
            "/static/..%2F..%2Frequirements.txt",
            "/static/../requirements.txt",
            "/static/%2e%2e/requirements.txt",
        ):
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 404)
                self.assertNotIn("fastapi", r.text.lower())

    def test_directorios_y_archivos_inexistentes_404(self):
        for ruta in ("/static/", "/static/js/", "/static/no-existe.css"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)


if __name__ == "__main__":
    unittest.main()
