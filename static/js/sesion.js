/* sesion.js: usuario en la cabecera, "Cerrar sesion" y revalidacion al volver con "Atras". */
(function () {
  "use strict";

  function cargarUsuario() {
    return window.Api.get("/api/me").then(function (u) {
      var el = document.getElementById("usuario-nombre");
      if (el && u) el.textContent = u.username;
    }).catch(function () { /* el 401 ya redirige; otros fallos no bloquean la pagina */ });
  }

  function cerrarSesion(boton) {
    boton.disabled = true;
    window.Api.post("/api/logout").then(
      function () { window.location.assign("/"); },
      function () { window.location.assign("/"); }
    );
  }

  document.addEventListener("DOMContentLoaded", function () {
    cargarUsuario();
    var boton = document.getElementById("btn-logout");
    if (boton) boton.addEventListener("click", function () { cerrarSesion(boton); });
  });

  // Pagina restaurada desde la cache del navegador (Atras tras cerrar sesion): revalidar.
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) cargarUsuario();
  });
})();
