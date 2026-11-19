"""Modelos Pydantic estrictos (D10). Pydantic solo vive en inventario/api/."""
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    id: int
    username: str


class ProductoOut(BaseModel):
    codigo: str
    nombre: str
    stock: int
    sin_stock: bool
