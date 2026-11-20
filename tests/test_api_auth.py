import unittest

from tests.helpers import PASSWORD_ADMIN_TEST, cliente_de_test, login

MENSAJE = "Usuario o contraseña incorrectos."


class ApiAuthBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client, cls.ruta = cliente_de_test(cls.addClassCleanup)

    def setUp(self):
        self.client.cookies.clear()


class LoginTest(ApiAuthBase):
    def test_login_valido_devuelve_usuario_sin_hash(self):
        r = login(self.client)
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(set(cuerpo), {"id", "username"})
        self.assertIsInstance(cuerpo["id"], int)
        self.assertEqual(cuerpo["username"], "admin")

    def test_cookie_de_sesion_con_vigencia_de_12h(self):
        cabecera = login(self.client).headers["set-cookie"].lower()
        self.assertIn("inventario_session=", cabecera)
        self.assertIn("httponly", cabecera)
        self.assertIn("samesite=lax", cabecera)
        self.assertNotIn("secure", cabecera)
        self.assertIn("max-age=43200", cabecera)  # C-06 D2 reemplaza la decision 7 de C-01
        self.assertNotIn("expires", cabecera)

    def test_rechazos_con_el_mismo_401_generico(self):
        casos = [("admin", "incorrecta"), ("noexiste", PASSWORD_ADMIN_TEST), ("   ", "x")]
        for username, password in casos:
            with self.subTest(username=username):
                r = login(self.client, username, password)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(r.json()["detail"], MENSAJE)
                self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_422_por_cuerpo_invalido(self):
        invalidos = [
            (None, "El cuerpo de la petición es obligatorio."),
            ({"username": "admin"}, "El campo password es obligatorio."),
            ({"username": "admin", "password": ""}, "El campo password es obligatorio."),
            ({"username": "", "password": "x"}, "El campo username es obligatorio."),
            ({"username": 5, "password": "x"}, "El campo username debe ser texto."),
            ({"username": "admin", "password": None}, "El campo password es obligatorio."),
            ({"username": None, "password": "x"}, "El campo username es obligatorio."),
        ]
        for cuerpo, mensaje in invalidos:
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post("/api/login", json=cuerpo)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": mensaje})

    def test_422_por_longitud_excesiva(self):
        casos = [
            ({"username": "u" * 65, "password": "x"}, "El campo username admite hasta 64 caracteres."),
            ({"username": "admin", "password": "p" * 129}, "El campo password admite hasta 128 caracteres."),
        ]
        for cuerpo, mensaje in casos:
            with self.subTest(usuario=len(cuerpo["username"]), clave=len(cuerpo["password"])):
                r = self.client.post("/api/login", json=cuerpo)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": mensaje})

    def test_422_por_json_mal_formado(self):
        r = self.client.post(
            "/api/login",
            content='{"username": "admin",',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El cuerpo de la petición no es JSON válido."})

    def test_422_por_cuerpo_que_no_es_objeto(self):
        r = self.client.post("/api/login", json=[1, 2])
        self.assertEqual(r.status_code, 422)
        self.assertIsInstance(r.json()["detail"], str)

    def test_longitudes_limite_se_procesan(self):
        for cuerpo in (
            {"username": "u" * 64, "password": "x"},
            {"username": "admin", "password": "p" * 128},
        ):
            with self.subTest(usuario=len(cuerpo["username"]), clave=len(cuerpo["password"])):
                r = self.client.post("/api/login", json=cuerpo)
                self.assertEqual(r.status_code, 401)


class LoginHttpsOnlyTest(unittest.TestCase):
    def test_cookie_secure_con_https_only(self):
        client, _ = cliente_de_test(self.addCleanup, https_only=True)
        self.assertIn("secure", login(client).headers["set-cookie"].lower())


class MeTest(ApiAuthBase):
    def test_sin_sesion_401(self):
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_con_sesion_devuelve_usuario(self):
        login(self.client)
        r = self.client.get("/api/me")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "admin")

    def test_cookie_con_firma_invalida_401(self):
        self.client.cookies.set("inventario_session", "eyJ1c3VhcmlvX2lkIjogMX0=.abc.def")
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_login_fallido_posterior_cierra_la_sesion(self):
        login(self.client)
        self.assertEqual(self.client.get("/api/me").status_code, 200)
        self.assertEqual(login(self.client, password="mala").status_code, 401)
        self.assertEqual(self.client.get("/api/me").status_code, 401)


class LogoutTest(ApiAuthBase):
    def test_logout_cierra_sesion(self):
        login(self.client)
        r = self.client.post("/api/logout")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.content, b"")
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_logout_sin_sesion_204(self):
        self.assertEqual(self.client.post("/api/logout").status_code, 204)
