/* validacion.js: funciones puras (sin DOM ni fetch). Cada una devuelve null (valido) o el mensaje.
   El backend sigue siendo la autoridad (RN-VA-04). Mensajes: design D6. */
(function () {
  "use strict";

  var MAX_CANTIDAD = 10000;
  var MAX_COMPONENTES = 100;
  var MAX_LINEAS_MODIFICACION = 100;
  var MSG_STOCK = "El stock debe ser un entero entre 0 y 10.000.";

  function adjetivo(etiqueta) {
    return /^La\s/.test(etiqueta) ? "obligatoria" : "obligatorio";
  }

  // opciones.recortar === false: no se recorta (contraseñas).
  function requerido(valor, etiqueta, opciones) {
    var texto = valor == null ? "" : String(valor);
    if (!(opciones && opciones.recortar === false)) texto = texto.trim();
    return texto === "" ? etiqueta + " es " + adjetivo(etiqueta) + "." : null;
  }

  function cantidad(texto) {
    var t = texto == null ? "" : String(texto).trim();
    var msg = "La cantidad debe ser un entero entre 1 y 10.000.";
    if (!/^\d+$/.test(t)) return msg;
    var n = Number(t);
    return n >= 1 && n <= MAX_CANTIDAD ? null : msg;
  }

  // Stock absoluto (alta y "Fijar en"): entero de 0 a 10.000.
  function stock(texto) {
    var t = texto == null ? "" : String(texto).trim();
    if (!/^\d+$/.test(t)) return MSG_STOCK;
    var n = Number(t);
    return n >= 0 && n <= MAX_CANTIDAD ? null : MSG_STOCK;
  }

  function largo(valor, max, etiqueta) {
    var t = valor == null ? "" : String(valor).trim();
    return t.length > max ? etiqueta + " admite hasta " + max + " caracteres." : null;
  }

  function fecha(texto) {
    var msg = "La fecha debe ser una fecha real con formato AAAA-MM-DD.";
    var t = texto == null ? "" : String(texto).trim();
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
    if (!m) return msg;
    var a = Number(m[1]), mes = Number(m[2]), d = Number(m[3]);
    var f = new Date(Date.UTC(a, mes - 1, d));
    var real = f.getUTCFullYear() === a && f.getUTCMonth() === mes - 1 && f.getUTCDate() === d;
    return real && a >= 1 ? null : msg;
  }

  // Ambos opcionales: con alguno vacio no hay rango que comparar.
  function rango(desde, hasta) {
    var d = desde == null ? "" : String(desde).trim();
    var h = hasta == null ? "" : String(hasta).trim();
    if (d === "" || h === "") return null;
    return d > h ? "Desde no puede ser posterior a Hasta." : null;
  }

  // lineas: [{codigo, cantidad}] -> {general, porLinea: [null | {producto, cantidad}]}
  function componentes(lineas) {
    var salida = { general: null, porLinea: [] };
    if (!lineas || lineas.length < 1) {
      salida.general = "Agregá al menos un componente.";
      return salida;
    }
    if (lineas.length > MAX_COMPONENTES) {
      salida.general = "Una orden admite hasta 100 componentes.";
    }
    lineas.forEach(function (l) {
      var producto = requerido(l.codigo, "El producto");
      var cant = cantidad(l.cantidad);
      salida.porLinea.push(producto || cant ? { producto: producto, cantidad: cant } : null);
    });
    return salida;
  }

  // lineas: [{codigo, modo: "fijar"|"sumar", valor, nombre}] ->
  //   {general, porLinea: [null | {producto, valor, nombre}]}
  function lineasModificacion(lineas) {
    var salida = { general: null, porLinea: [] };
    if (!lineas || lineas.length < 1) {
      salida.general = "Agregá al menos un producto.";
      return salida;
    }
    if (lineas.length > MAX_LINEAS_MODIFICACION) {
      salida.general = "Una modificación admite hasta 100 productos.";
    }
    var primera = {};
    lineas.forEach(function (l, i) {
      var codigo = l.codigo == null ? "" : String(l.codigo).trim();
      var producto = null;
      if (codigo === "") {
        producto = "Elegí un producto.";
      } else if (Object.prototype.hasOwnProperty.call(primera, codigo)) {
        producto = "Este producto ya está en la línea " + primera[codigo] + ".";
      } else {
        primera[codigo] = i + 1;
      }
      var valor = l.modo === "sumar" ? cantidad(l.valor) : stock(l.valor);
      var nombre = largo(l.nombre, 120, "El nombre");
      salida.porLinea.push(producto || valor || nombre ? { producto: producto, valor: valor, nombre: nombre } : null);
    });
    return salida;
  }

  function hayErrores(resultado) {
    return !!resultado.general || resultado.porLinea.some(function (e) { return e !== null; });
  }

  // Fecha local AAAA-MM-DD (para proponer "hoy").
  function hoy(ahora) {
    var d = ahora || new Date();
    function dos(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + dos(d.getMonth() + 1) + "-" + dos(d.getDate());
  }

  window.Validacion = {
    requerido: requerido, cantidad: cantidad, stock: stock, largo: largo, fecha: fecha,
    rango: rango, componentes: componentes, lineasModificacion: lineasModificacion,
    hayErrores: hayErrores, hoy: hoy
  };
})();
