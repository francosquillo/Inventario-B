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

6. **Categorías de producto (`paso-5e-categorias-productos`)**: la primera vez que arrancás sobre una base anterior, la app agrega la columna de categoría a `productos` (todos los productos existentes quedan "Sin categoría"), crea la tabla `categorias` y la siembra con "Motor", "Aceite" y "Filtro" **solo si está vacía** (una categoría renombrada o creada por vos no se pisa al reiniciar). Es una sola transacción: si algo falla se revierte y la app no arranca. **Antes de ese primer arranque, copiá tu `dev-local.db`** (por ejemplo a `dev-local.bak.db`, que `.gitignore` ya cubre con `*.db`) por si necesitás volver atrás. Los arranques siguientes no tocan nada.

La sesión dura 12 horas desde la última petición.

## Buscar y exportar a PDF

- **Buscar**: en `/inventario`, el campo "Buscar por código o nombre" filtra la tabla mientras escribís (sin distinguir mayúsculas ni tildes). Escape vacía solo el texto.
- **Filtrar por categoría**: el selector junto al buscador ("Todas las categorías", cada categoría y "Sin categoría") se combina con la búsqueda; el conteo dice "N de M productos" cuando filtra y "Limpiar filtros" restablece ambos. Los filtros se conservan al recargar la tabla tras una acción.
- **Exportar el inventario**: "Exportar PDF" exporta las filas que se ven (todas si no hay filtros), con la columna Categoría; con una categoría elegida, el encabezado dice "Aceite · 3 productos · AAAA-MM-DD". En `/ordenes`, cada orden tiene su propio "Exportar PDF".
- **Cómo se guarda**: el botón abre el diálogo de impresión del navegador; elegí el destino "Guardar como PDF". Si no querés la URL y la fecha del navegador en los bordes de la hoja, desactivá "Encabezados y pies de página" en las opciones del diálogo.

## Categorías

- **Qué son**: cada producto tiene a lo sumo una categoría (opcional; sin ella figura "Sin categoría"). El catálogo viene sembrado con Motor, Aceite y Filtro. En este paso **se administra solo por la API**, desde `/docs` con la sesión iniciada: no hay pantalla para crearlas.
- **API** (requieren sesión): `GET /api/categorias` (lista ordenada por nombre), `POST /api/categorias` (`{"nombre": "Tren delantero"}`; la clave, p. ej. `tren-delantero`, se deriva del nombre o se puede indicar con `clave`) y `PATCH /api/categorias/{clave}` (`{"nombre": "..."}`: renombra; **la clave no se puede cambiar**). El nombre es único sin distinguir mayúsculas (409 si se repite); no hay borrado.
- **En los productos**: "Nuevo ingreso" tiene "Categoría (opcional)"; "Modificar stock" permite asignar o quitar la categoría de cada línea (cambiar solo la categoría no registra movimiento ni reactiva un producto dado de baja); "Nueva orden" ofrece, en cada línea, un filtro de categoría para acotar la lista de productos (no se guarda en la orden). Las respuestas de producto de la API incluyen `categoria` (la clave o `null`).
- **Reporte**: `/reportes` muestra la categoría actual de cada producto (columna "Categoría").

## Reporte de productos en órdenes

- **Pantalla `/reportes`** (pestaña "Reportes"): muestra cuánto se usó de cada producto en las órdenes de un período, con la cantidad total y en cuántas órdenes figura. Ordena por cantidad (de mayor a menor) y marca los productos "dado de baja".
- **Fechas**: "Desde" es obligatorio; "Hasta" es opcional y vacío significa hoy (hora de Argentina). Al abrir la pantalla vienen cargadas con el mes en curso, pero el reporte no se genera hasta pulsar "Generar".
- **Producto**: por defecto "Todos los productos"; también se puede filtrar por uno de los productos usados en alguna orden (activos y dados de baja).
- **Exportar PDF**: exporta el último reporte generado (título, rango, cantidad de productos y tabla); el archivo se propone como `reporte-AAAA-MM-DD_AAAA-MM-DD`.
- **API** (requieren sesión, solo lectura): `GET /api/reportes/productos-en-ordenes?desde=&hasta=&codigo=` y `GET /api/reportes/productos-usados`.

## Tests

```bash
.venv/Scripts/python -m unittest discover -s tests -t .
```

Los tests usan `unittest` y SQLite real en un archivo temporal; no tocan tu base de desarrollo.
