"""Guardas estaticas de C-06i: formulario de orden compartido (orden-form.js), modal "Editar orden",
chequeo final en /ordenes y en el PDF. No ejecutan JS: fijan la estructura de los mockups L1, E1, E2 y
P1 aprobados y las reglas de seguridad (sin innerHTML, datos solo con textContent/createElement)."""
import re
import unittest
from pathlib import Path

from inventario.domain.chequeo_final import CHEQUEO_FINAL

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


def orden_de(html, *scripts):
    posiciones = [html.index(f"/static/js/{s}") for s in scripts]
    return posiciones == sorted(posiciones)


class FormularioCompartidoTest(unittest.TestCase):
    def setUp(self):
        self.form = leer("js", "orden-form.js")
        self.inventario = leer("js", "inventario.js")
        self.index = leer("index.html")

    def test_orden_form_expone_window_ordenform_sin_tocar_el_dom_al_cargar(self):
        self.assertIn("window.OrdenForm", self.form)
        self.assertNotRegex(self.form, r"(?m)^(?:document\.|window\.addEventListener)")
        # El DOM solo se toca dentro de `montar` (funciones), nunca al cargar el archivo.
        self.assertNotRegex(self.form, r"(?m)^  (?:const|let|var) \w+ = (?:document|\$)\(")

    def test_index_carga_orden_form_antes_de_inventario_y_tras_sus_dependencias(self):
        for dependencia in (
            "validacion.js", "api.js", "ui.js", "busqueda.js", "precios.js", "datos-orden.js",
            "procesos.js", "servicios.js",
        ):
            with self.subTest(dependencia=dependencia):
                self.assertTrue(orden_de(self.index, dependencia, "orden-form.js", "inventario.js"))

    def test_inventario_js_ya_no_define_la_logica_del_formulario_de_orden(self):
        for resto in (
            "function nuevaLineaProceso", "function enviarOrden", "function mapearErrorOrden",
            "function leerProcesos", "function llenarSelectServicio", "function actualizarResumen",
            "function validarOrden", 'Api.post("/api/ordenes"',
        ):
            with self.subTest(resto=resto):
                self.assertNotIn(resto, self.inventario)
        self.assertIn("OrdenForm.montar(", self.inventario)

    def test_orden_form_tiene_la_logica_movida_y_no_usa_innerhtml(self):
        for presente in (
            "function nuevaLineaProceso", "function enviarOrden", "function mapearErrorOrden",
            "function validarOrden", "Precios.resumen", "Servicios.armar", "DatosOrden.validar",
        ):
            with self.subTest(presente=presente):
                self.assertIn(presente, self.form)
        self.assertNotIn("innerHTML", self.form)
        self.assertNotIn("innerHTML", self.inventario)


class ModalEditarTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("ordenes.html")
        self.js = leer("js", "ordenes.js")
        self.css = leer("css", "app.css")

    def test_estructura_del_modal_e1(self):
        for fragmento in (
            'id="modal-editar"', 'role="dialog"', 'aria-modal="true"', 'id="form-editar"',
            'id="ord-titulo-num"', 'id="ord-numero-fijo"', 'id="ord-chequeo"', "Chequeo final",
            "Guardar cambios", 'id="ord-enviar"', 'id="ord-alerta"',
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.html)

    def test_sin_columna_de_categoria_y_sin_campo_de_numero(self):
        modal = self.html[self.html.index('id="modal-editar"'):]
        self.assertNotIn(">Categoría<", modal)
        self.assertNotIn('id="ord-numero"', modal)

    def test_scripts_antes_de_ordenes_js(self):
        for dep in (
            "precios.js", "datos-orden.js", "procesos.js", "servicios.js", "busqueda.js",
            "chequeo-final.js", "orden-form.js",
        ):
            with self.subTest(dep=dep):
                self.assertTrue(orden_de(self.html, "validacion.js", "api.js", "ui.js", dep, "ordenes.js"))

    def test_boton_editar_accesible_y_fuera_del_papel(self):
        self.assertIn("data-editar", self.js)
        self.assertRegex(self.js, r'"Editar orden " \+ o\.numero')
        self.assertRegex(self.js, r'"class": "btn btn-secondary btn-sm[^"]*no-print')

    def test_monta_el_formulario_compartido_en_modo_editar(self):
        self.assertIn("OrdenForm.montar(", self.js)
        self.assertIn('modo: "editar"', self.js)
        self.assertIn("/api/productos/inactivos", self.js)
        self.assertIn("/api/inventario", self.js)
        self.assertNotIn("innerHTML", self.js)

    def test_aviso_de_ajustes(self):
        for texto in ("actualizada.", "descontada", "devuelta", "reactivado", "Sin cambios de stock."):
            with self.subTest(texto=texto):
                self.assertIn(texto, self.js)

    def test_orden_form_envia_put_codificado_y_el_chequeo(self):
        form = leer("js", "orden-form.js")
        self.assertIn('Api.put("/api/ordenes/" + encodeURIComponent(', form)
        self.assertIn("chequeo_final", form)
        self.assertIn("conservar_servicio", form)
        self.assertIn("Importe de ", form)

    def test_css_nuevo_solo_en_app_css(self):
        for clase in (".chk-row", ".line-sc", ".alert-danger", ".ajustes", ".chk-print"):
            with self.subTest(clase=clase):
                self.assertIn(clase, self.css)


class ChequeoEnPantallaYPdfTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "ordenes.js")
        self.css = leer("css", "app.css")

    def test_fila_en_pantalla_solo_si_hay_items_despues_de_adicionales(self):
        self.assertIn("Chequeo final:", self.js)
        self.assertRegex(self.js, r"o\.chequeo_final")
        self.assertLess(self.js.index("Servicios adicionales:"), self.js.index("Chequeo final:"))
        self.assertIn("chips-chk", self.js)

    def test_hoja_impresa_lista_los_seis_items_con_marca_de_texto(self):
        self.assertIn("ChequeoFinal.ITEMS", self.js)
        for texto in ("[✓]", "Hecho", "No se hizo", "chk-print"):
            with self.subTest(texto=texto):
                self.assertIn(texto, self.js)
        self.assertRegex(self.js, r"\[(?:\\u00a0|\s){2}\]")

    def test_la_marca_no_depende_solo_del_color_y_el_resumen_viene_de_la_api(self):
        self.assertIn("o.subtotal_servicios", self.js)
        self.assertNotIn("Precios.resumen", self.js)

    def test_ordenes_html_carga_chequeo_final_js(self):
        html = leer("ordenes.html")
        self.assertIn("/static/js/chequeo-final.js", html)

    def test_ids_de_chequeo_final_son_los_de_la_lista_fija(self):
        js = leer("js", "chequeo-final.js")
        for clave, nombre in CHEQUEO_FINAL:
            with self.subTest(clave=clave):
                self.assertIn(f'clave: "{clave}"', js)
                self.assertIn(f'nombre: "{nombre}"', js)
