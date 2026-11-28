"""Defensa CSRF fijada por tests de caracterizacion (C-06, D3).

Sin token CSRF: el cuerpo exige JSON (los formularios cross-site no pueden enviarlo
sin preflight), SameSite=Lax y no hay CORS.
"""
import json
import sqlite3
import unittest

from tests.helpers import cliente_de_test, login, movimientos, sembrar

CREDENCIALES = json.dumps({"username": "admin", "password": "Clave-Test-1"})
TIPOS_NO_JSON = (
    "text/plain",
    "application/x-www-form-urlencoded",
    "multipart/form-data; boundary=x",
)
MENSAJE = "El cuerpo de la petición debe ser un objeto JSON."


class CsrfTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)

    def test_login_con_cuerpo_no_json_422_sin_cookie(self):
        for tipo in TIPOS_NO_JSON:
            with self.subTest(tipo=tipo):
                r = self.client.post(
                    "/api/login", content=CREDENCIALES, headers={"Content-Type": tipo}
                )
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": MENSAJE})
                self.assertNotIn("set-cookie", r.headers)

    def test_mutaciones_con_text_plain_422_sin_efectos(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        cuerpos = {
            "/api/stock/ingreso": {"codigo": "A-01", "cantidad": 3},
            "/api/stock/egreso": {"codigo": "A-01", "cantidad": 1},
            "/api/ordenes": {
                "numero": "OT-1",
                "fecha": "2026-11-20",
                "componentes": [{"codigo": "A-01", "cantidad": 1}],
            },
        }
        for url, cuerpo in cuerpos.items():
            with self.subTest(url=url):
                r = self.client.post(
                    url, content=json.dumps(cuerpo), headers={"Content-Type": "text/plain"}
                )
                self.assertEqual(r.status_code, 422)
        self.assertEqual(self.client.get("/api/inventario").json()[0]["stock"], 5)
        self.assertEqual(self.client.get("/api/ordenes").json(), [])
        conn = sqlite3.connect(self.ruta)
        try:
            self.assertEqual(movimientos(conn), [])
        finally:
            conn.close()

    def test_edicion_de_orden_con_text_plain_422_sin_efectos(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        alta = {"numero": "OT-1", "fecha": "2026-11-20", "componentes": [{"codigo": "A-01", "cantidad": 1}]}
        self.assertEqual(self.client.post("/api/ordenes", json=alta).status_code, 201)
        edicion = {"fecha": "2026-11-21", "componentes": [{"codigo": "A-01", "cantidad": 3}]}
        for tipo in TIPOS_NO_JSON:
            with self.subTest(tipo=tipo):
                r = self.client.put(
                    "/api/ordenes/OT-1", content=json.dumps(edicion), headers={"Content-Type": tipo}
                )
                self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE}))
        orden = self.client.get("/api/ordenes").json()[0]
        self.assertEqual((orden["fecha"], orden["componentes"][0]["cantidad"]), ("2026-11-20", 1))
        self.assertEqual(self.client.get("/api/inventario").json()[0]["stock"], 4)

    def test_servicios_generales_con_cualquier_tipo_no_json_422_sin_efectos(self):
        login(self.client)
        cuerpo = json.dumps({"nombre": "Servicio 50 hs", "chequeos": ["A"]})
        for tipo in TIPOS_NO_JSON:
            with self.subTest(tipo=tipo):
                r = self.client.post(
                    "/api/servicios-generales", content=cuerpo, headers={"Content-Type": tipo}
                )
                self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE}))
                r = self.client.patch(
                    "/api/servicios-generales/servicio-20-hs",
                    content=json.dumps({"nombre": "X"}),
                    headers={"Content-Type": tipo},
                )
                self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE}))
        self.assertEqual(
            self.client.get("/api/servicios-generales").json(),
            [{
                "clave": "servicio-20-hs",
                "nombre": "Servicio 20 hs",
                "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"],
            }],
        )

    def test_alta_y_modificacion_con_cualquier_tipo_no_json_422_sin_efectos(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        cuerpos = {
            "/api/productos": {"codigo": "N-01", "nombre": "Arandela", "stock": 3},
            "/api/stock/modificaciones": {
                "lineas": [{"codigo": "A-01", "modo": "sumar", "cantidad": 1}]
            },
        }
        tipos = ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data")
        for url, cuerpo in cuerpos.items():
            for tipo in tipos:
                with self.subTest(url=url, tipo=tipo):
                    r = self.client.post(
                        url, content=json.dumps(cuerpo), headers={"Content-Type": tipo}
                    )
                    self.assertEqual(r.status_code, 422)
        inventario = self.client.get("/api/inventario").json()
        self.assertEqual([(p["codigo"], p["stock"]) for p in inventario], [("A-01", 5)])
        conn = sqlite3.connect(self.ruta)
        try:
            self.assertEqual(movimientos(conn), [])
        finally:
            conn.close()

    def test_sin_cors_para_origen_ajeno(self):
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1)])
        login(self.client)
        r = self.client.options(
            "/api/ordenes/OT-0001",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        self.assertFalse(200 <= r.status_code < 300)
        self.assertNotIn("access-control-allow-origin", r.headers)
        r = self.client.get("/api/inventario", headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse([h for h in r.headers if h.startswith("access-control-allow")])


if __name__ == "__main__":
    unittest.main()
