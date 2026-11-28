## ADDED Requirements

### Requirement: Botón Editar en cada orden
En `/ordenes`, cada orden SHALL tener un botón "Editar" (con nombre accesible "Editar orden OT-XXXX") junto a "Exportar PDF" y "Eliminar", que abre el modal "Editar orden". El botón SHALL NOT imprimirse en el PDF.

#### Scenario: Abrir la edición
- **GIVEN** un usuario con sesión en `/ordenes` con la orden `OT-0043`
- **WHEN** pulsa "Editar" en `OT-0043`
- **THEN** se abre el modal "Editar orden OT-0043" con el foco en el primer campo editable

### Requirement: Modal de edición de orden
El modal "Editar orden" SHALL mostrar el mismo formulario que "Nueva orden" (fecha, "Cliente y embarcación", servicio general con precio, componentes con importe, servicios adicionales con precio y resumen en vivo), precargado con el contenido vigente de la orden, con el número visible en el título y no editable, más el fieldset "Chequeo final". El botón principal SHALL decir "Guardar cambios". Al cancelar o cerrar, SHALL NOT enviarse nada.

#### Scenario: Formulario precargado
- **GIVEN** la orden `OT-0043` con fecha `2026-11-27`, cliente "Juan Pérez", el servicio "Servicio 20 hs" a 4500000, `ACE-01` x 2 a 1200000, el servicio adicional "Limpieza" a 1500000 y el chequeo "Entrega"
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** el formulario muestra esos valores (importes como `45.000,00`, `12.000,00` y `15.000,00`), "Entrega" marcado y el resumen con Subtotal servicios $ 60.000,00, Subtotal ítems $ 12.000,00 y Total $ 72.000,00

#### Scenario: Cancelar
- **GIVEN** el modal "Editar orden OT-0043" con cambios sin guardar
- **WHEN** el usuario pulsa "Cancelar"
- **THEN** el modal se cierra, no se envía ninguna petición y la orden no cambia

#### Scenario: Servicio que ya no está en el catálogo
- **GIVEN** la orden `OT-0043` con el servicio "Servicio 20 hs" y `servicio-20-hs` borrado del catálogo
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** el selector de servicio general muestra "Servicio 20 hs (actual)" elegido, con sus chequeos guardados en "Incluye:"
- **AND** al guardar sin cambiarlo, la orden conserva ese servicio

#### Scenario: Servicio adicional que ya no está en el catálogo
- **GIVEN** la orden `OT-0043` con el servicio adicional del catálogo "Pulido" a 800000, que luego se borró del catálogo
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** "Pulido" aparece como servicio adicional personalizado con su importe `8.000,00`

### Requirement: Stock disponible al editar
En el modal de edición, la etiqueta de cada producto SHALL indicar su stock actual y, si la orden ya lo tenía, la cantidad que la orden ya descontó, porque también se puede usar. Los productos dados de baja que ya están en la orden SHALL aparecer en su línea marcados "(dado de baja)" y no SHALL ofrecerse en líneas nuevas. Como en "Nueva orden", el stock lo valida la API (409) y el error se muestra bajo la línea.

#### Scenario: Etiqueta con lo ya descontado
- **GIVEN** la orden `OT-0043` con `ACE-01` x 2 y `ACE-01` con stock 3
- **WHEN** se abre "Editar orden OT-0043"
- **THEN** la línea de `ACE-01` muestra "(stock 3 + 2 en esta orden)" y debajo la ayuda "Hasta 5: 3 en stock + 2 ya descontados por esta orden."

#### Scenario: Producto dado de baja en la orden
- **GIVEN** la orden `OT-0043` con `C-99` x 2 y `C-99` dado de baja
- **WHEN** se abre "Editar orden OT-0043" y se agrega una línea nueva
- **THEN** la línea de `C-99` lo muestra marcado "(dado de baja)" y el selector de la línea nueva no ofrece `C-99`

#### Scenario: Excede lo disponible
- **GIVEN** el modal "Editar orden OT-0043" con `ACE-01` x 2 y stock 3
- **WHEN** el usuario pone 6 en esa línea, pulsa "Guardar cambios" y la API responde 409
- **THEN** la línea de `ACE-01` muestra "Disponible 3, solicitado 4" con `aria-invalid` y el modal sigue abierto

### Requirement: Chequeo final en el formulario de edición
El fieldset "Chequeo final" SHALL mostrar los seis ítems de la lista fija como casillas con su nombre y, en la misma fila, una caja de importe (mismo formato y validación que los demás importes) habilitada solo si la casilla está marcada; al desmarcar, el importe SHALL vaciarse y deshabilitarse. El resumen en vivo SHALL sumar los importes del chequeo al "Subtotal servicios". Cada casilla y cada importe SHALL tener nombre accesible y objetivos táctiles de al menos 44 px.

#### Scenario: Marcar con precio
- **GIVEN** el modal "Editar orden" con Subtotal servicios $ 60.000,00
- **WHEN** el usuario marca "Combustible" y escribe `8.000` en su importe
- **THEN** el resumen muestra Subtotal servicios $ 68.000,00 y el Total aumenta $ 8.000,00

#### Scenario: Desmarcar
- **GIVEN** "Combustible" marcado con importe `8.000`
- **WHEN** el usuario lo desmarca
- **THEN** su importe queda vacío y deshabilitado y el resumen deja de sumarlo

