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


# --- Servicios generales (C-06g) ---
SERVICIO_NOMBRE_MAX = 60
CHEQUEO_NOMBRE_MAX = 60
CHEQUEOS_MAX = 30
MENSAJE_NOMBRE_SERVICIO_LARGO = (
    f"El nombre del servicio general admite hasta {SERVICIO_NOMBRE_MAX} caracteres."
)
MENSAJE_CLAVE_SERVICIO = (
    "La clave del servicio general admite solo minúsculas sin tilde, números y guiones "
    "(hasta 30 caracteres)."
)
MENSAJE_CHEQUEOS_TIPO = "El campo chequeos debe ser una lista de textos."
MENSAJE_SIN_CHEQUEOS = "El servicio general requiere al menos un chequeo."
MENSAJE_DEMASIADOS_CHEQUEOS = f"El servicio general admite hasta {CHEQUEOS_MAX} chequeos."


def normalizar_nombre_servicio(nombre):
    """Nombre de servicio general del catalogo: recortado, 1 a 60 caracteres."""
    return normalizar_nombre(nombre, SERVICIO_NOMBRE_MAX, MENSAJE_NOMBRE_SERVICIO_LARGO)


def validar_clave_servicio(clave):
    return validar_clave(clave, MENSAJE_CLAVE_SERVICIO)


def normalizar_chequeos(valor):
    """Lista de chequeos de un servicio general -> tupla de textos recortados, en orden.

    None o lista vacia = sin chequeos (error); 1 a 30, de 1 a 60 caracteres, sin repetir
    (casefold). Los errores por chequeo llevan su posicion desde 1.
    """
    if valor is None:
        raise DatosInvalidos(MENSAJE_SIN_CHEQUEOS)
    if not isinstance(valor, (list, tuple)) or not all(isinstance(v, str) for v in valor):
        raise DatosInvalidos(MENSAJE_CHEQUEOS_TIPO)
    if not valor:
        raise DatosInvalidos(MENSAJE_SIN_CHEQUEOS)
    if len(valor) > CHEQUEOS_MAX:
        raise DatosInvalidos(MENSAJE_DEMASIADOS_CHEQUEOS)
    vistos = set()
    chequeos = []
    for posicion, texto in enumerate(valor, start=1):
        nombre = texto.strip()
        if not nombre:
            raise DatosInvalidos(f"Chequeo {posicion}: El nombre es obligatorio.")
        if len(nombre) > CHEQUEO_NOMBRE_MAX:
            raise DatosInvalidos(
                f"Chequeo {posicion}: El nombre admite hasta {CHEQUEO_NOMBRE_MAX} caracteres."
            )
        if nombre.casefold() in vistos:
            raise DatosInvalidos(f"Chequeo {posicion}: '{nombre}' está repetido.")
        vistos.add(nombre.casefold())
        chequeos.append(nombre)
    return tuple(chequeos)


# --- Precios y datos del cliente de ordenes (C-06h) ---
PRECIO_MAX = 99_999_999_999
MENSAJE_PRECIO = f"El precio debe ser un entero de centavos entre 0 y {PRECIO_MAX:,}.".replace(",", ".")
CELULAR_MIN = 6
CELULAR_MAX = 20
MENSAJE_CELULAR = (
    "El celular admite solo números, espacios, +, - y paréntesis "
    f"(de {CELULAR_MIN} a {CELULAR_MAX} caracteres)."
)
_CELULAR = re.compile(r"\+?[0-9 ()-]+")


def validar_precio(valor, mensaje=MENSAJE_PRECIO):
    """Precio opcional en centavos: None = sin precio; si no, entero (no bool) de 0 al maximo."""
    if valor is None:
        return None
    if type(valor) is not int or not 0 <= valor <= PRECIO_MAX:
        raise DatosInvalidos(mensaje)
    return valor


def normalizar_texto_opcional(valor, campo, tope, mensaje_largo, mensaje_tipo=None):
    """Texto opcional: None o blanco = None; recortado, hasta `tope` caracteres."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise DatosInvalidos(mensaje_tipo or f"El campo {campo} debe ser texto.")
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > tope:
        raise DatosInvalidos(mensaje_largo)
    return valor


def validar_celular(valor):
    """Celular opcional: recortado, 6 a 20 caracteres, solo digitos, espacios, - y () con un + inicial."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise DatosInvalidos("El campo celular debe ser texto.")
    valor = valor.strip()
    if not valor:
        return None
    digitos = sum(c.isdigit() for c in valor)
    if (
        not CELULAR_MIN <= len(valor) <= CELULAR_MAX
        or not _CELULAR.fullmatch(valor)
        or digitos < CELULAR_MIN
    ):
        raise DatosInvalidos(MENSAJE_CELULAR)
    return valor
