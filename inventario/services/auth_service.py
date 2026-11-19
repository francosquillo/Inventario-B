"""Login: autenticación por usuario y contraseña."""
from inventario.domain.entities import UsuarioAutenticado
from inventario.domain.errors import CredencialesInvalidas
from inventario.security import hashear_password, verificar_password

# Relleno para igualar el costo de un login con usuario inexistente.
_HASH_RELLENO, _SALT_RELLENO = hashear_password("relleno-no-valido", salt="00" * 16)


class AuthService:
    def __init__(self, usuarios):
        self._usuarios = usuarios

    def login(self, username, password):
        username = (username or "").strip()
        usuario = self._usuarios.obtener_por_username(username) if username else None
        if usuario is None:
            verificar_password(password or "", _HASH_RELLENO, _SALT_RELLENO)
            raise CredencialesInvalidas()
        if not password or not verificar_password(password, usuario.password_hash, usuario.salt):
            raise CredencialesInvalidas()
        return UsuarioAutenticado(id=usuario.id, username=usuario.username)
