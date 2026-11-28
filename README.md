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

6. **Categorías de producto (`paso-5e-categorias-productos`)**: la primera vez que arrancás sobre una base anterior, la app agrega la columna de categoría a `productos` (todos los productos existentes quedan "Sin categoría"), crea la tabla `categorias` y la siembra con "Motor", "Aceite" y "Filtro" **solo al crear la tabla** (desde `paso-5f-procesos-ordenes` el catálogo no se vuelve a sembrar: una categoría renombrada, creada o borrada por vos no se pisa ni resucita al reiniciar). Es una sola transacción: si algo falla se revierte y la app no arranca. **Antes de ese primer arranque, copiá tu `dev-local.db`** (por ejemplo a `dev-local.bak.db`, que `.gitignore` ya cubre con `*.db`) por si necesitás volver atrás. Los arranques siguientes no tocan nada.

La sesión dura 12 horas desde la última petición.

7. **Procesos de órdenes (`paso-5f-procesos-ordenes`)**: la primera vez que arrancás, la app crea las tablas `procesos` (con "Cambio motor", "Cambio filtro" y "Limpieza") y `orden_procesos`. Es **aditiva**: no cambia ninguna fila ni tabla existente (las órdenes anteriores quedan sin procesos), todo en una transacción (si algo falla se revierte y la app no arranca). **Antes de ese primer arranque, copiá tu `dev-local.db` a `dev-local.bak-5f.db`** (`.gitignore` ya cubre `*.db`) por si necesitás volver atrás. Los arranques siguientes no tocan nada ni resiembran aunque vacíes el catálogo.

8. **Servicios generales de órdenes (`paso-5g-servicios-generales`)**: la primera vez que arrancás, la app crea las tablas `servicios_generales` (con "Servicio 20 hs"), `servicio_chequeos` (sus chequeos: "Chequeo de motor", "Chequeo de combustible" y "Chequeo eléctrico"), `orden_servicio` y `orden_servicio_chequeos`. Es **aditiva**: no cambia ninguna fila ni tabla existente (las órdenes anteriores quedan sin servicio general), todo en una transacción (si algo falla se revierte y la app no arranca). **Antes de ese primer arranque, copiá tu `dev-local.db` a `dev-local.bak-5g.db`** (`.gitignore` ya cubre `*.db`) por si necesitás volver atrás. Los arranques siguientes no tocan nada ni resiembran aunque vacíes o cambies el catálogo.
9. **Datos del cliente y precios de órdenes (`paso-5h-precios-datos-orden`)**: la primera vez que arrancás, la app agrega a `ordenes` las columnas `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso` y `fecha_egreso`, y a `orden_items`, `orden_procesos` y `orden_servicio` la columna `precio_centavos`. Es **aditiva**: no cambia ninguna fila (las órdenes anteriores quedan sin datos ni precios y con su `fecha` intacta), todo en una transacción (si algo falla se revierte y la app no arranca). **Antes de ese primer arranque, copiá tu `dev-local.db` a `dev-local.bak-5h.db`** (`.gitignore` ya cubre `*.db`) por si necesitás volver atrás. Los arranques siguientes no tocan nada.

## Buscar y exportar a PDF

- **Buscar**: en `/inventario`, el campo "Buscar por código o nombre" filtra la tabla mientras escribís (sin distinguir mayúsculas ni tildes). Escape vacía solo el texto.
- **Filtrar por categoría**: el selector junto al buscador ("Todas las categorías", cada categoría y "Sin categoría") se combina con la búsqueda; el conteo dice "N de M productos" cuando filtra y "Limpiar filtros" restablece ambos. Los filtros se conservan al recargar la tabla tras una acción.
- **Exportar el inventario**: "Exportar PDF" exporta las filas que se ven (todas si no hay filtros), con la columna Categoría; con una categoría elegida, el encabezado dice "Aceite · 3 productos · AAAA-MM-DD". En `/ordenes`, cada orden tiene su propio "Exportar PDF".
- **Cómo se guarda**: el botón abre el diálogo de impresión del navegador; elegí el destino "Guardar como PDF". Si no querés la URL y la fecha del navegador en los bordes de la hoja, desactivá "Encabezados y pies de página" en las opciones del diálogo.

## Categorías

