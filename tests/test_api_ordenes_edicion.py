"""PUT /api/ordenes/{numero}: edicion con ajuste de stock por diferencia (C-06i, design D1)."""
import json
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/ordenes"
# A-01 con 7 para que, tras el alta de OT-0043 (x 2), quede en 5 como en los escenarios.
PRODUCTOS = [("A-01", "Tornillo", 7, 1), ("B-02", "Tuerca", 3, 1), ("C-99", "Viejo", 2, 0)]
MSG_NUMERO = "El número de la orden no se puede cambiar."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


class EdicionBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, PRODUCTOS)
        self.assertEqual(login(self.client).status_code, 200)
        r = self.client.post(
            URL,
            json={
                "numero": "OT-0043", "fecha": "2026-11-27",
                "componentes": [{"codigo": "A-01", "cantidad": 2}],
            },
        )
        self.assertEqual(r.status_code, 201)
        self.id_orden = r.json()["id"]

    def put(self, url_numero="ot-0043", **extra):
        cuerpo = {"fecha": "2026-11-27", "componentes": [{"codigo": "A-01", "cantidad": 2}]}
        cuerpo.update(extra)
        return self.client.put(f"{URL}/{url_numero}", json=cuerpo)

    def stocks(self):
        return dict(consultar(self.ruta, "SELECT codigo, stock FROM productos"))

    def orden(self, numero="OT-0043"):
        return self.client.get(URL, params={"numero": numero}).json()[0]

    def estado(self):
        return (
            self.stocks(),
            self.client.get(URL).json(),
            self.client.get("/api/movimientos").json(),
        )


class EdicionConAjustesTest(EdicionBase):
    def test_edicion_con_ajustes_diccionario_exacto_y_sin_movimientos(self):
        movimientos_antes = self.client.get("/api/movimientos").json()
        r = self.put(
            componentes=[{"codigo": "B-02", "cantidad": 1, "precio": 50000}],
            chequeo_final=[{"clave": "entrega", "precio": 500000}],
        )
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        orden = cuerpo["orden"]
        self.assertEqual((orden["numero"], orden["id"]), ("OT-0043", self.id_orden))
        self.assertEqual(
            orden["componentes"],
            [{"codigo": "B-02", "nombre": "Tuerca", "cantidad": 1, "precio": 50000}],
        )
        self.assertEqual(
            orden["chequeo_final"], [{"clave": "entrega", "nombre": "Entrega", "precio": 500000}]
        )
        self.assertEqual(
            (orden["subtotal_servicios"], orden["subtotal_items"], orden["total"]),
            (500000, 50000, 550000),
        )
        self.assertEqual(
            cuerpo["ajustes"],
            [
                {"codigo": "A-01", "nombre": "Tornillo", "cantidad_anterior": 2,
                 "cantidad_nueva": 0, "stock": 7, "reactivado": False},
                {"codigo": "B-02", "nombre": "Tuerca", "cantidad_anterior": 0,
                 "cantidad_nueva": 1, "stock": 2, "reactivado": False},
            ],
        )
        self.assertEqual(set(cuerpo), {"orden", "ajustes"})
        self.assertEqual(self.stocks(), {"A-01": 7, "B-02": 2, "C-99": 2})
        self.assertEqual(self.client.get("/api/movimientos").json(), movimientos_antes)

    def test_aumentar_y_reducir_con_otra_orden(self):
        r = self.put(componentes=[{"codigo": "A-01", "cantidad": 4}], cliente="Juan Pérez")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.stocks()["A-01"], 3)
        self.assertEqual(r.json()["orden"]["cliente"], "Juan Pérez")
        self.assertEqual(r.json()["ajustes"][0]["cantidad_nueva"], 4)
        r = self.put(componentes=[{"codigo": "A-01", "cantidad": 1}])
        self.assertEqual(self.stocks()["A-01"], 6)
        self.assertIsNone(r.json()["orden"]["cliente"])  # reemplazo completo

    def test_edicion_identica_devuelve_ajustes_vacios(self):
        r = self.put()
        self.assertEqual((r.status_code, r.json()["ajustes"]), (200, []))
        self.assertEqual(self.stocks()["A-01"], 5)

    def test_conservar_servicio_por_api(self):
        self.client.put(f"{URL}/OT-0043", json={
            "fecha": "2026-11-27", "componentes": [{"codigo": "A-01", "cantidad": 2}],
            "servicio": "servicio-20-hs",
        })
        r = self.put("OT-0043", conservar_servicio=True, precio_servicio=4500000)
        self.assertEqual(r.status_code, 200)
        servicio = r.json()["orden"]["servicio"]
        self.assertEqual(servicio["nombre"], "Servicio 20 hs")
        self.assertEqual(len(servicio["chequeos"]), 3)
        self.assertEqual(servicio["precio"], 4500000)

    def test_numero_con_barra(self):
        self.client.post(URL, json={
            "numero": "OT/12", "fecha": "2026-11-27",
            "componentes": [{"codigo": "B-02", "cantidad": 1}],
        })
        r = self.put("OT/12", componentes=[{"codigo": "B-02", "cantidad": 2}])
        self.assertEqual((r.status_code, r.json()["orden"]["numero"]), (200, "OT/12"))
        self.assertEqual(self.stocks()["B-02"], 1)

    def test_la_orden_editada_se_lista_con_su_contenido_vigente(self):
        self.put(fecha="2026-11-28", componentes=[{"codigo": "A-01", "cantidad": 3}])
        listada = self.client.get(URL, params={"desde": "2026-11-28"}).json()
        self.assertEqual([(o["numero"], o["fecha"]) for o in listada], [("OT-0043", "2026-11-28")])
        self.assertEqual(listada[0]["componentes"][0]["cantidad"], 3)


