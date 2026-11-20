"""Consulta de la bitacora de movimientos: validacion de filtros."""
from inventario.services.fechas import parsear_filtro_fecha, validar_rango
from inventario.services.normalizacion import normalizar_codigo


class MovimientosService:
    def __init__(self, movimiento_repo):
        self._repo = movimiento_repo

    def listar(self, codigo=None, desde=None, hasta=None):
        if codigo is None or (isinstance(codigo, str) and not codigo.strip()):
            codigo = None
        else:
            codigo = normalizar_codigo(codigo)
        f_desde = parsear_filtro_fecha("desde", desde)
        f_hasta = parsear_filtro_fecha("hasta", hasta)
        validar_rango(desde, hasta, f_desde, f_hasta)
        return self._repo.listar(codigo, f_desde, f_hasta)
