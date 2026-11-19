# Flujos Principales

Cada flujo describe la interacción entre adaptador (CLI/FastAPI), services y repositorio. Los services son los mismos en ambas fases.

## Flujo 1: Login
**Disparador**: el usuario abre la CLI o la página de login.
**Actor**: Usuario.

**Pasos**:
1. Adaptador pide usuario y contraseña (oculta).
2. AuthService busca el usuario en el repositorio.
3. Recalcula PBKDF2 con el salt almacenado y compara en tiempo constante.
4. Éxito: CLI abre el menú / FastAPI (`POST /api/login`) guarda `usuario_id` en la cookie firmada (`SessionMiddleware`); el JS de `static/login.html` redirige a `static/index.html` (inventario). Sin sesión, los endpoints responden 401 (`Depends(get_current_user)`) y el JS redirige al login.

```
Usuario → Adaptador → AuthService → UsuarioRepo
                                  ← usuario (hash, salt)
        ← sesión / menú
```

**Casos de error**:
- Usuario inexistente o contraseña incorrecta → mensaje genérico (RN-AU-05).
- Campos vacíos → validación RN-VA-02.

## Flujo 2: Ingreso de stock
**Disparador**: opción "Ingresar stock" / modal de ingreso.
**Actor**: Usuario autenticado.

**Pasos**:
1. Adaptador recibe código y cantidad; valida cantidad entera > 0.
2. StockService busca el producto por código.
3. Existe y activo → suma. Existe e inactivo → reactiva y suma. No existe → pide nombre y crea.
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
**Disparador**: opción "Descontar stock" / modal de egreso.
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
**Disparador**: opción "Crear orden" / modal de nueva orden.
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
**Disparador**: opción "Listar órdenes" / modal de listado.
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario elige "todas" o ingresa `desde` y `hasta`.
2. OrdenService valida fechas y desde ≤ hasta.
3. Repo consulta `fecha BETWEEN desde AND hasta` (inclusivo) junto a sus ítems y los nombres de producto (activos o no).

**Casos de error**:
- Fecha inválida o rango invertido → mensaje claro.
- Sin resultados → mensaje de lista vacía.

## Flujo 6: Borrar orden
**Disparador**: opción "Borrar orden" / modal de borrado.
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario indica la orden; el adaptador pide confirmación (`s/n` / modal).
2. El adaptador pregunta: "¿Reintegrar el stock al inventario?".
3. Si sí: atómico, suma las cantidades de `orden_items` a cada producto y borra la orden. Si no: solo borra la orden (y sus ítems por cascade).

**Casos de error**:
- Orden inexistente → mensaje claro.
- Confirmación negada → no se hace nada.
- Falla a mitad de reintegro → rollback completo (RN-OR-09).

## Flujo 7: Borrar producto (lógico)
**Disparador**: opción "Borrar producto" / modal de borrado.
**Actor**: Usuario autenticado.

**Pasos**:
1. Usuario selecciona producto; el adaptador pide confirmación.
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
