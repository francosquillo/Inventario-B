"""POST /api/stock/modificaciones (specs api-http, modificacion-stock)."""
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/stock/modificaciones"
MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000."
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def consultar(ruta, sql, params=()):
    conn = conectar(ruta)
    try:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def fijar(codigo, stock, **extra):
    return {"codigo": codigo, "modo": "fijar", "stock": stock, **extra}


def sumar(codigo, cantidad, **extra):
    return {"codigo": codigo, "modo": "sumar", "cantidad": cantidad, **extra}


class SinSesionTest(unittest.TestCase):
    def test_sin_sesion_401_sin_cambios(self):
        client, ruta = cliente_de_test(self.addCleanup)
        sembrar(ruta, [("A-01", "Tornillo", 5, 1)])
        r = client.post(URL, json={"lineas": [fijar("A-01", 9)]})
        self.assertEqual((r.status_code, r.json()), (401, {"detail": "No autenticado."}))
        self.assertEqual(consultar(ruta, "SELECT stock FROM productos"), [(5,)])


class Base(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(
            self.ruta,
            [
                ("A-01", "Tornillo", 5, 1),
                ("B-10", "Tuerca", 0, 1),
                ("C-99", "Junta", 2, 0),
            ],
        )
        self.assertEqual(login(self.client).status_code, 200)

    def modificar(self, *lineas):
        return self.client.post(URL, json={"lineas": list(lineas)})

    def estado(self):
        return consultar(self.ruta, "SELECT codigo, nombre, stock, activo FROM productos ORDER BY id")

    def cantidad_movimientos(self):
        return consultar(self.ruta, "SELECT COUNT(*) FROM movimientos")[0][0]

    def assertRechazo(self, respuesta, status, mensaje):
        self.assertEqual((respuesta.status_code, respuesta.json()), (status, {"detail": mensaje}))
        self.assertEqual(
            self.estado(),
            [("A-01", "Tornillo", 5, 1), ("B-10", "Tuerca", 0, 1), ("C-99", "Junta", 2, 0)],
        )
        self.assertEqual(self.cantidad_movimientos(), 0)


class ExitoTest(Base):
    def test_fijar_y_sumar_devuelve_las_lineas_exactas(self):
        r = self.modificar(fijar("A-01", 12, nombre="Tornillo M8"), sumar("b-10", 4))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "lineas": [
                    {
                        "codigo": "A-01",
                        "nombre": "Tornillo M8",
                        "stock": 12,
                        "sin_stock": False,
                        "modo": "fijar",
                        "stock_anterior": 5,
                        "nombre_anterior": "Tornillo",
                        "reactivado": False,
                    },
                    {
                        "codigo": "B-10",
                        "nombre": "Tuerca",
                        "stock": 4,
                        "sin_stock": False,
                        "modo": "sumar",
                        "stock_anterior": 0,
                        "nombre_anterior": "Tuerca",
                        "reactivado": False,
                    },
                ]
            },
        )
        tipos = [(m["codigo"], m["tipo"]) for m in self.client.get("/api/movimientos").json()]
        self.assertEqual(sorted(tipos), [("A-01", "ajuste"), ("B-10", "ingreso")])

    def test_reactivacion_con_fijar_mayor_a_cero(self):
        r = self.modificar(fijar("C-99", 6))
        self.assertEqual((r.status_code, r.json()["lineas"][0]["stock"], r.json()["lineas"][0]["reactivado"]), (200, 6, True))
        self.assertIn("C-99", [p["codigo"] for p in self.client.get("/api/inventario").json()])

    def test_reactivacion_con_sumar(self):
        r = self.modificar(sumar("C-99", 3))
        self.assertEqual((r.json()["lineas"][0]["stock"], r.json()["lineas"][0]["reactivado"]), (5, True))

    def test_fijar_cero_en_inactivo_no_reactiva(self):
        r = self.modificar(fijar("C-99", 0))
        linea = r.json()["lineas"][0]
        self.assertEqual((r.status_code, linea["stock"], linea["sin_stock"], linea["reactivado"]), (200, 0, True, False))
        self.assertNotIn("C-99", [p["codigo"] for p in self.client.get("/api/inventario").json()])
        self.assertIn("C-99", [p["codigo"] for p in self.client.get("/api/productos/inactivos").json()])

    def test_mismo_stock_o_solo_renombrar_en_inactivo_no_reactiva(self):
        for linea in (fijar("C-99", 2), fijar("C-99", 2, nombre="Junta tórica")):
            with self.subTest(linea=linea):
                r = self.modificar(linea)
                self.assertEqual(r.status_code, 200)
                self.assertFalse(r.json()["lineas"][0]["reactivado"])
        self.assertEqual(self.estado()[2], ("C-99", "Junta tórica", 2, 0))
        self.assertEqual(self.cantidad_movimientos(), 0)

    def test_linea_sin_cambios_se_acepta(self):
        r = self.modificar(fijar("A-01", 5))
        linea = r.json()["lineas"][0]
        self.assertEqual((r.status_code, linea["stock"], linea["stock_anterior"]), (200, 5, 5))
        self.assertEqual(self.cantidad_movimientos(), 0)

    def test_nombre_vacio_se_ignora(self):
        r = self.modificar(fijar("A-01", 6, nombre="   "))
        self.assertEqual(r.json()["lineas"][0]["nombre"], "Tornillo")


