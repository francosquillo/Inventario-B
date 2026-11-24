"""Guardas estaticas del frontend (C-06, design D8). No ejecutan JS: fijan reglas de
seguridad y de coherencia con el design system sobre los archivos de static/."""
import re
import unittest
from pathlib import Path

from tests.helpers import cliente_de_test

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"
DESIGN = RAIZ / "design-system"
PAGINAS = ("login.html", "index.html", "ordenes.html", "reportes.html")

PROHIBIDOS_JS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(")
PALETA_TAILWIND = re.compile(
    r"\b(?:bg|text|border|ring|divide|from|to|via|fill|stroke|outline|decoration|placeholder)"
    r"-(?:gray|slate|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan"
    r"|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b"
    r"|\b(?:bg|text|border)-(?:white|black)\b"
)
ATRIBUTO_LOCAL = re.compile(r'(?:src|href)="(/[^"/][^"]*)"')


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


class CopiasDelDesignSystemTest(unittest.TestCase):
    def test_css_identico_al_design_system(self):
        for nombre in ("tokens.css", "ui.css"):
            with self.subTest(nombre=nombre):
                self.assertEqual(
                    (STATIC / "css" / nombre).read_bytes(),
                    (DESIGN / nombre).read_bytes(),
                )


class PaginasTest(unittest.TestCase):
    def test_estructura_comun(self):
        for nombre in PAGINAS:
            html = leer(STATIC / nombre)
            with self.subTest(pagina=nombre):
                self.assertIn('<html lang="es">', html)
                self.assertIn('<meta name="viewport"', html)
                self.assertIn("/static/css/tokens.css", html)
                self.assertIn("/static/css/ui.css", html)
                self.assertIn("/static/js/tailwind-config.js", html)
                self.assertRegex(html, r"https://cdn\.tailwindcss\.com/3\.4\.\d+\"")

    def test_tailwind_con_version_exacta_en_todas(self):
        for nombre in PAGINAS:
            with self.subTest(pagina=nombre):
                self.assertNotRegex(leer(STATIC / nombre), r"cdn\.tailwindcss\.com/?\"")

    def test_recursos_locales_responden_200(self):
        client, _ = cliente_de_test(self.addCleanup)
        for nombre in PAGINAS:
            for ruta in ATRIBUTO_LOCAL.findall(leer(STATIC / nombre)):
                with self.subTest(pagina=nombre, ruta=ruta):
                    if ruta in ("/", "/inventario", "/ordenes", "/reportes"):
                        continue  # paginas: dependen de la sesion
                    self.assertEqual(client.get(ruta).status_code, 200)

    def test_tailwind_config_cargado_antes_de_los_scripts_de_la_pagina(self):
        for nombre in PAGINAS:
            html = leer(STATIC / nombre)
            with self.subTest(pagina=nombre):
                self.assertLess(
                    html.index("cdn.tailwindcss.com"), html.index("tailwind-config.js")
                )

    def test_sin_clases_de_la_paleta_de_tailwind(self):
        for nombre in PAGINAS:
            with self.subTest(pagina=nombre):
                self.assertEqual(PALETA_TAILWIND.findall(leer(STATIC / nombre)), [])

    def test_hidden_gana_a_las_utilidades_de_display(self):
        # Hallazgo del verify: `class="flex" hidden` se veia igual (Tailwind pisa [hidden]).
        css = leer(STATIC / "css" / "app.css")
        self.assertRegex(css, r"\[hidden\]\s*\{\s*display:\s*none\s*!important")
        for nombre in PAGINAS:
            self.assertIn("/static/css/app.css", leer(STATIC / nombre))

    def test_el_detector_de_paleta_detecta(self):
        # Triangulacion de la guarda: debe saltar ante clases prohibidas y no ante tokens.
        self.assertTrue(PALETA_TAILWIND.search('class="bg-gray-100"'))
        self.assertTrue(PALETA_TAILWIND.search('class="text-red-600 p-2"'))
        self.assertTrue(PALETA_TAILWIND.search('class="bg-white"'))
        self.assertFalse(PALETA_TAILWIND.search('class="bg-surface text-accent-text border-line"'))


class JavaScriptTest(unittest.TestCase):
    def test_hay_scripts(self):
        nombres = {p.name for p in (STATIC / "js").glob("*.js")}
        for esperado in ("tailwind-config.js", "validacion.js", "api.js", "ui.js", "sesion.js"):
            self.assertIn(esperado, nombres)

    def test_sin_apis_que_interpretan_html(self):
        for js in sorted((STATIC / "js").glob("*.js")):
            codigo = leer(js)
            for prohibido in PROHIBIDOS_JS:
                with self.subTest(archivo=js.name, prohibido=prohibido):
                    self.assertNotIn(prohibido, codigo)


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.html = leer(STATIC / "login.html")

    def test_contrasena_oculta_con_autocomplete(self):
        campo = re.search(r'<input[^>]*id="password"[^>]*>', self.html).group(0)
        self.assertIn('type="password"', campo)
        self.assertIn('autocomplete="current-password"', campo)

    def test_boton_mostrar_asociado_a_la_contrasena(self):
        self.assertRegex(self.html, r'<button[^>]*data-toggle="password"[^>]*>Mostrar</button>')

    def test_usuario_con_autocomplete_y_limites(self):
        campo = re.search(r'<input[^>]*id="username"[^>]*>', self.html).group(0)
        self.assertIn('autocomplete="username"', campo)
        self.assertIn('maxlength="64"', campo)

    def test_aviso_de_sesion_expirada_oculto_por_defecto(self):
        aviso = re.search(r'<div[^>]*id="aviso-expirada"[^>]*>[^<]*</div>', self.html).group(0)
        self.assertIn("hidden", aviso)
        self.assertIn("Tu sesión expiró. Ingresá de nuevo.", aviso)

    def test_formulario_sin_envio_nativo(self):
        form = re.search(r"<form[^>]*>", self.html).group(0)
        self.assertIn("novalidate", form)
        self.assertNotIn("action=", form)

    def test_login_js_implementa_el_flujo(self):
        js = leer(STATIC / "js" / "login.js")
        for fragmento in ("/api/login", "/inventario", "sesion", "Ingresando…", "Validacion.requerido"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, js)


def ids_de(html):
    return set(re.findall(r'\bid="([^"]+)"', html))


class CamposEtiquetadosMixin:
    """Spec 'Etiquetas': todo campo estatico tiene <label for> o aria-label."""

    def comprobar_etiquetas(self, html):
        etiquetados = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
        for campo in re.findall(r"<(?:input|select|textarea)\b[^>]*>", html):
            if 'type="hidden"' in campo:
                continue
            with self.subTest(campo=campo[:60]):
                ident = re.search(r'\bid="([^"]+)"', campo)
                self.assertTrue(
                    "aria-label=" in campo or (ident and ident.group(1) in etiquetados),
                    "campo sin etiqueta: " + campo,
                )

    def comprobar_modales(self, html, esperados):
        ids = ids_de(html)
        for modal in esperados:
            with self.subTest(modal=modal):
                m = re.search(r'<div[^>]*id="%s"[^>]*>' % modal, html)
                self.assertIsNotNone(m, "falta el modal " + modal)
                self.assertIn('class="overlay"', m.group(0))
                self.assertIn("hidden", m.group(0))
                bloque = html[m.end(): m.end() + 400]
                dialogo = re.search(r'<div[^>]*role="(?:dialog|alertdialog)"[^>]*>', bloque).group(0)
                self.assertIn('aria-modal="true"', dialogo)
                self.assertIn(re.search(r'aria-labelledby="([^"]+)"', dialogo).group(1), ids)


class InventarioPaginaTest(CamposEtiquetadosMixin, unittest.TestCase):
    def setUp(self):
        self.html = leer(STATIC / "index.html")
        self.js = leer(STATIC / "js" / "inventario.js")

    def test_cabecera_y_acciones(self):
        for texto in ("Cerrar sesión", "Usuario:", "Nuevo ingreso", "Modificar stock",
                      "Nueva orden", "Ver órdenes", 'href="/ordenes"'):
            with self.subTest(texto=texto):
                self.assertIn(texto, self.html)
        for ident in ("btn-nuevo", "btn-modificar"):
            self.assertIn('id="%s"' % ident, self.html)

    def test_sin_los_modales_viejos_de_ingreso_y_egreso(self):
        for viejo in ("Ingreso de stock", "Egreso de stock", "modal-ingreso", "modal-egreso",
                      "btn-ingreso", "btn-egreso"):
            with self.subTest(viejo=viejo):
                self.assertNotIn(viejo, self.html)

    def test_estados_de_la_lista(self):
        for ident in ("inv-cargando", "inv-error", "inv-reintentar", "inv-vacio", "inv-conteo",
                      "inv-cuerpo", "aviso-exito"):
            with self.subTest(ident=ident):
                self.assertIn('id="%s"' % ident, self.html)
        self.assertIn("Todavía no hay productos", self.html)
        self.assertIn("Cargando inventario…", self.html)

    def test_cartel_vacio_indica_crear_con_nuevo_ingreso(self):
        self.assertIn("Creá el primero con Nuevo ingreso.", self.html)
        self.assertNotIn("Registrá un ingreso", self.html)

    def test_cuatro_modales_accesibles(self):
        self.comprobar_modales(self.html, ("modal-nuevo", "modal-modificar", "modal-orden", "modal-baja"))

    def test_modal_nuevo_ingreso_pide_codigo_nombre_y_stock(self):
        for ident, etiqueta in (("nu-codigo", "Código"), ("nu-nombre", "Nombre"), ("nu-stock", "Stock")):
            with self.subTest(ident=ident):
                self.assertRegex(self.html, r'<label[^>]*for="%s"[^>]*>%s</label>' % (ident, etiqueta))
                self.assertIn('id="%s"' % ident, self.html)
        stock = re.search(r'<input[^>]*id="nu-stock"[^>]*>', self.html).group(0)
        self.assertIn('inputmode="numeric"', stock)
        self.assertRegex(self.html, r'id="nu-enviar"[^>]*>Crear producto<')
        self.assertIn("Este código está dado de baja: se va a reactivar con el nombre, el stock y la categoría que indiques.", self.html)

    def test_modal_modificar_stock_y_plantilla_de_linea(self):
        self.assertRegex(self.html, r'id="mod-enviar"[^>]*>Guardar cambios<')
        self.assertIn("Agregar producto", self.html)
        plantilla = re.search(r'<template id="tpl-mline">(.*?)</template>', self.html, re.S)
        self.assertIsNotNone(plantilla, "falta la plantilla de linea")
        cuerpo = plantilla.group(1)
        self.assertRegex(cuerpo, r'<fieldset[^>]*class="seg"')
        self.assertEqual(len(re.findall(r'type="radio"', cuerpo)), 2)
        self.assertIn("Fijar en", cuerpo)
        self.assertIn("Sumar", cuerpo)
        self.assertIn("Quitar", cuerpo)
        self.assertIn("Nuevo nombre (opcional)", cuerpo)

    def test_campos_con_etiqueta(self):
        self.comprobar_etiquetas(self.html)

    def test_el_aviso_de_codigo_dado_de_baja_no_bloquea_el_envio(self):
        self.assertNotRegex(self.html, r'id="nu-(?:codigo|nombre|stock)"[^>]*\b(?:required|disabled|readonly)\b')
        self.assertRegex(self.html, r'id="nu-aviso"[^>]*aria-live="polite"[^>]*hidden|id="nu-aviso"[^>]*hidden[^>]*aria-live="polite"')

    def test_js_usa_los_endpoints_y_codifica_codigos(self):
        for fragmento in ("/api/inventario", "/api/productos", "/api/productos/inactivos",
                          "/api/stock/modificaciones", "/api/ordenes", "encodeURIComponent"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        self.assertNotRegex(self.js, r"/api/productos/\$\{(?!encodeURIComponent)")

    def test_ningun_js_llama_a_los_endpoints_de_ingreso_y_egreso(self):
        for js in sorted((STATIC / "js").glob("*.js")):
            codigo = leer(js)
            for ruta in ("/api/stock/ingreso", "/api/stock/egreso"):
                with self.subTest(archivo=js.name, ruta=ruta):
                    self.assertNotIn(ruta, codigo)
        for html in PAGINAS:
            self.assertNotIn("/api/stock/ingreso", leer(STATIC / html))

    def test_js_ya_no_tiene_las_funciones_de_ingreso_y_egreso(self):
        for viejo in ("abrirIngreso", "enviarIngreso", "abrirEgreso", "enviarEgreso", "hintCodigoNuevo"):
            with self.subTest(viejo=viejo):
                self.assertNotIn(viejo, self.js)

    def test_js_valida_con_el_modulo_puro(self):
        for fragmento in ("Validacion.stock", "Validacion.requerido", "Validacion.componentes",
                          "Validacion.lineasModificacion", "Validacion.fecha", "Validacion.hoy"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)

    def test_resumen_y_avisos_dependen_de_reactivado_de_la_respuesta(self):
        for fragmento in ("reactivado", "se va a reactivar al guardar",
                          "sigue dado de baja (sin cambio de stock)", "sigue dado de baja (stock 0)",
                          "Stock modificado", "Este producto ya no existe: elegí otro o quitá la línea.",
                          "Guardando…", "optgroup", "codigos"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        # La marca "reactivado" del resumen sale solo de la respuesta de la API.
        self.assertRegex(self.js, r"l\.reactivado")
        # Los errores de modificacion llegan por linea ("Linea N:").
        self.assertRegex(self.js, r"\^L\S*nea \(\\d\+\)")


class ValidacionStaticaTest(unittest.TestCase):
    def test_validacion_js_expone_stock_y_lineas_de_modificacion(self):
        js = leer(STATIC / "js" / "validacion.js")
        for fragmento in ("stock:", "lineasModificacion:", "El stock debe ser un entero entre 0 y 10.000.",
                          "Elegí un producto.", "ya está en la línea"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, js)


class OrdenesPaginaTest(CamposEtiquetadosMixin, unittest.TestCase):
    def setUp(self):
        self.html = leer(STATIC / "ordenes.html")
        self.js = leer(STATIC / "js" / "ordenes.js")

    def test_enlace_de_regreso_y_filtros(self):
        self.assertIn("&larr; Inventario", self.html)
        self.assertIn('href="/inventario"', self.html)
        for ident in ("f-desde", "f-hasta", "f-numero"):
            with self.subTest(ident=ident):
                self.assertIn('id="%s"' % ident, self.html)
        for texto in ("Filtrar", "Ver todas"):
            self.assertIn(texto, self.html)

    def test_estados_de_la_lista(self):
        for ident in ("ord-cargando", "ord-error", "ord-reintentar", "ord-vacio", "ord-lista",
                      "ord-conteo", "aviso-exito", "filtros-alerta"):
            with self.subTest(ident=ident):
                self.assertIn('id="%s"' % ident, self.html)
        self.assertIn("Cargando órdenes…", self.html)

    def test_casilla_devolver_stock_marcada_por_defecto(self):
        casilla = re.search(r'<input[^>]*id="del-devolver"[^>]*>', self.html).group(0)
        self.assertIn('type="checkbox"', casilla)
        self.assertRegex(casilla, r"\bchecked\b")

    def test_boton_de_borrado_dice_devolver_por_defecto(self):
        boton = re.search(r'<button[^>]*id="del-confirmar"[^>]*>([^<]*)</button>', self.html)
        self.assertEqual(boton.group(1), "Borrar y devolver stock")

    def test_modal_accesible_y_campos_con_etiqueta(self):
        self.comprobar_modales(self.html, ("modal-borrar",))
        self.comprobar_etiquetas(self.html)

    def test_js_endpoints_y_codificacion(self):
        for fragmento in ("/api/ordenes", "URLSearchParams", "encodeURIComponent", "reintegrar=",
                          "Borrar sin devolver stock", "Borrar y devolver stock",
                          "No hay órdenes en ese período", "Validacion.rango", "reactivado"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        self.assertNotRegex(self.js, r"/api/ordenes/\$\{(?!encodeURIComponent)")

    def test_vacio_sin_filtros_dice_solo_no_hay_ordenes(self):
        # Sin filtros (consulta vacia) el cartel es "No hay órdenes" a secas; con filtros, "en ese período".
        self.assertRegex(self.js, r'consulta\s*\?\s*"No hay órdenes en ese período"\s*:\s*"No hay órdenes"')


class ExportarPdfEstaticoTest(unittest.TestCase):
    """C-06c: guardas de static/js/exportar.js, busqueda.js y la hoja de impresion."""

    def test_exportar_js_usa_la_impresion_del_navegador(self):
        js = leer(STATIC / "js" / "exportar.js")
        for fragmento in ("window.print", "afterprint", "document.title", "matchMedia", "textContent",
                          "data-exportando"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, js)
        for prohibido in ("fetch", "XMLHttpRequest"):
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, js)

    def test_busqueda_js_es_pura(self):
        js = leer(STATIC / "js" / "busqueda.js")
        for prohibido in ("fetch", "XMLHttpRequest", "document."):
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, js)

    def test_hoja_de_impresion_en_app_css(self):
        css = leer(STATIC / "css" / "app.css")
        for fragmento in ("@media print", ".print-only", "table-header-group", "break-inside: avoid", "@page"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, css)

    def test_paginas_tienen_el_encabezado_de_impresion_y_cargan_exportar(self):
        for nombre in ("index.html", "ordenes.html", "reportes.html"):
            html = leer(STATIC / nombre)
            with self.subTest(pagina=nombre):
                self.assertRegex(
                    html, r'<header id="print-head" class="print-only" aria-hidden="true">\s*</header>')
                self.assertIn("/static/js/exportar.js", html)


class BuscadorYExportacionInventarioTest(unittest.TestCase):
    """C-06c: buscador y 'Exportar PDF' de /inventario."""

    def setUp(self):
        self.html = leer(STATIC / "index.html")
        self.js = leer(STATIC / "js" / "inventario.js")

    def test_carga_los_modulos_antes_de_inventario_js(self):
        for modulo in ("busqueda.js", "exportar.js"):
            with self.subTest(modulo=modulo):
                self.assertLess(self.html.index("/static/js/" + modulo),
                                self.html.index("/static/js/inventario.js"))

    def test_campo_de_busqueda_etiquetado(self):
        campo = re.search(r'<input[^>]*id="inv-buscar"[^>]*>', self.html).group(0)
        self.assertIn('type="search"', campo)
        self.assertRegex(self.html, r'<label[^>]*for="inv-buscar"[^>]*>Buscar por código o nombre</label>')

    def test_boton_exportar_y_cartel_sin_coincidencias(self):
        boton = re.search(r'<button[^>]*id="btn-exportar-inv"[^>]*>([^<]*)</button>', self.html)
        self.assertEqual(boton.group(1), "Exportar PDF")
        cartel = re.search(r'<div[^>]*id="inv-sin-coincidencias"[^>]*>', self.html).group(0)
        self.assertIn("hidden", cartel)
        self.assertIn('role="status"', cartel)
        self.assertIn("Limpiar filtros", self.html)

    def test_js_usa_los_modulos_y_no_busca_en_el_servidor(self):
        for fragmento in ("Busqueda.mensajeSinCoincidencias", "Busqueda.filtrar", "Busqueda.conteo",
                          "Exportar.imprimir", "(sin stock)", "Escape"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        self.assertNotIn("q=", self.js)

    def test_las_regiones_de_pantalla_no_salen_en_papel(self):
        # Cabecera, acciones, aviso y cabecera del panel (buscador/exportar) llevan no-print.
        self.assertRegex(self.html, r'<header class="[^"]*no-print')
        self.assertRegex(self.html, r'<div id="aviso-exito"[^>]*no-print')


class ExportarOrdenEstaticoTest(unittest.TestCase):
    """C-06c: 'Exportar PDF' por orden en /ordenes (sin exportacion global)."""

    def setUp(self):
        self.html = leer(STATIC / "ordenes.html")
        self.js = leer(STATIC / "js" / "ordenes.js")

    def test_carga_exportar_y_no_hay_boton_global(self):
        self.assertLess(self.html.index("/static/js/exportar.js"), self.html.index("/static/js/ordenes.js"))
        self.assertNotIn("Exportar PDF", self.html)

    def test_boton_por_orden_accesible_y_conectado(self):
        for fragmento in ("data-exportar-orden", "Exportar PDF de la orden ", "Exportar.imprimir",
                          'modo: "orden"', "data-exportar"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        self.assertNotIn("fetch", self.js)


class NavegacionReportesTest(unittest.TestCase):
    """C-06d: pestaña "Reportes" en las tres paginas protegidas (mockup N1)."""

    def test_pestana_reportes_y_una_sola_pagina_actual(self):
        for nombre in ("index.html", "ordenes.html", "reportes.html"):
            html = leer(STATIC / nombre)
            with self.subTest(pagina=nombre):
                nav = re.search(r'<nav aria-label="Secciones".*?</nav>', html, re.S).group(0)
                self.assertRegex(nav, r'<a class="navlink" href="/reportes"[^>]*>Reportes</a>')
                self.assertEqual(nav.count('aria-current="page"'), 1)
        propia = {"index.html": "/inventario", "ordenes.html": "/ordenes", "reportes.html": "/reportes"}
        for nombre, href in propia.items():
            nav = re.search(r'<nav aria-label="Secciones".*?</nav>', leer(STATIC / nombre), re.S).group(0)
            with self.subTest(propia=nombre):
                self.assertRegex(nav, r'href="%s" aria-current="page"' % href)


class ReportesPaginaTest(CamposEtiquetadosMixin, unittest.TestCase):
    """C-06d: pantalla /reportes (mockups R0-R9)."""

    def setUp(self):
        self.html = leer(STATIC / "reportes.html")
        self.js = leer(STATIC / "js" / "reportes.js")

    def test_carga_los_modulos_en_orden(self):
        posiciones = [self.html.index("/static/js/%s.js" % m) for m in
                      ("validacion", "api", "ui", "sesion", "exportar", "reportes")]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_encabezado_de_impresion_y_campos(self):
        self.assertRegex(self.html, r'<header id="print-head" class="print-only" aria-hidden="true">\s*</header>')
        for ident in ("r-desde", "r-hasta"):
            self.assertRegex(self.html, r'<input[^>]*id="%s"[^>]*type="date"|<input[^>]*type="date"[^>]*id="%s"' % (ident, ident))
        self.assertIn('id="r-producto"', self.html)
        self.comprobar_etiquetas(self.html)

    def test_rotulos_de_los_filtros(self):
        self.assertRegex(self.html, r'for="r-desde">Desde <span[^>]*>\(obligatorio\)</span>')
        self.assertRegex(self.html, r'for="r-hasta">Hasta <span[^>]*>\(opcional\)</span>')
        self.assertIn("Vacío = hoy", self.html)

    def test_estados_y_botones(self):
        for ident in ("rep-inicial", "rep-cargando", "rep-error", "rep-vacio", "rep-resumen",
                      "rep-tabla", "btn-generar", "btn-exportar-rep"):
            with self.subTest(ident=ident):
                self.assertIn('id="%s"' % ident, self.html)
        for texto in ("Generar", "Exportar PDF", "Reintentar", "Generando reporte…"):
            self.assertIn(texto, self.html)
        inicial = re.search(r'<div[^>]*id="rep-inicial"[^>]*>', self.html).group(0)
        self.assertNotIn("hidden", inicial)
        self.assertIn("Elegí el período y pulsá «Generar» para ver el reporte.", self.html)
        boton = re.search(r'<button[^>]*id="btn-exportar-rep"[^>]*>', self.html).group(0)
        self.assertIn(" disabled", boton)
        self.assertIn("no-print", re.search(r'<p[^>]*id="rep-resumen"[^>]*>', self.html).group(0))

    def test_tabla_con_columnas_en_orden(self):
        cab = re.search(r"<thead>.*?</thead>", self.html, re.S).group(0)
        self.assertEqual(re.findall(r"<th[^>]*>([^<]*)</th>", cab), ["Código", "Nombre", "Categoría", "Cantidad", "Órdenes"])
        self.assertIn("tbl-rep", self.html)

    def test_js_endpoints_y_validacion(self):
        for fragmento in ("/api/reportes/productos-en-ordenes", "/api/reportes/productos-usados",
                          "optgroup", "Activos", "Dados de baja", "Validacion.rango", "Validacion.requerido",
                          "dado de baja", "No hay productos usados en órdenes", "no se usó en órdenes"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)
        for prohibido in ("/api/inventario", "/api/productos/inactivos"):
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, self.js)

    def test_js_exporta_el_ultimo_reporte(self):
        for fragmento in ("Exportar.imprimir", "Reporte de productos en órdenes", "archivo:", 'modo: "reporte"'):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, self.js)


if __name__ == "__main__":
    unittest.main()
