"""Lectura de configuración desde variables de entorno."""
import os

ENV_DB_PATH = "INVENTARIO_DB_PATH"
ENV_ADMIN_PASSWORD = "ADMIN_DEFAULT_PASSWORD"
DB_PATH_POR_DEFECTO = "inventario.db"


def ruta_db():
    return os.environ.get(ENV_DB_PATH) or DB_PATH_POR_DEFECTO


def password_admin():
    valor = os.environ.get(ENV_ADMIN_PASSWORD)
    if valor is None or not valor.strip():
        return None
    return valor


ENV_SECRET_KEY = "SECRET_KEY"
ENV_SESSION_HTTPS_ONLY = "SESSION_HTTPS_ONLY"
_VALORES_VERDADEROS = frozenset({"1", "true"})


def secret_key():
    valor = os.environ.get(ENV_SECRET_KEY)
    if valor is None or not valor.strip():
        return None
    return valor


def session_https_only():
    valor = os.environ.get(ENV_SESSION_HTTPS_ONLY, "")
    return valor.strip().lower() in _VALORES_VERDADEROS
