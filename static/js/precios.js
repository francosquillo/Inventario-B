/* precios.js: importes en pesos <-> centavos enteros y resumen de la nueva orden (spec interfaz-web: Importes, Resumen); sin DOM ni red, aritmetica entera, sin coma flotante. */
(function () {
  "use strict";

  var MAXIMO_CENTAVOS = 99999999999;
  var ERROR_FORMATO = "Ingresá un importe válido (ej. 12.500,50).";
  var ERROR_MAXIMO = "El importe admite hasta $ 999.999.999,99.";
  // Entero sin separador o con puntos de miles solo en grupos de 3; coma decimal con 1-2 digitos.
  var FORMATO = /^(\d+|\d{1,3}(?:\.\d{3})+)(?:,(\d{1,2}))?$/;

  // texto -> {centavos: entero|null, error: texto|null}; vacio = sin precio (centavos null, sin error).
  function parsear(texto) {
    var t = String(texto == null ? "" : texto).trim();
    if (t === "") return { centavos: null, error: null };
    t = t.replace(/^\$\s*/, "");
    var m = FORMATO.exec(t);
    if (!m) return { centavos: null, error: ERROR_FORMATO };
    var entero = m[1].replace(/\./g, "").replace(/^0+(?=\d)/, "");
    if (entero.length > 9) return { centavos: null, error: ERROR_MAXIMO };
    var decimales = (m[2] || "") + "00";
    var centavos = Number(entero) * 100 + Number(decimales.slice(0, 2));
    if (centavos > MAXIMO_CENTAVOS) return { centavos: null, error: ERROR_MAXIMO };
    return { centavos: centavos, error: null };
  }

  // centavos|null -> "$ 12.500,50" | "—"
  function formatear(centavos) {
    if (centavos == null) return "—";
    var entero = String(Math.floor(centavos / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    var dec = String(centavos % 100);
    return "$ " + entero + "," + (dec.length < 2 ? "0" + dec : dec);
  }

  function aCentavos(valor) {
    return typeof valor === "number" && isFinite(valor) ? valor : 0; // vacio o invalido = 0
  }

  function sumar(lista) {
    return (lista || []).reduce(function (acc, v) { return acc + aCentavos(v); }, 0);
  }

  // {servicio, adicionales: [centavos|null], items: [centavos|null], chequeo_final?: [centavos|null]} -> subtotales y total
  // (vista previa). El chequeo final suma al subtotal de servicios.
  function resumen(datos) {
    var servicios = aCentavos(datos.servicio) + sumar(datos.adicionales) + sumar(datos.chequeo_final);
    var items = sumar(datos.items);
    return { subtotal_servicios: servicios, subtotal_items: items, total: servicios + items };
  }

  window.Precios = {
    MAXIMO_CENTAVOS: MAXIMO_CENTAVOS,
    ERROR_FORMATO: ERROR_FORMATO,
    ERROR_MAXIMO: ERROR_MAXIMO,
    parsear: parsear,
    formatear: formatear,
    resumen: resumen
  };
})();
