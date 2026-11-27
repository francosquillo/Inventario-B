"""Catalogo de servicios generales: listado, alta, modificacion y borrado (la clave es inmutable)."""
from inventario.domain.errors import (
    DatosInvalidos,
    ServicioGeneralDuplicado,
    ServicioGeneralNoEncontrado,
)
from inventario.services.normalizacion import (
    MENSAJE_CLAVE_SERVICIO,
    clave_desde_texto,
    normalizar_chequeos,
    normalizar_nombre_servicio,
    validar_clave_servicio,
)

MENSAJE_SIN_CAMBIOS = "Indicá el nombre o los chequeos a modificar."
SIN_CAMBIO = object()  # el campo no viene en la modificacion (distinto de un None explicito)


def _clave_de_ruta(clave):
    if not isinstance(clave, str) or not clave.strip():
        raise DatosInvalidos(MENSAJE_CLAVE_SERVICIO)
    return clave.strip().lower()


class ServicioGeneralService:
    def __init__(self, servicio_repo):
        self._repo = servicio_repo

    def listar(self):
        return self._repo.listar()

    def crear(self, nombre, chequeos, clave=None):
        nombre = normalizar_nombre_servicio(nombre)
        if clave is None or (isinstance(clave, str) and not clave.strip()):
            clave = clave_desde_texto(nombre, MENSAJE_CLAVE_SERVICIO)
        elif not isinstance(clave, str):
            raise DatosInvalidos("El campo clave debe ser texto.")
        else:
            clave = validar_clave_servicio(clave.strip().lower())
        chequeos = normalizar_chequeos(chequeos)
        # El nombre repetido gana: sin clave indicada, la derivada coincidiria con la existente.
        self._validar_nombre_libre(nombre, excepto=None)
        if self._repo.obtener(clave) is not None:
            raise ServicioGeneralDuplicado("clave", clave)
        return self._repo.crear(clave, nombre, chequeos)

    def modificar(self, clave, nombre=SIN_CAMBIO, chequeos=SIN_CAMBIO):
        clave = _clave_de_ruta(clave)
        if nombre is SIN_CAMBIO and chequeos is SIN_CAMBIO:
            raise DatosInvalidos(MENSAJE_SIN_CAMBIOS)
        # Todo se valida antes de escribir: un chequeo invalido no deja pasar un renombre.
        nuevo_nombre = None if nombre is SIN_CAMBIO else normalizar_nombre_servicio(nombre)
        nuevos_chequeos = None if chequeos is SIN_CAMBIO else normalizar_chequeos(chequeos)
        if self._repo.obtener(clave) is None:
            raise ServicioGeneralNoEncontrado(clave)
        if nuevo_nombre is not None:
            self._validar_nombre_libre(nuevo_nombre, excepto=clave)
        return self._repo.modificar(clave, nombre=nuevo_nombre, chequeos=nuevos_chequeos)

    def borrar(self, clave):
        return self._repo.borrar(_clave_de_ruta(clave))

    def _validar_nombre_libre(self, nombre, excepto):
        """Unicidad sin distinguir mayusculas (casefold); la BD es la red ante carreras."""
        buscado = nombre.casefold()
        for otro in self._repo.listar():
            if otro.clave != excepto and otro.nombre.casefold() == buscado:
                raise ServicioGeneralDuplicado("nombre", nombre)
