"""Utilidades compartidas por los tests (SQLite real en memoria)."""
import os
import secrets
import tempfile

from inventario.repositories.sqlite_repo import conectar, inicializar_esquema


def conexion_inicializada():
    conn = conectar(":memory:")
    inicializar_esquema(conn)
    return conn


def insertar_producto(conn, codigo, nombre, stock=0, activo=1):
    cur = conn.execute(
        "INSERT INTO productos (codigo, nombre, stock, activo) VALUES (?, ?, ?, ?)",
        (codigo, nombre, stock, activo),
    )
    return cur.lastrowid


# --- Helpers de la API (D12): archivo SQLite real en directorio temporal ---
PASSWORD_ADMIN_TEST = "Clave-Test-1"


def app_de_test(add_cleanup, password_admin=PASSWORD_ADMIN_TEST, https_only=False):
    """Crea la app sobre un archivo temporal. Devuelve (app, ruta_db).

    `add_cleanup` es `addCleanup`/`addClassCleanup` del test: el directorio se
    borra al final (LIFO: registrar el TestClient despues para que cierre antes).
    """
    from inventario.api.app import crear_app

    tmp = tempfile.TemporaryDirectory()
    add_cleanup(tmp.cleanup)
    ruta = os.path.join(tmp.name, "test.db")
    app = crear_app(
        ruta_db=ruta,
        secret_key=secrets.token_urlsafe(32),
        password_admin=password_admin,
        https_only=https_only,
    )
    return app, ruta


def cliente_de_test(add_cleanup, **kwargs):
    """TestClient con lifespan activo. Devuelve (client, ruta_db)."""
    from fastapi.testclient import TestClient

    app, ruta = app_de_test(add_cleanup, **kwargs)
    client = TestClient(app)
    client.__enter__()
    add_cleanup(client.__exit__, None, None, None)
    return client, ruta


def login(client, username="admin", password=PASSWORD_ADMIN_TEST):
    return client.post("/api/login", json={"username": username, "password": password})
