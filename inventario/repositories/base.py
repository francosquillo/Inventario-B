"""Contratos de repositorio (los implementa SQLite hoy, Supabase en el Paso 5)."""
from abc import ABC, abstractmethod
from datetime import date, datetime

from inventario.domain.entities import (
    Categoria,
    DatosOrden,
    Proceso,
    ProcesoOrden,
    ServicioGeneral,
    ServicioOrden,
    LineaModificacion,
    Movimiento,
    Orden,
    Producto,
    ProductoEnOrdenes,
    ProductoUsado,
    ResultadoBorradoOrden,
    ResultadoIngreso,
    ResultadoModificacion,
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
    def listar_inactivos(self) -> "list[Producto]":
        """Productos dados de baja (activo = 0), ordenados por codigo."""

    @abstractmethod
    def dar_de_baja(self, codigo: str) -> Producto:
        """activo = 0 sobre un producto activo (codigo ya normalizado). Conserva el stock.

        No escribe en `movimientos`. Lanza ProductoNoEncontrado si no existe o ya esta inactivo.
        """


class CategoriaRepository(ABC):
    @abstractmethod
    def listar(self) -> "list[Categoria]":
        """Catalogo ordenado por nombre (y clave)."""

    @abstractmethod
    def obtener(self, clave: str) -> "Categoria | None": ...

    @abstractmethod
    def crear(self, clave: str, nombre: str) -> Categoria:
        """Datos ya validados. Lanza CategoriaDuplicada si la clave o el nombre ya existen."""

    @abstractmethod
    def renombrar(self, clave: str, nombre: str) -> Categoria:
        """Cambia solo el nombre. Lanza CategoriaNoEncontrada o CategoriaDuplicada."""

    @abstractmethod
    def borrar(self, clave: str) -> Categoria:
        """Borra y devuelve la categoria. Lanza CategoriaNoEncontrada o CategoriaEnUso."""


class ProcesoRepository(ABC):
    @abstractmethod
    def listar(self) -> "list[Proceso]":
        """Catalogo ordenado por nombre (y clave)."""

    @abstractmethod
    def obtener(self, clave: str) -> "Proceso | None": ...

    @abstractmethod
    def crear(self, clave: str, nombre: str) -> Proceso:
        """Datos ya validados. Lanza ProcesoDuplicado si la clave o el nombre ya existen."""

    @abstractmethod
    def renombrar(self, clave: str, nombre: str) -> Proceso:
        """Cambia solo el nombre. Lanza ProcesoNoEncontrado o ProcesoDuplicado."""

    @abstractmethod
    def borrar(self, clave: str) -> Proceso:
        """Borra y devuelve el proceso (las ordenes conservan su snapshot). Lanza ProcesoNoEncontrado."""


class ServicioGeneralRepository(ABC):
    @abstractmethod
    def listar(self) -> "list[ServicioGeneral]":
        """Catalogo ordenado por nombre (y clave), con los chequeos en orden."""

    @abstractmethod
    def obtener(self, clave: str) -> "ServicioGeneral | None": ...

    @abstractmethod
    def crear(self, clave: str, nombre: str, chequeos: "tuple[str, ...]") -> ServicioGeneral:
        """Datos ya validados. Lanza ServicioGeneralDuplicado si la clave o el nombre ya existen."""

    @abstractmethod
    def modificar(
        self,
        clave: str,
        nombre: "str | None" = None,
        chequeos: "tuple[str, ...] | None" = None,
    ) -> ServicioGeneral:
        """Cambia el nombre y/o reemplaza todos los chequeos, todo o nada.

        Lanza ServicioGeneralNoEncontrado o ServicioGeneralDuplicado.
        """

    @abstractmethod
    def borrar(self, clave: str) -> ServicioGeneral:
        """Borra y devuelve el servicio (las ordenes conservan su snapshot).

        Lanza ServicioGeneralNoEncontrado.
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

    @abstractmethod
    def dar_de_alta(
        self,
        codigo: str,
        nombre: str,
        stock: int,
        usuario_id: int,
        fecha: datetime,
        categoria: "str | None" = None,
    ) -> ResultadoIngreso:
        """Alta explicita (datos ya validados y normalizados); todo o nada.

        `categoria` es la clave de una categoria existente o None; una reactivacion la reemplaza.

        Producto nuevo: activo con `stock` y, si stock > 0, un `ingreso`. Activo existente:
        ProductoDuplicado. Inactivo: se reactiva con nombre y stock nuevos y, si el stock
        cambia, un `ajuste` (conservado -> nuevo).
        """

    @abstractmethod
    def modificar(
        self, lineas: "list[LineaModificacion]", usuario_id: int, fecha: datetime
    ) -> "list[ResultadoModificacion]":
        """Aplica el lote (lineas validadas, codigos unicos) en una sola transaccion.

        Lanza ProductosInexistentes con todos los codigos sin producto (activo o inactivo).
        """


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
        items: "list[tuple[str, int, int | None]]",
        usuario_id: int,
        creada_en: datetime,
        procesos: "tuple[ProcesoOrden, ...]" = (),
        servicio: "ServicioOrden | None" = None,
        datos: "DatosOrden" = DatosOrden(),
    ) -> Orden:
        """Crea la orden, sus datos, procesos, servicio y precios y descuenta el stock; todo o nada.

        `items` llega validado y consolidado: (codigo, cantidad_total, precio_centavos|None)
        en orden de primera aparicion, codigos unicos. No escribe en `movimientos` (RN-ST-06).
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
    def productos_en_ordenes(
        self, desde: date, hasta: date, codigo: "str | None"
    ) -> "list[ProductoEnOrdenes]":
        """Total por producto de las ordenes con fecha en [desde, hasta] (ambos inclusivos).

        Fechas ya validadas (`hasta` ya resuelto) y `codigo` ya normalizado (o None).
        `cantidad` = suma de cantidades; `ordenes` = cantidad de ordenes (un producto aparece
        a lo sumo una vez por orden por la PK (orden_id, producto_id), asi que COUNT(*) basta).
        Orden: cantidad DESC y luego codigo. Incluye productos dados de baja. Solo lectura.
        En Postgres sera la funcion RPC `productos_en_ordenes(p_desde, p_hasta, p_codigo)`.
        """

    @abstractmethod
    def productos_usados(self) -> "list[ProductoUsado]":
        """Productos (activos y dados de baja) que figuran en al menos una orden, por codigo.

        En Postgres sera la funcion RPC `productos_usados()`.
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
