# Design — paso-5h-precios-datos-orden (C-06h)

## Context

Ver `proposal.md` (Why). Estado observado (C-01..C-06g archivados):

- **Esquema** (`inventario/repositories/sqlite_repo.py`): `ordenes (id, numero, fecha CHECK date, usuario_id, created_at)` y `orden_items (orden_id, producto_id, cantidad, PK (orden_id, producto_id))` en `ESQUEMA_SQL`; `orden_procesos` la crea `_crear_procesos`; `orden_servicio` (PK `orden_id`) y `orden_servicio_chequeos` las crea `_crear_servicios_generales`. Patrón de migración aditiva: `_migrar_productos_categoria` hace `ALTER TABLE ... ADD COLUMN` dentro de `_transaccion` (`BEGIN IMMEDIATE`) con verificación de conteos; `inicializar_esquema` corre todo lo transaccional antes de `NORMALIZAR_FECHAS_SQL`.
- **Órdenes**: `SqliteOrdenRepository.crear(numero, fecha, items, usuario_id, creada_en, procesos=(), servicio=None)`; `items` = `[(codigo, cantidad)]` ya consolidado; todo en una `_transaccion`. Lectura: `_SQL_LISTAR_ORDENES` (JOIN con ítems) + `_leer_procesos`/`_leer_servicios` por lote → `_a_ordenes`. Entidades: `Orden(id, numero, fecha, usuario, items, procesos=(), servicio=None)`, `ItemOrden(codigo, nombre, cantidad)`, `ProcesoOrden(nombre, personalizado)`, `ServicioOrden(nombre, chequeos)`.
- **Service**: `OrdenService.crear(numero, fecha, componentes, usuario_id, procesos, procesos_personalizados, servicio)` valida número → fecha → componentes (`_consolidar` suma repetidos) → servicio → procesos → personalizados; todo `DatosInvalidos` (422) antes de duplicado/productos/stock.
- **API**: `OrdenRequest` con tipos laxos (`Optional[Any]`) para que el service dé los mensajes; `orden_out(orden)` arma `OrdenOut`.
- **Web**: "Nueva orden" en `static/index.html` (`#modal-orden`, `max-width:36rem`): número + fecha; fieldset "Servicio general" (`select#ord-servicio` + "Incluye:"); "Componentes" (líneas `.line`: n.º, producto, cantidad, Quitar; filtro por categoría); "Procesos" (líneas `.pline`: select + Quitar, caja "Personalizado"). Módulos puros probados con Node: `procesos.js`, `servicios.js`. `/ordenes`: `ordenes.js` `articulo(o)` arma cabecera, fila "Servicio general:", fila "Procesos:" y tabla; "Exportar PDF" imprime el artículo con `#print-head` ("Orden OT-XXXX" / "Fecha: … · N componentes") y CSS de impresión en `app.css` (servicio primero, procesos al final como "Procesos realizados").
- `/reportes` (C-06d) y los filtros de `/ordenes` usan `ordenes.fecha`.

## Goals / Non-Goals

**Goals:**
- Precios tipeados (servicio general, cada ítem, cada servicio adicional), exactos (sin float), opcionales.
- Subtotal servicios, subtotal ítems y total calculados con una sola regla en backend y una réplica probada en el navegador (vista previa en vivo).
- Datos del cliente y la embarcación y fechas de ingreso y egreso, todos opcionales; la `fecha` de la orden no cambia.
- Migración aditiva e idempotente; alta de orden sigue siendo una sola transacción (regla dura 3).
- API compatible hacia atrás (todo campo nuevo es opcional).

**Non-Goals:**
- Editar precios o datos de una orden ya creada, checkeo final (C-06i); formato de impresión nuevo (C-06j).
- Lista de precios del catálogo, precios sugeridos, IVA, descuentos, moneda distinta de ARS.
- Filtros, búsqueda o reportes por cliente o por monto; total en `/reportes`.
- Renombrar "procesos" en tablas, rutas, campos de API o mensajes del backend.

## Decisions

### D1 — Dinero: centavos enteros (decisiones 1, 2)

