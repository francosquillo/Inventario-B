"""Categorias en los repositorios SQLite (C-06e, grupo 3): SQLite real en memoria."""
import unittest
from datetime import date, datetime

from inventario.domain.entities import Categoria, LineaModificacion, Producto
from inventario.domain.errors import (
    CategoriaDuplicada,
    CategoriaEnUso,
    CategoriaNoEncontrada,
    ProductoDuplicado,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteCategoriaRepository,
    SqliteOrdenRepository,
    SqliteProductoRepository,
    SqliteStockRepository,
)
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        self.categorias = SqliteCategoriaRepository(self.conn)
        self.stock = SqliteStockRepository(self.conn)
        self.productos = SqliteProductoRepository(self.conn)

    def categoria_de(self, codigo):
        fila = self.conn.execute(
            "SELECT c.clave FROM productos p LEFT JOIN categorias c ON c.id = p.categoria_id "
            "WHERE p.codigo = ?",
            (codigo,),
        ).fetchone()
        return fila["clave"]

    def filas_categorias(self):
        return [tuple(f) for f in self.conn.execute("SELECT clave, nombre FROM categorias ORDER BY id")]


class ListarCategoriasTest(Base):
    def test_listar_ordenado_por_nombre(self):
        self.assertEqual(
            self.categorias.listar(),
            [Categoria("aceite", "Aceite"), Categoria("filtro", "Filtro"), Categoria("motor", "Motor")],
        )

    def test_listar_sigue_el_nombre_no_la_clave(self):
        self.conn.execute("UPDATE categorias SET nombre = 'Zeta' WHERE clave = 'aceite'")
        self.conn.execute("UPDATE categorias SET nombre = 'Alfa' WHERE clave = 'motor'")
        self.conn.commit()
        self.assertEqual([c.clave for c in self.categorias.listar()], ["motor", "filtro", "aceite"])


class ProductoConCategoriaTest(Base):
    def test_listar_activos_devuelve_clave_o_none(self):
        insertar_producto(self.conn, "A-01", "Aceite 10W40", 3, categoria="aceite")
        insertar_producto(self.conn, "B-02", "Tuerca", 2)
        por_codigo = {p.codigo: p for p in self.productos.listar_activos()}
        self.assertEqual(por_codigo["A-01"].categoria, "aceite")
        self.assertIsNone(por_codigo["B-02"].categoria)

    def test_listar_inactivos_devuelve_clave_o_none(self):
        insertar_producto(self.conn, "A-01", "Aceite", 3, activo=0, categoria="aceite")
        insertar_producto(self.conn, "B-02", "Tuerca", 2, activo=0)
        self.assertEqual([p.categoria for p in self.productos.listar_inactivos()], ["aceite", None])

    def test_producto_sin_categoria_por_defecto(self):
        self.assertIsNone(Producto(1, "A", "n", 0, True).categoria)

    def test_egreso_baja_ingreso_devuelven_la_categoria_sin_cambiarla(self):
        insertar_producto(self.conn, "F-01", "Filtro", 5, categoria="filtro")
        self.assertEqual(self.stock.registrar_egreso("F-01", 1, self.uid, FECHA).categoria, "filtro")
        self.assertEqual(self.productos.dar_de_baja("F-01").categoria, "filtro")
        r = self.stock.registrar_ingreso("F-01", 1, None, self.uid, FECHA)
        self.assertEqual(r.producto.categoria, "filtro")
        self.assertEqual(self.categoria_de("F-01"), "filtro")


class AltaConCategoriaTest(Base):
    def alta(self, codigo, categoria, nombre="Nombre", stock=1):
        return self.stock.dar_de_alta(codigo, nombre, stock, self.uid, FECHA, categoria=categoria)

    def test_crea_con_categoria(self):
        r = self.alta("N-01", "aceite")
        self.assertEqual(r.producto.categoria, "aceite")
        self.assertEqual(self.categoria_de("N-01"), "aceite")

    def test_sin_categoria(self):
        r = self.alta("N-02", None)
        self.assertIsNone(r.producto.categoria)
        self.assertIsNone(self.categoria_de("N-02"))

    def test_reactivacion_reemplaza_la_categoria(self):
        insertar_producto(self.conn, "R-01", "Viejo", 2, activo=0, categoria="motor")
        r = self.alta("R-01", "filtro", stock=2)
        self.assertTrue(r.reactivado)
        self.assertEqual(self.categoria_de("R-01"), "filtro")

    def test_reactivacion_sin_categoria_la_quita(self):
        insertar_producto(self.conn, "R-02", "Viejo", 2, activo=0, categoria="motor")
        self.alta("R-02", None, stock=2)
        self.assertIsNone(self.categoria_de("R-02"))

    def test_duplicado_activo_con_cualquier_categoria(self):
        insertar_producto(self.conn, "D-01", "Dup", 1, categoria="motor")
        for cat in (None, "motor", "aceite"):
            with self.subTest(cat=cat):
                with self.assertRaises(ProductoDuplicado):
                    self.alta("D-01", cat)
        self.assertEqual(self.categoria_de("D-01"), "motor")


