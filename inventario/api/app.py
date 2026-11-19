"""App factory y composition root. Unico modulo (junto al resto de api/) que conoce FastAPI."""
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from inventario import config
from inventario.api.routers import auth, inventario
from inventario.domain.errors import CredencialesInvalidas, MENSAJE_CREDENCIALES_INVALIDAS
from inventario.repositories.sqlite_repo import (
    SqliteUsuarioRepository,
    conectar,
    inicializar_esquema,
)
from inventario.services.inicializacion_service import sembrar_admin

log = logging.getLogger("inventario")

SESSION_COOKIE = "inventario_session"
_SIN_VALOR = object()


def inicializar_base(ruta_db, password_admin, repo_cls=SqliteUsuarioRepository):
    """Crea esquema y admin (idempotente). Devuelve la contrasena solo si fue generada."""
    conn = conectar(ruta_db)
    try:
        inicializar_esquema(conn)
        try:
            return sembrar_admin(repo_cls(conn), password_admin)
        except sqlite3.IntegrityError as exc:
            # Otro proceso creo el admin entre la consulta y el insert (D6).
            log.warning("Seed del admin omitido por IntegrityError: %s", exc)
            return None
    finally:
        conn.close()


def crear_app(*, ruta_db=None, secret_key=None, password_admin=_SIN_VALOR, https_only=None):
    ruta_db = ruta_db or config.ruta_db()
    if secret_key is None:
        secret_key = config.secret_key()
    if not secret_key or not secret_key.strip():
        raise RuntimeError(
            f"Falta la variable de entorno {config.ENV_SECRET_KEY}. Generala con: "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    if https_only is None:
        https_only = config.session_https_only()
    if password_admin is _SIN_VALOR:
        password_admin = config.password_admin()

    @asynccontextmanager
    async def lifespan(app):
        generada = inicializar_base(ruta_db, password_admin)
        if generada is not None:
            log.warning(
                "Se creo el usuario 'admin' con la contrasena generada: %s "
                "(anotala, no se volvera a mostrar)",
                generada,
            )
        app.state.ruta_db = ruta_db
        yield

    app = FastAPI(title="Inventario-B API", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie=SESSION_COOKIE,
        max_age=None,  # cookie de sesion del navegador (decision 7)
        same_site="lax",
        https_only=https_only,
    )
    app.include_router(auth.router)
    app.include_router(inventario.router)

    @app.exception_handler(CredencialesInvalidas)
    async def credenciales_invalidas(request: Request, exc: CredencialesInvalidas):
        return JSONResponse(status_code=401, content={"detail": MENSAJE_CREDENCIALES_INVALIDAS})

    return app
