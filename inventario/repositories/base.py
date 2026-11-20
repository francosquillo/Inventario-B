"""Contratos de repositorio (los implementa SQLite hoy, Supabase en el Paso 5)."""
from abc import ABC, abstractmethod
from datetime import date, datetime

from inventario.domain.entities import (
    Movimiento,
    Orden,
    Producto,
    ResultadoBorradoOrden,
    ResultadoIngreso,
    Usuario,
)


class UsuarioRepository(ABC):
    @abstractmethod
    def obtener_por_username(self, username: str) -> "Usuario | None": ...

    @abstractmethod
    def obtener_por_id(self, usuario_id: int) -> "Usuario | None": ...

    @abstractmethod
    def crear(self, username: str, password_hash: str, salt: str) -> Usuario: ...


class ProductoRepository(ABC):
    @abstractmethod
    def listar_activos(self) -> "list[Producto]": ...

    @abstractmethod
    def dar_de_baja(self, codigo: str) -> Producto:
        """activo = 0 sobre un producto activo (codigo ya normalizado). Conserva el stock.

        No escribe en `movimientos`. Lanza ProductoNoEncontrado si no existe o ya esta inactivo.
        """


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


class OrdenRepository(ABC):
    """Unidad de trabajo atomica (en Postgres sera la funcion RPC `crear_orden`)."""

    @abstractmethod
    def crear(
        self,
        numero: str,
        fecha: date,
        items: "list[tuple[str, int]]",
        usuario_id: int,
        creada_en: datetime,
    ) -> Orden:
        """Crea la orden y descuenta el stock; todo o nada.

        `items` llega validado y consolidado: (codigo, cantidad_total) en orden de
        primera aparicion, codigos unicos. No escribe en `movimientos` (RN-ST-06).
        Lanza OrdenDuplicada, ProductosNoEncontrados o StockInsuficienteOrden.
        """

    @abstractmethod
    def listar(
        self, numero: "str | None", desde: "date | None", hasta: "date | None"
    ) -> "list[Orden]":
        """Ordenes con sus componentes, de la mas nueva a la mas vieja.

        Ordena por `fecha` DESC y luego `id` DESC; componentes por codigo. Los filtros
        son opcionales y se combinan con AND: `numero` exacto (ya normalizado) y
        `desde`/`hasta` inclusivos sobre la fecha de la orden. Incluye los componentes
        de productos dados de baja.
        """

    @abstractmethod
    def existe_numero(self, numero: str) -> bool:
        """True si hay una orden con ese numero exacto (ya normalizado), sin importar la fecha."""

    @abstractmethod
    def borrar(self, numero: str, reintegrar: bool) -> ResultadoBorradoOrden:
        """Borra la orden y sus lineas (numero ya normalizado); si `reintegrar`, devuelve el stock
        y reactiva. Todo o nada. No escribe en `movimientos` (DD-09). Lanza OrdenNoEncontrada.

        En Postgres sera la funcion RPC `borrar_orden(p_numero, p_reintegrar)`.
        """
