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


def insertar_usuario(conn, username="admin"):
    cur = conn.execute(
        "INSERT INTO usuarios (username, password_hash, salt) VALUES (?, 'hash', 'salt')",
        (username,),
    )
    return cur.lastrowid


def movimientos(conn):
    """Filas (tipo, cantidad, codigo, usuario_id, fecha) ordenadas por id."""
    filas = conn.execute(
        "SELECT m.tipo, m.cantidad, p.codigo, m.usuario_id, m.fecha "
        "FROM movimientos m JOIN productos p ON p.id = m.producto_id ORDER BY m.id"
    ).fetchall()
    return [tuple(f) for f in filas]


def insertar_movimiento(conn, fecha, producto_id, tipo, cantidad, usuario_id):
    """Siembra la bitacora con la fecha como texto."""
    cur = conn.execute(
        "INSERT INTO movimientos (fecha, producto_id, tipo, cantidad, usuario_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (fecha, producto_id, tipo, cantidad, usuario_id),
    )
    return cur.lastrowid


def sembrar(ruta, productos):
    """Inserta productos (codigo, nombre, stock, activo) en la base de archivo `ruta`."""
    conn = conectar(ruta)
    try:
        for codigo, nombre, stock, activo in productos:
            insertar_producto(conn, codigo, nombre, stock, activo)
        conn.commit()
    finally:
        conn.close()


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