- ★ Columna `precio_centavos INTEGER NULL` con `CHECK (precio_centavos IS NULL OR (typeof(precio_centavos) = 'integer' AND precio_centavos BETWEEN 0 AND 99999999999))` en `orden_items`, `orden_procesos` y `orden_servicio`. Tope $ 999.999.999,99: entra holgado en `INTEGER` de SQLite, en `bigint` de Postgres y como entero exacto en JS (100 ítems + 41 servicios × tope ≈ 1,4·10¹³ < 2⁵³).
- ★ **API en centavos enteros** (`precio`, `precio_servicio`, `subtotal_*`, `total`): el backend nunca parsea decimales ni usa `float`/`Decimal`; Pydantic recibe `Any` y el service exige `int` (no `bool`, no `float`, no texto). Mensaje: "El precio debe ser un entero de centavos entre 0 y 99.999.999.999." (con prefijo "Componente N: ", "Proceso N: ", "Proceso personalizado N: "; para el servicio: "El precio del servicio general debe ser un entero de centavos entre 0 y 99.999.999.999."). Alternativa: pesos con decimales en JSON (`12500.50`) → parseo de float en el backend; descartada.
- ★ **La web trabaja en pesos ARS**: la caja acepta `12500`, `12.500`, `12500,5`, `12.500,50`, `$ 12.500` (punto de miles **solo** en grupos de 3; coma decimal con 1-2 dígitos) y convierte a centavos con aritmética de enteros sobre el texto (sin `parseFloat`). `12.5` es **inválido** (ambiguo en es-AR): "Ingresá un importe válido (ej. 12.500,50)."; mayor al tope: "El importe admite hasta $ 999.999.999,99.". Formato de salida: `$ 12.500,00` (siempre 2 decimales, `Intl.NumberFormat("es-AR")` sobre `centavos/100` solo para mostrar, o armado manual con enteros ★ manual para no depender del ICU del navegador en tests Node).
- ★ **Opcional; vacío = `NULL` = "sin precio"**, distinto de 0 (0 = bonificado). Se muestra "—".

### D2 — Subtotales y total (pedido por el usuario 2026-11-27) (decisión 3)

- Reglas: **Subtotal servicios** = precio del servicio general + Σ precios de los servicios adicionales (procesos del catálogo y personalizados); **Subtotal ítems** = Σ importes de los ítems; **Total** = ambos. **Precio vacío cuenta como 0** (pedido del usuario). Sin ningún precio: 0, 0, 0.
- ★ **Calculados, no guardados**: propiedades de `Orden` en `domain/entities.py` (`subtotal_servicios`, `subtotal_items`, `total`, sumando `precio or 0`). No hay columnas que desincronizar si C-06i edita precios.
- ★ **La API los devuelve** (`subtotal_servicios`, `subtotal_items`, `total`, siempre enteros) en alta, listado y `orden` del borrado. Justificación: una sola autoridad de cálculo (backend, probada con `unittest`); `/ordenes` y el PDF muestran lo que dice la API sin recalcular; cualquier otro cliente (`/docs`, C-07) ve el mismo número. Costo: tres campos más por orden (aditivo).
- ★ **Réplica en el navegador solo para la vista previa en vivo** de "Nueva orden": función pura `Precios.resumen({servicio, adicionales: [...], items: [...]})` en `static/js/precios.js` (centavos o `null` → `{subtotal_servicios, subtotal_items, total}`), probada con Node con **los mismos casos** que el test del dominio (tabla de casos compartida en ambos tests, incluidos precios vacíos). Importes vacíos o inválidos mientras se tipea cuentan 0.

### D3 — Precio de cada ítem = importe de la línea (decisión 4)

- ★ El usuario tipea **lo que cobra por esa línea** (p. ej. "Aceite 10W40 x 2 → $ 24.000"), no un precio unitario: es lo que pidió ("individual por ítem"), evita multiplicar y redondear, y se consolida sin conflicto: si la API recibe el mismo código en varias líneas, la línea consolidada lleva **la suma de los importes indicados** (`NULL` si ninguna lo indicó). La web ya impide repetir producto, así que es un caso solo de API. Alternativa: precio unitario × cantidad (conflicto si dos líneas repetidas traen unitarios distintos; habría que rechazarlo).
- La columna de la tabla se llama **"Importe"**.

### D4 — Precio de cada servicio adicional (confirmado por el usuario 2026-11-27) (decisión 5)

