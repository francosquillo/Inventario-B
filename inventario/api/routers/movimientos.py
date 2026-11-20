"""Consulta de la bitacora de movimientos (requiere sesion)."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_movimientos_service
from inventario.api.schemas import ErrorOut, MovimientoOut, movimiento_out
from inventario.services.movimientos_service import MovimientosService

router = APIRouter(
    prefix="/api/movimientos", tags=["movimientos"], dependencies=[Depends(get_current_user)]
)


@router.get(
    "",
    response_model=List[MovimientoOut],
    responses={422: {"model": ErrorOut, "description": "Filtros inválidos (mensaje en español)"}},
)
def listar_movimientos(
    movimientos: Annotated[MovimientosService, Depends(get_movimientos_service)],
    codigo: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
):
    return [movimiento_out(m) for m in movimientos.listar(codigo, desde, hasta)]
