"""Modelos Pydantic estrictos (D10). Pydantic solo vive en inventario/api/."""
from datetime import date, datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    id: int
    username: str


class ProductoOut(BaseModel):
    codigo: str
    nombre: str
    stock: int
    sin_stock: bool


class ErrorOut(BaseModel):
    detail: str


Cantidad = Annotated[int, Field(strict=True, gt=0, le=10_000)]


class IngresoRequest(BaseModel):
    # El recorte va antes de medir: los limites aplican al valor normalizado.
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad
    nombre: Optional[str] = Field(default=None, max_length=120)


class EgresoRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad


class IngresoOut(ProductoOut):
    creado: bool
    reactivado: bool


def producto_out(producto):
    return ProductoOut(
        codigo=producto.codigo,
        nombre=producto.nombre,
        stock=producto.stock,
        sin_stock=producto.sin_stock,
    )


def ingreso_out(resultado):
    return IngresoOut(
        **producto_out(resultado.producto).model_dump(),
        creado=resultado.creado,
        reactivado=resultado.reactivado,
    )


class MovimientoOut(BaseModel):
    fecha: datetime
    codigo: str
    nombre: str
    tipo: str
    cantidad: int
    usuario: str


def movimiento_out(movimiento):
    return MovimientoOut(
        fecha=movimiento.fecha,
        codigo=movimiento.codigo,
        nombre=movimiento.nombre,
        tipo=movimiento.tipo,
        cantidad=movimiento.cantidad,
        usuario=movimiento.usuario,
    )


# `fecha` NO se recorta: el formato AAAA-MM-DD es estricto y lo valida el service;
# el recorte solo aplica a numero y codigo (que el service normaliza igual).
TextoRecortado = Annotated[str, StringConstraints(strip_whitespace=True)]


class ComponenteRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    codigo: TextoRecortado = Field(min_length=1, max_length=50)
    cantidad: Cantidad


class OrdenRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    numero: TextoRecortado = Field(min_length=1, max_length=30)
    fecha: str = Field(min_length=1)
    componentes: List[ComponenteRequest] = Field(min_length=1, max_length=100)


class ComponenteOut(BaseModel):
    codigo: str
    nombre: str
    cantidad: int


class OrdenOut(BaseModel):
    id: int
    numero: str
    fecha: date
    usuario: str
    componentes: List[ComponenteOut]


class FaltanteOut(BaseModel):
    codigo: str
    disponible: int
    solicitado: int


class StockInsuficienteOut(BaseModel):
    detail: str
    faltantes: Optional[List[FaltanteOut]] = None


def orden_out(orden):
    return OrdenOut(
        id=orden.id,
        numero=orden.numero,
        fecha=orden.fecha,
        usuario=orden.usuario,
        componentes=[
            ComponenteOut(codigo=i.codigo, nombre=i.nombre, cantidad=i.cantidad)
            for i in orden.items
        ],
    )


class ReintegroOut(BaseModel):
    codigo: str
    nombre: str
    cantidad: int
    stock: int
    reactivado: bool


class BorradoOrdenOut(BaseModel):
    orden: OrdenOut
    reintegrado: bool
    reintegros: List[ReintegroOut]


def borrado_orden_out(resultado):
    return BorradoOrdenOut(
        orden=orden_out(resultado.orden),
        reintegrado=resultado.reintegrado,
        reintegros=[
            ReintegroOut(
                codigo=r.codigo,
                nombre=r.nombre,
                cantidad=r.cantidad,
                stock=r.stock,
                reactivado=r.reactivado,
            )
            for r in resultado.reintegros
        ],
    )
