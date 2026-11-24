"""Funciones puras de static/js/reportes.js ejecutadas con Node (se omiten sin Node)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REPORTES = RAIZ / "static" / "js" / "reportes.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const R = window.Reporte;
const casos = JSON.parse(process.argv[2]);
const salida = casos.map(([fn, args]) => {
  const a = args.map((x) => (x && x.__fecha) ? new Date(x.__fecha[0], x.__fecha[1], x.__fecha[2]) : x);
  const r = R[fn](...a);
  return r instanceof URLSearchParams ? r.toString() : r;
});
process.stdout.write(JSON.stringify(salida));
"""

USADOS = [
    {"codigo": "C-99", "nombre": "Viejo", "activo": False},
    {"codigo": "B-02", "nombre": "Tuerca", "activo": True},
    {"codigo": "A-01", "nombre": "Tornillo", "activo": True},
    {"codigo": "Z-00", "nombre": "Zeta", "activo": False},
]


def fecha(anio, mes0, dia):
    """Fecha local; el mes va base 0 como en Date de JS."""
    return {"__fecha": [anio, mes0, dia]}


def ejecutar(casos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(REPORTES), json.dumps(casos)],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def uno(fn, *args):
    return ejecutar([[fn, list(args)]])[0]


@unittest.skipUnless(NODE, "Node no esta instalado")
class RangoYParametrosTest(unittest.TestCase):
    def test_rango_por_defecto_es_el_mes_en_curso(self):
        self.assertEqual(uno("rangoPorDefecto", fecha(2026, 10, 24)),
                         {"desde": "2026-11-01", "hasta": "2026-11-24"})

    def test_rango_por_defecto_en_los_bordes_del_anio(self):
        self.assertEqual(uno("rangoPorDefecto", fecha(2026, 0, 1)),
                         {"desde": "2026-01-01", "hasta": "2026-01-01"})
        self.assertEqual(uno("rangoPorDefecto", fecha(2026, 11, 31)),
                         {"desde": "2026-12-01", "hasta": "2026-12-31"})

    def test_parametros_omite_los_vacios(self):
        self.assertEqual(uno("parametros", "2026-11-01", "2026-11-24", "A-01"),
                         "desde=2026-11-01&hasta=2026-11-24&codigo=A-01")
        self.assertEqual(uno("parametros", "2026-11-01", "", ""), "desde=2026-11-01")
        self.assertEqual(uno("parametros", "2026-11-01", "  ", "A/01"),
                         "desde=2026-11-01&codigo=A%2F01")

    def test_hasta_efectivo(self):
        self.assertEqual(uno("hastaEfectivo", "", fecha(2026, 10, 24)), "2026-11-24")
        self.assertEqual(uno("hastaEfectivo", "  ", fecha(2026, 10, 24)), "2026-11-24")
        self.assertEqual(uno("hastaEfectivo", "2026-10-31", fecha(2026, 10, 24)), "2026-10-31")


@unittest.skipUnless(NODE, "Node no esta instalado")
class SelectorTest(unittest.TestCase):
    def test_grupos_activos_y_dados_de_baja_ordenados_por_codigo(self):
        self.assertEqual(uno("gruposProductos", USADOS), [
            {"grupo": "Activos", "opciones": [
                {"codigo": "A-01", "etiqueta": "A-01 · Tornillo"},
                {"codigo": "B-02", "etiqueta": "B-02 · Tuerca"},
            ]},
            {"grupo": "Dados de baja", "opciones": [
                {"codigo": "C-99", "etiqueta": "C-99 · Viejo"},
                {"codigo": "Z-00", "etiqueta": "Z-00 · Zeta"},
            ]},
        ])

    def test_grupo_vacio_se_omite(self):
        solo_baja = [p for p in USADOS if not p["activo"]]
        self.assertEqual([g["grupo"] for g in uno("gruposProductos", solo_baja)], ["Dados de baja"])
        self.assertEqual(uno("gruposProductos", []), [])

    def test_etiqueta_de_cualquiera_de_los_dos_grupos(self):
        grupos = uno("gruposProductos", USADOS)
        self.assertEqual(uno("etiquetaProducto", "A-01", grupos), "A-01 · Tornillo")
        self.assertEqual(uno("etiquetaProducto", "C-99", grupos), "C-99 · Viejo")
        self.assertEqual(uno("etiquetaProducto", "", grupos), "")
        self.assertEqual(uno("etiquetaProducto", "X-00", grupos), "X-00")


@unittest.skipUnless(NODE, "Node no esta instalado")
class TextosTest(unittest.TestCase):
    def test_linea_de_encabezado_plural_y_singular(self):
        cinco = [{}] * 5
        self.assertEqual(uno("lineaEncabezado", cinco, "2026-11-01", "2026-11-24", ""),
                         "2026-11-01 a 2026-11-24 · 5 productos")
        self.assertEqual(uno("lineaEncabezado", [{}], "2026-11-01", "2026-11-24", ""),
                         "2026-11-01 a 2026-11-24 · 1 producto")

    def test_linea_de_encabezado_con_producto(self):
        self.assertEqual(
            uno("lineaEncabezado", [{}], "2026-11-01", "2026-11-24", "A-01 · Tornillo"),
            "A-01 · Tornillo · 2026-11-01 a 2026-11-24 · 1 producto")

    def test_mensaje_vacio_con_y_sin_producto(self):
        self.assertEqual(uno("mensajeVacio", "2026-10-01", "2026-10-31", ""),
                         "No hay productos usados en órdenes entre 2026-10-01 y 2026-10-31")
        self.assertEqual(uno("mensajeVacio", "2026-11-01", "2026-11-24", "A-01 · Tornillo"),
                         "«A-01 · Tornillo» no se usó en órdenes entre 2026-11-01 y 2026-11-24")

    def test_nombre_de_archivo(self):
        self.assertEqual(uno("nombreArchivo", "2026-11-01", "2026-11-24", ""),
                         "reporte-2026-11-01_2026-11-24")
        self.assertEqual(uno("nombreArchivo", "2026-11-01", "2026-11-24", "A-01"),
                         "reporte-A-01-2026-11-01_2026-11-24")
        self.assertEqual(uno("nombreArchivo", "2026-11-01", "2026-11-24", "A/01"),
                         "reporte-A-01-2026-11-01_2026-11-24")


if __name__ == "__main__":
    unittest.main()
