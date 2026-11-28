"""Alta y consulta de ordenes de trabajo (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from inventario.api.dependencies import get_current_user, get_orden_service
from inventario.api.schemas import (
    BorradoOrdenOut,
    EdicionOrdenOut,
    ErrorOut,
    OrdenEdicionRequest,
    OrdenOut,
    OrdenRequest,
    StockInsuficienteOut,
    borrado_orden_out,
    edicion_orden_out,
    orden_out,
)
from inventario.domain.entities import UsuarioAutenticado
from inventario.domain.errors import ProductosNoEncontrados
from inventario.services.orden_service import OrdenService

router = APIRouter(prefix="/api/ordenes", tags=["ordenes"])

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[OrdenService, Depends(get_orden_service)]

MENSAJE_REINTEGRAR_REPETIDO = "El campo reintegrar debe enviarse una sola vez."
_CAMPOS_DATOS = ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso")


def _componentes(datos):
    return [(c.codigo, c.cantidad, c.precio) for c in datos.componentes]


def _datos_orden(datos):
    return {campo: getattr(datos, campo) for campo in _CAMPOS_DATOS}


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
    return orden_out(
        ordenes.crear(
            datos.numero,
            datos.fecha,
            _componentes(datos),
            usuario.id,
            procesos=datos.procesos,
            procesos_personalizados=datos.procesos_personalizados,
            servicio=datos.servicio,
            datos=_datos_orden(datos),
            precio_servicio=datos.precio_servicio,
            chequeo_final=datos.chequeo_final,
        )
    )


@router.put(
    "/{numero:path}",
    response_model=EdicionOrdenOut,
    summary="Editar una orden por su número",
    description=(
        "Reemplaza por completo el contenido de la orden (el número de la URL se normaliza y "
        "no se puede cambiar): fecha, datos, componentes, servicios, precios y chequeo final; "
        "lo que no se envía queda vacío. El stock se ajusta **por diferencia** (descuenta lo que "
        "aumenta, reintegra lo que baja o se quita; reintegrar reactiva productos dados de baja), "
        "todo o nada y sin escribir en movimientos. `ajustes` lista los productos cuyo stock "
        "cambió. Con `conservar_servicio=true` se mantiene el servicio general guardado. "
        "Los caracteres `?` y `#` del número deben ir codificados (`%3F`, `%23`)."
    ),
    responses={
        404: {
            "model": ErrorOut,
            "description": "Orden inexistente, o productos inexistentes/inactivos (con `codigos`)",
        },
        409: {
            "model": StockInsuficienteOut,
            "description": "Stock insuficiente (con `faltantes`; `solicitado` = cantidad adicional)",
        },
        422: {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"},
    },
)
def editar_orden(numero: str, datos: OrdenEdicionRequest, usuario: Usuario, ordenes: Servicio):
    try:
        resultado = ordenes.editar(
            numero,
            datos.fecha,
            _componentes(datos),
            procesos=datos.procesos,
            procesos_personalizados=datos.procesos_personalizados,
            servicio=datos.servicio,
            datos=_datos_orden(datos),
            precio_servicio=datos.precio_servicio,
            chequeo_final=datos.chequeo_final,
            conservar_servicio=datos.conservar_servicio,
            numero_cuerpo=datos.numero,
        )
    except ProductosNoEncontrados as exc:
        # La web marca las lineas por `codigos`; el alta mantiene su cuerpo solo con `detail`.
        return JSONResponse(
            status_code=404, content={"detail": str(exc), "codigos": list(exc.codigos)}
        )
    return edicion_orden_out(resultado)


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
