import unittest
from datetime import date

from inventario.domain.errors import DatosInvalidos
from inventario.services.fechas import parsear_fecha, parsear_filtro_fecha, validar_rango

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


class ParsearFiltroFechaTest(unittest.TestCase):
    def test_vacio_o_ausente_es_sin_limite(self):
        for valor in (None, ""):
            with self.subTest(valor=valor):
                self.assertIsNone(parsear_filtro_fecha("desde", valor))

    def test_fecha_valida(self):
        self.assertEqual(parsear_filtro_fecha("hasta", "2026-11-19"), date(2026, 11, 19))

    def test_formato_incorrecto_nombra_el_filtro(self):
        for nombre, valor in (("desde", "19/11/2026"), ("hasta", "x"), ("desde", " 2026-11-20")):
            with self.subTest(nombre=nombre, valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    parsear_filtro_fecha(nombre, valor)
                self.assertEqual(
                    str(ctx.exception), f"La fecha '{nombre}' debe tener formato AAAA-MM-DD."
                )

    def test_fecha_inexistente_con_valor(self):
        for nombre, valor in (("hasta", "2026-02-30"), ("desde", "2026-13-01")):
            with self.subTest(nombre=nombre, valor=valor):
                with self.assertRaises(DatosInvalidos) as ctx:
                    parsear_filtro_fecha(nombre, valor)
                self.assertEqual(
                    str(ctx.exception), f"La fecha '{nombre}' ({valor}) no es una fecha válida."
                )


class ValidarRangoTest(unittest.TestCase):
    def test_desde_posterior_a_hasta_con_los_textos_originales(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            validar_rango("2026-11-20", "2026-11-19", date(2026, 11, 20), date(2026, 11, 19))
        self.assertEqual(
            str(ctx.exception),
            "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).",
        )

    def test_rangos_validos_no_lanzan(self):
        d = date(2026, 11, 19)
        validar_rango("2026-11-19", "2026-11-19", d, d)
        validar_rango("2026-11-18", "2026-11-19", date(2026, 11, 18), d)
        validar_rango("2026-11-19", None, d, None)
        validar_rango(None, "2026-11-19", None, d)
        validar_rango(None, None, None, None)