- **Un precio por cada servicio adicional** (cada línea, del catálogo o personalizada, tiene su propia caja), **no** un precio único para todos (confirmado por el usuario, 2026-11-27).
- ★ API compatible: cada elemento de `procesos` puede ser la clave (texto, como hoy) **o** `{clave, precio}`; cada elemento de `procesos_personalizados`, el texto **o** `{nombre, precio}`. Objeto sin `clave`/`nombre` de texto o con otras claves → mensaje de tipo existente ("El campo procesos debe ser una lista de textos." / "…procesos_personalizados…"), que se conserva para no romper contratos (ver Riesgos). Error de precio → "Proceso N: …" / "Proceso personalizado N: …" (N = posición en su lista).
- ★ Clave del catálogo repetida en la API: cuenta la **primera aparición con su precio** (se mantiene la regla de C-06f). En la web, dos líneas con el mismo servicio del catálogo pasan a ser **error** ("Ya está en otra línea."), porque cada línea lleva su precio y descartar uno en silencio perdería plata.
- La web envía **siempre objetos** (`{clave, precio}` / `{nombre, precio}`, `precio: null` si vacío).
- `orden_procesos.precio_centavos`; `ProcesoOrden.precio: Optional[int] = None`.

### D5 — Precio del servicio general (decisión 6)

- `orden_servicio.precio_centavos` (anticipado en C-06g D1); `ServicioOrden.precio = None`. Campo de API **`precio_servicio`** (top-level, porque `servicio` es la clave en texto). `precio_servicio` sin servicio → 422 "No se puede indicar el precio del servicio general sin elegir uno.". En la web la caja "Precio" del servicio se deshabilita y vacía con "Sin servicio general".

### D6 — "Procesos" → "Servicios adicionales" solo en la interfaz (decisión 7)

- ★ Cambian solo textos visibles de la web: legend "Servicios adicionales", botón "Agregar servicio adicional", caja "Servicio adicional personalizado", contador/ayuda "Una orden admite hasta 10 servicios adicionales personalizados.", aviso "No se pudo cargar la lista de servicios adicionales.", fila "Servicios adicionales:" en `/ordenes` y título impreso "Servicios adicionales" (antes "Procesos realizados").
- **No cambian**: tablas (`procesos`, `orden_procesos`), rutas (`/api/procesos`), campos JSON, mensajes del backend ("El proceso 'x' no existe.", "Proceso personalizado N: …") ni los mensajes de `procesos.js` que replican al backend. Justificación: cero migración de datos/API y C-07 sin cambios de nombres; el usuario ve el concepto nuevo donde trabaja. Impacto: un 422 del backend puede decir "proceso" (raro: la web valida antes). Alternativa: renombrar todo (rutas, campos, tablas, tests de C-06f) — mucho churn sin valor funcional.

### D7 — Datos del cliente y la embarcación (decidido por el usuario 2026-11-27: todos opcionales) (decisiones 8, 9)

- **Todos opcionales** (decidido por el usuario, 2026-11-27): `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso`, `fecha_egreso`. Ausente, `null`, `""` o solo espacios → `NULL`. Se validan solo si se cargan. En la web, sin asterisco ni marca de obligatorio.
- ★ Límites: `cliente` hasta 80; `casco`, `motor`, `trailer` hasta 60 (texto libre recortado, espacios internos conservados). Mensajes: "El cliente admite hasta 80 caracteres.", "El campo casco admite hasta 60 caracteres." (ídem motor/trailer), "El campo X debe ser texto.".
- ★ **Celular permisivo**: recortado, 6-20 caracteres, regex `^\+?[0-9 ()-]+$` y al menos 6 dígitos (acepta `11 5555-1234`, `+54 9 11 5555-1234`, `(011) 4555-1234`). Se guarda tal cual lo escribió (sin normalizar). Mensaje: "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres).". Alternativa: normalizar a E.164 (YAGNI; no hay envío de SMS/WhatsApp).
- Columnas nuevas en `ordenes` (D9). Entidad `DatosOrden(cliente=None, celular=None, casco=None, motor=None, trailer=None, fecha_ingreso=None, fecha_egreso=None)`, `Orden.datos: DatosOrden = DatosOrden()`.

### D8 — "Fecha" sin cambios; fecha de ingreso y de egreso nuevas (modificado por el usuario 2026-11-27) (decisión 10)

