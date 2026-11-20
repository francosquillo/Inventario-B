"""App factory y composition root. Unico modulo (junto al resto de api/) que conoce FastAPI."""
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from inventario import config
from inventario.api.errores_validacion import mensaje_validacion
from inventario.api.routers import auth, inventario, movimientos, stock
from inventario.domain.errors import (
    CredencialesInvalidas,
    DatosInvalidos,
    MENSAJE_CREDENCIALES_INVALIDAS,
    NombreRequerido,
    ProductoNoEncontrado,
    StockInsuficiente,
)
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
    app.include_router(stock.router)
    app.include_router(movimientos.router)

    @app.exception_handler(CredencialesInvalidas)
    async def credenciales_invalidas(request: Request, exc: CredencialesInvalidas):
        return JSONResponse(status_code=401, content={"detail": MENSAJE_CREDENCIALES_INVALIDAS})

    def _responder(status):
        async def handler(request: Request, exc):
            return JSONResponse(status_code=status, content={"detail": str(exc)})

        return handler

    for tipo, status in (
        (DatosInvalidos, 422),
        (NombreRequerido, 422),
        (ProductoNoEncontrado, 404),
        (StockInsuficiente, 409),
    ):
        app.add_exception_handler(tipo, _responder(status))

    @app.exception_handler(RequestValidationError)
    async def validacion_en_espanol(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422, content={"detail": mensaje_validacion(exc.errors())}
        )

    return app
