"""Entidades de dominio inmutables."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    id: int
    username: str
    password_hash: str
    salt: str


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: int
    username: str


@dataclass(frozen=True)
class Producto:
    id: int
    codigo: str
    nombre: str
    stock: int
    activo: bool

    @property
    def sin_stock(self):
        return self.stock == 0
