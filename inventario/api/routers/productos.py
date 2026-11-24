"""Alta, dados de baja y baja de productos (requiere sesion). Sin logica: request -> service -> schema."""
from typing import Annotated, List

from fastapi import APIRouter, Depends

from inventario.api.dependencies import (
    get_current_user,
    get_producto_service,
    get_stock_service,
)
from inventario.api.schemas import (
    AltaProductoRequest,
    ErrorOut,
    IngresoOut,
    ProductoOut,
    ingreso_out,
    producto_out,
)
from inventario.domain.entities import UsuarioAutenticado
from inventario.services.producto_service import ProductoService
from inventario.services.stock_service import StockService

router = APIRouter(prefix="/api/productos", tags=["productos"])

Usuario = Annotated[UsuarioAutenticado, Depends(get_current_user)]
Servicio = Annotated[ProductoService, Depends(get_producto_service)]
ServicioStock = Annotated[StockService, Depends(get_stock_service)]


@router.post(
    "",
    response_model=IngresoOut,
    status_code=201,
    summary="Dar de alta un producto",
    description=(
        "Alta explícita con código, nombre y stock inicial (0 a 10.000). Con stock mayor que 0 "
        "registra un ingreso. Si el código es de un producto dado de baja lo reactiva con el "
        "nombre, stock y categoría nuevos (`reactivado: true`; registra un ajuste si el stock "
        "cambia). `categoria` es la clave de una categoría existente (opcional)."
    ),
    responses={
        409: {"model": ErrorOut, "description": "Ya existe un producto activo con ese código"},
        422: {"model": ErrorOut, "description": "Datos inválidos (mensaje en español)"},
    },
)
def dar_de_alta(datos: AltaProductoRequest, usuario: Usuario, stock: ServicioStock):
    return ingreso_out(
        stock.dar_de_alta(datos.codigo, datos.nombre, datos.stock, usuario.id, datos.categoria)
    )


@router.get(
    "/inactivos",
    response_model=List[ProductoOut],
    summary="Listar productos dados de baja",
    description="Productos con baja lógica, ordenados por código; `[]` si no hay ninguno.",
)
def listar_inactivos(usuario: Usuario, productos: Servicio):
    return [producto_out(p) for p in productos.listar_inactivos()]


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