#### Scenario: Importe inválido
- **GIVEN** "Entrega" marcado
- **WHEN** el usuario escribe `12.5` en su importe y pulsa "Guardar cambios"
- **THEN** el importe muestra "Ingresá un importe válido (ej. 12.500,50)." y no se envía nada

### Requirement: Resultado de la edición
Al guardar, el botón SHALL deshabilitarse mientras espera. Si la API acepta, el modal SHALL cerrarse, la lista SHALL recargarse con los filtros vigentes y un aviso persistente SHALL decir "Orden OT-XXXX actualizada." con cada ajuste de stock (descontado o devuelto, stock resultante, reactivado) o "Sin cambios de stock.". Si rechaza, el modal SHALL quedar abierto con lo cargado y mostrar el error en la línea afectada o en la alerta general; si la orden ya no existe, SHALL decirlo.

#### Scenario: Guardado con ajustes
- **GIVEN** el modal "Editar orden OT-0043" con `ACE-01` x 2 pasado a x 3
- **WHEN** el usuario pulsa "Guardar cambios" y la API acepta
- **THEN** el modal se cierra, `OT-0043` aparece con `ACE-01` x 3 y el aviso dice "Orden OT-0043 actualizada." con "ACE-01 −1 descontada (stock 2)" si el stock era 3

#### Scenario: Guardado con reintegro de un producto dado de baja
- **GIVEN** el modal "Editar orden OT-0043" con `FIL-01` (dado de baja, stock 3) x 1 y el usuario quita esa línea
- **WHEN** pulsa "Guardar cambios" y la API acepta
- **THEN** el aviso incluye "FIL-01 +1 devuelta (stock 4, reactivado)"

#### Scenario: Guardado sin ajustes
- **GIVEN** el modal "Editar orden OT-0043" donde solo cambió el cliente
- **WHEN** pulsa "Guardar cambios" y la API acepta
- **THEN** el aviso dice "Orden OT-0043 actualizada." y "Sin cambios de stock."

#### Scenario: Stock insuficiente
- **GIVEN** el modal "Editar orden OT-0043" y otro usuario dejó `ACE-01` sin stock
- **WHEN** el usuario aumenta `ACE-01` y la API responde 409
- **THEN** el modal sigue abierto con lo cargado y la línea de `ACE-01` muestra el faltante

#### Scenario: Orden borrada mientras se editaba
- **GIVEN** el modal "Editar orden OT-0043" abierto y la orden borrada por otro usuario
- **WHEN** el usuario pulsa "Guardar cambios" y la API responde 404
- **THEN** el modal informa que la orden ya no existe y, al cerrarlo, la lista se recarga sin `OT-0043`

### Requirement: Chequeo final en pantalla
En `/ordenes`, cada orden con chequeo final SHALL mostrar una fila "Chequeo final:" con un chip por ítem marcado ("Combustible · $ 8.000,00" o "Entrega · —"), después de los servicios adicionales; sin ítems marcados la fila SHALL NOT mostrarse.

#### Scenario: Orden con chequeo en pantalla
- **GIVEN** la orden `OT-0043` con el chequeo "Combustible" a 800000 y "Entrega" sin precio
- **WHEN** se muestra `/ordenes`
- **THEN** `OT-0043` tiene la fila "Chequeo final:" con "Combustible · $ 8.000,00" y "Entrega · —"

#### Scenario: Orden sin chequeo
- **GIVEN** la orden `OT-0041` sin chequeo final
- **WHEN** se muestra `/ordenes`
- **THEN** `OT-0041` no tiene fila "Chequeo final:"

### Requirement: Chequeo final completo en el PDF de una orden
El PDF de una orden ("Exportar PDF") SHALL incluir, después de "Servicios adicionales" y antes del resumen, la sección "Chequeo final" con los seis ítems de la lista fija en su orden (pedido del usuario, 2026-11-27). Cada ítem hecho SHALL mostrar "[✓]", su nombre, el texto "Hecho" y su precio ("—" si no tiene). Cada ítem no hecho SHALL mostrar "[ ]", su nombre y el texto "No se hizo", sin precio. La marca SHALL leerse por texto y símbolo, también impresa en blanco y negro.

#### Scenario: PDF con chequeo parcial
- **GIVEN** la orden `OT-0043` con el chequeo "Combustible" a 800000 y "Entrega" sin precio
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0043`
- **THEN** la sección "Chequeo final" lista, en orden, "[✓] Combustible · Hecho · $ 8.000,00", "[ ] Puesta en marcha · No se hizo", "[ ] Check-list y verificación final · No se hizo", "[ ] Prueba en el lago · No se hizo", "[ ] Limpieza de cortesía · No se hizo" y "[✓] Entrega · Hecho · —", antes del resumen
- **AND** el botón "Editar" no aparece en la hoja

#### Scenario: PDF de una orden sin chequeo
- **GIVEN** la orden `OT-0041` sin ningún ítem de chequeo marcado
- **WHEN** el usuario pulsa "Exportar PDF" en `OT-0041`
- **THEN** la sección "Chequeo final" lista los seis ítems con "[ ]" y "No se hizo"

#### Scenario: Marca legible sin color
- **GIVEN** la hoja de `OT-0043` impresa en blanco y negro
- **WHEN** se lee la sección "Chequeo final"
- **THEN** cada ítem se distingue como hecho o no hecho por su símbolo y su texto, sin depender del color
