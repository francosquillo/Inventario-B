/* exportar.js: exportar a PDF con el dialogo de impresion del navegador (spec exportacion-pdf).
   Reutilizable por cualquier pagina; las funciones puras no tocan el DOM al cargarse. */
(function () {
  "use strict";

  function dos(n) { return (n < 10 ? "0" : "") + n; }

  // Fecha local AAAA-MM-DD.
  function fecha(date) {
    return date.getFullYear() + "-" + dos(date.getMonth() + 1) + "-" + dos(date.getDate());
  }

  // base + "-" + fecha; todo caracter fuera de [A-Za-z0-9] se vuelve "-" (repetidos colapsados, sin "-" en los bordes de la base).
  function nombreArchivo(base, date) {
    var limpia = String(base).replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    return limpia + "-" + fecha(date);
  }

  // Llena el encabezado de la hoja (#print-head: titulo y una linea, solo con textContent).
  function llenarEncabezado(titulo, linea) {
    var cab = document.getElementById("print-head");
    if (!cab) return;
    cab.textContent = "";
    var h = document.createElement("h1");
    h.textContent = titulo;
    var p = document.createElement("p");
    p.textContent = linea;
    cab.appendChild(h);
    cab.appendChild(p);
  }

  // opciones: { titulo, linea, base, modo, alRestaurar }. Abre el dialogo de impresion ("Guardar como PDF").
  function imprimir(opciones) {
    var body = document.body;
    var tituloOriginal = document.title;
    llenarEncabezado(opciones.titulo, opciones.linea);
    body.setAttribute("data-exportando", opciones.modo);
    document.title = nombreArchivo(opciones.base, new Date());

    var hecho = false;
    var consulta = window.matchMedia ? window.matchMedia("print") : null;
    function restaurar() {
      if (hecho) return;
      hecho = true;
      window.removeEventListener("afterprint", restaurar);
      if (consulta && consulta.removeEventListener) consulta.removeEventListener("change", alCambiar);
      document.title = tituloOriginal;
      body.removeAttribute("data-exportando");
      var cab = document.getElementById("print-head");
      if (cab) cab.textContent = "";
      if (opciones.alRestaurar) opciones.alRestaurar();
    }
    function alCambiar(e) { if (!e.matches) restaurar(); }

    window.addEventListener("afterprint", restaurar);
    if (consulta && consulta.addEventListener) consulta.addEventListener("change", alCambiar);
    window.print();
  }

  window.Exportar = { fecha: fecha, nombreArchivo: nombreArchivo, imprimir: imprimir };
})();