class EdicionRechazosTest(EdicionBase):
    def assertRechazo(self, r, status, detail=None):
        self.assertEqual(r.status_code, status)
        if detail is not None:
            self.assertEqual(r.json()["detail"], detail)

    def test_stock_insuficiente_409_con_faltantes_y_sin_cambios(self):
        self.client.put(f"{URL}/OT-0043", json={
            "fecha": "2026-11-27", "componentes": [{"codigo": "A-01", "cantidad": 2}],
        })
        self.client.post("/api/stock/egreso", json={"codigo": "A-01", "cantidad": 4})  # stock 1
        antes = self.estado()
        r = self.put(componentes=[{"codigo": "A-01", "cantidad": 5}])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["faltantes"], [{"codigo": "A-01", "disponible": 1, "solicitado": 3}])
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.orden()["componentes"][0]["cantidad"], 2)

    def test_orden_inexistente_404(self):
        antes = self.estado()
        r = self.put("OT-9999")
        self.assertRechazo(r, 404, "No existe una orden con número 'OT-9999'.")
        self.assertEqual(self.estado(), antes)

    def test_producto_inexistente_404_con_codigos(self):
        antes = self.estado()
        r = self.put(componentes=[
            {"codigo": "A-01", "cantidad": 2}, {"codigo": "ZZ-99", "cantidad": 1},
            {"codigo": "C-99", "cantidad": 1},
        ])
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["codigos"], ["ZZ-99", "C-99"])
        self.assertIn("'ZZ-99'", r.json()["detail"])
        self.assertEqual(self.estado(), antes)

    def test_un_solo_producto_inexistente_404_con_codigos(self):
        r = self.put(componentes=[{"codigo": "ZZ-99", "cantidad": 1}])
        self.assertEqual(
            (r.status_code, r.json()),
            (404, {"detail": "No existe un producto activo con código 'ZZ-99'.", "codigos": ["ZZ-99"]}),
        )

    def test_numero_en_el_cuerpo_422(self):
        antes = self.estado()
        r = self.put(numero="OT-0044")
        self.assertRechazo(r, 422, MSG_NUMERO)
        self.assertEqual(self.estado(), antes)
        self.assertRechazo(self.put(numero=None), 200)  # null se ignora

    def test_conservar_sin_servicio_422(self):
        r = self.put(conservar_servicio=True)
        self.assertRechazo(r, 422, "La orden no tiene un servicio general para conservar.")

    def test_conservar_y_elegir_422_y_tipo_invalido_422(self):
        self.assertRechazo(
            self.put(conservar_servicio=True, servicio="servicio-20-hs"), 422,
            "No se puede elegir un servicio general y conservar el actual a la vez.",
        )
        self.assertRechazo(
            self.put(conservar_servicio="si"), 422,
            "El campo conservar_servicio debe ser true o false.",
        )

    def test_chequeo_invalido_422_sin_tocar_stock(self):
        antes = self.estado()
        r = self.put(
            componentes=[{"codigo": "A-01", "cantidad": 3}], chequeo_final=["lavado"]
        )
        self.assertRechazo(r, 422, "El ítem de chequeo final 'lavado' no existe.")
        self.assertEqual(self.estado(), antes)

    def test_fecha_invalida_422_antes_del_404(self):
        r = self.put("OT-9999", fecha="2026-02-30")
        self.assertRechazo(r, 422, "La fecha (2026-02-30) no es una fecha válida.")

    def test_sin_sesion_401_sin_cambios(self):
        self.client.post("/api/logout")
        r = self.put(componentes=[{"codigo": "A-01", "cantidad": 4}])
        self.assertEqual(r.status_code, 401)
        login(self.client)
        self.assertEqual(self.stocks()["A-01"], 5)

    def test_cuerpo_que_no_es_json_422_sin_cambios(self):
        antes = self.estado()
        for tipo in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data"):
            with self.subTest(tipo=tipo):
                r = self.client.put(
                    f"{URL}/OT-0043",
                    content=json.dumps({
                        "fecha": "2026-11-27",
                        "componentes": [{"codigo": "A-01", "cantidad": 4}],
                    }),
                    headers={"Content-Type": tipo},
                )
                self.assertRechazo(r, 422, "El cuerpo de la petición debe ser un objeto JSON.")
        self.assertEqual(self.estado(), antes)

    def test_componentes_vacios_422(self):
        r = self.put(componentes=[])
        self.assertEqual(r.status_code, 422)


