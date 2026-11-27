"""Procesos en la API (C-06f, spec api-http): catalogo, procesos en ordenes y borrado de categorias."""
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/procesos"
SEMBRADOS = [
    {"clave": "cambio-filtro", "nombre": "Cambio filtro"},
    {"clave": "cambio-motor", "nombre": "Cambio motor"},
    {"clave": "limpieza", "nombre": "Limpieza"},
]
MENSAJE_JSON = "El cuerpo de la petición debe ser un objeto JSON."
TIPOS_NO_JSON = ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x")
PRODUCTOS = [("A-01", "Tornillo", 20, 1), ("B-02", "Tuerca", 10, 1)]


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
        return consultar(self.ruta, "SELECT clave, nombre FROM procesos ORDER BY id")


class SinSesionTest(Base):
    def test_get_401(self):
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))

    def test_post_patch_delete_401_sin_efectos(self):
        antes = self.catalogo()
        self.assertEqual(self.client.post(URL, json={"nombre": "Pintura"}).status_code, 401)
        self.assertEqual(self.client.patch(f"{URL}/limpieza", json={"nombre": "X"}).status_code, 401)
        self.assertEqual(self.client.delete(f"{URL}/limpieza").status_code, 401)
        self.assertEqual(self.catalogo(), antes)


class ListarTest(Base):
    def test_lista_exacta_ordenada_por_nombre(self):
        self.entrar()
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (200, SEMBRADOS))


class CrearTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_201_con_clave_derivada_visible_en_get(self):
        r = self.client.post(URL, json={"nombre": "  Pintura del casco "})
        self.assertEqual(
            (r.status_code, r.json()), (201, {"clave": "pintura-del-casco", "nombre": "Pintura del casco"})
        )
        self.assertIn(r.json(), self.client.get(URL).json())

    def test_clave_indicada(self):
        r = self.client.post(URL, json={"nombre": "Pintura", "clave": "pint"})
        self.assertEqual((r.status_code, r.json()["clave"]), (201, "pint"))

    def test_409_clave_y_nombre_con_detail_exacto(self):
        antes = self.catalogo()
        r = self.client.post(URL, json={"nombre": "Otro", "clave": "limpieza"})
        self.assertEqual((r.status_code, r.json()), (409, {"detail": "Ya existe un proceso con clave 'limpieza'."}))
        r = self.client.post(URL, json={"nombre": "LIMPIEZA", "clave": "otra"})
        self.assertEqual((r.status_code, r.json()), (409, {"detail": "Ya existe un proceso con nombre 'LIMPIEZA'."}))
        self.assertEqual(self.catalogo(), antes)

    def test_422_nombre_faltante_largo_y_clave_invalida(self):
        casos = [
            ({}, "El campo nombre es obligatorio."),
            ({"nombre": "x" * 61}, "El nombre del proceso admite hasta 60 caracteres."),
            (
                {"nombre": "Ok", "clave": "Clave Mala"},
                "La clave del proceso admite solo minúsculas sin tilde, números y guiones "
                "(hasta 30 caracteres).",
            ),
        ]
        antes = self.catalogo()
        for cuerpo, mensaje in casos:
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post(URL, json=cuerpo)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
        self.assertEqual(self.catalogo(), antes)


class RenombrarTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_200_con_clave_en_mayusculas_en_la_ruta(self):
        r = self.client.patch(f"{URL}/LIMPIEZA", json={"nombre": "Limpieza total"})
        self.assertEqual((r.status_code, r.json()), (200, {"clave": "limpieza", "nombre": "Limpieza total"}))

    def test_404_409_y_422(self):
        r = self.client.patch(f"{URL}/nada", json={"nombre": "X"})
        self.assertEqual((r.status_code, r.json()), (404, {"detail": "No existe un proceso con clave 'nada'."}))
        r = self.client.patch(f"{URL}/limpieza", json={"nombre": "cambio motor"})
        self.assertEqual(r.status_code, 409)
        r = self.client.patch(f"{URL}/limpieza", json={"nombre": "X", "clave": "otra"})
        self.assertEqual(
            (r.status_code, r.json()),
            (422, {"detail": "La clave de un proceso no se puede cambiar."}),
        )
        self.assertEqual(self.catalogo()[2], ("limpieza", "Limpieza"))

    def test_openapi_clave_en_parameters_y_cuerpo_solo_con_nombre(self):
        doc = self.client.get("/openapi.json").json()
        op = doc["paths"][URL + "/{clave}"]["patch"]
        self.assertEqual([p["name"] for p in op["parameters"]], ["clave"])
        ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        esquema = doc["components"]["schemas"][ref.rsplit("/", 1)[1]]
        self.assertEqual(list(esquema["properties"]), ["nombre"])


class BorrarTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, PRODUCTOS)
        self.entrar()

    def test_200_con_lo_borrado_y_404(self):
        r = self.client.delete(f"{URL}/limpieza")
        self.assertEqual((r.status_code, r.json()), (200, {"clave": "limpieza", "nombre": "Limpieza"}))
        self.assertNotIn("limpieza", [p["clave"] for p in self.client.get(URL).json()])
        r = self.client.delete(f"{URL}/limpieza")
        self.assertEqual((r.status_code, r.json()), (404, {"detail": "No existe un proceso con clave 'limpieza'."}))

    def test_borrar_uno_usado_por_una_orden_conserva_el_nombre_en_la_orden(self):
        self.client.post(
            "/api/ordenes",
            json={
                "numero": "OT-1", "fecha": "2026-11-20",
                "componentes": [{"codigo": "A-01", "cantidad": 1}],
                "procesos": ["limpieza"],
            },
        )
        self.assertEqual(self.client.delete(f"{URL}/limpieza").status_code, 200)
        orden = self.client.get("/api/ordenes").json()[0]
        self.assertEqual(orden["procesos"], [{"nombre": "Limpieza", "personalizado": False, "precio": None}])


