"""Contratos de repositorio (los implementa SQLite hoy, Supabase en el Paso 5)."""
from abc import ABC, abstractmethod
from datetime import date, datetime

from inventario.domain.entities import Movimiento, Producto, ResultadoIngreso, Usuario


class UsuarioRepository(ABC):
    @abstractmethod
    def obtener_por_username(self, username: str) -> "Usuario | None": ...

    @abstractmethod
    def crear(self, username: str, password_hash: str, salt: str) -> Usuario: ...


class ProductoRepository(ABC):
    @abstractmethod
    def listar_activos(self) -> "list[Producto]": ...


class StockRepository(ABC):
    """Cada metodo es una unidad de trabajo atomica (en Postgres sera una funcion RPC)."""

    @abstractmethod
    def registrar_ingreso(
        self, codigo: str, cantidad: int, nombre: "str | None", usuario_id: int, fecha: datetime
    ) -> ResultadoIngreso: ...

    @abstractmethod
    def registrar_egreso(
        self, codigo: str, cantidad: int, usuario_id: int, fecha: datetime
    ) -> Producto: ...


class MovimientoRepository(ABC):
    @abstractmethod
    def listar(
        self, codigo: "str | None", desde: "date | None", hasta: "date | None"
    ) -> "list[Movimiento]": ...
