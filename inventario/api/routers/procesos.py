"""Catalogo de procesos de ordenes (requiere sesion): listar, crear, renombrar y borrar."""
from typing import Annotated, List

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_current_user, get_proceso_service
from inventario.api.schemas import (
    ErrorOut,
    ProcesoAltaRequest,
    ProcesoOut,
    ProcesoRenombreRequest,
)
from inventario.domain.errors import DatosInvalidos
from inventario.services.proceso_service import ProcesoService

router = APIRouter(
    prefix="/api/procesos", tags=["procesos"], dependencies=[Depends(get_current_user)]
)

Servicio = Annotated[ProcesoService, Depends(get_proceso_service)]

_422 = {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"}
_409 = {"model": ErrorOut, "description": "Clave o nombre ya usados por otro proceso"}
_404 = {"model": ErrorOut, "description": "No existe un proceso con esa clave"}


def _salida(proceso):
    return ProcesoOut(clave=proceso.clave, nombre=proceso.nombre)


@router.get("", response_model=List[ProcesoOut], summary="Listar los procesos")
def listar(procesos: Servicio):
    """Catálogo de procesos de órdenes, ordenado por nombre."""
    return [_salida(p) for p in procesos.listar()]


@router.post(
    "",
    response_model=ProcesoOut,
    status_code=201,
    summary="Crear un proceso",
    description=(
        "Nombre obligatorio (1 a 60 caracteres, único sin distinguir mayúsculas). La clave es "
        "opcional: si falta se deriva del nombre (minúsculas, sin tildes, con guiones)."
    ),
    responses={409: _409, 422: _422},
)
def crear(datos: ProcesoAltaRequest, procesos: Servicio):
    return _salida(procesos.crear(datos.nombre, datos.clave))


@router.patch(
    "/{clave}",
    response_model=ProcesoOut,
    summary="Renombrar un proceso",
    description="Cambia solo el nombre; la clave no se puede cambiar. Las órdenes ya creadas no cambian.",
    responses={404: _404, 409: _409, 422: _422},
)
def renombrar(clave: str, datos: ProcesoRenombreRequest, procesos: Servicio):
    if "clave" in datos.model_fields_set:
        raise DatosInvalidos("La clave de un proceso no se puede cambiar.")
    return _salida(procesos.renombrar(clave, datos.nombre))


@router.delete(
    "/{clave}",
    response_model=ProcesoOut,
    summary="Borrar un proceso",
    description=(
        "Quita el proceso del catálogo y devuelve lo borrado. Las órdenes que lo usaron conservan "
        "su nombre."
    ),
    responses={404: _404, 422: _422},
)
def borrar(clave: str, procesos: Servicio):
    return _salida(procesos.borrar(clave))
