"""Comportamiento de static/js/procesos.js (validacion pura de la nueva orden) ejecutado con Node.

Se omite si Node no esta instalado.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROCESOS = RAIZ / "static" / "js" / "procesos.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const [lineas, catalogo] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(window.Procesos.armar(lineas, catalogo)));
"""

CATALOGO = [
    {"clave": "cambio-filtro", "nombre": "Cambio filtro"},
    {"clave": "cambio-motor", "nombre": "Cambio motor"},
    {"clave": "limpieza", "nombre": "Limpieza"},
]


def armar(lineas, catalogo=None):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(PROCESOS), json.dumps([lineas, CATALOGO if catalogo is None else catalogo])],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def linea(valor, texto=""):
    return {"valor": valor, "texto": texto}


def pers(texto):
    return linea("personalizado", texto)


@unittest.skipUnless(NODE, "Node no esta instalado")
class ArmarTest(unittest.TestCase):
    def test_lineas_de_catalogo_en_orden(self):
        r = armar([linea("limpieza"), linea("cambio-motor")])
        self.assertEqual(
            r, {"procesos": ["limpieza", "cambio-motor"], "procesos_personalizados": [], "errores": [None, None]}
        )

    def test_sin_lineas(self):
        self.assertEqual(armar([]), {"procesos": [], "procesos_personalizados": [], "errores": []})

    def test_linea_de_catalogo_con_texto_residual_no_envia_el_texto(self):
        r = armar([linea("limpieza", "texto viejo")])
        self.assertEqual((r["procesos"], r["procesos_personalizados"]), (["limpieza"], []))

    def test_mismo_proceso_en_dos_lineas_se_cuenta_una_vez_sin_error(self):
        r = armar([linea("limpieza"), linea("cambio-motor"), linea("limpieza")])
        self.assertEqual(r["procesos"], ["limpieza", "cambio-motor"])
        self.assertEqual(r["errores"], [None, None, None])

    def test_personalizados_recortados_y_en_orden(self):
        r = armar([pers("  Pulido fino "), linea("limpieza"), pers("Pintura")])
        self.assertEqual(r["procesos"], ["limpieza"])
        self.assertEqual(r["procesos_personalizados"], ["Pulido fino", "Pintura"])
        self.assertEqual(r["errores"], [None, None, None])

    def test_vacio_marca_su_indice(self):
        r = armar([pers("Pulido"), pers("   ")])
        self.assertEqual(r["errores"], [None, "El nombre es obligatorio."])

    def test_largo(self):
        self.assertEqual(armar([pers("x" * 60)])["errores"], [None])
        self.assertEqual(armar([pers("x" * 61)])["errores"], ["El nombre admite hasta 60 caracteres."])

    def test_igual_al_catalogo_sin_distinguir_mayusculas_ni_tildes_de_caso(self):
        catalogo = CATALOGO + [{"clave": "reparacion", "nombre": "Reparación"}]
        r = armar([pers("limpieza"), pers(" CAMBIO MOTOR "), pers("REPARACIÓN")], catalogo)
        self.assertEqual(
            r["errores"],
            [
                "'limpieza' ya está en la lista de procesos; marcalo ahí.",
                "'CAMBIO MOTOR' ya está en la lista de procesos; marcalo ahí.",
                "'REPARACIÓN' ya está en la lista de procesos; marcalo ahí.",
            ],
        )

    def test_repetido_marca_el_segundo(self):
        r = armar([pers("Pulido"), pers("PULIDO")])
        self.assertEqual(r["errores"], [None, "'PULIDO' está repetido."])

    def test_tope_de_diez_personalizados(self):
        r = armar([pers("P" + str(i)) for i in range(11)])
        self.assertEqual(r["errores"][:10], [None] * 10)
        self.assertEqual(r["errores"][10], "Una orden admite hasta 10 procesos personalizados.")
        self.assertEqual(len(armar([pers("P" + str(i)) for i in range(10)])["procesos_personalizados"]), 10)

    def test_catalogo_caido_solo_personalizados(self):
        r = armar([pers("Pulido")], [])
        self.assertEqual((r["procesos_personalizados"], r["errores"]), (["Pulido"], [None]))


if __name__ == "__main__":
    unittest.main()
