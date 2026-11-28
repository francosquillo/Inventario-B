"""Modelos Pydantic estrictos (D10). Pydantic solo vive en inventario/api/."""
from datetime import date, datetime
from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.json_schema import SkipJsonSchema

from inventario.domain.chequeo_final import CLAVES_CHEQUEO_FINAL


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    id: int
    username: str


class ProductoOut(BaseModel):
    codigo: str
    nombre: str
    stock: int
    sin_stock: bool
    categoria: Optional[str] = None


class CategoriaOut(BaseModel):
    clave: str
    nombre: str


# Los campos de categoria y nombre se declaran sin tipo estricto (`Any`): los valida el service,
# para que un valor que no sea texto reciba el mensaje de dominio y no el 422 generico.
class CategoriaAltaRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: Optional[Any] = None
    clave: Optional[Any] = None


class CategoriaRenombreRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: Optional[Any] = None
    # Solo para rechazarla (la clave es inmutable y va en la URL); oculta en /docs.
    clave: SkipJsonSchema[Optional[Any]] = None


class ProcesoOut(BaseModel):
    clave: str
    nombre: str


class ProcesoAltaRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: Optional[Any] = None
    clave: Optional[Any] = None


class ProcesoRenombreRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: Optional[Any] = None
    # Solo para rechazarla (la clave es inmutable y va en la URL); oculta en /docs.
    clave: SkipJsonSchema[Optional[Any]] = None


class ServicioGeneralOut(BaseModel):
    clave: str
    nombre: str
    chequeos: List[str]


class ServicioGeneralAltaRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    # Tipos laxos: los valida el service con mensajes de dominio en espanol.
    nombre: Optional[Any] = None
    chequeos: Optional[Any] = None
    clave: Optional[Any] = None


class ServicioGeneralCambioRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: Optional[Any] = None
    chequeos: Optional[Any] = None
    clave: Optional[Any] = None  # solo para rechazarla: la clave es inmutable


class ErrorOut(BaseModel):
    detail: str


Cantidad = Annotated[int, Field(strict=True, gt=0, le=10_000)]


class IngresoRequest(BaseModel):
    # El recorte va antes de medir: los limites aplican al valor normalizado.
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad
    nombre: Optional[str] = Field(default=None, max_length=120)


class EgresoRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    cantidad: Cantidad


Stock = Annotated[int, Field(strict=True, ge=0, le=10_000)]


class AltaProductoRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=120)
    stock: Stock
    categoria: Optional[Any] = None


