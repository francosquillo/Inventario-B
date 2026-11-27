"""Comportamiento de static/js/precios.js (importes en pesos <-> centavos y resumen) con Node.

Se omite si Node no esta instalado. La tabla de casos del resumen es la misma de
tests/test_orden_totales.py (calculo del backend).
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from tests.test_orden_totales import CASOS

RAIZ = Path(__file__).resolve().parents[1]
PRECIOS = RAIZ / "static" / "js" / "precios.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const [funcion, argumentos] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(window.Precios[funcion](...argumentos)));
"""

ERROR_FORMATO = "Ingresá un importe válido (ej. 12.500,50)."
ERROR_MAXIMO = "El importe admite hasta $ 999.999.999,99."


def llamar(funcion, *argumentos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(PRECIOS), json.dumps([funcion, list(argumentos)])],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def parsear(texto):
    return llamar("parsear", texto)


@unittest.skipUnless(NODE, "Node no esta instalado")
class ParsearTest(unittest.TestCase):
    def test_miles_y_centavos_a_centavos_enteros(self):
        self.assertEqual(parsear("12.500,50"), {"centavos": 1250050, "error": None})

    def test_formas_validas(self):
        casos = {
            "12500": 1250000,
            "12.500": 1250000,
            "12500,5": 1250050,
            "12.500,50": 1250050,
            "$ 12.500": 1250000,
            "$12.500,05": 1250005,
            " 0 ": 0,
            "0,01": 1,
            "1.234.567": 123456700,
            "999.999.999,99": 99999999999,
        }
        for texto, centavos in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(parsear(texto), {"centavos": centavos, "error": None})

    def test_vacio_o_espacios_es_sin_precio(self):
        for texto in ("", "   ", None):
            with self.subTest(texto=texto):
                self.assertEqual(parsear(texto), {"centavos": None, "error": None})

    def test_formas_invalidas(self):
        for texto in ("12.5", "1.23.456", "-100", "1,234", "abc", "12,", ",50", "1.2345", "12,5,0", "$"):
            with self.subTest(texto=texto):
                self.assertEqual(parsear(texto), {"centavos": None, "error": ERROR_FORMATO})

    def test_mayor_al_tope(self):
        for texto in ("1.000.000.000", "1000000000,00", "99999999999999999999"):
            with self.subTest(texto=texto):
                self.assertEqual(parsear(texto), {"centavos": None, "error": ERROR_MAXIMO})


@unittest.skipUnless(NODE, "Node no esta instalado")
class FormatearTest(unittest.TestCase):
    def test_formato_argentino_con_dos_decimales(self):
        casos = {
            1250050: "$ 12.500,50",
            0: "$ 0,00",
            5: "$ 0,05",
            100: "$ 1,00",
            123456789: "$ 1.234.567,89",
            99999999999: "$ 999.999.999,99",
        }
        for centavos, esperado in casos.items():
            with self.subTest(centavos=centavos):
                self.assertEqual(llamar("formatear", centavos), esperado)

    def test_sin_precio_es_guion(self):
        self.assertEqual(llamar("formatear", None), "—")


@unittest.skipUnless(NODE, "Node no esta instalado")
class ResumenTest(unittest.TestCase):
    def test_misma_tabla_de_casos_que_el_dominio(self):
        for descripcion, servicio, adicionales, items, st_serv, st_items, total in CASOS:
            with self.subTest(descripcion):
                r = llamar("resumen", {"servicio": servicio, "adicionales": list(adicionales), "items": list(items)})
                self.assertEqual(
                    r, {"subtotal_servicios": st_serv, "subtotal_items": st_items, "total": total}
                )

    def test_sin_nada_vale_cero(self):
        self.assertEqual(
            llamar("resumen", {"servicio": None, "adicionales": [], "items": []}),
            {"subtotal_servicios": 0, "subtotal_items": 0, "total": 0},
        )

    def test_importes_invalidos_mientras_se_tipea_cuentan_cero(self):
        r = llamar("resumen", {"servicio": "abc", "adicionales": [None, 100], "items": [None, 50]})
        self.assertEqual(r, {"subtotal_servicios": 100, "subtotal_items": 50, "total": 150})


if __name__ == "__main__":
    unittest.main()
