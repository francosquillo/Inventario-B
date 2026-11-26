"""Normalizacion de categorias y CategoriaService (C-06e): SQLite real."""
import unittest
from datetime import datetime

from inventario.domain.entities import LineaModificacion
from inventario.domain.errors import (
    CategoriaDuplicada,
    CategoriaEnUso,
    CategoriaNoEncontrada,
    DatosInvalidos,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import SqliteCategoriaRepository, SqliteStockRepository
from inventario.services.categoria_service import CategoriaService
from inventario.services.normalizacion import clave_desde_texto, normalizar_categoria
from inventario.services.stock_service import StockService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
MSG_FORMATO = (
    "La clave de la categoría admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)


class NormalizarCategoriaTest(unittest.TestCase):
    def test_recorta_y_pasa_a_minusculas(self):
        self.assertEqual(normalizar_categoria("  Filtro "), "filtro")
        self.assertEqual(normalizar_categoria("ACEITE"), "aceite")

    def test_blanco_o_none_es_sin_categoria(self):
        for valor in (None, "", "   "):
            with self.subTest(valor=valor):
                self.assertIsNone(normalizar_categoria(valor))

    def test_no_texto_se_rechaza(self):
        for valor in (3, True, 1.5, ["a"]):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as cm:
                    normalizar_categoria(valor)
                self.assertEqual(str(cm.exception), "El campo categoria debe ser texto.")


class ClaveDesdeTextoTest(unittest.TestCase):
    def test_deriva(self):
        casos = {
            "  Tren delantero ": "tren-delantero",
            "Encendido / Bujías": "encendido-bujias",
            "Niño": "nino",
            "A  B--C": "a-b-c",
            "--x--": "x",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(clave_desde_texto(texto), esperado)

    def test_sin_letras_ni_numeros(self):
        with self.assertRaises(DatosInvalidos) as cm:
            clave_desde_texto("***")
        self.assertEqual(str(cm.exception), MSG_FORMATO)

    def test_recorta_a_30_sin_guion_final(self):
        self.assertEqual(clave_desde_texto("a" * 29 + " bbbb"), "a" * 29)
        self.assertEqual(clave_desde_texto("x" * 40), "x" * 30)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.servicio = CategoriaService(SqliteCategoriaRepository(self.conn))

    def claves(self):
        return [c.clave for c in self.servicio.listar()]


class ListarTest(Base):
    def test_listar(self):
        self.assertEqual(
            [(c.clave, c.nombre) for c in self.servicio.listar()],
            [("aceite", "Aceite"), ("filtro", "Filtro"), ("motor", "Motor")],
        )


class CrearTest(Base):
    def test_deriva_la_clave(self):
        c = self.servicio.crear("  Tren delantero ")
        self.assertEqual((c.clave, c.nombre), ("tren-delantero", "Tren delantero"))
        self.assertIn("tren-delantero", self.claves())

    def test_clave_indicada_se_normaliza(self):
        c = self.servicio.crear("Sistema de frenos", " Frenos ")
        self.assertEqual((c.clave, c.nombre), ("frenos", "Sistema de frenos"))

    def test_clave_blanca_se_deriva(self):
        self.assertEqual(self.servicio.crear("Bujías", "  ").clave, "bujias")

    def test_clave_invalida(self):
        for clave in ("fre nos!", "x" * 31, "mo_tor"):
            with self.subTest(clave=clave):
                with self.assertRaises(DatosInvalidos) as cm:
                    self.servicio.crear("Algo", clave)
                self.assertEqual(str(cm.exception), MSG_FORMATO)
        self.assertEqual(len(self.claves()), 3)

    def test_nombre_sin_letras_para_derivar(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.servicio.crear("***")
        self.assertEqual(str(cm.exception), MSG_FORMATO)

    def test_clave_repetida(self):
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.servicio.crear("Motor diésel", "MOTOR")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con clave 'motor'.")

    def test_nombre_repetido_sin_distinguir_mayusculas(self):
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.servicio.crear("ACEITE", "lubricante")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con nombre 'ACEITE'.")
        self.assertEqual(len(self.claves()), 3)

    def test_nombre_repetido_con_tildes_y_enie(self):
        self.servicio.crear("Ñandú")
        with self.assertRaises(CategoriaDuplicada):
            self.servicio.crear("ÑANDÚ", "otra-clave")

    def test_nombre_repetido_con_casefold_completo(self):
        self.servicio.crear("Straße", "s1")
        with self.assertRaises(CategoriaDuplicada):
            self.servicio.crear("STRASSE", "s2")

    def test_nombre_vacio_o_no_texto(self):
        for nombre in ("", "   ", None):
            with self.subTest(nombre=nombre):
                with self.assertRaises(DatosInvalidos) as cm:
                    self.servicio.crear(nombre)
                self.assertEqual(str(cm.exception), "El campo nombre es obligatorio.")

    def test_nombre_largo(self):
        self.servicio.crear("x" * 40)
        with self.assertRaises(DatosInvalidos) as cm:
            self.servicio.crear("y" * 41)
        self.assertEqual(str(cm.exception), "El nombre de la categoría admite hasta 40 caracteres.")


class RenombrarTest(Base):
    def test_renombra_y_normaliza_la_clave_de_la_ruta(self):
        insertar_producto(self.conn, "M-01", "Bujia", 1, categoria="motor")
        c = self.servicio.renombrar("MOTOR", "Motor y transmisión")
        self.assertEqual((c.clave, c.nombre), ("motor", "Motor y transmisión"))
        fila = self.conn.execute(
            "SELECT c.clave FROM productos p JOIN categorias c ON c.id = p.categoria_id"
        ).fetchone()
        self.assertEqual(fila[0], "motor")

    def test_mismo_nombre_y_solo_mayusculas(self):
        self.assertEqual(self.servicio.renombrar("aceite", "Aceite").nombre, "Aceite")
        self.assertEqual(self.servicio.renombrar("aceite", "ACEITE").nombre, "ACEITE")

    def test_nombre_de_otra(self):
        with self.assertRaises(CategoriaDuplicada) as cm:
            self.servicio.renombrar("filtro", "aceite")
        self.assertEqual(str(cm.exception), "Ya existe una categoría con nombre 'aceite'.")

    def test_inexistente(self):
        with self.assertRaises(CategoriaNoEncontrada):
            self.servicio.renombrar("frenos", "Frenos")

    def test_nombre_invalido(self):
        with self.assertRaises(DatosInvalidos):
            self.servicio.renombrar("motor", "  ")


class BorrarTest(Base):
    def test_normaliza_y_delega(self):
        self.assertEqual(self.servicio.borrar(" MOTOR ").clave, "motor")
        self.assertEqual([c.clave for c in self.servicio.listar()], ["aceite", "filtro"])

    def test_en_uso_lanza_con_el_mensaje_exacto(self):
        insertar_producto(self.conn, "F-1", "Filtro", 1, categoria="filtro")
        insertar_producto(self.conn, "F-2", "Filtro 2", 1, activo=0, categoria="filtro")
        with self.assertRaises(CategoriaEnUso) as cm:
            self.servicio.borrar("filtro")
        self.assertEqual(str(cm.exception), "La categoría 'filtro' está asignada a 2 producto(s).")

    def test_inexistente_y_clave_vacia(self):
        with self.assertRaises(CategoriaNoEncontrada):
            self.servicio.borrar("nada")
        for valor in ("", "  ", None, 3):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as cm:
                    self.servicio.borrar(valor)
                self.assertEqual(str(cm.exception), MSG_FORMATO)


class StockBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo M4", 5)
        insertar_producto(self.conn, "B-10", "Tuerca", 0)
        self.service = StockService(
            SqliteStockRepository(self.conn),
            SqliteCategoriaRepository(self.conn),
            ahora=lambda: FECHA_FIJA,
        )

    def productos(self):
        return self.conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]

    def categoria(self, codigo):
        fila = self.conn.execute(
            "SELECT c.clave FROM productos p LEFT JOIN categorias c ON c.id = p.categoria_id "
            "WHERE p.codigo = ?",
            (codigo,),
        ).fetchone()
        return fila[0]


class AltaCategoriaServiceTest(StockBase):
    def test_categoria_normalizada(self):
        r = self.service.dar_de_alta("N-01", "Bujia", 1, self.uid, categoria="Aceite")
        self.assertEqual(r.producto.categoria, "aceite")
        r = self.service.dar_de_alta("N-02", "Otra", 1, self.uid, categoria="  FILTRO ")
        self.assertEqual(r.producto.categoria, "filtro")

    def test_sin_categoria_o_en_blanco(self):
        for codigo, cat in (("N-01", None), ("N-02", "   ")):
            with self.subTest(cat=cat):
                r = self.service.dar_de_alta(codigo, "Bujia", 1, self.uid, categoria=cat)
                self.assertIsNone(r.producto.categoria)

    def test_categoria_inexistente_no_crea_nada(self):
        antes = self.productos()
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.dar_de_alta("X-01", "Bujia", 1, self.uid, categoria="Encendido")
        self.assertEqual(str(cm.exception), "La categoría 'encendido' no existe.")
        self.assertEqual(self.productos(), antes)
        self.assertEqual(movimientos(self.conn), [])

    def test_categoria_larga_se_recorta_en_el_mensaje(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.dar_de_alta("X-01", "Bujia", 1, self.uid, categoria="x" * 60)
        self.assertEqual(str(cm.exception), f"La categoría '{'x' * 30}…' no existe.")

    def test_categoria_no_texto(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.dar_de_alta("X-01", "Bujia", 1, self.uid, categoria=3)
        self.assertEqual(str(cm.exception), "El campo categoria debe ser texto.")


def linea(codigo, valor, categoria, cambia=True):
    return LineaModificacion(codigo, "fijar", valor, None, cambia, categoria)


class ModificacionCategoriaServiceTest(StockBase):
    def modificar(self, *lineas):
        return self.service.modificar(list(lineas), self.uid)

    def assertRechaza(self, mensaje, *lineas):
        with self.assertRaises(DatosInvalidos) as cm:
            self.modificar(*lineas)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertIsNone(self.categoria("A-01"))
        self.assertEqual(movimientos(self.conn), [])

    def test_asigna_normalizando(self):
        res = self.modificar(linea("A-01", 5, " Motor "))
        self.assertEqual(self.categoria("A-01"), "motor")
        self.assertEqual(res[0].categoria, "motor")

    def test_none_quita_y_sin_cambia_no_toca(self):
        self.modificar(linea("A-01", 5, "motor"))
        self.modificar(linea("A-01", 5, "filtro", cambia=False))
        self.assertEqual(self.categoria("A-01"), "motor")
        self.modificar(linea("A-01", 5, None))
        self.assertIsNone(self.categoria("A-01"))

    def test_inexistente_en_la_linea_2(self):
        self.assertRechaza(
            "Línea 2: La categoría 'frenos' no existe.",
            linea("A-01", 7, "motor"),
            linea("B-10", 1, "frenos"),
        )

    def test_no_texto_en_la_linea_1(self):
        self.assertRechaza("Línea 1: El campo categoria debe ser texto.", linea("A-01", 7, 3))

    def test_gana_la_primera_linea_invalida_antes_que_los_repetidos(self):
        self.assertRechaza(
            "Línea 3: La categoría 'frenos' no existe.",
            linea("A-01", 1, None, cambia=False),
            linea("A-01", 2, None, cambia=False),
            linea("B-10", 1, "frenos"),
        )


if __name__ == "__main__":
    unittest.main()
