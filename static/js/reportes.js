/* reportes.js: pantalla /reportes (specs interfaz-web: Pantalla de reportes, Estado inicial, Selector,
   Estados, Validacion, Exportar; exportacion-pdf). Las funciones puras viven en window.Reporte y no tocan
   el DOM al cargarse; los datos se pintan solo con textContent / createElement (design D3). */
(function () {
  "use strict";

  function dos(n) { return (n < 10 ? "0" : "") + n; }
  function iso(date) { return date.getFullYear() + "-" + dos(date.getMonth() + 1) + "-" + dos(date.getDate()); }
  function vacio(texto) { return texto == null || String(texto).trim() === ""; }

  // Mes en curso: dia 1 hasta hoy (fecha local).
  function rangoPorDefecto(date) {
    return { desde: iso(new Date(date.getFullYear(), date.getMonth(), 1)), hasta: iso(date) };
  }

  // Query del reporte: `hasta` y `codigo` vacios no se envian.
  function parametros(desde, hasta, codigo) {
    var q = new URLSearchParams();
    q.set("desde", String(desde).trim());
    if (!vacio(hasta)) q.set("hasta", String(hasta).trim());
    if (!vacio(codigo)) q.set("codigo", String(codigo).trim());
    return q;
  }

  // Hasta vacio = hoy (fecha local del navegador).
  function hastaEfectivo(hasta, date) {
    return vacio(hasta) ? iso(date) : String(hasta).trim();
  }

  function porCodigo(a, b) { return a.codigo < b.codigo ? -1 : a.codigo > b.codigo ? 1 : 0; }

  // [{grupo, opciones:[{codigo, etiqueta}]}]: "Activos" y "Dados de baja", ordenados por codigo, sin grupos vacios.
  function gruposProductos(usados) {
    var grupos = [];
    [["Activos", true], ["Dados de baja", false]].forEach(function (g) {
      var opciones = usados
        .filter(function (p) { return !!p.activo === g[1]; })
        .sort(porCodigo)
        .map(function (p) { return { codigo: p.codigo, etiqueta: p.codigo + " · " + p.nombre }; });
      if (opciones.length) grupos.push({ grupo: g[0], opciones: opciones });
    });
    return grupos;
  }

  // "CODIGO · Nombre" del producto elegido ("" sin filtro; el codigo solo si no esta en la lista).
  function etiquetaProducto(codigo, grupos) {
    if (vacio(codigo)) return "";
    for (var i = 0; i < grupos.length; i++) {
      for (var j = 0; j < grupos[i].opciones.length; j++) {
        if (grupos[i].opciones[j].codigo === codigo) return grupos[i].opciones[j].etiqueta;
      }
    }
    return codigo;
  }

  // Misma linea en pantalla y en el PDF: "[CODIGO · Nombre · ]AAAA-MM-DD a AAAA-MM-DD · N productos".
  function lineaEncabezado(filas, desde, hasta, productoEtiqueta) {
    var n = filas.length;
    return (productoEtiqueta ? productoEtiqueta + " · " : "") + desde + " a " + hasta + " · " +
      n + (n === 1 ? " producto" : " productos");
  }

  function mensajeVacio(desde, hasta, productoEtiqueta) {
    var rango = "entre " + desde + " y " + hasta;
    return productoEtiqueta
      ? "«" + productoEtiqueta + "» no se usó en órdenes " + rango
      : "No hay productos usados en órdenes " + rango;
  }

  // reporte-[CODIGO-]AAAA-MM-DD_AAAA-MM-DD (el codigo se sanea como en C-06c).
  function nombreArchivo(desde, hasta, codigo) {
    var cod = vacio(codigo) ? "" : String(codigo).replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "") + "-";
    return "reporte-" + cod + desde + "_" + hasta;
  }

  window.Reporte = {
    rangoPorDefecto: rangoPorDefecto, parametros: parametros, hastaEfectivo: hastaEfectivo,
    gruposProductos: gruposProductos, etiquetaProducto: etiquetaProducto,
    lineaEncabezado: lineaEncabezado, mensajeVacio: mensajeVacio, nombreArchivo: nombreArchivo
  };

  if (typeof document === "undefined") return; // pruebas con Node: solo las funciones puras

  // ------------------------------------------------------------------ pantalla

  var Api = window.Api;
  var UI = window.UI;
  var $ = function (id) { return document.getElementById(id); };

  var grupos = [];      // productos usados, agrupados (para las etiquetas)
  var ultimo = null;    // ultimo reporte generado: {desde, hasta (efectivo), codigo, etiqueta, filas}
  var pedido = null;    // ultima consulta (para "Reintentar"): {desde, hasta, codigo}
  var generando = false;

  function mostrarEstado(estado) {
    $("rep-inicial").hidden = estado !== "inicial";
    $("rep-cargando").hidden = estado !== "cargando";
    $("rep-error").hidden = estado !== "error";
    $("rep-vacio").hidden = estado !== "vacio";
    $("rep-tabla").hidden = estado !== "datos";
    $("rep-resumen").hidden = estado !== "datos";
    $("btn-exportar-rep").disabled = estado !== "datos";
    $("btn-generar").disabled = estado === "cargando";
  }

  function estadoEstable() { return ultimo ? (ultimo.filas.length ? "datos" : "vacio") : "inicial"; }

  function llenarSelector() {
    var sel = $("r-producto");
    var elegido = sel.value;
    UI.vaciar(sel);
    sel.appendChild(UI.el("option", { value: "" }, "Todos los productos"));
    grupos.forEach(function (g) {
      var og = UI.el("optgroup", { label: g.grupo });
      g.opciones.forEach(function (o) { og.appendChild(UI.el("option", { value: o.codigo }, o.etiqueta)); });
      sel.appendChild(og);
    });
    sel.value = elegido;
  }

  function pintarTabla(filas) {
    var cuerpo = UI.vaciar($("rep-cuerpo"));
    filas.forEach(function (f) {
      var tr = UI.el("tr");
      tr.appendChild(UI.el("td", { "class": "num" }, f.codigo));
      var nombre = UI.el("td", null, f.nombre);
      if (!f.activo) nombre.appendChild(UI.el("span", { "class": "badge badge-baja bg-warning-subtle text-warning-fg" }, "dado de baja"));
      tr.appendChild(nombre);
      tr.appendChild(UI.el("td", { "class": "num r" }, String(f.cantidad)));
      tr.appendChild(UI.el("td", { "class": "num r" }, String(f.ordenes)));
      cuerpo.appendChild(tr);
    });
  }

  function pintarUltimo() {
    var r = ultimo;
    if (r.filas.length === 0) {
      $("rep-vacio-titulo").textContent = mensajeVacio(r.desde, r.hasta, r.etiqueta);
      mostrarEstado("vacio");
      return;
    }
    pintarTabla(r.filas);
    $("rep-resumen").textContent = lineaEncabezado(r.filas, r.desde, r.hasta, r.etiqueta);
    mostrarEstado("datos");
  }

  // Valida Desde obligatorio, fechas reales y rango contra el `hasta` efectivo. Devuelve true si es valido.
  function validar() {
    var form = $("form-reporte");
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("filtros-alerta"));
    var desde = $("r-desde"), hasta = $("r-hasta");
    var eDesde = Validacion.requerido(desde.value, "La fecha") || Validacion.fecha(desde.value);
    if (eDesde) { UI.errorBajoCampo(desde, eDesde); desde.focus(); return false; }
    if (!vacio(hasta.value)) {
      var eHasta = Validacion.fecha(hasta.value);
      if (eHasta) { UI.errorBajoCampo(hasta, eHasta, $("r-hasta-ayuda")); hasta.focus(); return false; }
    }
    var eRango = Validacion.rango(desde.value, hastaEfectivo(hasta.value, new Date()));
    if (eRango) {
      var campo = vacio(hasta.value) ? desde : hasta;
      UI.errorBajoCampo(campo, eRango, campo === hasta ? $("r-hasta-ayuda") : null);
      campo.focus();
      return false;
    }
    return true;
  }

  function consultar(p) {
    pedido = p;
    generando = true;
    mostrarEstado("cargando");
    var efectivo = hastaEfectivo(p.hasta, new Date());
    return Api.get("/api/reportes/productos-en-ordenes?" + parametros(p.desde, p.hasta, p.codigo).toString()).then(
      function (filas) {
        generando = false;
        ultimo = { desde: p.desde, hasta: efectivo, codigo: p.codigo, etiqueta: etiquetaProducto(p.codigo, grupos), filas: filas };
        pintarUltimo();
      },
      function (err) {
        generando = false;
        if (err.status === 422) {
          UI.alerta($("filtros-alerta"), err.detail, "error");
          if (ultimo) pintarUltimo(); else mostrarEstado("inicial");
        } else {
          $("rep-error-texto").textContent = err.detail;
          mostrarEstado("error");
        }
      }
    );
  }

  function generar(e) {
    e.preventDefault();
    if (generando || !validar()) return;
    consultar({ desde: $("r-desde").value.trim(), hasta: $("r-hasta").value.trim(), codigo: $("r-producto").value });
  }

  // Exporta el ultimo reporte generado (no los campos actuales).
  function exportar() {
    if (!ultimo || ultimo.filas.length === 0) return;
    Exportar.imprimir({
      titulo: "Reporte de productos en órdenes",
      linea: lineaEncabezado(ultimo.filas, ultimo.desde, ultimo.hasta, ultimo.etiqueta),
      archivo: nombreArchivo(ultimo.desde, ultimo.hasta, ultimo.codigo),
      modo: "reporte"
    });
  }

  function cargarProductos() {
    return Api.get("/api/reportes/productos-usados").then(
      function (usados) { grupos = gruposProductos(usados); llenarSelector(); },
      function () { /* el selector queda solo con "Todos los productos"; el reporte se genera igual */ }
    );
  }

  document.addEventListener("DOMContentLoaded", function () {
    var r = rangoPorDefecto(new Date());
    $("r-desde").value = r.desde;
    $("r-hasta").value = r.hasta;
    mostrarEstado("inicial");
    $("form-reporte").addEventListener("submit", generar);
    $("rep-reintentar").addEventListener("click", function () { if (pedido) consultar(pedido); });
    $("btn-exportar-rep").addEventListener("click", exportar);
    cargarProductos();
  });
})();
