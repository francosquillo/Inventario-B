"""Servicios generales en la API (C-06g, spec api-http): catalogo y servicio en las ordenes."""
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/servicios-generales"
CHEQUEOS_20 = ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]
VEINTE = {"clave": "servicio-20-hs", "nombre": "Servicio 20 hs", "chequeos": CHEQUEOS_20}
PRODUCTOS = [("A-01", "Tornillo", 20, 1), ("B-02", "Tuerca", 10, 1)]
COMPONENTES = [{"codigo": "A-01", "cantidad": 1}]


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


class Base(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)

    def entrar(self):
        self.assertEqual(login(self.client).status_code, 200)

    def catalogo(self):
        return consultar(
            self.ruta,
            "SELECT s.clave, s.nombre, c.posicion, c.nombre FROM servicios_generales s "
            "LEFT JOIN servicio_chequeos c ON c.servicio_id = s.id ORDER BY s.id, c.posicion",
        )

    def crear_orden(self, numero="OT-1", **extra):
        cuerpo = {"numero": numero, "fecha": "2026-11-20", "componentes": COMPONENTES, **extra}
        return self.client.post("/api/ordenes", json=cuerpo)


class SinSesionTest(Base):
    def test_get_401(self):
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))

    def test_post_patch_delete_401_sin_efectos(self):
        antes = self.catalogo()
        cuerpo = {"nombre": "Servicio 50 hs", "chequeos": ["A"]}
        self.assertEqual(self.client.post(URL, json=cuerpo).status_code, 401)
        self.assertEqual(self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "X"}).status_code, 401)
        self.assertEqual(self.client.delete(f"{URL}/servicio-20-hs").status_code, 401)
        self.assertEqual(self.catalogo(), antes)


class ListarTest(Base):
    def test_lista_exacta_del_servicio_sembrado(self):
        self.entrar()
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (200, [VEINTE]))

    def test_ordenada_por_nombre(self):
        self.entrar()
        self.client.post(URL, json={"nombre": "Servicio 100 hs", "chequeos": ["A"]})
        self.assertEqual(
            [s["clave"] for s in self.client.get(URL).json()], ["servicio-100-hs", "servicio-20-hs"]
        )


class CrearTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_201_con_clave_derivada_y_chequeos_recortados_visible_en_get(self):
        r = self.client.post(
            URL, json={"nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite", " Chequeo de motor "]}
        )
        esperado = {
            "clave": "servicio-100-hs",
            "nombre": "Servicio 100 hs",
            "chequeos": ["Cambio de aceite", "Chequeo de motor"],
        }
        self.assertEqual((r.status_code, r.json()), (201, esperado))
        self.assertIn(esperado, self.client.get(URL).json())

    def test_clave_indicada(self):
        r = self.client.post(URL, json={"nombre": "Otro", "chequeos": ["A"], "clave": "otro-s"})
        self.assertEqual((r.status_code, r.json()["clave"]), (201, "otro-s"))

    def test_409_nombre_y_clave_con_detail_exacto(self):
        antes = self.catalogo()
        r = self.client.post(URL, json={"nombre": "servicio 20 hs", "chequeos": ["A"]})
        self.assertEqual(
            (r.status_code, r.json()),
            (409, {"detail": "Ya existe un servicio general con nombre 'servicio 20 hs'."}),
        )
        r = self.client.post(URL, json={"nombre": "Otro", "chequeos": ["A"], "clave": "servicio-20-hs"})
        self.assertEqual(
            (r.status_code, r.json()),
            (409, {"detail": "Ya existe un servicio general con clave 'servicio-20-hs'."}),
        )
        self.assertEqual(self.catalogo(), antes)

    def test_422_nombre_clave_y_chequeos_invalidos(self):
        casos = [
            ({"chequeos": ["A"]}, "El campo nombre es obligatorio."),
            ({"nombre": "x" * 61, "chequeos": ["A"]}, "El nombre del servicio general admite hasta 60 caracteres."),
            (
                {"nombre": "Ok", "chequeos": ["A"], "clave": "Clave Mala"},
                "La clave del servicio general admite solo minúsculas sin tilde, números y guiones "
                "(hasta 30 caracteres).",
            ),
            ({"nombre": "Ok", "chequeos": []}, "El servicio general requiere al menos un chequeo."),
            ({"nombre": "Ok"}, "El servicio general requiere al menos un chequeo."),
            ({"nombre": "Ok", "chequeos": "A"}, "El campo chequeos debe ser una lista de textos."),
            ({"nombre": "Ok", "chequeos": ["A", " "]}, "Chequeo 2: El nombre es obligatorio."),
            ({"nombre": "Ok", "chequeos": ["A", "a"]}, "Chequeo 2: 'a' está repetido."),
            (
                {"nombre": "Ok", "chequeos": [str(i) for i in range(31)]},
                "El servicio general admite hasta 30 chequeos.",
            ),
        ]
        antes = self.catalogo()
        for cuerpo, mensaje in casos:
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post(URL, json=cuerpo)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
        self.assertEqual(self.catalogo(), antes)


class ModificarTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_200_solo_chequeos_con_la_clave_en_mayusculas_en_la_ruta(self):
        r = self.client.patch(
            f"{URL}/SERVICIO-20-HS", json={"chequeos": ["Chequeo de motor", "Chequeo de batería"]}
        )
        self.assertEqual(
            (r.status_code, r.json()),
            (200, {"clave": "servicio-20-hs", "nombre": "Servicio 20 hs",
                   "chequeos": ["Chequeo de motor", "Chequeo de batería"]}),
        )

    def test_200_solo_nombre_conserva_los_chequeos(self):
        r = self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "Service 20 horas"})
        self.assertEqual((r.status_code, r.json()), (200, {**VEINTE, "nombre": "Service 20 horas"}))

    def test_422_cuerpo_vacio_y_con_clave(self):
        antes = self.catalogo()
        r = self.client.patch(f"{URL}/servicio-20-hs", json={})
        self.assertEqual(
            (r.status_code, r.json()), (422, {"detail": "Indicá el nombre o los chequeos a modificar."})
        )
        r = self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "Service 20", "clave": "service-20"})
        self.assertEqual(
            (r.status_code, r.json()),
            (422, {"detail": "La clave de un servicio general no se puede cambiar."}),
        )
        self.assertEqual(self.catalogo(), antes)

    def test_422_chequeos_invalidos_no_cambian_el_nombre(self):
        antes = self.catalogo()
        r = self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "Otro", "chequeos": ["A", "a"]})
        self.assertEqual((r.status_code, r.json()), (422, {"detail": "Chequeo 2: 'a' está repetido."}))
        self.assertEqual(self.catalogo(), antes)

    def test_404_y_409(self):
        r = self.client.patch(f"{URL}/servicio-500-hs", json={"nombre": "Servicio 500 hs"})
        self.assertEqual(
            (r.status_code, r.json()),
            (404, {"detail": "No existe un servicio general con clave 'servicio-500-hs'."}),
        )
        self.client.post(URL, json={"nombre": "Servicio 100 hs", "chequeos": ["A"]})
        r = self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "servicio 100 HS"})
        self.assertEqual(
            (r.status_code, r.json()),
            (409, {"detail": "Ya existe un servicio general con nombre 'servicio 100 HS'."}),
        )


class BorrarTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, PRODUCTOS)
        self.entrar()

    def test_200_con_lo_borrado_y_404(self):
        r = self.client.delete(f"{URL}/servicio-20-hs")
        self.assertEqual((r.status_code, r.json()), (200, VEINTE))
        self.assertEqual(self.client.get(URL).json(), [])
        r = self.client.delete(f"{URL}/servicio-20-hs")
        self.assertEqual(
            (r.status_code, r.json()),
            (404, {"detail": "No existe un servicio general con clave 'servicio-20-hs'."}),
        )

    def test_borrar_uno_usado_por_una_orden_conserva_el_snapshot(self):
        self.assertEqual(self.crear_orden(servicio="servicio-20-hs").status_code, 201)
        self.assertEqual(self.client.delete(f"{URL}/servicio-20-hs").status_code, 200)
        orden = self.client.get("/api/ordenes").json()[0]
        self.assertEqual(orden["servicio"], {"nombre": "Servicio 20 hs", "chequeos": CHEQUEOS_20})


class OrdenesConServicioTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, PRODUCTOS)
        self.entrar()

    def test_alta_con_servicio_201_con_servicio_exacto(self):
        r = self.crear_orden(servicio=" Servicio-20-HS ")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["servicio"], {"nombre": "Servicio 20 hs", "chequeos": CHEQUEOS_20})
        self.assertEqual(
            set(r.json()), {"id", "numero", "fecha", "usuario", "componentes", "procesos", "servicio"}
        )

    def test_alta_sin_servicio_null_o_blanco(self):
        self.assertIsNone(self.crear_orden("OT-1").json()["servicio"])
        self.assertIsNone(self.crear_orden("OT-2", servicio=None).json()["servicio"])
        self.assertIsNone(self.crear_orden("OT-3", servicio="  ").json()["servicio"])

    def test_422_inexistente_y_tipo_invalido_sin_tocar_stock(self):
        casos = [
            ("servicio-500-hs", "El servicio general 'servicio-500-hs' no existe."),
            (["servicio-20-hs"], "El campo servicio debe ser texto."),
            (3, "El campo servicio debe ser texto."),
        ]
        for valor, mensaje in casos:
            with self.subTest(valor=valor):
                r = self.crear_orden(servicio=valor)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
        self.assertEqual(self.client.get("/api/ordenes").json(), [])
        self.assertEqual(
            {p["codigo"]: p["stock"] for p in self.client.get("/api/inventario").json()},
            {"A-01": 20, "B-02": 10},
        )

    def test_listado_muestra_el_snapshot_tras_renombrar_y_reemplazar_chequeos(self):
        self.crear_orden(servicio="servicio-20-hs")
        self.client.patch(f"{URL}/servicio-20-hs", json={"nombre": "Service 20 horas", "chequeos": ["Uno"]})
        orden = self.client.get("/api/ordenes").json()[0]
        self.assertEqual(orden["servicio"], {"nombre": "Servicio 20 hs", "chequeos": CHEQUEOS_20})
        self.assertEqual(self.client.get(URL).json()[0]["nombre"], "Service 20 horas")

    def test_borrar_la_orden_devuelve_el_servicio_y_limpia_sus_filas(self):
        self.crear_orden(servicio="servicio-20-hs")
        r = self.client.delete("/api/ordenes/OT-1", params={"reintegrar": "true"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["orden"]["servicio"], {"nombre": "Servicio 20 hs", "chequeos": CHEQUEOS_20}
        )
        self.assertEqual(consultar(self.ruta, "SELECT * FROM orden_servicio"), [])
        self.assertEqual(consultar(self.ruta, "SELECT * FROM orden_servicio_chequeos"), [])
        self.assertEqual(self.client.get(URL).json(), [VEINTE])


if __name__ == "__main__":
    unittest.main()