- **Modificado por el usuario (2026-11-27)**, reemplaza la recomendación anterior "`fecha` = fecha de ingreso": la **"Fecha" de la orden queda exactamente como hoy** (obligatoria, etiqueta "Fecha", junto a "Número de orden", propone hoy; la usan los filtros de `/ordenes`, `/reportes` y el encabezado del PDF). Cero cambios en `ordenes.fecha`, en su validación y en sus mensajes.
- **Dos columnas nuevas y opcionales**: `fecha_ingreso TEXT NULL` y `fecha_egreso TEXT NULL` (`YYYY-MM-DD` reales). Son las fechas en que la embarcación entra y sale del taller; **sin relación ni restricción con `fecha`** (pueden ser anteriores o posteriores). Regla única entre ellas: con ambas presentes, `fecha_egreso >= fecha_ingreso`. Solo egreso o solo ingreso es válido.
- Mensajes (reutilizan `parsear_fecha`): "La fecha de ingreso debe tener formato AAAA-MM-DD." / "La fecha de ingreso (x) no es una fecha válida." (ídem egreso) y "La fecha de egreso no puede ser anterior a la de ingreso.".
- ★ En la web van **dentro del bloque "Cliente y embarcación"**, que conserva su nombre: las dos fechas describen la estadía de la embarcación en el taller (como casco, motor y trailer describen la embarcación), y un nombre corto se lee mejor que "Cliente, embarcación y estadía". La "Fecha" de la orden queda arriba, junto al número, como hoy.

### D9 — Migración idempotente (decisión 11)

`_migrar_datos_precios_orden(conn, loguear)` en `sqlite_repo.py`, llamada en `inicializar_esquema` **después de `_crear_servicios_generales`** (necesita `orden_servicio`) **y antes de `NORMALIZAR_FECHAS_SQL`**. ★ Un solo camino para bases nuevas y existentes (no se tocan `ESQUEMA_SQL`, `_CREAR_PROCESOS_SQL` ni `_CREAR_SERVICIOS_SQL`, así los tests de migración de C-06e/f/g siguen copiando su DDL literal):

```sql
ALTER TABLE ordenes ADD COLUMN cliente TEXT CHECK (cliente IS NULL OR length(trim(cliente)) BETWEEN 1 AND 80);
ALTER TABLE ordenes ADD COLUMN celular TEXT CHECK (celular IS NULL OR length(celular) BETWEEN 6 AND 20);
ALTER TABLE ordenes ADD COLUMN casco   TEXT CHECK (casco   IS NULL OR length(trim(casco))   BETWEEN 1 AND 60);
ALTER TABLE ordenes ADD COLUMN motor   TEXT CHECK (motor   IS NULL OR length(trim(motor))   BETWEEN 1 AND 60);
ALTER TABLE ordenes ADD COLUMN trailer TEXT CHECK (trailer IS NULL OR length(trim(trailer)) BETWEEN 1 AND 60);
ALTER TABLE ordenes ADD COLUMN fecha_ingreso TEXT CHECK (fecha_ingreso IS NULL OR
    (date(fecha_ingreso) IS NOT NULL AND fecha_ingreso = date(fecha_ingreso)));
ALTER TABLE ordenes ADD COLUMN fecha_egreso TEXT CHECK (fecha_egreso IS NULL OR
    (date(fecha_egreso) IS NOT NULL AND fecha_egreso = date(fecha_egreso)
     AND (fecha_ingreso IS NULL OR fecha_egreso >= fecha_ingreso)));
ALTER TABLE orden_items     ADD COLUMN precio_centavos INTEGER CHECK (<D1>);
ALTER TABLE orden_procesos  ADD COLUMN precio_centavos INTEGER CHECK (<D1>);
ALTER TABLE orden_servicio  ADD COLUMN precio_centavos INTEGER CHECK (<D1>);
```

1. Leer `PRAGMA table_info` de las cuatro tablas; si no falta ninguna columna → salir (idempotente).
2. En `_transaccion`: contar `ordenes`, `orden_items`, `orden_procesos`, `orden_servicio`, `orden_servicio_chequeos`, `productos`, `categorias`, `movimientos`, `procesos`, `servicios_generales`, `servicio_chequeos`; agregar **solo las columnas faltantes** (tabla `_COLUMNAS_NUEVAS`, diez columnas, `fecha_ingreso` antes que `fecha_egreso` de `(tabla, columna, ddl)`); verificar conteos iguales; error → rollback (DDL transaccional: no queda ninguna columna) y la excepción sube.
3. `log.info("Agregados datos del cliente y precios a las órdenes (%d orden(es) conservadas, sin datos ni precios).", n)` solo si la base ya existía.

Las filas existentes quedan en `NULL` (los CHECK aceptan `NULL`) y `ordenes.fecha` no se toca. **Riesgo verificado en el primer RED**: `ADD COLUMN` con un CHECK que referencia otra columna (`fecha_egreso >= fecha_ingreso`, agregada justo antes en la misma transacción); SQLite lo admite (un CHECK de columna puede leer otras columnas de la fila). Si la versión instalada lo rechazara, plan B: CHECK solo de formato y la regla egreso ≥ ingreso solo en el service (anotarlo como desvío).

