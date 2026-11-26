"""Normalizacion del codigo de producto: unica puerta de entrada (D3/D7)."""
import re
import unicodedata

from inventario.domain.errors import DatosInvalidos

CODIGO_MAX = 50
MENSAJE_CODIGO_OBLIGATORIO = "El campo codigo es obligatorio."
MENSAJE_CODIGO_LARGO = f"El campo codigo admite hasta {CODIGO_MAX} caracteres."


def normalizar_codigo(codigo):
    """Recorta y pasa a MAYUSCULAS. Lanza DatosInvalidos si esta vacio o es muy largo."""
    if not isinstance(codigo, str) or not codigo.strip():
        raise DatosInvalidos(MENSAJE_CODIGO_OBLIGATORIO)
    normalizado = codigo.strip().upper()
    if len(normalizado) > CODIGO_MAX:
        raise DatosInvalidos(MENSAJE_CODIGO_LARGO)
    return normalizado


CANTIDAD_MAX = 10_000
MENSAJE_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


STOCK_MAX = 10_000
MENSAJE_STOCK = "El stock debe ser un entero entre 0 y 10.000."


def validar_stock(stock):
    """Stock absoluto (alta y 'fijar'): entero de 0 a 10.000; type() is int rechaza bool."""
    if type(stock) is not int or not 0 <= stock <= STOCK_MAX:
        raise DatosInvalidos(MENSAJE_STOCK)
    return stock


def validar_cantidad(cantidad):
    # type() is int: rechaza bool, float y str.
    if type(cantidad) is not int or not 1 <= cantidad <= CANTIDAD_MAX:
        raise DatosInvalidos(MENSAJE_CANTIDAD)
    return cantidad


# --- Categorias (C-06e) ---
CATEGORIA_CLAVE_MAX = 30
CATEGORIA_NOMBRE_MAX = 40
MENSAJE_CATEGORIA_TIPO = "El campo categoria debe ser texto."
MENSAJE_CLAVE_CATEGORIA = (
    "La clave de la categoría admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)
MENSAJE_NOMBRE_CATEGORIA_OBLIGATORIO = "El campo nombre es obligatorio."
MENSAJE_NOMBRE_CATEGORIA_LARGO = (
    f"El nombre de la categoría admite hasta {CATEGORIA_NOMBRE_MAX} caracteres."
)
_CLAVE_CATEGORIA = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def normalizar_categoria(valor):
    """Clave de categoria de un producto: None o blanco = sin categoria; recorta y minusculas."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise DatosInvalidos(MENSAJE_CATEGORIA_TIPO)
    return valor.strip().lower() or None


def clave_desde_texto(texto, mensaje=MENSAJE_CLAVE_CATEGORIA):
    """Deriva una clave: sin tildes, minusculas, tramos no alfanumericos -> '-', hasta 30."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    clave = re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")
    clave = clave[:CATEGORIA_CLAVE_MAX].rstrip("-")
    if not clave:
        raise DatosInvalidos(mensaje)
    return clave


def validar_clave(clave, mensaje):
    """Clave ya normalizada (recorte + minusculas): formato y largo."""
    if len(clave) > CATEGORIA_CLAVE_MAX or not _CLAVE_CATEGORIA.fullmatch(clave):
        raise DatosInvalidos(mensaje)
    return clave


def validar_clave_categoria(clave):
    return validar_clave(clave, MENSAJE_CLAVE_CATEGORIA)


def normalizar_nombre(nombre, tope, mensaje_largo):
    """Nombre para mostrar de un catalogo: recortado, de 1 al tope de caracteres."""
    if not isinstance(nombre, str) or not nombre.strip():
        raise DatosInvalidos(MENSAJE_NOMBRE_CATEGORIA_OBLIGATORIO)
    nombre = nombre.strip()
    if len(nombre) > tope:
        raise DatosInvalidos(mensaje_largo)
    return nombre


def normalizar_nombre_categoria(nombre):
    """Nombre de categoria: recortado, 1 a 40 caracteres."""
    return normalizar_nombre(nombre, CATEGORIA_NOMBRE_MAX, MENSAJE_NOMBRE_CATEGORIA_LARGO)


# --- Procesos de ordenes (C-06f) ---
PROCESO_NOMBRE_MAX = 60
MENSAJE_NOMBRE_PROCESO_LARGO = (
    f"El nombre del proceso admite hasta {PROCESO_NOMBRE_MAX} caracteres."
)
MENSAJE_CLAVE_PROCESO = (
    "La clave del proceso admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)


def normalizar_nombre_proceso(nombre):
    """Nombre de proceso del catalogo: recortado, 1 a 60 caracteres."""
    return normalizar_nombre(nombre, PROCESO_NOMBRE_MAX, MENSAJE_NOMBRE_PROCESO_LARGO)


def validar_clave_proceso(clave):
    return validar_clave(clave, MENSAJE_CLAVE_PROCESO)
