# Design system — Inventario-B

Mode: system-and-mockups
Revision: 1
Approval: approved (2026-11-19, by user)
Fecha: 2026-11-19

Sin logo ni marca por decisión del usuario (2026-11-19). La cabecera muestra solo el título de texto "Inventario".

## Propósito
Fundación visual mínima para la UI web (Paso 5: FastAPI + HTML estático + Tailwind CDN + JS vanilla con `fetch` a la API JSON). Dirección elegida por el usuario: **Industrial sobrio** (grafito/pizarra, acento ámbar, tablas densas, códigos y números en monoespaciada). Tema claro principal; oscuro vía `prefers-color-scheme`.

## Fuentes
- Elección del usuario: "Industrial sobrio"; sin logo ni marca.
- `knowledge-base/README.md` y `knowledge-base/06_funcionalidades.md`.

## Layout acordado (2026-11-19)
- Inventario primero: tras la topbar, barra de acciones (Ingreso de stock, Egreso de stock, Nueva orden, Ver órdenes) y tabla de inventario.
- Ingreso, egreso, nueva orden y borrados (producto y orden) son modales flotantes con fondo atenuado; se cierran con Cancelar, X o Escape.
- Órdenes en pantalla aparte: `ordenes.html` (página estática `static/ordenes.html`, ruta `/ordenes` servida por FastAPI/`StaticFiles`; `tokens.css` y `ui.css` viven en `static/css/`), con enlace "← Inventario" de vuelta.

## Archivos
- `tokens.css` — variables CSS (color, tipografía, espaciado, radios, sombras, foco, movimiento, oscuro, reduced-motion).
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
Ver `components.html` para la config completa. Los valores son hex en variables: los modificadores de opacidad (`bg-accent/50`) no funcionan; usar los tokens `*-subtle`. El modo oscuro cambia solo.

## Colores clave (claro)
Fondo `#eef0f2`, superficie `#ffffff`, texto `#1c2127`, texto suave `#4a5460`, borde `#c3c9d0`, acento `#f59e0b` (texto sobre acento `#1c1400`, hover `#d98a06`), texto de acento `#8a4a05`, éxito `#15803d`, peligro `#b91c1c`.

## Accesibilidad
Foco visible, objetivos >= 40px, reduced-motion anula duraciones, tablas con scroll horizontal interno.
