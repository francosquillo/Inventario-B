"""Baja logica de productos (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_producto_service
from inventario.api.schemas import ErrorOut, ProductoOut, producto_out
from inventario.domain.entities import UsuarioAutenticado
from inventario.services.producto_service import ProductoService

router = APIRouter(prefix="/api/productos", tags=["productos"])

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[ProductoService, Depends(get_producto_service)]


@router.delete(
    "/{codigo:path}",
    response_model=ProductoOut,
    summary="Dar de baja un producto",
    description=(
        "Baja lógica (`activo = 0`): el producto deja de verse en el inventario y no admite "
        "egresos ni órdenes nuevas, pero conserva su stock y sigue en las órdenes y "
        "movimientos anteriores. Un ingreso posterior lo reactiva sumando al stock conservado. "
        "No escribe en movimientos."
    ),
    responses={
        404: {"model": ErrorOut, "description": "Producto inexistente o ya dado de baja"},
        422: {"model": ErrorOut, "description": "Código inválido (mensaje en español)"},
    },
)
def dar_de_baja(codigo: str, usuario: Usuario, productos: Servicio):
    return producto_out(productos.dar_de_baja(codigo))
