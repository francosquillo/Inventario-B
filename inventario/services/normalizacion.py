"""Normalizacion del codigo de producto: unica puerta de entrada (D3/D7)."""
from inventario.domain.errors import DatosInvalidos

CODIGO_MAX = 50
MENSAJE_CODIGO_OBLIGATORIO = "El campo codigo es obligatorio."
MENSAJE_CODIGO_LARGO = f"El campo codigo admite hasta {CODIGO_MAX} caracteres."


def normalizar_codigo(codigo):
    """Recorta y pasa a MAYUSCULAS. Lanza DatosInvalidos si esta vacio o es muy largo."""
    if not isinstance(codigo, str) or not codigo.strip():
        raise DatosInvalidos(MENSAJE_CODIGO_OBLIGATORIO)
    normalizado = codigo.strip().upper()
    if len(normalizado) > CODIGO_MAX:
        raise DatosInvalidos(MENSAJE_CODIGO_LARGO)
    return normalizado


CANTIDAD_MAX = 10_000
MENSAJE_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


STOCK_MAX = 10_000
MENSAJE_STOCK = "El stock debe ser un entero entre 0 y 10.000."


def validar_stock(stock):
    """Stock absoluto (alta y 'fijar'): entero de 0 a 10.000; type() is int rechaza bool."""
    if type(stock) is not int or not 0 <= stock <= STOCK_MAX:
        raise DatosInvalidos(MENSAJE_STOCK)
    return stock


def validar_cantidad(cantidad):
    # type() is int: rechaza bool, float y str.
    if type(cantidad) is not int or not 1 <= cantidad <= CANTIDAD_MAX:
        raise DatosInvalidos(MENSAJE_CANTIDAD)
    return cantidad
