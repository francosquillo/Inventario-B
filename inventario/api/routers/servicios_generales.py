"""Catalogo de servicios generales de ordenes (requiere sesion): listar, crear, modificar y borrar."""
from typing import Annotated, List

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_servicio_general_service
from inventario.api.schemas import (
    ErrorOut,
    ServicioGeneralAltaRequest,
    ServicioGeneralCambioRequest,
    ServicioGeneralOut,
)
from inventario.domain.errors import DatosInvalidos
from inventario.services.servicio_general_service import SIN_CAMBIO, ServicioGeneralService

router = APIRouter(
    prefix="/api/servicios-generales",
    tags=["servicios generales"],
    dependencies=[Depends(get_current_user)],
)

Servicio = Annotated[ServicioGeneralService, Depends(get_servicio_general_service)]

_422 = {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"}
_409 = {"model": ErrorOut, "description": "Clave o nombre ya usados por otro servicio general"}
_404 = {"model": ErrorOut, "description": "No existe un servicio general con esa clave"}


def _salida(servicio):
    return ServicioGeneralOut(
        clave=servicio.clave, nombre=servicio.nombre, chequeos=list(servicio.chequeos)
    )


@router.get("", response_model=List[ServicioGeneralOut], summary="Listar los servicios generales")
def listar(servicios: Servicio):
    """Catálogo de servicios generales con sus chequeos en orden, ordenado por nombre."""
    return [_salida(s) for s in servicios.listar()]


@router.post(
    "",
    response_model=ServicioGeneralOut,
    status_code=201,
    summary="Crear un servicio general",
    description=(
        "Nombre obligatorio (1 a 60 caracteres, único sin distinguir mayúsculas) y de 1 a 30 "
        "chequeos (1 a 60 caracteres, sin repetir, en el orden dado). La clave es opcional: si "
        "falta se deriva del nombre (minúsculas, sin tildes, con guiones)."
    ),
    responses={409: _409, 422: _422},
)
def crear(datos: ServicioGeneralAltaRequest, servicios: Servicio):
    return _salida(servicios.crear(datos.nombre, datos.chequeos, datos.clave))


@router.patch(
    "/{clave}",
    response_model=ServicioGeneralOut,
    summary="Modificar un servicio general",
    description=(
        "Cambia el nombre, reemplaza la lista completa de chequeos o ambas cosas, todo o nada; "
        "la clave no se puede cambiar. Las órdenes ya creadas no cambian."
    ),
    responses={404: _404, 409: _409, 422: _422},
)
def modificar(clave: str, datos: ServicioGeneralCambioRequest, servicios: Servicio):
    if "clave" in datos.model_fields_set:
        raise DatosInvalidos("La clave de un servicio general no se puede cambiar.")
    indicados = datos.model_fields_set
    return _salida(
        servicios.modificar(
            clave,
            nombre=datos.nombre if "nombre" in indicados else SIN_CAMBIO,
            chequeos=datos.chequeos if "chequeos" in indicados else SIN_CAMBIO,
        )
    )


@router.delete(
    "/{clave}",
    response_model=ServicioGeneralOut,
    summary="Borrar un servicio general",
    description=(
        "Quita el servicio del catálogo y devuelve lo borrado. Las órdenes que lo usaron "
        "conservan su nombre y sus chequeos."
    ),
    responses={404: _404, 422: _422},
)
def borrar(clave: str, servicios: Servicio):
    return _salida(servicios.borrar(clave))
