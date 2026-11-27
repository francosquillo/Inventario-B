# Mockups — paso-5h-precios-datos-orden (C-06h)

Solo las pantallas que cambian (pedido del usuario: "solo los mockups necesarios"). Reutilizan los assets aprobados de C-06g (`assets/mockup*.css`, `tailwind-config.js`, `mockup.js` = selector de estados, ahora con `?largo`) más `assets/mockup-5h.css` (piezas nuevas), con tokens de `design-system/` (Revision 2, tema oscuro único). Sin `brand.js`: el proyecto no tiene marca (cabecera de texto "Inventario").

Datos de ejemplo coherentes con las specs: `OT-0043` (fecha 2026-11-27, ingreso 2026-11-26, egreso 2026-11-29), servicio "Servicio 20 hs" $ 45.000, servicios adicionales "Limpieza" $ 15.000 y "Pulido" sin precio, ítems `ACE-01` x2 $ 12.000 y `FIL-01` sin precio → Subtotal servicios $ 60.000,00, Subtotal ítems $ 12.000,00, Total $ 72.000,00 (vacío = 0).

| ID | Archivo | Estado |
|----|---------|--------|
| N1 | `nueva-orden.html#N1` | "Nueva orden" (modal 44rem): número + "Fecha" **sin cambios** (modificado por el usuario, 2026-11-27); "Cliente y embarcación" (todos opcionales, sin marcas de obligatorio) con "Fecha de ingreso" y "Fecha de egreso"; servicio general con su precio; componentes con "Importe" (uno vacío); "Servicios adicionales" (antes "Procesos") con **un importe por línea** (Pulido vacío); resumen en vivo con subtotales y total |
| L1 | `ordenes.html#L1` | `/ordenes`: `OT-0043` con la fecha en la cabecera como hoy, fila de datos del cliente con "Ingreso:"/"Egreso:", servicio con precio, servicios adicionales con su precio cada uno, columna "Importe" y resumen al pie; `OT-0041` anterior a los precios (sin fila de datos, "—", resumen en $ 0,00) |
| P1 | `ordenes.html#P1` | Hoja impresa de `OT-0043`: encabezado "Fecha: … · 2 componentes" sin cambios, datos (con ingreso y egreso) en dos columnas, "Servicio general" con precio, tabla con "Importe", "Servicios adicionales" con precio y resumen al final (lo vacío no se imprime) |

**Omitidos a propósito** (no cambian el layout o usan estilos ya aprobados):
- Errores de validación (importe inválido, celular, egreso anterior, servicio adicional repetido): estilos `.err` + `aria-invalid` + `.line-err` ya aprobados, con los textos de la spec.
- "Sin servicio general": la caja de precio del servicio aparece deshabilitada y vacía (mismo control de N1).
- "Nueva orden" vacía: N1 con cajas vacías y resumen en $ 0,00.
- Catálogos caídos, borrado de orden, modal "Servicios generales": sin cambios respecto de C-06f/C-06g.

## Cómo verlos

Desde la raíz del repo: `.venv/Scripts/python -m http.server 8766 --bind 127.0.0.1` y abrir `http://127.0.0.1:8766/openspec/changes/paso-5h-precios-datos-orden/mockups/nueva-orden.html#N1` (la barra de arriba cambia de estado; `?captura` la oculta; `?largo` muestra el modal entero sin overlay). Detener el servidor al terminar.

Capturas en `previews/<pantalla>-<ID>-{mobile,desktop}.png` (390x844 y 1440x900, página completa; las de N1 con `?captura&largo` para ver el modal entero).

Approval: approved (2026-11-27, by user)
