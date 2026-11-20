/* inventario.js: pantalla /inventario (specs interfaz-web: Tabla, Ingreso, Egreso, Nueva orden,
   Errores por linea, Baja de producto). Datos solo con textContent / createElement (design D4). */
(function () {
  "use strict";

  const Api = window.Api;
  const UI = window.UI;
  const MAX_LINEAS = 100;
  const MENOS = "−";

  let productos = [];
  let bajaActual = null;

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- lista

  function mostrarEstado(estado) {
    $("inv-cargando").hidden = estado !== "cargando";
    $("inv-error").hidden = estado !== "error";
    $("inv-tabla").hidden = estado !== "datos";
    $("inv-conteo").hidden = estado !== "datos";
    $("inv-vacio").hidden = estado !== "vacio";
    $("inv-panel").hidden = estado === "vacio";
  }

  function textoStock(p) {
    const celda = UI.el("td", { "class": "num r" });
    if (p.sin_stock) {
      const badge = UI.el("span", { "class": "badge bg-warning-subtle text-warning-fg" }, String(p.stock));
      badge.appendChild(UI.el("span", { "class": "sr-only" }, ", sin stock"));
      celda.appendChild(badge);
    } else {
      celda.textContent = String(p.stock);
    }
    return celda;
  }

  function pintarTabla() {
    const cuerpo = UI.vaciar($("inv-cuerpo"));
    productos.forEach((p) => {
      const fila = UI.el("tr");
      fila.appendChild(UI.el("td", { "class": "num" }, p.codigo));
      fila.appendChild(UI.el("td", null, p.nombre));
      fila.appendChild(textoStock(p));
      const accion = UI.el("td", { "class": "r" });
      accion.appendChild(UI.el("button", {
        "class": "btn btn-secondary btn-sm", type: "button", "data-baja": p.codigo,
        "aria-label": "Eliminar " + p.codigo
      }, "Eliminar"));
      fila.appendChild(accion);
      cuerpo.appendChild(fila);
    });
    $("inv-conteo").textContent = productos.length + (productos.length === 1 ? " producto" : " productos");
  }

  function pintarCodigos() {
    const lista = UI.vaciar($("dl-codigos"));
    productos.forEach((p) => {
      const o = UI.el("option", { value: p.codigo });
      o.textContent = p.nombre;
      lista.appendChild(o);
    });
  }

  function etiquetaProducto(p) {
    return p.codigo + " · " + p.nombre + " (stock " + p.stock + ")";
  }

  // Llena un <select> con los productos activos. `conservar`: si el valor previo ya no esta, se deja visible.
  function llenarSelect(select, conservar) {
    const previo = select.value;
    UI.vaciar(select);
    select.appendChild(UI.el("option", { value: "" }, "Elegí un producto…"));
    productos.forEach((p) => select.appendChild(UI.el("option", { value: p.codigo }, etiquetaProducto(p))));
    if (previo && productos.some((p) => p.codigo === previo)) {
      select.value = previo;
    } else if (previo && conservar) {
      select.appendChild(UI.el("option", { value: previo }, previo + " · (ya no está activo)"));
      select.value = previo;
    }
  }

  function refrescarSelects(conservar) {
    llenarSelect($("egr-producto"), false);
    actualizarAyudaEgreso();
    document.querySelectorAll("#ord-lineas select").forEach((s) => llenarSelect(s, conservar));
  }

  function aplicarProductos(lista) {
    productos = lista;
    pintarCodigos();
    if (productos.length === 0) {
      mostrarEstado("vacio");
    } else {
      pintarTabla();
      mostrarEstado("datos");
    }
  }

  function cargar(conSpinner) {
    if (conSpinner) mostrarEstado("cargando");
    return Api.get("/api/inventario").then(
      (lista) => { aplicarProductos(lista); },
      (err) => {
        $("inv-error-texto").textContent = err.detail;
        mostrarEstado("error");
      }
    );
  }

  // ---------------------------------------------------------------- aviso de exito

  function ocultarExito() {
    const caja = $("aviso-exito");
    UI.vaciar(caja);
    caja.hidden = true;
  }

  // partes: lista de strings o nodos; se antepone "Listo.".
  function mostrarExito(partes) {
    const caja = UI.vaciar($("aviso-exito"));
    const p = UI.el("p", { "class": "flex-1 py-2" });
    p.appendChild(UI.el("strong", null, "Listo."));
    p.appendChild(document.createTextNode(" "));
    partes.forEach((parte) => {
      p.appendChild(typeof parte === "string" ? document.createTextNode(parte) : parte);
    });
    caja.appendChild(p);
    const cerrar = UI.el("button", { "class": "icon-btn", type: "button", "aria-label": "Cerrar aviso" }, "×");
    cerrar.addEventListener("click", ocultarExito);
    caja.appendChild(cerrar);
    caja.hidden = false;
  }

  const num = (t) => UI.el("span", { "class": "num" }, t);

  // ---------------------------------------------------------------- ingreso

  function hintCodigoNuevo() {
    const codigo = $("ing-codigo").value.trim();
    const nuevo = codigo !== "" && !productos.some((p) => p.codigo === codigo);
    $("ing-aviso").hidden = !nuevo;
  }

  function abrirIngreso() {
    ocultarExito();
    const form = $("form-ingreso");
    form.reset();
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("ing-alerta"));
    $("ing-aviso").hidden = true;
    UI.abrir($("modal-ingreso"));
  }

  function validarIngreso(form) {
    UI.limpiarErrores(form);
    const codigo = $("ing-codigo"), nombre = $("ing-nombre"), cantidad = $("ing-cantidad");
    const errores = [
      [codigo, Validacion.requerido(codigo.value, "El código") || Validacion.largo(codigo.value, 50, "El código")],
      [nombre, Validacion.largo(nombre.value, 120, "El nombre")],
      [cantidad, Validacion.cantidad(cantidad.value)]
    ].filter((e) => e[1]);
    errores.forEach((e) => UI.errorBajoCampo(e[0], e[1]));
    if (errores.length) errores[0][0].focus();
    return errores.length === 0;
  }

  function enviarIngreso(e) {
    e.preventDefault();
    const form = $("form-ingreso"), boton = $("ing-enviar"), alerta = $("ing-alerta");
    if (boton.disabled) return;
    UI.ocultarAlerta(alerta);
    if (!validarIngreso(form)) return;
    const cuerpo = { codigo: $("ing-codigo").value.trim(), cantidad: Number($("ing-cantidad").value.trim()) };
    const nombre = $("ing-nombre").value.trim();
    if (nombre !== "") cuerpo.nombre = nombre;
    const restaurar = UI.ocupado(boton, "Registrando…");
    Api.post("/api/stock/ingreso", cuerpo).then(
      (r) => {
        restaurar();
        UI.cerrar();
        const partes = ["Ingreso registrado: ", num(r.codigo), " +" + cuerpo.cantidad + " (stock " + r.stock + ")."];
        if (r.creado) partes.push(" Producto creado.");
        else if (r.reactivado) partes.push(" Producto reactivado.");
        mostrarExito(partes);
        cargar(false);
      },
      (err) => {
        restaurar();
        UI.alerta(alerta, err.detail, "error");
        alerta.id = "ing-alerta";
        if (err.status === 422 && /indicá un nombre para crearlo/.test(err.detail)) {
          UI.invalido($("ing-nombre"), "ing-alerta");
          $("ing-nombre").focus();
        }
      }
    );
  }

  // ---------------------------------------------------------------- egreso

  function actualizarAyudaEgreso() {
    const ayuda = $("egr-ayuda");
    const p = productos.find((x) => x.codigo === $("egr-producto").value);
    UI.vaciar(ayuda);
    if (p) {
      ayuda.appendChild(document.createTextNode("Stock actual: "));
      ayuda.appendChild(num(String(p.stock)));
    } else {
      ayuda.textContent = "Elegí un producto para ver su stock.";
    }
  }

  function abrirEgreso() {
    ocultarExito();
    const form = $("form-egreso");
    form.reset();
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("egr-alerta"));
    llenarSelect($("egr-producto"), false);
    actualizarAyudaEgreso();
    UI.abrir($("modal-egreso"));
  }

  function validarEgreso(form) {
    UI.limpiarErrores(form);
    const producto = $("egr-producto"), cantidad = $("egr-cantidad");
    const errores = [
      [producto, Validacion.requerido(producto.value, "El producto")],
      [cantidad, Validacion.cantidad(cantidad.value)]
    ].filter((e) => e[1]);
    errores.forEach((e) => UI.errorBajoCampo(e[0], e[1]));
    if (errores.length) errores[0][0].focus();
    return errores.length === 0;
  }

  function enviarEgreso(e) {
    e.preventDefault();
    const form = $("form-egreso"), boton = $("egr-enviar"), alerta = $("egr-alerta");
    if (boton.disabled) return;
    UI.ocultarAlerta(alerta);
    if (!validarEgreso(form)) return;
    const cuerpo = { codigo: $("egr-producto").value, cantidad: Number($("egr-cantidad").value.trim()) };
    const restaurar = UI.ocupado(boton, "Registrando…");
    Api.post("/api/stock/egreso", cuerpo).then(
      (r) => {
        restaurar();
        UI.cerrar();
        mostrarExito(["Egreso registrado: ", num(r.codigo), " " + MENOS + cuerpo.cantidad + " (stock " + r.stock + ")."]);
        cargar(false);
      },
      (err) => {
        restaurar();
        UI.alerta(alerta, err.detail, "error");
        if (err.status === 404) {
          cargar(false).then(() => {
            refrescarSelects(false);
            $("egr-ayuda").textContent = "La lista de productos se actualizó.";
            $("egr-producto").focus();
          });
        }
      }
    );
  }

  // ---------------------------------------------------------------- nueva orden

  function lineas() {
    return Array.from(document.querySelectorAll("#ord-lineas > li"));
  }

  function limpiarMarcaLinea(li) {
    li.removeAttribute("data-invalid");
    li.querySelectorAll("[data-error]").forEach((n) => n.remove());
    li.querySelectorAll("[aria-invalid]").forEach((c) => { c.removeAttribute("aria-invalid"); c.removeAttribute("aria-describedby"); });
  }

  function marcarLinea(li, campo, mensaje, comoAlerta) {
    li.setAttribute("data-invalid", "");
    const idx = lineas().indexOf(li) + 1;
    const id = "ord-l" + idx + (campo.tagName === "SELECT" ? "-p" : "-c") + "-e";
    const previo = document.getElementById(id);
    if (previo) previo.remove();
    const attrs = { "class": "err line-err", id: id, "data-error": true };
    if (comoAlerta) attrs.role = "alert";
    li.appendChild(UI.el("p", attrs, mensaje));
    UI.invalido(campo, id);
  }

  function renumerar() {
    const filas = lineas();
    filas.forEach((li, i) => {
      const n = i + 1;
      li.querySelector(".line-n").textContent = String(n);
      li.querySelector("select").setAttribute("aria-label", "Producto del componente " + n);
      li.querySelector("input").setAttribute("aria-label", "Cantidad del componente " + n);
      const quitar = li.querySelector("[data-quitar]");
      quitar.setAttribute("aria-label", "Quitar componente " + n);
      quitar.disabled = filas.length === 1;
    });
    const lleno = filas.length >= MAX_LINEAS;
    $("ord-agregar").disabled = lleno;
    $("ord-max").hidden = !lleno;
    $("ord-contador").textContent = filas.length + " de " + MAX_LINEAS + " componentes" + (lleno ? " (máximo)" : "");
  }

  function nuevaLinea(codigo, cantidad) {
    const li = UI.el("li", { "data-row": true });
    const fila = UI.el("div", { "class": "line" });
    fila.appendChild(UI.el("span", { "class": "line-n", "aria-hidden": "true" }, "0"));
    const select = UI.el("select", { "class": "field", "data-opts": true });
    fila.appendChild(select);
    fila.appendChild(UI.el("input", { "class": "field num", inputmode: "numeric", autocomplete: "off", value: cantidad || "" }));
    fila.appendChild(UI.el("button", { "class": "btn btn-secondary", type: "button", "data-quitar": true }, "Quitar"));
    li.appendChild(fila);
    llenarSelect(select, false);
    if (codigo) select.value = codigo;
    return li;
  }

  function agregarLinea() {
    if (lineas().length >= MAX_LINEAS) return;
    const li = nuevaLinea();
    $("ord-lineas").appendChild(li);
    renumerar();
    li.querySelector("select").focus();
  }

  function quitarLinea(li) {
    const filas = lineas();
    if (filas.length <= 1) return;
    const i = filas.indexOf(li);
    li.remove();
    renumerar();
    const resto = lineas();
    (resto[Math.min(i, resto.length - 1)].querySelector("select")).focus();
  }

  function abrirOrden() {
    ocultarExito();
    const form = $("form-orden");
    form.reset();
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("ord-alerta"));
    ocultarErrorGeneral();
    $("ord-fecha").value = Validacion.hoy();
    UI.vaciar($("ord-lineas")).appendChild(nuevaLinea());
    renumerar();
    UI.abrir($("modal-orden"));
  }

  function ocultarErrorGeneral() {
    const p = $("ord-general-e");
    p.textContent = "";
    p.hidden = true;
  }

  function leerLineas() {
    return lineas().map((li) => ({
      codigo: li.querySelector("select").value,
      cantidad: li.querySelector("input").value
    }));
  }

  function validarOrden(form) {
    UI.limpiarErrores(form);
    lineas().forEach(limpiarMarcaLinea);
    ocultarErrorGeneral();
    const numero = $("ord-numero"), fecha = $("ord-fecha");
    let primero = null;
    const eNumero = Validacion.requerido(numero.value, "El número de orden") || Validacion.largo(numero.value, 30, "El número de orden");
    if (eNumero) { UI.errorBajoCampo(numero, eNumero); primero = numero; }
    const eFecha = Validacion.fecha(fecha.value);
    if (eFecha) { UI.errorBajoCampo(fecha, eFecha, fecha); primero = primero || fecha; }
    const r = Validacion.componentes(leerLineas());
    if (r.general) {
      const p = $("ord-general-e");
      p.textContent = r.general;
      p.hidden = false;
    }
    lineas().forEach((li, i) => {
      const e = r.porLinea[i];
      if (!e) return;
      if (e.producto) {
        marcarLinea(li, li.querySelector("select"), e.producto, true);
        primero = primero || li.querySelector("select");
      }
      if (e.cantidad) {
        marcarLinea(li, li.querySelector("input"), e.cantidad, true);
        primero = primero || li.querySelector("input");
      }
    });
    if (primero) primero.focus();
    return primero === null && !r.general;
  }

  function mapearErrorOrden(err, alerta) {
    UI.alerta(alerta, err.detail, "error");
    alerta.id = "ord-alerta";
    const filas = lineas();
    let foco = null;
    if (err.status === 409 && err.faltantes) {
      err.faltantes.forEach((f) => {
        filas.forEach((li) => {
          if (li.querySelector("select").value !== f.codigo) return;
          const campo = li.querySelector("input");
          marcarLinea(li, campo, "Disponible " + f.disponible + ", solicitado " + f.solicitado, false);
          foco = foco || campo;
        });
      });
    } else if (err.status === 409) {
      UI.invalido($("ord-numero"), "ord-alerta");
      foco = $("ord-numero");
    } else if (err.status === 404) {
      const citados = (err.detail.match(/'([^']*)'/g) || []).map((s) => s.slice(1, -1));
      cargar(false).then(() => {
        refrescarSelects(true);
        filas.forEach((li) => {
          const select = li.querySelector("select");
          if (citados.indexOf(select.value) === -1) return;
          marcarLinea(li, select, "Este producto ya no está activo: elegí otro o quitá la línea.", false);
          foco = foco || select;
        });
        if (foco) foco.focus();
      });
      return;
    } else if (err.status === 422) {
      const m = /^Componente (\d+):\s*(.*)$/.exec(err.detail);
      if (m && filas[Number(m[1]) - 1]) {
        const li = filas[Number(m[1]) - 1];
        const campo = /producto|código/i.test(m[2]) ? li.querySelector("select") : li.querySelector("input");
        marcarLinea(li, campo, m[2], false);
        foco = campo;
      } else if (/fecha/i.test(err.detail)) {
        UI.invalido($("ord-fecha"), "ord-alerta");
        foco = $("ord-fecha");
      }
    }
    if (foco) foco.focus();
  }

  function enviarOrden(e) {
    e.preventDefault();
    const form = $("form-orden"), boton = $("ord-enviar"), alerta = $("ord-alerta");
    if (boton.disabled) return;
    UI.ocultarAlerta(alerta);
    if (!validarOrden(form)) return;
    const cuerpo = {
      numero: $("ord-numero").value.trim(),
      fecha: $("ord-fecha").value.trim(),
      componentes: leerLineas().map((l) => ({ codigo: l.codigo, cantidad: Number(l.cantidad.trim()) }))
    };
    const restaurar = UI.ocupado(boton, "Creando orden…");
    Api.post("/api/ordenes", cuerpo).then(
      (orden) => {
        restaurar();
        UI.cerrar();
        const enlace = UI.el("a", { "class": "font-semibold underline", href: "/ordenes" }, "Ver órdenes");
        mostrarExito(["Orden ", num(orden.numero), " creada. ", enlace]);
        cargar(false);
      },
      (err) => {
        restaurar();
        mapearErrorOrden(err, alerta);
      }
    );
  }

  // ---------------------------------------------------------------- baja de producto

  function abrirBaja(codigo) {
    const p = productos.find((x) => x.codigo === codigo);
    if (!p) return;
    ocultarExito();
    bajaActual = p;
    UI.ocultarAlerta($("baja-alerta"));
    $("baja-nota").hidden = true;
    $("baja-desc").hidden = false;
    $("baja-producto").textContent = p.codigo + " — " + p.nombre;
    $("baja-cancelar").hidden = false;
    $("baja-cancelar").textContent = "Cancelar";
    $("baja-confirmar").hidden = false;
    UI.abrir($("modal-baja"));
  }

  function confirmarBaja() {
    const boton = $("baja-confirmar"), alerta = $("baja-alerta");
    if (boton.disabled || !bajaActual) return;
    const codigo = bajaActual.codigo;
    UI.ocultarAlerta(alerta);
    const restaurar = UI.ocupado(boton, "Eliminando…");
    Api.borrar("/api/productos/" + encodeURIComponent(codigo)).then(
      () => {
        restaurar();
        UI.cerrar();
        mostrarExito(["Producto ", num(codigo), " dado de baja."]);
        cargar(false);
      },
      (err) => {
        restaurar();
        UI.alerta(alerta, err.detail, "error");
        if (err.status === 404) {
          $("baja-desc").hidden = true;
          $("baja-nota").hidden = false;
          $("baja-confirmar").hidden = true;
          $("baja-cancelar").textContent = "Cerrar";
          $("baja-cancelar").focus();
          cargar(false);
        }
      }
    );
  }

  // ---------------------------------------------------------------- arranque

  document.addEventListener("DOMContentLoaded", () => {
    $("btn-ingreso").addEventListener("click", abrirIngreso);
    $("btn-egreso").addEventListener("click", abrirEgreso);
    $("btn-orden").addEventListener("click", abrirOrden);
    $("inv-reintentar").addEventListener("click", () => { ocultarExito(); cargar(true); });

    $("inv-cuerpo").addEventListener("click", (e) => {
      const boton = e.target.closest("[data-baja]");
      if (boton) abrirBaja(boton.getAttribute("data-baja"));
    });

    $("ing-codigo").addEventListener("input", hintCodigoNuevo);
    $("form-ingreso").addEventListener("submit", enviarIngreso);

    $("egr-producto").addEventListener("change", actualizarAyudaEgreso);
    $("form-egreso").addEventListener("submit", enviarEgreso);

    $("ord-agregar").addEventListener("click", agregarLinea);
    $("ord-lineas").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar]");
      if (q) quitarLinea(q.closest("li"));
    });
    $("form-orden").addEventListener("submit", enviarOrden);

    $("baja-confirmar").addEventListener("click", confirmarBaja);

    cargar(true);
  });
})();
