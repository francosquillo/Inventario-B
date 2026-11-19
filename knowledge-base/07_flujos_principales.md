# Flujos Principales

Cada flujo describe la interacción entre el adaptador (API FastAPI), services y repositorio. En Fase 1 se invoca desde la Swagger UI (`/docs`) o `TestClient`; en Fase 2 desde el frontend. Services y endpoints son los mismos en ambas fases.

## Flujo 1: Login
**Disparador**: el usuario ejecuta `POST /api/login` desde `/docs` (Fase 1) o abre la página de login (Fase 2).
**Actor**: Usuario.

**Pasos**:
1. El adaptador recibe usuario y contraseña en el cuerpo JSON.
2. AuthService busca el usuario en el repositorio.
3. Recalcula PBKDF2 con el salt almacenado y compara en tiempo constante.
4. Éxito: FastAPI (`POST /api/login`) guarda `usuario_id` en la cookie firmada (`SessionMiddleware`); en `/docs` el navegador reenvía la cookie same-origin, así los demás endpoints funcionan; en Fase 2 el JS de `static/login.html` redirige a `static/index.html` (inventario). Sin sesión, los endpoints responden 401 (`Depends(get_current_user)`) y el JS redirige al login.

```
Usuario → Adaptador → AuthService → UsuarioRepo
                                  ← usuario (hash, salt)
        ← sesión (cookie firmada)
```

**Casos de error**:
- Usuario inexistente o contraseña incorrecta → mensaje genérico (RN-AU-05).
- Campos vacíos → validación RN-VA-02.

## Flujo 2: Ingreso de stock
**Disparador**: `POST /api/stock/ingreso` (Fase 1, `/docs`) / modal de ingreso (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código y cantidad; valida cantidad entera > 0.
2. StockService busca el producto por código.
3. Existe y activo → suma. Existe e inactivo → reactiva y suma. No existe → exige `nombre` en el cuerpo y crea.
4. En una sola operación atómica: actualiza stock y registra movimiento `ingreso`.

```
Usuario → Adaptador → StockService → ProductoRepo / MovimientoRepo
                                    (transacción o RPC)
        ← producto actualizado
```

**Casos de error**:
- Cantidad inválida → rechazo (RN-VA-01).
- Producto nuevo sin nombre → rechazo (RN-PR-07).
- Falla de persistencia → rollback, sin estado parcial.

## Flujo 3: Egreso manual de stock
**Disparador**: `POST /api/stock/egreso` (Fase 1, `/docs`) / modal de egreso (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código y cantidad.
2. StockService verifica que el producto exista, esté activo y que 0 < cantidad ≤ stock.
3. Atómico: descuenta stock y registra movimiento `egreso`.

**Casos de error**:
- Producto inexistente/inactivo → mensaje claro.
- Cantidad > stock → rechazo, stock sin cambios (RN-ST-02).
- Concurrencia: en Postgres el descuento usa `UPDATE ... WHERE stock >= cantidad` dentro de la función RPC para evitar negativos.

## Flujo 4: Crear orden
**Disparador**: `POST /api/ordenes` (Fase 1, `/docs`) / modal de nueva orden (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recoge número, fecha `YYYY-MM-DD` y lista de (producto, cantidad); valida formatos.
2. OrdenService verifica unicidad del número, que haya ≥ 1 componente y que todos sean productos activos.
3. Valida stock de TODOS los componentes; si alguno falla, devuelve la lista de faltantes y no modifica nada.
4. Atómico: inserta la orden, inserta `orden_items`, descuenta stock de cada producto.

```
Usuario → Adaptador → OrdenService → OrdenRepo.crear_con_descuento()
                                       SQLite: transacción
                                       Supabase: RPC crear_orden(...)
        ← orden creada | error con faltantes
```

**Casos de error**:
- Número duplicado → rechazo (RN-OR-01).
- Fecha inválida → rechazo (RN-VA-03).
- Stock insuficiente en algún componente → rechazo total (RN-OR-04).
- Producto repetido en la misma orden → se consolidan las cantidades sumándolas (RN-OR-11).

## Flujo 5: Listar órdenes
**Disparador**: `GET /api/ordenes?desde&hasta` (Fase 1, `/docs`) / pantalla de órdenes (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario elige "todas" o ingresa `desde` y `hasta`.
2. OrdenService valida fechas y desde ≤ hasta.
3. Repo consulta `fecha BETWEEN desde AND hasta` (inclusivo) junto a sus ítems y los nombres de producto (activos o no).

**Casos de error**:
- Fecha inválida o rango invertido → mensaje claro.
- Sin resultados → mensaje de lista vacía.

## Flujo 6: Borrar orden
**Disparador**: `DELETE /api/ordenes/{id}?reintegrar=` (Fase 1, `/docs`) / modal de borrado (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario indica la orden; en Fase 2 el frontend pide confirmación (modal). La API no tiene confirmación propia.
2. La llamada debe traer `reintegrar=true|false` explícito (en Fase 2 el modal pregunta "¿Reintegrar el stock al inventario?" cada vez).
3. Si sí: atómico, suma las cantidades de `orden_items` a cada producto y borra la orden. Si no: solo borra la orden (y sus ítems por cascade).

**Casos de error**:
- Orden inexistente → mensaje claro.
- Confirmación negada (frontend) → no se llama a la API; `reintegrar` ausente → la API rechaza.
- Falla a mitad de reintegro → rollback completo (RN-OR-09).

## Flujo 7: Borrar producto (lógico)
**Disparador**: `DELETE /api/productos/{codigo}` (Fase 1, `/docs`) / modal de borrado (Fase 2).
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario indica el producto; en Fase 2 el frontend pide confirmación (modal).
2. ProductoService setea `activo = 0`.
3. El producto sale del inventario y de la selección de componentes; las órdenes históricas siguen mostrándolo.

**Casos de error**: producto inexistente o ya inactivo → mensaje claro.

## Flujo 8: Despliegue (Fase 3)
**Disparador**: push a GitHub.
**Actor**: Operador.

**Pasos**:
1. Crear proyecto Supabase y ejecutar `schema.sql` (tablas + RPC); correr script de seed del admin.
2. Subir el repo a GitHub.
3. Importar en Vercel; cargar `SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY` (y `ADMIN_DEFAULT_PASSWORD` para el seed).
4. Verificar login, inventario y una orden de prueba.
