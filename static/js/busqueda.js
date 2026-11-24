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

  // Valor del filtro de categoria que selecciona los productos sin categoria.
  var SIN_CATEGORIA = "__sin__";

  // "" / undefined = todas; SIN_CATEGORIA = categoria null o ausente; si no, la clave exacta.
  function porCategoria(productos, categoria) {
    if (categoria == null || categoria === "") return productos;
    return productos.filter(function (p) {
      var c = p.categoria == null ? null : p.categoria;
      return categoria === SIN_CATEGORIA ? c === null : c === categoria;
    });
  }

  // Productos cuyo codigo o nombre contiene el texto completo (una sola subcadena) y que cumplen
  // el filtro de categoria (opcional, AND); conserva el orden.
  function filtrar(productos, texto, categoria) {
    var q = normalizar(texto);
    var lista = porCategoria(productos, categoria);
    if (q === "") return lista;
    return lista.filter(function (p) {
      return normalizar(p.codigo).indexOf(q) !== -1 || normalizar(p.nombre).indexOf(q) !== -1;
    });
  }

  // Cartel de "sin coincidencias": busqueda, categoria o ambas (nombreCategoria ya es el nombre a mostrar).
  function mensajeSinCoincidencias(texto, nombreCategoria) {
    var t = String(texto == null ? "" : texto).trim();
    var hayCategoria = nombreCategoria != null && nombreCategoria !== "";
    if (t !== "" && hayCategoria) {
      return "Ningún producto coincide con «" + t + "» en la categoría «" + nombreCategoria + "»";
    }
    if (t !== "") return "Ningún producto coincide con «" + t + "»";
    if (hayCategoria) return "Ningún producto en la categoría «" + nombreCategoria + "»";
    return "Ningún producto coincide con los filtros";
  }

  // Nombre a mostrar de una categoria: "Sin categoria" si no tiene; la clave cruda si el catalogo no la conoce.
  function nombreCategoria(clave, mapa) {
    if (clave == null || clave === "") return "Sin categoría";
    return (mapa && mapa[clave]) || clave;
  }

  // Linea del encabezado del PDF del inventario: "[Categoria · ]N productos · AAAA-MM-DD".
  function lineaInventario(n, nombreCat, fecha) {
    var cantidad = n + (n === 1 ? " producto" : " productos");
    return (nombreCat ? nombreCat + " · " : "") + cantidad + " · " + fecha;
  }

  // Nueva orden: true si el producto elegido (por codigo) sigue en la lista filtrada por categoria.
  function productoSigueVisible(codigo, productos, categoria) {
    if (!codigo) return false;
    return porCategoria(productos, categoria).some(function (p) { return p.codigo === codigo; });
  }

  // "T productos" / "1 producto"; con busqueda que filtra (V < T): "V de T productos".
  function conteo(visibles, total, hayBusqueda) {
    if (hayBusqueda && visibles < total) return visibles + " de " + total + " productos";
    return total + (total === 1 ? " producto" : " productos");
  }

  window.Busqueda = {
    SIN_CATEGORIA: SIN_CATEGORIA,
    normalizar: normalizar,
    porCategoria: porCategoria,
    filtrar: filtrar,
    conteo: conteo,
    mensajeSinCoincidencias: mensajeSinCoincidencias,
    nombreCategoria: nombreCategoria,
    lineaInventario: lineaInventario,
    productoSigueVisible: productoSigueVisible,
  };
})();
