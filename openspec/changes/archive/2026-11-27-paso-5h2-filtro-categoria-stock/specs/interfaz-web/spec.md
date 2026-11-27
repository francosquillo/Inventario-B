## ADDED Requirements

### Requirement: Filtro por categoría en la modificación de stock
Cada línea de "Modificar stock" SHALL tener, antes del producto, un filtro con la etiqueta visible "Filtrar por categoría" ("Todas las categorías" por defecto, cada categoría y "Sin categoría") que limita los productos activos y dados de baja ofrecidos en esa línea. Al cambiarlo, el producto elegido SHALL conservarse si pertenece a la categoría y, si no, la línea SHALL volver a "Elegí un producto…". El filtro de una línea SHALL NOT afectar a las demás.

#### Scenario: Elegir entre todos
- **GIVEN** `A-01` (sin categoría, activo), `AC-10` (`aceite`, activo) y `C-99` (`motor`, dado de baja)
- **WHEN** el usuario abre "Modificar stock" y despliega el producto de la línea 1
- **THEN** el filtro de la línea está en "Todas las categorías" y el selector ofrece `A-01` y `AC-10` en "Activos" y `C-99` en "Dados de baja"

#### Scenario: Filtrar una línea por categoría
- **WHEN** el usuario elige "Aceite" en el filtro de la línea 2
- **THEN** el selector de producto de la línea 2 ofrece solo `AC-10`, sin el grupo "Dados de baja", y el de la línea 1 sigue ofreciendo todos

#### Scenario: Filtrar por una categoría con productos dados de baja
- **WHEN** el usuario elige "Motor" en el filtro de una línea
- **THEN** el selector ofrece solo `C-99` dentro del grupo "Dados de baja", sin el grupo "Activos"

#### Scenario: Filtrar por "Sin categoría"
- **WHEN** el usuario elige "Sin categoría" en el filtro de una línea
- **THEN** el selector ofrece solo los productos sin categoría (`A-01`)

#### Scenario: Cambiar el filtro con un producto elegido
- **GIVEN** la línea 1 con `AC-10` elegido, el filtro en "Todas las categorías" y "Fijar en" con el valor propuesto
- **WHEN** el usuario elige "Aceite" y luego "Filtro" en el filtro de esa línea
- **THEN** con "Aceite" `AC-10` sigue elegido con su valor y su resultado, y con "Filtro" la línea vuelve a "Elegí un producto…" como si el usuario lo hubiera deseleccionado

#### Scenario: Categoría sin productos
- **GIVEN** ningún producto, activo ni dado de baja, de la categoría `helices`
- **WHEN** el usuario elige "Hélices" en el filtro de una línea
- **THEN** el selector de producto de esa línea ofrece solo "Elegí un producto…" y la línea muestra la ayuda "No hay productos en esta categoría.", que desaparece al volver a una categoría con productos

#### Scenario: Línea nueva y reapertura
- **WHEN** el usuario agrega una línea, o cierra y vuelve a abrir el modal
- **THEN** el filtro de cada línea nueva arranca en "Todas las categorías"

### Requirement: Filtro de la modificación separado de la categoría del producto
El filtro de una línea de "Modificar stock" SHALL ser solo de presentación: SHALL NOT cambiar el selector "Categoría" de la línea (que define la categoría del producto al guardar) ni enviarse en `POST /api/stock/modificaciones`. Cada línea SHALL mantener ambos controles con etiquetas distintas.

#### Scenario: Filtrar no cambia la categoría a guardar
- **GIVEN** la línea 1 con `AC-10` elegido y su "Categoría" precargada en "Aceite"
- **WHEN** el usuario cambia el filtro de esa línea a "Todas las categorías" y luego a "Aceite"
- **THEN** la "Categoría" de la línea sigue en "Aceite"

#### Scenario: El cuerpo no incluye el filtro
- **GIVEN** la línea 1 con el filtro en "Aceite", `AC-10` elegido y "Categoría" cambiada a "Filtro"
- **WHEN** el usuario guarda
- **THEN** la petición lleva `"categoria": "filtro"` en esa línea y ningún campo del filtro

#### Scenario: Etiquetas accesibles distintas
- **WHEN** la línea 2 se renderiza
- **THEN** el filtro se anuncia como "Filtrar por categoría, línea 2" y el otro selector como "Categoría de la línea 2"

## MODIFIED Requirements

### Requirement: Selector de productos de la modificación
El selector de producto de cada línea SHALL ofrecer los productos activos (`GET /api/inventario`) y, en un grupo aparte "Dados de baja", los de `GET /api/productos/inactivos`, cada uno como "CÓDIGO · Nombre (stock N)", limitados ambos grupos por el filtro por categoría de la línea; un grupo sin productos no se muestra. Un producto ya elegido en otra línea SHALL quedar deshabilitado en las demás.

#### Scenario: Producto dado de baja
- **GIVEN** el producto dado de baja `C-99` "Junta" con stock 2
- **WHEN** el usuario abre el selector y elige `C-99`
- **THEN** lo encuentra en el grupo "Dados de baja" y la línea avisa según lo que cargue: "Dado de baja: se va a reactivar al guardar." si el stock resultante cambia y queda mayor que 0 (sumar, o fijar en un valor distinto mayor que 0), o "Dado de baja: sigue dado de baja (sin cambio de stock)." / "Dado de baja: sigue dado de baja (stock 0)." si no

#### Scenario: Aviso de un dado de baja según el stock cargado
- **GIVEN** la línea 2 tiene el producto dado de baja `C-99` con stock 2 en modo "Fijar en"
- **WHEN** el usuario deja el valor en 2, lo cambia a 0 o lo cambia a 6
- **THEN** con 2 y con 0 la línea avisa que sigue dado de baja y con 6 avisa "Dado de baja: se va a reactivar al guardar."

#### Scenario: Producto ya elegido
- **GIVEN** la línea 1 tiene `A-01`
- **WHEN** el usuario abre el selector de la línea 2
- **THEN** `A-01` aparece deshabilitado

#### Scenario: Producto ya elegido dentro de un filtro
- **GIVEN** la línea 1 tiene `AC-10` y la línea 2 tiene el filtro en "Aceite"
- **WHEN** el usuario abre el selector de la línea 2
- **THEN** `AC-10` aparece deshabilitado con "— ya está en otra línea"
