"""Alta de ordenes de trabajo: validacion, normalizacion y consolidacion de componentes."""
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ahora_argentina
from inventario.services.fechas import parsear_fecha
from inventario.services.normalizacion import normalizar_codigo, validar_cantidad

NUMERO_MAX = 30
COMPONENTES_MAX = 100
MENSAJE_NUMERO_OBLIGATORIO = "El campo numero es obligatorio."
MENSAJE_NUMERO_LARGO = f"El campo numero admite hasta {NUMERO_MAX} caracteres."
MENSAJE_NUMERO_TIPO = "El campo numero debe ser texto."
MENSAJE_FECHA_OBLIGATORIA = "El campo fecha es obligatorio."
MENSAJE_FECHA_FORMATO = "La fecha debe tener formato AAAA-MM-DD."
MENSAJE_FECHA_INVALIDA = "La fecha ({valor}) no es una fecha válida."
MENSAJE_COMPONENTES_OBLIGATORIO = "El campo componentes es obligatorio."
MENSAJE_COMPONENTES_TIPO = "El campo componentes debe ser una lista."
MENSAJE_SIN_COMPONENTES = "La orden requiere al menos un componente."
MENSAJE_DEMASIADOS = f"La orden admite hasta {COMPONENTES_MAX} componentes."
MENSAJE_LINEA_TIPO = "debe ser un objeto con codigo y cantidad."


def _normalizar_numero(numero):
    if numero is None or (isinstance(numero, str) and not numero.strip()):
        raise DatosInvalidos(MENSAJE_NUMERO_OBLIGATORIO)
    if not isinstance(numero, str):
        raise DatosInvalidos(MENSAJE_NUMERO_TIPO)
    numero = numero.strip().upper()
    if len(numero) > NUMERO_MAX:
        raise DatosInvalidos(MENSAJE_NUMERO_LARGO)
    return numero


def _parsear_fecha(fecha):
    if fecha is None or fecha == "":
        raise DatosInvalidos(MENSAJE_FECHA_OBLIGATORIA)
    return parsear_fecha(fecha, MENSAJE_FECHA_FORMATO, MENSAJE_FECHA_INVALIDA)


def _validar_linea(posicion, linea):
    """Devuelve (codigo, cantidad) validados; el error lleva el numero de linea (desde 1)."""
    try:
        if not isinstance(linea, (tuple, list)) or len(linea) != 2:
            raise DatosInvalidos(MENSAJE_LINEA_TIPO)
        codigo, cantidad = linea
        return normalizar_codigo(codigo), validar_cantidad(cantidad)
    except DatosInvalidos as exc:
        raise DatosInvalidos(f"Componente {posicion}: {exc}") from None


def _consolidar(componentes):
    """Valida cada linea y suma las repetidas, en orden de primera aparicion.

    El tope de 10.000 rige por linea; el total consolidado solo lo limita el stock.
    """
    if componentes is None:
        raise DatosInvalidos(MENSAJE_COMPONENTES_OBLIGATORIO)
    if not isinstance(componentes, (list, tuple)):
        raise DatosInvalidos(MENSAJE_COMPONENTES_TIPO)
    if not componentes:
        raise DatosInvalidos(MENSAJE_SIN_COMPONENTES)
    if len(componentes) > COMPONENTES_MAX:
        raise DatosInvalidos(MENSAJE_DEMASIADOS)
    totales = {}
    for posicion, linea in enumerate(componentes, start=1):
        codigo, cantidad = _validar_linea(posicion, linea)
        totales[codigo] = totales.get(codigo, 0) + cantidad
    return list(totales.items())


class OrdenService:
    def __init__(self, orden_repo, ahora=ahora_argentina):
        self._repo = orden_repo
        self._ahora = ahora

    def crear(self, numero, fecha, componentes, usuario_id):
        numero = _normalizar_numero(numero)
        f_orden = _parsear_fecha(fecha)
        items = _consolidar(componentes)
        return self._repo.crear(numero, f_orden, items, usuario_id, self._ahora())
