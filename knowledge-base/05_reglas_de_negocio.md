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
- **RN-PR-03**: El borrado de producto es lógico (`activo = 0`): desaparece del inventario y de la selección para nuevas órdenes.
- **RN-PR-04**: Las órdenes históricas siguen mostrando productos dados de baja.
- **RN-PR-05**: El inventario general lista solo productos activos.
- **RN-PR-06**: Ingresar stock con el código de un producto inactivo lo reactiva (`activo = 1`) y suma la cantidad (mantiene unicidad del código).
- **RN-PR-07**: Un producto nuevo requiere nombre no vacío.

## Dominio: Stock y movimientos (RN-ST)

- **RN-ST-01**: Ingreso de stock se hace por código interno: si existe, suma la cantidad; si no existe, pide nombre y crea el producto con esa cantidad.
- **RN-ST-02**: Egreso manual (sin orden) exige cantidad entera > 0 y ≤ stock actual; si excede, se rechaza.
- **RN-ST-03**: Todo ingreso y egreso manual se registra en `movimientos` (fecha, producto, tipo, cantidad, usuario).
- **RN-ST-04**: La actualización de stock y el registro del movimiento son una operación atómica (ambos o ninguno).
- **RN-ST-05**: Los movimientos se registran sin pedir motivo.
- **RN-ST-06**: Los descuentos generados por órdenes NO se registran en `movimientos`; quedan reflejados en la propia orden (`orden_items`).

## Dominio: Órdenes (RN-OR)

- **RN-OR-01**: El número de orden es único.
- **RN-OR-02**: La fecha de la orden la ingresa el usuario a mano en formato `YYYY-MM-DD`.
- **RN-OR-03**: Una orden requiere al menos 1 componente; cada componente es un producto activo con cantidad entera > 0.
- **RN-OR-04**: Al crear, se valida el stock de TODOS los componentes; si alguno no alcanza, se rechaza la orden completa sin modificar nada.
- **RN-OR-05**: Si el stock alcanza, se descuentan todos los componentes y se crea la orden de forma atómica.
- **RN-OR-06**: Solo productos activos son seleccionables como componentes.
- **RN-OR-07**: El listado de órdenes admite todas o un filtro por número exacto (normalizado: recorte + MAYÚSCULAS) y/o un rango de fechas `YYYY-MM-DD` inclusivo en ambos extremos. `desde` y `hasta` son opcionales por separado (rango abierto), los filtros se combinan por AND y el rango se valida (desde ≤ hasta). Un número inexistente da 404; uno existente fuera del rango da lista vacía. Orden: fecha de la orden DESC, luego id DESC.
- **RN-OR-08**: Al borrar una orden, el sistema pregunta cada vez si se reintegra al inventario el stock descontado.
- **RN-OR-09**: Si se elige reintegrar, la devolución de stock y el borrado de la orden son atómicos; si no, solo se borra la orden.
- **RN-OR-10**: Las órdenes no se editan en v1.
- **RN-OR-11**: Si al crear una orden se carga varias veces el mismo producto, las cantidades se consolidan sumándose en una sola línea (la validación de stock se hace sobre el total).
- **RN-OR-12**: Al reintegrar stock por borrado de orden, si un producto estaba dado de baja (`activo = 0`) se reactiva (`activo = 1`) y recibe las unidades devueltas.

## Dominio: Validaciones globales (RN-VA)

- **RN-VA-01**: Las cantidades son enteros > 0.
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

- Las operaciones compuestas (crear orden, borrar orden con reintegro, ingreso/egreso con movimiento) son todo-o-nada. En SQLite se resuelve con transacciones; en Supabase con funciones RPC de Postgres.
- Cualquier error de validación devuelve un mensaje claro y no deja estado parcial.
