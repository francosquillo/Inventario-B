"""Hashing y verificación de contraseñas (PBKDF2-HMAC-SHA256, solo stdlib)."""
import hashlib
import hmac
import secrets

PBKDF2_ITERACIONES = 600_000
SALT_BYTES = 16
DKLEN = 32
PASSWORD_GENERADA_BYTES = 16


def hashear_password(password, salt=None, iteraciones=PBKDF2_ITERACIONES):
    """Devuelve (hash_hex, salt_hex). Si no se pasa salt (hex), genera uno aleatorio."""
    salt_bytes = secrets.token_bytes(SALT_BYTES) if salt is None else bytes.fromhex(salt)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, iteraciones, dklen=DKLEN
    )
    return derivado.hex(), salt_bytes.hex()


def verificar_password(password, hash_hex, salt_hex, iteraciones=PBKDF2_ITERACIONES):
    """Recalcula el hash y lo compara en tiempo constante."""
    calculado, _ = hashear_password(password, salt=salt_hex, iteraciones=iteraciones)
    return hmac.compare_digest(calculado, hash_hex)


def generar_password():
    """Contraseña aleatoria criptográficamente segura (22 caracteres)."""
    return secrets.token_urlsafe(PASSWORD_GENERADA_BYTES)
