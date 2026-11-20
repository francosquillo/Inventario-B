import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from inventario.repositories.sqlite_repo import conectar
from tests.helpers import PASSWORD_ADMIN_TEST, app_de_test

TABLAS = {"usuarios", "productos", "ordenes", "orden_items", "movimientos"}


def tablas(ruta):
    conn = conectar(ruta)
    try:
        filas = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {f["name"] for f in filas}
    finally:
        conn.close()


def usuarios(ruta):
    conn = conectar(ruta)
    try:
        return conn.execute("SELECT username, password_hash, salt FROM usuarios").fetchall()
    finally:
        conn.close()


class LifespanTest(unittest.TestCase):
    def test_arranque_crea_esquema_y_admin(self):
        app, ruta = app_de_test(self.addCleanup)
        with TestClient(app):
            pass
        self.assertTrue(TABLAS <= tablas(ruta))
        self.assertEqual([u["username"] for u in usuarios(ruta)], ["admin"])


class SecretKeyObligatoriaTest(unittest.TestCase):
    def test_sin_secret_key_en_entorno_falla(self):
        from inventario.api.app import crear_app

        with mock.patch.dict(os.environ, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                crear_app(ruta_db=":memory:")
        self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_secret_key_vacia_falla(self):
        from inventario.api.app import crear_app

        for valor in ("", "   "):
            with self.subTest(valor=valor):
                with self.assertRaises(RuntimeError) as ctx:
                    crear_app(ruta_db=":memory:", secret_key=valor)
                self.assertIn("SECRET_KEY", str(ctx.exception))


class LogPasswordGeneradaTest(unittest.TestCase):
    def test_password_generada_se_loguea_una_vez_y_sirve_para_login(self):
        from inventario.services.auth_service import AuthService
        from inventario.repositories.sqlite_repo import SqliteUsuarioRepository

        app, ruta = app_de_test(self.addCleanup, password_admin=None)
        with self.assertLogs("inventario", "WARNING") as cm:
            with TestClient(app):
                pass
        mensaje = cm.output[0]
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        servicio = AuthService(SqliteUsuarioRepository(conn))
        candidatas = [t.strip("'\"():,") for t in mensaje.split()]
        generada = [t for t in candidatas if len(t) >= 16 and _login_ok(servicio, t)]
        self.assertEqual(len(generada), 1)

        hash_antes = usuarios(ruta)[0]["password_hash"]
        with self.assertNoLogs("inventario", "WARNING"):
            with TestClient(app):
                pass
        self.assertEqual(usuarios(ruta)[0]["password_hash"], hash_antes)

    def test_password_de_entorno_no_se_loguea(self):
        app, _ = app_de_test(self.addCleanup, password_admin="Clave-Test-1")
        with self.assertNoLogs("inventario", "WARNING"):
            with TestClient(app):
                pass


def _login_ok(servicio, password):
    from inventario.domain.errors import CredencialesInvalidas

    try:
        servicio.login("admin", password)
        return True
    except CredencialesInvalidas:
        return False


class IdempotenciaTest(unittest.TestCase):
    def test_reinicio_conserva_datos_y_un_solo_admin(self):
        from tests.helpers import insertar_producto

        app, ruta = app_de_test(self.addCleanup)
        with TestClient(app):
            pass
        conn = conectar(ruta)
        insertar_producto(conn, "P-001", "Tornillo", 7)
        conn.commit()
        conn.close()
        with TestClient(app):
            pass
        conn = conectar(ruta)
        self.addCleanup(conn.close)
        fila = conn.execute("SELECT codigo, stock FROM productos").fetchall()
        self.assertEqual([(f["codigo"], f["stock"]) for f in fila], [("P-001", 7)])
        self.assertEqual(len(usuarios(ruta)), 1)


class CarreraDelSeedTest(unittest.TestCase):
    def test_integrity_error_por_admin_ya_creado_no_se_propaga(self):
        from inventario.api.app import inicializar_base
        from inventario.repositories.sqlite_repo import SqliteUsuarioRepository

        class RepoQueNoVeAlAdmin(SqliteUsuarioRepository):
            def obtener_por_username(self, username):
                return None

        app, ruta = app_de_test(self.addCleanup)
        with TestClient(app):
            pass  # el admin ya existe en la base real
        resultado = inicializar_base(ruta, None, repo_cls=RepoQueNoVeAlAdmin)
        self.assertIsNone(resultado)
        self.assertEqual(len(usuarios(ruta)), 1)

    def test_integrity_error_se_loguea_como_warning(self):
        from inventario.api.app import inicializar_base
        from inventario.repositories.sqlite_repo import SqliteUsuarioRepository

        class RepoQueNoVeAlAdmin(SqliteUsuarioRepository):
            def obtener_por_username(self, username):
                return None

        app, ruta = app_de_test(self.addCleanup)
        with TestClient(app):
            pass
        with self.assertLogs("inventario", "WARNING") as cm:
            inicializar_base(ruta, "Clave-Test-1", repo_cls=RepoQueNoVeAlAdmin)
        self.assertEqual(len(cm.records), 1)
        self.assertNotIn("Clave-Test-1", cm.output[0])
        self.assertIn("IntegrityError", cm.output[0])

    def test_sin_conflicto_no_loguea(self):
        from inventario.api.app import inicializar_base

        _, ruta = app_de_test(self.addCleanup)
        with self.assertNoLogs("inventario", "WARNING"):
            inicializar_base(ruta, "Clave-Test-1")


class DocsTest(unittest.TestCase):
    def test_docs_y_openapi_exponen_los_endpoints(self):
        from tests.helpers import cliente_de_test

        client, _ = cliente_de_test(self.addCleanup)
        self.assertEqual(client.get("/docs").status_code, 200)
        paths = client.get("/openapi.json").json()["paths"]
        for ruta in (
            "/api/login", "/api/logout", "/api/me", "/api/inventario",
            "/api/stock/ingreso", "/api/stock/egreso", "/api/movimientos",
            "/api/ordenes", "/api/ordenes/{numero}", "/api/productos/{codigo}",
        ):
            with self.subTest(ruta=ruta):
                self.assertIn(ruta, paths)


class OpenApiErrorOutTest(unittest.TestCase):
    def test_422_de_login_referencia_error_out(self):
        from tests.helpers import cliente_de_test

        client, _ = cliente_de_test(self.addCleanup)
        spec = client.get("/openapi.json").json()
        ref = spec["paths"]["/api/login"]["post"]["responses"]["422"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        self.assertTrue(ref.endswith("/ErrorOut"))
        self.assertIn("ErrorOut", spec["components"]["schemas"])


class RutaDbPorEntornoTest(unittest.TestCase):
    def _app_en_directorio_temporal(self, entorno):
        import secrets
        import tempfile

        from inventario.api.app import crear_app

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        previo = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, previo)
        base = {"SECRET_KEY": secrets.token_urlsafe(32), "ADMIN_DEFAULT_PASSWORD": "Clave-Test-1"}
        patcher = mock.patch.dict(os.environ, {**base, **entorno}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        return tmp.name, crear_app()

    def test_usa_inventario_db_path_del_entorno(self):
        import tempfile

        destino = tempfile.TemporaryDirectory()
        self.addCleanup(destino.cleanup)
        ruta = os.path.join(destino.name, "entorno.db")
        cwd, app = self._app_en_directorio_temporal({"INVENTARIO_DB_PATH": ruta})
        with TestClient(app):
            pass
        self.assertTrue(os.path.exists(ruta))
        self.assertTrue(TABLAS <= tablas(ruta))
        self.assertFalse(os.path.exists(os.path.join(cwd, "inventario.db")))

    def test_sin_variable_usa_inventario_db_en_el_directorio_actual(self):
        cwd, app = self._app_en_directorio_temporal({})
        with TestClient(app):
            pass
        por_defecto = os.path.join(cwd, "inventario.db")
        self.assertTrue(os.path.exists(por_defecto))
        self.assertTrue(TABLAS <= tablas(por_defecto))
