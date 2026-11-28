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
                {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": None},
                {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5, "precio": None},
            ],
        )
        self.assertEqual(set(c), CAMPOS_ORDEN)
        self.assertEqual(
            {k: c[k] for k in ("fecha_ingreso", "fecha_egreso", "cliente", "celular", "casco",
                               "motor", "trailer", "subtotal_servicios", "subtotal_items", "total")},
            {"fecha_ingreso": None, "fecha_egreso": None, "cliente": None, "celular": None,
             "casco": None, "motor": None, "trailer": None, "subtotal_servicios": 0,
             "subtotal_items": 0, "total": 0},
        )
        self.assertEqual(c["procesos"], [])
        self.assertIsNone(c["servicio"])

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
                    "fecha_ingreso": None,
                    "fecha_egreso": None,
                    "cliente": None,
                    "celular": None,
                    "casco": None,
                    "motor": None,
                    "trailer": None,
                    "usuario": "admin",
                    "componentes": [
                        {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": None},
                        {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 5, "precio": None},
                    ],
                    "procesos": [],
                    "servicio": None,
                    "chequeo_final": [],
                    "subtotal_servicios": 0,
                    "subtotal_items": 0,
                    "total": 0,
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
                {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 1, "precio": None},
                {"codigo": "B-02", "nombre": "Tuerca", "cantidad": 1, "precio": None},
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

    def test_lista_las_trece_rutas(self):
        self.assertEqual(len(self.spec["paths"]), 21)
        for ruta in ("/api/ordenes", "/api/ordenes/{numero}", "/api/productos/{codigo}"):
            with self.subTest(ruta=ruta):
                self.assertIn(ruta, self.spec["paths"])

    def test_delete_de_orden_documenta_parametros_y_respuestas(self):
        op = self.spec["paths"]["/api/ordenes/{numero}"]["delete"]
        params = {p["name"]: p for p in op["parameters"]}
        self.assertEqual(params["numero"]["in"], "path")
        self.assertIs(params["numero"]["required"], True)
        self.assertEqual(params["reintegrar"]["in"], "query")
        self.assertIs(params["reintegrar"]["required"], True)
        self.assertEqual(params["reintegrar"]["schema"]["enum"], ["true", "false"])
        self.assertTrue(self.esquema("/api/ordenes/{numero}", "delete", "200").endswith("/BorradoOrdenOut"))
        self.assertTrue(self.esquema("/api/ordenes/{numero}", "delete", "404").endswith("/ErrorOut"))
        self.assertTrue(self.esquema("/api/ordenes/{numero}", "delete", "422").endswith("/ErrorOut"))
        self.assertEqual(set(self.spec["paths"]["/api/ordenes/{numero}"]), {"put", "delete"})

    def test_delete_de_producto_documenta_respuestas(self):
        ruta = "/api/productos/{codigo}"
        self.assertEqual(set(self.spec["paths"][ruta]), {"delete"})
        self.assertTrue(self.esquema(ruta, "delete", "200").endswith("/ProductoOut"))
        self.assertTrue(self.esquema(ruta, "delete", "404").endswith("/ErrorOut"))
        self.assertTrue(self.esquema(ruta, "delete", "422").endswith("/ErrorOut"))
        params = self.spec["paths"][ruta]["delete"]["parameters"]
        self.assertEqual([(p["name"], p["in"]) for p in params], [("codigo", "path")])

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


class BorrarSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_y_la_orden_sigue(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        login(client)
        self.assertEqual(client.post(URL, json=cuerpo()).status_code, 201)
        client.post("/api/logout")
        r = client.delete(URL + "/OT-0001?reintegrar=true")
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))
        self.assertEqual(consultar(ruta, "SELECT COUNT(*) FROM ordenes"), [(1,)])
        self.assertEqual(consultar(ruta, "SELECT stock FROM productos"), [(4,)])

    def test_sin_sesion_gana_sobre_la_validacion(self):
        client, _ = cliente_de_test(self.addCleanup)
        self.assertEqual(client.delete(URL + "/OT-0001").status_code, 401)

    def test_sin_sesion_gana_sobre_reintegrar_repetido(self):
        client, _ = cliente_de_test(self.addCleanup)
        r = client.delete(URL + "/OT-0001?reintegrar=true&reintegrar=false")
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))


