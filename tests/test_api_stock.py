import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, movimientos, sembrar

MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def stock_de(ruta, codigo):
    filas = consultar(ruta, "SELECT stock FROM productos WHERE codigo = ?", (codigo,))
    return filas[0][0] if filas else None


def movs(ruta):
    conn = conectar(ruta)
    try:
        return movimientos(conn)
    finally:
        conn.close()


class StockSinSesionTest(unittest.TestCase):
    def test_ingreso_sin_sesion_401_sin_cambios(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        r = client.post("/api/stock/ingreso", json={"codigo": "A-01", "cantidad": 3})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(stock_de(ruta, "A-01"), 5)
        self.assertEqual(movs(ruta), [])

    def test_egreso_sin_sesion_401_sin_cambios(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        r = client.post("/api/stock/egreso", json={"codigo": "A-01", "cantidad": 3})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(stock_de(ruta, "A-01"), 5)

    def test_sin_sesion_con_cuerpo_invalido_sigue_siendo_401(self):
        client, _ = cliente_de_test(self.addCleanup)
        for ruta_http in ("/api/stock/ingreso", "/api/stock/egreso"):
            with self.subTest(ruta=ruta_http):
                r = client.post(ruta_http, json={"codigo": "", "cantidad": "x"})
                self.assertEqual(r.status_code, 401)


class StockBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(
            self.ruta,
            [("A-01", "Tornillo", 5, 1), ("B-10", "Tuerca", 0, 1), ("C-99", "Viejo", 2, 0)],
        )
        self.assertEqual(login(self.client).status_code, 200)

    def ingreso(self, **cuerpo):
        return self.client.post("/api/stock/ingreso", json=cuerpo)

    def egreso(self, **cuerpo):
        return self.client.post("/api/stock/egreso", json=cuerpo)


class IngresoConSesionTest(StockBase):
    def test_suma_devuelve_claves_exactas(self):
        r = self.ingreso(codigo="A-01", cantidad=3)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "codigo": "A-01",
                "nombre": "Tornillo",
                "stock": 8,
                "sin_stock": False,
                "categoria": None,
                "creado": False,
                "reactivado": False,
            },
        )

    def test_alta_con_codigo_en_minusculas_queda_en_mayusculas(self):
        r = self.ingreso(codigo="rd-6204", cantidad=4, nombre="  Rodamiento  ")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(
            (cuerpo["codigo"], cuerpo["nombre"], cuerpo["stock"], cuerpo["creado"]),
            ("RD-6204", "Rodamiento", 4, True),
        )
        inv = self.client.get("/api/inventario").json()
        self.assertIn("RD-6204", [p["codigo"] for p in inv])

    def test_reactivacion(self):
        r = self.ingreso(codigo="C-99", cantidad=3)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["reactivado"])
        self.assertFalse(r.json()["creado"])
        self.assertEqual(r.json()["stock"], 5)

    def test_movimiento_con_usuario_de_la_sesion_y_fecha_local(self):
        self.ingreso(codigo="A-01", cantidad=3)
        uid = self.client.get("/api/me").json()["id"]
        filas = movs(self.ruta)
        self.assertEqual(len(filas), 1)
        tipo, cantidad, codigo, usuario_id, fecha = filas[0]
        self.assertEqual((tipo, cantidad, codigo, usuario_id), ("ingreso", 3, "A-01", uid))
        self.assertTrue(fecha.endswith("-03:00"))

    def test_codigo_nuevo_sin_nombre_422_y_no_crea(self):
        r = self.ingreso(codigo="N-02", cantidad=1)
        self.assertEqual(r.status_code, 422)
        self.assertIsInstance(r.json()["detail"], str)
        self.assertEqual(
            r.json()["detail"], "El producto 'N-02' no existe: indicá un nombre para crearlo."
        )
        self.assertIsNone(stock_de(self.ruta, "N-02"))

    def test_nombre_null_se_acepta_como_ausente(self):
        r = self.ingreso(codigo="A-01", cantidad=1, nombre=None)
        self.assertEqual(r.status_code, 200)


