"""Vigencia de 12 h de la cookie de sesion (C-06, D2)."""
import base64
import json
import os
import secrets
import tempfile
import time
import unittest

import itsdangerous
from fastapi.testclient import TestClient

from inventario.api.app import SESSION_COOKIE, crear_app
from tests.helpers import PASSWORD_ADMIN_TEST, login


class FirmadorFijo(itsdangerous.TimestampSigner):
    """Firma como Starlette pero con un instante controlado."""

    def __init__(self, *args, ahora, **kwargs):
        super().__init__(*args, **kwargs)
        self._ahora = ahora

    def get_timestamp(self):
        return int(self._ahora)


class VigenciaTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.secret = secrets.token_urlsafe(32)
        app = crear_app(
            ruta_db=os.path.join(tmp.name, "t.db"),
            secret_key=self.secret,
            password_admin=PASSWORD_ADMIN_TEST,
            https_only=False,
        )
        self.client = TestClient(app, follow_redirects=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def cookie_firmada(self, horas_atras):
        uid = login(self.client).json()["id"]
        self.client.cookies.clear()
        datos = base64.b64encode(
            json.dumps({"usuario_id": uid, "username": "admin"}).encode()
        )
        firmador = FirmadorFijo(self.secret, ahora=time.time() - horas_atras * 3600)
        self.client.cookies.set(SESSION_COOKIE, firmador.sign(datos).decode())

    def test_set_cookie_del_login_con_max_age_12h(self):
        r = login(self.client)
        cookie = r.headers["set-cookie"].lower()
        self.assertIn("max-age=43200", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)

    def test_sesion_de_13_horas_expirada(self):
        self.cookie_firmada(13)
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<form", r.text)

    def test_sesion_de_11_horas_vigente(self):
        self.cookie_firmada(11)
        r = self.client.get("/api/me")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "admin")


if __name__ == "__main__":
    unittest.main()