class BorrarBase(unittest.TestCase):
    """OT-0001 (id 1): A-01 x2 y C-99 x4; C-99 queda dado de baja con stock 1."""

    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, [("A-01", "Tornillo", 5, 1), ("C-99", "Arandela", 5, 1)])
        self.assertEqual(login(self.client).status_code, 200)
        r = self.client.post(
            URL,
            json=dict(
                cuerpo(
                    componentes=[
                        {"codigo": "A-01", "cantidad": 2, "precio": 1000},
                        {"codigo": "C-99", "cantidad": 4},
                    ]
                ),
                cliente="Juan Pérez",
            ),
        )
        self.assertEqual(r.status_code, 201)
        conn = conectar(self.ruta)
        try:
            conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'C-99'")
            conn.commit()
        finally:
            conn.close()
        self.movimientos_antes = self.client.get("/api/movimientos").json()

    def borrar(self, numero="OT-0001", query="?reintegrar=true"):
        return self.client.delete(f"{URL}/{numero}{query}")

    def estado(self):
        return (
            consultar(self.ruta, "SELECT codigo, stock, activo FROM productos ORDER BY codigo"),
            consultar(self.ruta, "SELECT numero FROM ordenes"),
            consultar(self.ruta, "SELECT COUNT(*) FROM orden_items"),
        )

    def assertRechazo(self, r, status, detalle):
        antes = self.antes
        self.assertEqual((r.status_code, r.json()), (status, {"detail": detalle}))
        self.assertEqual(self.estado(), antes)
        self.assertEqual([o["numero"] for o in self.client.get(URL).json()], ["OT-0001"])


class BorrarExitoTest(BorrarBase):
    def test_con_reintegro_cuerpo_exacto_y_efectos(self):
        r = self.borrar("ot-0001", "?reintegrar=true")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "orden": {
                    "id": 1,
                    "numero": "OT-0001",
                    "fecha": "2026-11-20",
                    "fecha_ingreso": None,
                    "fecha_egreso": None,
                    "cliente": "Juan Pérez",
                    "celular": None,
                    "casco": None,
                    "motor": None,
                    "trailer": None,
                    "usuario": "admin",
                    "componentes": [
                        {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": 1000},
                        {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "precio": None},
                    ],
                    "procesos": [],
                    "servicio": None,
                    "chequeo_final": [],
                    "subtotal_servicios": 0,
                    "subtotal_items": 1000,
                    "total": 1000,
                },
                "reintegrado": True,
                "reintegros": [
                    {"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "stock": 5, "reactivado": False},
                    {"codigo": "C-99", "nombre": "Arandela", "cantidad": 4, "stock": 5, "reactivado": True},
                ],
            },
        )
        self.assertEqual(self.client.get(URL).json(), [])
        inventario = {p["codigo"]: p["stock"] for p in self.client.get("/api/inventario").json()}
        self.assertEqual(inventario, {"A-01": 5, "C-99": 5})
        self.assertEqual(self.client.get("/api/movimientos").json(), self.movimientos_antes)

    def test_sin_reintegro(self):
        r = self.borrar("OT-0001", "?reintegrar=false")
        self.assertEqual(r.status_code, 200)
        cuerpo_ = r.json()
        self.assertIs(cuerpo_["reintegrado"], False)
        self.assertEqual(cuerpo_["reintegros"], [])
        self.assertEqual(cuerpo_["orden"]["numero"], "OT-0001")
        self.assertEqual(self.client.get(URL).json(), [])
        inventario = {p["codigo"]: p["stock"] for p in self.client.get("/api/inventario").json()}
        self.assertEqual(inventario, {"A-01": 3})  # C-99 sigue inactivo
        self.assertEqual(
            consultar(self.ruta, "SELECT stock, activo FROM productos WHERE codigo='C-99'"),
            [(1, 0)],
        )
        self.assertEqual(self.client.get("/api/movimientos").json(), self.movimientos_antes)

    def test_numero_normalizado(self):
        r = self.borrar("%20ot-0001%20", "?reintegrar=false")
        self.assertEqual((r.status_code, r.json()["orden"]["numero"]), (200, "OT-0001"))

    def test_numero_con_barras(self):
        self.client.post(URL, json=cuerpo(numero="OT/2026/01"))
        r = self.borrar("OT/2026/01", "?reintegrar=true")
        self.assertEqual((r.status_code, r.json()["orden"]["numero"]), (200, "OT/2026/01"))
        self.assertEqual([o["numero"] for o in self.client.get(URL).json()], ["OT-0001"])

    def test_numero_con_signos_codificados(self):
        self.client.post(URL, json=cuerpo(numero="OT?1"))
        self.client.post(URL, json=cuerpo(numero="OT#1"))
        for crudo, esperado in (("OT%3F1", "OT?1"), ("OT%231", "OT#1")):
            with self.subTest(numero=esperado):
                r = self.borrar(crudo, "?reintegrar=false")
                self.assertEqual((r.status_code, r.json()["orden"]["numero"]), (200, esperado))
        r = self.borrar("XY%3F9", "?reintegrar=false")
        self.assertEqual(
            (r.status_code, r.json()), (404, {"detail": "No existe una orden con número 'XY?9'."})
        )


