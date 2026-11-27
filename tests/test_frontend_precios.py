"""Guardas estaticas de "Nueva orden" con datos del cliente, importes y resumen (C-06h, grupo 8).
No ejecutan JS: fijan la estructura del mockup N1 aprobado y las reglas de seguridad."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"


def leer(*partes):
    return STATIC.joinpath(*partes).read_text(encoding="utf-8")


def modal_orden(html):
    return html[html.index('id="modal-orden"'):html.index('id="modal-baja"')]


class NuevaOrdenDatosTest(unittest.TestCase):
    def setUp(self):
        self.html = leer("index.html")
        self.modal = modal_orden(self.html)

    def test_fecha_de_la_orden_sin_cambios_junto_al_numero(self):
        self.assertIn('id="ord-numero"', self.modal)
        self.assertIn('for="ord-fecha">Fecha (AAAA-MM-DD)</label>', self.modal)
        self.assertLess(self.modal.index('id="ord-fecha"'), self.modal.index("Cliente y embarcación"))

    def test_bloque_cliente_y_embarcacion_con_todos_los_campos_opcionales(self):
        i = self.modal.index("Cliente y embarcación")
        bloque = self.modal[i:self.modal.index("</fieldset>", i)]
        for campo in ("ord-cliente", "ord-celular", "ord-casco", "ord-motor", "ord-trailer",
                      "ord-ingreso", "ord-egreso"):
            self.assertIn(f'id="{campo}"', bloque)
        self.assertNotIn("required", bloque)
        self.assertNotIn("*", bloque)
        self.assertIn("todos opcionales", bloque)
        self.assertRegex(bloque, r'id="ord-celular"[^>]*type="tel"|type="tel"[^>]*id="ord-celular"')
        self.assertRegex(bloque, r'id="ord-ingreso"[^>]*type="date"|type="date"[^>]*id="ord-ingreso"')
        self.assertRegex(bloque, r'for="ord-egreso">Fecha de egreso</label>')

    def test_precio_del_servicio_general(self):
        self.assertIn('id="ord-servicio-precio"', self.modal)
        self.assertIn('aria-label="Precio del servicio general"', self.modal)
        self.assertRegex(self.modal, r'id="ord-servicio-precio"[^>]*inputmode="decimal"')

    def test_servicios_adicionales_reemplaza_a_procesos_en_la_interfaz(self):
        self.assertIn('<legend class="label">Servicios adicionales</legend>', self.modal)
        self.assertNotIn('<legend class="label">Procesos</legend>', self.modal)
        self.assertRegex(self.modal, r'id="ord-proc-agregar"[^>]*>Agregar servicio adicional</button>')
        self.assertIn("Una orden admite hasta 10 servicios adicionales personalizados.", self.modal)

    def test_resumen_al_final_del_cuerpo_con_aria_live(self):
        i = self.modal.index('class="resumen"')
        self.assertGreater(i, self.modal.index("Servicios adicionales"))
        self.assertLess(i, self.modal.index("modal-foot"))
        resumen = self.modal[i:self.modal.index("modal-foot")]
        self.assertIn('aria-live="polite"', self.modal[i - 40:i + 120])
        for texto in ("Subtotal servicios", "Subtotal ítems", "Total"):
            self.assertIn(texto, resumen)
        for id_ in ("ord-sub-servicios", "ord-sub-items", "ord-total"):
            self.assertIn(f'id="{id_}"', resumen)

    def test_modal_a_44rem_y_scripts_nuevos_antes_de_inventario_js(self):
        self.assertIn('class="modal modal-wide"', self.modal)
        self.assertIn("modal-wide", leer("css", "app.css"))
        for js in ("precios.js", "datos-orden.js", "procesos.js"):
            self.assertLess(self.html.index(f"/static/js/{js}"), self.html.index("/static/js/inventario.js"))


class NuevaOrdenJsTest(unittest.TestCase):
    def setUp(self):
        self.js = leer("js", "inventario.js")

    def test_usa_los_modulos_puros(self):
        for uso in ("Precios.parsear(", "Precios.resumen(", "Precios.formatear(", "DatosOrden.validar(",
                    "Procesos.armar("):
            self.assertIn(uso, self.js)

    def test_envia_datos_precios_y_objetos_de_procesos(self):
        for campo in ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso",
                      "fecha_egreso", "precio_servicio"):
            self.assertRegex(self.js, rf"\b{campo}\b")
        self.assertRegex(self.js, r"precio\s*:")
        self.assertRegex(self.js, r"cuerpo\.procesos\s*=\s*\w+\.procesos")
        self.assertRegex(self.js, r"cuerpo\.procesos_personalizados\s*=\s*\w+\.procesos_personalizados")

    def test_etiquetas_accesibles_de_las_cajas_de_importe(self):
        for texto in ("Importe de la línea ", "Precio del servicio adicional "):
            self.assertIn(texto, self.js)

    def test_textos_renombrados_de_servicios_adicionales(self):
        self.assertIn("Servicio adicional personalizado", self.js)
        self.assertIn("No se pudo cargar la lista de servicios adicionales.", self.js)
        self.assertNotIn("No se pudo cargar la lista de procesos.", self.js)

    def test_caja_de_precio_del_servicio_se_deshabilita_sin_servicio(self):
        self.assertIn('$("ord-servicio-precio")', self.js)
        self.assertRegex(self.js, r"precio\.disabled\s*=\s*clave\s*===\s*\"\"")
        self.assertRegex(self.js, r"if \(precio\.disabled\) precio\.value = \"\"")

    def test_sin_innerhtml_en_los_modulos_nuevos(self):
        self.assertNotIn("innerHTML", self.js)
        self.assertNotIn("innerHTML", leer("js", "precios.js"))
        self.assertNotIn("innerHTML", leer("js", "datos-orden.js"))
        self.assertIsNone(re.search(r"parseFloat", leer("js", "precios.js")))


if __name__ == "__main__":
    unittest.main()
