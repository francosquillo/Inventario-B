"""Ingreso y egreso de stock (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_stock_service
from inventario.api.schemas import (
    EgresoRequest,
    ErrorOut,
    IngresoOut,
    IngresoRequest,
    ProductoOut,
    ingreso_out,
    producto_out,
)
from inventario.domain.entities import UsuarioAutenticado
from inventario.services.stock_service import StockService

router = APIRouter(prefix="/api/stock", tags=["stock"])

_ERROR_422 = {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"}

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[StockService, Depends(get_stock_service)]


@router.post("/ingreso", response_model=IngresoOut, responses={422: _ERROR_422})
def ingresar(datos: IngresoRequest, usuario: Usuario, stock: Servicio):
    resultado = stock.ingresar(datos.codigo, datos.cantidad, datos.nombre, usuario.id)
    return ingreso_out(resultado)


@router.post(
    "/egreso",
    response_model=ProductoOut,
    responses={
        404: {"model": ErrorOut, "description": "Producto inexistente o inactivo"},
        409: {"model": ErrorOut, "description": "Stock insuficiente"},
        422: _ERROR_422,
    },
)
def egresar(datos: EgresoRequest, usuario: Usuario, stock: Servicio):
    return producto_out(stock.egresar(datos.codigo, datos.cantidad, usuario.id))
