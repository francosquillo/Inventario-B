"""Guardas estaticas de /ordenes y del PDF con datos del cliente y precios (C-06h, grupo 9).
No ejecutan JS: fijan la estructura de los mockups L1 y P1 aprobados y las reglas de seguridad."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


class OrdenesPantallaTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "ordenes.js")
        self.html = leer("ordenes.html")

    def test_carga_precios_js_antes_de_ordenes_js(self):
        self.assertLess(self.html.index("/static/js/precios.js"), self.html.index("/static/js/ordenes.js"))

    def test_la_fecha_sigue_en_la_cabecera_y_el_encabezado_impreso_no_cambia(self):
        self.assertRegex(self.js, r'"num text-sm text-muted" \}, o\.fecha\)')
        self.assertRegex(self.js, r'linea:\s*"Fecha: " \+ o\.fecha \+ " · " \+ n')
        self.assertRegex(self.js, r'titulo:\s*"Orden " \+ o\.numero')

    def test_fila_de_datos_solo_si_hay_alguno_con_ingreso_y_egreso(self):
        self.assertIn('"ord-datos"', self.js)
        for etiqueta in ("Cliente:", "Cel.:", "Casco:", "Motor:", "Trailer:", "Ingreso:", "Egreso:"):
            self.assertIn(etiqueta, self.js)
        self.assertIn("Celular:", self.js)  # etiqueta impresa
        for campo in ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso"):
            self.assertRegex(self.js, rf"o\.{campo}\b")
        self.assertRegex(self.js, r"datos\.length\s*===\s*0")

    def test_precio_del_servicio_y_chips_con_nombre_y_precio(self):
        self.assertRegex(self.js, r"o\.servicio\.precio")
        self.assertRegex(self.js, r"p\.precio")
        self.assertIn("Servicios adicionales:", self.js)
        self.assertIn("Servicios adicionales", self.js)
        self.assertNotIn("Procesos realizados", self.js)
        self.assertNotIn('"Procesos:"', self.js)

    def test_columna_importe_y_formato_de_precios(self):
        self.assertIn('"Importe"', self.js)
        self.assertRegex(self.js, r"c\.precio")
        self.assertIn("Precios.formatear(", self.js)

    def test_resumen_con_los_valores_de_la_api_sin_recalcular(self):
        for texto in ("Subtotal servicios", "Subtotal ítems", "Total"):
            self.assertIn(texto, self.js)
        for campo in ("subtotal_servicios", "subtotal_items", "total"):
            self.assertIn(f"o.{campo}", self.js)
        self.assertNotIn("Precios.resumen", self.js)
        self.assertNotRegex(self.js, r"\.reduce\(")

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)


class OrdenesCssTest(unittest.TestCase):
    def setUp(self):
        self.css = leer("css", "app.css")
        self.impresion = self.css[self.css.rindex("@media print"):]

    def test_clases_nuevas_con_tokens(self):
        for clase in (".ord-datos", ".ord-foot", ".precio", ".resumen"):
            self.assertIn(clase, self.css)
        self.assertRegex(self.css, r"\.ord-datos dt\s*\{[^}]*var\(--color-")

    def test_impresion_datos_en_dos_columnas_servicio_y_resumen_al_final(self):
        bloque = self.impresion
        self.assertRegex(bloque, r"\.ord-datos\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2")
        self.assertRegex(bloque, r"\.ord-foot\s*\{[^}]*order\s*:\s*3")
        self.assertIn(".sep", bloque)

    def test_tokens_y_ui_css_intactos(self):
        for nombre in ("tokens.css", "ui.css"):
            copia = leer("css", nombre)
            original = (RAIZ / "design-system" / nombre).read_text(encoding="utf-8")
            self.assertEqual(copia, original, nombre)
            self.assertNotIn("ord-datos", copia)
            self.assertIsNone(re.search(r"\.resumen\b", copia))


if __name__ == "__main__":
    unittest.main()