class EgresoConSesionTest(StockBase):
    def test_egreso_en_minusculas_devuelve_codigo_normalizado(self):
        r = self.egreso(codigo="a-01", cantidad=2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"codigo": "A-01", "nombre": "Tornillo", "stock": 3, "sin_stock": False, "categoria": None},
        )

    def test_egreso_de_todo_marca_sin_stock(self):
        r = self.egreso(codigo="A-01", cantidad=5)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["sin_stock"])

    def test_inexistente_e_inactivo_404_con_el_mismo_formato(self):
        for codigo, esperado in (("X-00", "X-00"), ("C-99", "C-99")):
            with self.subTest(codigo=codigo):
                r = self.egreso(codigo=codigo, cantidad=1)
                self.assertEqual(r.status_code, 404)
                self.assertEqual(
                    r.json(), {"detail": f"No existe un producto activo con código '{esperado}'."}
                )
        self.assertEqual(stock_de(self.ruta, "C-99"), 2)

    def test_exceso_409_con_disponible_y_stock_intacto(self):
        r = self.egreso(codigo="A-01", cantidad=6)
        self.assertEqual(r.status_code, 409)
        self.assertIn("disponible 5", r.json()["detail"])
        self.assertIn("solicitado 6", r.json()["detail"])
        self.assertEqual(stock_de(self.ruta, "A-01"), 5)
        self.assertEqual(movs(self.ruta), [])


class ValidacionHttpTest(StockBase):
    def casos_cantidad(self):
        return ["5", 2.5, 0, True, 10001, -1, None]

    def test_cantidad_invalida_en_ingreso_y_egreso(self):
        for cantidad in self.casos_cantidad():
            for llamar in (self.ingreso, self.egreso):
                with self.subTest(cantidad=cantidad, op=llamar.__name__):
                    r = llamar(codigo="A-01", cantidad=cantidad)
                    self.assertEqual(r.status_code, 422)
                    self.assertEqual(r.json(), {"detail": MSG_CANTIDAD})
        self.assertEqual(stock_de(self.ruta, "A-01"), 5)

    def test_cantidad_limite_se_acepta(self):
        r = self.ingreso(codigo="A-01", cantidad=10000)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["stock"], 10005)

    def test_cantidad_faltante(self):
        r = self.ingreso(codigo="A-01")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo cantidad es obligatorio."})

    def test_codigo_faltante_o_vacio(self):
        for cuerpo in ({"cantidad": 1}, {"codigo": "", "cantidad": 1}):
            with self.subTest(cuerpo=cuerpo):
                r = self.client.post("/api/stock/ingreso", json=cuerpo)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": "El campo codigo es obligatorio."})

    def test_codigo_demasiado_largo(self):
        r = self.ingreso(codigo="x" * 51, cantidad=1, nombre="N")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo codigo admite hasta 50 caracteres."})

    def test_codigo_solo_espacios_lo_rechaza_el_service(self):
        for llamar in (self.ingreso, self.egreso):
            with self.subTest(op=llamar.__name__):
                kwargs = {"codigo": "   ", "cantidad": 1}
                r = llamar(**kwargs)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": "El campo codigo es obligatorio."})
        self.assertEqual(consultar(self.ruta, "SELECT COUNT(*) FROM productos"), [(3,)])

    def test_nombre_demasiado_largo(self):
        r = self.ingreso(codigo="N-01", cantidad=1, nombre="n" * 121)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo nombre admite hasta 120 caracteres."})
        self.assertIsNone(stock_de(self.ruta, "N-01"))

    def test_codigo_con_espacios_se_mide_tras_normalizar(self):
        for codigo, esperado in (("  " + "a" * 48 + "  ", "A" * 48), (" " + "b" * 50 + " ", "B" * 50)):
            with self.subTest(largo=len(codigo)):
                r = self.ingreso(codigo=codigo, cantidad=1, nombre="N")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json()["codigo"], esperado)
                self.assertEqual(stock_de(self.ruta, esperado), 1)

    def test_codigo_de_51_tras_recortar_sigue_rechazado(self):
        r = self.ingreso(codigo=" " + "c" * 51 + " ", cantidad=1, nombre="N")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo codigo admite hasta 50 caracteres."})

    def test_nombre_con_espacios_se_mide_tras_recortar(self):
        r = self.ingreso(codigo="N-02", cantidad=1, nombre="  " + "n" * 120 + "  ")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["nombre"], "n" * 120)
        r = self.ingreso(codigo="N-03", cantidad=1, nombre=" " + "n" * 121 + " ")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo nombre admite hasta 120 caracteres."})
        self.assertIsNone(stock_de(self.ruta, "N-03"))

    def test_egreso_con_codigo_con_espacios_se_mide_tras_normalizar(self):
        r = self.egreso(codigo=" " + "z" * 50 + " ", cantidad=1)
        self.assertEqual(r.status_code, 404)

    def test_varios_errores_responde_solo_el_primero(self):
        r = self.client.post("/api/stock/ingreso", json={"cantidad": 0})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"detail": "El campo codigo es obligatorio."})


if __name__ == "__main__":
    unittest.main()
