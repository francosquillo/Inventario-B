"""Errores de dominio."""

MENSAJE_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."


class InventarioError(Exception):
    """Base de los errores de negocio."""


class CredencialesInvalidas(InventarioError):
    def __init__(self):
        super().__init__(MENSAJE_CREDENCIALES_INVALIDAS)
