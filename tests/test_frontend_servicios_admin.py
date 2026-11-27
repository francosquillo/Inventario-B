"""Guardas estaticas de la administracion del catalogo de servicios generales en /ordenes
(C-06g, grupo 8b). No ejecutan JS: fijan la estructura aprobada en los mockups (C1, C2)."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


class ModalHtmlTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("ordenes.html")

    def test_boton_junto_al_titulo_no_sale_en_papel(self):
        self.assertRegex(self.html, r'<div class="page-head no-print">')
        self.assertRegex(self.html, r'id="btn-servicios"[^>]*aria-haspopup="dialog"[^>]*>Servicios generales</button>')
        self.assertLess(self.html.index("<h1"), self.html.index('id="btn-servicios"'))

    def test_modal_con_las_tres_vistas(self):
        self.assertIn('id="modal-servicios"', self.html)
        for vista in ("srv-vista-lista", "srv-vista-form", "srv-vista-borrar"):
            with self.subTest(vista=vista):
                self.assertIn(f'id="{vista}"', self.html)

    def test_vista_lista_con_nuevo_estados_y_reintentar(self):
        self.assertRegex(self.html, r'id="srv-nuevo"[^>]*>Nuevo servicio</button>')
        self.assertIn("No hay servicios generales.", self.html)
        self.assertRegex(self.html, r'id="srv-reintentar"[^>]*>Reintentar</button>')
        self.assertRegex(self.html, r'id="srv-exito"[^>]*role="status"')

    def test_vista_formulario_con_nombre_chequeos_agregar_volver_guardar(self):
        self.assertRegex(self.html, r'<label class="label" for="srv-nombre">Nombre</label>')
        self.assertRegex(self.html, r'id="srv-nombre"[^>]*maxlength="60"')
        self.assertIn('<legend class="label">Chequeos</legend>', self.html)
        self.assertRegex(self.html, r'<ol id="srv-chequeos" class="clist"')
        self.assertRegex(self.html, r'id="srv-agregar"[^>]*>Agregar chequeo</button>')
        self.assertRegex(self.html, r'id="srv-volver"[^>]*>Volver</button>')
        self.assertRegex(self.html, r'id="srv-guardar"[^>]*>Guardar</button>')
        self.assertIn("Se copian en este orden a cada orden nueva con este servicio.", self.html)

    def test_confirmacion_de_borrado_con_boton_peligro(self):
        self.assertRegex(self.html, r'id="srv-eliminar-confirmar"[^>]*class="btn btn-danger"[^>]*>Eliminar servicio</button>|class="btn btn-danger"[^>]*id="srv-eliminar-confirmar"[^>]*>Eliminar servicio</button>')
        self.assertRegex(self.html, r'id="srv-eliminar-cancelar"[^>]*>Cancelar</button>')

    def test_titulos_enfocables_de_cada_vista(self):
        for titulo in ("srv-titulo-lista", "srv-titulo-form", "srv-titulo-borrar"):
            with self.subTest(titulo=titulo):
                self.assertRegex(self.html, rf'id="{titulo}"[^>]*tabindex="-1"')

    def test_carga_servicios_js_y_servicios_admin_js(self):
        self.assertIn("/static/js/servicios.js", self.html)
        a = self.html.index("/static/js/servicios-admin.js")
        self.assertLess(self.html.index("/static/js/servicios.js"), a)


class AdminJsTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "servicios-admin.js")

    def test_usa_los_cuatro_metodos_de_la_api(self):
        self.assertIn('"/api/servicios-generales"', self.js)
        self.assertIn("Api.get(", self.js)
        self.assertIn("Api.post(", self.js)
        self.assertIn('Api.pedir("PATCH"', self.js)
        self.assertIn("Api.borrar(", self.js)

    def test_valida_con_el_modulo_puro(self):
        self.assertIn("Servicios.validarFormulario(", self.js)

    def test_envia_nombre_y_chequeos(self):
        self.assertRegex(self.js, r"nombre\s*:\s*\w+\.nombre")
        self.assertRegex(self.js, r"chequeos\s*:\s*\w+\.chequeos")

    def test_mensajes_de_exito_y_de_borrado(self):
        self.assertIn("guardado.", self.js)
        self.assertIn("eliminado.", self.js)
        self.assertIn("Las órdenes que ya lo tienen lo conservan.", self.js)

    def test_accesibilidad_de_los_errores_por_campo(self):
        self.assertIn("aria-invalid", self.js)
        self.assertIn("aria-describedby", self.js)

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)

    def test_mapea_409_422_y_404(self):
        self.assertRegex(self.js, r"status\s*===\s*409")
        self.assertRegex(self.js, r"status\s*===\s*404")
        self.assertRegex(self.js, r"Chequeo \(\\d\+\)")

    def test_tope_de_chequeos_y_quitar_deshabilitado_con_uno(self):
        self.assertIn("Servicios.CHEQUEOS_MAX", self.js)
        self.assertRegex(self.js, r"disabled\s*=")


class CssAdminTest(unittest.TestCase):
    def test_piezas_del_mockup_en_app_css_con_tokens(self):
        css = leer("css", "app.css")
        for clase in (".srv-card", ".srv-list", ".cline", ".clist", ".page-head", ".srv-incluye"):
            with self.subTest(clase=clase):
                self.assertIn(clase, css)
        self.assertRegex(css, r"\.srv-card \+ \.srv-card\s*\{[^}]*var\(--color-border\)")

    def test_tokens_y_ui_css_intactos(self):
        # ui.css y tokens.css no llevan piezas de C-06g (viven en app.css).
        for archivo in ("tokens.css", "ui.css"):
            with self.subTest(archivo=archivo):
                texto = leer("css", archivo)
                for clase in (".srv-", ".cline", ".clist"):
                    self.assertNotIn(clase, texto)


if __name__ == "__main__":
    unittest.main()
