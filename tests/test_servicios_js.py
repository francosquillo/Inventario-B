"""Comportamiento de static/js/servicios.js (validacion pura de servicios generales) con Node.

Se omite si Node no esta instalado.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SERVICIOS = RAIZ / "static" / "js" / "servicios.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const [funcion, args] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(window.Servicios[funcion](...args)));
"""

CATALOGO = [
    {"clave": "servicio-20-hs", "nombre": "Servicio 20 hs",
     "chequeos": ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"]},
    {"clave": "servicio-100-hs", "nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite"]},
]


def llamar(funcion, *args):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(SERVICIOS), json.dumps([funcion, list(args)])],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def armar(valor, catalogo=None):
    return llamar("armar", valor, CATALOGO if catalogo is None else catalogo)


def validar(nombre, chequeos, clave_actual=None, catalogo=None):
    return llamar(
        "validarFormulario",
        {"nombre": nombre, "chequeos": chequeos},
        CATALOGO if catalogo is None else catalogo,
        clave_actual,
    )


@unittest.skipUnless(NODE, "Node no esta instalado")
class ArmarTest(unittest.TestCase):
    def test_clave_del_catalogo(self):
        self.assertEqual(armar("servicio-20-hs"), {"servicio": "servicio-20-hs", "error": None})

    def test_vacio_o_nulo_es_sin_servicio(self):
        self.assertEqual(armar(""), {"servicio": None, "error": None})
        self.assertEqual(armar(None), {"servicio": None, "error": None})

    def test_clave_fuera_del_catalogo_es_error(self):
        self.assertEqual(
            armar("servicio-500-hs"),
            {"servicio": None, "error": "El servicio general elegido ya no está disponible."},
        )

    def test_catalogo_caido_con_sin_servicio_no_da_error(self):
        self.assertEqual(armar("", []), {"servicio": None, "error": None})

    def test_catalogo_caido_con_clave_si_da_error(self):
        self.assertEqual(armar("servicio-20-hs", [])["servicio"], None)
        self.assertIsNotNone(armar("servicio-20-hs", [])["error"])


@unittest.skipUnless(NODE, "Node no esta instalado")
class ChequeosDeTest(unittest.TestCase):
    def test_chequeos_en_orden(self):
        self.assertEqual(
            llamar("chequeosDe", "servicio-20-hs", CATALOGO),
            ["Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico"],
        )

    def test_vacio_o_clave_desconocida_es_lista_vacia(self):
        self.assertEqual(llamar("chequeosDe", "", CATALOGO), [])
        self.assertEqual(llamar("chequeosDe", "nada", CATALOGO), [])
        self.assertEqual(llamar("chequeosDe", None, CATALOGO), [])


@unittest.skipUnless(NODE, "Node no esta instalado")
class ValidarFormularioTest(unittest.TestCase):
    def test_datos_validos_se_recortan_sin_errores(self):
        r = validar("  Servicio 50 hs ", [" Chequeo A ", "Chequeo B"])
        self.assertEqual(r["nombre"], "Servicio 50 hs")
        self.assertEqual(r["chequeos"], ["Chequeo A", "Chequeo B"])
        self.assertEqual(r["errores"], {"nombre": None, "general": None, "chequeos": [None, None]})

    def test_nombre_vacio_y_largo(self):
        self.assertEqual(validar("  ", ["A"])["errores"]["nombre"], "El campo nombre es obligatorio.")
        self.assertEqual(
            validar("x" * 61, ["A"])["errores"]["nombre"],
            "El nombre del servicio general admite hasta 60 caracteres.",
        )
        self.assertIsNone(validar("x" * 60, ["A"])["errores"]["nombre"])

    def test_nombre_de_otro_servicio_sin_distinguir_mayusculas_ni_tildes(self):
        self.assertEqual(
            validar("SERVICIO 100 HS", ["A"])["errores"]["nombre"],
            "Ya existe un servicio general con nombre 'SERVICIO 100 HS'.",
        )
        catalogo = [{"clave": "rev", "nombre": "Revisión", "chequeos": ["A"]}]
        self.assertEqual(
            validar("REVISIÓN", ["A"], None, catalogo)["errores"]["nombre"],
            "Ya existe un servicio general con nombre 'REVISIÓN'.",
        )

    def test_el_mismo_nombre_del_servicio_editado_no_es_error(self):
        self.assertIsNone(validar("servicio 20 HS", ["A"], "servicio-20-hs")["errores"]["nombre"])
        self.assertIsNotNone(validar("servicio 20 HS", ["A"], "servicio-100-hs")["errores"]["nombre"])

    def test_sin_chequeos_es_error_general(self):
        self.assertEqual(
            validar("Nuevo", [])["errores"]["general"], "El servicio general requiere al menos un chequeo."
        )

    def test_mas_de_treinta_es_error_general(self):
        self.assertEqual(
            validar("Nuevo", [f"C{i}" for i in range(31)])["errores"]["general"],
            "El servicio general admite hasta 30 chequeos.",
        )
        self.assertIsNone(validar("Nuevo", [f"C{i}" for i in range(30)])["errores"]["general"])

    def test_chequeo_vacio_o_largo_en_su_indice(self):
        r = validar("Nuevo", ["Ok", "  ", "x" * 61])
        self.assertEqual(
            r["errores"]["chequeos"],
            [None, "El nombre es obligatorio.", "El nombre admite hasta 60 caracteres."],
        )

    def test_chequeo_repetido_marca_el_segundo(self):
        r = validar("Nuevo", ["Eléctrico", "B", "ELÉCTRICO"])
        self.assertEqual(r["errores"]["chequeos"], [None, None, "'ELÉCTRICO' está repetido."])


if __name__ == "__main__":
    unittest.main()
