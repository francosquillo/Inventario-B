"""Baja logica de productos: normalizacion del codigo y delegacion al repositorio."""
from inventario.services.normalizacion import normalizar_codigo


class ProductoService:
    def __init__(self, producto_repo):
        self._repo = producto_repo

    def listar_inactivos(self):
        return self._repo.listar_inactivos()

    def dar_de_baja(self, codigo):
        return self._repo.dar_de_baja(normalizar_codigo(codigo))
