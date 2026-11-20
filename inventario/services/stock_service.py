"""Ingreso y egreso de stock: validacion, normalizacion y fuente de tiempo."""
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ahora_argentina
from inventario.services.normalizacion import normalizar_codigo

NOMBRE_MAX = 120
CANTIDAD_MAX = 10_000
MENSAJE_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."
MENSAJE_NOMBRE_LARGO = f"El campo nombre admite hasta {NOMBRE_MAX} caracteres."
MENSAJE_NOMBRE_TIPO = "El campo nombre debe ser texto."


def _validar_cantidad(cantidad):
    # type() is int: rechaza bool, float y str.
    if type(cantidad) is not int or not 1 <= cantidad <= CANTIDAD_MAX:
        raise DatosInvalidos(MENSAJE_CANTIDAD)
    return cantidad


def _normalizar_nombre(nombre):
    if nombre is None:
        return None
    if not isinstance(nombre, str):
        raise DatosInvalidos(MENSAJE_NOMBRE_TIPO)
    nombre = nombre.strip()
    if len(nombre) > NOMBRE_MAX:
        raise DatosInvalidos(MENSAJE_NOMBRE_LARGO)
    return nombre or None


class StockService:
    def __init__(self, stock_repo, ahora=ahora_argentina):
        self._repo = stock_repo
        self._ahora = ahora

    def ingresar(self, codigo, cantidad, nombre, usuario_id):
        codigo = normalizar_codigo(codigo)
        cantidad = _validar_cantidad(cantidad)
        nombre = _normalizar_nombre(nombre)
        return self._repo.registrar_ingreso(codigo, cantidad, nombre, usuario_id, self._ahora())

    def egresar(self, codigo, cantidad, usuario_id):
        codigo = normalizar_codigo(codigo)
        cantidad = _validar_cantidad(cantidad)
        return self._repo.registrar_egreso(codigo, cantidad, usuario_id, self._ahora())
