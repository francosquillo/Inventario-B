"""Catalogo de categorias (requiere sesion): listar, crear y renombrar. Sin logica de negocio."""
from typing import Annotated, List

from fastapi import APIRouter, Depends

from inventario.api.dependencies import get_categoria_service, get_current_user
from inventario.api.schemas import (
    CategoriaAltaRequest,
    CategoriaOut,
    CategoriaRenombreRequest,
    ErrorOut,
)
from inventario.domain.errors import DatosInvalidos
from inventario.services.categoria_service import CategoriaService

router = APIRouter(
    prefix="/api/categorias", tags=["categorias"], dependencies=[Depends(get_current_user)]
)

Servicio = Annotated[CategoriaService, Depends(get_categoria_service)]

_422 = {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"}
_409 = {"model": ErrorOut, "description": "Clave o nombre ya usados por otra categoría"}


def _salida(categoria):
    return CategoriaOut(clave=categoria.clave, nombre=categoria.nombre)


@router.get("", response_model=List[CategoriaOut], summary="Listar las categorías")
def listar(categorias: Servicio):
    """Catálogo de categorías de producto, ordenado por nombre."""
    return [_salida(c) for c in categorias.listar()]


@router.post(
    "",
    response_model=CategoriaOut,
    status_code=201,
    summary="Crear una categoría",
    description=(
        "Nombre obligatorio (1 a 40 caracteres, único sin distinguir mayúsculas). La clave es "
        "opcional: si falta se deriva del nombre (minúsculas, sin tildes, con guiones)."
    ),
    responses={409: _409, 422: _422},
)
def crear(datos: CategoriaAltaRequest, categorias: Servicio):
    return _salida(categorias.crear(datos.nombre, datos.clave))


@router.patch(
    "/{clave}",
    response_model=CategoriaOut,
    summary="Renombrar una categoría",
    description="Cambia solo el nombre; la clave no se puede cambiar.",
    responses={
        404: {"model": ErrorOut, "description": "No existe una categoría con esa clave"},
        409: _409,
        422: _422,
    },
)
def renombrar(clave: str, datos: CategoriaRenombreRequest, categorias: Servicio):
    if "clave" in datos.model_fields_set:
        raise DatosInvalidos("La clave de una categoría no se puede cambiar.")
    return _salida(categorias.renombrar(clave, datos.nombre))
