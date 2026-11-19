"""Consulta del inventario general."""


class InventarioService:
    def __init__(self, productos):
        self._productos = productos

    def listar(self):
        """Productos activos ordenados por código (orden en Python, independiente del motor)."""
        return sorted(self._productos.listar_activos(), key=lambda p: p.codigo)
