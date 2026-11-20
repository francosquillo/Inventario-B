"""Alta y consulta de ordenes de trabajo (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from inventario.api.dependencies import get_current_user, get_orden_service
from inventario.api.schemas import (
    BorradoOrdenOut,
    ErrorOut,
    OrdenOut,
    OrdenRequest,
    StockInsuficienteOut,
    borrado_orden_out,
    orden_out,
)
from inventario.domain.entities import UsuarioAutenticado
from inventario.services.orden_service import OrdenService

router = APIRouter(prefix="/api/ordenes", tags=["ordenes"])

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[OrdenService, Depends(get_orden_service)]

MENSAJE_REINTEGRAR_REPETIDO = "El campo reintegrar debe enviarse una sola vez."


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


@router.get(
    "",
    response_model=List[OrdenOut],
    responses={
        404: {"model": ErrorOut, "description": "No existe una orden con ese número"},
        422: {"model": ErrorOut, "description": "Filtros inválidos (mensaje en español)"},
    },
)
def listar_ordenes(
    usuario: Usuario,
    ordenes: Servicio,
    numero: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
):
    return [orden_out(o) for o in ordenes.listar(numero, desde, hasta)]


@router.delete(
    "/{numero:path}",
    response_model=BorradoOrdenOut,
    summary="Borrar una orden por su número",
    description=(
        "Borra la orden (el número se normaliza: recorte y mayúsculas) y sus componentes. "
        "Con `reintegrar=true` devuelve el stock de cada componente y reactiva los productos "
        "dados de baja; con `false` el stock queda como está. Todo o nada; no escribe en "
        "movimientos. **Irreversible**: la respuesta es el único registro de lo borrado. "
        "Los caracteres `?` y `#` del número deben ir codificados en la URL (`%3F`, `%23`); "
        "la `/` no necesita codificarse."
    ),
    responses={
        404: {"model": ErrorOut, "description": "No existe una orden con ese número"},
        422: {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"},
    },
)
def borrar_orden(
    numero: str,
    reintegrar: Annotated[str, Query(json_schema_extra={"enum": ["true", "false"]})],
    usuario: Usuario,
    ordenes: Servicio,
    request: Request,
):
    # Borrado irreversible: un `reintegrar` repetido es ambiguo (Starlette tomaría el último).
    # Corre tras la sesión (401) y antes de validar valor y número (422) y buscar (404).
    if len(request.query_params.getlist("reintegrar")) > 1:
        raise HTTPException(status_code=422, detail=MENSAJE_REINTEGRAR_REPETIDO)
    return borrado_orden_out(ordenes.borrar(numero, reintegrar))
