"""La conexion por request la crea la dependencia en un hilo del pool y la usan otras
dependencias/endpoints sincronicos en otro hilo: debe poder usarse entre hilos (C-06, hallazgo del verify)."""
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace

from inventario.api.dependencies import get_conexion


class ConexionEntreHilosTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ruta = os.path.join(tmp.name, "hilos.db")
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ruta_db=ruta)))

    def usar_en_otro_hilo(self, conn, sql):
        resultado = {}

        def tarea():
            try:
                resultado["valor"] = conn.execute(sql).fetchone()[0]
            except Exception as exc:  # se reporta en el hilo principal
                resultado["error"] = exc

        hilo = threading.Thread(target=tarea)
        hilo.start()
        hilo.join()
        return resultado

    def test_la_conexion_se_usa_desde_otro_hilo(self):
        gen = get_conexion(self.request)
        conn = next(gen)
        resultado = self.usar_en_otro_hilo(conn, "SELECT 41 + 1")
        self.assertNotIn("error", resultado, resultado.get("error"))
        self.assertEqual(resultado["valor"], 42)
        gen.close()

    def test_conserva_row_factory_y_claves_foraneas(self):
        gen = get_conexion(self.request)
        conn = next(gen)
        self.assertEqual(self.usar_en_otro_hilo(conn, "PRAGMA foreign_keys")["valor"], 1)
        fila = conn.execute("SELECT 7 AS n").fetchone()
        self.assertEqual(fila["n"], 7)
        gen.close()

    def test_se_cierra_al_terminar_el_request(self):
        import sqlite3

        gen = get_conexion(self.request)
        conn = next(gen)
        gen.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
