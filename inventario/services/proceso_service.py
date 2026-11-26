"""Catalogo de procesos de ordenes: listado, alta, renombrado y borrado (la clave es inmutable)."""
from inventario.domain.errors import DatosInvalidos, ProcesoDuplicado, ProcesoNoEncontrado
from inventario.services.normalizacion import (
    MENSAJE_CLAVE_PROCESO,
    clave_desde_texto,
    normalizar_nombre_proceso,
    validar_clave_proceso,
)


def _clave_de_ruta(clave):
    if not isinstance(clave, str) or not clave.strip():
        raise DatosInvalidos(MENSAJE_CLAVE_PROCESO)
    return clave.strip().lower()


class ProcesoService:
    def __init__(self, proceso_repo):
        self._repo = proceso_repo

    def listar(self):
        return self._repo.listar()

    def crear(self, nombre, clave=None):
        nombre = normalizar_nombre_proceso(nombre)
        if clave is None or (isinstance(clave, str) and not clave.strip()):
            clave = clave_desde_texto(nombre, MENSAJE_CLAVE_PROCESO)
        elif not isinstance(clave, str):
            raise DatosInvalidos("El campo clave debe ser texto.")
        else:
            clave = validar_clave_proceso(clave.strip().lower())
        if self._repo.obtener(clave) is not None:
            raise ProcesoDuplicado("clave", clave)
        self._validar_nombre_libre(nombre, excepto=None)
        return self._repo.crear(clave, nombre)

    def renombrar(self, clave, nombre):
        clave = _clave_de_ruta(clave)
        nombre = normalizar_nombre_proceso(nombre)
        if self._repo.obtener(clave) is None:
            raise ProcesoNoEncontrado(clave)
        self._validar_nombre_libre(nombre, excepto=clave)
        return self._repo.renombrar(clave, nombre)

    def borrar(self, clave):
        return self._repo.borrar(_clave_de_ruta(clave))

    def _validar_nombre_libre(self, nombre, excepto):
        """Unicidad sin distinguir mayusculas (casefold); la BD es la red ante carreras."""
        buscado = nombre.casefold()
        for otro in self._repo.listar():
            if otro.clave != excepto and otro.nombre.casefold() == buscado:
                raise ProcesoDuplicado("nombre", nombre)
