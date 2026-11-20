# Casos de `window.Validacion` (tarea 12.3)

Se ejecutan en el navegador con `browser_evaluate` sobre `/inventario`. Cada fila es una expresión JS y el resultado esperado (`null` = válido). Cubre los escenarios de `specs/interfaz-web` "Validación en el navegador" y "Errores del login".

| # | Escenario | Expresión | Esperado |
|---|-----------|-----------|----------|
| 1 | Cantidad 2.5 | `Validacion.cantidad("2.5")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 2 | Cantidad 0 | `Validacion.cantidad("0")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 3 | Cantidad 10001 | `Validacion.cantidad("10001")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 4 | Cantidad vacía | `Validacion.cantidad("")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 5 | Cantidad negativa | `Validacion.cantidad("-3")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 6 | Cantidad con letras | `Validacion.cantidad("1e3")` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 7 | Cantidad mínima | `Validacion.cantidad("1")` | `null` |
| 8 | Cantidad máxima | `Validacion.cantidad("10000")` | `null` |
| 9 | Cantidad con espacios | `Validacion.cantidad(" 7 ")` | `null` |
| 10 | Código largo (51) | `Validacion.largo("x".repeat(51), 50, "El código")` | `"El código admite hasta 50 caracteres."` |
| 11 | Código en el límite (50) | `Validacion.largo("x".repeat(50), 50, "El código")` | `null` |
| 12 | Número largo (31) | `Validacion.largo("x".repeat(31), 30, "El número de orden")` | `"El número de orden admite hasta 30 caracteres."` |
| 13 | Nombre largo (121) | `Validacion.largo("x".repeat(121), 120, "El nombre")` | `"El nombre admite hasta 120 caracteres."` |
| 14 | Fecha 2026-02-30 | `Validacion.fecha("2026-02-30")` | `"La fecha debe ser una fecha real con formato AAAA-MM-DD."` |
| 15 | Fecha con otro formato | `Validacion.fecha("20/11/2026")` | `"La fecha debe ser una fecha real con formato AAAA-MM-DD."` |
| 16 | Fecha vacía | `Validacion.fecha("")` | `"La fecha debe ser una fecha real con formato AAAA-MM-DD."` |
| 17 | Fecha mes 13 | `Validacion.fecha("2026-13-01")` | `"La fecha debe ser una fecha real con formato AAAA-MM-DD."` |
| 18 | Fecha válida | `Validacion.fecha("2026-11-20")` | `null` |
| 19 | 29 de febrero bisiesto | `Validacion.fecha("2028-02-29")` | `null` |
| 20 | 29 de febrero no bisiesto | `Validacion.fecha("2027-02-29")` | `"La fecha debe ser una fecha real con formato AAAA-MM-DD."` |
| 21 | Rango invertido | `Validacion.rango("2026-11-20", "2026-11-01")` | `"Desde no puede ser posterior a Hasta."` |
| 22 | Rango válido | `Validacion.rango("2026-11-01", "2026-11-20")` | `null` |
| 23 | Rango de un día | `Validacion.rango("2026-11-20", "2026-11-20")` | `null` |
| 24 | Rango con Hasta vacío | `Validacion.rango("2026-11-20", "")` | `null` |
| 25 | Obligatorio vacío (masc.) | `Validacion.requerido("   ", "El código")` | `"El código es obligatorio."` |
| 26 | Obligatorio vacío (fem.) | `Validacion.requerido("", "La contraseña")` | `"La contraseña es obligatoria."` |
| 27 | Obligatorio con valor | `Validacion.requerido(" A-01 ", "El código")` | `null` |
| 28 | Contraseña de espacios no se recorta | `Validacion.requerido("  ", "La contraseña", { recortar: false })` | `null` |
| 29 | Usuario vacío | `Validacion.requerido("", "El usuario")` | `"El usuario es obligatorio."` |
| 30 | Sin líneas | `Validacion.componentes([]).general` | `"Agregá al menos un componente."` |
| 31 | 101 líneas | `Validacion.componentes(Array.from({length:101},()=>({codigo:"A-01",cantidad:"1"}))).general` | `"Una orden admite hasta 100 componentes."` |
| 32 | 100 líneas válidas | `Validacion.hayErrores(Validacion.componentes(Array.from({length:100},()=>({codigo:"A-01",cantidad:"1"}))))` | `false` |
| 33 | Línea sin producto | `Validacion.componentes([{codigo:"",cantidad:"1"}]).porLinea[0].producto` | `"El producto es obligatorio."` |
| 34 | Línea con cantidad 0 | `Validacion.componentes([{codigo:"A-01",cantidad:"0"}]).porLinea[0].cantidad` | `"La cantidad debe ser un entero entre 1 y 10.000."` |
| 35 | Línea válida entre inválidas | `Validacion.componentes([{codigo:"A-01",cantidad:"2"},{codigo:"",cantidad:"1"}]).porLinea[0]` | `null` |
| 36 | Fecha de hoy local | `Validacion.hoy(new Date(2026, 10, 5))` | `"2026-11-05"` |
