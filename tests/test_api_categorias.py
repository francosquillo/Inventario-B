"""Categorias en la API (C-06e, spec api-http): catalogo, alta, renombrado y categoria en productos."""
import json
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/categorias"
SEMBRADAS = [
    {"clave": "aceite", "nombre": "Aceite"},
    {"clave": "filtro", "nombre": "Filtro"},
    {"clave": "motor", "nombre": "Motor"},
]
MENSAJE_JSON = "El cuerpo de la petición debe ser un objeto JSON."
TIPOS_NO_JSON = ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x")


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
        return consultar(self.ruta, "SELECT clave, nombre FROM categorias ORDER BY id")


class SinSesionTest(Base):
    def test_get_401(self):
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))

    def test_post_y_patch_401_sin_efectos(self):
        antes = self.catalogo()
        r = self.client.post(URL, json={"nombre": "Frenos"})
        self.assertEqual(r.status_code, 401)
        r = self.client.patch(f"{URL}/motor", json={"nombre": "Otro"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.catalogo(), antes)


class ListarTest(Base):
    def test_lista_exacta_ordenada_por_nombre(self):
        self.entrar()
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (200, SEMBRADAS))


class CrearTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_deriva_la_clave_y_queda_visible(self):
        r = self.client.post(URL, json={"nombre": "  Tren delantero "})
        self.assertEqual((r.status_code, r.json()), (201, {"clave": "tren-delantero", "nombre": "Tren delantero"}))
        claves = [c["clave"] for c in self.client.get(URL).json()]
        self.assertIn("tren-delantero", claves)

    def test_clave_indicada(self):
        r = self.client.post(URL, json={"nombre": "Sistema de frenos", "clave": " Frenos "})
        self.assertEqual(r.json(), {"clave": "frenos", "nombre": "Sistema de frenos"})

    def test_clave_repetida_409(self):
        r = self.client.post(URL, json={"nombre": "Motor diésel", "clave": "MOTOR"})
        self.assertEqual((r.status_code, r.json()), (409, {"detail": "Ya existe una categoría con clave 'motor'."}))
        self.assertEqual(len(self.catalogo()), 3)

    def test_nombre_repetido_409(self):
        r = self.client.post(URL, json={"nombre": "ACEITE", "clave": "lubricante"})
        self.assertEqual((r.status_code, r.json()), (409, {"detail": "Ya existe una categoría con nombre 'ACEITE'."}))
        self.assertEqual(len(self.catalogo()), 3)

    def test_422_nombre(self):
        casos = (
            ({}, "El campo nombre es obligatorio."),
            ({"nombre": ""}, "El campo nombre es obligatorio."),
            ({"nombre": "   "}, "El campo nombre es obligatorio."),
            ({"nombre": "x" * 41}, "El nombre de la categoría admite hasta 40 caracteres."),
        )
        for cuerpo, mensaje in casos:
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post(URL, json=cuerpo)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
        self.assertEqual(len(self.catalogo()), 3)

    def test_422_clave_invalida(self):
        for cuerpo in ({"nombre": "Algo", "clave": "fre nos!"}, {"nombre": "***"}):
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post(URL, json=cuerpo)
                self.assertEqual(r.status_code, 422)
                self.assertIn("La clave de la categoría admite solo", r.json()["detail"])
        self.assertEqual(len(self.catalogo()), 3)


class RenombrarTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, [("M-01", "Bujia", 1, 1)])
        self.entrar()

    def test_renombra_con_clave_en_mayusculas_y_conserva_productos(self):
        consultar(self.ruta, "SELECT 1")
        conn = conectar(self.ruta)
        conn.execute("UPDATE productos SET categoria_id = (SELECT id FROM categorias WHERE clave='motor')")
        conn.commit()
        conn.close()
        r = self.client.patch(f"{URL}/MOTOR", json={"nombre": "Motor y transmisión"})
        self.assertEqual((r.status_code, r.json()), (200, {"clave": "motor", "nombre": "Motor y transmisión"}))
        self.assertEqual(self.client.get("/api/inventario").json()[0]["categoria"], "motor")

    def test_404_inexistente(self):
        r = self.client.patch(f"{URL}/frenos", json={"nombre": "Frenos"})
        self.assertEqual((r.status_code, r.json()), (404, {"detail": "No existe una categoría con clave 'frenos'."}))

    def test_409_nombre_de_otra(self):
        r = self.client.patch(f"{URL}/filtro", json={"nombre": "aceite"})
        self.assertEqual((r.status_code, r.json()), (409, {"detail": "Ya existe una categoría con nombre 'aceite'."}))
        self.assertEqual(self.catalogo()[2], ("filtro", "Filtro"))

    def test_422_si_el_cuerpo_trae_clave(self):
        r = self.client.patch(f"{URL}/motor", json={"nombre": "Otro", "clave": "otra"})
        self.assertEqual(
            (r.status_code, r.json()), (422, {"detail": "La clave de una categoría no se puede cambiar."})
        )
        self.assertIn(("motor", "Motor"), self.catalogo())

    def test_422_nombre_vacio(self):
        r = self.client.patch(f"{URL}/motor", json={})
        self.assertEqual((r.status_code, r.json()), (422, {"detail": "El campo nombre es obligatorio."}))


class CsrfTest(Base):
    def test_cuerpos_no_json_422_y_catalogo_sin_cambios(self):
        self.entrar()
        antes = self.catalogo()
        cuerpo = json.dumps({"nombre": "Frenos"})
        for tipo in TIPOS_NO_JSON:
            for metodo, url in (("post", URL), ("patch", f"{URL}/motor")):
                with self.subTest(tipo=tipo, metodo=metodo):
                    r = getattr(self.client, metodo)(url, content=cuerpo, headers={"Content-Type": tipo})
                    self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE_JSON}))
        self.assertEqual(self.catalogo(), antes)


class ProductosConCategoriaTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1), ("C-99", "Junta", 2, 0)])
        conn = conectar(self.ruta)
        conn.execute("UPDATE productos SET categoria_id=(SELECT id FROM categorias WHERE clave='filtro') WHERE codigo='A-01'")
        conn.commit()
        conn.close()
        self.entrar()

    def test_inventario_e_inactivos_traen_categoria(self):
        self.assertEqual(self.client.get("/api/inventario").json()[0]["categoria"], "filtro")
        self.assertIsNone(self.client.get("/api/productos/inactivos").json()[0]["categoria"])

    def test_alta_con_categoria_normalizada(self):
        r = self.client.post("/api/productos", json={"codigo": "N-01", "nombre": "Aceite", "stock": 1, "categoria": "Aceite"})
        self.assertEqual((r.status_code, r.json()["categoria"]), (201, "aceite"))

    def test_alta_sin_categoria_y_reactivacion_sin_categoria(self):
        r = self.client.post("/api/productos", json={"codigo": "N-02", "nombre": "X", "stock": 1})
        self.assertIsNone(r.json()["categoria"])
        r = self.client.post("/api/productos", json={"codigo": "C-99", "nombre": "Junta", "stock": 2})
        self.assertEqual((r.status_code, r.json()["reactivado"], r.json()["categoria"]), (201, True, None))

    def test_alta_categoria_inexistente_y_no_texto(self):
        r = self.client.post("/api/productos", json={"codigo": "N-03", "nombre": "X", "stock": 1, "categoria": "encendido"})
        self.assertEqual((r.status_code, r.json()), (422, {"detail": "La categoría 'encendido' no existe."}))
        r = self.client.post("/api/productos", json={"codigo": "N-03", "nombre": "X", "stock": 1, "categoria": 3})
        self.assertEqual((r.status_code, r.json()), (422, {"detail": "El campo categoria debe ser texto."}))
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM productos"), [(2,)])

    def test_alta_409_con_categoria_valida(self):
        r = self.client.post("/api/productos", json={"codigo": "A-01", "nombre": "X", "stock": 1, "categoria": "motor"})
        self.assertEqual(r.status_code, 409)

    def test_modificacion_con_categoria_ausente_null_y_valor(self):
        url = "/api/stock/modificaciones"
        r = self.client.post(url, json={"lineas": [{"codigo": "A-01", "modo": "fijar", "stock": 5}]})
        linea = r.json()["lineas"][0]
        self.assertEqual((linea["categoria"], linea["categoria_anterior"]), ("filtro", "filtro"))
        r = self.client.post(url, json={"lineas": [{"codigo": "A-01", "modo": "fijar", "stock": 5, "categoria": "Motor"}]})
        linea = r.json()["lineas"][0]
        self.assertEqual((linea["categoria"], linea["categoria_anterior"]), ("motor", "filtro"))
        r = self.client.post(url, json={"lineas": [{"codigo": "A-01", "modo": "sumar", "cantidad": 1, "categoria": None}]})
        linea = r.json()["lineas"][0]
        self.assertEqual((linea["categoria"], linea["categoria_anterior"]), (None, "motor"))

    def test_modificacion_categoria_invalida_en_linea_2_no_cambia_nada(self):
        r = self.client.post(
            "/api/stock/modificaciones",
            json={"lineas": [
                {"codigo": "A-01", "modo": "fijar", "stock": 9, "categoria": "motor"},
                {"codigo": "C-99", "modo": "fijar", "stock": 3, "categoria": "frenos"},
            ]},
        )
        self.assertEqual((r.status_code, r.json()), (422, {"detail": "Línea 2: La categoría 'frenos' no existe."}))
        self.assertEqual(self.client.get("/api/inventario").json()[0]["stock"], 5)

    def test_modificacion_categoria_no_texto(self):
        r = self.client.post(
            "/api/stock/modificaciones",
            json={"lineas": [{"codigo": "A-01", "modo": "fijar", "stock": 5, "categoria": 3}]},
        )
        self.assertEqual(
            (r.status_code, r.json()), (422, {"detail": "Línea 1: El campo categoria debe ser texto."})
        )

    def test_egreso_y_baja_traen_categoria(self):
        r = self.client.post("/api/stock/egreso", json={"codigo": "A-01", "cantidad": 1})
        self.assertEqual(r.json()["categoria"], "filtro")
        r = self.client.delete("/api/productos/A-01")
        self.assertEqual(r.json()["categoria"], "filtro")

    def test_reporte_trae_categoria(self):
        r = self.client.post(
            "/api/ordenes",
            json={"numero": "OT-1", "fecha": "2026-11-20", "componentes": [{"codigo": "A-01", "cantidad": 1}]},
        )
        self.assertEqual(r.status_code, 201)
        r = self.client.get("/api/reportes/productos-en-ordenes", params={"desde": "2026-11-01", "hasta": "2026-11-30"})
        self.assertEqual(r.json()[0]["categoria"], "filtro")

    def test_openapi_sin_parametro_de_categoria_en_el_reporte(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        params = {p["name"] for p in paths["/api/reportes/productos-en-ordenes"]["get"]["parameters"]}
        self.assertNotIn("categoria", params)
        self.assertEqual(set(paths[URL]), {"get", "post"})
        self.assertEqual(set(paths[f"{URL}/{{clave}}"]), {"patch", "delete"})


if __name__ == "__main__":
    unittest.main()
