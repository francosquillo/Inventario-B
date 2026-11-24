"""GET /api/reportes/* (spec api-http): sesion, forma exacta, filtros, 422 en espanol, solo lectura."""
import unittest
from datetime import timedelta

from inventario.domain.tiempo import ahora_argentina
from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

URL = "/api/reportes/productos-en-ordenes"
USADOS = "/api/reportes/productos-usados"
PRODUCTOS = [
    ("A-01", "Tornillo", 100, 1),
    ("B-02", "Tuerca", 100, 1),
    ("C-99", "Viejo", 100, 1),
    ("D-04", "Nunca", 100, 1),
]
NOV = "desde=2026-11-01&hasta=2026-11-30"


def contar(ruta):
    conn = conectar(ruta)
    try:
        return [
            tuple(tuple(f) for f in conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall())
            for t in ("productos", "ordenes", "orden_items", "movimientos")
        ]
    finally:
        conn.close()


class SinSesionTest(unittest.TestCase):
    def test_401_con_y_sin_parametros(self):
        client, _ = cliente_de_test(self.addCleanup)
        for url in (f"{URL}?{NOV}", URL, USADOS):
            r = client.get(url)
            self.assertEqual(r.status_code, 401, url)
            self.assertEqual(r.json(), {"detail": "No autenticado."})


class ReporteBase(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, PRODUCTOS)
        self.assertEqual(login(self.client).status_code, 200)

    def orden(self, numero, fecha, componentes):
        r = self.client.post(
            "/api/ordenes",
            json={
                "numero": numero,
                "fecha": fecha,
                "componentes": [{"codigo": c, "cantidad": n} for c, n in componentes],
            },
        )
        self.assertEqual(r.status_code, 201, r.text)

    def dar_de_baja(self, codigo):
        conn = conectar(self.ruta)
        try:
            conn.execute("UPDATE productos SET activo = 0 WHERE codigo = ?", (codigo,))
            conn.commit()
        finally:
            conn.close()

    def sembrar_ordenes(self):
        self.orden("OT-1", "2026-11-05", [("A-01", 3), ("B-02", 1)])
        self.orden("OT-2", "2026-11-06", [("A-01", 2)])


class ReporteTest(ReporteBase):
    def test_200_lista_exacta(self):
        self.sembrar_ordenes()
        r = self.client.get(f"{URL}?{NOV}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            [
                {"codigo": "A-01", "nombre": "Tornillo", "activo": True, "categoria": None, "cantidad": 5, "ordenes": 2},
                {"codigo": "B-02", "nombre": "Tuerca", "activo": True, "categoria": None, "cantidad": 1, "ordenes": 1},
            ],
        )

    def test_filtro_por_codigo_normalizado(self):
        self.sembrar_ordenes()
        r = self.client.get(f"{URL}?{NOV}&codigo=b-02")
        self.assertEqual([f["codigo"] for f in r.json()], ["B-02"])

    def test_dado_de_baja_con_activo_false_y_filtro_por_su_codigo(self):
        self.orden("OT-1", "2026-11-05", [("C-99", 4), ("A-01", 1)])
        self.dar_de_baja("C-99")
        r = self.client.get(f"{URL}?{NOV}")
        self.assertEqual(r.json()[0]["activo"], False)
        r = self.client.get(f"{URL}?{NOV}&codigo=c-99")
        self.assertEqual(r.json(), [
            {"codigo": "C-99", "nombre": "Viejo", "activo": False, "categoria": None, "cantidad": 4, "ordenes": 1}
        ])

    def test_vacio_y_codigo_desconocido(self):
        self.assertEqual(self.client.get(f"{URL}?{NOV}").json(), [])
        self.sembrar_ordenes()
        r = self.client.get(f"{URL}?{NOV}&codigo=ZZ-99")
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_sin_hasta_equivale_a_hoy(self):
        hoy = ahora_argentina().date()
        self.orden("OT-1", hoy.isoformat(), [("A-01", 2)])
        self.orden("OT-2", (hoy - timedelta(days=1)).isoformat(), [("B-02", 1)])
        sin = self.client.get(f"{URL}?desde={hoy - timedelta(days=5)}")
        con = self.client.get(f"{URL}?desde={hoy - timedelta(days=5)}&hasta={hoy}")
        vacio = self.client.get(f"{URL}?desde={hoy - timedelta(days=5)}&hasta=")
        self.assertEqual(sin.status_code, 200)
        self.assertEqual(len(sin.json()), 2)
        self.assertEqual(sin.json(), con.json())
        self.assertEqual(sin.json(), vacio.json())

    def test_422_en_espanol(self):
        casos = [
            (URL, "La fecha 'desde' es obligatoria."),
            (f"{URL}?desde=", "La fecha 'desde' es obligatoria."),
            (f"{URL}?desde=01/11/2026", "La fecha 'desde' debe tener formato AAAA-MM-DD."),
            (
                f"{URL}?desde=2026-11-30&hasta=2026-11-01",
                "La fecha 'desde' (2026-11-30) no puede ser posterior a 'hasta' (2026-11-01).",
            ),
        ]
        for url, mensaje in casos:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 422, url)
            self.assertEqual(r.json(), {"detail": mensaje})

    def test_422_desde_futuro_sin_hasta(self):
        hoy = ahora_argentina().date()
        futuro = hoy + timedelta(days=10)
        r = self.client.get(f"{URL}?desde={futuro}")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(
            r.json()["detail"],
            f"La fecha 'desde' ({futuro}) no puede ser posterior a 'hasta' ({hoy}).",
        )

    def test_solo_lectura(self):
        self.sembrar_ordenes()
        antes = contar(self.ruta)
        self.client.get(f"{URL}?{NOV}")
        self.client.get(USADOS)
        self.assertEqual(contar(self.ruta), antes)


class UsadosTest(ReporteBase):
    def test_forma_exacta_orden_y_exclusion(self):
        self.orden("OT-1", "2026-11-05", [("C-99", 1), ("A-01", 1)])
        self.orden("OT-2", "2026-10-05", [("A-01", 1)])
        self.dar_de_baja("C-99")
        r = self.client.get(USADOS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [
            {"codigo": "A-01", "nombre": "Tornillo", "activo": True},
            {"codigo": "C-99", "nombre": "Viejo", "activo": False},
        ])

    def test_vacio_sin_ordenes(self):
        self.assertEqual(self.client.get(USADOS).json(), [])


if __name__ == "__main__":
    unittest.main()
