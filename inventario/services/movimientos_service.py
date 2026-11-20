"""Consulta de la bitacora de movimientos: validacion de filtros."""
import re
from datetime import date

from inventario.domain.errors import DatosInvalidos
from inventario.services.normalizacion import normalizar_codigo

_FORMATO_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _parsear_fecha(nombre, valor):
    """None o vacio -> sin limite; si no, AAAA-MM-DD y fecha real."""
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str) or not _FORMATO_FECHA.fullmatch(valor):
        raise DatosInvalidos(f"La fecha '{nombre}' debe tener formato AAAA-MM-DD.")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise DatosInvalidos(f"La fecha '{nombre}' ({valor}) no es una fecha válida.") from None


class MovimientosService:
    def __init__(self, movimiento_repo):
        self._repo = movimiento_repo

    def listar(self, codigo=None, desde=None, hasta=None):
        if codigo is None or (isinstance(codigo, str) and not codigo.strip()):
            codigo = None
        else:
            codigo = normalizar_codigo(codigo)
        f_desde = _parsear_fecha("desde", desde)
        f_hasta = _parsear_fecha("hasta", hasta)
        if f_desde and f_hasta and f_desde > f_hasta:
            raise DatosInvalidos(
                f"La fecha 'desde' ({desde}) no puede ser posterior a 'hasta' ({hasta})."
            )
        return self._repo.listar(codigo, f_desde, f_hasta)
