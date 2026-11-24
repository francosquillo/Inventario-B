"""Comportamiento de static/js/busqueda.js (funciones puras) ejecutado con Node.

Se omite si Node no esta instalado.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BUSQUEDA = RAIZ / "static" / "js" / "busqueda.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const B = window.Busqueda;
const casos = JSON.parse(process.argv[2]);
const salida = casos.map(([fn, args]) => B[fn](...args));
process.stdout.write(JSON.stringify(salida));
"""

CATALOGO = [
    {"codigo": "A-01", "nombre": "Tornillo M8"},
    {"codigo": "A-02", "nombre": "Tornillo M10"},
    {"codigo": "B-10", "nombre": "Tuerca M8"},
    {"codigo": "C-03", "nombre": "Arandela"},
    {"codigo": "D-04", "nombre": "Junta tórica"},
]


def ejecutar(casos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(BUSQUEDA), json.dumps(casos)],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def codigos(lista):
    return [p["codigo"] for p in lista]


def filtrar(texto, productos=None):
    return codigos(ejecutar([["filtrar", [productos or CATALOGO, texto]]])[0])


@unittest.skipUnless(NODE, "Node no esta instalado")
class FiltrarTest(unittest.TestCase):
    def test_nombre_parcial_sin_mayusculas(self):
        productos = [
            {"codigo": "A-01", "nombre": "Tornillo M8"},
            {"codigo": "B-10", "nombre": "Tuerca M8"},
            {"codigo": "C-03", "nombre": "Arandela"},
        ]
        self.assertEqual(filtrar("tor", productos), ["A-01"])

    def test_codigo_parcial_conserva_el_orden(self):
        self.assertEqual(filtrar("a-0"), ["A-01", "A-02"])

    def test_coincidencia_en_codigo_y_nombre_no_duplica(self):
        productos = CATALOGO + [{"codigo": "M8-X", "nombre": "Perno M8"}]
        self.assertEqual(filtrar("m8", productos), ["A-01", "B-10", "M8-X"])

    def test_ignora_tildes_y_mayusculas(self):
        self.assertEqual(filtrar("TORICA"), ["D-04"])
        self.assertEqual(filtrar("tórica"), ["D-04"])

    def test_vacio_blancos_y_nulo_devuelven_todo(self):
        for texto in ("", "   ", None):
            with self.subTest(texto=texto):
                self.assertEqual(filtrar(texto), codigos(CATALOGO))

    def test_sin_coincidencias(self):
        self.assertEqual(filtrar("xyz"), [])

    def test_texto_completo_es_una_sola_subcadena(self):
        self.assertEqual(filtrar("tornillo m8"), ["A-01"])
        self.assertEqual(filtrar("m8 tornillo"), [])

    def test_html_en_el_texto_no_rompe(self):
        self.assertEqual(filtrar("<b>x</b>"), [])


@unittest.skipUnless(NODE, "Node no esta instalado")
class NormalizarTest(unittest.TestCase):
    def test_normaliza(self):
        entradas = ["  TórIca ", None, "Ñandú"]
        res = ejecutar([["normalizar", [e]] for e in entradas])
        self.assertEqual(res, ["torica", "", "nandu"])


@unittest.skipUnless(NODE, "Node no esta instalado")
class ConteoTest(unittest.TestCase):
    def test_conteo(self):
        casos = [
            [12, 12, False], [1, 1, False], [2, 12, True], [0, 12, True], [1, 12, True], [12, 12, True],
            [1, 1, True], [0, 0, True],
        ]
        res = ejecutar([["conteo", c] for c in casos])
        self.assertEqual(res, [
            "12 productos", "1 producto", "2 de 12 productos", "0 de 12 productos",
            "1 de 12 productos", "12 productos",
            "1 producto", "0 productos",
        ])


CON_CATEGORIA = [
    {"codigo": "A-01", "nombre": "Tornillo M8", "categoria": "motor"},
    {"codigo": "A-02", "nombre": "Aceite 10W40", "categoria": "aceite"},
    {"codigo": "B-10", "nombre": "Tuerca M8", "categoria": None},
    {"codigo": "C-03", "nombre": "Filtro de aceite", "categoria": "aceite"},
    {"codigo": "D-04", "nombre": "Junta tórica"},
]


def filtrar3(texto, categoria, productos=None):
    return codigos(ejecutar([["filtrar", [productos or CON_CATEGORIA, texto, categoria]]])[0])


