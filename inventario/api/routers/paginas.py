"""Paginas HTML estaticas con redireccion segun sesion. Sin datos en el HTML (C-06, D1)."""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse

from inventario.api.dependencies import get_conexion, usuario_de_sesion

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"

CABECERAS_PAGINA = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}

router = APIRouter(include_in_schema=False)


def _html(nombre):
    return FileResponse(
        STATIC_DIR / nombre, media_type="text/html", headers=CABECERAS_PAGINA
    )


def _redirigir(destino):
    return RedirectResponse(destino, status_code=303, headers=CABECERAS_PAGINA)


@router.get("/")
def login(request: Request, conn=Depends(get_conexion)):
    if usuario_de_sesion(request, conn) is not None:
        return _redirigir("/inventario")
    return _html("login.html")


@router.get("/inventario")
def inventario(request: Request, conn=Depends(get_conexion)):
    if usuario_de_sesion(request, conn) is None:
        return _redirigir("/")
    return _html("index.html")


@router.get("/ordenes")
def ordenes(request: Request, conn=Depends(get_conexion)):
    if usuario_de_sesion(request, conn) is None:
        return _redirigir("/")
    return _html("ordenes.html")
