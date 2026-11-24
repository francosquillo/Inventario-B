"""Catalogo de categorias: listado, alta y renombrado (la clave es inmutable)."""
from inventario.domain.errors import CategoriaDuplicada, CategoriaNoEncontrada, DatosInvalidos
from inventario.services.normalizacion import (
    MENSAJE_CLAVE_CATEGORIA,
    clave_desde_texto,
    normalizar_nombre_categoria,
    validar_clave_categoria,
)


class CategoriaService:
    def __init__(self, categoria_repo):
        self._repo = categoria_repo

    def listar(self):
        return self._repo.listar()

    def crear(self, nombre, clave=None):
        nombre = normalizar_nombre_categoria(nombre)
        if clave is None or (isinstance(clave, str) and not clave.strip()):
            clave = clave_desde_texto(nombre)
        elif not isinstance(clave, str):
            raise DatosInvalidos("El campo clave debe ser texto.")
        else:
            clave = validar_clave_categoria(clave.strip().lower())
        if self._repo.obtener(clave) is not None:
            raise CategoriaDuplicada("clave", clave)
        self._validar_nombre_libre(nombre, excepto=None)
        return self._repo.crear(clave, nombre)

    def renombrar(self, clave, nombre):
        if not isinstance(clave, str) or not clave.strip():
            raise DatosInvalidos(MENSAJE_CLAVE_CATEGORIA)
        clave = clave.strip().lower()
        nombre = normalizar_nombre_categoria(nombre)
        if self._repo.obtener(clave) is None:
            raise CategoriaNoEncontrada(clave)
        self._validar_nombre_libre(nombre, excepto=clave)
        return self._repo.renombrar(clave, nombre)

    def _validar_nombre_libre(self, nombre, excepto):
        """Unicidad sin distinguir mayusculas (casefold); la BD es la red ante carreras."""
        buscado = nombre.casefold()
        for otra in self._repo.listar():
            if otra.clave != excepto and otra.nombre.casefold() == buscado:
                raise CategoriaDuplicada("nombre", nombre)
