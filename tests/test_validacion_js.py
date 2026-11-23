"""Comportamiento de static/js/validacion.js (funciones puras) ejecutado con Node.

Se omite si Node no esta instalado; el resto de la suite no depende de el. Las guardas
estaticas de tests/test_frontend_estatico.py cubren los mensajes aun sin Node.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VALIDACION = RAIZ / "static" / "js" / "validacion.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const V = window.Validacion;
const casos = JSON.parse(process.argv[2]);
const salida = casos.map(([fn, args]) => V[fn](...args));
process.stdout.write(JSON.stringify(salida));
"""

MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000."
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def ejecutar(casos):
    """casos: [(funcion, [argumentos])] -> lista de resultados."""
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(VALIDACION), json.dumps(casos)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def linea(codigo, modo, valor, nombre=""):
    return {"codigo": codigo, "modo": modo, "valor": valor, "nombre": nombre}


@unittest.skipUnless(NODE, "Node no esta instalado")
class StockTest(unittest.TestCase):
    def test_acepta_bordes_y_texto_con_espacios(self):
        entradas = ["0", "1", "10000", " 7 "]
        res = ejecutar([["stock", [e]] for e in entradas])
        self.assertEqual(res, [None, None, None, None])

    def test_rechaza_negativos_decimales_vacio_texto_y_fuera_de_rango(self):
        entradas = ["-1", "2.5", "10001", "", "  ", "abc", "1e3", None]
        res = ejecutar([["stock", [e]] for e in entradas])
        self.assertEqual(res, [MSG_STOCK] * len(entradas))


@unittest.skipUnless(NODE, "Node no esta instalado")
class LineasModificacionTest(unittest.TestCase):
    def validar(self, lineas):
        return ejecutar([["lineasModificacion", [lineas]]])[0]

    def test_sin_lineas_o_demasiadas(self):
        self.assertEqual(self.validar([])["general"], "Agregá al menos un producto.")
        res = self.validar([linea("A-%d" % i, "sumar", "1") for i in range(101)])
        self.assertEqual(res["general"], "Una modificación admite hasta 100 productos.")
        res = self.validar([linea("A-%d" % i, "sumar", "1") for i in range(100)])
        self.assertIsNone(res["general"])

    def test_lineas_validas(self):
        res = self.validar([linea("A-01", "fijar", "0"), linea("B-02", "sumar", "10000")])
        self.assertEqual(res, {"general": None, "porLinea": [None, None]})

    def test_linea_sin_producto(self):
        res = self.validar([linea("", "fijar", "3")])
        self.assertEqual(res["porLinea"][0]["producto"], "Elegí un producto.")

    def test_fijar_valida_stock_y_sumar_valida_cantidad(self):
        res = self.validar([linea("A-01", "fijar", "-1"), linea("B-02", "sumar", "0")])
        self.assertEqual(res["porLinea"][0]["valor"], MSG_STOCK)
        self.assertEqual(res["porLinea"][1]["valor"], MSG_CANTIDAD)

    def test_cero_vale_para_fijar_pero_no_para_sumar(self):
        res = self.validar([linea("A-01", "fijar", "0"), linea("B-02", "sumar", "0")])
        self.assertIsNone(res["porLinea"][0])
        self.assertIsNotNone(res["porLinea"][1])

    def test_producto_repetido_marca_la_segunda_aparicion(self):
        res = self.validar([linea("A-01", "fijar", "1"), linea("B-02", "sumar", "1"), linea("A-01", "sumar", "1")])
        self.assertIsNone(res["porLinea"][0])
        self.assertEqual(res["porLinea"][2]["producto"], "Este producto ya está en la línea 1.")

    def test_nombre_largo(self):
        res = self.validar([linea("A-01", "fijar", "1", "x" * 121)])
        self.assertEqual(res["porLinea"][0]["nombre"], "El nombre admite hasta 120 caracteres.")
        res = self.validar([linea("A-01", "fijar", "1", "x" * 120)])
        self.assertIsNone(res["porLinea"][0])

    def test_hay_errores_reconoce_los_nuevos_resultados(self):
        res = ejecutar(
            [
                ["hayErrores", [{"general": None, "porLinea": [None]}]],
                ["hayErrores", [{"general": None, "porLinea": [{"valor": "x"}]}]],
                ["hayErrores", [{"general": "x", "porLinea": []}]],
            ]
        )
        self.assertEqual(res, [False, True, True])


if __name__ == "__main__":
    unittest.main()