@unittest.skipUnless(NODE, "Node no esta instalado")
class FiltrarPorCategoriaTest(unittest.TestCase):
    def test_solo_los_de_la_categoria_en_orden(self):
        self.assertEqual(filtrar3("", "aceite"), ["A-02", "C-03"])

    def test_todas_y_sin_tercer_parametro_no_filtran(self):
        self.assertEqual(filtrar3("", ""), codigos(CON_CATEGORIA))
        self.assertEqual(filtrar("m8", CON_CATEGORIA), ["A-01", "B-10"])

    def test_sin_categoria_incluye_null_y_ausente(self):
        self.assertEqual(filtrar3("", "__sin__"), ["B-10", "D-04"])

    def test_texto_y_categoria_se_combinan(self):
        self.assertEqual(filtrar3("aceite", "aceite"), ["A-02", "C-03"])
        self.assertEqual(filtrar3("filtro", "aceite"), ["C-03"])
        self.assertEqual(filtrar3("m8", "aceite"), [])
        self.assertEqual(filtrar3("torica", "__sin__"), ["D-04"])

    def test_categoria_sin_productos(self):
        self.assertEqual(filtrar3("", "frenos"), [])

    def test_conteo_con_filtro_de_categoria(self):
        res = ejecutar([["conteo", [2, 5, True]], ["conteo", [5, 5, True]]])
        self.assertEqual(res, ["2 de 5 productos", "5 productos"])


@unittest.skipUnless(NODE, "Node no esta instalado")
class MensajeSinCoincidenciasTest(unittest.TestCase):
    def test_tres_variantes(self):
        casos = [
            ["xyz", ""],
            ["  xyz ", None],
            ["", "Motor"],
            ["tor", "Aceite"],
            ["", ""],
        ]
        res = ejecutar([["mensajeSinCoincidencias", c] for c in casos])
        self.assertEqual(res, [
            "Ningún producto coincide con «xyz»",
            "Ningún producto coincide con «xyz»",
            "Ningún producto en la categoría «Motor»",
            "Ningún producto coincide con «tor» en la categoría «Aceite»",
            "Ningún producto coincide con los filtros",
        ])


@unittest.skipUnless(NODE, "Node no esta instalado")
class EtiquetasDeCategoriaTest(unittest.TestCase):
    MAPA = {"aceite": "Aceite", "motor": "Motor"}

    def test_nombre_de_categoria(self):
        casos = [
            [None, self.MAPA],
            ["aceite", self.MAPA],
            ["frenos", self.MAPA],
            ["frenos", {}],
            ["", self.MAPA],
        ]
        res = ejecutar([["nombreCategoria", c] for c in casos])
        self.assertEqual(res, ["Sin categoría", "Aceite", "frenos", "frenos", "Sin categoría"])

    def test_linea_del_pdf_del_inventario(self):
        casos = [
            [3, "Aceite", "2026-11-24"],
            [1, "Motor", "2026-11-24"],
            [12, "", "2026-11-24"],
            [1, None, "2026-11-24"],
        ]
        res = ejecutar([["lineaInventario", c] for c in casos])
        self.assertEqual(res, [
            "Aceite · 3 productos · 2026-11-24",
            "Motor · 1 producto · 2026-11-24",
            "12 productos · 2026-11-24",
            "1 producto · 2026-11-24",
        ])


@unittest.skipUnless(NODE, "Node no esta instalado")
class OrdenPorCategoriaTest(unittest.TestCase):
    def test_por_categoria(self):
        res = ejecutar([
            ["porCategoria", [CON_CATEGORIA, ""]],
            ["porCategoria", [CON_CATEGORIA, "aceite"]],
            ["porCategoria", [CON_CATEGORIA, "__sin__"]],
            ["porCategoria", [CON_CATEGORIA, "frenos"]],
        ])
        self.assertEqual([codigos(r) for r in res], [
            codigos(CON_CATEGORIA), ["A-02", "C-03"], ["B-10", "D-04"], [],
        ])

    def test_producto_sigue_visible(self):
        casos = [
            ["A-02", CON_CATEGORIA, "aceite"],
            ["A-01", CON_CATEGORIA, "aceite"],
            ["A-01", CON_CATEGORIA, ""],
            ["", CON_CATEGORIA, ""],
            ["ZZZ", CON_CATEGORIA, ""],
            ["B-10", CON_CATEGORIA, "__sin__"],
        ]
        res = ejecutar([["productoSigueVisible", c] for c in casos])
        self.assertEqual(res, [True, False, True, False, False, True])


if __name__ == "__main__":
    unittest.main()
