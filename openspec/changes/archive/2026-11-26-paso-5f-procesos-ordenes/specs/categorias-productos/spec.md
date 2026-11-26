# Spec Delta

## MODIFIED Requirements

### Requirement: Catálogo de categorías
El sistema SHALL mantener un catálogo de categorías de producto, cada una con una clave única (identificador estable: minúsculas, sin tildes, números y guiones, hasta 30 caracteres) y un nombre para mostrar único sin distinguir mayúsculas. Al crearse el catálogo SHALL contener las categorías de ejemplo `motor` ("Motor"), `aceite` ("Aceite") y `filtro` ("Filtro"). Las categorías SHALL administrarse (crear, renombrar y borrar) solo por la API (sin pantalla en la web).

#### Scenario: Categorías de ejemplo
- **GIVEN** una base recién inicializada
- **WHEN** se consulta el catálogo de categorías
- **THEN** contiene exactamente `aceite` "Aceite", `filtro` "Filtro" y `motor` "Motor"

#### Scenario: Orden del listado
- **WHEN** se consulta el catálogo de categorías
- **THEN** las categorías aparecen ordenadas por nombre: "Aceite", "Filtro", "Motor"

## ADDED Requirements

### Requirement: Borrar categoría
Borrar una categoría (clave normalizada con recorte + minúsculas) SHALL quitarla del catálogo solo si ningún producto, activo o dado de baja, la tiene asignada; si alguno la usa SHALL rechazarse con "La categoría 'x' está asignada a N producto(s)." sin cambios. Una clave inexistente SHALL rechazarse. Una categoría borrada SHALL NOT volver a aparecer al reiniciar.

#### Scenario: Borrar una categoría sin productos
- **GIVEN** la categoría `motor` sin productos asignados
- **WHEN** se borra `MOTOR`
- **THEN** el catálogo ya no incluye `motor`

#### Scenario: Categoría en uso
- **GIVEN** la categoría `filtro` asignada a `F-01` (activo) y a `F-09` (dado de baja)
- **WHEN** se borra `filtro`
- **THEN** se rechaza con "La categoría 'filtro' está asignada a 2 producto(s)." y `F-01` y `F-09` conservan la categoría `filtro`

#### Scenario: Categoría inexistente
- **WHEN** se borra `frenos`, que no existe
- **THEN** se rechaza con "No existe una categoría con clave 'frenos'."

#### Scenario: Catálogo vaciado no se resiembra
- **GIVEN** que se borraron `motor`, `aceite` y `filtro` y el catálogo quedó vacío
- **WHEN** el sistema se reinicia
- **THEN** el catálogo de categorías sigue vacío
