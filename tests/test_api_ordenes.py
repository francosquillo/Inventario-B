import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/ordenes"
PRODUCTOS = [("A-01", "Tornillo", 5, 1), ("B-02", "Tuerca", 10, 1), ("C-99", "Viejo", 2, 0)]
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def cuerpo(numero="ot-0001", fecha="2026-11-20", componentes=None):
    if componentes is None:
        componentes = [{"codigo": "A-01", "cantidad": 1}]
    return {"numero": numero, "fecha": fecha, "componentes": componentes}


class OrdenesSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_sin_cambios(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, PRODUCTOS)
        r = client.post(URL, json=cuerpo())
        self.assertEqual(r.status_code, 401)
        self.assertEqual(consultar(ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])
        self.assertEqual(consultar(ruta, "SELECT stock FROM productos WHERE codigo='A-01'"), [(5,)])

    def test_sin_sesion_con_cuerpo_invalido_sigue_siendo_401(self):
        client, _ = cliente_de_test(self.addCleanup)
        r = client.post(URL, json={"numero": "", "componentes": "x"})
        self.assertEqual(r.status_code, 401)

    def test_tras_logout_vuelve_a_401(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, PRODUCTOS)
        login(client)
        client.post("/api/logout")
        self.assertEqual(client.post(URL, json=cuerpo()).status_code, 401)

    def test_listado_sin_sesion_401(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, PRODUCTOS)
        r = client.get(URL)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"detail": "No autenticado."})


class OrdenesBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, PRODUCTOS)
        self.assertEqual(login(self.client).status_code, 200)

    def crear(self, **kwargs):
        return self.client.post(URL, json=cuerpo(**kwargs))

    def stocks(self):
        return dict(consultar(self.ruta, "SELECT codigo, stock FROM productos"))

    def assertSinCambios(self):
        self.assertEqual(self.stocks(), {"A-01": 5, "B-02": 10, "C-99": 2})
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM orden_items"), [(0,)])


class AltaTest(OrdenesBase):
    COMPONENTES_SPEC = [
        {"codigo": "b-02", "cantidad": 4},
        {"codigo": "A-01", "cantidad": 2},
        {"codigo": "B-02", "cantidad": 1},
    ]

    def test_orden_creada_cuerpo_exacto(self):
        r = self.crear(componentes=self.COMPONENTES_SPEC)
        self.assertEqual(r.status_code, 201)
        c = r.json()
        self.assertIsInstance(c["id"], int)
        self.assertEqual(
            {k: c[k] for k in ("numero", "fecha", "usuario")},
            {"numero": "OT-0001", "fecha": "2026-11-20", "usuario": "admin"},
        )
        self.assertEqual(
            c["componentes"],
            [
                {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2},
                {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5},
            ],
        )
        self.assertEqual(set(c), {"id", "numero", "fecha", "usuario", "componentes"})

    def test_inventario_descontado_y_sin_movimientos(self):
        self.crear(componentes=self.COMPONENTES_SPEC)
        inv = {p["codigo"]: p["stock"] for p in self.client.get("/api/inventario").json()}
        self.assertEqual((inv["A-01"], inv["B-02"]), (3, 5))
        self.assertEqual(self.client.get("/api/movimientos").json(), [])

    def test_segunda_orden_con_stock_a_cero(self):
        r = self.crear(numero="ot-2", componentes=[{"codigo": "a-01", "cantidad": 5}])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["numero"], "OT-2")
        inv = {p["codigo"]: p for p in self.client.get("/api/inventario").json()}
        self.assertEqual(inv["A-01"]["stock"], 0)
        self.assertTrue(inv["A-01"]["sin_stock"])


