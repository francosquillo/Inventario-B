import sqlite3
import unittest

from inventario.domain.entities import Producto, Usuario
from inventario.repositories.sqlite_repo import (
    SqliteProductoRepository,
    SqliteUsuarioRepository,
)
from tests.helpers import conexion_inicializada, insertar_producto


class UsuarioRepoTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.repo = SqliteUsuarioRepository(self.conn)

    def test_crear_y_obtener(self):
        creado = self.repo.crear("admin", "hh", "ss")
        obtenido = self.repo.obtener_por_username("admin")
        self.assertIsInstance(obtenido, Usuario)
        self.assertEqual(obtenido, creado)
        self.assertEqual((obtenido.username, obtenido.password_hash, obtenido.salt), ("admin", "hh", "ss"))

    def test_inexistente_devuelve_none(self):
        self.assertIsNone(self.repo.obtener_por_username("nadie"))

    def test_obtener_por_id(self):
        creado = self.repo.crear("admin", "hh", "ss")
        otro = self.repo.crear("otro", "h2", "s2")
        self.assertEqual(self.repo.obtener_por_id(creado.id), creado)
        self.assertEqual(self.repo.obtener_por_id(otro.id).username, "otro")

    def test_obtener_por_id_inexistente_devuelve_none(self):
        creado = self.repo.crear("admin", "hh", "ss")
        self.assertIsNone(self.repo.obtener_por_id(creado.id + 100))
        self.assertIsNone(self.repo.obtener_por_id(0))

    def test_username_con_comilla(self):
        self.repo.crear("o'brien", "h", "s")
        self.assertEqual(self.repo.obtener_por_username("o'brien").username, "o'brien")

    def test_inyeccion_no_funciona(self):
        self.repo.crear("admin", "h", "s")
        self.assertIsNone(self.repo.obtener_por_username("x' OR '1'='1"))

    def test_username_duplicado_propaga_integrity_error(self):
        self.repo.crear("admin", "h", "s")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.crear("admin", "h2", "s2")


class ProductoRepoTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.repo = SqliteProductoRepository(self.conn)

    def test_lista_solo_activos_como_entidades(self):
        insertar_producto(self.conn, "P-001", "Uno", 3, 1)
        insertar_producto(self.conn, "P-002", "Dos", 0, 0)
        res = self.repo.listar_activos()
        self.assertEqual(len(res), 1)
        p = res[0]
        self.assertIsInstance(p, Producto)
        self.assertEqual((p.codigo, p.nombre, p.stock), ("P-001", "Uno", 3))
        self.assertIs(p.activo, True)

    def test_base_vacia(self):
        self.assertEqual(self.repo.listar_activos(), [])

    def test_todos_inactivos(self):
        insertar_producto(self.conn, "P-001", "Uno", 3, 0)
        insertar_producto(self.conn, "P-002", "Dos", 1, 0)
        self.assertEqual(self.repo.listar_activos(), [])
