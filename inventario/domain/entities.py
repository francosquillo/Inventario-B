"""Entidades de dominio inmutables."""
from dataclasses import dataclass
from datetime import date, datetime


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
class Categoria:
    clave: str
    nombre: str


@dataclass(frozen=True)
class Proceso:
    """Proceso del catalogo (clave estable + nombre para mostrar)."""

    clave: str
    nombre: str


@dataclass(frozen=True)
class ProcesoOrden:
    """Proceso de una orden: snapshot del nombre y marca de personalizado (sin FK al catalogo)."""

    nombre: str
    personalizado: bool


@dataclass(frozen=True)
class ServicioGeneral:
    """Servicio general del catalogo: clave estable, nombre y chequeos en orden (C-06g)."""

    clave: str
    nombre: str
    chequeos: "tuple[str, ...]"


@dataclass(frozen=True)
class ServicioOrden:
    """Servicio de una orden: snapshot del nombre y los chequeos (sin FK al catalogo)."""

    nombre: str
    chequeos: "tuple[str, ...]"


@dataclass(frozen=True)
class Producto:
    id: int
    codigo: str
    nombre: str
    stock: int
    activo: bool
    categoria: "str | None" = None  # clave de la categoria; None = sin categoria

    @property
    def sin_stock(self):
        return self.stock == 0


@dataclass(frozen=True)
class ResultadoIngreso:
    producto: Producto
    creado: bool
    reactivado: bool


@dataclass(frozen=True)
class Movimiento:
    fecha: datetime
    codigo: str
    nombre: str
    tipo: str
    cantidad: int
    usuario: str
    stock_anterior: "int | None" = None
    stock_nuevo: "int | None" = None


@dataclass(frozen=True)
class LineaModificacion:
    """Línea validada de una modificación: modo 'fijar' (valor = stock) o 'sumar' (valor = cantidad)."""

    codigo: str
    modo: str
    valor: int
    nombre: "str | None"
    cambia_categoria: bool = False  # False = no tocar; True = asignar `categoria` (None quita)
    categoria: "str | None" = None


@dataclass(frozen=True)
class ResultadoModificacion:
    codigo: str
    nombre: str
    stock: int
    modo: str
    stock_anterior: int
    nombre_anterior: str
    reactivado: bool
    categoria: "str | None" = None
    categoria_anterior: "str | None" = None

    @property
    def sin_stock(self):
        return self.stock == 0


@dataclass(frozen=True)
class ItemOrden:
    codigo: str
    nombre: str
    cantidad: int


@dataclass(frozen=True)
class Orden:
    id: int
    numero: str
    fecha: date
    usuario: str
    items: "tuple[ItemOrden, ...]"
    procesos: "tuple[ProcesoOrden, ...]" = ()
    servicio: "ServicioOrden | None" = None


@dataclass(frozen=True)
class Faltante:
    codigo: str
    disponible: int
    solicitado: int


@dataclass(frozen=True)
class Reintegro:
    codigo: str
    nombre: str
    cantidad: int
    stock: int
    reactivado: bool


@dataclass(frozen=True)
class ResultadoBorradoOrden:
    orden: Orden
    reintegrado: bool
    reintegros: "tuple[Reintegro, ...]"


@dataclass(frozen=True)
class ProductoEnOrdenes:
    """Total de un producto en las ordenes de un rango (reporte)."""

    codigo: str
    nombre: str
    activo: bool
    cantidad: int
    ordenes: int
    categoria: "str | None" = None


@dataclass(frozen=True)
class ProductoUsado:
    """Producto que figura en al menos una orden."""

    codigo: str
    nombre: str
    activo: bool
