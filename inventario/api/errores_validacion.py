"""Mensajes de validacion en espanol para los 422 de Pydantic (D10). Funcion pura."""

MENSAJE_GENERICO = "Los datos enviados no son válidos."
MENSAJE_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."
MENSAJE_FECHA = "La fecha debe tener formato AAAA-MM-DD."
MENSAJE_STOCK = "El stock debe ser un entero entre 0 y 10.000."
MENSAJE_MODO = "El campo modo debe ser fijar o sumar."

_MENSAJES_CUERPO = {
    "json_invalid": "El cuerpo de la petición no es JSON válido.",
    "model_attributes_type": "El cuerpo de la petición debe ser un objeto JSON.",
    "dict_type": "El cuerpo de la petición debe ser un objeto JSON.",
}
_CAMPOS_FECHA = ("desde", "hasta")
_MENSAJES_COMPONENTES = {
    "too_short": "La orden requiere al menos un componente.",
    "too_long": "La orden admite hasta 100 componentes.",
    "list_type": "El campo componentes debe ser una lista.",
}
_MENSAJES_LINEAS = {
    "too_short": "La modificación requiere al menos una línea.",
    "too_long": "La modificación admite hasta 100 líneas.",
    "list_type": "El campo lineas debe ser una lista.",
}
_TIPOS_TIPO_INCORRECTO = ("string_type", "list_type")
_TIPOS_MODO = ("union_tag_invalid", "union_tag_not_found")
# Listas de lineas: campo del cuerpo -> (etiqueta del prefijo, mensaje de "no es un objeto").
_LISTAS = {
    "componentes": ("Componente", "debe ser un objeto con codigo y cantidad."),
    "lineas": ("Línea", "debe ser un objeto con codigo, modo y stock o cantidad."),
}
_TIPOS_LINEA_NO_OBJETO = ("model_type", "model_attributes_type", "dict_type")
_UBICACIONES = ("body", "query")


def _campo(loc):
    """Ultimo elemento texto de `loc` que no sea body/query (nombre tal como lo ve el cliente)."""
    for parte in reversed(loc):
        if isinstance(parte, str) and parte not in _UBICACIONES:
            return parte
    return None


def _linea(loc):
    """(lista, numero desde 1) si el error cae dentro de una lista de lineas, si no None."""
    for i, parte in enumerate(loc[:-1]):
        if parte in _LISTAS and isinstance(loc[i + 1], int):
            return parte, loc[i + 1] + 1
    return None


def _mensaje_de(error):
    ubicacion = _linea(tuple(error.get("loc", ())))
    if ubicacion is None:
        return _mensaje_campo(error)
    lista, numero = ubicacion
    etiqueta, mensaje_no_objeto = _LISTAS[lista]
    if error.get("type") in _TIPOS_LINEA_NO_OBJETO and isinstance(error["loc"][-1], int):
        return f"{etiqueta} {numero}: {mensaje_no_objeto}"
    return f"{etiqueta} {numero}: {_mensaje_campo(error)}"


def _mensaje_campo(error):
    tipo = error.get("type")
    loc = tuple(error.get("loc", ()))
    if tipo in _TIPOS_MODO:
        return MENSAJE_MODO
    if tipo in _MENSAJES_CUERPO and not (
        tipo in _TIPOS_LINEA_NO_OBJETO and _linea(loc) is not None
    ):
        return _MENSAJES_CUERPO[tipo]
    campo = _campo(loc)
    if tipo == "missing" and campo is None:
        return "El cuerpo de la petición es obligatorio."
    if campo is None:
        return MENSAJE_GENERICO
    if tipo in _TIPOS_TIPO_INCORRECTO and error.get("input") is None:
        return f"El campo {campo} es obligatorio."  # null equivale a no enviado
    if campo == "componentes" and tipo in _MENSAJES_COMPONENTES:
        return _MENSAJES_COMPONENTES[tipo]
    if campo == "lineas" and tipo in _MENSAJES_LINEAS:
        return _MENSAJES_LINEAS[tipo]
    if campo == "stock" and tipo != "missing":
        return MENSAJE_STOCK
    if campo in _CAMPOS_FECHA:
        return MENSAJE_FECHA
    if campo == "cantidad" and tipo != "missing":
        return MENSAJE_CANTIDAD
    if tipo in ("missing", "string_too_short"):
        return f"El campo {campo} es obligatorio."
    if tipo == "string_too_long":
        maximo = error.get("ctx", {}).get("max_length")
        return f"El campo {campo} admite hasta {maximo} caracteres."
    if tipo == "string_type":
        return f"El campo {campo} debe ser texto."
    return f"El campo {campo} no es válido."


def mensaje_validacion(errores):
    """Mensaje en espanol del primer error (el cliente corrige campo por campo)."""
    if not errores:
        return MENSAJE_GENERICO
    return _mensaje_de(errores[0])