### D10 — Entidades, repositorio y atomicidad (decisión 12)

- `ItemOrden.precio`, `ProcesoOrden.precio`, `ServicioOrden.precio` (`Optional[int] = None`, defaults para no romper constructores); `DatosOrden`; `Orden.datos`; propiedades de D2.
- `OrdenRepository.crear(numero, fecha, items, usuario_id, creada_en, procesos=(), servicio=None, datos=DatosOrden())` con `items = [(codigo, cantidad, precio)]`. Un solo `INSERT` de orden con los seis datos; ítems, procesos y servicio con su `precio_centavos`; **todo en la misma `_transaccion`** (sin cambios de estructura).
- Lectura: `_SQL_LISTAR_ORDENES` suma `o.cliente, o.celular, o.casco, o.motor, o.trailer, o.fecha_egreso, i.precio_centavos`; `_SQL_PROCESOS_DE_ORDENES` y `_SQL_SERVICIOS_DE_ORDENES` suman `precio_centavos`. Borrado sin cambios (las columnas viajan con sus filas).

### D11 — Validación en el service (decisión 13)

- `OrdenService.crear(..., datos=None, precio_servicio=None)` con `datos` como dict `{cliente, celular, casco, motor, trailer, fecha_ingreso, fecha_egreso}`; validación en funciones puras de `services/normalizacion.py` / `orden_service.py` (`normalizar_texto_opcional`, `validar_celular`, `validar_precio(valor, prefijo)`).
- **Prioridad dentro de "datos inválidos"**: número → fecha → fecha de ingreso → fecha de egreso → cliente → celular → casco → motor → trailer → componentes (cantidad y precio por línea) → servicio → precio del servicio → procesos (con precio) → personalizados (con precio). Así siguen valiendo todos los escenarios de prioridad de C-06f/C-06g.
- `_consolidar` devuelve `(codigo, cantidad, precio)` sumando precios no nulos (D3). Una línea `{codigo, cantidad}` sin `precio` sigue válida.

### D12 — API (decisión 14)

- `ComponenteRequest.precio: Optional[Any] = None`; `OrdenRequest` + `cliente`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso`, `fecha_egreso`, `precio_servicio` (`Optional[Any] = None`); `procesos`/`procesos_personalizados` siguen `Optional[Any]`. Descripciones OpenAPI: "Precio en centavos de ARS (entero ≥ 0) o null"; `fecha` sin cambios.
- `OrdenOut` exacto: `id, numero, fecha, fecha_ingreso, fecha_egreso, cliente, celular, casco, motor, trailer, usuario, componentes[{codigo, nombre, cantidad, precio}], procesos[{nombre, personalizado, precio}], servicio null|{nombre, chequeos, precio}, subtotal_servicios, subtotal_items, total`. Aditivo; se actualizan los tests de diccionario exacto (alta, listado, borrado). Sin rutas nuevas (OpenAPI sigue en 21).

### D13 — "Nueva orden" (mockup N1) (decisiones 15, 16)

- Modal a `max-width:44rem` (más campos por fila en escritorio; en 390 px todo apila).
- Orden de bloques: fila 1 "Número de orden" · "Fecha (AAAA-MM-DD)" **sin cambios** (ayuda "Hoy; se puede cambiar."); fieldset **"Cliente y embarcación"** (todos opcionales, sin asteriscos: Cliente ancho; Celular `type=tel inputmode=tel`; Casco, Motor, Trailer; **Fecha de ingreso** y **Fecha de egreso** `type=date`); "Servicio general" (select + caja **"Precio"** a la derecha en escritorio, abajo en móvil; "Incluye:"); "Componentes" (cada línea gana la caja **"Importe"** con prefijo `$`: escritorio `n · producto · cant · importe · Quitar`, móvil `producto` arriba y `cant · importe · Quitar` abajo); **"Servicios adicionales"** (cada línea: select · **importe** · Quitar; caja personalizada abajo); **resumen** al final del cuerpo (caja con "Subtotal servicios", "Subtotal ítems" y "Total" alineados a la derecha, `aria-live="polite"`, cifras `tabular-nums`).
- Cajas de importe: `type=text inputmode=decimal`, `aria-label` por línea ("Importe de la línea 2", "Precio del servicio adicional 1"), placeholder `0,00`, errores bajo la línea con `aria-invalid`/`aria-describedby` (patrón `.line-err`).
- Módulos puros nuevos (sin DOM al cargar, `window.X`, probados con Node): `static/js/precios.js` (`parsear(texto) → {centavos|null, error|null}`, `formatear(centavos|null) → "$ 12.500,00" | "—"`, `resumen(...)`) y `static/js/datos-orden.js` (`validar({cliente, celular, casco, motor, trailer, fecha_ingreso, fecha_egreso}) → {valores, errores}` con los mismos textos que el backend). `procesos.js` gana la detección de repetidos por línea.

### D14 — `/ordenes` (mockup L1) (decisión 17)

- Cabecera **sin cambios**: número · fecha · "N componentes" · acciones.
- Fila de datos (solo si tiene alguno): "Cliente: Juan Pérez · Cel.: 11 5555-1234 · Casco: Bermuda 190 · Motor: Mercury 90 HP · Trailer: AB 123 CD · Ingreso: 2026-11-26 · Egreso: 2026-11-29", solo los que tiene, envolviendo en móvil (`dl` en línea).
- "Servicio general:" nombre + **precio** + chips de chequeos; "Servicios adicionales:" chips con "Nombre · $ 15.000,00" (o "Nombre · —").
- Tabla de componentes con columna **"Importe"** (derecha, `—` si vacío).
- **Resumen** al pie de la orden, alineado a la derecha: "Subtotal servicios", "Subtotal ítems", "Total" (Total en negrita), valores de la API. Órdenes viejas: fila de datos ausente, importes "—", resumen en "$ 0,00" (regla "vacío = 0"; ver Open Questions Q3).

### D15 — PDF de una orden (mockup P1) (decisión 18)

Misma mecánica de C-06c/C-06f/C-06g (imprime el artículo; `#print-head`), sin rediseño (C-06j):

