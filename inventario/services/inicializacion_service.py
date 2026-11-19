"""Seed idempotente del usuario admin."""
from inventario.security import generar_password, hashear_password

ADMIN_USERNAME = "admin"


def sembrar_admin(usuarios, password_entorno):
    """Crea `admin` si no existe. Devuelve la contraseña solo si fue generada."""
    if usuarios.obtener_por_username(ADMIN_USERNAME) is not None:
        return None
    generada = None
    password = password_entorno
    if password is None:
        password = generada = generar_password()
    hash_hex, salt_hex = hashear_password(password)
    usuarios.crear(ADMIN_USERNAME, hash_hex, salt_hex)
    return generada
