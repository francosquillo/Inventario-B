"""Alta de ordenes de trabajo (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_orden_service
from inventario.api.schemas import (
    ErrorOut,
    OrdenOut,
    OrdenRequest,
    StockInsuficienteOut,
    orden_out,
)
from inventario.domain.entities import UsuarioAutenticado
from inventario.services.orden_service import OrdenService

router = APIRouter(prefix="/api/ordenes", tags=["ordenes"])

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[OrdenService, Depends(get_orden_service)]


@router.post(
    "",
    status_code=201,
    response_model=OrdenOut,
    responses={
        404: {"model": ErrorOut, "description": "Productos inexistentes o inactivos"},
        409: {
            "model": StockInsuficienteOut,
            "description": "Número duplicado o stock insuficiente (con `faltantes`)",
        },
        422: {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"},
    },
)
def crear_orden(datos: OrdenRequest, usuario: Usuario, ordenes: Servicio):
    componentes = [(c.codigo, c.cantidad) for c in datos.componentes]
    return orden_out(ordenes.crear(datos.numero, datos.fecha, componentes, usuario.id))
