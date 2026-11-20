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


def parsear_filtro_fecha(nombre, valor):
    """Filtro opcional: None o vacio -> sin limite; si no, AAAA-MM-DD y fecha real."""
    if valor is None or valor == "":
        return None
    return parsear_fecha(
        valor,
        f"La fecha '{nombre}' debe tener formato AAAA-MM-DD.",
        f"La fecha '{nombre}' ({{valor}}) no es una fecha válida.",
    )


def validar_rango(texto_desde, texto_hasta, desde, hasta):
    """`desde`/`hasta` ya parseados (o None); los textos originales van en el mensaje."""
    if desde is not None and hasta is not None and desde > hasta:
        raise DatosInvalidos(
            f"La fecha 'desde' ({texto_desde}) no puede ser posterior a 'hasta' ({texto_hasta})."
        )
