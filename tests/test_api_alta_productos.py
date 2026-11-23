"""POST /api/productos y GET /api/productos/inactivos (specs api-http, alta-productos)."""
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/productos"
MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


class AltaSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_y_no_se_crea_nada(self):
        client, ruta = cliente_de_test(self.addCleanup)
        r = client.post(URL, json={"codigo": "N-01", "nombre": "Arandela", "stock": 1})
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))
        self.assertEqual(consultar(ruta, "SELECT COUNT(*) FROM productos"), [(0,)])


class AltaBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, [("A-01", "Tornillo M4", 5, 1), ("C-99", "Junta", 2, 0)])
        self.assertEqual(login(self.client).status_code, 200)

    def productos(self):
        return consultar(self.ruta, "SELECT COUNT(*) FROM productos")[0][0]

    def movimientos(self):
        return consultar(self.ruta, "SELECT COUNT(*) FROM movimientos")[0][0]

    def alta(self, **cuerpo):
        return self.client.post(URL, json=cuerpo)

    def assertRechazo(self, respuesta, status, mensaje):
        self.assertEqual((respuesta.status_code, respuesta.json()), (status, {"detail": mensaje}))
        self.assertEqual(self.productos(), 2)
        self.assertEqual(self.movimientos(), 0)


class AltaExitosaTest(AltaBase):
    def test_alta_con_stock_cero_devuelve_201_y_aparece_en_inventario(self):
        r = self.alta(codigo="n-01", nombre="Arandela 6mm", stock=0)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json(),
            {
                "codigo": "N-01",
                "nombre": "Arandela 6mm",
                "stock": 0,
                "sin_stock": True,
                "creado": True,
                "reactivado": False,
            },
        )
        codigos = [p["codigo"] for p in self.client.get("/api/inventario").json()]
        self.assertIn("N-01", codigos)
        self.assertEqual(self.movimientos(), 0)

    def test_alta_con_stock_registra_ingreso(self):
        r = self.alta(codigo="  rd-6204 ", nombre="  Rodamiento  ", stock=4)
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.json()["codigo"], r.json()["nombre"], r.json()["stock"]), ("RD-6204", "Rodamiento", 4))
        self.assertEqual(r.json()["sin_stock"], False)
        mov = self.client.get("/api/movimientos").json()
        self.assertEqual((mov[0]["tipo"], mov[0]["cantidad"], mov[0]["usuario"]), ("ingreso", 4, "admin"))

    def test_stock_maximo(self):
        self.assertEqual(self.alta(codigo="N-03", nombre="Junta", stock=10_000).status_code, 201)

    def test_reactivacion_responde_201_con_reactivado(self):
        r = self.alta(codigo="C-99", nombre="Junta tórica", stock=6)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json(),
            {
                "codigo": "C-99",
                "nombre": "Junta tórica",
                "stock": 6,
                "sin_stock": False,
                "creado": False,
                "reactivado": True,
            },
        )
        mov = self.client.get("/api/movimientos").json()
        self.assertEqual(
            (mov[0]["tipo"], mov[0]["cantidad"], mov[0]["stock_anterior"], mov[0]["stock_nuevo"]),
            ("ajuste", 4, 2, 6),
        )
        self.assertEqual(self.productos(), 2)


class AltaErroresTest(AltaBase):
    def test_codigo_activo_409(self):
        r = self.alta(codigo="a-01", nombre="Otro", stock=1)
        self.assertRechazo(r, 409, "Ya existe un producto con código 'A-01'.")
        self.assertEqual(consultar(self.ruta, "SELECT nombre, stock FROM productos WHERE codigo='A-01'"), [("Tornillo M4", 5)])

    def test_nombre_faltante_o_en_blanco_422(self):
        for cuerpo in (
            {"codigo": "N-02", "stock": 3},
            {"codigo": "N-02", "nombre": "   ", "stock": 3},
            {"codigo": "N-02", "nombre": None, "stock": 3},
        ):
            with self.subTest(cuerpo=cuerpo):
                self.assertRechazo(self.client.post(URL, json=cuerpo), 422, "El campo nombre es obligatorio.")

    def test_stock_invalido_422(self):
        for stock in (-1, 10_001, "5", 2.5, True):
            with self.subTest(stock=stock):
                self.assertRechazo(self.alta(codigo="N-02", nombre="X", stock=stock), 422, MSG_STOCK)

    def test_stock_faltante_422(self):
        r = self.client.post(URL, json={"codigo": "N-02", "nombre": "X"})
        self.assertRechazo(r, 422, "El campo stock es obligatorio.")

    def test_codigo_faltante_o_largo_422(self):
        self.assertRechazo(
            self.client.post(URL, json={"nombre": "X", "stock": 1}), 422, "El campo codigo es obligatorio."
        )
        self.assertRechazo(
            self.alta(codigo="x" * 51, nombre="X", stock=1),
            422,
            "El campo codigo admite hasta 50 caracteres.",
        )

    def test_nombre_largo_422(self):
        self.assertRechazo(
            self.alta(codigo="N-02", nombre="x" * 121, stock=1),
            422,
            "El campo nombre admite hasta 120 caracteres.",
        )


class InactivosTest(unittest.TestCase):
    def test_sin_sesion_401(self):
        client, _ = cliente_de_test(self.addCleanup)
        self.assertEqual(client.get(f"{URL}/inactivos").status_code, 401)

    def test_lista_ordenada_por_codigo_sin_activos(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1), ("C-99", "Junta", 2, 0), ("B-02", "Tuerca", 0, 0)])
        login(client)
        r = client.get(f"{URL}/inactivos")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            [
                {"codigo": "B-02", "nombre": "Tuerca", "stock": 0, "sin_stock": True},
                {"codigo": "C-99", "nombre": "Junta", "stock": 2, "sin_stock": False},
            ],
        )

    def test_ninguno_devuelve_lista_vacia(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        login(client)
        self.assertEqual(client.get(f"{URL}/inactivos").json(), [])

    def test_delete_de_un_codigo_inactivos_sigue_llegando_a_la_baja(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("INACTIVOS", "Rara", 1, 1)])
        login(client)
        r = client.delete(f"{URL}/INACTIVOS")
        self.assertEqual((r.status_code, r.json()["codigo"]), (200, "INACTIVOS"))
        self.assertEqual(client.delete(f"{URL}/INACTIVOS").status_code, 404)

    def test_get_inactivos_no_se_confunde_con_un_codigo(self):
        client, ruta = cliente_de_test(self.addCleanup)
        login(client)
        self.assertEqual(client.get(f"{URL}/inactivos").json(), [])


if __name__ == "__main__":
    unittest.main()
