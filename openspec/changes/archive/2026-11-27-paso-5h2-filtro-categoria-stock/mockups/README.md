# Mockups — paso-5h2-filtro-categoria-stock (C-06h2)

Solo el modal que cambia: **"Modificar stock"** (pedido del usuario: mockups mínimos). Reutilizan los assets aprobados de C-06h (`assets/mockup.css`, `tailwind-config.js`, `mockup.js` = selector de estados con `?captura` y `?largo`) más `assets/mockup-5h2.css` (cabecera de la línea con el filtro), con tokens de `design-system/` (Revision 2, tema oscuro único). Sin `brand.js`: el proyecto no tiene marca. La base es el modal real de `static/index.html` y el M1 aprobado de C-06e.

Datos de ejemplo: categorías Aceite, Filtro, Hélices (sin productos) y Motor; activos `A-01`, `ACE-01`, `ACE-02`, `FIL-01`, `FIL-02`, `MOT-01`, `MOT-02`; dados de baja `C-99` (Motor) y `D-05` (sin categoría).

| ID | Archivo | Estado |
|----|---------|--------|
| S1 | `modificar-stock.html#S1` | Cada línea con **"Filtrar por categoría"** (etiqueta visible) antes de **"Producto"**, en "Todas las categorías". Línea 1: `FIL-01` elegido, "Fijar en" 9, Categoría "Filtro" precargada (abajo, sin cambios). Línea 2 recién agregada, vacía. Modal de 44rem (antes 40rem) |
| S2 | `modificar-stock.html#S2` | Línea 2 filtrada por "Motor": el producto (desplegado como ilustración con `size`; el nativo no se captura abierto) ofrece `MOT-01`, `MOT-02` en "Activos" y `C-99` en "Dados de baja". La línea 1 no cambia |
| S3 | `modificar-stock.html#S3` | Línea 2 filtrada por "Hélices" (sin productos): producto solo "Elegí un producto…" y la ayuda "No hay productos en esta categoría." |

**Omitidos a propósito** (no agregan un estado visual nuevo):
- Reseteo al cambiar el filtro con un producto que no pertenece: la línea queda igual que la línea 2 de S1 ("Elegí un producto…", valor vacío, Categoría "Sin categoría").
- Filtro "Sin categoría" o "Aceite": mismo control que S2 con otra lista.
- Grupo vacío oculto (p. ej. "Aceite" sin dados de baja): S2 ya muestra el patrón de grupos; un grupo menos no cambia el layout.
- Producto deshabilitado "— ya está en otra línea" dentro del filtro, errores de la línea (`.err`/`aria-invalid`) y resumen tras guardar: estilos ya aprobados en C-06/C-06e, sin cambios.
- Pantalla de inventario, "Nuevo ingreso" y "Nueva orden": no cambian.

## Cómo verlos

Desde la raíz del repo: `.venv/Scripts/python -m http.server 8767 --bind 127.0.0.1` y abrir `http://127.0.0.1:8767/openspec/changes/paso-5h2-filtro-categoria-stock/mockups/modificar-stock.html#S1` (la barra de arriba cambia de estado; `?captura` la oculta; `?largo` muestra el modal entero sin overlay). Detener el servidor al terminar.

Capturas en `previews/modificar-stock-<ID>-{mobile,desktop}.png` (390x844 y 1440x900, página completa con `?captura&largo`).

Approval: approved (2026-11-27, by user)