class AltaConChequeoApiTest(EdicionBase):
    def test_alta_con_chequeo_devuelve_el_orden_fijo_y_suma_servicios(self):
        r = self.client.post(URL, json={
            "numero": "OT-5", "fecha": "2026-11-27",
            "componentes": [{"codigo": "B-02", "cantidad": 1}],
            "chequeo_final": ["entrega", {"clave": "combustible", "precio": 800000}],
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()["chequeo_final"],
            [
                {"clave": "combustible", "nombre": "Combustible", "precio": 800000},
                {"clave": "entrega", "nombre": "Entrega", "precio": None},
            ],
        )
        self.assertEqual(r.json()["subtotal_servicios"], 800000)

    def test_alta_sin_chequeo_devuelve_lista_vacia(self):
        self.assertEqual(self.orden()["chequeo_final"], [])

    def test_alta_con_item_inexistente_422_sin_tocar_stock(self):
        r = self.client.post(URL, json={
            "numero": "OT-6", "fecha": "2026-11-27",
            "componentes": [{"codigo": "B-02", "cantidad": 1}], "chequeo_final": ["lavado"],
        })
        self.assertEqual(
            (r.status_code, r.json()["detail"]), (422, "El ítem de chequeo final 'lavado' no existe.")
        )
        self.assertEqual(self.stocks()["B-02"], 3)

    def test_listado_y_borrado_incluyen_el_chequeo(self):
        self.put(chequeo_final=["entrega"])
        self.assertEqual(self.orden()["chequeo_final"][0]["clave"], "entrega")
        r = self.client.delete(f"{URL}/OT-0043", params={"reintegrar": "true"})
        self.assertEqual(r.json()["orden"]["chequeo_final"][0]["clave"], "entrega")


class OpenApiEdicionTest(EdicionBase):
    def test_put_documentado_en_la_ruta_del_borrado(self):
        spec = self.client.get("/openapi.json").json()
        ruta = spec["paths"]["/api/ordenes/{numero}"]
        self.assertEqual(set(ruta), {"put", "delete"})
        for codigo in ("200", "404", "409", "422"):
            self.assertIn(codigo, ruta["put"]["responses"])
        self.assertTrue(
            ruta["put"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
            .endswith("/EdicionOrdenOut")
        )


if __name__ == "__main__":
    unittest.main()
