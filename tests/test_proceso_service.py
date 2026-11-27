"""ProcesoService y procesos en el alta de ordenes (C-06f, grupo 4): SQLite real."""
import unittest
from datetime import datetime

from inventario.domain.entities import Proceso, ProcesoOrden
from inventario.domain.errors import DatosInvalidos, ProcesoDuplicado, ProcesoNoEncontrado
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteOrdenRepository,
    SqliteProcesoRepository,
    SqliteServicioGeneralRepository,
)
from inventario.services.orden_service import OrdenService
from inventario.services.proceso_service import ProcesoService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario

FECHA_FIJA = datetime(2026, 11, 24, 10, 0, tzinfo=ZONA_AR)
MSG_CLAVE = (
    "La clave del proceso admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.service = ProcesoService(SqliteProcesoRepository(self.conn))

    def assertInvalido(self, mensaje, funcion, *args):
        with self.assertRaises(DatosInvalidos) as cm:
            funcion(*args)
        self.assertEqual(str(cm.exception), mensaje)


class CrearTest(Base):
    def test_deriva_la_clave_del_nombre_recortado(self):
        self.assertEqual(
            self.service.crear("  Pintura del casco "), Proceso("pintura-del-casco", "Pintura del casco")
        )
        self.assertIn(Proceso("pintura-del-casco", "Pintura del casco"), self.service.listar())

    def test_deriva_sin_tildes_ni_enie(self):
        self.assertEqual(self.service.crear("Reparación Ñandú").clave, "reparacion-nandu")

    def test_clave_indicada_se_normaliza(self):
        self.assertEqual(self.service.crear("Pintura", " PINTURA-2 ").clave, "pintura-2")

    def test_clave_blanca_se_deriva(self):
        self.assertEqual(self.service.crear("Pintura", "  ").clave, "pintura")

    def test_clave_invalida(self):
        for clave in ("con espacio", "a_b", "-a", "a--b", "x" * 31):
            with self.subTest(clave=clave):
                self.assertInvalido(MSG_CLAVE, self.service.crear, "Pintura", clave)

    def test_clave_no_texto(self):
        self.assertInvalido("El campo clave debe ser texto.", self.service.crear, "Pintura", 3)

    def test_nombre_sin_letras_para_derivar(self):
        self.assertInvalido(MSG_CLAVE, self.service.crear, "***")

    def test_clave_repetida(self):
        with self.assertRaises(ProcesoDuplicado) as cm:
            self.service.crear("Otro", "limpieza")
        self.assertEqual((cm.exception.campo, cm.exception.valor), ("clave", "limpieza"))

    def test_nombre_repetido_sin_distinguir_mayusculas_ni_tildes(self):
        self.service.crear("Reparación")
        for nombre in ("LIMPIEZA", "limpieza", "REPARACIÓN"):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ProcesoDuplicado) as cm:
                    self.service.crear(nombre, "otra-clave")
                self.assertEqual(cm.exception.campo, "nombre")

    def test_nombre_vacio_o_no_texto(self):
        for nombre in (None, "", "   ", 3):
            with self.subTest(nombre=nombre):
                self.assertInvalido("El campo nombre es obligatorio.", self.service.crear, nombre)

    def test_nombre_de_60_pasa_y_de_61_no(self):
        self.assertEqual(self.service.crear("x" * 60).nombre, "x" * 60)
        self.assertInvalido(
            "El nombre del proceso admite hasta 60 caracteres.", self.service.crear, "y" * 61
        )


class RenombrarTest(Base):
    def test_renombra_y_normaliza_la_clave_de_la_ruta(self):
        self.assertEqual(
            self.service.renombrar(" LIMPIEZA ", " Limpieza total "), Proceso("limpieza", "Limpieza total")
        )

    def test_mismo_nombre_no_es_error(self):
        self.assertEqual(self.service.renombrar("limpieza", "limpieza").nombre, "limpieza")

    def test_nombre_de_otro(self):
        with self.assertRaises(ProcesoDuplicado):
            self.service.renombrar("limpieza", "CAMBIO MOTOR")

    def test_inexistente(self):
        with self.assertRaises(ProcesoNoEncontrado):
            self.service.renombrar("nada", "X")

    def test_nombre_invalido_y_clave_vacia(self):
        self.assertInvalido("El campo nombre es obligatorio.", self.service.renombrar, "limpieza", " ")
        self.assertInvalido(MSG_CLAVE, self.service.renombrar, " ", "X")


class BorrarTest(Base):
    def test_normaliza_y_borra(self):
        self.assertEqual(self.service.borrar(" Limpieza "), Proceso("limpieza", "Limpieza"))
        self.assertEqual(len(self.service.listar()), 2)

    def test_inexistente_y_clave_vacia(self):
        with self.assertRaises(ProcesoNoEncontrado):
            self.service.borrar("nada")
        self.assertInvalido(MSG_CLAVE, self.service.borrar, "  ")


class OrdenBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.procesos = ProcesoService(SqliteProcesoRepository(self.conn))
        self.service = OrdenService(
            SqliteOrdenRepository(self.conn),
            SqliteProcesoRepository(self.conn),
            SqliteServicioGeneralRepository(self.conn),
            ahora=lambda: FECHA_FIJA,
        )

    def crear(self, numero="OT-1", componentes=(("A-01", 1),), **kwargs):
        return self.service.crear(numero, "2026-11-20", componentes, self.uid, **kwargs)

    def stock(self):
        return self.conn.execute("SELECT stock FROM productos WHERE codigo='A-01'").fetchone()[0]

    def assertInvalido(self, mensaje, **kwargs):
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear(**kwargs)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertEqual(self.stock(), 5)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0], 0)


class AltaConProcesosCatalogoTest(OrdenBase):
    def test_claves_se_resuelven_a_nombres_sin_repetir(self):
        orden = self.crear(procesos=["Limpieza", "cambio-filtro", "limpieza"])
        self.assertEqual(
            orden.procesos, (ProcesoOrden("Limpieza", False), ProcesoOrden("Cambio filtro", False))
        )

    def test_sin_procesos_o_none(self):
        self.assertEqual(self.crear("OT-1").procesos, ())
        self.assertEqual(self.crear("OT-2", procesos=None, procesos_personalizados=None).procesos, ())
        self.assertEqual(self.crear("OT-3", procesos=[], procesos_personalizados=[]).procesos, ())

    def test_clave_inexistente(self):
        self.assertInvalido("El proceso 'pintura' no existe.", procesos=["limpieza", "pintura"])

    def test_clave_inexistente_larga_se_recorta(self):
        self.assertInvalido(f"El proceso '{'x' * 30}…' no existe.", procesos=["x" * 40])

    def test_tipo_invalido(self):
        mensaje = "El campo procesos debe ser una lista de textos."
        for valor in ("limpieza", [3], {"a": 1}, [None], 5):
            with self.subTest(valor=valor):
                self.assertInvalido(mensaje, procesos=valor)

    def test_usa_el_nombre_actual_del_catalogo(self):
        self.procesos.renombrar("limpieza", "Limpieza total")
        self.assertEqual(self.crear(procesos=["limpieza"]).procesos[0].nombre, "Limpieza total")


class AltaConPersonalizadosTest(OrdenBase):
    def test_recortados_y_en_orden_tras_los_del_catalogo(self):
        orden = self.crear(
            procesos=["limpieza"], procesos_personalizados=["  Pulido fino ", "Pintura"]
        )
        self.assertEqual(
            orden.procesos,
            (
                ProcesoOrden("Limpieza", False),
                ProcesoOrden("Pulido fino", True),
                ProcesoOrden("Pintura", True),
            ),
        )

    def test_espacios_internos_se_conservan(self):
        self.assertEqual(
            self.crear(procesos_personalizados=["a  b"]).procesos, (ProcesoOrden("a  b", True),)
        )

    def test_vacio(self):
        self.assertInvalido(
            "Proceso personalizado 2: El nombre es obligatorio.",
            procesos_personalizados=["Pulido", "   "],
        )

    def test_largo(self):
        self.assertInvalido(
            "Proceso personalizado 1: El nombre del proceso admite hasta 60 caracteres.",
            procesos_personalizados=["x" * 61],
        )
        self.assertEqual(len(self.crear(procesos_personalizados=["x" * 60]).procesos), 1)

    def test_tope_de_diez(self):
        self.assertInvalido(
            "La orden admite hasta 10 procesos personalizados.",
            procesos_personalizados=[f"P{i}" for i in range(11)],
        )
        orden = self.crear(procesos_personalizados=[f"P{i}" for i in range(10)])
        self.assertEqual(len(orden.procesos), 10)

    def test_igual_al_catalogo_aunque_no_este_marcado(self):
        for texto in ("limpieza", "LIMPIEZA", "  Cambio Motor "):
            with self.subTest(texto=texto):
                self.assertInvalido(
                    f"Proceso personalizado 1: '{texto.strip()}' ya está en la lista de procesos; marcalo ahí.",
                    procesos_personalizados=[texto],
                )

    def test_repetidos_entre_si(self):
        self.assertInvalido(
            "Proceso personalizado 2: 'PULIDO' está repetido.",
            procesos_personalizados=["Pulido", "PULIDO"],
        )

    def test_tipo_invalido(self):
        mensaje = "El campo procesos_personalizados debe ser una lista de textos."
        for valor in ("Pulido", [3], [None]):
            with self.subTest(valor=valor):
                self.assertInvalido(mensaje, procesos_personalizados=valor)

    def test_no_aparece_en_el_catalogo(self):
        self.crear(procesos_personalizados=["Pulido"])
        self.assertNotIn("Pulido", [p.nombre for p in self.procesos.listar()])


class PrioridadTest(OrdenBase):
    def test_componentes_vacios_gana_sobre_proceso_inexistente(self):
        self.assertInvalido("La orden requiere al menos un componente.", componentes=[], procesos=["nada"])

    def test_proceso_inexistente_gana_sobre_numero_duplicado(self):
        self.crear("OT-1")
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear("OT-1", procesos=["nada"])
        self.assertEqual(str(cm.exception), "El proceso 'nada' no existe.")

    def test_procesos_gana_sobre_personalizados(self):
        self.assertInvalido(
            "El proceso 'nada' no existe.", procesos=["nada"], procesos_personalizados=[""]
        )


if __name__ == "__main__":
    unittest.main()
