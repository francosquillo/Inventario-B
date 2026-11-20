"""Modelos Pydantic estrictos (D10). Pydantic solo vive en inventario/api/."""
from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


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
