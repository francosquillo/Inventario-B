"""Reportes de solo lectura (requieren sesion): productos usados en ordenes."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_reporte_service
from inventario.api.schemas import (
    ErrorOut,
    ProductoEnOrdenesOut,
    ProductoUsadoOut,
    producto_en_ordenes_out,
    producto_usado_out,
)
from inventario.services.reporte_service import ReporteService

router = APIRouter(
    prefix="/api/reportes", tags=["reportes"], dependencies=[Depends(get_current_user)]
)


@router.get(
    "/productos-en-ordenes",
    response_model=List[ProductoEnOrdenesOut],
    responses={422: {"model": ErrorOut, "description": "Filtros inválidos (mensaje en español)"}},
)
def productos_en_ordenes(
    reportes: Annotated[ReporteService, Depends(get_reporte_service)],
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    codigo: Optional[str] = None,
):
    """Total por producto en las órdenes del rango; `desde` obligatorio, `hasta` vacío = hoy."""
    return [producto_en_ordenes_out(f) for f in reportes.productos_en_ordenes(desde, hasta, codigo)]


@router.get("/productos-usados", response_model=List[ProductoUsadoOut])
def productos_usados(reportes: Annotated[ReporteService, Depends(get_reporte_service)]):
    """Productos (activos y dados de baja) que figuran en al menos una orden."""
    return [producto_usado_out(p) for p in reportes.productos_usados()]
