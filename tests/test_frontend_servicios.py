"""Guardas estaticas del servicio general en el frontend (C-06g, grupos 7, 8 y 9). No ejecutan JS:
fijan la estructura aprobada en los mockups (S1, L2) y las reglas de seguridad."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


class NuevaOrdenServicioTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.js = leer("js", "inventario.js")

    def test_bloque_entre_la_fecha_y_componentes_dentro_del_formulario(self):
        i_fecha = self.html.index('id="ord-fecha"')
        i_srv = self.html.index('<legend class="label">Servicio general</legend>')
        i_comp = self.html.index('<legend class="label">Componentes</legend>')
        self.assertTrue(i_fecha < i_srv < i_comp)
        self.assertLess(self.html.index('id="form-orden"'), i_srv)

    def test_select_con_sin_servicio_por_defecto_lista_incluye_y_aviso(self):
        self.assertRegex(self.html, r'<select[^>]*id="ord-servicio"')
        self.assertRegex(self.html, r'<option value="">Sin servicio general</option>')
        self.assertIn("Incluye:", self.html)
        self.assertRegex(self.html, r'<ul id="ord-servicio-chequeos"')
        self.assertRegex(self.html, r'id="ord-servicio-aviso"[^>]*role="alert"')
        self.assertRegex(self.html, r'<label class="sr-only" for="ord-servicio">')

    def test_index_carga_servicios_js_antes_de_inventario_js(self):
        a = self.html.index("/static/js/servicios.js")
        self.assertLess(a, self.html.index("/static/js/inventario.js"))

    def test_js_pide_el_catalogo_valida_con_servicios_y_envia_el_campo(self):
        self.assertIn('Api.get("/api/servicios-generales")', self.js)
        self.assertIn("Servicios.armar(", self.js)
        self.assertIn("Servicios.chequeosDe(", self.js)
        self.assertRegex(self.js, r"servicio\s*[:=]\s*\w+\.servicio\b")

    def test_js_maneja_el_catalogo_caido_y_el_422_del_servicio(self):
        self.assertIn("No se pudo cargar la lista de servicios generales.", self.js)
        self.assertRegex(self.js, r"El servicio general '")
        self.assertIn("El campo servicio debe ser texto.", self.js)
        self.assertIn("recargarServicios", self.js)

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)
        self.assertNotIn("innerHTML", leer("js", "servicios.js"))

    def test_css_del_bloque_incluye_con_tokens(self):
        css = leer("css", "app.css")
        self.assertRegex(css, r"\.srv-incluye\s*\{[^}]*var\(--color-")


class OrdenesServicioTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "ordenes.js")
        self.css = leer("css", "app.css")

    def test_fila_de_servicio_solo_si_hay_servicio_y_antes_de_procesos(self):
        self.assertRegex(self.js, r"if\s*\(\s*o\.servicio\s*\)")
        self.assertIn("Servicio general:", self.js)
        self.assertIn('"srv-nombre"', self.js)
        self.assertLess(self.js.index("o.servicio"), self.js.index("Servicios adicionales:"))

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)

    def test_exportar_no_cambia_titulo_ni_linea(self):
        self.assertIn('titulo: "Orden " + o.numero', self.js)
        self.assertIn('linea: "Fecha: " + o.fecha + " · " + n', self.js)


class PdfDeUnaOrdenTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "ordenes.js")
        self.css = leer("css", "app.css")
        self.impresion = self.css[self.css.rindex("@media print"):]

    def test_etiqueta_de_impresion_servicio_general(self):
        self.assertRegex(self.js, r'"lbl-print"[^)]*"Servicio general"')

    def test_bloque_de_servicio_va_antes_que_la_tabla_y_procesos_despues(self):
        self.assertRegex(self.impresion, r"\.chips-srv\s*\{[^}]*order\s*:\s*0")
        self.assertRegex(self.impresion, r"\.chips\s*\{[^}]*order\s*:\s*2")

    def test_nombre_y_chequeos_uno_por_linea_sin_fondo_de_chip(self):
        self.assertIn(".srv-nombre", self.impresion)
        self.assertRegex(self.impresion, r"\.chips ul\s*\{[^}]*display\s*:\s*block")

    def test_el_dom_pone_servicio_antes_de_la_tabla_de_componentes(self):
        self.assertLess(self.js.index("o.servicio"), self.js.index('"overflow-x-auto"'))

    def test_cabecera_con_el_boton_de_servicios_no_sale_en_papel(self):
        html = leer("ordenes.html")
        self.assertRegex(html, r'<div class="page-head no-print">')
        self.assertRegex(html, r'aria-haspopup="dialog"[^>]*>Servicios generales</button>')


if __name__ == "__main__":
    unittest.main()
