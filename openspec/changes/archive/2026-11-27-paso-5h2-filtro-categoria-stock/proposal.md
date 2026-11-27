# Proposal — paso-5h2-filtro-categoria-stock (C-06h2)

## Why

En el modal **"Modificar stock"** el selector de producto de cada línea lista **todos** los productos (activos y dados de baja), en orden de código. Con un catálogo que crece, encontrar un producto cuesta; en "Nueva orden" ya se resolvió con un filtro por categoría por línea (C-06e). El usuario pidió lo mismo para "Modificar stock" (2026-11-27), después de C-06h (decisión explícita: primero los precios) y antes de C-06i.

Governance **BAJO**: solo presentación en el navegador. Sin cambios de esquema, de API ni de datos; el filtro no viaja en el cuerpo de `POST /api/stock/modificaciones`. Con componente visual (mockup gate `system-and-mockups`, design system Revision 2).

## What Changes

- **Filtro por categoría en cada línea de "Modificar stock"**, ubicado **antes del producto** (misma lectura que "Nueva orden": primero se acota, después se elige), con etiqueta visible **"Filtrar por categoría"** y opciones **"Todas las categorías"** (por defecto), cada categoría del catálogo (orden alfabético por nombre) y **"Sin categoría"**.
- El filtro acota **los dos grupos** del selector de producto: "Activos" y "Dados de baja"; un grupo que queda vacío no se muestra. Se mantienen la etiqueta "CÓDIGO · Nombre (stock N)" y la regla de "ya está en otra línea" (deshabilitado).
- Al cambiar el filtro, el producto elegido **se conserva si pertenece** a la categoría filtrada y, si no, la línea **vuelve a "Elegí un producto…"** (y se limpian el valor propuesto, el resultado y el aviso de esa línea, como al deseleccionar).
- Si el filtro deja la lista vacía, el producto ofrece solo "Elegí un producto…" y la línea muestra la ayuda **"No hay productos en esta categoría."** (asociada al selector con `aria-describedby`).
- El filtro de una línea **no afecta** a las demás; cada línea nueva arranca en "Todas las categorías"; abrir el modal de nuevo resetea todo.
- **No se confunde** con el selector "Categoría" que ya tiene la línea (cambia la categoría del producto al guardar): conserva su etiqueta y ubicación, y el filtro nunca lo modifica ni se envía a la API.
- **Reutiliza** `Busqueda.porCategoria`, `Busqueda.productoSigueVisible` y `llenarSelectCategoria` (sin duplicar lógica de filtrado).
- **Fuera de alcance**: buscador de texto en el selector, filtro en el modal "Nuevo ingreso", cambios en la API o el esquema, recordar el filtro entre aperturas.
- Al archivar: actualizar KB 06 (US-005) y 07 (flujo de modificar stock).

## Capabilities

### New Capabilities
<!-- ninguna -->

### Modified Capabilities
- `interfaz-web`: se agregan los requisitos "Filtro por categoría en la modificación de stock" y "Filtro de la modificación separado de la categoría del producto", y se ajusta "Selector de productos de la modificación" para que el filtro acote ambos grupos.

## Impact

- `static/index.html`: plantilla `tpl-mline` (filtro con su etiqueta antes del producto; etiqueta visible "Producto") y modal "Modificar stock" de 40rem a 44rem (el ancho de "Nueva orden") para que filtro y producto se lean completos.
- `static/js/inventario.js`: `llenarSelectMod` (filtra activos y dados de baja con `Busqueda.porCategoria`, conserva/resetea con `Busqueda.productoSigueVisible`), `nuevaLineaMod`, `renumerarMod` (ids, `for`, `aria-label` del filtro), `alCambiarLineaMod` (cambio de filtro), `llenarSelectoresCategoria` (recarga del catálogo), ayuda de lista vacía.
- `static/css/app.css`: grilla de `.mline-head` con la columna del filtro (390 px sin scroll horizontal).
- Tests: guardas estáticas nuevas (`tests/test_frontend_filtro_modificar.py`) y casos Node de `Busqueda` con productos dados de baja (`tests/test_busqueda_js.py`).
- Sin dependencias nuevas; sin cambios en `domain/`, `services/`, `repositories/` ni en la API.
