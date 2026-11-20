# Mockups — paso-5-web-local (C-06)

- Design system revision: 2 (`design-system/README.md`, dark-only theme, approval pending; Revision 1 was approved 2026-11-19)
- Approval: approved (2026-11-20, by user)
- Preview: pending (the orchestrator renders at 390x844 and 1440x900)
- Date: 2026-11-20

These are static HTML/CSS review files, **not** the production frontend. They have no backend. Every state is selected by `#ID`.

## Preview

`file://` is blocked in the orchestrator's browser. Serve the **repo root** instead, because the mockups link `../../../../design-system/tokens.css` and `ui.css` directly (one visual source):

```bash
python -m http.server 8765 --bind 127.0.0.1
```

Then open these URLs:

- http://127.0.0.1:8765/openspec/changes/paso-5-web-local/mockups/login.html#L1
- http://127.0.0.1:8765/openspec/changes/paso-5-web-local/mockups/inventario.html#I1
- http://127.0.0.1:8765/openspec/changes/paso-5-web-local/mockups/ordenes.html#O1

How the state URLs work:

- **Changing state.** Each page has a dashed "MAQUETA" bar with a state selector, ← → buttons and links between screens. The bar is not part of the app. To change state, change the `#ID` (for example `inventario.html#MO3`).
- **Clean captures.** Add `?captura` before the hash, for example `inventario.html?captura#MO3`. This hides the bar.
- **Theme.** The app is always dark (user decision 2026-11-20): `tokens.css` sets `color-scheme: dark` on `:root` and ignores `prefers-color-scheme`. **T2** checks this: capture `inventario.html#T2` and `ordenes.html#T2` with a **light** OS (Playwright `emulateMedia({ colorScheme: 'light' })`); they must look the same as I1/O1, dark.
- **Reduced motion.** `tokens.css` sets all durations to 0. The mockups add no animation.
- **Requirements.** Tailwind Play CDN `3.4.17` (pinned version) needs internet access. JS is required to select states.

## Screens and states

