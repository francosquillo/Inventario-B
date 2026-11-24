## MODIFIED Requirements

### Requirement: Listado de productos activos
El inventario general SHALL listar únicamente los productos activos, mostrando para cada uno código, nombre, stock y categoría (o ninguna), ordenados por código de forma ascendente. La categoría SHALL NOT alterar el orden ni el criterio de inclusión.

#### Scenario: Solo activos
- **GIVEN** los productos `P-001` (activo), `P-002` (inactivo) y `P-003` (activo)
- **WHEN** se consulta el inventario
- **THEN** el listado contiene `P-001` y `P-003` y no contiene `P-002`

#### Scenario: Orden por código
- **GIVEN** los productos activos `B-10`, `A-01` y `C-05`
- **WHEN** se consulta el inventario
- **THEN** el listado aparece en el orden `A-01`, `B-10`, `C-05`

#### Scenario: Categoría de cada producto
- **GIVEN** los productos activos `A-01` (sin categoría) y `F-01` (categoría `filtro`)
- **WHEN** se consulta el inventario
- **THEN** `A-01` aparece sin categoría y `F-01` con categoría `filtro`, en ese orden
