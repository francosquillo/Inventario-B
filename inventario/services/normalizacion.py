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
