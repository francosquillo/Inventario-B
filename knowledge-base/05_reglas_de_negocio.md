# Reglas de Negocio

Cada regla tiene un código único `RN-{DOMINIO}-{NN}` para trazabilidad.

## Dominio: Autenticación (RN-AU)

- **RN-AU-01**: Para operar el sistema se requiere login con usuario y contraseña.
- **RN-AU-02**: Las contraseñas se guardan como hash PBKDF2-HMAC-SHA256 (`hashlib.pbkdf2_hmac`) con salt aleatorio por usuario; nunca en texto plano.
- **RN-AU-03**: Sin sesión válida no se accede a ninguna operación (API: endpoints protegidos devuelven 401; web: el frontend redirige al login).
- **RN-AU-04**: Existe un usuario `admin` creado por defecto al inicializar la base. Todos los usuarios tienen los mismos permisos.
- **RN-AU-05**: Credenciales inválidas se rechazan con un mensaje genérico (no revela si falló usuario o contraseña).
- **RN-AU-06**: La comparación de hashes usa comparación en tiempo constante (`hmac.compare_digest`).

## Dominio: Productos (RN-PR)

- **RN-PR-01**: El código interno es único por producto.
- **RN-PR-02**: El stock de un producto nunca es negativo; un producto con stock 0 sigue existiendo.
- **RN-PR-03**: El borrado de producto es lógico (`activo = 0`): desaparece del inventario y de la selección para nuevas órdenes. La baja no genera movimientos ni pierde stock; se reactiva al ingresar stock con su código o por reintegro de una orden (RN-OR-12).
- **RN-PR-04**: Las órdenes históricas siguen mostrando productos dados de baja.
- **RN-PR-05**: El inventario general lista solo productos activos.
- **RN-PR-06**: Ingresar stock con el código de un producto inactivo lo reactiva (`activo = 1`) y suma la cantidad (mantiene unicidad del código).
- **RN-PR-07**: Un producto nuevo requiere nombre no vacío.
- **RN-PR-08**: El alta explícita (`POST /api/productos`, "Nuevo ingreso" en la web) exige código (hasta 50, normalizado con recorte + MAYÚSCULAS), nombre (1 a 120) y stock inicial entero de 0 a 10.000; con stock 0 el producto queda activo sin stock y sin movimiento.
- **RN-PR-09**: Dar de alta el código de un producto activo se rechaza con 409 "Ya existe un producto con código 'X'." sin modificar nada.
- **RN-PR-10**: Dar de alta el código de un producto dado de baja lo reactiva reemplazando su nombre y su stock por los nuevos (`reactivado: true`); registra un `ajuste` si el stock cambia y ningún movimiento si no cambia.
- **RN-PR-11** (C-06e): La categoría de un producto es opcional (`null`/ausente = "Sin categoría"). Se envía como clave (se normaliza con recorte + minúsculas); una clave desconocida se rechaza con 422 "La categoría 'x' no existe." (en lotes, con prefijo "Línea N: ").
- **RN-PR-12** (C-06e): Dar de alta (Nuevo ingreso) el código de un producto dado de baja reemplaza también su categoría por la indicada (o la quita); la categoría no influye en el 409 por código activo ni en la decisión de reactivar.
- **RN-PR-13** (C-06e): En "Modificar stock", una línea puede traer `categoria` (clave, o `null` para quitarla; ausente = no cambia). Cambiar solo la categoría no registra movimiento y no reactiva un producto dado de baja.
- **RN-PR-14** (C-06e): Las categorías se administran solo por la API (sin pantalla web): `POST /api/categorias` (clave opcional, derivada del nombre si falta) `PATCH /api/categorias/{clave}` (solo renombra; la clave es inmutable, enviarla da 422) y `DELETE /api/categorias/{clave}` (C-06f). Clave repetida → 409 "Ya existe una categoría con clave 'x'."; nombre repetido (sin distinguir mayúsculas) → 409 "…con nombre 'X'."; clave inexistente → 404.
- **RN-PR-15** (C-06f): Borrar una categoría con `DELETE /api/categorias/{clave}` solo se permite si ningún producto, activo o dado de baja, la tiene asignada; si alguno la usa → 409 "La categoría 'x' está asignada a N producto(s)." sin cambios. Una categoría borrada no se vuelve a sembrar al reiniciar.

