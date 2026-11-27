"""Guardas estaticas del filtro por categoria de "Modificar stock" (C-06h2, grupos 3 a 5).
No ejecutan JS: fijan la estructura aprobada en los mockups y las reglas de seguridad."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


def seccion(texto, desde, hasta):
    i = texto.index(desde)
    return texto[i:texto.index(hasta, i)]


class PlantillaFiltroTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.css = leer("css", "app.css")
        self.plantilla = seccion(self.html, 'id="tpl-mline"', "</template>")

    def test_filtro_antes_del_producto_en_la_cabecera(self):
        cabecera = seccion(self.plantilla, 'class="mline-head"', 'class="mline-body"')
        i_filtro = cabecera.index("data-filtro")
        i_producto = cabecera.index("data-producto")
        self.assertLess(i_filtro, i_producto)
        self.assertRegex(cabecera, r"<select[^>]*data-filtro")

    def test_etiquetas_visibles_distintas(self):
        self.assertRegex(self.plantilla, r'data-filtro-etiqueta[^>]*>Filtrar por categor.a<')
        self.assertRegex(self.plantilla, r'data-producto-etiqueta[^>]*>Producto<')

    def test_selector_categoria_del_producto_sigue_abajo(self):
        dos = seccion(self.plantilla, 'class="mline-two"', "</li>")
        self.assertRegex(dos, r'data-categoria-etiqueta[^>]*>Categor.a<')
        self.assertRegex(dos, r"<select[^>]*data-categoria")
        self.assertNotIn("data-filtro", dos)

    def test_sin_innerhtml_en_la_plantilla(self):
        self.assertNotIn("innerHTML", self.plantilla)

    def test_css_grilla_de_la_cabecera_con_columna_del_filtro(self):
        self.assertRegex(self.css, r"\.mline-head\s*\{[^}]*12rem")
        self.assertRegex(self.css, r"@media \(max-width: 639\.98px\)[^@]*\.mline-head[^}]*grid-template-areas")

    def test_modal_modificar_mide_44rem(self):
        modal = seccion(self.html, 'id="modal-modificar"', "</div>")
        self.assertIn("max-width:44rem", modal)
        self.assertNotIn("40rem", modal)


class LogicaFiltroTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "inventario.js")
        self.llenar = seccion(self.js, "function llenarSelectMod(", "function refrescarSelectsMod")
        self.alcambiar = seccion(self.js, "function alCambiarLineaMod(", "function actualizarLineaMod")

    def test_llenar_select_filtra_ambos_grupos(self):
        self.assertIn("Busqueda.porCategoria(productos, categoria)", self.llenar)
        self.assertIn("Busqueda.porCategoria(inactivos, categoria)", self.llenar)
        self.assertIn("Busqueda.productoSigueVisible(", self.llenar)
        self.assertIn("productos.concat(inactivos)", self.llenar)

    def test_ya_no_existe_sigue_con_conservar(self):
        self.assertIn("(ya no existe)", self.llenar)
        self.assertIn("conservar", self.llenar)

    def test_nueva_linea_llena_el_filtro(self):
        nueva = seccion(self.js, "function nuevaLineaMod(", "function agregarLineaMod")
        self.assertIn('select[data-filtro]', nueva)
        self.assertIn('"Todas las categorías", true', nueva)

    def test_recarga_de_catalogo_incluye_el_filtro(self):
        sel = seccion(self.js, "function llenarSelectoresCategoria(", "function cargarCategorias")
        self.assertIn("#mod-lineas select[data-filtro]", sel)
        self.assertIn('"Todas las categorías", true', sel)

    def test_rama_del_filtro_en_el_cambio(self):
        self.assertIn('select[data-filtro]', self.alcambiar)

    def test_reseteo_antes_de_refrescar(self):
        rama = seccion(self.alcambiar, 'select[data-filtro]', "} else if")
        self.assertLess(rama.index("productoSigueVisible"), rama.index("refrescarSelectsMod("))

    def test_reseteo_comparte_camino_con_elegir_sin_producto(self):
        self.assertIn("function aplicarProductoMod(", self.js)
        self.assertGreaterEqual(self.alcambiar.count("aplicarProductoMod("), 2)

    def test_ayuda_de_lista_vacia_con_constante_compartida(self):
        self.assertEqual(self.js.count("No hay productos en esta categoría."), 1)
        self.assertIn("AYUDA_SIN_PRODUCTOS", self.js)
        self.assertIn("function actualizarAyudaMod(", self.js)
        cuerpo = self.js[self.js.index("function actualizarAyudaMod("):]
        cuerpo = cuerpo[:cuerpo.index("\n  }\n")]
        self.assertIn("mod-", cuerpo)
        self.assertIn("-vacio", cuerpo)
        self.assertIn("aria-describedby", cuerpo)
        self.assertIn("removeAttribute", cuerpo)
        self.assertIn("remove()", cuerpo)

    def test_refrescar_llama_a_la_ayuda(self):
        refr = seccion(self.js, "function refrescarSelectsMod(", "function renumerarMod")
        self.assertIn("actualizarAyudaMod", refr)

    def test_un_solo_filtrado_sin_filter_manual_por_categoria(self):
        self.assertNotRegex(self.js, r"\.filter\([^)]*categoria")

    def test_sin_innerhtml(self):
        self.assertNotIn("innerHTML", self.js)


class AccesibilidadYCuerpoTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "inventario.js")

    def test_renumerar_etiqueta_filtro_y_producto(self):
        ren = seccion(self.js, "function renumerarMod(", "function nuevaLineaMod")
        self.assertIn('"Filtrar por categoría, línea " + n', ren)
        self.assertIn('"Producto de la línea " + n', ren)
        self.assertIn('"Categoría de la línea " + n', ren)
        self.assertIn('"-fil"', ren)
        self.assertIn('"-prod"', ren)
        self.assertIn("[data-filtro-etiqueta]", ren)
        self.assertIn("[data-producto-etiqueta]", ren)

    def test_leer_lineas_no_lee_el_filtro(self):
        leer_ = seccion(self.js, "function leerLineasMod(", "function ocultarGeneralMod")
        self.assertNotIn("data-filtro", leer_)
        claves = re.findall(r"^\s+(\w+): ", leer_, re.M)
        self.assertEqual(claves, ["codigo", "modo", "valor", "nombre", "categoria"])


if __name__ == "__main__":
    unittest.main()
