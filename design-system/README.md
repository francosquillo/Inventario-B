# Design system — Inventario-B

Mode: system-and-mockups
Revision: 2
Approval: approved (2026-11-20, by user)
Fecha: 2026-11-20

Sin logo ni marca por decisión del usuario (2026-11-19). La cabecera muestra solo el título de texto "Inventario".

## Propósito
Fundación visual mínima para la UI web (Paso 5: FastAPI + HTML estático + Tailwind CDN + JS vanilla con `fetch` a la API JSON). Dirección elegida por el usuario: **Industrial sobrio** (grafito/pizarra, acento ámbar, tablas densas, códigos y números en monoespaciada). Tema oscuro único (decisión del usuario 2026-11-20): no hay tema claro ni selector de tema, y no se sigue `prefers-color-scheme`; `:root` declara `color-scheme: dark` para que los controles nativos (fecha, select, casillas, scrollbars, autofill) también sean oscuros.

## Fuentes
- Elección del usuario: "Industrial sobrio"; sin logo ni marca.
- `knowledge-base/README.md` y `knowledge-base/06_funcionalidades.md`.

## Layout acordado (2026-11-19)
- Inventario primero: tras la topbar, barra de acciones (Ingreso de stock, Egreso de stock, Nueva orden, Ver órdenes) y tabla de inventario.
- Ingreso, egreso, nueva orden y borrados (producto y orden) son modales flotantes con fondo atenuado; se cierran con Cancelar, X o Escape.
- Órdenes en pantalla aparte: `ordenes.html` (página estática `static/ordenes.html`, ruta `/ordenes` servida por FastAPI/`StaticFiles`; `tokens.css` y `ui.css` viven en `static/css/`), con enlace "← Inventario" de vuelta.

## Archivos
- `tokens.css` — variables CSS (paleta oscura única, tipografía, espaciado, radios, sombras, foco, movimiento, reduced-motion).
- `components.html` — pantalla de inventario con modales funcionales, más "Referencia de componentes" (botones, campos, alertas, login).
- `ordenes.html` — pantalla de órdenes: filtro Desde/Hasta, tabla, estado vacío, confirmar borrado con "¿Reintegrar stock?".
- `ui.css` / `ui.js` — estilos de componentes y JS mínimo de modales, compartidos por ambas pantallas.
- `previews/` — capturas 390x844 y 1440x900.

## Decisiones abiertas (TBD)
- (TBD) Umbral de "stock bajo": el diseño solo marca stock 0.

## Cambiar valores visuales
Editar solo `tokens.css`. Al cambiar un token, subir `Revision`, rerenderizar mockups afectados y pedir nueva aprobación.

## Uso con Tailwind CDN
```html
<link rel="stylesheet" href="tokens.css">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = { theme: { extend: {
    colors: {
      surface: 'var(--color-surface)', ink: 'var(--color-text)', muted: 'var(--color-text-muted)',
      accent: { DEFAULT: 'var(--color-accent)', contrast: 'var(--color-accent-contrast)' },
      danger: { DEFAULT: 'var(--color-danger)', subtle: 'var(--color-danger-subtle)', fg: 'var(--color-danger-fg)' }
    },
    fontFamily: { sans: 'var(--font-sans)', mono: 'var(--font-mono)' }
  }}};
</script>
```
Ver `components.html` para la config completa. Los valores son hex en variables: los modificadores de opacidad (`bg-accent/50`) no funcionan; usar los tokens `*-subtle`. El tema es siempre oscuro: no usar variantes `dark:` de Tailwind.

## Colores clave (tema oscuro único)
Fondo `#121518`, superficie `#1b1f24`, superficie 2 `#252a31`, borde decorativo `#3a424c`, borde de controles `#66707d`, texto `#e8ebee`, texto suave `#a4aeb9`, acento `#fbbf24` (texto sobre acento `#1c1400`, hover `#fcd34d`), texto de acento `#fbbf24`, éxito `#16a34a`, peligro `#dc2626`, foco `#93c5fd`.

- `--color-border` (decorativo): divisores de filas, cabeceras y tarjetas; no necesita 3:1.
- `--color-border-strong` (nuevo en Rev 2): borde de `.field`, `.btn-secondary` y `.modal`; >= 3:1 sobre `surface`, `bg` y el fondo atenuado.

## Diferencias aprobadas en los mockups de paso-5-web-local (2026-11-20)
- Modal de borrar orden: casilla "Devolver stock", marcada por defecto; el botón de confirmar dice "Borrar y devolver stock" o "Borrar sin devolver stock".
- `/ordenes`: filtro por Número además de las fechas `desde`/`hasta`.
- Estado vacío de `/ordenes`: "No hay órdenes en ese período" con filtros aplicados; "No hay órdenes" sin filtros.