## Dominio: Stock y movimientos (RN-ST)

- **RN-ST-01**: Ingreso de stock se hace por código interno: si existe, suma la cantidad; si no existe, pide nombre y crea el producto con esa cantidad.
- **RN-ST-02**: Egreso manual (sin orden) exige cantidad entera > 0 y ≤ stock actual; si excede, se rechaza.
- **RN-ST-03**: Todo ingreso y egreso manual se registra en `movimientos` (fecha, producto, tipo, cantidad, usuario).
- **RN-ST-04**: La actualización de stock y el registro del movimiento son una operación atómica (ambos o ninguno).
- **RN-ST-05**: Los movimientos se registran sin pedir motivo.
- **RN-ST-06**: Los descuentos generados por órdenes NO se registran en `movimientos`; quedan reflejados en la propia orden (`orden_items`).
- **RN-ST-07**: La modificación de stock (`POST /api/stock/modificaciones`, "Modificar stock" en la web) recibe de 1 a 100 líneas y es todo o nada en una transacción. Orden de rechazos: validación de datos (primera línea inválida, "Línea N: ..."), producto repetido en el lote ("Línea N: el producto 'X' ya está en la línea M."), códigos inexistentes (404 con todos los códigos).
- **RN-ST-08**: Cada línea tiene un modo: `fijar` (stock absoluto entero de 0 a 10.000; si cambia registra un movimiento `ajuste` con stock anterior, stock nuevo y cantidad = diferencia absoluta) o `sumar` (cantidad entera de 1 a 10.000; registra un `ingreso`). Fijar el mismo stock en un producto activo se acepta sin efectos ni movimiento.
- **RN-ST-09**: Una línea puede traer un nombre nuevo opcional (hasta 120; vacío o igual = sin cambio); renombrar no registra movimientos.
- **RN-ST-10**: Una línea sobre un producto dado de baja lo reactiva solo si su stock cambia efectivamente (`sumar`, o `fijar` en un valor distinto) y el stock resultante es > 0 (`reactivado: true`); si no (fijar en 0, mismo stock o solo renombrar) sigue dado de baja (`reactivado: false`). La reactivación no registra movimiento propio.

## Dominio: Órdenes (RN-OR)

- **RN-OR-01**: El número de orden es único.
- **RN-OR-02**: La fecha de la orden la ingresa el usuario a mano en formato `YYYY-MM-DD`.
- **RN-OR-03**: Una orden requiere al menos 1 componente; cada componente es un producto activo con cantidad entera > 0.
- **RN-OR-04**: Al crear, se valida el stock de TODOS los componentes; si alguno no alcanza, se rechaza la orden completa sin modificar nada.
- **RN-OR-05**: Si el stock alcanza, se descuentan todos los componentes y se crea la orden de forma atómica.
- **RN-OR-06**: Solo productos activos son seleccionables como componentes.
- **RN-OR-07**: El listado de órdenes admite todas o un filtro por número exacto (normalizado: recorte + MAYÚSCULAS) y/o un rango de fechas `YYYY-MM-DD` inclusivo en ambos extremos. `desde` y `hasta` son opcionales por separado (rango abierto), los filtros se combinan por AND y el rango se valida (desde ≤ hasta). Un número inexistente da 404; uno existente fuera del rango da lista vacía. Orden: fecha de la orden DESC, luego id DESC.
- **RN-OR-08**: Al borrar una orden, identificada por su número (no por id), el sistema pregunta cada vez si se reintegra al inventario el stock descontado; la API exige `reintegrar=true|false` explícito en cada llamada.
- **RN-OR-09**: Si se elige reintegrar, la devolución de stock y el borrado de la orden son atómicos (una transacción, todo o nada); si no, solo se borra la orden. Ninguna de las dos opciones genera movimientos de stock.
- **RN-OR-10**: Las órdenes no se editan en v1.
- **RN-OR-11**: Si al crear una orden se carga varias veces el mismo producto, las cantidades se consolidan sumándose en una sola línea (la validación de stock se hace sobre el total).
- **RN-OR-12**: Al reintegrar stock por borrado de orden, si un producto estaba dado de baja (`activo = 0`) se reactiva (`activo = 1`) y recibe las unidades devueltas, conservando su stock previo.

