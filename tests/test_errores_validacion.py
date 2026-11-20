import unittest

from pydantic import ValidationError

from inventario.api.errores_validacion import mensaje_validacion
from inventario.api.schemas import IngresoRequest, LoginRequest

MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


def errores_de(modelo, datos):
    try:
        modelo.model_validate(datos)
    except ValidationError as exc:
        return exc.errors()
    raise AssertionError("los datos eran validos")


class MensajeValidacionTest(unittest.TestCase):
    def mensaje(self, modelo, datos):
        # FastAPI antepone "body" a loc; se replica para usar errores reales.
        errores = [{**e, "loc": ("body", *e["loc"])} for e in errores_de(modelo, datos)]
        return mensaje_validacion(errores)

    def test_campo_faltante(self):
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": "admin"}),
            "El campo password es obligatorio.",
        )

    def test_campo_vacio(self):
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": "", "password": "x"}),
            "El campo username es obligatorio.",
        )

    def test_texto_demasiado_largo(self):
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": "u" * 65, "password": "x"}),
            "El campo username admite hasta 64 caracteres.",
        )
        self.assertEqual(
            self.mensaje(IngresoRequest, {"codigo": "c" * 51, "cantidad": 1}),
            "El campo codigo admite hasta 50 caracteres.",
        )
        self.assertEqual(
            self.mensaje(IngresoRequest, {"codigo": "A", "cantidad": 1, "nombre": "n" * 121}),
            "El campo nombre admite hasta 120 caracteres.",
        )

    def test_tipo_de_texto_incorrecto(self):
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": 5, "password": "x"}),
            "El campo username debe ser texto.",
        )

    def test_cualquier_error_de_cantidad(self):
        for cantidad in ("5", 2.5, 0, True, 10001, -3):
            with self.subTest(cantidad=cantidad):
                self.assertEqual(
                    self.mensaje(IngresoRequest, {"codigo": "A-01", "cantidad": cantidad}),
                    MSG_CANTIDAD,
                )

    def test_cantidad_faltante_es_obligatoria(self):
        self.assertEqual(
            self.mensaje(IngresoRequest, {"codigo": "A-01"}),
            "El campo cantidad es obligatorio.",
        )

    def test_varios_errores_devuelve_solo_el_primero(self):
        self.assertEqual(
            self.mensaje(IngresoRequest, {"cantidad": 0}),
            "El campo codigo es obligatorio.",
        )

    def test_tipo_desconocido_cae_en_mensaje_generico_con_campo(self):
        errores = [{"type": "otro", "loc": ("body", "x"), "msg": "..."}]
        self.assertEqual(mensaje_validacion(errores), "El campo x no es válido.")

    def test_sin_campo_cae_en_mensaje_generico(self):
        errores = [{"type": "otro", "loc": ("body",), "msg": "..."}]
        self.assertEqual(mensaje_validacion(errores), "Los datos enviados no son válidos.")
        self.assertEqual(mensaje_validacion([]), "Los datos enviados no son válidos.")

    def test_errores_de_cuerpo(self):
        casos = [
            ({"type": "json_invalid", "loc": ("body", 1)}, "El cuerpo de la petición no es JSON válido."),
            ({"type": "missing", "loc": ("body",)}, "El cuerpo de la petición es obligatorio."),
            (
                {"type": "model_attributes_type", "loc": ("body",)},
                "El cuerpo de la petición debe ser un objeto JSON.",
            ),
            (
                {"type": "dict_type", "loc": ("body",)},
                "El cuerpo de la petición debe ser un objeto JSON.",
            ),
        ]
        for error, esperado in casos:
            with self.subTest(tipo=error["type"]):
                self.assertEqual(mensaje_validacion([error]), esperado)

    def test_fechas_en_query(self):
        errores = [{"type": "date_from_datetime_parsing", "loc": ("query", "desde")}]
        self.assertEqual(mensaje_validacion(errores), "La fecha debe tener formato AAAA-MM-DD.")


if __name__ == "__main__":
    unittest.main()
