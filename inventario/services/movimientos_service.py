"""Consulta de la bitacora de movimientos: validacion de filtros."""
from inventario.domain.errors import DatosInvalidos
from inventario.services.fechas import parsear_fecha
from inventario.services.normalizacion import normalizar_codigo


def _parsear_fecha(nombre, valor):
    """None o vacio -> sin limite; si no, AAAA-MM-DD y fecha real."""
    if valor is None or valor == "":
        return None
    return parsear_fecha(
        valor,
        f"La fecha '{nombre}' debe tener formato AAAA-MM-DD.",
        f"La fecha '{nombre}' ({{valor}}) no es una fecha válida.",
    )


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
