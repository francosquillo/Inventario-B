/* procesos.js: validacion pura de los procesos de "Nueva orden" (spec interfaz-web: Validacion de procesos); sin DOM ni red. */
(function () {
  "use strict";

  var PERSONALIZADO = "personalizado";
  var NOMBRE_MAX = 60;
  var PERSONALIZADOS_MAX = 10;

  function minusculas(texto) {
    return String(texto).toLowerCase();
  }

  // lineas: [{valor: clave del catalogo | "personalizado", texto, precio: centavos|null}]; catalogo: [{clave, nombre}].
  // Devuelve {procesos: [{clave, precio}], procesos_personalizados: [{nombre, precio}], errores}:
  // errores[i] es el mensaje de la linea i o null. Un proceso del catalogo repetido es error en su
  // segunda linea (cada linea lleva su precio: descartar uno en silencio perderia plata); un
  // personalizado igual al catalogo, repetido o fuera del tope tambien. El texto de una linea de
  // catalogo no se envia.
  function armar(lineas, catalogo) {
    var nombresCatalogo = {};
    (catalogo || []).forEach(function (p) { nombresCatalogo[minusculas(p.nombre)] = true; });
    var procesos = [];
    var clavesVistas = {};
    var personalizados = [];
    var vistos = {};
    var errores = lineas.map(function (l) {
      var precio = l.precio == null ? null : l.precio;
      if (l.valor !== PERSONALIZADO) {
        if (!l.valor) return null;
        if (clavesVistas[l.valor]) return "Ya está en otra línea.";
        clavesVistas[l.valor] = true;
        procesos.push({ clave: l.valor, precio: precio });
        return null;
      }
      var texto = String(l.texto == null ? "" : l.texto).trim();
      var clave = minusculas(texto);
      var error = null;
      if (texto === "") error = "El nombre es obligatorio.";
      else if (texto.length > NOMBRE_MAX) error = "El nombre admite hasta " + NOMBRE_MAX + " caracteres.";
      else if (nombresCatalogo[clave]) error = "'" + texto + "' ya está en la lista de procesos; marcalo ahí.";
      else if (vistos[clave]) error = "'" + texto + "' está repetido.";
      else if (personalizados.length >= PERSONALIZADOS_MAX) {
        error = "Una orden admite hasta " + PERSONALIZADOS_MAX + " procesos personalizados.";
      }
      if (error === null) {
        vistos[clave] = true;
        personalizados.push({ nombre: texto, precio: precio });
      }
      return error;
    });
    return { procesos: procesos, procesos_personalizados: personalizados, errores: errores };
  }

  window.Procesos = {
    PERSONALIZADO: PERSONALIZADO,
    NOMBRE_MAX: NOMBRE_MAX,
    PERSONALIZADOS_MAX: PERSONALIZADOS_MAX,
    armar: armar
  };
})();