- **RN-OR-13** (C-06f): Una orden puede registrar cero o más procesos (opcionales). Los del catálogo se indican por clave (recorte + minúsculas); el mismo proceso del catálogo repetido cuenta una sola vez; una clave inexistente rechaza la orden completa ("El proceso 'x' no existe.").
- **RN-OR-14** (C-06f): Una orden admite hasta 10 procesos personalizados de texto libre (recortado, 1 a 60 caracteres). Un personalizado no puede llamarse como un proceso del catálogo (se pide marcarlo de la lista) ni repetirse entre los personalizados (sin distinguir mayúsculas). Los errores se informan con la posición ("Proceso personalizado N: ..."). Un personalizado queda solo en su orden: no se agrega al catálogo.
- **RN-OR-15** (C-06f): Cada proceso registrado guarda su nombre al crear la orden (snapshot) y si fue personalizado; renombrar o borrar el proceso del catálogo no altera órdenes ya creadas. Se devuelven en orden de carga (catálogo primero, luego personalizados).
- **RN-OR-16** (C-06f): Crear la orden con sus procesos es atómico (todo o nada, junto con el descuento de stock); registrar procesos no toca stock, movimientos ni productos, y la orden sigue exigiendo al menos un componente. Borrar una orden borra sus procesos.
- **RN-OR-17** (C-06f): El catálogo de procesos se administra solo por la API: `POST /api/procesos` (clave opcional derivada del nombre), `PATCH /api/procesos/{clave}` (solo renombra; clave inmutable), `DELETE /api/procesos/{clave}` (permitido aunque haya órdenes que lo usaron). Clave o nombre repetido (sin distinguir mayúsculas) → 409; clave inexistente → 404; nombre vacío o de más de 60 → 422.

## Dominio: Validaciones globales (RN-VA)

- **RN-VA-01**: Las cantidades son enteros > 0. Excepción: el stock inicial del alta y el stock fijado por un ajuste son enteros de 0 a 10.000 (RN-PR-08, RN-ST-08).
- **RN-VA-02**: Los campos obligatorios no pueden estar vacíos (se recortan espacios antes de validar).
- **RN-VA-03**: Las fechas usan formato `YYYY-MM-DD` y deben ser fechas reales (p. ej. `2026-02-30` es inválida).
- **RN-VA-04**: Toda validación se aplica en frontend (UX) y en backend (autoridad); el backend nunca confía en el frontend.
- **RN-VA-05**: Todo borrado (orden o producto) requiere confirmación (la confirmación es del adaptador de UI: modal en la web; la API exige el parámetro explícito `reintegrar` y no tiene paso de confirmación propio).

## Dominio: Seguridad (RN-SE)

- **RN-SE-01**: Prohibido hardcodear URLs, claves API o contraseñas; todo vía `os.environ` (`.env` local, variables de Vercel).
- **RN-SE-02**: `SUPABASE_KEY` (service_role) se usa solo en el backend FastAPI; el navegador nunca habla con Supabase.
- **RN-SE-03**: La sesión web es una cookie firmada (Starlette `SessionMiddleware`) con `SECRET_KEY` (HttpOnly, SameSite=Lax, `https_only` en producción).
- **RN-SE-04**: `.env` está en `.gitignore`; `.env.example` contiene solo nombres de variables, sin valores reales.
- **RN-SE-05**: Todas las consultas están parametrizadas (sin concatenar SQL con input de usuario).
- **RN-SE-06**: La contraseña se oculta al tipearla (web con `input type="password"`; en `/docs` el campo es de texto de la API, sin enmascarar, aceptado en el prototipo local).

## Dominio: Excepciones globales

- Las operaciones compuestas (crear orden, borrar orden con reintegro, ingreso/egreso con movimiento, alta de producto, modificación de stock en lote) son todo-o-nada. En SQLite se resuelve con transacciones; en Supabase con funciones RPC de Postgres.
- Cualquier error de validación devuelve un mensaje claro y no deja estado parcial.
