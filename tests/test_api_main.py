import importlib
import os
import secrets
import sys
import tempfile
import unittest
from unittest import mock

from fastapi import FastAPI


def _descartar(*nombres):
    for n in nombres:
        sys.modules.pop(n, None)


class MainTest(unittest.TestCase):
    def test_main_expone_app_con_entorno_definido(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        entorno = {
            "SECRET_KEY": secrets.token_urlsafe(32),
            "INVENTARIO_DB_PATH": os.path.join(tmp.name, "t.db"),
        }
        self.addCleanup(_descartar, "inventario.api.main")
        with mock.patch.dict(os.environ, entorno):
            _descartar("inventario.api.main")
            with mock.patch("dotenv.load_dotenv"):
                modulo = importlib.import_module("inventario.api.main")
        self.assertIsInstance(modulo.app, FastAPI)

    def test_importar_app_sin_secret_key_no_falla_ni_crea_app(self):
        _descartar("inventario.api.app")
        with mock.patch.dict(os.environ, clear=True):
            modulo = importlib.import_module("inventario.api.app")
        self.assertFalse(hasattr(modulo, "app"))
