# Mockups — paso-5i-modificar-ordenes-checkeo (C-06i)

Solo se mockean las pantallas y estados que cambian (preferencia del usuario: mockups mínimos). Reutilizan los assets aprobados de C-06h (`assets/mockup*.css`, `tailwind-config.js`, `mockup.js` = selector de estados con `?captura` y `?largo`). Las piezas nuevas están en `assets/mockup-5i.css`. Los tokens vienen de `design-system/` (Revision 2, tema oscuro único) y no se tocan. Sin `brand.js`: la cabecera es el texto "Inventario".

Datos de ejemplo coherentes con las specs: `OT-0043` tenía `ACE-01` x 2 ($ 12.000) y `FIL-01` x 1 (producto ya dado de baja). Se edita a `ACE-01` x 3 ($ 18.000), se quita `FIL-01` (se devuelve su stock y se reactiva) y se marca el chequeo "Combustible" $ 8.000 y "Entrega" sin precio. Totales: Subtotal servicios $ 68.000,00 (45.000 + 15.000 + 8.000 del chequeo), Subtotal ítems $ 18.000,00 y Total $ 86.000,00.

| ID | Archivo | Estado |
|----|---------|--------|
| L1 | `ordenes.html#L1` | `/ordenes` después de guardar: aviso "Orden OT-0043 actualizada." con los ajustes de stock (`ACE-01` −1 descontada, `FIL-01` +1 devuelta y reactivada), botón "Editar" en cada orden, fila "Chequeo final:" con precios y `OT-0041` sin chequeo (no muestra la fila) |
| E1 | `ordenes.html#E1` | Modal "Editar orden OT-0043" precargado. Muestra: número fijo, servicio "Servicio 20 hs (actual)" (conserva lo guardado en la orden), ayuda "Hasta 5: 3 en stock + 2 ya descontados por esta orden.", `FIL-01` "(dado de baja)" en su línea, fieldset "Chequeo final" (6 casillas, la tercera "Check-list y verificación final"; el importe solo se habilita si la casilla está marcada), resumen con el chequeo sumado y botón "Guardar cambios" |
| E2 | `ordenes.html#E2` | El mismo modal después de un 409: alerta general con el detalle y error bajo la cantidad ("Disponible 3, solicitado 4", `aria-invalid`). El modal sigue abierto y no se modificó nada |
| P1 | `ordenes.html#P1` | Hoja impresa (Exportar PDF): igual que la de C-06h más la sección "Chequeo final" antes del resumen, con **los seis ítems** (pedido del usuario, 2026-11-27). Los hechos llevan `[✓]`, "Hecho" y su precio; los no hechos llevan `[ ]` y "No se hizo", sin precio. Se distinguen por símbolo y texto, no solo por color, así que se lee igual impreso en blanco y negro. El resumen ya incluye el chequeo y "Editar" no se imprime |

**Omitidos a propósito** (no cambian, o usan estilos ya aprobados):
- "Nueva orden": no cambia visualmente. El chequeo solo se carga al editar (Q8 de `design.md`). Si el usuario pide chequeo también al crear, se agrega un estado N2.
- Errores de validación de importes, cliente o fechas en el modal de edición: usan los mismos estilos `.err`, `aria-invalid` y `.line-err` aprobados en C-06h, con los mismos textos.
- Orden borrada mientras se editaba (404), errores de red y estado de carga: usan la alerta estándar del modal y los estados existentes de `/ordenes`.
- Edición sin ajustes ("Sin cambios de stock."): es el mismo aviso de L1 con otro texto.
- Modal de borrado y modal "Servicios generales": sin cambios.
- PDF de una orden sin ningún chequeo hecho: es P1 con los seis ítems como "No se hizo" (Q11 de `design.md`).
- En `/ordenes` (pantalla) siguen apareciendo solo los ítems hechos (L1); el pedido de mostrar los no hechos es solo para el PDF.

## Cómo verlos

Desde la raíz del repo: `.venv/Scripts/python -m http.server 8771 --bind 127.0.0.1` y abrir `http://127.0.0.1:8771/openspec/changes/paso-5i-modificar-ordenes-checkeo/mockups/ordenes.html#L1`. La barra de arriba cambia de estado; `?captura` la oculta y `?largo` muestra el modal entero. Detener el servidor al terminar.

Capturas en `previews/ordenes-<ID>-{mobile,desktop}.png` (390x844 y 1440x900, página completa; E1 y E2 con `?captura&largo`).

Approval: approved (2026-11-27, by user; amended: 6th item "Check-list y verificación final" added after approval as requested by the user)
Preview: rendered (2026-11-27, tras sumar el 6.º ítem; 390x844 y 1440x900)
