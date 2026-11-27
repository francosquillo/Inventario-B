"""Guardas estaticas de los procesos en el frontend (C-06f, grupos 7 a 9). No ejecutan JS:
fijan la estructura aprobada en los mockups (N1, N2, L1, P1) y las reglas de seguridad."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


class NuevaOrdenProcesosTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.js = leer("js", "inventario.js")

    def test_bloque_procesos_despues_de_componentes_dentro_del_formulario(self):
        i_comp = self.html.index("<legend class=\"label\">Componentes</legend>")
        i_proc = self.html.index("<legend class=\"label\">Servicios adicionales</legend>")
        i_foot = self.html.index("modal-foot", i_proc)
        self.assertTrue(i_comp < i_proc < i_foot)
        self.assertLess(self.html.index('id="form-orden"'), i_proc)

    def test_contenedor_de_lineas_boton_y_ayuda_del_tope(self):
        self.assertRegex(self.html, r'<ul id="ord-procesos" class="plist"')
        self.assertRegex(self.html, r'id="ord-proc-agregar"[^>]*>Agregar servicio adicional</button>')
        self.assertIn("Una orden admite hasta 10 servicios adicionales personalizados.", self.html)
        self.assertIn('id="ord-proc-aviso"', self.html)

    def test_index_carga_procesos_js_antes_de_inventario_js(self):
        a = self.html.index("/static/js/procesos.js")
        self.assertLess(a, self.html.index("/static/js/inventario.js"))

    def test_js_pide_el_catalogo_valida_con_procesos_y_envia_ambos_campos(self):
        self.assertIn('Api.get("/api/procesos")', self.js)
        self.assertIn("Procesos.armar(", self.js)
        self.assertRegex(self.js, r"procesos\s*[:=]\s*\w+\.procesos\b")
        self.assertRegex(self.js, r"procesos_personalizados\s*[:=]\s*\w+\.procesos_personalizados")

    def test_js_maneja_errores_de_la_api(self):
        self.assertIn("No se pudo cargar la lista de servicios adicionales.", self.js)
        self.assertRegex(self.js, r"Proceso personalizado")
        self.assertRegex(self.js, r"no existe")

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)
        self.assertNotIn("innerHTML", leer("js", "procesos.js"))


class OrdenesChipsTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "ordenes.js")
        self.css = leer("css", "app.css")

    def test_fila_de_procesos_solo_si_hay_procesos(self):
        self.assertRegex(self.js, r"o\.procesos[^;\n]*length\s*>\s*0")
        self.assertIn("Servicios adicionales:", self.js)
        self.assertIn("Servicios adicionales", self.js)
        self.assertIn('"chips"', self.js)
        self.assertIn('"chip"', self.js)

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)

    def test_css_de_chips_y_lineas_con_tokens(self):
        for clase in (".plist", ".pline", ".chips", ".chip"):
            self.assertIn(clase, self.css)
        self.assertRegex(self.css, r"\.chip\s*\{[^}]*var\(--color-")

    def test_css_de_impresion_del_bloque_de_procesos(self):
        impresion = self.css[self.css.rindex("@media print"):]
        self.assertIn(".chips", impresion)
        self.assertRegex(impresion, r"\.chips\s*\{[^}]*order\s*:")
        self.assertIn(".lbl-print", impresion)

    def test_exportar_no_cambia_titulo_ni_linea(self):
        self.assertIn("Exportar.imprimir(", self.js)
        self.assertRegex(self.js, r"titulo:\s*\"Orden \" \+")


if __name__ == "__main__":
    unittest.main()
