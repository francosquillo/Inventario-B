# Mockups — paso-5b-fixes-menores (C-06b)

- Design system revision: 2 (`design-system/README.md`, tema oscuro único, aprobado 2026-11-20)
- Approval: approved (2026-11-20, by user)
- Preview: rendered (2026-11-20, Playwright, 19 estados × 390x844 y 1440x900 en `previews/`)
- Date: 2026-11-20

Son archivos HTML/CSS estáticos de revisión, **no** el frontend de producción. No tienen backend. Cada estado se elige por `#ID`. Visual heredado de los mockups aprobados de C-06 (`openspec/changes/archive/2026-11-20-paso-5-web-local/mockups/inventario.html`); solo cambian la barra de acciones, el cartel de inventario vacío y los dos modales nuevos.

## Preview

Servir la **raíz del repo** (los mockups enlazan `../../../../design-system/tokens.css` y `ui.css`):

```bash
python -m http.server 8765 --bind 127.0.0.1
```

- http://127.0.0.1:8765/openspec/changes/paso-5b-fixes-menores/mockups/inventario.html#I1
- `?captura` antes del `#` oculta la barra "MAQUETA" (capturas limpias), p. ej. `inventario.html?captura#MS3`.
- T2: capturar con el SO en modo claro (`emulateMedia({ colorScheme: 'light' })`); debe verse oscuro.
- Tailwind Play CDN `3.4.17` (requiere internet). JS requerido para elegir estados.

Archivos: `inventario.html`, `assets/mockup.css` (sección C = piezas nuevas: `.mline`, `.seg`, `.delta`, `.tag-baja`, `.tag-react`, `.sum-list`), `assets/mockup.js` (selector de estados, agregar/quitar líneas, cambio de modo; sin `innerHTML`), `assets/tailwind-config.js` (copia de C-06).

## Pantallas y estados

| ID | Estado |
|----|--------|
| I1 | Inventario con la barra nueva: "Nuevo ingreso", "Modificar stock", "Nueva orden", "Ver órdenes" |
| I2 | Vacío: "Todavía no hay productos — Creá el primero con Nuevo ingreso." |
| NI1 | Nuevo ingreso vacío: Código, Nombre, Stock (obligatorios; "Puede ser 0") — botón "Crear producto" |
| NI2 | Validación del navegador: "El nombre es obligatorio." / "El stock es obligatorio." |
| NI3 | 409 "Ya existe un producto con código 'A-01'." solo en la alerta superior; Código `aria-invalid`, `aria-describedby` → alerta, con foco |
| NI4 | Código de un producto dado de baja: aviso no bloqueante "Este código está dado de baja: se va a reactivar con el nombre y el stock que indiques." |
| NI5 | Éxito reactivado: "Producto reactivado: C-99 · Junta tórica (stock 6)." y la fila vuelve |
| NI6 | Éxito con stock 0: "Producto creado: N-01 · Arandela 6mm (stock 0)." y la fila con el 0 resaltado |
| MS1 | Modificar stock, una línea "Fijar en" 12 → "Stock actual 7 → 12"; nombre opcional ("Sin cambios (Tornillo M8)") |
| MS2 | Selector desplegado (en la maqueta, como lista): grupos "Activos" y "Dados de baja"; A-01 deshabilitado "— ya está en otra línea"; C-99 dado de baja con el mismo stock: aviso neutro "Dado de baja: sigue dado de baja (sin cambio de stock)." |
| MS3 | Cuatro líneas: fijar (A-01 7 → 12), sumar (B-02 0 → 24), solo renombrar (CAJA/10, stock 4 · sin cambios) y dado de baja (C-99, sumar 3: el stock cambia y queda > 0, aviso "se va a reactivar al guardar") |
| MS4 | Validación por línea: stock -1, línea sin producto ("Elegí un producto."), suma 0 |
| MS5 | 422 "Línea 2: El stock debe ser un entero entre 0 y 10.000." arriba + línea 2 marcada |
| MS6 | 404 `codigos: ["D-05"]`: alerta, línea 2 con "Este producto ya no existe: elegí otro o quitá la línea.", "La lista de productos se actualizó." |
| MS7 | Enviando: "Guardando…" deshabilitado |
| MS8 | Resumen de éxito persistente: "Stock modificado (4 productos)" con `7 → 12`, `0 → 24 (+24)`, "stock 4 sin cambios · nombre antes: …" y "2 → 5 (+3) · reactivado"; tabla actualizada |
| T1 | Foco visible en "Nuevo ingreso" |
| T1b | Foco visible en el selector "Fijar en / Sumar" de una línea |
| T2 | I1 con el SO en modo claro → se ve oscuro |

Capturas: `previews/inventario-<ID>-mobile.png` (390x844) y `previews/inventario-<ID>-desktop.png` (1440x900). Verificado: sin scroll horizontal de página en ningún estado; fondo oscuro en todos (incluido T2).

**Regla de reactivación (decisión del usuario 2026-11-20)**: un dado de baja se reactiva solo si el stock cambia y queda > 0 (sumar, o fijar en un valor distinto > 0). Fijar 0, fijar el mismo stock o solo renombrar lo dejan dado de baja: la línea avisa "sigue dado de baja (sin cambio de stock / stock 0)". Estados que lo muestran: MS2 (neutro), MS3, MS7, T1b y MS8 (reactivación por sumar). Revisión 2026-11-20: MS2 re-renderizado.

**Nota (maqueta)**: MS2 muestra el `<select>` como lista (`size`) solo para poder capturar las opciones; en la app es un desplegable normal con `<optgroup>`.
