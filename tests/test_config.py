import os
import unittest
from unittest import mock

from inventario import config


class RutaDbTest(unittest.TestCase):
    def test_usa_variable_de_entorno(self):
        with mock.patch.dict(os.environ, {"INVENTARIO_DB_PATH": "/tmp/otra.db"}):
            self.assertEqual(config.ruta_db(), "/tmp/otra.db")

    def test_default_en_cwd(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(config.ruta_db(), "inventario.db")


class PasswordAdminTest(unittest.TestCase):
    def test_devuelve_valor_definido(self):
        with mock.patch.dict(os.environ, {"ADMIN_DEFAULT_PASSWORD": "Clave-1"}):
            self.assertEqual(config.password_admin(), "Clave-1")

    def test_none_si_falta_vacia_o_espacios(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertIsNone(config.password_admin())
        for valor in ("", "   "):
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {"ADMIN_DEFAULT_PASSWORD": valor}):
                    self.assertIsNone(config.password_admin())


class SecretKeyTest(unittest.TestCase):
    def test_devuelve_valor_definido(self):
        with mock.patch.dict(os.environ, {"SECRET_KEY": "clave-de-test"}):
            self.assertEqual(config.secret_key(), "clave-de-test")

    def test_none_si_falta_vacia_o_espacios(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertIsNone(config.secret_key())
        for valor in ("", "   "):
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {"SECRET_KEY": valor}):
                    self.assertIsNone(config.secret_key())


class SessionHttpsOnlyTest(unittest.TestCase):
    def test_true_para_valores_afirmativos(self):
        for valor in ("1", "true", "TRUE"):
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {"SESSION_HTTPS_ONLY": valor}):
                    self.assertIs(config.session_https_only(), True)

    def test_false_si_falta_o_negativo(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertIs(config.session_https_only(), False)
        for valor in ("0", "false", ""):
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {"SESSION_HTTPS_ONLY": valor}):
                    self.assertIs(config.session_https_only(), False)
