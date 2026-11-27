/* servicios.js: validacion pura de los servicios generales (spec interfaz-web: Servicio general en la nueva orden, Errores del servicio general); sin DOM ni red. */
(function () {
  "use strict";

  var NOMBRE_MAX = 60;
  var CHEQUEO_MAX = 60;
  var CHEQUEOS_MAX = 30;

  function minusculas(texto) {
    return String(texto).toLowerCase();
  }

  // valor: clave elegida en el selector ("" = sin servicio); catalogo: [{clave, nombre, chequeos}].
  // Devuelve {servicio: clave|null, error: texto|null}.
  function armar(valor, catalogo) {
    if (valor == null || valor === "") return { servicio: null, error: null };
    var existe = (catalogo || []).some(function (s) { return s.clave === valor; });
    if (!existe) return { servicio: null, error: "El servicio general elegido ya no está disponible." };
    return { servicio: valor, error: null };
  }

  // Chequeos del servicio elegido, en orden; [] para "sin servicio" o una clave desconocida.
  function chequeosDe(clave, catalogo) {
    var servicio = (catalogo || []).filter(function (s) { return s.clave === clave; })[0];
    return servicio ? servicio.chequeos.slice() : [];
  }

  // datos: {nombre, chequeos: [texto]}; claveActual: clave del servicio editado o null si es nuevo.
  // Devuelve {nombre, chequeos (recortados), errores: {nombre, general, chequeos: [msg|null]}}.
  function validarFormulario(datos, catalogo, claveActual) {
    var nombre = String(datos.nombre == null ? "" : datos.nombre).trim();
    var errorNombre = null;
    if (nombre === "") errorNombre = "El campo nombre es obligatorio.";
    else if (nombre.length > NOMBRE_MAX) {
      errorNombre = "El nombre del servicio general admite hasta " + NOMBRE_MAX + " caracteres.";
    } else {
      var buscado = minusculas(nombre);
      var repetido = (catalogo || []).some(function (s) {
        return s.clave !== claveActual && minusculas(s.nombre) === buscado;
      });
      if (repetido) errorNombre = "Ya existe un servicio general con nombre '" + nombre + "'.";
    }

    var lineas = (datos.chequeos || []).map(function (t) { return String(t == null ? "" : t).trim(); });
    var general = null;
    if (lineas.length === 0) general = "El servicio general requiere al menos un chequeo.";
    else if (lineas.length > CHEQUEOS_MAX) general = "El servicio general admite hasta " + CHEQUEOS_MAX + " chequeos.";

    var vistos = {};
    var errores = lineas.map(function (texto) {
      if (texto === "") return "El nombre es obligatorio.";
      if (texto.length > CHEQUEO_MAX) return "El nombre admite hasta " + CHEQUEO_MAX + " caracteres.";
      var clave = minusculas(texto);
      if (vistos[clave]) return "'" + texto + "' está repetido.";
      vistos[clave] = true;
      return null;
    });
    return { nombre: nombre, chequeos: lineas, errores: { nombre: errorNombre, general: general, chequeos: errores } };
  }

  window.Servicios = {
    NOMBRE_MAX: NOMBRE_MAX,
    CHEQUEO_MAX: CHEQUEO_MAX,
    CHEQUEOS_MAX: CHEQUEOS_MAX,
    armar: armar,
    chequeosDe: chequeosDe,
    validarFormulario: validarFormulario
  };
})();
