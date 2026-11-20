"""Parseo estricto de fechas AAAA-MM-DD, compartido por movimientos y ordenes."""
import re
from datetime import date

from inventario.domain.errors import DatosInvalidos

_FORMATO_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parsear_fecha(valor, mensaje_formato, mensaje_invalida):
    """Devuelve `date`. `mensaje_invalida` admite el marcador `{valor}`."""
    if not isinstance(valor, str) or not _FORMATO_FECHA.fullmatch(valor):
        raise DatosInvalidos(mensaje_formato)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise DatosInvalidos(mensaje_invalida.format(valor=valor)) from None
