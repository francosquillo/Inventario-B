"""Errores de dominio."""

MENSAJE_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."


class InventarioError(Exception):
    """Base de los errores de negocio."""


class CredencialesInvalidas(InventarioError):
    def __init__(self):
        super().__init__(MENSAJE_CREDENCIALES_INVALIDAS)


class DatosInvalidos(InventarioError):
    """Validación de los services (HTTP 422)."""


class NombreRequerido(InventarioError):
    def __init__(self, codigo):
        self.codigo = codigo
        super().__init__(f"El producto '{codigo}' no existe: indicá un nombre para crearlo.")


class ProductoNoEncontrado(InventarioError):
    def __init__(self, codigo):
        self.codigo = codigo
        super().__init__(f"No existe un producto activo con código '{codigo}'.")


class StockInsuficiente(InventarioError):
    def __init__(self, codigo, disponible, solicitado):
        self.codigo = codigo
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"Stock insuficiente para '{codigo}': disponible {disponible}, solicitado {solicitado}."
        )
