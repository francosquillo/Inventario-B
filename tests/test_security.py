import unittest
from unittest import mock

from inventario import security
from inventario.security import (
    PBKDF2_ITERACIONES,
    generar_password,
    hashear_password,
    verificar_password,
)

IT = 1000  # iteraciones bajas solo para tests de mecánica


class HashingTest(unittest.TestCase):
    def test_verifica_la_contrasena_original(self):
        h, s = hashear_password("s3creta!", iteraciones=IT)
        self.assertTrue(verificar_password("s3creta!", h, s, iteraciones=IT))

    def test_rechaza_contrasenas_distintas_o_vacia(self):
        h, s = hashear_password("s3creta!", iteraciones=IT)
        for intento in ("S3creta!", "", "s3creta! "):
            with self.subTest(intento=intento):
                self.assertFalse(verificar_password(intento, h, s, iteraciones=IT))

    def test_misma_contrasena_da_salts_y_hashes_distintos(self):
        h1, s1 = hashear_password("igual", iteraciones=IT)
        h2, s2 = hashear_password("igual", iteraciones=IT)
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(h1, h2)

    def test_formato_hex_de_hash_y_salt(self):
        h, s = hashear_password("x", iteraciones=IT)
        self.assertRegex(h, r"^[0-9a-f]{64}$")
        self.assertRegex(s, r"^[0-9a-f]{32}$")

    def test_mismo_salt_es_determinista(self):
        _, s = hashear_password("x", iteraciones=IT)
        h1, _ = hashear_password("y", salt=s, iteraciones=IT)
        h2, s2 = hashear_password("y", salt=s, iteraciones=IT)
        self.assertEqual(h1, h2)
        self.assertEqual(s, s2)

    def test_usa_compare_digest(self):
        h, s = hashear_password("x", iteraciones=IT)
        with mock.patch.object(
            security.hmac, "compare_digest", wraps=security.hmac.compare_digest
        ) as espia:
            verificar_password("x", h, s, iteraciones=IT)
        espia.assert_called_once()

    def test_default_de_iteraciones(self):
        self.assertEqual(PBKDF2_ITERACIONES, 600_000)


class GenerarPasswordTest(unittest.TestCase):
    def test_longitud_minima_y_aleatoriedad(self):
        a, b = generar_password(), generar_password()
        self.assertGreaterEqual(len(a), 16)
        self.assertNotEqual(a, b)
