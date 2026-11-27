/* ordenes.js: pantalla /ordenes (specs interfaz-web: Pantalla de ordenes, Estados, Borrado, Resultado).
   Datos solo con textContent / createElement (design D4). */
(function () {
  "use strict";

  const Api = window.Api;
  const UI = window.UI;

  let ordenes = [];
  let consulta = "";      // query string de los filtros aplicados
  let ordenABorrar = null;

  const $ = (id) => document.getElementById(id);
  const num = (t) => UI.el("span", { "class": "num" }, t);

  // ---------------------------------------------------------------- lista

  function mostrarEstado(estado) {
    $("ord-cargando").hidden = estado !== "cargando";
    $("ord-error").hidden = estado !== "error";
    $("ord-vacio").hidden = estado !== "vacio";
    $("ord-lista").hidden = estado !== "lista";
    $("ord-conteo").hidden = estado !== "lista";
  }

  // Importe en pesos o "—" si no tiene precio (los precios llegan de la API en centavos).
  function precioEl(centavos, extra) {
    const sin = centavos == null;
    return UI.el("span", { "class": "precio" + (sin ? " sin" : "") + (extra ? " " + extra : "") }, Precios.formatear(centavos));
  }

  // Fila de datos del cliente y la embarcacion: solo los que la orden tiene (en papel, en dos columnas).
  function filaDatos(o) {
    const campos = [
      ["cliente", "Cliente:", "Cliente:", o.cliente],
      ["celular", "Cel.:", "Celular:", o.celular],
      ["casco", "Casco:", "Casco:", o.casco],
      ["motor", "Motor:", "Motor:", o.motor],
      ["trailer", "Trailer:", "Trailer:", o.trailer],
      ["ingreso", "Ingreso:", "Ingreso:", o.fecha_ingreso],
      ["egreso", "Egreso:", "Egreso:", o.fecha_egreso]
    ];
    const datos = campos.filter((c) => c[3]);
    if (datos.length === 0) return null;
    const dl = UI.el("dl", { "class": "ord-datos", "aria-label": "Datos del cliente de " + o.numero });
    datos.forEach((c) => {
      const item = UI.el("div", { "class": "d-" + c[0] });
      const dt = UI.el("dt");
      dt.appendChild(UI.el("span", { "class": "lbl-screen" }, c[1]));
      dt.appendChild(UI.el("span", { "class": "lbl-print" }, c[2]));
      item.appendChild(dt);
      item.appendChild(UI.el("dd", { "class": c[0] === "ingreso" || c[0] === "egreso" || c[0] === "celular" ? "num" : "" }, c[3]));
      dl.appendChild(item);
    });
    return dl;
  }

  // Resumen al pie de la orden: los tres valores salen de la API (nunca se recalculan aca).
  function resumenOrden(o) {
    const pie = UI.el("div", { "class": "ord-foot" });
    const caja = UI.el("div", { "class": "resumen", "aria-label": "Resumen de precios de " + o.numero });
    const dl = UI.el("dl");
    [
      ["Subtotal servicios", o.subtotal_servicios, ""],
      ["Subtotal ítems", o.subtotal_items, ""],
      ["Total", o.total, "tot"]
    ].forEach((f) => {
      dl.appendChild(UI.el("dt", { "class": f[2] }, f[0]));
      dl.appendChild(UI.el("dd", { "class": f[2] }, Precios.formatear(f[1])));
    });
    caja.appendChild(dl);
    pie.appendChild(caja);
    return pie;
  }

  function articulo(o) {
    const art = UI.el("article", { "class": "ord", "aria-labelledby": "ord-t-" + o.id });
    const cab = UI.el("div", { "class": "ord-head" });
    cab.appendChild(UI.el("h3", { id: "ord-t-" + o.id, "class": "num font-bold" }, o.numero));
    cab.appendChild(UI.el("span", { "class": "num text-sm text-muted" }, o.fecha));
    const n = o.componentes.length;
    cab.appendChild(UI.el("span", { "class": "text-sm text-muted" }, n + (n === 1 ? " componente" : " componentes")));
    cab.appendChild(UI.el("button", {
      "class": "btn btn-secondary btn-sm ml-auto", type: "button",
      "data-exportar-orden": o.numero, "aria-label": "Exportar PDF de la orden " + o.numero
    }, "Exportar PDF"));
    cab.appendChild(UI.el("button", {
      "class": "btn btn-secondary btn-sm", type: "button",
      "data-borrar": o.numero, "aria-label": "Eliminar orden " + o.numero
    }, "Eliminar"));
    art.appendChild(cab);

    const datos = filaDatos(o);
    if (datos) art.appendChild(datos);

    // Servicio general (C-06g): solo si la orden lo tiene; va antes de la fila de procesos. En papel pasa primero
    // (tras el encabezado y antes de la tabla), como "Servicio general".
    if (o.servicio) {
      const bloqueServicio = UI.el("div", { "class": "chips chips-srv" });
      const etiquetaServicio = UI.el("span", { "class": "lbl" });
      etiquetaServicio.appendChild(UI.el("span", { "class": "lbl-screen" }, "Servicio general:"));
      etiquetaServicio.appendChild(UI.el("span", { "class": "lbl-print" }, "Servicio general"));
      bloqueServicio.appendChild(etiquetaServicio);
      const linea = UI.el("span", { "class": "srv-linea" });
      linea.appendChild(UI.el("span", { "class": "srv-nombre" }, o.servicio.nombre));
      linea.appendChild(precioEl(o.servicio.precio));
      bloqueServicio.appendChild(linea);
      const chequeos = UI.el("ul", { "aria-label": "Chequeos del servicio de " + o.numero });
      o.servicio.chequeos.forEach((c) => chequeos.appendChild(UI.el("li", { "class": "chip" }, c)));
      bloqueServicio.appendChild(chequeos);
      art.appendChild(bloqueServicio);
    }

    // Servicios adicionales (procesos, C-06f): solo si la orden tiene; en pantalla "Servicios adicionales:"
    // + chips con su precio, en papel "Servicios adicionales" (uno por linea, precio a la derecha).
    if (o.procesos && o.procesos.length > 0) {
      const bloque = UI.el("div", { "class": "chips" });
      const etiqueta = UI.el("span", { "class": "lbl" });
      etiqueta.appendChild(UI.el("span", { "class": "lbl-screen" }, "Servicios adicionales:"));
      etiqueta.appendChild(UI.el("span", { "class": "lbl-print" }, "Servicios adicionales"));
      bloque.appendChild(etiqueta);
      const lista = UI.el("ul", { "aria-label": "Servicios adicionales de " + o.numero });
      o.procesos.forEach((p) => {
        const chip = UI.el("li", { "class": "chip" }, p.nombre);
        chip.appendChild(UI.el("span", { "class": "sep", "aria-hidden": "true" }, " · "));
        chip.appendChild(precioEl(p.precio));
        lista.appendChild(chip);
      });
      bloque.appendChild(lista);
      art.appendChild(bloque);
    }

    const region = UI.el("div", {
      "class": "overflow-x-auto", tabindex: "0", role: "region", "aria-label": "Componentes de " + o.numero
    });
    const tabla = UI.el("table", { "class": "tbl tbl-fit tbl-comp" });
    const fila = UI.el("tr");
    fila.appendChild(UI.el("th", { scope: "col" }, "Código"));
    fila.appendChild(UI.el("th", { scope: "col" }, "Nombre"));
    fila.appendChild(UI.el("th", { scope: "col", "class": "r" }, "Cantidad"));
    fila.appendChild(UI.el("th", { scope: "col", "class": "r" }, "Importe"));
    tabla.appendChild(UI.el("thead")).appendChild(fila);
    const cuerpo = UI.el("tbody");
    o.componentes.forEach((c) => {
      const tr = UI.el("tr");
      tr.appendChild(UI.el("td", { "class": "num" }, c.codigo));
      tr.appendChild(UI.el("td", null, c.nombre));
      tr.appendChild(UI.el("td", { "class": "num r" }, String(c.cantidad)));
      tr.appendChild(UI.el("td", { "class": "num r" + (c.precio == null ? " text-muted" : "") }, Precios.formatear(c.precio)));
      cuerpo.appendChild(tr);
    });
    tabla.appendChild(cuerpo);
    region.appendChild(tabla);
    art.appendChild(region);
    art.appendChild(resumenOrden(o));
    return art;
  }

  function pintarLista() {
    if (ordenes.length === 0) {
      cartel(
        consulta ? "No hay órdenes en ese período" : "No hay órdenes",
        consulta ? "Probá con otras fechas o elegí \"Ver todas\"." : "Las órdenes que crees desde Inventario aparecen acá."
      );
      return;
    }
    const lista = UI.vaciar($("ord-lista"));
    ordenes.forEach((o) => lista.appendChild(articulo(o)));
    $("ord-conteo").textContent = ordenes.length + (ordenes.length === 1 ? " orden" : " órdenes");
    mostrarEstado("lista");
  }

  function cartel(titulo, ayuda) {
    $("ord-vacio-titulo").textContent = titulo;
    $("ord-vacio-ayuda").textContent = ayuda;
    mostrarEstado("vacio");
  }

  function cargar(conSpinner) {
    if (conSpinner) mostrarEstado("cargando");
    return Api.get("/api/ordenes" + consulta).then(
      (lista) => { ordenes = lista; pintarLista(); },
      (err) => {
        ordenes = [];
        if (err.status === 404) {
          cartel(err.detail, "Revisá el número o elegí \"Ver todas\".");
        } else if (err.status === 422) {
          UI.alerta($("filtros-alerta"), err.detail, "error");
          UI.invalido($("f-desde"), "filtros-alerta");
          UI.invalido($("f-hasta"), "filtros-alerta");
          mostrarEstado("vacio");
          cartel("No se pudo listar las órdenes", "Corregí los filtros e intentá de nuevo.");
        } else {
          $("ord-error-texto").textContent = err.detail;
          mostrarEstado("error");
        }
      }
    );
  }

  // ---------------------------------------------------------------- exportar una orden

  // Exporta solo esa orden: la marca (data-exportar) deja visible su <article> en la hoja de impresion.
  function exportarOrden(numero) {
    const o = ordenes.find((x) => x.numero === numero);
    if (!o) return;
    const articulo = Array.from($("ord-lista").querySelectorAll("article.ord"))
      .find((a) => a.getAttribute("aria-labelledby") === "ord-t-" + o.id);
    if (!articulo) return;
    const n = o.componentes.length;
    articulo.setAttribute("data-exportar", "");
    Exportar.imprimir({
      titulo: "Orden " + o.numero,
      linea: "Fecha: " + o.fecha + " · " + n + (n === 1 ? " componente" : " componentes"),
      base: "orden-" + o.numero,
      modo: "orden",
      alRestaurar: () => { articulo.removeAttribute("data-exportar"); }
    });
  }

  // ---------------------------------------------------------------- filtros

  function validarFiltros(form) {
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("filtros-alerta"));
    const desde = $("f-desde"), hasta = $("f-hasta"), numero = $("f-numero");
    let primero = null;
    [desde, hasta].forEach((campo) => {
      const e = campo.value.trim() === "" ? null : Validacion.fecha(campo.value);
      if (e) { UI.errorBajoCampo(campo, e); primero = primero || campo; }
    });
    const eRango = primero ? null : Validacion.rango(desde.value, hasta.value);
    if (eRango) {
      UI.errorBajoCampo(hasta, eRango);
      UI.invalido(desde, hasta.id + "-e");
      primero = desde;
    }
    const eNumero = Validacion.largo(numero.value, 30, "El número");
    if (eNumero) { UI.errorBajoCampo(numero, eNumero); primero = primero || numero; }
    if (primero) primero.focus();
    return primero === null;
  }

  function armarConsulta() {
    const p = new URLSearchParams();
    const desde = $("f-desde").value.trim(), hasta = $("f-hasta").value.trim(), numero = $("f-numero").value.trim();
    if (desde !== "") p.set("desde", desde);
    if (hasta !== "") p.set("hasta", hasta);
    if (numero !== "") p.set("numero", numero);
    const s = p.toString();
    return s === "" ? "" : "?" + s;
  }

  function filtrar(e) {
    e.preventDefault();
    ocultarExito();
    if (!validarFiltros($("form-filtros"))) return;
    consulta = armarConsulta();
    cargar(true);
  }

  function verTodas() {
    ocultarExito();
    const form = $("form-filtros");
    form.reset();
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("filtros-alerta"));
    consulta = "";
    cargar(true);
  }

  // ---------------------------------------------------------------- aviso de exito

  function ocultarExito() {
    UI.vaciar($("aviso-exito"));
    $("aviso-exito").hidden = true;
  }

  function mostrarResumen(numero, resultado) {
    const caja = UI.vaciar($("aviso-exito"));
    const cuerpo = UI.el("div", { "class": "flex-1 py-2" });
    const p = UI.el("p");
    const fuerte = UI.el("strong");
    fuerte.appendChild(document.createTextNode("Orden "));
    fuerte.appendChild(num(numero));
    if (resultado.reintegrado) {
      fuerte.appendChild(document.createTextNode(" borrada."));
      p.appendChild(fuerte);
      p.appendChild(document.createTextNode(" Stock devuelto:"));
      cuerpo.appendChild(p);
      const ul = UI.el("ul", { "class": "mt-1 space-y-0.5 list-disc pl-5" });
      resultado.reintegros.forEach((r) => {
        const li = UI.el("li");
        li.appendChild(num(r.codigo));
        li.appendChild(document.createTextNode(" +" + r.cantidad + " (stock " + r.stock));
        if (r.reactivado) {
          li.appendChild(document.createTextNode(", "));
          li.appendChild(UI.el("strong", null, "reactivado"));
        }
        li.appendChild(document.createTextNode(")"));
        ul.appendChild(li);
      });
      cuerpo.appendChild(ul);
    } else {
      fuerte.appendChild(document.createTextNode(" borrada sin devolver stock."));
      p.appendChild(fuerte);
      cuerpo.appendChild(p);
    }
    caja.appendChild(cuerpo);
    const cerrar = UI.el("button", { "class": "icon-btn", type: "button", "aria-label": "Cerrar aviso" }, "×");
    cerrar.addEventListener("click", ocultarExito);
    caja.appendChild(cerrar);
    caja.hidden = false;
  }

  // ---------------------------------------------------------------- borrar orden

  function textoBoton() {
    return $("del-devolver").checked ? "Borrar y devolver stock" : "Borrar sin devolver stock";
  }

  function actualizarOpcion() {
    const marcada = $("del-devolver").checked;
    $("del-confirmar").textContent = textoBoton();
    $("del-ayuda").textContent = marcada
      ? "Los componentes vuelven al inventario. Si un producto estaba dado de baja, se reactiva."
      : "El stock no cambia: los componentes no vuelven al inventario.";
  }

  function abrirBorrar(numero) {
    const o = ordenes.find((x) => x.numero === numero);
    if (!o) return;
    ocultarExito();
    ordenABorrar = o;
    UI.ocultarAlerta($("del-alerta"));
    $("del-nota").hidden = true;
    $("del-desc").hidden = false;
    $("del-opcion").hidden = false;
    $("del-devolver").checked = true;
    $("del-confirmar").hidden = false;
    $("del-cancelar").textContent = "Cancelar";
    const n = o.componentes.length;
    const desc = UI.vaciar($("del-desc"));
    desc.appendChild(document.createTextNode("Se borrará la orden "));
    desc.appendChild(UI.el("strong", { "class": "num" }, o.numero));
    desc.appendChild(document.createTextNode(
      " (" + o.fecha + ", " + n + (n === 1 ? " componente" : " componentes") + "). Esta acción no se puede deshacer."
    ));
    actualizarOpcion();
    UI.abrir($("modal-borrar"));
  }

  function confirmarBorrado() {
    const boton = $("del-confirmar"), alerta = $("del-alerta");
    if (boton.disabled || !ordenABorrar) return;
    const numero = ordenABorrar.numero;
    const reintegrar = $("del-devolver").checked;
    UI.ocultarAlerta(alerta);
    const restaurar = UI.ocupado(boton, "Borrando…");
    const url = "/api/ordenes/" + encodeURIComponent(numero) + "?reintegrar=" + (reintegrar ? "true" : "false");
    Api.borrar(url).then(
      (resultado) => {
        restaurar();
        UI.cerrar();
        ordenes = ordenes.filter((o) => o.numero !== numero);
        pintarLista();
        mostrarResumen(numero, resultado);
      },
      (err) => {
        restaurar();
        UI.alerta(alerta, err.detail, "error");
        if (err.status === 404) {
          $("del-desc").hidden = true;
          $("del-opcion").hidden = true;
          $("del-nota").hidden = false;
          $("del-confirmar").hidden = true;
          $("del-cancelar").textContent = "Cerrar";
          $("del-cancelar").focus();
          cargar(false);
        }
      }
    );
  }

  // ---------------------------------------------------------------- arranque

  document.addEventListener("DOMContentLoaded", () => {
    $("form-filtros").addEventListener("submit", filtrar);
    $("f-limpiar").addEventListener("click", verTodas);
    $("ord-reintentar").addEventListener("click", () => cargar(true));
    $("ord-lista").addEventListener("click", (e) => {
      const x = e.target.closest("[data-exportar-orden]");
      if (x) { exportarOrden(x.getAttribute("data-exportar-orden")); return; }
      const b = e.target.closest("[data-borrar]");
      if (b) abrirBorrar(b.getAttribute("data-borrar"));
    });
    $("del-devolver").addEventListener("change", actualizarOpcion);
    $("del-confirmar").addEventListener("click", confirmarBorrado);
    cargar(true);
  });
})();
