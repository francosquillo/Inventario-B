import unittest
from datetime import date

from inventario.domain.errors import DatosInvalidos
from inventario.services.fechas import parsear_fecha

MSG_FORMATO = "formato-x"
MSG_INVALIDA = "invalida {valor}"


def parsear(valor):
    return parsear_fecha(valor, MSG_FORMATO, MSG_INVALIDA)


class ParsearFechaTest(unittest.TestCase):
    def test_acepta_fecha_valida(self):
        self.assertEqual(parsear("2026-11-20"), date(2026, 11, 20))
        self.assertEqual(parsear("2024-02-29"), date(2024, 2, 29))

    def test_rechaza_formato(self):
        for valor in ("20/11/2026", "2026-11-20T10:00", "2026-11-20\n", "２０２６-11-20", 20261120, None):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    parsear(valor)
                self.assertEqual(str(ctx.exception), MSG_FORMATO)

    def test_rechaza_fecha_inexistente_con_su_mensaje(self):
        for valor in ("2026-02-30", "2026-13-01", "2025-02-29"):
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    parsear(valor)
                self.assertEqual(str(ctx.exception), f"invalida {valor}")