| File | ID | State |
|------|----|-------|
| login.html | L1 | empty |
| | L2 | 401 "Usuario o contraseña incorrectos.", username kept, password cleared and focused |
| | L3 | empty fields ("El usuario es obligatorio." / "La contraseña es obligatoria.") |
| | L4 | submitting: "Ingresando…" disabled |
| | L5 | "Tu sesión expiró. Ingresá de nuevo." (`/?sesion=expirada`) |
| inventario.html | I1 | with data: header (Inventario · nav Inventario/Órdenes · Usuario: admin · Cerrar sesión), action bar, "4 productos", stock 0 highlighted (B-02), Eliminar |
| | I2 | "Todavía no hay productos" |
| | I3 | "Cargando inventario…" |
| | I4 | network error + "Reintentar" |
| | I5 | persistent success alert (ingreso), closable |
| | I5b | (extra) "Orden OT-0003 creada." + link to Órdenes |
| | I5c | (extra) "Producto B-02 dado de baja." (row removed) |
| | MI1 | Ingreso empty: free-text código with datalist, Nombre "Solo si el código es nuevo." |
| | MI2 | non-blocking hint "Código nuevo o dado de baja: si es nuevo, indicá un nombre." |
| | MI3 | browser validation: "El código es obligatorio." + "La cantidad debe ser un entero entre 1 y 10.000." |
| | MI4 | 422 "El producto 'C-99' no existe: indicá un nombre para crearlo." shown **only** in the modal's top alert; Nombre invalid (`aria-invalid`, `aria-describedby` → alert) and focused |
| | ME1 | Egreso: dropdown "A-01 · Tornillo M8 (stock 7)", "Stock actual" |
| | ME2 | 409 "Stock insuficiente para 'CAJA/10': disponible 4, solicitado 10." |
| | ME3 | 404 "No existe un producto activo con código 'B-02'.", list reloaded without B-02 |
| | MO1 | Nueva orden: 3 lines, date 2026-11-20 (today, editable), counter "3 de 100 componentes"; Agregar/Quitar work |
| | MO2 | per-field/per-line validation (number, empty product, quantity 0) |
| | MO3 | 409 faltantes: alert with `detail` + "Disponible D, solicitado S" on lines 2 and 3 |
| | MO4 | 404 for a product that is no longer active: line 2 marked |
| | MO5 | 422 "Componente 2: …": line 2 marked |
| | MO6 | 409 "Ya existe una orden con número 'OT-0001'." shown **only** in the top alert; Número invalid (`aria-invalid`, `aria-describedby` → alert) and focused |
| | MO7 | submitting: "Creando orden…" disabled |
| | MO7b | 100 lines: "Agregar componente" disabled, "100 de 100 componentes (máximo)" (view scrolled to the end) |
| | MB1 | product deletion confirmation (alertdialog, focus on Cancelar) |
| | MB2 | deletion 404 + "Cerrar" |
| | T1 | static focus ring on the "Ingreso de stock" button |
| | T1b | focus on a field inside the modal |
| | T2 | same as I1 with a light OS (`colorScheme: light`): must render dark |
| ordenes.html | O1 | Desde/Hasta/Número filters + list of orders with components (code, name, quantity), including a deactivated product |
| | O2 | "No hay órdenes en ese período" (with filters). Without filters and no orders the text is just "No hay órdenes" — user decision 2026-11-20, after mockup approval; same layout, only the text changes |
| | O3 | "No existe una orden con número 'OT-9999'." (typed: `ot-9999`) |
| | O4 | browser check "Desde no puede ser posterior a Hasta." (not sent) |
| | O4b | API 422 shown as-is next to the filters |
| | O5 | "Cargando órdenes…" |
| | O6 | network error + "Reintentar" |
| | MD1 | "Devolver stock" **checked** by default → "Borrar y devolver stock" (the checkbox changes the button live) |
| | MD2 | unchecked → "Borrar sin devolver stock" |
| | MD3 | summary with restored stock per product: A-01 +2 (stock 9); C-99 +4 (stock 4, **reactivado**) |
| | MD3b | "Orden OT-0001 borrada sin devolver stock." |
| | MD4 | 404 "No existe una orden con número 'OT-0001'.", list reloaded |
| | T1c | (extra) focus on a filter and on a nav link |
| | T2 | same as O1 with a light OS (`colorScheme: light`): must render dark |
| all | T3 | checked automatically: no horizontal page scroll at 390 px or 1440 px in any state (scrollWidth = clientWidth) |

## Files

- `login.html`, `inventario.html`, `ordenes.html`: one per screen. Their modals are written out in the HTML, one block per state.
- `assets/tailwind-config.js`: maps Tailwind names to `var(--token)`. It is the same as `components.html`, plus `info`. In the app this becomes `static/js/tailwind-config.js`.
- `assets/mockup.css`: section A holds the new UI pieces, which are candidates for `ui.css`: `.navlink`, `.hint`, `.line`, `.modal-form/.modal-foot`, `.check`, `.ord`. Section B is the mockup chrome.
- `assets/mockup.js`: switches states by hash, plus a focus trap, Escape, add/remove lines, password toggle and the "Devolver stock" checkbox. It is mockup-only and uses no `innerHTML`.

## Sources

- `design-system/tokens.css`, `ui.css`, `components.html`, `ordenes.html`, `previews/` (Revision 2: dark-only theme).
- `openspec/changes/paso-5-web-local/design.md` (D1–D9, UI Mockups checklist), `specs/interfaz-web/spec.md`, and the main specs for the exact API messages (`ordenes-trabajo`, `baja-productos`, `consulta-ordenes`).
- The user's decisions of 2026-11-20 (routes, session expired, dropdown "CÓDIGO · Nombre (stock N)", ingreso hint, texts, errors in modals, persistent success, today's date, 1–100 lines, "Devolver stock" checked, /ordenes filters, out of scope).

