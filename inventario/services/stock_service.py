"""Ingreso y egreso de stock: validacion, normalizacion y fuente de tiempo."""
from inventario.domain.entities import LineaModificacion
from inventario.domain.errors import DatosInvalidos
from inventario.domain.tiempo import ahora_argentina
from inventario.services.normalizacion import (
    CATEGORIA_CLAVE_MAX,
    normalizar_categoria,
    normalizar_codigo,
    validar_cantidad,
    validar_stock,
)

NOMBRE_MAX = 120
MENSAJE_NOMBRE_LARGO = f"El campo nombre admite hasta {NOMBRE_MAX} caracteres."
MENSAJE_NOMBRE_TIPO = "El campo nombre debe ser texto."


def _normalizar_nombre(nombre):
    if nombre is None:
        return None
    if not isinstance(nombre, str):
        raise DatosInvalidos(MENSAJE_NOMBRE_TIPO)
    nombre = nombre.strip()
    if len(nombre) > NOMBRE_MAX:
        raise DatosInvalidos(MENSAJE_NOMBRE_LARGO)
    return nombre or None


def _validar_categoria(valor, claves):
    """Clave normalizada (o None) validada contra el catalogo; no modifica nada."""
    clave = normalizar_categoria(valor)
    if clave is not None and clave not in claves:
        mostrada = clave if len(clave) <= CATEGORIA_CLAVE_MAX else clave[:CATEGORIA_CLAVE_MAX] + "…"
        raise DatosInvalidos(f"La categoría '{mostrada}' no existe.")
    return clave


LINEAS_MAX = 100
MODOS = ("fijar", "sumar")
MENSAJE_NOMBRE_OBLIGATORIO = "El campo nombre es obligatorio."
MENSAJE_SIN_LINEAS = "La modificación requiere al menos una línea."
MENSAJE_DEMASIADAS_LINEAS = f"La modificación admite hasta {LINEAS_MAX} líneas."
MENSAJE_MODO = "El campo modo debe ser fijar o sumar."


def _validar_linea(posicion, linea, claves):
    """Devuelve la línea normalizada; el error lleva 'Línea N: ' (N desde 1)."""
    try:
        codigo = normalizar_codigo(linea.codigo)
        if linea.modo not in MODOS:
            raise DatosInvalidos(MENSAJE_MODO)
        validar = validar_stock if linea.modo == "fijar" else validar_cantidad
        valor = validar(linea.valor)
        nombre = _normalizar_nombre(linea.nombre)
        cambia = bool(linea.cambia_categoria)
        categoria = _validar_categoria(linea.categoria, claves) if cambia else None
    except DatosInvalidos as exc:
        raise DatosInvalidos(f"Línea {posicion}: {exc}") from None
    return LineaModificacion(codigo, linea.modo, valor, nombre, cambia, categoria)


def _validar_lineas(lineas, claves_de):
    """Valida todas las líneas (la primera inválida gana) y luego rechaza repetidos."""
    if not isinstance(lineas, (list, tuple)) or not lineas:
        raise DatosInvalidos(MENSAJE_SIN_LINEAS)
    if len(lineas) > LINEAS_MAX:
        raise DatosInvalidos(MENSAJE_DEMASIADAS_LINEAS)
    claves = claves_de() if any(l.cambia_categoria for l in lineas) else frozenset()
    validadas = [_validar_linea(i, linea, claves) for i, linea in enumerate(lineas, start=1)]
    primera = {}
    for posicion, linea in enumerate(validadas, start=1):
        if linea.codigo in primera:
            raise DatosInvalidos(
                f"Línea {posicion}: el producto '{linea.codigo}' ya está en la línea "
                f"{primera[linea.codigo]}."
            )
        primera[linea.codigo] = posicion
    return validadas


class StockService:
    def __init__(self, stock_repo, categoria_repo, ahora=ahora_argentina):
        self._repo = stock_repo
        self._categorias = categoria_repo
        self._ahora = ahora

    def ingresar(self, codigo, cantidad, nombre, usuario_id):
        codigo = normalizar_codigo(codigo)
        cantidad = validar_cantidad(cantidad)
        nombre = _normalizar_nombre(nombre)
        return self._repo.registrar_ingreso(codigo, cantidad, nombre, usuario_id, self._ahora())

    def _claves_de_categorias(self):
        return frozenset(c.clave for c in self._categorias.listar())

    def dar_de_alta(self, codigo, nombre, stock, usuario_id, categoria=None):
        codigo = normalizar_codigo(codigo)
        nombre = _normalizar_nombre(nombre)
        if nombre is None:
            raise DatosInvalidos(MENSAJE_NOMBRE_OBLIGATORIO)
        stock = validar_stock(stock)
        if categoria is not None:
            categoria = _validar_categoria(categoria, self._claves_de_categorias())
        return self._repo.dar_de_alta(
            codigo, nombre, stock, usuario_id, self._ahora(), categoria
        )

    def modificar(self, lineas, usuario_id):
        validadas = _validar_lineas(lineas, self._claves_de_categorias)
        return self._repo.modificar(validadas, usuario_id, self._ahora())

    def egresar(self, codigo, cantidad, usuario_id):
        codigo = normalizar_codigo(codigo)
        cantidad = validar_cantidad(cantidad)
        return self._repo.registrar_egreso(codigo, cantidad, usuario_id, self._ahora())