class ErroresTest(Base):
    def test_inexistente_404_con_codigos_y_sin_cambios(self):
        r = self.modificar(fijar("A-01", 3), sumar("z-01", 1))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(
            r.json(), {"detail": "No existe un producto con código 'Z-01'.", "codigos": ["Z-01"]}
        )
        self.assertEqual(self.estado()[0], ("A-01", "Tornillo", 5, 1))
        self.assertEqual(self.cantidad_movimientos(), 0)

    def test_varios_inexistentes_los_lista_todos(self):
        r = self.modificar(sumar("Z-01", 1), sumar("Z-02", 1))
        self.assertEqual(r.json()["codigos"], ["Z-01", "Z-02"])
        self.assertEqual(r.json()["detail"], "No existen productos con código: 'Z-01', 'Z-02'.")

    def test_modo_invalido_o_faltante(self):
        mensaje = "Línea 1: El campo modo debe ser fijar o sumar."
        self.assertRechazo(self.modificar({"codigo": "A-01", "modo": "restar", "stock": 1}), 422, mensaje)
        self.assertRechazo(self.modificar({"codigo": "A-01", "stock": 1}), 422, mensaje)

    def test_valor_faltante(self):
        self.assertRechazo(
            self.modificar(sumar("A-01", 1), {"codigo": "B-10", "modo": "fijar"}),
            422,
            "Línea 2: El campo stock es obligatorio.",
        )
        self.assertRechazo(
            self.modificar({"codigo": "B-10", "modo": "sumar"}),
            422,
            "Línea 1: El campo cantidad es obligatorio.",
        )

    def test_stock_fuera_de_rango(self):
        for valor in (-1, 10_001, "5", 2.5):
            with self.subTest(valor=valor):
                self.assertRechazo(
                    self.modificar(sumar("B-10", 1), fijar("A-01", valor)), 422, f"Línea 2: {MSG_STOCK}"
                )

    def test_cantidad_fuera_de_rango(self):
        for valor in (0, -1, 10_001, "1"):
            with self.subTest(valor=valor):
                self.assertRechazo(self.modificar(sumar("A-01", valor)), 422, f"Línea 1: {MSG_CANTIDAD}")

    def test_codigo_vacio_o_largo(self):
        self.assertRechazo(
            self.modificar(sumar("  ", 1)), 422, "Línea 1: El campo codigo es obligatorio."
        )
        self.assertRechazo(
            self.modificar(sumar("x" * 51, 1)),
            422,
            "Línea 1: El campo codigo admite hasta 50 caracteres.",
        )

    def test_nombre_largo(self):
        self.assertRechazo(
            self.modificar(fijar("A-01", 1), fijar("B-10", 1), fijar("C-99", 1, nombre="x" * 121)),
            422,
            "Línea 3: El campo nombre admite hasta 120 caracteres.",
        )

    def test_producto_repetido(self):
        self.assertRechazo(
            self.modificar(fijar("A-01", 3), sumar("a-01", 2)),
            422,
            "Línea 2: el producto 'A-01' ya está en la línea 1.",
        )

    def test_lista_vacia_ausente_o_demasiado_larga(self):
        self.assertRechazo(
            self.client.post(URL, json={"lineas": []}), 422, "La modificación requiere al menos una línea."
        )
        self.assertRechazo(
            self.client.post(URL, json={}), 422, "El campo lineas es obligatorio."
        )
        self.assertRechazo(
            self.client.post(URL, json={"lineas": [sumar(f"X-{i}", 1) for i in range(101)]}),
            422,
            "La modificación admite hasta 100 líneas.",
        )

    def test_linea_que_no_es_objeto(self):
        self.assertRechazo(
            self.client.post(URL, json={"lineas": ["A-01"]}),
            422,
            "Línea 1: debe ser un objeto con codigo, modo y stock o cantidad.",
        )

    def test_validacion_antes_que_inexistencia(self):
        r = self.modificar(sumar("Z-01", 1), sumar("A-01", 0))
        self.assertEqual((r.status_code, r.json()), (422, {"detail": f"Línea 2: {MSG_CANTIDAD}"}))


if __name__ == "__main__":
    unittest.main()
