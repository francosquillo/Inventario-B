/* chequeo-final.js: lista fija del chequeo final de una orden y lectura del formulario (spec interfaz-web: Chequeo final en el formulario de edicion); sin DOM ni red. Usa Precios.parsear. La lista es igual a CHEQUEO_FINAL del backend (la compara tests/test_chequeo_final_js.py). */
(function () {
  "use strict";

  var ITEMS = [
    { clave: "combustible", nombre: "Combustible" },
    { clave: "puesta-en-marcha", nombre: "Puesta en marcha" },
    { clave: "check-list-y-verificacion-final", nombre: "Check-list y verificación final" },
    { clave: "prueba-en-el-lago", nombre: "Prueba en el lago" },
    { clave: "limpieza-de-cortesia", nombre: "Limpieza de cortesía" },
    { clave: "entrega", nombre: "Entrega" }
  ];

  // estado: [{clave, marcado, importe: texto}] -> {valores: [{clave, precio: centavos|null}] (solo los marcados),
  // errores: [mensaje|null por fila de `estado`]}. El importe de un item sin marcar no se valida ni se envia.
  function leer(estado) {
    var valores = [];
    var errores = estado.map(function (fila) {
      if (!fila.marcado) return null;
      var importe = window.Precios.parsear(fila.importe);
      if (importe.error) return importe.error;
      valores.push({ clave: fila.clave, precio: importe.centavos });
      return null;
    });
    return { valores: valores, errores: errores };
  }

  window.ChequeoFinal = { ITEMS: ITEMS, leer: leer };
})();
