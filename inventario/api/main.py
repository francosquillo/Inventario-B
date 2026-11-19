"""Entrada ASGI: `uvicorn inventario.api.main:app`."""
from dotenv import load_dotenv

from inventario.api.app import crear_app

load_dotenv()  # no pisa variables ya definidas en el entorno
app = crear_app()
