"""Contratos de repositorio (los implementa SQLite hoy, Supabase en el Paso 5)."""
from abc import ABC, abstractmethod

from inventario.domain.entities import Producto, Usuario


class UsuarioRepository(ABC):
    @abstractmethod
    def obtener_por_username(self, username: str) -> "Usuario | None": ...

    @abstractmethod
    def crear(self, username: str, password_hash: str, salt: str) -> Usuario: ...


class ProductoRepository(ABC):
    @abstractmethod
    def listar_activos(self) -> "list[Producto]": ...