1. Encabezado **sin cambios**: "Orden OT-0043" / "Fecha: 2026-11-27 · 2 componentes".
2. Datos del cliente (los que tenga), en dos columnas: "Cliente: …" · "Celular: …", "Ingreso: …" · "Egreso: …", "Casco: …" · "Motor: …", "Trailer: …".
3. "Servicio general": nombre y precio en la misma línea; chequeos uno por línea.
4. Tabla de componentes con "Importe".
5. "Servicios adicionales" (antes "Procesos realizados"): uno por línea con su precio a la derecha.
6. Resumen al final: "Subtotal servicios", "Subtotal ítems", "Total" a la derecha, con línea superior.

Cambia materialmente la hoja (datos, columna, precios, resumen) → mockup P1.

### D16 — Paridad Supabase (C-07) (decisión 19)

Postgres: `ordenes` + `cliente text check (char_length(btrim(cliente)) between 1 and 80)`, `celular`, `casco`, `motor`, `trailer`, `fecha_ingreso date`, `fecha_egreso date check (fecha_egreso >= fecha_ingreso)` (null-safe); `precio_centavos bigint check (precio_centavos between 0 and 99999999999)` en `orden_items`, `orden_procesos`, `orden_servicio`. La RPC `crear_orden` recibe los datos y los precios (ítems y procesos como jsonb con `precio`, `p_precio_servicio`). Subtotales/total los sigue calculando el dominio Python. Anotar en `CHANGES.md` § C-07 al archivar.

### D17 — Tests (Strict TDD, `unittest`, SQLite real)

- Migración: `tests/test_sqlite_migracion_precios.py` con el DDL de C-06g **copiado literal** (doce tablas, órdenes con ítems, procesos y servicio): columnas nuevas, filas idénticas, idempotencia (3 arranques), falla inyectada → ninguna columna nueva, log solo si la base existía; CHECKs (precio negativo/no entero/tope, cliente vacío/81, egreso < ingreso).
- Dominio: `tests/test_orden_totales.py` (tabla de casos de D2, compartida en espíritu con el test JS).
- Repositorio, service (validación, prioridad, consolidación de importes), API (`TestClient`: alta con datos y precios, compatibilidad sin campos nuevos, 422, diccionarios exactos, OpenAPI 21 rutas), JS puro con Node (`tests/test_precios_js.py`, `tests/test_datos_orden_js.py`, `tests/test_procesos_js.py` ampliado), guardas estáticas de HTML/JS, navegador en el verify contra los mockups.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-27)
- Mockups: openspec/changes/paso-5h-precios-datos-orden/mockups/ (`nueva-orden.html`, `ordenes.html`, `README.md`)
- Approval: approved (2026-11-27, by user)
- Preview: rendered (2026-11-27, 390x844 y 1440x900 vía http local; `mockups/previews/nueva-orden-N1-{mobile,desktop}.png`, `ordenes-L1-{mobile,desktop}.png`, `ordenes-P1-{mobile,desktop}.png`)
- Visual verify: passed (2026-11-27; uvicorn sobre una copia de `dev-local.db`, 1440x900 y 390x844; capturas en `mockups/verify/`; sin errores de consola ni pedidos fallidos)
- Independent verify: PASS WITH WARNINGS (2026-11-27)

