import unittest
from unittest import mock

from inventario.domain.entities import UsuarioAutenticado
from inventario.domain.errors import MENSAJE_CREDENCIALES_INVALIDAS, CredencialesInvalidas
from inventario.repositories.sqlite_repo import SqliteUsuarioRepository
from inventario.services import auth_service
from inventario.services.auth_service import AuthService
from inventario.services.inicializacion_service import sembrar_admin
from tests.helpers import conexion_inicializada

PASSWORD = "Clave-Test-1"


class LoginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = conexion_inicializada()
        cls.repo = SqliteUsuarioRepository(cls.conn)
        sembrar_admin(cls.repo, PASSWORD)
        cls.servicio = AuthService(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_login_valido(self):
        usuario = self.servicio.login("admin", PASSWORD)
        self.assertIsInstance(usuario, UsuarioAutenticado)
        self.assertEqual(usuario.username, "admin")
        self.assertEqual(usuario.id, self.repo.obtener_por_username("admin").id)
        self.assertFalse(hasattr(usuario, "password_hash"))

    def test_espacios_alrededor_del_usuario(self):
        self.assertEqual(self.servicio.login("  admin  ", PASSWORD).username, "admin")

    def test_credenciales_invalidas_mismo_mensaje(self):
        casos = [
            ("admin", "incorrecta"),
            ("fantasma", PASSWORD),
            ("", PASSWORD),
            ("   ", PASSWORD),
            ("admin", ""),
        ]
        for usuario, password in casos:
            with self.subTest(usuario=usuario, password=password):
                with self.assertRaises(CredencialesInvalidas) as ctx:
                    self.servicio.login(usuario, password)
                self.assertEqual(str(ctx.exception), MENSAJE_CREDENCIALES_INVALIDAS)

    def test_usuario_inexistente_igual_deriva_pbkdf2(self):
        with mock.patch.object(
            auth_service, "verificar_password", wraps=auth_service.verificar_password
        ) as espia:
            with self.assertRaises(CredencialesInvalidas):
                self.servicio.login("fantasma", PASSWORD)
        espia.assert_called_once()
