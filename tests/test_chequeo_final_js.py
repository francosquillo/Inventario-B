"""Comportamiento de static/js/chequeo-final.js (lista fija y lectura del formulario) con Node.

Se omite si Node no esta instalado. La lista ITEMS debe ser igual a CHEQUEO_FINAL del backend.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from inventario.domain.chequeo_final import CHEQUEO_FINAL

RAIZ = Path(__file__).resolve().parents[1]
MODULO = RAIZ / "static" / "js" / "chequeo-final.js"
PRECIOS = RAIZ / "static" / "js" / "precios.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
require(process.argv[2]);
const [funcion, argumentos] = JSON.parse(process.argv[3]);
const r = funcion === "ITEMS" ? window.ChequeoFinal.ITEMS : window.ChequeoFinal[funcion](...argumentos);
process.stdout.write(JSON.stringify(r));
"""

ERROR_FORMATO = "Ingresá un importe válido (ej. 12.500,50)."
ERROR_MAXIMO = "El importe admite hasta $ 999.999.999,99."


def llamar(funcion, *argumentos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(PRECIOS), str(MODULO), json.dumps([funcion, list(argumentos)])],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def fila(clave, marcado, importe=""):
    return {"clave": clave, "marcado": marcado, "importe": importe}


@unittest.skipUnless(NODE, "Node no esta instalado")
class ItemsTest(unittest.TestCase):
    def test_items_igual_a_la_lista_fija_del_backend(self):
        esperado = [{"clave": c, "nombre": n} for c, n in CHEQUEO_FINAL]
        self.assertEqual(llamar("ITEMS"), esperado)
        self.assertEqual(len(esperado), 6)

    def test_check_list_y_verificacion_final_esta_en_el_tercer_lugar(self):
        items = llamar("ITEMS")
        self.assertEqual(
            (items[2]["clave"], items[2]["nombre"]),
            ("check-list-y-verificacion-final", "Check-list y verificación final"),
        )


@unittest.skipUnless(NODE, "Node no esta instalado")
class LeerTest(unittest.TestCase):
    def test_solo_los_marcados_con_importe_en_centavos_o_null(self):
        r = llamar("leer", [
            fila("combustible", True, "8.000,00"), fila("puesta-en-marcha", False, "999"),
            fila("entrega", True, ""),
        ])
        self.assertEqual(r["valores"], [
            {"clave": "combustible", "precio": 800000}, {"clave": "entrega", "precio": None},
        ])
        self.assertEqual(r["errores"], [None, None, None])

    def test_ninguno_marcado_devuelve_lista_vacia(self):
        r = llamar("leer", [fila("combustible", False), fila("entrega", False, "5")])
        self.assertEqual(r, {"valores": [], "errores": [None, None]})

    def test_importe_invalido_es_error_de_su_fila(self):
        r = llamar("leer", [
            fila("combustible", True, "12.5"), fila("entrega", True, "1.000"),
        ])
        self.assertEqual(r["errores"], [ERROR_FORMATO, None])
        self.assertEqual(r["valores"], [{"clave": "entrega", "precio": 100000}])  # la fila con error no se envia

    def test_importe_sobre_el_maximo(self):
        r = llamar("leer", [fila("entrega", True, "1.000.000.000,00")])
        self.assertEqual(r["errores"], [ERROR_MAXIMO])

    def test_importe_de_un_item_no_marcado_no_se_valida(self):
        r = llamar("leer", [fila("combustible", False, "abc")])
        self.assertEqual(r["errores"], [None])

    def test_importes_de_los_marcados_en_el_orden_recibido(self):
        r = llamar("leer", [fila("entrega", True, "1"), fila("combustible", True, "2")])
        self.assertEqual([v["clave"] for v in r["valores"]], ["entrega", "combustible"])


if __name__ == "__main__":
    unittest.main()
