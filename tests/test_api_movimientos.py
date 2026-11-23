import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import (
    cliente_de_test,
    insertar_movimiento,
    insertar_producto,
    login,
)

CLAVES = {
    "fecha", "codigo", "nombre", "tipo", "cantidad", "usuario", "stock_anterior", "stock_nuevo",
}


def sembrar_movimientos(ruta, filas):
    """filas: (fecha, codigo, tipo, cantidad, activo). Crea productos si faltan."""
    conn = conectar(ruta)
    try:
        uid = conn.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone()[0]
        ids = {}
        for fecha, codigo, tipo, cantidad, activo in filas:
            if codigo not in ids:
                ids[codigo] = insertar_producto(conn, codigo, f"Prod {codigo}", 5, activo)
            insertar_movimiento(conn, fecha, ids[codigo], tipo, cantidad, uid)
        conn.commit()
    finally:
        conn.close()


class MovimientosAjusteTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        self.assertEqual(login(self.client).status_code, 200)

    def test_ajuste_expone_anterior_y_nuevo(self):
        conn = conectar(self.ruta)
        try:
            uid = conn.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone()[0]
            pid = insertar_producto(conn, "A-01", "Tornillo", 4)
            conn.execute(
                "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id,"
                " stock_anterior, stock_nuevo)"
                " VALUES ('2026-11-19T10:00:00-03:00', ?, 'ajuste', 3, ?, 7, 4)",
                (pid, uid),
            )
            conn.commit()
        finally:
            conn.close()
        lista = self.client.get("/api/movimientos?codigo=a-01").json()
        self.assertEqual(len(lista), 1)
        self.assertEqual(
            (lista[0]["tipo"], lista[0]["cantidad"], lista[0]["stock_anterior"], lista[0]["stock_nuevo"]),
            ("ajuste", 3, 7, 4),
        )


class MovimientosSinSesionTest(unittest.TestCase):
    def test_sin_sesion_401(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar_movimientos(ruta, [("2026-11-19T15:30:00-03:00", "A-01", "ingreso", 1, 1)])
        r = client.get("/api/movimientos")
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("A-01", r.text)

    def test_sin_sesion_con_filtros_invalidos_sigue_401(self):
        client, _ = cliente_de_test(self.addCleanup)
        self.assertEqual(client.get("/api/movimientos?desde=mal").status_code, 401)


class MovimientosConSesionTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        self.assertEqual(login(self.client).status_code, 200)

    def test_sin_movimientos_lista_vacia(self):
        r = self.client.get("/api/movimientos")
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_tras_un_ingreso_por_api(self):
        self.client.post(
            "/api/stock/ingreso", json={"codigo": "a-01", "cantidad": 3, "nombre": "Tornillo"}
        )
        r = self.client.get("/api/movimientos")
        self.assertEqual(r.status_code, 200)
        lista = r.json()
        self.assertEqual(len(lista), 1)
        self.assertEqual(set(lista[0]), CLAVES)
        self.assertEqual(
            (lista[0]["codigo"], lista[0]["tipo"], lista[0]["cantidad"], lista[0]["usuario"]),
            ("A-01", "ingreso", 3, "admin"),
        )
        self.assertTrue(lista[0]["fecha"].endswith("-03:00"))
        self.assertIsNone(lista[0]["stock_anterior"])
        self.assertIsNone(lista[0]["stock_nuevo"])

    def test_orden_y_serializacion_exacta_de_fecha(self):
        sembrar_movimientos(
            self.ruta,
            [
                ("2026-11-18T09:00:00-03:00", "A-01", "ingreso", 2, 1),
                ("2026-11-19T15:30:00-03:00", "A-01", "egreso", 1, 1),
            ],
        )
        lista = self.client.get("/api/movimientos").json()
        self.assertEqual(
            [m["fecha"] for m in lista],
            ["2026-11-19T15:30:00-03:00", "2026-11-18T09:00:00-03:00"],
        )
        self.assertEqual(lista[0]["tipo"], "egreso")


class MovimientosFiltrosTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        self.assertEqual(login(self.client).status_code, 200)
        sembrar_movimientos(
            self.ruta,
            [
                ("2026-11-17T10:00:00-03:00", "A-01", "ingreso", 1, 1),
                ("2026-11-18T10:00:00-03:00", "A-01", "ingreso", 2, 1),
                ("2026-11-19T10:00:00-03:00", "B-10", "ingreso", 3, 1),
                ("2026-11-19T11:00:00-03:00", "C-99", "ingreso", 4, 0),
            ],
        )

    def codigos(self, query):
        r = self.client.get("/api/movimientos" + query)
        self.assertEqual(r.status_code, 200, r.text)
        return [m["codigo"] for m in r.json()]

    def test_codigo_en_minusculas_y_fechas(self):
        self.assertEqual(self.codigos("?codigo=a-01&desde=2026-11-18&hasta=2026-11-19"), ["A-01"])

    def test_incluye_producto_inactivo(self):
        self.assertEqual(self.codigos("?codigo=C-99"), ["C-99"])

    def test_codigo_vacio_es_sin_filtro(self):
        self.assertEqual(len(self.codigos("?codigo=")), 4)

    def test_filtro_solo_desde(self):
        self.assertEqual(self.codigos("?desde=2026-11-19"), ["C-99", "B-10"])

    def test_errores_de_filtro_en_espanol(self):
        casos = [
            ("?desde=19/11/2026", "La fecha 'desde' debe tener formato AAAA-MM-DD."),
            ("?desde=2026-02-30", "La fecha 'desde' (2026-02-30) no es una fecha válida."),
            (
                "?desde=2026-11-20&hasta=2026-11-19",
                "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).",
            ),
        ]
        casos += [
            ("?desde=%202026-11-19", "La fecha 'desde' debe tener formato AAAA-MM-DD."),
            ("?hasta=2026-11-19%0A", "La fecha 'hasta' debe tener formato AAAA-MM-DD."),
        ]
        for query, mensaje in casos:
            with self.subTest(query=query):
                r = self.client.get("/api/movimientos" + query)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json(), {"detail": mensaje})


class OpenApiTest(unittest.TestCase):
    def test_siete_endpoints_y_422_con_error_out(self):
        client, _ = cliente_de_test(self.addCleanup)
        paths = client.get("/openapi.json").json()["paths"]
        for ruta in (
            "/api/login",
            "/api/logout",
            "/api/me",
            "/api/inventario",
            "/api/stock/ingreso",
            "/api/stock/egreso",
            "/api/movimientos",
            "/api/ordenes",
            "/api/ordenes/{numero}",
            "/api/productos/{codigo}",
        ):
            with self.subTest(ruta=ruta):
                self.assertIn(ruta, paths)
        operaciones = [
            paths["/api/stock/ingreso"]["post"],
            paths["/api/stock/egreso"]["post"],
            paths["/api/movimientos"]["get"],
        ]
        for op in operaciones:
            ref = op["responses"]["422"]["content"]["application/json"]["schema"]["$ref"]
            self.assertTrue(ref.endswith("/ErrorOut"))


if __name__ == "__main__":
    unittest.main()
