"""Ingreso y egreso de stock (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_stock_service
from inventario.api.schemas import (
    EgresoRequest,
    ErrorOut,
    IngresoOut,
    IngresoRequest,
    ModificacionOut,
    ModificacionRequest,
    ProductoOut,
    ProductosInexistentesOut,
    ingreso_out,
    modificacion_out,
    producto_out,
)
from inventario.domain.entities import LineaModificacion, UsuarioAutenticado
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


@router.post(
    "/modificaciones",
    response_model=ModificacionOut,
    summary="Modificar el stock de varios productos",
    description=(
        "Lote de 1 a 100 líneas, todo o nada. Cada línea fija el stock (`modo: fijar`, "
        "registra un ajuste) o suma unidades (`modo: sumar`, registra un ingreso) y puede "
        "cambiar el nombre. Un producto dado de baja se reactiva solo si su stock cambia "
        "y queda mayor que 0."
    ),
    responses={
        404: {"model": ProductosInexistentesOut, "description": "Productos inexistentes"},
        422: _ERROR_422,
    },
)
def modificar(datos: ModificacionRequest, usuario: Usuario, stock: Servicio):
    lineas = [
        LineaModificacion(
            codigo=linea.codigo,
            modo=linea.modo,
            valor=linea.stock if linea.modo == "fijar" else linea.cantidad,
            nombre=linea.nombre,
        )
        for linea in datos.lineas
    ]
    return modificacion_out(stock.modificar(lineas, usuario.id))
