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


class OrdenDuplicada(InventarioError):
    def __init__(self, numero):
        self.numero = numero
        super().__init__(f"Ya existe una orden con número '{numero}'.")


class OrdenNoEncontrada(InventarioError):
    def __init__(self, numero):
        self.numero = numero
        super().__init__(f"No existe una orden con número '{numero}'.")


class ProductosNoEncontrados(InventarioError):
    def __init__(self, codigos):
        self.codigos = tuple(codigos)
        if len(self.codigos) == 1:
            mensaje = f"No existe un producto activo con código '{self.codigos[0]}'."
        else:
            lista = ", ".join(f"'{c}'" for c in self.codigos)
            mensaje = f"No existen productos activos con código: {lista}."
        super().__init__(mensaje)


class StockInsuficienteOrden(InventarioError):
    def __init__(self, faltantes):
        self.faltantes = tuple(faltantes)
        detalle = "; ".join(
            f"'{f.codigo}' (disponible {f.disponible}, solicitado {f.solicitado})"
            for f in self.faltantes
        )
        super().__init__(f"Stock insuficiente para la orden: {detalle}.")


class ProductoDuplicado(InventarioError):
    def __init__(self, codigo):
        self.codigo = codigo
        super().__init__(f"Ya existe un producto con código '{codigo}'.")


class ProductosInexistentes(InventarioError):
    """Códigos sin producto alguno (activo ni dado de baja)."""

    def __init__(self, codigos):
        self.codigos = tuple(codigos)
        if len(self.codigos) == 1:
            mensaje = f"No existe un producto con código '{self.codigos[0]}'."
        else:
            lista = ", ".join(f"'{c}'" for c in self.codigos)
            mensaje = f"No existen productos con código: {lista}."
        super().__init__(mensaje)


class CategoriaDuplicada(InventarioError):
    """Clave o nombre (sin distinguir mayusculas) ya usados por otra categoria (HTTP 409)."""

    def __init__(self, campo, valor):
        self.campo = campo
        self.valor = valor
        super().__init__(f"Ya existe una categoría con {campo} '{valor}'.")


class CategoriaNoEncontrada(InventarioError):
    def __init__(self, clave):
        self.clave = clave
        super().__init__(f"No existe una categoría con clave '{clave}'.")
