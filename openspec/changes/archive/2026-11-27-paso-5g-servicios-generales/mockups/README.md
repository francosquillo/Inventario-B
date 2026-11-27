# Mockups — paso-5g-servicios-generales (C-06g)

Solo las pantallas que cambian (pedido del usuario: "solo los mockups necesarios"). Reutilizan los assets aprobados de C-06f (`assets/mockup*.css`, `tailwind-config.js`; `mockup.js` = selector de estados) más `assets/mockup-5g.css` (piezas nuevas), con tokens de `design-system/` (Revision 2, tema oscuro único). Sin `brand.js`: el proyecto no tiene marca (cabecera de texto "Inventario", decisión del usuario).

| ID | Archivo | Estado |
|----|---------|--------|
| S1 | `nueva-orden.html#S1` | "Nueva orden": bloque "Servicio general" entre la fecha y Componentes con "Servicio 20 hs" elegido y su lista "Incluye:" (solo lectura). Por defecto el selector dice "Sin servicio general" y la lista no se ve |
| L2 | `ordenes.html#L2` | `/ordenes`: botón "Servicios generales" junto al título; `OT-0043` con fila "Servicio general:" (nombre + chips) antes de "Procesos:"; `OT-0042` solo con procesos; `OT-0041` sin filas |
| C1 | `ordenes.html#C1` | Modal "Servicios generales", vista lista: tarjeta por servicio con chequeos, "Editar"/"Eliminar", "Nuevo servicio" y aviso de éxito |
| C2 | `ordenes.html#C2` | Mismo modal, vista formulario ("Editar servicio general"): Nombre, líneas numeradas de chequeos con "Quitar", "Agregar chequeo" con contador, "Volver"/"Guardar" |

**Omitidos a propósito** (no cambian el layout aprobado):
- Hoja impresa (PDF): el bloque "Servicio general" usa el mismo estilo que "Procesos realizados" del P1 aprobado en C-06f (título chico + lista uno por línea), ubicado primero: tras el encabezado y antes de la tabla de componentes (cambio del usuario, 2026-11-27); luego la tabla y "Procesos realizados". Se verifica en el verify contra la spec.
- Confirmación de borrado del servicio: mismo patrón que el modal "Borrar orden" ya aprobado (texto + "Cancelar" / botón `btn-danger`).
- "Nuevo servicio": es C2 vacío con otro título.
- Errores (catálogo caído, 422, validación por línea): usan los estilos de error ya aprobados (`.err`, `aria-invalid`), con los textos de la spec.

## Cómo verlos

Desde la raíz del repo: `.venv/Scripts/python -m http.server 8765 --bind 127.0.0.1` y abrir `http://127.0.0.1:8765/openspec/changes/paso-5g-servicios-generales/mockups/ordenes.html#L2` (la barra de arriba cambia de estado; `?captura` la oculta). Detener el servidor al terminar.

Capturas en `previews/<pantalla>-<ID>-{mobile,desktop}.png` (390x844 y 1440x900; `ordenes-L2-mobile.png` es de página completa).

Approval: approved (2026-11-27, by user)
