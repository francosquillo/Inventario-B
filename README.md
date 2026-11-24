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

5. **Base existente y actualización de esquema**: la primera vez que arrancás con el cambio `paso-5b-fixes-menores` sobre una base creada antes, la app reconstruye la tabla `movimientos` automáticamente (agrega el tipo `ajuste` y las columnas `stock_anterior` y `stock_nuevo`) en una sola transacción y conserva todas las filas. **Antes de ese primer arranque, copiá tu `dev-local.db`** (por ejemplo a `dev-local.db.bak`, fuera del repo o ignorada por git) por si necesitás volver atrás: el código viejo no entiende los movimientos de tipo `ajuste`. Los arranques siguientes no tocan nada.

La sesión dura 12 horas desde la última petición.

## Buscar y exportar a PDF

- **Buscar**: en `/inventario`, el campo "Buscar por código o nombre" filtra la tabla mientras escribís (sin distinguir mayúsculas ni tildes). Escape o "Limpiar búsqueda" la vacían.
- **Exportar el inventario**: "Exportar PDF" exporta las filas que se ven (todas si no hay búsqueda). En `/ordenes`, cada orden tiene su propio "Exportar PDF".
- **Cómo se guarda**: el botón abre el diálogo de impresión del navegador; elegí el destino "Guardar como PDF". Si no querés la URL y la fecha del navegador en los bordes de la hoja, desactivá "Encabezados y pies de página" en las opciones del diálogo.

## Tests

```bash
.venv/Scripts/python -m unittest discover -s tests -t .
```

Los tests usan `unittest` y SQLite real en un archivo temporal; no tocan tu base de desarrollo.