class BorrarErroresTest(BorrarBase):
    def setUp(self):
        super().setUp()
        self.antes = self.estado()

    def test_reintegrar_ausente_o_vacio(self):
        for query in ("", "?reintegrar="):
            with self.subTest(query=query):
                self.assertRechazo(
                    self.borrar(query=query), 422, "El campo reintegrar es obligatorio."
                )

    def test_reintegrar_invalido(self):
        for valor in ("si", "1", "TRUE", "False"):
            with self.subTest(valor=valor):
                self.assertRechazo(
                    self.borrar(query=f"?reintegrar={valor}"),
                    422,
                    "El campo reintegrar debe ser true o false.",
                )

    def test_reintegrar_repetido(self):
        for query in (
            "?reintegrar=true&reintegrar=false",
            "?reintegrar=false&reintegrar=true",
            "?reintegrar=true&reintegrar=true",
            "?reintegrar=si&reintegrar=no",
        ):
            with self.subTest(query=query):
                self.assertRechazo(
                    self.borrar(query=query),
                    422,
                    "El campo reintegrar debe enviarse una sola vez.",
                )

    def test_reintegrar_repetido_gana_sobre_404_y_numero_invalido(self):
        mensaje = "El campo reintegrar debe enviarse una sola vez."
        query = "?reintegrar=true&reintegrar=false"
        self.assertRechazo(self.borrar("ot-0999", query), 422, mensaje)
        self.assertRechazo(self.borrar("%20%20", query), 422, mensaje)

    def test_numero_en_blanco_y_largo(self):
        self.assertRechazo(
            self.borrar("%20%20"), 422, "El campo numero es obligatorio."
        )
        self.assertRechazo(
            self.borrar("N" * 31), 422, "El campo numero admite hasta 30 caracteres."
        )

    def test_inexistente_y_prioridad_422_sobre_404(self):
        r = self.borrar("ot-0999", "?reintegrar=false")
        self.assertRechazo(r, 404, "No existe una orden con número 'OT-0999'.")
        self.assertRechazo(
            self.borrar("ot-0999", ""), 422, "El campo reintegrar es obligatorio."
        )

    def test_segundo_borrado_da_404_y_no_reintegra_otra_vez(self):
        self.assertEqual(self.borrar().status_code, 200)
        despues = self.estado()
        r = self.borrar()
        self.assertEqual(
            (r.status_code, r.json()),
            (404, {"detail": "No existe una orden con número 'OT-0001'."}),
        )
        self.assertEqual(self.estado(), despues)


CAMPOS_ORDEN = {
    "id", "numero", "fecha", "fecha_ingreso", "fecha_egreso", "cliente", "celular", "casco",
    "motor", "trailer", "usuario", "componentes", "procesos", "servicio",
    "chequeo_final", "subtotal_servicios", "subtotal_items", "total",
}
MSG_PRECIO = "El precio debe ser un entero de centavos entre 0 y 99.999.999.999."


