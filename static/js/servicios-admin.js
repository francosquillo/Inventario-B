/* servicios-admin.js: modal "Servicios generales" de /ordenes (specs interfaz-web: Catalogo de servicios
   generales en la web, Formulario, Validacion, Borrado; design D12). Un solo modal con tres vistas
   (lista, formulario y confirmacion de borrado). Datos solo con textContent / createElement (design D4). */
(function () {
  "use strict";

  const Api = window.Api;
  const UI = window.UI;
  const URL_SERVICIOS = "/api/servicios-generales";
  const CLASE_EXITO = "flex items-start gap-2 py-1 px-3 rounded-md border border-success bg-success-subtle text-success-fg text-sm";

  let catalogo = [];        // [{clave, nombre, chequeos}] ordenado por nombre
  let claveEditada = null;  // clave del servicio en el formulario (null = nuevo)
  let aBorrar = null;       // servicio de la confirmacion de borrado
  let secuencia = 0;        // ids unicos de las lineas de chequeo

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- vistas

  function mostrarVista(id, titulo) {
    ["srv-vista-lista", "srv-vista-form", "srv-vista-borrar"].forEach((v) => { $(v).hidden = v !== id; });
    $(titulo).focus();
  }

  function aviso(texto, tipo) {
    const caja = $("srv-exito");
    if (!texto) { UI.vaciar(caja); caja.hidden = true; return; }
    if (tipo === "error") {
      UI.alerta(caja, texto, "error");
    } else {
      UI.vaciar(caja);
      caja.className = CLASE_EXITO;
      caja.setAttribute("role", "status");
      caja.textContent = texto;
      caja.hidden = false;
    }
  }

  // ---------------------------------------------------------------- lista

  function estadoLista(estado) {
    $("srv-cargando").hidden = estado !== "cargando";
    $("srv-error").hidden = estado !== "error";
    $("srv-contenido").hidden = estado !== "lista";
  }

  function tarjeta(s) {
    const li = UI.el("li", { "class": "srv-card" });
    const cab = UI.el("div", { "class": "srv-card-head" });
    cab.appendChild(UI.el("h3", null, s.nombre));
    const editar = UI.el("button", {
      "class": "btn btn-secondary btn-sm", type: "button", "aria-label": "Editar " + s.nombre
    }, "Editar");
    editar.addEventListener("click", () => abrirFormulario(s));
    const eliminar = UI.el("button", {
      "class": "btn btn-secondary btn-sm", type: "button", "aria-label": "Eliminar " + s.nombre
    }, "Eliminar");
    eliminar.addEventListener("click", () => abrirBorrado(s));
    cab.appendChild(editar);
    cab.appendChild(eliminar);
    li.appendChild(cab);
    const chips = UI.el("div", { "class": "chips" });
    const ul = UI.el("ul", { "aria-label": "Chequeos de " + s.nombre });
    s.chequeos.forEach((c) => ul.appendChild(UI.el("li", { "class": "chip" }, c)));
    chips.appendChild(ul);
    li.appendChild(chips);
    return li;
  }

  function pintarLista() {
    const n = catalogo.length;
    $("srv-conteo").textContent = n === 0
      ? ""
      : n + (n === 1 ? " servicio" : " servicios") + ". Las órdenes ya creadas conservan el servicio como estaba.";
    $("srv-vacio").hidden = n !== 0;
    const lista = UI.vaciar($("srv-lista"));
    lista.hidden = n === 0;
    catalogo.forEach((s) => lista.appendChild(tarjeta(s)));
    estadoLista("lista");
  }

  function cargarLista(conSpinner) {
    if (conSpinner) estadoLista("cargando");
    return Api.get(URL_SERVICIOS).then(
      (lista) => { catalogo = lista; pintarLista(); },
      (err) => {
        catalogo = [];
        $("srv-error-texto").textContent = err.detail;
        estadoLista("error");
      }
    );
  }

  function abrir() {
    aviso("");
    mostrarVista("srv-vista-lista", "srv-titulo-lista");
    UI.abrir($("modal-servicios"));
    $("srv-titulo-lista").focus();
    cargarLista(true);
  }

  function volverALista(mensaje, tipo) {
    mostrarVista("srv-vista-lista", "srv-titulo-lista");
    aviso(mensaje, tipo);
    return cargarLista(false);
  }

  // ---------------------------------------------------------------- formulario

  function lineas() {
    return Array.from($("srv-chequeos").children);
  }

  function cajaChequeo(li) { return li.querySelector("input"); }

  function renumerar() {
    const filas = lineas();
    const unica = filas.length === 1;
    filas.forEach((li, i) => {
      li.querySelector(".line-n").textContent = String(i + 1);
      cajaChequeo(li).setAttribute("aria-label", "Chequeo " + (i + 1));
      const quitar = li.querySelector("button");
      quitar.setAttribute("aria-label", "Quitar chequeo " + (i + 1));
      quitar.disabled = unica;
    });
    const lleno = filas.length >= Servicios.CHEQUEOS_MAX;
    $("srv-agregar").disabled = lleno;
    $("srv-max").hidden = !lleno;
    $("srv-contador").textContent = filas.length + " de " + Servicios.CHEQUEOS_MAX + " chequeos";
  }

  function nuevaLinea(texto) {
    secuencia += 1;
    const li = UI.el("li", { "data-k": String(secuencia) });
    const fila = UI.el("div", { "class": "cline" });
    fila.appendChild(UI.el("span", { "class": "line-n", "aria-hidden": "true" }, ""));
    const caja = UI.el("input", {
      "class": "field", id: "srv-c-" + secuencia, maxlength: String(Servicios.CHEQUEO_MAX), autocomplete: "off"
    });
    caja.value = texto || "";
    fila.appendChild(caja);
    fila.appendChild(UI.el("button", { "class": "btn btn-secondary", type: "button", "data-quitar": true }, "Quitar"));
    li.appendChild(fila);
    return li;
  }

  function agregarLinea() {
    if (lineas().length >= Servicios.CHEQUEOS_MAX) return;
    const li = nuevaLinea("");
    $("srv-chequeos").appendChild(li);
    renumerar();
    cajaChequeo(li).focus();
  }

  function quitarLinea(li) {
    const filas = lineas();
    if (filas.length <= 1) return;
    const i = filas.indexOf(li);
    li.remove();
    renumerar();
    const resto = lineas();
    cajaChequeo(resto[Math.min(i, resto.length - 1)]).focus();
  }

  function limpiarErroresForm() {
    UI.limpiarErrores($("srv-vista-form"));
    UI.ocultarAlerta($("srv-form-alerta"));
    const general = $("srv-chequeos-e");
    general.textContent = "";
    general.hidden = true;
  }

  function marcarCampo(campo, id) {
    campo.setAttribute("aria-invalid", "true");
    campo.setAttribute("aria-describedby", id);
  }

  function errorChequeo(li, mensaje) {
    const caja = cajaChequeo(li);
    const id = "srv-ce-" + li.getAttribute("data-k");
    const previo = document.getElementById(id);
    if (previo) previo.remove();
    li.appendChild(UI.el("p", { "class": "err cline-err", id: id, role: "alert", "data-error": true }, mensaje));
    marcarCampo(caja, id);
    return caja;
  }

  function errorGeneral(mensaje) {
    const p = $("srv-chequeos-e");
    p.textContent = mensaje;
    p.hidden = false;
  }

  function abrirFormulario(servicio) {
    claveEditada = servicio ? servicio.clave : null;
    limpiarErroresForm();
    $("srv-titulo-form").textContent = servicio ? "Editar servicio general" : "Nuevo servicio general";
    $("srv-nombre").value = servicio ? servicio.nombre : "";
    const lista = UI.vaciar($("srv-chequeos"));
    (servicio ? servicio.chequeos : [""]).forEach((c) => lista.appendChild(nuevaLinea(c)));
    renumerar();
    mostrarVista("srv-vista-form", "srv-titulo-form");
  }

  function leerFormulario() {
    return { nombre: $("srv-nombre").value, chequeos: lineas().map((li) => cajaChequeo(li).value) };
  }

  function validarFormulario() {
    limpiarErroresForm();
    const v = Servicios.validarFormulario(leerFormulario(), catalogo, claveEditada);
    let primero = null;
    if (v.errores.nombre) {
      UI.errorBajoCampo($("srv-nombre"), v.errores.nombre);
      primero = $("srv-nombre");
    }
    if (v.errores.general) {
      errorGeneral(v.errores.general);
      primero = primero || $("srv-agregar");
    }
    lineas().forEach((li, i) => {
      const e = v.errores.chequeos[i];
      if (!e) return;
      const campo = errorChequeo(li, e);
      primero = primero || campo;
    });
    if (primero) primero.focus();
    return primero === null ? v : null;
  }

  function mapearErrorFormulario(err) {
    const alerta = $("srv-form-alerta");
    let foco = null;
    const chequeo = err.status === 422 ? /^Chequeo (\d+):\s*(.*)$/.exec(err.detail) : null;
    if (err.status === 404) {
      volverALista(err.detail, "error");
      return;
    } else if (err.status === 409) {
      foco = $("srv-nombre");
      UI.errorBajoCampo(foco, err.detail);
    } else if (chequeo && lineas()[Number(chequeo[1]) - 1]) {
      foco = errorChequeo(lineas()[Number(chequeo[1]) - 1], chequeo[2]);
    } else if (err.status === 422 && /nombre/i.test(err.detail)) {
      foco = $("srv-nombre");
      UI.errorBajoCampo(foco, err.detail);
    } else {
      UI.alerta(alerta, err.detail, "error");
    }
    if (foco) foco.focus();
  }

  function guardar(e) {
    e.preventDefault();
    const boton = $("srv-guardar");
    if (boton.disabled) return;
    const v = validarFormulario();
    if (!v) return;
    const cuerpo = { nombre: v.nombre, chequeos: v.chequeos };
    const restaurar = UI.ocupado(boton, "Guardando…");
    const pedido = claveEditada === null
      ? Api.post(URL_SERVICIOS, cuerpo)
      : Api.pedir("PATCH", URL_SERVICIOS + "/" + encodeURIComponent(claveEditada), cuerpo);
    pedido.then(
      (guardado) => {
        restaurar();
        volverALista("Servicio general " + guardado.nombre + " guardado.", "exito");
      },
      (err) => {
        restaurar();
        mapearErrorFormulario(err);
      }
    );
  }

  // ---------------------------------------------------------------- borrado

  function abrirBorrado(servicio) {
    aBorrar = servicio;
    UI.ocultarAlerta($("srv-borrar-alerta"));
    const desc = UI.vaciar($("srv-borrar-desc"));
    desc.appendChild(document.createTextNode("¿Eliminar el servicio general "));
    desc.appendChild(UI.el("strong", null, servicio.nombre));
    desc.appendChild(document.createTextNode("? Las órdenes que ya lo tienen lo conservan."));
    mostrarVista("srv-vista-borrar", "srv-titulo-borrar");
  }

  function confirmarBorrado() {
    const boton = $("srv-eliminar-confirmar");
    if (boton.disabled || !aBorrar) return;
    const servicio = aBorrar;
    UI.ocultarAlerta($("srv-borrar-alerta"));
    const restaurar = UI.ocupado(boton, "Eliminando…");
    Api.borrar(URL_SERVICIOS + "/" + encodeURIComponent(servicio.clave)).then(
      () => {
        restaurar();
        aBorrar = null;
        volverALista("Servicio general " + servicio.nombre + " eliminado.", "exito");
      },
      (err) => {
        restaurar();
        if (err.status === 404) {
          aBorrar = null;
          volverALista(err.detail, "error");
        } else {
          UI.alerta($("srv-borrar-alerta"), err.detail, "error");
        }
      }
    );
  }

  // ---------------------------------------------------------------- arranque

  document.addEventListener("DOMContentLoaded", () => {
    $("btn-servicios").addEventListener("click", abrir);
    $("srv-reintentar").addEventListener("click", () => cargarLista(true));
    $("srv-nuevo").addEventListener("click", () => abrirFormulario(null));
    $("srv-agregar").addEventListener("click", agregarLinea);
    $("srv-chequeos").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar]");
      if (q) quitarLinea(q.closest("li"));
    });
    $("srv-volver").addEventListener("click", () => {
      mostrarVista("srv-vista-lista", "srv-titulo-lista");
      aviso("");
    });
    $("srv-vista-form").addEventListener("submit", guardar);
    $("srv-eliminar-cancelar").addEventListener("click", () => {
      aBorrar = null;
      mostrarVista("srv-vista-lista", "srv-titulo-lista");
    });
    $("srv-eliminar-confirmar").addEventListener("click", confirmarBorrado);
  });
})();