class _LineaBase(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    nombre: Optional[str] = Field(default=None, max_length=120)
    # Ausente = no cambia; null = quitar la categoria; texto = asignar (lo valida el service).
    categoria: Optional[Any] = None


class LineaFijar(_LineaBase):
    modo: Literal["fijar"]
    stock: Stock


class LineaSumar(_LineaBase):
    modo: Literal["sumar"]
    cantidad: Cantidad


LineaModificacionIn = Annotated[Union[LineaFijar, LineaSumar], Field(discriminator="modo")]


class ModificacionRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    lineas: List[LineaModificacionIn] = Field(min_length=1, max_length=100)


class LineaModificadaOut(ProductoOut):
    modo: str
    stock_anterior: int
    nombre_anterior: str
    reactivado: bool
    categoria_anterior: Optional[str] = None


class ModificacionOut(BaseModel):
    lineas: List[LineaModificadaOut]


def modificacion_out(resultados):
    return ModificacionOut(
        lineas=[
            LineaModificadaOut(
                codigo=r.codigo,
                nombre=r.nombre,
                stock=r.stock,
                sin_stock=r.sin_stock,
                categoria=r.categoria,
                categoria_anterior=r.categoria_anterior,
                modo=r.modo,
                stock_anterior=r.stock_anterior,
                nombre_anterior=r.nombre_anterior,
                reactivado=r.reactivado,
            )
            for r in resultados
        ]
    )


class ProductosInexistentesOut(BaseModel):
    detail: str
    codigos: List[str]


class IngresoOut(ProductoOut):
    creado: bool
    reactivado: bool


def producto_out(producto):
    return ProductoOut(
        codigo=producto.codigo,
        nombre=producto.nombre,
        stock=producto.stock,
        sin_stock=producto.sin_stock,
        categoria=producto.categoria,
    )


def ingreso_out(resultado):
    return IngresoOut(
        **producto_out(resultado.producto).model_dump(),
        creado=resultado.creado,
        reactivado=resultado.reactivado,
    )


class MovimientoOut(BaseModel):
    fecha: datetime
    codigo: str
    nombre: str
    tipo: str
    cantidad: int
    usuario: str
    stock_anterior: Optional[int] = None
    stock_nuevo: Optional[int] = None


def movimiento_out(movimiento):
    return MovimientoOut(
        fecha=movimiento.fecha,
        codigo=movimiento.codigo,
        nombre=movimiento.nombre,
        tipo=movimiento.tipo,
        cantidad=movimiento.cantidad,
        usuario=movimiento.usuario,
        stock_anterior=movimiento.stock_anterior,
        stock_nuevo=movimiento.stock_nuevo,
    )


class ProductoEnOrdenesOut(BaseModel):
    codigo: str
    nombre: str
    activo: bool
    categoria: Optional[str] = None
    cantidad: int
    ordenes: int


def producto_en_ordenes_out(fila):
    return ProductoEnOrdenesOut(
        codigo=fila.codigo,
        nombre=fila.nombre,
        activo=fila.activo,
        categoria=fila.categoria,
        cantidad=fila.cantidad,
        ordenes=fila.ordenes,
    )


class ProductoUsadoOut(BaseModel):
    codigo: str
    nombre: str
    activo: bool


def producto_usado_out(producto):
    return ProductoUsadoOut(codigo=producto.codigo, nombre=producto.nombre, activo=producto.activo)


# `fecha` NO se recorta: el formato AAAA-MM-DD es estricto y lo valida el service;
# el recorte solo aplica a numero y codigo (que el service normaliza igual).
TextoRecortado = Annotated[str, StringConstraints(strip_whitespace=True)]


DESCRIPCION_PRECIO = (
    "Precio en centavos de ARS (entero >= 0, p. ej. 1250050 = $ 12.500,50) o null. "
    "Un precio vacio cuenta 0 en los subtotales."
)


class ComponenteRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    codigo: TextoRecortado = Field(min_length=1, max_length=50)
    cantidad: Cantidad
    # Tipo laxo: lo valida el service (con prefijo "Componente N:").
    precio: Optional[Any] = Field(
        default=None, description="Importe de la linea. " + DESCRIPCION_PRECIO
    )


class ContenidoOrdenRequest(BaseModel):
    """Campos que comparten el alta y la edicion de una orden (todos menos el numero)."""

    model_config = ConfigDict(strict=True)

    fecha: str = Field(min_length=1)
    componentes: List[ComponenteRequest] = Field(min_length=1, max_length=100)
    # Tipos laxos: los valida el service con mensajes de dominio en espanol.
    procesos: Optional[Any] = Field(
        default=None,
        description=(
            "Claves del catalogo (texto) u objetos {clave, precio}; "
            "el precio es opcional (" + DESCRIPCION_PRECIO + ")"
        ),
    )
    procesos_personalizados: Optional[Any] = Field(
        default=None,
        description="Textos u objetos {nombre, precio}; el precio es opcional (centavos o null).",
    )
    servicio: Optional[Any] = None
    precio_servicio: Optional[Any] = Field(
        default=None, description="Precio del servicio general. " + DESCRIPCION_PRECIO
    )
    cliente: Optional[Any] = Field(default=None, description="Opcional, hasta 80 caracteres.")
    celular: Optional[Any] = Field(
        default=None, description="Opcional, 6 a 20 caracteres: digitos, espacios, +, - y ()."
    )
    casco: Optional[Any] = Field(default=None, description="Opcional, hasta 60 caracteres.")
    motor: Optional[Any] = Field(default=None, description="Opcional, hasta 60 caracteres.")
    trailer: Optional[Any] = Field(default=None, description="Opcional, hasta 60 caracteres.")
    fecha_ingreso: Optional[Any] = Field(
        default=None,
        description="Opcional, AAAA-MM-DD: ingreso de la embarcacion (distinta de `fecha`).",
    )
    fecha_egreso: Optional[Any] = Field(
        default=None,
        description="Opcional, AAAA-MM-DD: egreso; no puede ser anterior al ingreso.",
    )
    chequeo_final: Optional[Any] = Field(
        default=None,
        description=(
            "Opcional: items marcados del chequeo final, por clave (texto) u objeto "
            "{clave, precio}; el precio es opcional (centavos o null). Claves: "
            + ", ".join(CLAVES_CHEQUEO_FINAL) + "."
        ),
    )


class OrdenRequest(ContenidoOrdenRequest):
    numero: TextoRecortado = Field(min_length=1, max_length=30)


class OrdenEdicionRequest(ContenidoOrdenRequest):
    """Reemplazo completo de la orden de la URL; lo que no se envia queda vacio."""

    numero: Optional[Any] = Field(
        default=None, description="No se puede cambiar: si se envia, la API responde 422."
    )
    conservar_servicio: Optional[Any] = Field(
        default=None,
        description=(
            "true: conserva el servicio general guardado (nombre y chequeos) y actualiza solo "
            "`precio_servicio`; no se combina con `servicio`. false por defecto."
        ),
    )


class ComponenteOut(BaseModel):
    codigo: str
    nombre: str
    cantidad: int
    precio: Optional[int] = None


class ProcesoOrdenOut(BaseModel):
    nombre: str
    personalizado: bool
    precio: Optional[int] = None


class ServicioOrdenOut(BaseModel):
    nombre: str
    chequeos: List[str]
    precio: Optional[int] = None


class ChequeoFinalOut(BaseModel):
    clave: str
    nombre: str
    precio: Optional[int] = None


class OrdenOut(BaseModel):
    id: int
    numero: str
    fecha: date
    fecha_ingreso: Optional[date] = None
    fecha_egreso: Optional[date] = None
    cliente: Optional[str] = None
    celular: Optional[str] = None
    casco: Optional[str] = None
    motor: Optional[str] = None
    trailer: Optional[str] = None
    usuario: str
    componentes: List[ComponenteOut]
    procesos: List[ProcesoOrdenOut] = []
    servicio: Optional[ServicioOrdenOut] = None
    chequeo_final: List[ChequeoFinalOut] = []
    subtotal_servicios: int = Field(
        description="Centavos; un precio vacio cuenta 0. Incluye el chequeo final."
    )
    subtotal_items: int = Field(description="Centavos; un precio vacio cuenta 0.")
    total: int = Field(description="Centavos: subtotal_servicios + subtotal_items.")


class FaltanteOut(BaseModel):
    codigo: str
    disponible: int
    solicitado: int


class StockInsuficienteOut(BaseModel):
    detail: str
    faltantes: Optional[List[FaltanteOut]] = None


def orden_out(orden):
    return OrdenOut(
        id=orden.id,
        numero=orden.numero,
        fecha=orden.fecha,
        fecha_ingreso=orden.datos.fecha_ingreso,
        fecha_egreso=orden.datos.fecha_egreso,
        cliente=orden.datos.cliente,
        celular=orden.datos.celular,
        casco=orden.datos.casco,
        motor=orden.datos.motor,
        trailer=orden.datos.trailer,
        usuario=orden.usuario,
        componentes=[
            ComponenteOut(codigo=i.codigo, nombre=i.nombre, cantidad=i.cantidad, precio=i.precio)
            for i in orden.items
        ],
        procesos=[
            ProcesoOrdenOut(nombre=p.nombre, personalizado=p.personalizado, precio=p.precio)
            for p in orden.procesos
        ],
        servicio=(
            ServicioOrdenOut(
                nombre=orden.servicio.nombre,
                chequeos=list(orden.servicio.chequeos),
                precio=orden.servicio.precio,
            )
            if orden.servicio
            else None
        ),
        chequeo_final=[
            ChequeoFinalOut(clave=c.clave, nombre=c.nombre, precio=c.precio)
            for c in orden.chequeo_final
        ],
        subtotal_servicios=orden.subtotal_servicios,
        subtotal_items=orden.subtotal_items,
        total=orden.total,
    )


class ReintegroOut(BaseModel):
    codigo: str
    nombre: str
    cantidad: int
    stock: int
    reactivado: bool


class BorradoOrdenOut(BaseModel):
    orden: OrdenOut
    reintegrado: bool
    reintegros: List[ReintegroOut]


def borrado_orden_out(resultado):
    return BorradoOrdenOut(
        orden=orden_out(resultado.orden),
        reintegrado=resultado.reintegrado,
        reintegros=[
            ReintegroOut(
                codigo=r.codigo,
                nombre=r.nombre,
                cantidad=r.cantidad,
                stock=r.stock,
                reactivado=r.reactivado,
            )
            for r in resultado.reintegros
        ],
    )


class AjusteOut(BaseModel):
    codigo: str
    nombre: str
    cantidad_anterior: int
    cantidad_nueva: int
    stock: int
    reactivado: bool


class EdicionOrdenOut(BaseModel):
    orden: OrdenOut
    ajustes: List[AjusteOut]


def edicion_orden_out(resultado):
    return EdicionOrdenOut(
        orden=orden_out(resultado.orden),
        ajustes=[
            AjusteOut(
                codigo=a.codigo,
                nombre=a.nombre,
                cantidad_anterior=a.cantidad_anterior,
                cantidad_nueva=a.cantidad_nueva,
                stock=a.stock,
                reactivado=a.reactivado,
            )
            for a in resultado.ajustes
        ],
    )
