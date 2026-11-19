import unittest

from inventario.repositories.sqlite_repo import SqliteUsuarioRepository
from inventario.security import verificar_password
from inventario.services.inicializacion_service import ADMIN_USERNAME, sembrar_admin
from tests.helpers import conexion_inicializada


class SembrarAdminTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.repo = SqliteUsuarioRepository(self.conn)

    def test_con_password_de_entorno(self):
        self.assertIsNone(sembrar_admin(self.repo, "Clave-Entorno-1"))
        admin = self.repo.obtener_por_username(ADMIN_USERNAME)
        self.assertIsNotNone(admin)
        self.assertTrue(verificar_password("Clave-Entorno-1", admin.password_hash, admin.salt))
        self.assertFalse(verificar_password("otra", admin.password_hash, admin.salt))

    def test_sin_password_genera_y_devuelve_una(self):
        generada = sembrar_admin(self.repo, None)
        self.assertGreaterEqual(len(generada), 16)
        admin = self.repo.obtener_por_username(ADMIN_USERNAME)
        self.assertTrue(verificar_password(generada, admin.password_hash, admin.salt))

    def test_no_guarda_texto_plano(self):
        sembrar_admin(self.repo, "Clave-Entorno-1")
        fila = self.conn.execute("SELECT password_hash, salt FROM usuarios").fetchone()
        for valor in fila:
            self.assertNotIn("Clave-Entorno-1", valor)

    def test_idempotente(self):
        for primera, segunda in (("Clave-1", "Clave-2"), (None, None)):
            with self.subTest(primera=primera):
                self.conn.execute("DELETE FROM usuarios")
                sembrar_admin(self.repo, primera)
                antes = self.conn.execute("SELECT password_hash, salt FROM usuarios").fetchall()
                self.assertIsNone(sembrar_admin(self.repo, segunda))
                despues = self.conn.execute("SELECT password_hash, salt FROM usuarios").fetchall()
                self.assertEqual(len(despues), 1)
                self.assertEqual(tuple(antes[0]), tuple(despues[0]))
