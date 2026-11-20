"""Dependencias de FastAPI: conexion por request, services y usuario actual (D8/D9)."""
from fastapi import Depends, HTTPException, Request

from inventario.domain.entities import UsuarioAutenticado
from inventario.repositories.sqlite_repo import (
    SqliteMovimientoRepository,
    SqliteProductoRepository,
    SqliteStockRepository,
    SqliteUsuarioRepository,
    conectar,
)
from inventario.services.auth_service import AuthService
from inventario.services.inventario_service import InventarioService
from inventario.services.movimientos_service import MovimientosService
from inventario.services.stock_service import StockService

SESSION_USUARIO_ID = "usuario_id"
SESSION_USERNAME = "username"
MENSAJE_NO_AUTENTICADO = "No autenticado."


def get_conexion(request: Request):
    conn = conectar(request.app.state.ruta_db)
    try:
        yield conn
    finally:
        conn.close()


def get_auth_service(conn=Depends(get_conexion)):
    return AuthService(SqliteUsuarioRepository(conn))


def get_inventario_service(conn=Depends(get_conexion)):
    return InventarioService(SqliteProductoRepository(conn))


def get_stock_service(conn=Depends(get_conexion)):
    return StockService(SqliteStockRepository(conn))


def get_movimientos_service(conn=Depends(get_conexion)):
    return MovimientosService(SqliteMovimientoRepository(conn))


def get_current_user(request: Request) -> UsuarioAutenticado:
    usuario_id = request.session.get(SESSION_USUARIO_ID)
    username = request.session.get(SESSION_USERNAME)
    if usuario_id is None or username is None:
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)
    return UsuarioAutenticado(id=usuario_id, username=username)
