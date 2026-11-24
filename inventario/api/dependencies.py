"""Dependencias de FastAPI: conexion por request, services y usuario actual (D8/D9)."""
import sqlite3

from fastapi import Depends, HTTPException, Request

from inventario.domain.entities import UsuarioAutenticado
from inventario.repositories.sqlite_repo import (
    SqliteCategoriaRepository,
    SqliteMovimientoRepository,
    SqliteOrdenRepository,
    SqliteProductoRepository,
    SqliteStockRepository,
    SqliteUsuarioRepository,
)
from inventario.services.auth_service import AuthService
from inventario.services.categoria_service import CategoriaService
from inventario.services.inventario_service import InventarioService
from inventario.services.movimientos_service import MovimientosService
from inventario.services.orden_service import OrdenService
from inventario.services.reporte_service import ReporteService
from inventario.services.producto_service import ProductoService
from inventario.services.stock_service import StockService

SESSION_USUARIO_ID = "usuario_id"
SESSION_USERNAME = "username"
MENSAJE_NO_AUTENTICADO = "No autenticado."


def _abrir_conexion(ruta):
    # FastAPI corre las dependencias y endpoints sincronicos en hilos del pool, y la conexion
    # de un request puede crearse en un hilo y usarse en otro. Se usa de a una por vez dentro
    # de un unico request, asi que desactivar el chequeo de hilo es seguro; mismos row_factory y PRAGMA que `conectar`.
    conn = sqlite3.connect(ruta, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conexion(request: Request):
    conn = _abrir_conexion(request.app.state.ruta_db)
    try:
        yield conn
    finally:
        conn.close()


def get_auth_service(conn=Depends(get_conexion)):
    return AuthService(SqliteUsuarioRepository(conn))


def get_inventario_service(conn=Depends(get_conexion)):
    return InventarioService(SqliteProductoRepository(conn))


def get_stock_service(conn=Depends(get_conexion)):
    return StockService(SqliteStockRepository(conn), SqliteCategoriaRepository(conn))


def get_categoria_service(conn=Depends(get_conexion)):
    return CategoriaService(SqliteCategoriaRepository(conn))


def get_movimientos_service(conn=Depends(get_conexion)):
    return MovimientosService(SqliteMovimientoRepository(conn))


def get_orden_service(conn=Depends(get_conexion)):
    return OrdenService(SqliteOrdenRepository(conn))


def get_reporte_service(conn=Depends(get_conexion)):
    return ReporteService(SqliteOrdenRepository(conn))


def get_producto_service(conn=Depends(get_conexion)):
    return ProductoService(SqliteProductoRepository(conn))


def usuario_de_sesion(request: Request, conn):
    """Usuario de la sesion, o None sin sesion o si ya no existe (limpia la sesion)."""
    usuario_id = request.session.get(SESSION_USUARIO_ID)
    username = request.session.get(SESSION_USERNAME)
    if usuario_id is None or username is None:
        return None
    # La cookie esta firmada pero puede sobrevivir al usuario (base reseteada o
    # usuario borrado): se confirma contra `usuarios` antes de operar.
    usuario = SqliteUsuarioRepository(conn).obtener_por_id(usuario_id)
    if usuario is None:
        request.session.clear()
        return None
    return UsuarioAutenticado(id=usuario.id, username=usuario.username)


def get_current_user(request: Request, conn=Depends(get_conexion)) -> UsuarioAutenticado:
    usuario = usuario_de_sesion(request, conn)
    if usuario is None:
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)
    return usuario
