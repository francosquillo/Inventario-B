import unittest

from pydantic import ValidationError

from inventario.api.errores_validacion import mensaje_validacion
from inventario.api.schemas import IngresoRequest, LoginRequest, OrdenRequest

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

    def test_null_en_campo_de_texto_obligatorio_es_obligatorio(self):
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": None, "password": "x"}),
            "El campo username es obligatorio.",
        )
        self.assertEqual(
            self.mensaje(LoginRequest, {"username": "admin", "password": None}),
            "El campo password es obligatorio.",
        )
        self.assertEqual(
            self.mensaje(IngresoRequest, {"codigo": None, "cantidad": 1}),
            "El campo codigo es obligatorio.",
        )
        # Un tipo incorrecto distinto de null sigue siendo "debe ser texto".
        self.assertEqual(
            self.mensaje(IngresoRequest, {"codigo": 5, "cantidad": 1}),
            "El campo codigo debe ser texto.",
        )

    def test_nombre_null_es_valido_como_no_enviado(self):
        modelo = IngresoRequest.model_validate({"codigo": "A", "cantidad": 1, "nombre": None})
        self.assertIsNone(modelo.nombre)

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


class MensajeOrdenTest(unittest.TestCase):
    def mensaje(self, datos):
        errores = [{**e, "loc": ("body", *e["loc"])} for e in errores_de(OrdenRequest, datos)]
        return mensaje_validacion(errores)

    def orden(self, **cambios):
        base = {
            "numero": "OT-1",
            "fecha": "2026-11-20",
            "componentes": [{"codigo": "A-01", "cantidad": 1}],
        }
        base.update(cambios)
        return base

    def test_segundo_componente_sin_codigo(self):
        datos = self.orden(componentes=[{"codigo": "A-01", "cantidad": 1}, {"cantidad": 2}])
        self.assertEqual(self.mensaje(datos), "Componente 2: El campo codigo es obligatorio.")

    def test_codigo_vacio_o_largo_en_una_linea(self):
        self.assertEqual(
            self.mensaje(self.orden(componentes=[{"codigo": "  ", "cantidad": 1}])),
            "Componente 1: El campo codigo es obligatorio.",
        )
        self.assertEqual(
            self.mensaje(self.orden(componentes=[{"codigo": "c" * 51, "cantidad": 1}])),
            "Componente 1: El campo codigo admite hasta 50 caracteres.",
        )

    def test_cantidad_invalida_en_una_linea(self):
        for cantidad in ("5", 2.5, 0, True, 10001):
            with self.subTest(cantidad=cantidad):
                datos = self.orden(componentes=[{"codigo": "A-01", "cantidad": cantidad}])
                self.assertEqual(self.mensaje(datos), f"Componente 1: {MSG_CANTIDAD}")

    def test_cantidad_faltante_en_una_linea(self):
        datos = self.orden(componentes=[{"codigo": "A-01"}])
        self.assertEqual(self.mensaje(datos), "Componente 1: El campo cantidad es obligatorio.")

    def test_componentes_vacio_largo_y_no_lista(self):
        self.assertEqual(
            self.mensaje(self.orden(componentes=[])), "La orden requiere al menos un componente."
        )
        largo = [{"codigo": "A-01", "cantidad": 1}] * 101
        self.assertEqual(
            self.mensaje(self.orden(componentes=largo)), "La orden admite hasta 100 componentes."
        )
        for valor in ("A-01", {"codigo": "A-01"}, 5):
            with self.subTest(valor=valor):
                self.assertEqual(
                    self.mensaje(self.orden(componentes=valor)),
                    "El campo componentes debe ser una lista.",
                )

    def test_componentes_faltante(self):
        datos = self.orden()
        del datos["componentes"]
        self.assertEqual(self.mensaje(datos), "El campo componentes es obligatorio.")

    def test_linea_que_no_es_objeto(self):
        for valor in ("A-01", 5, ["A-01", 1]):
            with self.subTest(valor=valor):
                self.assertEqual(
                    self.mensaje(self.orden(componentes=[valor])),
                    "Componente 1: debe ser un objeto con codigo y cantidad.",
                )

    def test_fecha_faltante_o_vacia_y_tipo(self):
        sin_fecha = self.orden()
        del sin_fecha["fecha"]
        self.assertEqual(self.mensaje(sin_fecha), "El campo fecha es obligatorio.")
        self.assertEqual(self.mensaje(self.orden(fecha="")), "El campo fecha es obligatorio.")
        self.assertEqual(self.mensaje(self.orden(fecha=20261120)), "El campo fecha debe ser texto.")

    def test_null_en_campos_obligatorios_de_la_orden(self):
        self.assertEqual(self.mensaje(self.orden(fecha=None)), "El campo fecha es obligatorio.")
        self.assertEqual(self.mensaje(self.orden(numero=None)), "El campo numero es obligatorio.")
        self.assertEqual(
            self.mensaje(self.orden(componentes=None)), "El campo componentes es obligatorio."
        )
        self.assertEqual(
            self.mensaje(self.orden(componentes=[{"codigo": None, "cantidad": 1}])),
            "Componente 1: El campo codigo es obligatorio.",
        )
        self.assertEqual(self.mensaje(self.orden(numero=5)), "El campo numero debe ser texto.")

    def test_fecha_con_espacios_o_salto_de_linea_no_se_recorta(self):
        # El recorte lo haria Pydantic antes de que el service valide el formato.
        for fecha in (" 2026-11-20 ", "2026-11-20\n", "\t2026-11-20"):
            with self.subTest(fecha=repr(fecha)):
                modelo = OrdenRequest.model_validate(self.orden(fecha=fecha))
                self.assertEqual(modelo.fecha, fecha)

    def test_numero_y_codigo_siguen_recortandose(self):
        modelo = OrdenRequest.model_validate(
            self.orden(numero="  ot-1 ", componentes=[{"codigo": " a-01 ", "cantidad": 1}])
        )
        self.assertEqual(modelo.numero, "ot-1")
        self.assertEqual(modelo.componentes[0].codigo, "a-01")

    def test_numero_largo_y_vacio(self):
        self.assertEqual(
            self.mensaje(self.orden(numero="X" * 31)),
            "El campo numero admite hasta 30 caracteres.",
        )
        self.assertEqual(
            self.mensaje(self.orden(numero="   ")), "El campo numero es obligatorio."
        )


if __name__ == "__main__":
    unittest.main()