Base: mockups aprobados de C-06g (assets copiados), tokens `design-system/tokens.css` + `ui.css`, tema oscuro único, cabecera de texto "Inventario". Solo las pantallas que cambian:

| ID | Pantalla | Estado |
|----|----------|--------|
| N1 | Nueva orden | "Fecha" sin cambios junto al número; "Cliente y embarcación" (todo opcional, con Fecha de ingreso y de egreso), precio del servicio general, "Importe" por componente, "Servicios adicionales" con un importe por línea (uno vacío) y resumen con subtotales y total |
| L1 | Órdenes | `OT-0043` con fecha como hoy, fila de datos con ingreso/egreso, precios, chips de servicios adicionales con precio, columna "Importe" y resumen; `OT-0041` anterior a los precios (sin datos, "—", resumen en $ 0,00) |
| P1 | Órdenes · hoja impresa | PDF de `OT-0043`: encabezado "Fecha:" sin cambios, datos con ingreso/egreso, servicio con precio, tabla con "Importe", "Servicios adicionales" con precios y resumen |

Sin mockup propio (justificado en `mockups/README.md`): errores de validación (estilos `.err`/`aria-invalid` ya aprobados), "Sin servicio general" (caja de precio deshabilitada), catálogo caído, modal de borrado. Una vez aprobados, N1, L1 y P1 son criterio de aceptación de las tareas de UI y del verify.

## Risks / Trade-offs

- [Migración sobre `dev-local.db` real] → solo `ADD COLUMN` en una transacción con verificación de conteos; backup `dev-local.bak-5h.db` y verify sobre una **copia**. Rollback: código anterior (ignora las columnas) o restaurar el backup.
- [`ADD COLUMN` con CHECK que lee `fecha_ingreso`] → probado en el primer RED; plan B en D9.
- [Centavos en la API] → menos amigable en `/docs` (hay que escribir `1250050`); a cambio, exactitud sin floats. Documentado en OpenAPI y README.
- [Total con precios vacíos = 0] → una orden sin precios muestra "$ 0,00", que puede leerse como "gratis"; regla pedida por el usuario; Q3 propone ocultar el resumen si la orden no tiene ningún precio.
- [Renombre solo en la interfaz] → API y backend siguen diciendo "proceso"; un 422 del backend puede mostrarse con esa palabra.
- [Mensaje de tipo de `procesos` no menciona objetos] → se mantiene el texto de C-06f para no romper contratos; `/docs` documenta la forma objeto.
- [Diccionarios exactos de `OrdenOut`] → aditivo para clientes; se actualizan los tests existentes de alta, listado y borrado.
- [Vista previa JS vs cálculo del backend] → misma tabla de casos en ambos tests; lo que se guarda y muestra en `/ordenes` es siempre lo del backend.

## Migration Plan

1. Antes del primer arranque: copiar `dev-local.db` a `dev-local.bak-5h.db` (el apply lo hace en el grupo 1 sin abrir el original).
2. Arrancar uvicorn: `_migrar_datos_precios_orden` agrega las diez columnas (`ordenes.fecha` intacta) y loguea "Agregados datos del cliente y precios a las órdenes (N orden(es) conservadas, sin datos ni precios).".
3. Arranques siguientes: nada.
4. Rollback: volver al código anterior (las columnas sobrantes se ignoran) o restaurar `dev-local.bak-5h.db`.

## Open Questions

Ya resueltas por el usuario (2026-11-27): subtotales + total con vacío = 0 (D2); un precio por cada servicio adicional (D4); todos los datos del cliente opcionales (D7); "Fecha" sin cambios + ingreso/egreso nuevos y opcionales dentro de "Cliente y embarcación" (D8). Quedan para confirmar (no bloquean; se aplica la ★):