class DatosYPreciosApiTest(OrdenesBase):
    """C-06h: datos del cliente, fechas de ingreso/egreso y precios en el alta y la consulta."""

    def post(self, **extra):
        cuerpo_base = {
            "numero": "OT-0043", "fecha": "2026-11-27",
            "componentes": [{"codigo": "A-01", "cantidad": 2, "precio": 1200000}],
        }
        cuerpo_base.update(extra)
        return self.client.post(URL, json=cuerpo_base)

    def completo(self):
        return self.post(
            fecha_ingreso="2026-11-26", fecha_egreso="2026-11-29", cliente="Juan Pérez",
            celular="11 5555-1234", casco="Bermuda 190", motor="Mercury 90 HP", trailer="",
            servicio="servicio-20-hs", precio_servicio=4500000,
            procesos=[{"clave": "limpieza", "precio": 1500000}],
            procesos_personalizados=[{"nombre": "Pulido"}],
        )

    def test_alta_con_datos_y_precios_cuerpo_exacto(self):
        r = self.completo()
        self.assertEqual(r.status_code, 201, r.text)
        c = r.json()
        self.assertEqual(set(c), CAMPOS_ORDEN)
        self.assertEqual(
            {k: c[k] for k in (
                "fecha", "fecha_ingreso", "fecha_egreso", "cliente", "celular", "casco", "motor",
                "trailer", "subtotal_servicios", "subtotal_items", "total",
            )},
            {
                "fecha": "2026-11-27", "fecha_ingreso": "2026-11-26", "fecha_egreso": "2026-11-29",
                "cliente": "Juan Pérez", "celular": "11 5555-1234", "casco": "Bermuda 190",
                "motor": "Mercury 90 HP", "trailer": None,
                "subtotal_servicios": 6000000, "subtotal_items": 1200000, "total": 7200000,
            },
        )
        self.assertEqual(
            c["componentes"],
            [{"codigo": "A-01", "nombre": "Tornillo", "cantidad": 2, "precio": 1200000}],
        )
        self.assertEqual(c["servicio"]["precio"], 4500000)
        self.assertEqual(
            c["procesos"],
            [
                {"nombre": "Limpieza", "personalizado": False, "precio": 1500000},
                {"nombre": "Pulido", "personalizado": True, "precio": None},
            ],
        )
        self.assertEqual(self.client.get(URL).json()[0], c)

    def test_alta_sin_campos_nuevos_es_compatible(self):
        r = self.crear(numero="OT-1", componentes=[{"codigo": "A-01", "cantidad": 1}])
        self.assertEqual(r.status_code, 201)
        c = r.json()
        self.assertEqual(c["fecha"], "2026-11-20")
        for campo in ("fecha_ingreso", "fecha_egreso", "cliente", "celular", "casco", "motor", "trailer"):
            self.assertIsNone(c[campo], campo)
        self.assertEqual(c["componentes"][0]["precio"], None)
        self.assertEqual((c["subtotal_servicios"], c["subtotal_items"], c["total"]), (0, 0, 0))

    def test_datos_vacios_se_guardan_como_null(self):
        for n, vacio in enumerate(("  ", "", None)):
            with self.subTest(vacio=vacio):
                r = self.post(numero=f"OT-{n}", cliente=vacio, celular=vacio, casco=vacio,
                              fecha_ingreso=vacio, fecha_egreso=vacio,
                              componentes=[{"codigo": "A-01", "cantidad": 1}])
                self.assertEqual(r.status_code, 201, r.text)
                for campo in ("cliente", "celular", "casco", "fecha_ingreso", "fecha_egreso"):
                    self.assertIsNone(r.json()[campo])

    def test_solo_fecha_de_egreso(self):
        r = self.post(fecha_egreso="2026-11-20")
        self.assertEqual((r.status_code, r.json()["fecha_ingreso"], r.json()["fecha_egreso"]),
                         (201, None, "2026-11-20"))

    def test_422_sin_tocar_el_stock(self):
        casos = (
            ({"cliente": "x" * 81}, "El cliente admite hasta 80 caracteres."),
            ({"fecha_ingreso": "2026-11-27", "fecha_egreso": "2026-11-26"},
             "La fecha de egreso no puede ser anterior a la de ingreso."),
            ({"componentes": [{"codigo": "A-01", "cantidad": 1, "precio": 1500.5}]},
             f"Componente 1: {MSG_PRECIO}"),
            ({"precio_servicio": 1000}, "No se puede indicar el precio del servicio general sin elegir uno."),
            ({"celular": "abc"},
             "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)."),
            ({"cliente": 3}, "El campo cliente debe ser texto."),
            ({"procesos": [{"clave": "limpieza", "precio": -1}]}, f"Proceso 1: {MSG_PRECIO}"),
        )
        for extra, mensaje in casos:
            with self.subTest(extra=extra):
                r = self.post(**extra)
                self.assertEqual((r.status_code, r.json()), (422, {"detail": mensaje}))
        self.assertEqual(self.stocks(), {"A-01": 5, "B-02": 10, "C-99": 2})
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM ordenes"), [(0,)])

    def test_listado_con_subtotales_y_precios_vacios_cuentan_cero(self):
        self.post(
            numero="OT-0004", servicio="servicio-20-hs", precio_servicio=4500000,
            procesos=["limpieza"],
            componentes=[
                {"codigo": "A-01", "cantidad": 1, "precio": 1200000},
                {"codigo": "B-02", "cantidad": 1},
            ],
        )
        o = self.client.get(URL, params={"numero": "OT-0004"}).json()[0]
        self.assertEqual((o["subtotal_servicios"], o["subtotal_items"], o["total"]),
                         (4500000, 1200000, 5700000))

    def test_orden_anterior_a_la_migracion_trae_todo_en_null_y_totales_en_cero(self):
        conn = conectar(self.ruta)
        try:
            uid = conn.execute("SELECT id FROM usuarios LIMIT 1").fetchone()[0]
            oid = conn.execute(
                "INSERT INTO ordenes (numero, fecha, usuario_id) VALUES ('OT-OLD', '2026-11-01', ?)",
                (uid,),
            ).lastrowid
            conn.execute(
                "INSERT INTO orden_items (orden_id, producto_id, cantidad) "
                "SELECT ?, id, 1 FROM productos WHERE codigo = 'A-01'", (oid,),
            )
            conn.execute(
                "INSERT INTO orden_procesos (orden_id, posicion, nombre, personalizado) "
                "VALUES (?, 1, 'Limpieza', 0)", (oid,),
            )
            conn.commit()
        finally:
            conn.close()
        o = self.client.get(URL, params={"numero": "OT-OLD"}).json()[0]
        for campo in ("fecha_ingreso", "fecha_egreso", "cliente", "celular", "casco", "motor", "trailer"):
            self.assertIsNone(o[campo])
        self.assertIsNone(o["componentes"][0]["precio"])
        self.assertIsNone(o["procesos"][0]["precio"])
        self.assertEqual((o["subtotal_servicios"], o["subtotal_items"], o["total"]), (0, 0, 0))

    def test_renombrar_el_proceso_no_cambia_nombre_ni_precio_en_la_orden(self):
        self.post(procesos=[{"clave": "limpieza", "precio": 1500000}])
        self.client.patch("/api/procesos/limpieza", json={"nombre": "Limpieza total"})
        proceso = self.client.get(URL).json()[0]["procesos"][0]
        self.assertEqual(proceso, {"nombre": "Limpieza", "personalizado": False, "precio": 1500000})

    def test_filtros_de_fecha_son_sobre_la_fecha_de_la_orden(self):
        self.post(fecha="2026-11-20", fecha_ingreso="2026-11-24", fecha_egreso="2026-11-25")
        self.assertEqual(self.client.get(URL, params={"desde": "2026-11-24"}).json(), [])
        self.assertEqual(len(self.client.get(URL, params={"hasta": "2026-11-20"}).json()), 1)

    def test_borrado_devuelve_datos_precios_y_totales(self):
        creada = self.completo().json()
        r = self.client.delete(f"{URL}/OT-0043", params={"reintegrar": "false"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["orden"], creada)

    def test_openapi_documenta_los_campos_nuevos_y_sigue_con_21_rutas(self):
        spec = self.client.get("/openapi.json").json()
        self.assertEqual(len(spec["paths"]), 21)
        orden = spec["components"]["schemas"]["OrdenRequest"]["properties"]
        for campo in ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso",
                      "fecha_egreso", "precio_servicio"):
            self.assertIn(campo, orden)
        self.assertIn("centavos", orden["precio_servicio"]["description"])
        self.assertIn("centavos", spec["components"]["schemas"]["ComponenteRequest"]["properties"]["precio"]["description"])
        salida = spec["components"]["schemas"]["OrdenOut"]["properties"]
        self.assertTrue({"subtotal_servicios", "subtotal_items", "total", "fecha_ingreso"} <= set(salida))