class CsrfTest(Base):
    def test_post_y_patch_con_cuerpo_no_json_422_sin_cambios(self):
        self.entrar()
        antes = self.catalogo()
        for tipo in TIPOS_NO_JSON:
            with self.subTest(tipo=tipo):
                r = self.client.post(URL, content='{"nombre": "Pintura"}', headers={"Content-Type": tipo})
                self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE_JSON}))
                r = self.client.patch(
                    f"{URL}/limpieza", content='{"nombre": "X"}', headers={"Content-Type": tipo}
                )
                self.assertEqual((r.status_code, r.json()), (422, {"detail": MENSAJE_JSON}))
        self.assertEqual(self.catalogo(), antes)

    def test_alta_de_orden_con_procesos_y_text_plain_422_sin_orden(self):
        sembrar(self.ruta, PRODUCTOS)
        self.entrar()
        r = self.client.post(
            "/api/ordenes",
            content='{"numero":"OT-1","fecha":"2026-11-20","componentes":'
            '[{"codigo":"A-01","cantidad":1}],"procesos":["limpieza"]}',
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])


class OrdenesConProcesosTest(Base):
    def setUp(self):
        super().setUp()
        sembrar(self.ruta, PRODUCTOS)
        self.entrar()

    def crear(self, **extra):
        cuerpo = {
            "numero": "OT-1", "fecha": "2026-11-20",
            "componentes": [{"codigo": "A-01", "cantidad": 2}],
        }
        cuerpo.update(extra)
        return self.client.post("/api/ordenes", json=cuerpo)

    def sin_cambios(self):
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])
        self.assertEqual(consultar(self.ruta, "SELECT stock FROM productos WHERE codigo='A-01'"), [(20,)])

    def test_alta_con_procesos_y_personalizados_201_exacto(self):
        r = self.crear(procesos=["limpieza", "cambio-motor"], procesos_personalizados=[" Pulido "])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()["procesos"],
            [
                {"nombre": "Limpieza", "personalizado": False, "precio": None},
                {"nombre": "Cambio motor", "personalizado": False, "precio": None},
                {"nombre": "Pulido", "personalizado": True, "precio": None},
            ],
        )

    def test_sin_procesos_devuelve_lista_vacia(self):
        self.assertEqual(self.crear().json()["procesos"], [])
        self.assertEqual(self.crear(numero="OT-2", procesos=[], procesos_personalizados=[]).json()["procesos"], [])

    def test_422_proceso_inexistente_personalizado_vacio_y_tipo_invalido(self):
        casos = [
            ({"procesos": ["pintura"]}, "El proceso 'pintura' no existe."),
            ({"procesos_personalizados": ["  "]}, "Proceso personalizado 1: El nombre es obligatorio."),
            ({"procesos": "limpieza"}, "El campo procesos debe ser una lista de textos."),
            ({"procesos": [3]}, "El campo procesos debe ser una lista de textos."),
            (
                {"procesos_personalizados": "x"},
                "El campo procesos_personalizados debe ser una lista de textos.",
            ),
        ]
        for extra, mensaje in casos:
            with self.subTest(extra=extra):
                r = self.crear(**extra)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
                self.sin_cambios()

    def test_listado_conserva_el_snapshot_tras_renombrar_el_proceso(self):
        self.crear(procesos=["limpieza"])
        self.client.patch(f"{URL}/limpieza", json={"nombre": "Limpieza total"})
        orden = self.client.get("/api/ordenes").json()[0]
        self.assertEqual(orden["procesos"], [{"nombre": "Limpieza", "personalizado": False, "precio": None}])

    def test_borrar_la_orden_devuelve_sus_procesos_y_no_deja_filas(self):
        self.crear(procesos=["limpieza"], procesos_personalizados=["Pulido"])
        r = self.client.delete("/api/ordenes/OT-1", params={"reintegrar": "true"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["orden"]["procesos"],
            [
                {"nombre": "Limpieza", "personalizado": False, "precio": None},
                {"nombre": "Pulido", "personalizado": True, "precio": None},
            ],
        )
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM orden_procesos"), [(0,)])


class BorrarCategoriaTest(Base):
    def setUp(self):
        super().setUp()
        self.entrar()

    def test_200_y_fuera_del_get(self):
        r = self.client.delete("/api/categorias/Motor")
        self.assertEqual((r.status_code, r.json()), (200, {"clave": "motor", "nombre": "Motor"}))
        self.assertNotIn("motor", [c["clave"] for c in self.client.get("/api/categorias").json()])

    def test_404(self):
        r = self.client.delete("/api/categorias/nada")
        self.assertEqual((r.status_code, r.json()), (404, {"detail": "No existe una categoría con clave 'nada'."}))

    def test_409_en_uso_con_detail_exacto_y_sin_cambios(self):
        conn = conectar(self.ruta)
        conn.execute(
            "INSERT INTO productos (codigo, nombre, stock, categoria_id) "
            "VALUES ('F-1', 'Filtro', 1, (SELECT id FROM categorias WHERE clave = 'filtro'))"
        )
        conn.commit()
        conn.close()
        r = self.client.delete("/api/categorias/filtro")
        self.assertEqual(
            (r.status_code, r.json()),
            (409, {"detail": "La categoría 'filtro' está asignada a 1 producto(s)."}),
        )
        self.assertIn("filtro", [c["clave"] for c in self.client.get("/api/categorias").json()])

    def test_401_sin_sesion(self):
        self.client.post("/api/logout")
        r = self.client.delete("/api/categorias/motor")
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
