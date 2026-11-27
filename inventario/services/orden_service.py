"""Alta de ordenes de trabajo: validacion, normalizacion y consolidacion de componentes."""
from inventario.domain.entities import ProcesoOrden, ServicioOrden
from inventario.domain.errors import DatosInvalidos, OrdenNoEncontrada
from inventario.domain.tiempo import ahora_argentina
from inventario.services.fechas import parsear_fecha, parsear_filtro_fecha, validar_rango
from inventario.services.normalizacion import (
    MENSAJE_NOMBRE_PROCESO_LARGO,
    PROCESO_NOMBRE_MAX,
    normalizar_codigo,
    validar_cantidad,
)

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
MENSAJE_REINTEGRAR_OBLIGATORIO = "El campo reintegrar es obligatorio."
MENSAJE_REINTEGRAR_VALOR = "El campo reintegrar debe ser true o false."
MENSAJE_LINEA_TIPO = "debe ser un objeto con codigo y cantidad."
PERSONALIZADOS_MAX = 10
CLAVE_ERROR_MAX = 30
MENSAJE_PROCESOS_TIPO = "El campo procesos debe ser una lista de textos."
MENSAJE_PERSONALIZADOS_TIPO = "El campo procesos_personalizados debe ser una lista de textos."
MENSAJE_SERVICIO_TIPO = "El campo servicio debe ser texto."
MENSAJE_PERSONALIZADOS_DEMASIADOS = (
    f"La orden admite hasta {PERSONALIZADOS_MAX} procesos personalizados."
)


def _normalizar_numero(numero):
    if numero is None or (isinstance(numero, str) and not numero.strip()):
        raise DatosInvalidos(MENSAJE_NUMERO_OBLIGATORIO)
    if not isinstance(numero, str):
        raise DatosInvalidos(MENSAJE_NUMERO_TIPO)
    numero = numero.strip().upper()
    if len(numero) > NUMERO_MAX:
        raise DatosInvalidos(MENSAJE_NUMERO_LARGO)
    return numero


def _normalizar_numero_filtro(numero):
    """Filtro opcional: None o en blanco -> sin filtro; si no, la misma normalizacion del alta."""
    if numero is None or (isinstance(numero, str) and not numero.strip()):
        return None
    return _normalizar_numero(numero)


def _parsear_reintegrar(reintegrar):
    """Solo "true"/"false" exactos (minusculas); un bool de Python pasa tal cual."""
    if isinstance(reintegrar, bool):
        return reintegrar
    if reintegrar is None or (isinstance(reintegrar, str) and reintegrar == ""):
        raise DatosInvalidos(MENSAJE_REINTEGRAR_OBLIGATORIO)
    if reintegrar == "true":
        return True
    if reintegrar == "false":
        return False
    raise DatosInvalidos(MENSAJE_REINTEGRAR_VALOR)


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


def _lista_de_textos(valor, mensaje):
    """None -> []; si no es lista (o tupla) de str, DatosInvalidos con `mensaje`."""
    if valor is None:
        return []
    if not isinstance(valor, (list, tuple)) or not all(isinstance(v, str) for v in valor):
        raise DatosInvalidos(mensaje)
    return list(valor)


def _recortar(clave):
    return clave if len(clave) <= CLAVE_ERROR_MAX else clave[:CLAVE_ERROR_MAX] + "…"


def _resolver_servicio(servicio, repo):
    """Clave del catalogo -> ServicioOrden (snapshot de nombre y chequeos); vacio/None = sin servicio."""
    if servicio is None:
        return None
    if not isinstance(servicio, str):
        raise DatosInvalidos(MENSAJE_SERVICIO_TIPO)
    clave = servicio.strip().lower()
    if not clave:
        return None
    encontrado = repo.obtener(clave)
    if encontrado is None:
        raise DatosInvalidos(f"El servicio general '{_recortar(clave)}' no existe.")
    return ServicioOrden(encontrado.nombre, tuple(encontrado.chequeos))


def _resolver_procesos(procesos, catalogo):
    """Claves del catalogo -> ProcesoOrden (sin repetir, primera aparicion), en el orden recibido."""
    claves = [c.strip().lower() for c in _lista_de_textos(procesos, MENSAJE_PROCESOS_TIPO)]
    por_clave = {p.clave: p.nombre for p in catalogo}
    resueltos = []
    for clave in dict.fromkeys(claves):
        if clave not in por_clave:
            raise DatosInvalidos(f"El proceso '{_recortar(clave)}' no existe.")
        resueltos.append(ProcesoOrden(por_clave[clave], False))
    return resueltos


def _validar_personalizados(personalizados, catalogo):
    """Textos libres: recortados, 1-60 caracteres, sin repetir ni coincidir con el catalogo."""
    textos = _lista_de_textos(personalizados, MENSAJE_PERSONALIZADOS_TIPO)
    if len(textos) > PERSONALIZADOS_MAX:
        raise DatosInvalidos(MENSAJE_PERSONALIZADOS_DEMASIADOS)
    del_catalogo = {p.nombre.casefold() for p in catalogo}
    vistos = set()
    validos = []
    for posicion, texto in enumerate(textos, start=1):
        nombre = texto.strip()
        if not nombre:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: El nombre es obligatorio.")
        if len(nombre) > PROCESO_NOMBRE_MAX:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: {MENSAJE_NOMBRE_PROCESO_LARGO}")
        clave = nombre.casefold()
        if clave in del_catalogo:
            raise DatosInvalidos(
                f"Proceso personalizado {posicion}: '{nombre}' ya está en la lista de procesos; "
                "marcalo ahí."
            )
        if clave in vistos:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: '{nombre}' está repetido.")
        vistos.add(clave)
        validos.append(ProcesoOrden(nombre, True))
    return validos


class OrdenService:
    def __init__(self, orden_repo, proceso_repo, servicio_repo, ahora=ahora_argentina):
        self._repo = orden_repo
        self._procesos = proceso_repo
        self._servicios = servicio_repo
        self._ahora = ahora

    def crear(
        self,
        numero,
        fecha,
        componentes,
        usuario_id,
        procesos=None,
        procesos_personalizados=None,
        servicio=None,
    ):
        numero = _normalizar_numero(numero)
        f_orden = _parsear_fecha(fecha)
        items = _consolidar(componentes)
        servicio_orden = _resolver_servicio(servicio, self._servicios)
        catalogo = self._procesos.listar()
        todos = _resolver_procesos(procesos, catalogo) + _validar_personalizados(
            procesos_personalizados, catalogo
        )
        return self._repo.crear(
            numero,
            f_orden,
            items,
            usuario_id,
            self._ahora(),
            procesos=tuple(todos),
            servicio=servicio_orden,
        )

    def listar(self, numero=None, desde=None, hasta=None):
        numero = _normalizar_numero_filtro(numero)
        f_desde = parsear_filtro_fecha("desde", desde)
        f_hasta = parsear_filtro_fecha("hasta", hasta)
        validar_rango(desde, hasta, f_desde, f_hasta)
        ordenes = self._repo.listar(numero, f_desde, f_hasta)
        # Vacio con numero: 404 solo si el numero no existe; si existe, quedo fuera del rango.
        if not ordenes and numero is not None and not self._repo.existe_numero(numero):
            raise OrdenNoEncontrada(numero)
        return ordenes

    def borrar(self, numero, reintegrar):
        # Primero gana el error de `reintegrar`; luego el de `numero`; el 404 lo da el repo.
        valor = _parsear_reintegrar(reintegrar)
        numero = _normalizar_numero(numero)
        return self._repo.borrar(numero, valor)
