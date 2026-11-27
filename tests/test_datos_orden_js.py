"""Comportamiento de static/js/datos-orden.js (validacion pura de los datos del cliente) con Node.

Se omite si Node no esta instalado. Los textos replican los del backend (services/orden_service.py).
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "static" / "js" / "datos-orden.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
process.stdout.write(JSON.stringify(window.DatosOrden.validar(JSON.parse(process.argv[2]))));
"""

MSG_CELULAR = "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)."
CAMPOS = ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso")


def validar(**campos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(DATOS), json.dumps(campos)],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def sin_errores(valores):
    return {"valores": valores, "errores": {}}


@unittest.skipUnless(NODE, "Node no esta instalado")
class ValidarDatosTest(unittest.TestCase):
    def test_todo_vacio_da_null_sin_errores(self):
        for vacio in ("", "   ", None):
            with self.subTest(vacio=vacio):
                r = validar(**{c: vacio for c in CAMPOS})
                self.assertEqual(r, sin_errores({c: None for c in CAMPOS}))

    def test_sin_ningun_campo_tambien_es_valido(self):
        self.assertEqual(validar(), sin_errores({c: None for c in CAMPOS}))

    def test_recorta_y_conserva_espacios_internos(self):
        r = validar(cliente="  Juan  Pérez ", casco=" Bermuda 190 ", fecha_ingreso="2026-11-26")
        self.assertEqual(r["valores"]["cliente"], "Juan  Pérez")
        self.assertEqual(r["valores"]["casco"], "Bermuda 190")
        self.assertEqual(r["valores"]["fecha_ingreso"], "2026-11-26")
        self.assertEqual(r["errores"], {})

    def test_cliente_largo(self):
        self.assertEqual(validar(cliente="x" * 80)["errores"], {})
        self.assertEqual(
            validar(cliente="x" * 81)["errores"], {"cliente": "El cliente admite hasta 80 caracteres."}
        )

    def test_casco_motor_y_trailer_largos(self):
        for campo in ("casco", "motor", "trailer"):
            with self.subTest(campo=campo):
                self.assertEqual(validar(**{campo: "x" * 60})["errores"], {})
                self.assertEqual(
                    validar(**{campo: "x" * 61})["errores"],
                    {campo: f"El campo {campo} admite hasta 60 caracteres."},
                )

    def test_celulares_validos(self):
        for texto in ("11 5555-1234", "+54 9 11 5555-1234", "(011) 4555-1234", " 1155551234 "):
            with self.subTest(celular=texto):
                r = validar(celular=texto)
                self.assertEqual(r["errores"], {})
                self.assertEqual(r["valores"]["celular"], texto.strip())

    def test_celulares_invalidos(self):
        for texto in ("11-abc", "12345", "11+5555 1234", "1" * 21, "(((---)))"):
            with self.subTest(celular=texto):
                self.assertEqual(validar(celular=texto)["errores"], {"celular": MSG_CELULAR})

    def test_fechas_solo_ingreso_solo_egreso_y_misma_fecha(self):
        self.assertEqual(validar(fecha_egreso="2026-11-20")["errores"], {})
        self.assertEqual(validar(fecha_ingreso="2026-11-20")["errores"], {})
        self.assertEqual(validar(fecha_ingreso="2026-11-27", fecha_egreso="2026-11-27")["errores"], {})
        self.assertEqual(validar(fecha_ingreso="2026-11-26", fecha_egreso="2026-11-29")["errores"], {})

    def test_egreso_anterior_al_ingreso(self):
        r = validar(fecha_ingreso="2026-11-27", fecha_egreso="2026-11-26")
        self.assertEqual(
            r["errores"], {"fecha_egreso": "La fecha de egreso no puede ser anterior a la de ingreso."}
        )

    def test_fechas_mal_escritas_o_inexistentes(self):
        self.assertEqual(
            validar(fecha_ingreso="30/11/2026")["errores"],
            {"fecha_ingreso": "La fecha de ingreso debe tener formato AAAA-MM-DD."},
        )
        self.assertEqual(
            validar(fecha_egreso="2026-02-30")["errores"],
            {"fecha_egreso": "La fecha de egreso (2026-02-30) no es una fecha válida."},
        )

    def test_varios_errores_a_la_vez_uno_por_campo(self):
        r = validar(cliente="x" * 81, celular="abc", fecha_ingreso="2026-11-27", fecha_egreso="2026-11-01")
        self.assertEqual(set(r["errores"]), {"cliente", "celular", "fecha_egreso"})


if __name__ == "__main__":
    unittest.main()