- **Qué son**: cada producto tiene a lo sumo una categoría (opcional; sin ella figura "Sin categoría"). El catálogo viene sembrado con Motor, Aceite y Filtro. En este paso **se administra solo por la API**, desde `/docs` con la sesión iniciada: no hay pantalla para crearlas.
- **API** (requieren sesión): `GET /api/categorias` (lista ordenada por nombre), `POST /api/categorias` (`{"nombre": "Tren delantero"}`; la clave, p. ej. `tren-delantero`, se deriva del nombre o se puede indicar con `clave`) y `PATCH /api/categorias/{clave}` (`{"nombre": "..."}`: renombra; **la clave no se puede cambiar**). El nombre es único sin distinguir mayúsculas (409 si se repite). `DELETE /api/categorias/{clave}` borra una categoría y devuelve lo borrado; si algún producto (activo o dado de baja) la usa responde **409** ("La categoría 'x' está asignada a N producto(s).") y no cambia nada: reasigná esos productos con "Modificar stock" y volvé a intentar.
- **En los productos**: "Nuevo ingreso" tiene "Categoría (opcional)"; "Modificar stock" permite asignar o quitar la categoría de cada línea (cambiar solo la categoría no registra movimiento ni reactiva un producto dado de baja); "Nueva orden" ofrece, en cada línea, un filtro de categoría para acotar la lista de productos (no se guarda en la orden). Las respuestas de producto de la API incluyen `categoria` (la clave o `null`).
- **Reporte**: `/reportes` muestra la categoría actual de cada producto (columna "Categoría").

## Procesos de órdenes

- **Qué son**: cada orden puede registrar cero o más procesos realizados (por ejemplo "Cambio motor"). Vienen del catálogo (sembrado con Cambio motor, Cambio filtro y Limpieza) o son **personalizados**: texto libre válido solo para esa orden (hasta 10, de 1 a 60 caracteres, no entran al catálogo). La orden guarda el nombre tal como era al crearla: renombrar o borrar un proceso del catálogo no cambia las órdenes anteriores.
- **En la web**: "Nueva orden" tiene el bloque "Procesos" debajo de "Componentes" ("Agregar proceso": cada línea elige un proceso o "Personalizado"); `/ordenes` muestra la fila "Procesos:" con chips en cada orden que tiene, y el PDF de una orden los lista debajo de la tabla como "Procesos realizados".
- **API** (requieren sesión; el catálogo se administra **solo desde `/docs`**): `GET /api/procesos`, `POST /api/procesos` (`{"nombre": "Pintura"}`; la clave se deriva del nombre o se indica con `clave`), `PATCH /api/procesos/{clave}` (`{"nombre": "..."}`; la clave no se puede cambiar) y `DELETE /api/procesos/{clave}` (devuelve lo borrado). Nombre único sin distinguir mayúsculas (409). `POST /api/ordenes` acepta `procesos` (claves del catálogo) y `procesos_personalizados` (textos), ambos opcionales; las órdenes devuelven `procesos: [{"nombre", "personalizado", "precio"}]`. Alta y borrado de la orden con sus procesos son atómicos.

## Servicios generales de órdenes

- **Qué son**: cada orden puede registrar **cero o un** servicio general (por ejemplo "Servicio 20 hs"), que es un nombre con una lista ordenada de **chequeos** incluidos (hasta 30, de 1 a 60 caracteres, sin repetir). Vienen del catálogo (sembrado con "Servicio 20 hs": Chequeo de motor, Chequeo de combustible y Chequeo eléctrico). La orden guarda el nombre y **todos** los chequeos tal como eran al crearla: renombrar, cambiar los chequeos o borrar un servicio del catálogo no cambia las órdenes anteriores. Puede llevar precio (ver "Datos del cliente y precios de órdenes") y no modifica el stock.
- **En la web**: "Nueva orden" tiene el bloque "Servicio general" entre la fecha y "Componentes" (un desplegable con "Sin servicio general" y los servicios; al elegir uno se ve la lista "Incluye:"). `/ordenes` muestra la fila "Servicio general:" (nombre y chips de chequeos) en cada orden que lo tiene, y el PDF de una orden lo imprime primero, tras el encabezado y antes de la tabla de componentes. El botón **"Servicios generales"** de `/ordenes` abre el catálogo para crear, editar (nombre y chequeos) y eliminar servicios.
- **API** (requieren sesión; también se puede administrar desde `/docs`): `GET /api/servicios-generales`, `POST /api/servicios-generales` (`{"nombre": "Servicio 100 hs", "chequeos": ["Cambio de aceite"]}`; la clave se deriva del nombre o se indica con `clave`), `PATCH /api/servicios-generales/{clave}` (`{"nombre": "..."}` y/o `{"chequeos": [...]}`, que **reemplaza la lista completa**; la clave no se puede cambiar) y `DELETE /api/servicios-generales/{clave}` (devuelve lo borrado). Nombre único sin distinguir mayúsculas (409). `POST /api/ordenes` acepta `servicio` (clave del catálogo o `null`), opcional; las órdenes devuelven `servicio: null | {"nombre", "chequeos": [texto], "precio"}`. Alta y borrado de la orden con su servicio son atómicos.

## Datos del cliente y precios de órdenes

