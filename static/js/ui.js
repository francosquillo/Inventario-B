/* ui.js: modales, foco, alertas y helpers de DOM. Evolucion de design-system/ui.js.
   Los datos se insertan solo con textContent / createElement (design D4). */
(function () {
  "use strict";

  var FOCUS = 'input:not([type=hidden]):not([disabled]),select:not([disabled]),textarea:not([disabled]),button:not([disabled]),[href]';
  var CLASE_ALERTA = {
    error: "p-3 rounded-md border border-danger bg-danger-subtle text-danger-fg text-sm",
    info: "p-3 rounded-md border border-line bg-info-subtle text-info-fg text-sm"
  };
  var actual = null;   // overlay abierto
  var retorno = null;  // control que lo abrio

  function el(etiqueta, atributos, texto) {
    var nodo = document.createElement(etiqueta);
    if (atributos) {
      Object.keys(atributos).forEach(function (k) {
        if (atributos[k] === false || atributos[k] == null) return;
        nodo.setAttribute(k, atributos[k] === true ? "" : atributos[k]);
      });
    }
    if (texto != null) nodo.textContent = texto;
    return nodo;
  }

  function vaciar(nodo) {
    while (nodo.firstChild) nodo.removeChild(nodo.firstChild);
    return nodo;
  }

  function visibles(raiz) {
    return [].slice.call(raiz.querySelectorAll(FOCUS)).filter(function (n) {
      return n.offsetParent !== null;
    });
  }

  function abrir(overlay) {
    if (!overlay) return;
    if (actual && actual !== overlay) cerrar();
    retorno = document.activeElement;
    actual = overlay;
    overlay.hidden = false;
    var destino = overlay.querySelector("[data-autofocus]") ||
      overlay.querySelector("input:not([type=hidden]):not([type=checkbox]):not([disabled]),select:not([disabled]),textarea:not([disabled])") ||
      overlay.querySelector(FOCUS);
    if (destino) destino.focus();
  }

  function cerrar() {
    if (!actual) return;
    var overlay = actual;
    actual = null;
    overlay.hidden = true;
    var volver = retorno;
    retorno = null;
    overlay.dispatchEvent(new CustomEvent("modal:cerrado"));
    if (volver && document.contains(volver) && volver.focus) volver.focus();
  }

  function ocupadoModal() {
    return actual && actual.querySelector('[aria-busy="true"]') !== null;
  }

  document.addEventListener("click", function (e) {
    if (!actual) return;
    if (ocupadoModal()) return;
    if (e.target === actual || (e.target.closest && e.target.closest("[data-close]") && actual.contains(e.target))) {
      cerrar();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (!actual) return;
    if (e.key === "Escape") {
      if (!ocupadoModal()) cerrar();
      return;
    }
    if (e.key === "Tab") {
      var items = visibles(actual);
      if (!items.length) return;
      var a = items[0], z = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === a || !actual.contains(document.activeElement))) {
        e.preventDefault(); z.focus();
      } else if (!e.shiftKey && (document.activeElement === z || !actual.contains(document.activeElement))) {
        e.preventDefault(); a.focus();
      }
    }
  });

  // Mostrar / ocultar contraseña: <button data-toggle="id-del-input">.
  document.addEventListener("click", function (e) {
    var tg = e.target.closest && e.target.closest("[data-toggle]");
    if (!tg) return;
    var input = document.getElementById(tg.getAttribute("data-toggle"));
    if (!input) return;
    var mostrar = input.type === "password";
    input.type = mostrar ? "text" : "password";
    tg.textContent = mostrar ? "Ocultar" : "Mostrar";
    tg.setAttribute("aria-pressed", String(mostrar));
  });

  // Alerta en un contenedor: reemplaza su contenido. tipo: "error" | "info".
  function alerta(contenedor, texto, tipo) {
    vaciar(contenedor);
    contenedor.className = CLASE_ALERTA[tipo || "error"];
    contenedor.setAttribute("role", "alert");
    contenedor.textContent = texto;
    contenedor.hidden = false;
    return contenedor;
  }

  function ocultarAlerta(contenedor) {
    vaciar(contenedor);
    contenedor.hidden = true;
  }

  // Boton "enviando": deshabilitado + texto; devuelve una funcion que restaura.
  function ocupado(boton, textoOcupado) {
    var original = boton.textContent;
    boton.disabled = true;
    boton.setAttribute("aria-busy", "true");
    boton.textContent = textoOcupado;
    return function () {
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
      boton.textContent = original;
    };
  }

  // Marca un campo invalido enlazado a un mensaje existente (alerta) por aria-describedby.
  function invalido(campo, idMensaje) {
    campo.setAttribute("aria-invalid", "true");
    if (idMensaje) campo.setAttribute("aria-describedby", idMensaje);
  }

  // Error de validacion bajo su campo: <p class="err" role="alert"> tras el campo (o su contenedor).
  function errorBajoCampo(campo, mensaje, ancla) {
    var id = (campo.id || "campo") + "-e";
    var previo = document.getElementById(id);
    if (previo) previo.remove();
    campo.setAttribute("aria-invalid", "true");
    var p = el("p", { "class": "err", id: id, role: "alert", "data-error": true }, mensaje);
    (ancla || campo).insertAdjacentElement("afterend", p);
    var ids = (campo.getAttribute("data-desc-base") || "");
    campo.setAttribute("aria-describedby", (ids ? ids + " " : "") + id);
    return p;
  }

  function limpiarErrores(raiz) {
    [].forEach.call(raiz.querySelectorAll("[data-error]"), function (n) { n.remove(); });
    [].forEach.call(raiz.querySelectorAll('[aria-invalid="true"]'), function (c) {
      c.removeAttribute("aria-invalid");
      var base = c.getAttribute("data-desc-base");
      if (base) c.setAttribute("aria-describedby", base); else c.removeAttribute("aria-describedby");
    });
  }

  window.UI = {
    el: el, vaciar: vaciar, abrir: abrir, cerrar: cerrar, alerta: alerta,
    ocultarAlerta: ocultarAlerta, ocupado: ocupado, invalido: invalido,
    errorBajoCampo: errorBajoCampo, limpiarErrores: limpiarErrores
  };
})();
