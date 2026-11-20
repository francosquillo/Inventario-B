# Inventario-B

Control de stock de piezas y órdenes de trabajo para un taller o pyme chica. Backend FastAPI + SQLite con una web local (HTML estático + Tailwind + JavaScript vanilla) servida por el mismo servidor.

## Correr en local

1. **Entorno virtual y dependencias** (desde la raíz del repo):

   ```bash
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements-dev.txt
   ```

   En Linux/macOS el intérprete está en `.venv/bin/python`.

2. **Configuración**: creá **tu propio** archivo `.env` copiando `.env.example` y completá estas variables (el `.env` nunca se commitea):

   | Variable | Valor para desarrollo local |
   |----------|-----------------------------|
   | `SECRET_KEY` | Obligatoria. Generala con `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `SESSION_HTTPS_ONLY` | `false` (con `true` el navegador no manda la cookie por `http://localhost`) |
   | `INVENTARIO_DB_PATH` | `dev-local.db` (archivo SQLite de desarrollo; los `*.db` están en `.gitignore`) |
   | `ADMIN_DEFAULT_PASSWORD` | Opcional. Contraseña inicial del `admin`; ver el punto 4 |

3. **Arrancar el servidor**:

   ```bash
   .venv/Scripts/python -m uvicorn inventario.api.main:app --reload
   ```

   Abrí http://localhost:8000. La documentación interactiva de la API está en http://localhost:8000/docs.

4. **Credenciales**: usuario `admin`. La contraseña es `ADMIN_DEFAULT_PASSWORD` si la definiste **antes del primer arranque sobre esa base**; si no, es una contraseña generada que aparece **una sola vez** en el log de uvicorn.
   Si la perdiste: apuntá `INVENTARIO_DB_PATH` a un archivo nuevo (o borrá el `.db` de desarrollo) y arrancá de nuevo; se crea un `admin` nuevo.

La sesión dura 12 horas desde la última petición.

## Tests

```bash
.venv/Scripts/python -m unittest discover -s tests -t .
```

Los tests usan `unittest` y SQLite real en un archivo temporal; no tocan tu base de desarrollo.
