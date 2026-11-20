/* login.js: formulario de acceso (specs interfaz-web: Formulario, Errores del login, Sesion expirada). */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("login-form");
    var usuario = document.getElementById("username");
    var clave = document.getElementById("password");
    var alerta = document.getElementById("login-alerta");
    var boton = document.getElementById("login-enviar");
    var enviando = false;

    if (new URLSearchParams(window.location.search).get("sesion") === "expirada") {
      document.getElementById("aviso-expirada").hidden = false;
    }

    function validar() {
      window.UI.limpiarErrores(form);
      window.UI.ocultarAlerta(alerta);
      var eUsuario = window.Validacion.requerido(usuario.value, "El usuario");
      var eClave = window.Validacion.requerido(clave.value, "La contraseña", { recortar: false });
      var primero = null;
      if (eUsuario) { window.UI.errorBajoCampo(usuario, eUsuario); primero = usuario; }
      if (eClave) {
        window.UI.errorBajoCampo(clave, eClave, clave.parentNode);
        primero = primero || clave;
      }
      if (primero) primero.focus();
      return primero === null;
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (enviando || !validar()) return;
      enviando = true;
      var restaurar = window.UI.ocupado(boton, "Ingresando…");
      window.Api.post("/api/login", { username: usuario.value.trim(), password: clave.value }).then(
        function () { window.location.assign("/inventario"); },
        function (err) {
          enviando = false;
          restaurar();
          window.UI.alerta(alerta, err.detail, "error");
          if (err.status === 401) clave.value = "";
          clave.focus();
        }
      );
    });
  });
})();