class RechazosTest(OrdenesBase):
    def test_409_stock_con_faltantes_exactos(self):
        sembrar(self.ruta, [("D-04", "Arandela", 1, 1), ("E-05", "Junta", 0, 1)])
        r = self.crear(
            componentes=[{"codigo": "D-04", "cantidad": 2}, {"codigo": "E-05", "cantidad": 1}]
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(
            r.json(),
            {
                "detail": "Stock insuficiente para la orden: 'D-04' (disponible 1, solicitado 2); "
                "'E-05' (disponible 0, solicitado 1).",
                "faltantes": [
                    {"codigo": "D-04", "disponible": 1, "solicitado": 2},
                    {"codigo": "E-05", "disponible": 0, "solicitado": 1},
                ],
            },
        )
        self.assertEqual(self.stocks()["D-04"], 1)
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])

    def test_409_un_faltante_sobre_producto_con_stock(self):
        r = self.crear(componentes=[{"codigo": "A-01", "cantidad": 6}])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(
            r.json()["faltantes"], [{"codigo": "A-01", "disponible": 5, "solicitado": 6}]
        )
        self.assertSinCambios()

    def test_409_duplicado_sin_faltantes(self):
        self.assertEqual(self.crear().status_code, 201)
        r = self.crear(numero="OT-0001")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json(), {"detail": "Ya existe una orden con número 'OT-0001'."})
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(1,)])
        self.assertEqual(self.stocks()["A-01"], 4)

    def test_404_inexistente_e_inactivo(self):
        r = self.crear(componentes=[{"codigo": "X-00", "cantidad": 1}])
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "No existe un producto activo con código 'X-00'."})
        r = self.crear(
            componentes=[{"codigo": "X-00", "cantidad": 1}, {"codigo": "C-99", "cantidad": 1}]
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(
            r.json()["detail"], "No existen productos activos con código: 'X-00', 'C-99'."
        )
        self.assertSinCambios()

    def test_422_casos(self):
        casos = (
            (dict(componentes=[]), "La orden requiere al menos un componente."),
            (
                dict(componentes=[{"codigo": "A-01", "cantidad": "5"}]),
                f"Componente 1: {MSG_CANTIDAD}",
            ),
            (
                dict(
                    componentes=[
                        {"codigo": "A-01", "cantidad": 1},
                        {"codigo": "B-02", "cantidad": 0},
                    ]
                ),
                f"Componente 2: {MSG_CANTIDAD}",
            ),
            (dict(fecha="20/11/2026"), "La fecha debe tener formato AAAA-MM-DD."),
            (dict(fecha="2026-02-30"), "La fecha (2026-02-30) no es una fecha válida."),
            (dict(numero="X" * 31), "El campo numero admite hasta 30 caracteres."),
        )
        for kwargs, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                r = self.crear(**kwargs)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": mensaje})
        self.assertSinCambios()

    def test_422_fecha_con_espacios_o_salto_de_linea(self):
        for fecha in (" 2026-11-20 ", "2026-11-20\n", "\t2026-11-20", "2026-11-20 "):
            with self.subTest(fecha=repr(fecha)):
                r = self.crear(fecha=fecha)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(
                    r.json(), {"detail": "La fecha debe tener formato AAAA-MM-DD."}
                )
        self.assertSinCambios()
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])

    def test_numero_y_codigo_con_espacios_se_recortan(self):
        r = self.crear(numero="  ot-0007 ", componentes=[{"codigo": " a-01 ", "cantidad": 1}])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["numero"], "OT-0007")

    def test_422_null_en_numero_y_fecha(self):
        for campo in ("numero", "fecha"):
            with self.subTest(campo=campo):
                r = self.crear(**{campo: None})
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": f"El campo {campo} es obligatorio."})
        self.assertSinCambios()

    def test_422_cuerpo_no_json_y_no_objeto(self):
        r = self.client.post(
            URL, content="no es json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El cuerpo de la petición no es JSON válido."})
        r = self.client.post(URL, json=[1, 2])
        self.assertEqual(r.status_code, 422)
        self.assertIsInstance(r.json()["detail"], str)

    def test_422_falta_fecha(self):
        r = self.client.post(
            URL, json={"numero": "OT-1", "componentes": [{"codigo": "A-01", "cantidad": 1}]}
        )
        self.assertEqual(
            (r.status_code, r.json()), (422, {"detail": "El campo fecha es obligatorio."})
        )


