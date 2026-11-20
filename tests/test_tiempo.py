import unittest
from datetime import datetime, timedelta

from inventario.domain.tiempo import ZONA_AR, ahora_argentina


class TiempoTest(unittest.TestCase):
    def test_zona_ar_es_menos_tres_horas(self):
        self.assertEqual(ZONA_AR.utcoffset(None), timedelta(hours=-3))

    def test_ahora_argentina_es_aware_con_offset_y_sin_microsegundos(self):
        ahora = ahora_argentina()
        self.assertIsInstance(ahora, datetime)
        self.assertEqual(ahora.utcoffset(), timedelta(hours=-3))
        self.assertEqual(ahora.microsecond, 0)

    def test_isoformat_termina_en_offset_fijo(self):
        self.assertTrue(ahora_argentina().isoformat(timespec="seconds").endswith("-03:00"))
