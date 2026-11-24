"""Funciones puras de static/js/exportar.js ejecutadas con Node (se omiten sin Node)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EXPORTAR = RAIZ / "static" / "js" / "exportar.js"
NODE = shutil.which("node")

PUENTE = """
globalThis.window = {};
require(process.argv[1]);
const E = window.Exportar;
const casos = JSON.parse(process.argv[2]);
const salida = casos.map(([fn, args]) => {
  const a = args.map((x) => (x && x.__fecha) ? new Date(x.__fecha[0], x.__fecha[1], x.__fecha[2]) : x);
  return E[fn](...a);
});
process.stdout.write(JSON.stringify(salida));
"""


def fecha(anio, mes0, dia):
    """Fecha local; el mes va base 0 como en Date de JS."""
    return {"__fecha": [anio, mes0, dia]}


def ejecutar(casos):
    r = subprocess.run(
        [NODE, "-e", PUENTE, str(EXPORTAR), json.dumps(casos)],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "Node no esta instalado")
class NombreArchivoTest(unittest.TestCase):
    def test_inventario(self):
        res = ejecutar([["nombreArchivo", ["inventario", fecha(2026, 10, 24)]]])
        self.assertEqual(res, ["inventario-2026-11-24"])

    def test_caracteres_raros_y_guiones_repetidos(self):
        res = ejecutar([
            ["nombreArchivo", ["orden-OT/2026#1", fecha(2026, 10, 24)]],
            ["nombreArchivo", ["orden--OT 0042 ", fecha(2026, 10, 24)]],
            ["nombreArchivo", ["orden-OT-0042", fecha(2026, 0, 5)]],
        ])
        self.assertEqual(res, [
            "orden-OT-2026-1-2026-11-24",
            "orden-OT-0042-2026-11-24",
            "orden-OT-0042-2026-01-05",
        ])


@unittest.skipUnless(NODE, "Node no esta instalado")
class FechaTest(unittest.TestCase):
    def test_rellena_con_ceros(self):
        res = ejecutar([
            ["fecha", [fecha(2026, 0, 5)]],
            ["fecha", [fecha(2026, 11, 31)]],
        ])
        self.assertEqual(res, ["2026-01-05", "2026-12-31"])


@unittest.skipUnless(NODE, "Node no esta instalado")
class LimpiarArchivoTest(unittest.TestCase):
    def test_conserva_guion_bajo_y_guiones(self):
        res = ejecutar([["limpiarArchivo", ["reporte-A-01-2026-11-01_2026-11-24"]]])
        self.assertEqual(res, ["reporte-A-01-2026-11-01_2026-11-24"])

    def test_caracteres_raros_se_vuelven_guion_colapsado(self):
        res = ejecutar([
            ["limpiarArchivo", ["reporte A/01 .. x"]],
            ["limpiarArchivo", ["--reporte--"]],
            ["limpiarArchivo", ["rep#orte$$_2026"]],
        ])
        self.assertEqual(res, ["reporte-A-01-x", "reporte", "rep-orte-_2026"])

    def test_nombre_archivo_de_c06c_no_cambia(self):
        res = ejecutar([["nombreArchivo", ["inventario", fecha(2026, 10, 24)]]])
        self.assertEqual(res, ["inventario-2026-11-24"])


class ImprimirUsaArchivoTest(unittest.TestCase):
    def test_imprimir_prefiere_opciones_archivo(self):
        js = EXPORTAR.read_text(encoding="utf-8")
        self.assertIn("opciones.archivo", js)
        self.assertIn("limpiarArchivo(opciones.archivo)", js)
        self.assertIn("nombreArchivo(opciones.base, new Date())", js)


if __name__ == "__main__":
    unittest.main()