class ListadoTest(OrdenesBase):
    def comp(self, *pares):
        return [{"codigo": c, "cantidad": n} for c, n in pares]

    def numeros(self, query=""):
        r = self.client.get(URL + query)
        self.assertEqual(r.status_code, 200, r.text)
        return [o["numero"] for o in r.json()]

    def test_sin_ordenes_devuelve_lista_vacia(self):
        r = self.client.get(URL)
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_listado_cuerpo_exacto_con_el_mismo_id_del_alta(self):
        creada = self.crear(componentes=self.comp(("b-02", 5), ("A-01", 2)))
        self.assertEqual(creada.status_code, 201)
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            [
                {
                    "id": creada.json()["id"],
                    "numero": "OT-0001",
                    "fecha": "2026-11-20",
                    "usuario": "admin",
                    "componentes": [
                        {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2},
                        {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5},
                    ],
                }
            ],
        )
        self.assertEqual(r.json()[0], creada.json())

    def test_orden_por_fecha_descendente_y_luego_id(self):
        self.crear(numero="OT-1", fecha="2026-11-18")
        self.crear(numero="OT-2", fecha="2026-11-20")
        self.crear(numero="OT-3", fecha="2026-11-20")
        self.assertEqual(self.numeros(), ["OT-3", "OT-2", "OT-1"])

    def sembrar_tres(self):
        self.crear(numero="OT-0001", fecha="2026-11-17")
        self.crear(numero="OT-0002", fecha="2026-11-20")
        self.crear(numero="OT-0003", fecha="2026-11-19")

    def test_filtros_combinados_y_rango_abierto(self):
        self.sembrar_tres()
        self.assertEqual(
            self.numeros("?numero=ot-0002&desde=2026-11-20&hasta=2026-11-20"), ["OT-0002"]
        )
        self.assertEqual(self.numeros("?desde=2026-11-18"), ["OT-0002", "OT-0003"])
        self.assertEqual(self.numeros("?hasta=2026-11-19"), ["OT-0003", "OT-0001"])

    def test_parametros_vacios_equivalen_a_sin_filtro(self):
        self.sembrar_tres()
        self.assertEqual(
            self.numeros("?numero=&desde=&hasta="), ["OT-0002", "OT-0003", "OT-0001"]
        )

    def test_numero_inexistente_es_404_con_mensaje(self):
        self.sembrar_tres()
        r = self.client.get(URL + "?numero=ot-9")
        self.assertEqual(
            (r.status_code, r.json()), (404, {"detail": "No existe una orden con número 'OT-9'."})
        )

    def test_numero_existente_fuera_del_rango_es_200_vacio(self):
        self.sembrar_tres()
        r = self.client.get(URL + "?numero=OT-0001&desde=2026-11-18")
        self.assertEqual((r.status_code, r.json()), (200, []))
        self.assertEqual(self.numeros("?numero=OT-0001&desde=2026-11-17"), ["OT-0001"])

    def test_422_tiene_prioridad_sobre_404(self):
        r = self.client.get(URL + "?numero=OT-9&desde=19/11/2026")
        self.assertEqual(
            (r.status_code, r.json()),
            (422, {"detail": "La fecha 'desde' debe tener formato AAAA-MM-DD."}),
        )

    def test_producto_dado_de_baja_sigue_en_la_orden_pero_no_en_inventario(self):
        self.crear(componentes=self.comp(("A-01", 1), ("B-02", 1)))
        conn = conectar(self.ruta)
        try:
            conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'B-02'")
            conn.commit()
        finally:
            conn.close()
        (orden,) = self.client.get(URL).json()
        self.assertEqual(
            orden["componentes"],
            [
                {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 1},
                {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 1},
            ],
        )
        codigos = [p["codigo"] for p in self.client.get("/api/inventario").json()]
        self.assertNotIn("B-02", codigos)

    def test_422_con_detalle_exacto(self):
        casos = (
            ("?desde=19/11/2026", "La fecha 'desde' debe tener formato AAAA-MM-DD."),
            ("?hasta=2026-02-30", "La fecha 'hasta' (2026-02-30) no es una fecha válida."),
            (
                "?desde=2026-11-20&hasta=2026-11-19",
                "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).",
            ),
            ("?numero=" + "X" * 31, "El campo numero admite hasta 30 caracteres."),
        )
        for query, detalle in casos:
            with self.subTest(query=query):
                r = self.client.get(URL + query)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": detalle}))

    def test_tras_logout_el_listado_da_401(self):
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.client.post("/api/logout")
        self.assertEqual(self.client.get(URL).status_code, 401)


class OpenApiOrdenesTest(unittest.TestCase):
    def setUp(self):
        client, _ = cliente_de_test(self.addCleanup)
        self.spec = client.get("/openapi.json").json()

    def esquema(self, ruta, metodo, codigo):
        resp = self.spec["paths"][ruta][metodo]["responses"][codigo]
        return resp["content"]["application/json"]["schema"]["$ref"]

    def test_lista_los_ocho_endpoints(self):
        self.assertEqual(len(self.spec["paths"]), 8)
        self.assertIn("/api/ordenes", self.spec["paths"])

    def test_respuestas_documentadas_de_ordenes(self):
        self.assertTrue(self.esquema(URL, "post", "422").endswith("/ErrorOut"))
        self.assertTrue(self.esquema(URL, "post", "409").endswith("/StockInsuficienteOut"))
        self.assertTrue(self.esquema(URL, "post", "404").endswith("/ErrorOut"))
        self.assertTrue(self.esquema(URL, "post", "201").endswith("/OrdenOut"))

    def test_get_documenta_lista_404_y_422(self):
        resp = self.spec["paths"][URL]["get"]["responses"]
        self.assertEqual(resp["200"]["content"]["application/json"]["schema"]["items"]["$ref"][-8:], "OrdenOut")
        self.assertTrue(self.esquema(URL, "get", "404").endswith("/ErrorOut"))
        self.assertTrue(self.esquema(URL, "get", "422").endswith("/ErrorOut"))
        self.assertEqual(set(self.spec["paths"][URL]), {"get", "post"})

    def test_422_de_otros_endpoints_siguen_con_error_out(self):
        for ruta, metodo in (
            ("/api/login", "post"),
            ("/api/stock/ingreso", "post"),
            ("/api/stock/egreso", "post"),
            ("/api/movimientos", "get"),
        ):
            with self.subTest(ruta=ruta):
                self.assertTrue(self.esquema(ruta, metodo, "422").endswith("/ErrorOut"))
