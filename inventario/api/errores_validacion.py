"""Mensajes de validacion en espanol para los 422 de Pydantic (D10). Funcion pura."""

MENSAJE_GENERICO = "Los datos enviados no son válidos."
MENSAJE_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."
MENSAJE_FECHA = "La fecha debe tener formato AAAA-MM-DD."

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
_TIPOS_TIPO_INCORRECTO = ("string_type", "list_type")
_MENSAJE_LINEA_TIPO = "debe ser un objeto con codigo y cantidad."
_TIPOS_LINEA_NO_OBJETO = ("model_type", "model_attributes_type", "dict_type")
_UBICACIONES = ("body", "query")


def _campo(loc):
    """Ultimo elemento texto de `loc` que no sea body/query (nombre tal como lo ve el cliente)."""
    for parte in reversed(loc):
        if isinstance(parte, str) and parte not in _UBICACIONES:
            return parte
    return None


def _linea(loc):
    """Numero de componente (desde 1) si el error cae dentro de `componentes`, si no None."""
    for i, parte in enumerate(loc[:-1]):
        if parte == "componentes" and isinstance(loc[i + 1], int):
            return loc[i + 1] + 1
    return None


def _mensaje_de(error):
    linea = _linea(tuple(error.get("loc", ())))
    if linea is None:
        return _mensaje_campo(error)
    if error.get("type") in _TIPOS_LINEA_NO_OBJETO and isinstance(error["loc"][-1], int):
        return f"Componente {linea}: {_MENSAJE_LINEA_TIPO}"
    return f"Componente {linea}: {_mensaje_campo(error)}"


def _mensaje_campo(error):
    tipo = error.get("type")
    loc = tuple(error.get("loc", ()))
    if tipo in _MENSAJES_CUERPO:
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