## Accesibilidad
Foco visible, objetivos >= 40px, reduced-motion anula duraciones, tablas con scroll horizontal interno. Contraste WCAG AA verificado numéricamente (Rev 2, tabla abajo). Placeholder con `--color-text-muted` (`.field::placeholder`, opacidad 1).

## Changelog
- **Rev 2 (2026-11-20)**: tema oscuro único por decisión del usuario; `color-scheme: dark`; contraste AA verificado. Se quitaron los valores claros y el `@media (prefers-color-scheme: dark)` (la paleta oscura pasa a `:root`). Nuevo token `--color-border-strong: #66707d` porque `--color-border` (#3a424c) daba 1.63:1 sobre la superficie, insuficiente para el borde de campos y botones. `ui.css`: `.field`, `.btn-secondary` y `.modal` usan `--color-border-strong`; nuevos `.field::placeholder` y `.field:disabled`. `components.html`: alertas info y aviso, select, placeholder y campo deshabilitado. Las capturas de `previews/` son de la Rev 1 y se re-renderizan.
- **Rev 1 (2026-11-19)**: "Industrial sobrio", tema claro principal y oscuro vía `prefers-color-scheme`. Aprobada por el usuario.

### Contraste Rev 2 (WCAG 2.x, AA)
| Par (texto/elemento sobre fondo) | Colores | Ratio | Mínimo | Resultado |
|---|---|---|---|---|
| Texto sobre fondo / superficie / superficie 2 | `#e8ebee` / `#121518`, `#1b1f24`, `#252a31` | 15.31 / 13.84 / 12.07 | 4.5 | Pasa |
| Texto suave sobre fondo / superficie / superficie 2 (cabecera de tabla, fila con hover, campo deshabilitado) | `#a4aeb9` | 8.14 / 7.36 / 6.42 | 4.5 | Pasa |
| Placeholder sobre campo | `#a4aeb9` / `#1b1f24` | 7.36 | 4.5 | Pasa |
| Enlace (texto de acento) sobre superficie / fondo / superficie 2 | `#fbbf24` | 9.92 / 10.98 / 8.65 | 4.5 | Pasa |
| Botón primario: texto sobre ámbar / ámbar hover | `#1c1400` / `#fbbf24`, `#fcd34d` | 10.94 / 12.67 | 4.5 | Pasa |
| Botón peligro: texto blanco sobre rojo | `#ffffff` / `#dc2626` | 4.83 | 4.5 | Pasa |
| Alerta error: texto / borde sobre fondo sutil | `#fca5a5`, `#dc2626` / `#3a1618` | 8.46 / 3.32 | 4.5 / 3 | Pasa |
| Alerta éxito: texto / borde sobre fondo sutil | `#86efac`, `#16a34a` / `#12301d` | 10.20 / 4.35 | 4.5 / 3 | Pasa |
| Alerta aviso y badge `sin_stock`: texto sobre fondo sutil | `#fcd34d` / `#3a2a0a` | 9.61 | 4.5 | Pasa |
| Alerta info / pista: texto sobre fondo sutil | `#93c5fd` / `#14264a` | 8.28 | 4.5 | Pasa |
| Texto de error de campo sobre superficie | `#fca5a5` / `#1b1f24` | 8.73 | 4.5 | Pasa |
| Borde de campo inválido sobre superficie | `#dc2626` / `#1b1f24` | 3.43 | 3 | Pasa |
| Borde de controles sobre superficie / fondo | `#66707d` / `#1b1f24`, `#121518` | 3.30 / 3.65 | 3 | Pasa (Rev 1: `#3a424c`, 1.63, fallaba) |
| Anillo de foco sobre superficie / fondo / superficie 2 | `#93c5fd` | 9.18 / 10.16 / 8.01 | 3 | Pasa |
| Borde del modal sobre fondo atenuado (negro 70 % sobre `#121518` = `#050607`) | `#66707d` | 4.04 | 3 | Pasa |
| Superficie del modal sobre fondo atenuado | `#1b1f24` / `#050607` | 1.22 | — | Informativo: el borde da el límite |
| Rayado/hover de tabla (superficie 2 sobre superficie) | `#252a31` / `#1b1f24` | 1.15 | — | Informativo (decorativo) |
| Botón deshabilitado (opacidad 0.5) | `#1c1a12` / `#8b6f24` | 3.65 | — | Exento (WCAG 1.4.3) |