- **Datos del cliente (todos opcionales)**: cada orden puede registrar `cliente` (hasta 80 caracteres), `celular` (6 a 20 caracteres: dígitos, espacios, `-`, paréntesis y un `+` inicial), `casco`, `motor` y `trailer` (hasta 60) y las fechas `fecha_ingreso` y `fecha_egreso` de la embarcación (`AAAA-MM-DD`; con ambas, el egreso no puede ser anterior al ingreso). La **`fecha` de la orden** sigue igual (obligatoria, la usan los filtros de `/ordenes` y `/reportes`) y no se compara con el ingreso ni el egreso.
- **Precios**: se tipean en la web en pesos (`12500`, `12.500`, `12.500,50`, `$ 12.500`) y la API los recibe y devuelve en **centavos enteros** (`1250050` = $ 12.500,50; de 0 a 99.999.999.999). Hay un precio opcional para el servicio general (`precio_servicio`), uno por cada servicio adicional y uno por cada componente (el **importe de la línea**, no un precio unitario). Vacío = sin precio, distinto de 0.
- **Subtotales y total** (calculados, no guardados; precio vacío cuenta 0): `subtotal_servicios` (servicio general + servicios adicionales), `subtotal_items` y `total`. La web los muestra en vivo en "Nueva orden" y `/ordenes` y el PDF de una orden los muestran con los valores que devuelve la API.
- **"Servicios adicionales"** es el nombre en la interfaz de los **procesos** (tablas, rutas y campos de la API siguen llamándose `procesos`).
- **API**: `POST /api/ordenes` acepta, además de lo anterior, `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso`, `fecha_egreso` y `precio_servicio`; cada componente acepta `precio`; `procesos` acepta claves o `{"clave", "precio"}` y `procesos_personalizados` acepta textos o `{"nombre", "precio"}`. Ejemplo:

```json
{
  "numero": "OT-0043", "fecha": "2026-11-27",
  "fecha_ingreso": "2026-11-26", "fecha_egreso": "2026-11-29",
  "cliente": "Juan Pérez", "celular": "11 5555-1234", "casco": "Bermuda 190",
  "componentes": [{"codigo": "A-01", "cantidad": 2, "precio": 1200000}],
  "servicio": "servicio-20-hs", "precio_servicio": 4500000,
  "procesos": [{"clave": "limpieza", "precio": 1500000}],
  "procesos_personalizados": [{"nombre": "Pulido"}]
}
```

  Las órdenes devuelven además `fecha_ingreso`, `fecha_egreso`, `cliente`, `celular`, `casco`, `motor`, `trailer`, `precio` en cada componente, proceso y servicio, y `subtotal_servicios`, `subtotal_items` y `total` (en este ejemplo 6000000, 1200000 y 7200000).

## Editar órdenes y chequeo final

- **Editar una orden**: en `/ordenes`, el botón "Editar" abre el mismo formulario de "Nueva orden" precargado. El número no se puede cambiar; todo lo demás (fecha, datos del cliente, servicio general, componentes, servicios adicionales, precios y chequeo final) se reemplaza por completo.
- **Stock por diferencia, todo o nada**: al guardar se descuenta lo que aumenta y se reintegra lo que baja o se quita (reintegrar reactiva productos dados de baja). Si algún producto no alcanza (409) o no existe/está dado de baja y se quiere aumentar (404), no cambia nada. La edición **no escribe movimientos** (igual que el alta y el borrado); la respuesta lista los `ajustes`.
- **API**: `PUT /api/ordenes/{numero}` con el cuerpo del alta sin `numero` (si se envía, 422), más `conservar_servicio` (`true` conserva el servicio general guardado y actualiza solo `precio_servicio`; no se combina con `servicio`). Responde `{"orden": {...}, "ajustes": [{"codigo", "nombre", "cantidad_anterior", "cantidad_nueva", "stock", "reactivado"}]}`. Ejemplo:

```json
{
  "fecha": "2026-11-27",
  "componentes": [{"codigo": "B-02", "cantidad": 1, "precio": 50000}],
  "chequeo_final": [{"clave": "entrega", "precio": 500000}]
}
```

- **Chequeo final**: lista fija de seis ítems (`combustible`, `puesta-en-marcha`, `check-list-y-verificacion-final`, `prueba-en-el-lago`, `limpieza-de-cortesia`, `entrega`), cada uno marcado con un precio opcional en centavos. `chequeo_final` (claves o `{"clave", "precio"}`) se acepta en el alta y la edición, se devuelve siempre (vacío si no hay) y suma al `subtotal_servicios`. En la web se carga solo al editar; el PDF de una orden lista los seis ítems (`[✓] Hecho` / `[ ] No se hizo`).
- **Migración (`paso-5i-modificar-ordenes-checkeo`)**: la primera vez que arrancás, la app crea la tabla `orden_chequeo_final` (aditiva, una transacción, las órdenes anteriores quedan sin chequeo). **Antes de ese primer arranque, copiá tu `dev-local.db` a `dev-local.bak-5i.db`** (`.gitignore` ya cubre `*.db`).

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
