/* api.js: cliente fetch de la API JSON (design D5). Expone window.Api y window.ApiError. */
(function () {
  "use strict";

  var MSG_RED = "No se pudo conectar con el servidor. Revisá que esté en marcha y probá de nuevo.";
  var MSG_INESPERADO = "Ocurrió un error inesperado. Probá de nuevo.";

  function ApiError(status, detail, faltantes, codigos) {
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.faltantes = faltantes || null;
    this.codigos = codigos || null;
    this.message = detail;
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  function esLogin(url) {
    return url.split("?")[0] === "/api/login";
  }

  function leerJson(respuesta) {
    return respuesta.text().then(function (texto) {
      if (texto === "") return null;
      try { return JSON.parse(texto); } catch (e) { return null; }
    });
  }

  function pedir(metodo, url, cuerpo) {
    var opciones = {
      method: metodo,
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    };
    if (cuerpo !== undefined) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(cuerpo);
    }
    return fetch(url, opciones).then(
      function (respuesta) {
        if (respuesta.status === 401 && !esLogin(url)) {
          window.location.assign("/?sesion=expirada");
          return new Promise(function () {}); // nunca resuelve: nadie pinta un error encima
        }
        return leerJson(respuesta).then(function (datos) {
          if (respuesta.ok) return datos;
          var detail = datos && typeof datos.detail === "string" ? datos.detail : null;
          if (respuesta.status >= 500 || detail === null) detail = MSG_INESPERADO;
          var faltantes = datos && Array.isArray(datos.faltantes) ? datos.faltantes : null;
          var codigos = datos && Array.isArray(datos.codigos) ? datos.codigos : null;
          throw new ApiError(respuesta.status, detail, faltantes, codigos);
        });
      },
      function () { throw new ApiError(0, MSG_RED); }
    );
  }

  window.ApiError = ApiError;
  window.Api = {
    pedir: pedir,
    get: function (url) { return pedir("GET", url); },
    post: function (url, cuerpo) { return pedir("POST", url, cuerpo); },
    borrar: function (url) { return pedir("DELETE", url); }
  };
})();