- **Q1 — Precio del ítem**: ★ importe de la línea (lo que se cobra por la pieza en esa cantidad). ¿O preferís precio unitario × cantidad?
- **Q2 — Centavos**: ★ la web acepta centavos (`12.500,50`) y muestra siempre `,00`. ¿O preferís solo pesos enteros (`$ 12.500`)?
- **Q3 — Órdenes viejas sin precios**: ★ resumen en `$ 0,00` (regla literal). ¿O se oculta el resumen cuando la orden no tiene ningún precio?
- **Q4 — Renombre**: ★ "Servicios adicionales" solo en la web. ¿Hace falta también en API/mensajes?
- **Q5 — Límites**: cliente 80, casco/motor/trailer 60, celular 6-20. ¿Ok?

Al archivar: KB 02 (campos nuevos del alta y de la respuesta de órdenes), 04 (columnas nuevas, centavos, `fecha` vs. `fecha_ingreso`/`fecha_egreso`), 05 (RN-OR de precios, subtotales/total, datos del cliente, ingreso y egreso; RN-VA de importes y celular), 06 (US-006/US-007 con datos, precios y resumen), 07 (flujos de alta, listado y PDF); `CHANGES.md` C-06h `[x]` y paridad C-07 de D16.

## Decisiones para revisión del usuario

> Governance ALTO. ★ = recomendada. **Pedido/decidido por el usuario (2026-11-27)**: precios tipeados de servicio general, de cada ítem y de cada servicio adicional; subtotal servicios + subtotal ítems + total, vacío = 0; un precio por servicio adicional; todos los datos del cliente opcionales; "Fecha" sin cambios con ingreso/egreso nuevos.

1. **Representación** — ★ centavos enteros en la base y en la API; pesos ARS en la web. Alt.: pesos con decimales en la API.
2. **Precios opcionales** — ★ vacío = sin precio (`NULL`), distinto de 0; rango 0..$ 999.999.999,99.
3. **Subtotales y total** — calculados (no guardados), devueltos por la API, réplica JS solo para la vista previa; vacío = 0. _Pedido por el usuario (2026-11-27)._
4. **Precio del ítem** — ★ importe de la línea; repetidos en la API suman importes (Q1).
5. **Servicios adicionales** — un precio por línea (_confirmado por el usuario, 2026-11-27_); API acepta texto u objeto `{clave|nombre, precio}`; repetido del catálogo: la web da error, la API toma el primero.
6. **Precio del servicio general** — ★ `precio_servicio` top-level; sin servicio → 422.
7. **Renombre** — ★ "Servicios adicionales" solo en la web (Q4).
8. **Datos del cliente** — todos opcionales (_decidido por el usuario, 2026-11-27_); validados solo si se cargan.
9. **Límites y celular** — ★ 80/60, celular permisivo 6-20 sin normalizar (Q5).
10. **Fechas** — "Fecha" de la orden sin cambios; `fecha_ingreso` y `fecha_egreso` nuevas, opcionales, sin relación con `fecha`, egreso ≥ ingreso solo con ambas; en el bloque "Cliente y embarcación". _Modificado por el usuario (2026-11-27)._
11. **Migración** — ★ `ADD COLUMN` de las diez columnas en una transacción, idempotente, un solo camino para bases nuevas y viejas; backup `dev-local.bak-5h.db`.
12. **Atomicidad** — ★ datos y precios en la misma transacción del alta.
13. **Prioridad de errores** — ★ número → fecha → ingreso → egreso → cliente → celular → casco → motor → trailer → componentes → servicio → precio del servicio → procesos → personalizados.
14. **API** — ★ campos nuevos opcionales; `OrdenOut` con datos, `precio` por línea, subtotales y total; 21 rutas.
15. **"Nueva orden"** — ★ layout de D13 (mockup N1), modal a 44rem, resumen en vivo al final.
16. **Formato de importes** — ★ `12.500,50` (punto de miles, coma decimal), `12.5` inválido; salida `$ 12.500,00`; vacío "—".
17. **`/ordenes`** — ★ layout de D14 (mockup L1).
18. **PDF** — ★ esquema actual (encabezado "Fecha:" sin cambios) + datos con ingreso/egreso, "Importe", precios y resumen (mockup P1); "Procesos realizados" → "Servicios adicionales".
19. **Paridad C-07** — ★ columnas equivalentes en Postgres y RPC con datos y precios.
