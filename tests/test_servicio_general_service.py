"""ServicioGeneralService con SQLite real (C-06g, grupo 4)."""
import unittest

from inventario.domain.entities import ServicioGeneral
from inventario.domain.errors import (
    DatosInvalidos,
    ServicioGeneralDuplicado,
    ServicioGeneralNoEncontrado,
)
from inventario.repositories.sqlite_repo import SqliteServicioGeneralRepository
from inventario.services.servicio_general_service import ServicioGeneralService
from tests.helpers import conexion_inicializada

CHEQUEOS_20 = ("Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico")
MSG_CLAVE = (
    "La clave del servicio general admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)
MSG_TIPO = "El campo chequeos debe ser una lista de textos."
MSG_SIN = "El servicio general requiere al menos un chequeo."


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.service = ServicioGeneralService(SqliteServicioGeneralRepository(self.conn))

    def catalogo(self):
        return [(s.clave, s.nombre, s.chequeos) for s in self.service.listar()]

    def assertInvalido(self, mensaje, fn, *args, **kwargs):
        antes = self.catalogo()
        with self.assertRaises(DatosInvalidos) as cm:
            fn(*args, **kwargs)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertEqual(self.catalogo(), antes)


class CrearTest(Base):
    def test_deriva_la_clave_y_recorta(self):
        r = self.service.crear("  Servicio 100 hs ", ["Cambio de aceite"])
        self.assertEqual(r, ServicioGeneral("servicio-100-hs", "Servicio 100 hs", ("Cambio de aceite",)))

    def test_clave_con_tildes_y_simbolos_se_normaliza(self):
        self.assertEqual(self.service.crear("Revisión  Básica!", ["A"]).clave, "revision-basica")

    def test_clave_indicada_se_normaliza_a_minusculas(self):
        r = self.service.crear("Otro", ["A"], clave="  Mi-Clave ")
        self.assertEqual(r.clave, "mi-clave")

    def test_clave_invalida(self):
        self.assertInvalido(MSG_CLAVE, self.service.crear, "Otro", ["A"], clave="serv 100!")

    def test_clave_no_texto(self):
        self.assertInvalido("El campo clave debe ser texto.", self.service.crear, "Otro", ["A"], clave=3)

    def test_clave_repetida(self):
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.service.crear("Service veinte", ["A"], clave="Servicio-20-HS")
        self.assertEqual(str(cm.exception), "Ya existe un servicio general con clave 'servicio-20-hs'.")

    def test_nombre_repetido_sin_distinguir_mayusculas(self):
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.service.crear("SERVICIO 20 HS", ["A"])
        self.assertEqual(str(cm.exception), "Ya existe un servicio general con nombre 'SERVICIO 20 HS'.")

    def test_nombre_repetido_con_tildes_casefold(self):
        self.service.crear("Revisión", ["A"])
        with self.assertRaises(ServicioGeneralDuplicado):
            self.service.crear("REVISIÓN", ["A"])

    def test_nombre_vacio_o_largo(self):
        self.assertInvalido("El campo nombre es obligatorio.", self.service.crear, "   ", ["A"])
        self.assertInvalido("El campo nombre es obligatorio.", self.service.crear, None, ["A"])
        self.assertInvalido(
            "El nombre del servicio general admite hasta 60 caracteres.",
            self.service.crear, "x" * 61, ["A"],
        )
        self.assertEqual(self.service.crear("x" * 60, ["A"]).nombre, "x" * 60)


class ChequeosTest(Base):
    def test_recortados_y_en_orden(self):
        r = self.service.crear("Nuevo", ["  Chequeo de motor ", "Chequeo de hélice"])
        self.assertEqual(r.chequeos, ("Chequeo de motor", "Chequeo de hélice"))

    def test_espacios_internos_se_conservan(self):
        self.assertEqual(self.service.crear("Nuevo", ["a  b"]).chequeos, ("a  b",))

    def test_vacios_o_ausentes(self):
        self.assertInvalido(MSG_SIN, self.service.crear, "Nuevo", [])
        self.assertInvalido(MSG_SIN, self.service.crear, "Nuevo", None)

    def test_treinta_si_treinta_y_uno_no(self):
        self.assertEqual(len(self.service.crear("Nuevo", [f"C{i}" for i in range(30)]).chequeos), 30)
        self.assertInvalido(
            "El servicio general admite hasta 30 chequeos.",
            self.service.crear, "Otro", [f"C{i}" for i in range(31)],
        )

    def test_vacio_o_largo_informa_la_posicion(self):
        self.assertInvalido(
            "Chequeo 2: El nombre es obligatorio.", self.service.crear, "N", ["Chequeo de motor", "   "]
        )
        self.assertInvalido(
            "Chequeo 2: El nombre admite hasta 60 caracteres.",
            self.service.crear, "N", ["Chequeo de motor", "x" * 61],
        )
        self.assertInvalido(
            "Chequeo 1: El nombre es obligatorio.", self.service.crear, "N", [""]
        )

    def test_repetido_sin_distinguir_mayusculas_ni_tildes(self):
        self.assertInvalido(
            "Chequeo 2: 'CHEQUEO DE MOTOR' está repetido.",
            self.service.crear, "N", ["Chequeo de motor", "CHEQUEO DE MOTOR"],
        )
        self.assertInvalido(
            "Chequeo 3: 'ELÉCTRICO' está repetido.", self.service.crear, "N", ["Eléctrico", "B", "ELÉCTRICO"]
        )

    def test_tipo_invalido(self):
        self.assertInvalido(MSG_TIPO, self.service.crear, "N", "Chequeo de motor")
        self.assertInvalido(MSG_TIPO, self.service.crear, "N", [3])
        self.assertInvalido(MSG_TIPO, self.service.crear, "N", ["ok", None])


class ModificarTest(Base):
    def test_renombra_con_la_clave_en_mayusculas(self):
        r = self.service.modificar("SERVICIO-20-HS", nombre="Service 20 horas")
        self.assertEqual(r, ServicioGeneral("servicio-20-hs", "Service 20 horas", CHEQUEOS_20))

    def test_mismo_nombre_no_es_error(self):
        r = self.service.modificar("servicio-20-hs", nombre="servicio 20 HS")
        self.assertEqual(r.nombre, "servicio 20 HS")

    def test_solo_chequeos(self):
        r = self.service.modificar("servicio-20-hs", chequeos=[" Chequeo de motor", "Chequeo de batería"])
        self.assertEqual(r.chequeos, ("Chequeo de motor", "Chequeo de batería"))
        self.assertEqual(r.nombre, "Servicio 20 hs")

    def test_chequeos_invalidos_con_nombre_valido_no_cambian_nada(self):
        self.assertInvalido(
            "Chequeo 2: 'a' está repetido.",
            self.service.modificar, "servicio-20-hs", nombre="Service 20 horas", chequeos=["A", "a"],
        )

    def test_nombre_de_otro_servicio(self):
        self.service.crear("Servicio 100 hs", ["A"])
        antes = self.catalogo()
        with self.assertRaises(ServicioGeneralDuplicado) as cm:
            self.service.modificar("servicio-20-hs", nombre="servicio 100 HS")
        self.assertEqual(str(cm.exception), "Ya existe un servicio general con nombre 'servicio 100 HS'.")
        self.assertEqual(self.catalogo(), antes)

    def test_sin_nombre_ni_chequeos(self):
        self.assertInvalido("Indicá el nombre o los chequeos a modificar.", self.service.modificar, "servicio-20-hs")

    def test_nombre_vacio_explicito(self):
        self.assertInvalido(
            "El campo nombre es obligatorio.", self.service.modificar, "servicio-20-hs", nombre=None
        )

    def test_inexistente(self):
        with self.assertRaises(ServicioGeneralNoEncontrado) as cm:
            self.service.modificar("servicio-500-hs", nombre="X")
        self.assertEqual(str(cm.exception), "No existe un servicio general con clave 'servicio-500-hs'.")

    def test_clave_de_ruta_vacia(self):
        self.assertInvalido(MSG_CLAVE, self.service.modificar, "  ", nombre="X")


class BorrarTest(Base):
    def test_normaliza_la_clave_y_devuelve_lo_borrado(self):
        r = self.service.borrar(" Servicio-20-HS ")
        self.assertEqual(r, ServicioGeneral("servicio-20-hs", "Servicio 20 hs", CHEQUEOS_20))
        self.assertEqual(self.catalogo(), [])

    def test_inexistente(self):
        with self.assertRaises(ServicioGeneralNoEncontrado) as cm:
            self.service.borrar("servicio-500-hs")
        self.assertEqual(str(cm.exception), "No existe un servicio general con clave 'servicio-500-hs'.")

    def test_clave_vacia(self):
        self.assertInvalido(MSG_CLAVE, self.service.borrar, "")


class ListarTest(Base):
    def test_ordenado_por_nombre(self):
        self.service.crear("Servicio 100 hs", ["A"])
        self.assertEqual(
            [s.clave for s in self.service.listar()], ["servicio-100-hs", "servicio-20-hs"]
        )


if __name__ == "__main__":
    unittest.main()