## Differences from the design system (Revision 2)

All of these use existing tokens only. None changes `tokens.css` or `ui.css`.

1. **Header navigation** (`.navlink`) with Inventario/Órdenes and an amber `aria-current` underline. On mobile it moves to a second row. This is new; the design system only had "← Inventario".
2. **Delete-order checkbox** "Devolver stock" instead of the "¿Reintegrar stock?" radios. The button text describes the result. The modal title is "Borrar orden" (it was "Eliminar orden").
3. **Order list as cards per order** with a components table (code, name, quantity), instead of a single table with "TOR ×8". This is needed to show the name.
4. **Nueva orden** has numbered lines (needed for "Componente N"), a 40 px "Quitar" button (it was `btn-sm`), a counter, and a footer outside the scroll area (`.modal-foot`) so "Crear orden" stays visible with 100 lines.
5. **Info alert/hint** (`--color-info-*`, which already existed in tokens) for "sesión expirada" and "código nuevo".
6. **Closable success alert** (× button).
7. Empty-period text: "No hay órdenes en ese período" (it was "rango").
8. **Mobile only (< 640 px).** From 640 px up, everything looks the same as the design system (Revision 2). These rules live in `mockup.css` (`.tbl-fit`, `.line`, mobile media queries).
   - **Tables fit with no horizontal scroll.** The `min-width` (26rem for inventory, 18rem for components) applies only from 640 px. Cells use tighter padding. The name can break onto a second line.
   - **"Eliminar" touch target.** In tables, "Eliminar" grows to 40 px tall on mobile. It stays `btn-sm` (32 px) on desktop.
   - **Two-row component lines in Nueva orden.** Row 1 holds the number and a full-width product select. Row 2 holds Cantidad and Quitar. Lines are separated by a divider, and errors stay under each line.
   - **Smaller modal margins.** The overlay has 0.5rem around it and the modal has 0.75rem padding.
   - **Smaller product dropdowns.** They use `--text-sm` (14 px) so that "CAJA/10 · Caja de arandelas ×10 (stock 4)" fits whole. At 16 px it gets cut off at 390 px.
     - Trade-off: iOS Safari zooms when a field under 16 px gets focus.
     - Names longer than about 45 characters will still be cut off when the dropdown is closed. The native picker shows them in full.

## Decisions recorded (user, 2026-11-20)

- **API messages in modals appear only in the top alert.** When one field is affected (Nombre in MI4, Número in MO6), that field is marked invalid with `aria-invalid="true"` and `aria-describedby` pointing to the alert's `id`, and it receives focus. The message is not repeated under the field.
  - Browser-validation errors still go under their own field.
  - Per-line marks in Nueva orden still show their own text ("Disponible D, solicitado S", 404 code, "Componente N").
- **Delete summary (MD3) is a list** with one item per product (`A-01 +2 (stock 5)`, `C-99 +4 (stock 5, reactivado)`). The spec and tasks were updated to match.
- **Navigation:** both the "← Inventario" link and the header nav stay. The "Ver órdenes" button also stays.
- **Ingreso hint:** "Código nuevo o dado de baja: si es nuevo, indicá un nombre." The spec was updated to match.
- **Dropdown format:** "A-01 · Tornillo M8 (stock 7)" ("CÓDIGO · Nombre (stock N)"). Design D4 was updated to match.

## TBD / to confirm

- (TBD) **Per-line error text for the 404 in Nueva orden** ("Este producto ya no está activo: elegí otro o quitá la línea.") is not defined in the spec.
- (TBD) **Product deletion 404 (MB2)** replaces the buttons with "Cerrar". This is a mockup decision.
- (TBD) "Stock bajo" threshold: out of scope. Only stock 0 is highlighted (`sin_stock`), as in the design system.
- Product names and stock values are sample data.
