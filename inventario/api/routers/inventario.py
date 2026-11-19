"""Consulta del inventario general (requiere sesion)."""
from typing import List

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_inventario_service
from inventario.api.schemas import ProductoOut

router = APIRouter(prefix="/api", tags=["inventario"], dependencies=[Depends(get_current_user)])


@router.get("/inventario", response_model=List[ProductoOut])
def listar_inventario(inventario=Depends(get_inventario_service)):
    return [
        ProductoOut(codigo=p.codigo, nombre=p.nombre, stock=p.stock, sin_stock=p.sin_stock)
        for p in inventario.listar()
    ]
