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


def linea(valor, texto="", precio=None):
    return {"valor": valor, "texto": texto, "precio": precio}


def pers(texto, precio=None):
    return linea("personalizado", texto, precio)


def cat(clave, precio=None):
    return {"clave": clave, "precio": precio}


def nom(nombre, precio=None):
    return {"nombre": nombre, "precio": precio}


@unittest.skipUnless(NODE, "Node no esta instalado")
class ArmarTest(unittest.TestCase):
    def test_lineas_de_catalogo_en_orden(self):
        r = armar([linea("limpieza"), linea("cambio-motor")])
        self.assertEqual(
            r,
            {
                "procesos": [cat("limpieza"), cat("cambio-motor")],
                "procesos_personalizados": [],
                "errores": [None, None],
            },
        )

    def test_sin_lineas(self):
        self.assertEqual(armar([]), {"procesos": [], "procesos_personalizados": [], "errores": []})

    def test_linea_de_catalogo_con_texto_residual_no_envia_el_texto(self):
        r = armar([linea("limpieza", "texto viejo")])
        self.assertEqual((r["procesos"], r["procesos_personalizados"]), ([cat("limpieza")], []))

    def test_mismo_proceso_en_dos_lineas_es_error_en_la_segunda(self):
        r = armar([linea("limpieza", precio=1000), linea("cambio-motor"), linea("limpieza", precio=2000)])
        self.assertEqual(r["procesos"], [cat("limpieza", 1000), cat("cambio-motor")])
        self.assertEqual(r["errores"], [None, None, "Ya está en otra línea."])

    def test_tres_lineas_iguales_marcan_la_segunda_y_la_tercera(self):
        r = armar([linea("limpieza"), linea("limpieza"), linea("limpieza")])
        self.assertEqual(r["errores"], [None, "Ya está en otra línea.", "Ya está en otra línea."])
        self.assertEqual(r["procesos"], [cat("limpieza")])

    def test_cada_linea_lleva_su_precio_vacio_o_cargado(self):
        r = armar([linea("limpieza", precio=1500000), linea("cambio-motor"), pers("Pulido", 800000), pers("Pintura")])
        self.assertEqual(r["procesos"], [cat("limpieza", 1500000), cat("cambio-motor", None)])
        self.assertEqual(r["procesos_personalizados"], [nom("Pulido", 800000), nom("Pintura", None)])
        self.assertEqual(r["errores"], [None, None, None, None])

    def test_personalizados_recortados_y_en_orden(self):
        r = armar([pers("  Pulido fino "), linea("limpieza"), pers("Pintura")])
        self.assertEqual(r["procesos"], [cat("limpieza")])
        self.assertEqual(r["procesos_personalizados"], [nom("Pulido fino"), nom("Pintura")])
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
        self.assertEqual((r["procesos_personalizados"], r["errores"]), ([nom("Pulido")], [None]))


if __name__ == "__main__":
    unittest.main()
