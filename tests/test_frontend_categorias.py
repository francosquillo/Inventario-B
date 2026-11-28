"""Guardas estaticas de la categoria en el frontend (C-06e, grupos 7 a 11). No ejecutan JS:
fijan la estructura aprobada en los mockups y las reglas de seguridad (sin innerHTML)."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


def seccion(texto, desde, hasta):
    """Fragmento entre dos marcas (la primera aparicion de cada una)."""
    i = texto.index(desde)
    return texto[i:texto.index(hasta, i)]


class InventarioCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.js = leer("js", "inventario.js") + leer("js", "orden-form.js")  # C-06i: el formulario de orden vive en orden-form.js

    def test_columna_categoria_entre_nombre_y_stock(self):
        self.assertRegex(
            self.html,
            r'<th scope="col">Nombre</th><th scope="col" class="cat-col">Categor.a</th>'
            r'<th scope="col" class="r">Stock</th>',
        )

    def test_filtro_con_etiqueta_accesible(self):
        self.assertRegex(self.html, r'<label class="sr-only" for="inv-categoria">Categor.a</label>')
        self.assertIn('<select class="field" id="inv-categoria"', self.html)

    def test_limpiar_filtros(self):
        self.assertRegex(self.html, r'id="inv-limpiar"[^>]*>Limpiar filtros</button>')
        self.assertNotIn("Limpiar búsqueda", self.html)

    def test_js_carga_el_catalogo_y_filtra_con_categoria(self):
        self.assertIn("/api/categorias", self.js)
        self.assertRegex(self.js, r"Busqueda\.filtrar\(productos, texto, categoriaElegida\(\)\)")
        self.assertIn("Busqueda.mensajeSinCoincidencias(", self.js)
        self.assertIn("cat-inline", self.js)
        self.assertIn("cat-col", self.js)

    def test_busqueda_js_cargado_en_el_inventario(self):
        self.assertIn("/static/js/busqueda.js", self.html)


class NuevoIngresoCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.js = leer("js", "inventario.js") + leer("js", "orden-form.js")  # C-06i: el formulario de orden vive en orden-form.js

    def test_selector_despues_de_stock_con_sin_categoria(self):
        modal = seccion(self.html, 'id="modal-nuevo"', 'id="modal-modificar"')
        self.assertRegex(modal, r'<label class="label" for="nu-categoria">Categor.a ')
        self.assertIn('<select class="field" id="nu-categoria"', modal)
        self.assertLess(modal.index('id="nu-stock"'), modal.index('id="nu-categoria"'))

    def test_aviso_de_baja_menciona_la_categoria(self):
        self.assertIn(
            "con el nombre, el stock y la categoría que indiques.", self.html
        )

    def test_el_cuerpo_incluye_la_categoria(self):
        cuerpo = seccion(self.js, "function enviarNuevo", "const restaurar")
        self.assertRegex(cuerpo, r"categoria:")

    def test_no_precarga_la_categoria_del_dado_de_baja(self):
        aviso = seccion(self.js, "function avisoCodigoDeBaja", "function abrirNuevo")
        self.assertNotIn("categoria", aviso)


class ModificarCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.js = leer("js", "inventario.js") + leer("js", "orden-form.js")  # C-06i: el formulario de orden vive en orden-form.js

    def test_plantilla_con_selector_etiquetado(self):
        plantilla = seccion(self.html, 'id="tpl-mline"', "</template>")
        self.assertRegex(plantilla, r"<select[^>]*data-categoria")
        self.assertRegex(plantilla, r'data-categoria-etiqueta[^>]*>Categor.a<')
        self.assertIn("mline-two", plantilla)

    def test_cada_linea_envia_la_categoria_y_el_resumen_la_muestra(self):
        self.assertRegex(self.js, r"linea\.categoria = ")
        self.assertIn("categoría: ", self.js)

    def test_precarga_desde_el_producto_elegido(self):
        self.assertIn("categoria_anterior", self.js)
        self.assertRegex(self.js, r"info\.p\.categoria")


class NuevaOrdenCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "inventario.js") + leer("js", "orden-form.js")  # C-06i: el formulario de orden vive en orden-form.js

    def test_la_linea_tiene_selector_de_categoria_antes_del_producto(self):
        nueva = seccion(self.js, "function nuevaLinea(", "function agregarLinea")
        self.assertIn("data-cat", nueva)
        self.assertLess(nueva.index("data-cat"), nueva.index('"data-opts"'))
        self.assertIn("No hay productos en esta categoría.", self.js)

    def test_etiqueta_de_cada_selector_de_categoria(self):
        self.assertIn('"Categoría de la línea " + n', self.js)

    def test_el_cuerpo_de_la_orden_no_incluye_categoria(self):
        cuerpo = seccion(self.js, "function enviarOrden", "const restaurar")
        self.assertNotIn("categoria", cuerpo)

    def test_los_selectores_de_producto_ya_no_se_buscan_como_el_primer_select(self):
        self.assertNotIn('li.querySelector("select")', self.js)


class PdfInventarioCategoriaTest(unittest.TestCase):
    def test_la_linea_del_pdf_usa_la_categoria_elegida(self):
        js = leer("js", "inventario.js") + leer("js", "orden-form.js")  # C-06i: el formulario de orden vive en orden-form.js
        exportar = seccion(js, "function exportarInventario", "function etiquetaProducto")
        self.assertIn("Busqueda.lineaInventario(", exportar)

    def test_hoja_de_impresion_con_la_columna_categoria(self):
        css = leer("css", "app.css")
        self.assertIn(".tbl .cat-col { display:table-cell !important", css)
        self.assertIn(".tbl .cat-inline { display:none !important", css)


class ReportesCategoriaTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("reportes.html")
        self.js = leer("js", "reportes.js")

    def test_columna_entre_nombre_y_cantidad(self):
        self.assertRegex(
            self.html,
            r'<th scope="col">Nombre</th><th scope="col" class="cat-col">Categor.a</th>'
            r'<th scope="col" class="r">Cantidad</th>',
        )

    def test_sin_filtro_de_categoria(self):
        self.assertNotRegex(self.html, r'<select[^>]*categor')
        self.assertNotIn("categoria", seccion(self.js, "function parametros", "// Hasta vacio"))

    def test_el_js_pide_el_catalogo_y_tolera_el_fallo(self):
        self.assertIn("/api/categorias", self.js)
        self.assertIn("Busqueda.nombreCategoria(", self.js)
        self.assertIn("/static/js/busqueda.js", self.html)


class CssCategoriaTest(unittest.TestCase):
    def test_piezas_nuevas_en_app_css_y_no_en_ui_css(self):
        app = leer("css", "app.css")
        for pieza in (".cat-col", ".cat-inline", ".inv-filtros", ".mline-two", ".line-help", ".cat-none"):
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, app)
        self.assertNotIn("cat-col", leer("css", "ui.css"))


if __name__ == "__main__":
    unittest.main()
