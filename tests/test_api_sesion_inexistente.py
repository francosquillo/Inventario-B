"""Sesion firmada cuyo usuario ya no existe en `usuarios`: 401, nunca 500 (C-03, W-2)."""
import unittest

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import cliente_de_test, login, sembrar

PRODUCTOS = [("A-01", "Tornillo", 5, 1)]
ORDEN = {"numero": "OT-1", "fecha": "2026-11-20", "componentes": [{"codigo": "A-01", "cantidad": 1}]}

# (nombre, metodo, url, cuerpo)
ENDPOINTS = (
    ("crear orden", "post", "/api/ordenes", ORDEN),
    ("listar ordenes", "get", "/api/ordenes", None),
    ("ingreso", "post", "/api/stock/ingreso", {"codigo": "A-01", "cantidad": 1}),
    ("egreso", "post", "/api/stock/egreso", {"codigo": "A-01", "cantidad": 1}),
    ("movimientos", "get", "/api/movimientos", None),
    ("inventario", "get", "/api/inventario", None),
    ("me", "get", "/api/me", None),
)


def foto(ruta):
    """Contenido de las tablas de datos (todo salvo usuarios)."""
    conn = conectar(ruta)
    try:
        return {
            tabla: [tuple(f) for f in conn.execute(f"SELECT * FROM {tabla} ORDER BY 1").fetchall()]
            for tabla in ("productos", "movimientos", "ordenes", "orden_items")
        }
    finally:
        conn.close()


def ejecutar(sql, ruta, params=()):
    conn = conectar(ruta)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


class SesionDeUsuarioInexistenteTest(unittest.TestCase):
    def setUp(self):
        self.client, self.ruta = cliente_de_test(self.addCleanup)
        sembrar(self.ruta, PRODUCTOS)
        self.assertEqual(login(self.client).status_code, 200)
        self.antes = foto(self.ruta)

    def llamar(self, metodo, url, cuerpo):
        if metodo == "post":
            return self.client.post(url, json=cuerpo)
        return self.client.get(url)

    def test_sesion_valida_antes_de_borrar_al_usuario(self):
        for nombre, metodo, url, cuerpo in ENDPOINTS[1:2] + ENDPOINTS[4:]:
            with self.subTest(endpoint=nombre):
                self.assertEqual(self.llamar(metodo, url, cuerpo).status_code, 200)

    def test_usuario_borrado_da_401_en_todos_los_endpoints_protegidos(self):
        ejecutar("DELETE FROM usuarios", self.ruta)
        for nombre, metodo, url, cuerpo in ENDPOINTS:
            with self.subTest(endpoint=nombre):
                r = self.llamar(metodo, url, cuerpo)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(r.json(), {"detail": "No autenticado."})
        self.assertEqual(foto(self.ruta), self.antes)

    def test_usuario_recreado_con_otro_id_invalida_la_sesion_vieja(self):
        ejecutar("DELETE FROM usuarios", self.ruta)
        ejecutar(
            "INSERT INTO usuarios (id, username, password_hash, salt) VALUES (999, 'admin', 'h', 's')",
            self.ruta,
        )
        for nombre, metodo, url, cuerpo in ENDPOINTS:
            with self.subTest(endpoint=nombre):
                self.assertEqual(self.llamar(metodo, url, cuerpo).status_code, 401)
        self.assertEqual(foto(self.ruta), self.antes)

    def test_la_cookie_vieja_se_descarta_y_el_login_vuelve_a_funcionar(self):
        ejecutar("DELETE FROM usuarios WHERE username = 'admin'", self.ruta)
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        # Segunda llamada: la cookie ya no lleva datos de sesion; sigue siendo 401.
        self.assertEqual(self.client.post("/api/ordenes", json=ORDEN).status_code, 401)
        self.assertEqual(foto(self.ruta), self.antes)


if __name__ == "__main__":
    unittest.main()
