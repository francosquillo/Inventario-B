"""Ingreso y egreso de stock: validacion, normalizacion y fuente de tiempo."""
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ahora_argentina
from inventario.services.normalizacion import normalizar_codigo, validar_cantidad

NOMBRE_MAX = 120
MENSAJE_NOMBRE_LARGO = f"El campo nombre admite hasta {NOMBRE_MAX} caracteres."
MENSAJE_NOMBRE_TIPO = "El campo nombre debe ser texto."


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
        cantidad = validar_cantidad(cantidad)
        nombre = _normalizar_nombre(nombre)
        return self._repo.registrar_ingreso(codigo, cantidad, nombre, usuario_id, self._ahora())

    def egresar(self, codigo, cantidad, usuario_id):
        codigo = normalizar_codigo(codigo)
        cantidad = validar_cantidad(cantidad)
        return self._repo.registrar_egreso(codigo, cantidad, usuario_id, self._ahora())
