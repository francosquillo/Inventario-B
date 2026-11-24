"""Reporte de productos usados en ordenes: validacion de filtros y delegacion al repositorio."""
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ahora_argentina
from inventario.services.fechas import parsear_filtro_fecha, validar_rango
from inventario.services.normalizacion import normalizar_codigo

MENSAJE_DESDE_OBLIGATORIA = "La fecha 'desde' es obligatoria."


def _en_blanco(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip())


class ReporteService:
    def __init__(self, orden_repo, ahora=ahora_argentina):
        self._repo = orden_repo
        self._ahora = ahora

    def productos_en_ordenes(self, desde, hasta=None, codigo=None):
        if _en_blanco(desde):
            raise DatosInvalidos(MENSAJE_DESDE_OBLIGATORIA)
        f_desde = parsear_filtro_fecha("desde", desde)
        if _en_blanco(hasta):
            f_hasta = self._ahora().date()
            texto_hasta = f_hasta.isoformat()
        else:
            texto_hasta = hasta
            f_hasta = parsear_filtro_fecha("hasta", hasta)
        validar_rango(desde, texto_hasta, f_desde, f_hasta)
        codigo = None if _en_blanco(codigo) else normalizar_codigo(codigo)
        return self._repo.productos_en_ordenes(f_desde, f_hasta, codigo)

    def productos_usados(self):
        return self._repo.productos_usados()
