/* datos-orden.js: validacion pura de los datos del cliente y la embarcacion de "Nueva orden" (spec interfaz-web: Datos del cliente en la nueva orden); sin DOM ni red. Mismos textos que el backend. */
(function () {
  "use strict";

  var CLIENTE_MAX = 80;
  var EMBARCACION_MAX = 60;
  var CELULAR_MIN = 6;
  var CELULAR_MAX = 20;
  var MSG_CELULAR = "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres).";
  var FORMATO_CELULAR = /^\+?[0-9 ()-]+$/;
  var FORMATO_FECHA = /^\d{4}-\d{2}-\d{2}$/;

  function recortar(valor) {
    var t = String(valor == null ? "" : valor).trim();
    return t === "" ? null : t;
  }

  function fechaReal(texto) {
    var p = texto.split("-").map(Number);
    var d = new Date(Date.UTC(p[0], p[1] - 1, p[2]));
    return d.getUTCFullYear() === p[0] && d.getUTCMonth() === p[1] - 1 && d.getUTCDate() === p[2];
  }

  function validarFecha(texto, etiqueta, errores, campo) {
    if (texto === null) return;
    if (!FORMATO_FECHA.test(texto)) {
      errores[campo] = "La fecha de " + etiqueta + " debe tener formato AAAA-MM-DD.";
    } else if (!fechaReal(texto)) {
      errores[campo] = "La fecha de " + etiqueta + " (" + texto + ") no es una fecha válida.";
    }
  }

  // campos: {cliente, celular, casco, motor, trailer, fecha_ingreso, fecha_egreso} (texto o vacio).
  // Devuelve {valores (recortados, null si vacio), errores: {campo: mensaje}}; todos son opcionales.
  function validar(campos) {
    campos = campos || {};
    var valores = {};
    ["cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso"].forEach(function (c) {
      valores[c] = recortar(campos[c]);
    });
    var errores = {};
    validarFecha(valores.fecha_ingreso, "ingreso", errores, "fecha_ingreso");
    validarFecha(valores.fecha_egreso, "egreso", errores, "fecha_egreso");
    if (valores.fecha_ingreso && valores.fecha_egreso && !errores.fecha_ingreso && !errores.fecha_egreso &&
        valores.fecha_egreso < valores.fecha_ingreso) {
      errores.fecha_egreso = "La fecha de egreso no puede ser anterior a la de ingreso.";
    }
    if (valores.cliente !== null && valores.cliente.length > CLIENTE_MAX) {
      errores.cliente = "El cliente admite hasta " + CLIENTE_MAX + " caracteres.";
    }
    var celular = valores.celular;
    if (celular !== null) {
      var digitos = (celular.match(/[0-9]/g) || []).length;
      if (celular.length < CELULAR_MIN || celular.length > CELULAR_MAX || !FORMATO_CELULAR.test(celular) ||
          digitos < CELULAR_MIN) {
        errores.celular = MSG_CELULAR;
      }
    }
    ["casco", "motor", "trailer"].forEach(function (c) {
      if (valores[c] !== null && valores[c].length > EMBARCACION_MAX) {
        errores[c] = "El campo " + c + " admite hasta " + EMBARCACION_MAX + " caracteres.";
      }
    });
    return { valores: valores, errores: errores };
  }

  window.DatosOrden = {
    CLIENTE_MAX: CLIENTE_MAX,
    EMBARCACION_MAX: EMBARCACION_MAX,
    validar: validar
  };
})();
