/* busqueda.js: funciones puras del buscador de /inventario (spec interfaz-web: Buscador, Conteo); sin DOM ni red. */
(function () {
  "use strict";

  // Minusculas, sin tildes y sin espacios en los bordes. null/undefined -> "".
  function normalizar(texto) {
    return String(texto == null ? "" : texto)
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  // Productos cuyo codigo o nombre contiene el texto completo (una sola subcadena); conserva el orden.
  function filtrar(productos, texto) {
    var q = normalizar(texto);
    if (q === "") return productos;
    return productos.filter(function (p) {
      return normalizar(p.codigo).indexOf(q) !== -1 || normalizar(p.nombre).indexOf(q) !== -1;
    });
  }

  // "T productos" / "1 producto"; con busqueda que filtra (V < T): "V de T productos".
  function conteo(visibles, total, hayBusqueda) {
    if (hayBusqueda && visibles < total) return visibles + " de " + total + " productos";
    return total + (total === 1 ? " producto" : " productos");
  }

  window.Busqueda = { normalizar: normalizar, filtrar: filtrar, conteo: conteo };
})();