def fijar(codigo, valor, nombre=None, **kw):
    return LineaModificacion(codigo, "fijar", valor, nombre, **kw)


class ModificarCategoriaTest(Base):
    def modificar(self, *lineas):
        return self.stock.modificar(list(lineas), self.uid, FECHA)

    def test_asigna_categoria(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        res = self.modificar(fijar("A-01", 5, cambia_categoria=True, categoria="motor"))
        self.assertEqual(self.categoria_de("A-01"), "motor")
        self.assertEqual((res[0].categoria, res[0].categoria_anterior), ("motor", None))

    def test_quita_categoria(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5, categoria="motor")
        res = self.modificar(fijar("A-01", 5, cambia_categoria=True, categoria=None))
        self.assertIsNone(self.categoria_de("A-01"))
        self.assertEqual((res[0].categoria, res[0].categoria_anterior), (None, "motor"))

    def test_sin_cambia_categoria_no_toca(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5, categoria="motor")
        res = self.modificar(fijar("A-01", 7, categoria="filtro"))
        self.assertEqual(self.categoria_de("A-01"), "motor")
        self.assertEqual((res[0].categoria, res[0].categoria_anterior), ("motor", "motor"))

    def test_solo_categoria_sobre_activo_no_registra_movimiento(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.modificar(fijar("A-01", 5, cambia_categoria=True, categoria="aceite"))
        self.assertEqual(movimientos(self.conn), [])

    def test_solo_categoria_sobre_dado_de_baja_no_lo_reactiva(self):
        insertar_producto(self.conn, "B-01", "Viejo", 3, activo=0)
        res = self.modificar(fijar("B-01", 3, cambia_categoria=True, categoria="filtro"))
        self.assertFalse(res[0].reactivado)
        fila = self.conn.execute("SELECT activo FROM productos WHERE codigo='B-01'").fetchone()
        self.assertEqual(fila["activo"], 0)
        self.assertEqual(self.categoria_de("B-01"), "filtro")

    def test_misma_categoria_no_cambia_nada(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5, categoria="motor")
        self.conn.commit()
        antes = self.conn.total_changes
        res = self.modificar(fijar("A-01", 5, cambia_categoria=True, categoria="motor"))
        self.assertEqual(self.conn.total_changes, antes)
        self.assertEqual(res[0].categoria_anterior, "motor")

    def test_categoria_junto_con_stock_y_nombre(self):
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        res = self.modificar(fijar("A-01", 9, "Tornillo largo", cambia_categoria=True, categoria="motor"))
        self.assertEqual((res[0].stock, res[0].nombre, res[0].categoria), (9, "Tornillo largo", "motor"))
        self.assertEqual(len(movimientos(self.conn)), 1)


class CrearRenombrarCategoriaTest(Base):
    def test_crear_devuelve_la_categoria(self):
        self.assertEqual(self.categorias.crear("frenos", "Frenos"), Categoria("frenos", "Frenos"))
        self.assertIn(("frenos", "Frenos"), self.filas_categorias())

    def test_crear_clave_repetida(self):
        antes = self.filas_categorias()
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.categorias.crear("motor", "Motor diesel")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con clave 'motor'.")
        self.assertEqual(self.filas_categorias(), antes)

    def test_crear_nombre_repetido_sin_distinguir_mayusculas(self):
        antes = self.filas_categorias()
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.categorias.crear("lubricante", "ACEITE")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con nombre 'ACEITE'.")
        self.assertEqual(self.filas_categorias(), antes)

    def test_obtener(self):
        self.assertEqual(self.categorias.obtener("motor"), Categoria("motor", "Motor"))
        self.assertIsNone(self.categorias.obtener("frenos"))

    def test_renombrar_cambia_solo_el_nombre_y_conserva_productos(self):
        insertar_producto(self.conn, "M-01", "Bujia", 1, categoria="motor")
        r = self.categorias.renombrar("motor", "Motor y transmisión")
        self.assertEqual(r, Categoria("motor", "Motor y transmisión"))
        self.assertEqual(self.categoria_de("M-01"), "motor")

    def test_renombrar_solo_mayusculas(self):
        self.assertEqual(self.categorias.renombrar("aceite", "ACEITE").nombre, "ACEITE")

    def test_renombrar_inexistente(self):
        with self.assertRaises(CategoriaNoEncontrada) as cm:
            self.categorias.renombrar("frenos", "Frenos")
        self.assertEqual(str(cm.exception), "No existe una categoría con clave 'frenos'.")

    def test_renombrar_nombre_de_otra(self):
        antes = self.filas_categorias()
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.categorias.renombrar("filtro", "aceite")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con nombre 'aceite'.")
        self.assertEqual(self.filas_categorias(), antes)


class ReporteConCategoriaTest(Base):
    def test_productos_en_ordenes_trae_la_categoria_actual(self):
        insertar_producto(self.conn, "A-01", "Aceite", 100, categoria="aceite")
        insertar_producto(self.conn, "B-02", "Tuerca", 100)
        insertar_producto(self.conn, "C-03", "Viejo", 100, categoria="filtro")
        ordenes = SqliteOrdenRepository(self.conn)
        ordenes.crear("OT-1", date(2026, 11, 5), [("A-01", 3), ("B-02", 2), ("C-03", 1)], self.uid, FECHA)
        self.conn.execute("UPDATE productos SET activo = 0 WHERE codigo = 'C-03'")
        self.conn.commit()
        filas = ordenes.productos_en_ordenes(date(2026, 11, 1), date(2026, 11, 30), None)
        self.assertEqual(
            [(f.codigo, f.categoria, f.cantidad, f.activo) for f in filas],
            [("A-01", "aceite", 3, True), ("B-02", None, 2, True), ("C-03", "filtro", 1, False)],
        )

    def test_productos_usados_sin_cambios(self):
        insertar_producto(self.conn, "A-01", "Aceite", 100, categoria="aceite")
        ordenes = SqliteOrdenRepository(self.conn)
        ordenes.crear("OT-1", date(2026, 11, 5), [("A-01", 1)], self.uid, FECHA)
        self.assertEqual([(p.codigo, p.nombre, p.activo) for p in ordenes.productos_usados()],
                         [("A-01", "Aceite", True)])


class BorrarCategoriaTest(Base):
    def test_sin_productos_la_borra_y_devuelve_la_categoria(self):
        self.assertEqual(self.categorias.borrar("motor"), Categoria("motor", "Motor"))
        self.assertIsNone(self.categorias.obtener("motor"))
        self.assertEqual(len(self.categorias.listar()), 2)

    def test_usada_por_activo_y_dado_de_baja_lanza_en_uso_con_la_cantidad_sin_cambios(self):
        insertar_producto(self.conn, "F-01", "Filtro aire", 3, categoria="filtro")
        insertar_producto(self.conn, "F-02", "Filtro viejo", 0, activo=0, categoria="filtro")
        antes = self.filas_categorias()
        with self.assertRaises(CategoriaEnUso) as cm:
            self.categorias.borrar("filtro")
        self.assertEqual((cm.exception.clave, cm.exception.cantidad), ("filtro", 2))
        self.assertEqual(self.filas_categorias(), antes)
        self.assertEqual(self.categoria_de("F-01"), "filtro")
        self.assertFalse(self.conn.in_transaction)

    def test_cuenta_solo_los_productos_de_esa_categoria(self):
        insertar_producto(self.conn, "F-01", "Filtro aire", 3, categoria="filtro")
        self.assertEqual(self.categorias.borrar("motor").clave, "motor")

    def test_inexistente(self):
        with self.assertRaises(CategoriaNoEncontrada):
            self.categorias.borrar("nada")
        self.assertFalse(self.conn.in_transaction)

    def test_tras_reasignar_el_producto_se_puede_borrar(self):
        insertar_producto(self.conn, "F-01", "Filtro aire", 3, categoria="filtro")
        self.conn.execute("UPDATE productos SET categoria_id = NULL")
        self.conn.commit()
        self.assertEqual(self.categorias.borrar("filtro").clave, "filtro")


if __name__ == "__main__":
    unittest.main()
