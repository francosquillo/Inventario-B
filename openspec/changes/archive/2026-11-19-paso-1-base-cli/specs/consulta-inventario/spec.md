# Spec Delta

## Purpose

Permite a un usuario autenticado conocer el stock disponible: lista los productos activos con su código, nombre y stock, incluyendo los que no tienen unidades.

## ADDED Requirements

### Requirement: Listado de productos activos
El inventario general SHALL listar únicamente los productos activos, mostrando para cada uno código, nombre y stock, ordenados por código de forma ascendente.

#### Scenario: Solo activos
- **GIVEN** los productos `P-001` (activo), `P-002` (inactivo) y `P-003` (activo)
- **WHEN** se consulta el inventario
- **THEN** el listado contiene `P-001` y `P-003` y no contiene `P-002`

#### Scenario: Orden por código
- **GIVEN** los productos activos `B-10`, `A-01` y `C-05`
- **WHEN** se consulta el inventario
- **THEN** el listado aparece en el orden `A-01`, `B-10`, `C-05`

### Requirement: Productos con stock cero visibles
Un producto activo con stock 0 SHALL aparecer en el inventario y SHALL distinguirse como sin stock.

#### Scenario: Producto sin unidades
- **GIVEN** un producto activo `P-001` con stock 0
- **WHEN** se consulta el inventario
- **THEN** `P-001` aparece en el listado con stock 0 marcado como sin stock

#### Scenario: Producto con unidades no se marca
- **GIVEN** un producto activo `P-002` con stock 5
- **WHEN** se consulta el inventario
- **THEN** `P-002` aparece con stock 5 sin marca de sin stock

### Requirement: Inventario vacío
Si no hay productos activos, el sistema SHALL devolver un listado vacío explícito (no un error), para que la interfaz que lo presente muestre el estado de inventario vacío.

#### Scenario: Sin productos
- **GIVEN** una base recién inicializada sin productos
- **WHEN** se consulta el inventario
- **THEN** el resultado es un listado vacío, sin error

#### Scenario: Solo productos inactivos
- **GIVEN** una base donde todos los productos están inactivos
- **WHEN** se consulta el inventario
- **THEN** el resultado es un listado vacío, sin error
