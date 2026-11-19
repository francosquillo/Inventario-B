"""Login, logout y usuario actual. Sin logica de negocio: delega en AuthService."""
from fastapi import APIRouter, Depends, Request, Response

from inventario.api.dependencies import (
    SESSION_USERNAME,
    SESSION_USUARIO_ID,
    get_auth_service,
    get_current_user,
)
from inventario.api.schemas import LoginRequest, UsuarioOut

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=UsuarioOut)
def login(datos: LoginRequest, request: Request, auth=Depends(get_auth_service)):
    request.session.clear()  # tambien ante fallo: mitiga fijacion de sesion
    usuario = auth.login(datos.username, datos.password)
    request.session[SESSION_USUARIO_ID] = usuario.id
    request.session[SESSION_USERNAME] = usuario.username
    return UsuarioOut(id=usuario.id, username=usuario.username)


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=UsuarioOut)
def me(usuario=Depends(get_current_user)):
    return UsuarioOut(id=usuario.id, username=usuario.username)
