/* inventario.js: pantalla /inventario (specs interfaz-web: Tabla, Nuevo ingreso, Modificar stock,
   Nueva orden, Errores por linea, Baja de producto). Datos solo con textContent / createElement (design D4). */
(function () {
  "use strict";

  const Api = window.Api;
  const UI = window.UI;
  const MAX_LINEAS = 100;
  const MENOS = "−";

  let productos = [];
  let visibles = [];        // filas que deja pasar el buscador (lo que se exporta)
  let estadoActual = "cargando";
  let inactivos = [];
  let bajaActual = null;
  let secuenciaLinea = 0;
  let ordenForm = null;     // formulario de "Nueva orden" (orden-form.js)
  let categorias = [];      // catalogo [{clave, nombre}] ordenado por nombre (vacio si fallo la carga)
  let mapaCategorias = {};  // clave -> nombre

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- lista

  function hayBusqueda() {
    return Busqueda.normalizar($("inv-buscar").value) !== "";
  }

  // Valor del filtro de categoria: "" (todas), la clave o Busqueda.SIN_CATEGORIA.
  function categoriaElegida() {
    return $("inv-categoria").value;
  }

  function hayFiltros() {
    return hayBusqueda() || categoriaElegida() !== "";
  }

  // Nombre a mostrar del filtro elegido ("" si son todas).
  function nombreFiltroCategoria() {
    const valor = categoriaElegida();
    if (valor === "") return "";
    return valor === Busqueda.SIN_CATEGORIA ? "Sin categoría" : Busqueda.nombreCategoria(valor, mapaCategorias);
  }

  function nombreCategoriaDe(clave) {
    return Busqueda.nombreCategoria(clave, mapaCategorias);
  }

  // Llena un <select> de categoria. `primera`: texto de la opcion vacia ("Todas las categorias", "Sin categoria", "Todas").
  // `conSin`: agrega "Sin categoria" (solo filtros). Conserva el valor previo si sigue existiendo.
  function llenarSelectCategoria(select, primera, conSin) {
    const previo = select.value;
    UI.vaciar(select);
    select.appendChild(UI.el("option", { value: "" }, primera));
    categorias.forEach((c) => select.appendChild(UI.el("option", { value: c.clave }, c.nombre)));
    if (conSin) select.appendChild(UI.el("option", { value: Busqueda.SIN_CATEGORIA }, "Sin categoría"));
    const existe = Array.from(select.options).some((o) => o.value === previo);
    select.value = existe ? previo : "";
  }

  // Selector de categoria de una linea (nuevo ingreso / modificar): una clave que el catalogo no tiene se agrega para no perderla.
  function elegirCategoria(select, clave) {
    if (clave && !Array.from(select.options).some((o) => o.value === clave)) {
      select.appendChild(UI.el("option", { value: clave }, nombreCategoriaDe(clave)));
    }
    select.value = clave || "";
  }

  function llenarSelectoresCategoria() {
    llenarSelectCategoria($("inv-categoria"), "Todas las categorías", true);
    llenarSelectCategoria($("nu-categoria"), "Sin categoría", false);
    document.querySelectorAll("#mod-lineas select[data-categoria]").forEach((s) => llenarSelectCategoria(s, "Sin categoría", false));
    document.querySelectorAll("#mod-lineas select[data-filtro]").forEach((s) => llenarSelectCategoria(s, "Todas las categorías", true));
    ordenForm.refrescarCategorias();
  }

  // Catalogo de categorias; si falla, la tabla muestra la clave cruda y los filtros solo ofrecen "Todas".
  function cargarCategorias() {
    return Api.get("/api/categorias").then(
      (lista) => { categorias = lista; },
      () => { categorias = []; }
    ).then(() => {
      mapaCategorias = {};
      categorias.forEach((c) => { mapaCategorias[c.clave] = c.nombre; });
      ordenForm.setCategorias(categorias);
      llenarSelectoresCategoria();
      aplicarBusqueda(); // repinta con los nombres si la tabla ya se mostro con claves
    });
  }

  function mostrarEstado(estado) {
    estadoActual = estado;
    const sinCoincidencias = estado === "datos" && hayFiltros() && visibles.length === 0;
    $("inv-sin-coincidencias").hidden = !sinCoincidencias;
    $("btn-exportar-inv").disabled = estado !== "datos" || visibles.length === 0;
    $("inv-cargando").hidden = estado !== "cargando";
    $("inv-error").hidden = estado !== "error";
    $("inv-tabla").hidden = estado !== "datos" || sinCoincidencias;
    $("inv-conteo").hidden = estado !== "datos";
    $("inv-vacio").hidden = estado !== "vacio";
    $("inv-panel").hidden = estado === "vacio";
  }

  function textoStock(p) {
    const celda = UI.el("td", { "class": "num r" });
    if (p.sin_stock) {
      const badge = UI.el("span", { "class": "badge bg-warning-subtle text-warning-fg" }, String(p.stock));
      badge.appendChild(UI.el("span", { "class": "sr-only" }, ", sin stock"));
      badge.appendChild(UI.el("span", { "class": "print-only", "aria-hidden": "true" }, " (sin stock)"));
      celda.appendChild(badge);
    } else {
      celda.textContent = String(p.stock);
    }
    return celda;
  }

  function pintarTabla() {
    const cuerpo = UI.vaciar($("inv-cuerpo"));
    const texto = $("inv-buscar").value;
    visibles = Busqueda.filtrar(productos, texto, categoriaElegida());
    visibles.forEach((p) => {
      const fila = UI.el("tr");
      const sinCat = p.categoria == null;
      fila.appendChild(UI.el("td", { "class": "num" }, p.codigo));
      const nombre = UI.el("td", null, p.nombre);
      // Móvil: la categoría va como segunda línea bajo el nombre; desde 640 px y en el papel es una columna.
      nombre.appendChild(UI.el("span", { "class": "cat-inline" + (sinCat ? " cat-none" : "") }, nombreCategoriaDe(p.categoria)));
      fila.appendChild(nombre);
      fila.appendChild(UI.el("td", { "class": "cat-col" + (sinCat ? " cat-none" : "") }, nombreCategoriaDe(p.categoria)));
      fila.appendChild(textoStock(p));
      const accion = UI.el("td", { "class": "r" });
      accion.appendChild(UI.el("button", {
        "class": "btn btn-secondary btn-sm", type: "button", "data-baja": p.codigo,
        "aria-label": "Eliminar " + p.codigo
      }, "Eliminar"));
      fila.appendChild(accion);
      cuerpo.appendChild(fila);
    });
    $("inv-conteo").textContent = Busqueda.conteo(visibles.length, productos.length, hayFiltros());
    $("inv-sin-coincidencias-msg").textContent = Busqueda.mensajeSinCoincidencias(texto, nombreFiltroCategoria());
  }

  // Repinta la tabla con el texto actual del buscador (solo si ya hay datos en pantalla).
  function aplicarBusqueda() {
    if (estadoActual !== "datos") return;
    pintarTabla();
    mostrarEstado("datos");
  }

  // Escape en "Buscar": limpia solo el texto.
  function limpiarBusqueda() {
    const campo = $("inv-buscar");
    campo.value = "";
    aplicarBusqueda();
    campo.focus();
  }

  // "Limpiar filtros": texto y categoria; el foco vuelve a "Buscar".
  function limpiarFiltros() {
    $("inv-categoria").value = "";
    limpiarBusqueda();
  }

  function exportarInventario() {
    const n = visibles.length;
    if (estadoActual !== "datos" || n === 0) return;
    Exportar.imprimir({
      titulo: "Inventario",
      linea: Busqueda.lineaInventario(n, nombreFiltroCategoria(), Exportar.fecha(new Date())),
      base: "inventario",
      modo: "inventario"
    });
  }

  function etiquetaProducto(p) {
    return p.codigo + " · " + p.nombre + " (stock " + p.stock + ")";
  }

  // Ayuda bajo la linea cuando el filtro de categoria no deja ningun producto (Nueva orden y Modificar stock).
  const AYUDA_SIN_PRODUCTOS = OrdenForm.AYUDA_SIN_PRODUCTOS;

  function aplicarProductos(lista) {
    productos = lista;
    ordenForm.setProductos(lista);
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

  // partes: lista de strings o nodos; se antepone "Listo.". `lista` (opcional): <ul> bajo el texto.
  function mostrarExito(partes, lista) {
    const caja = UI.vaciar($("aviso-exito"));
    const cuerpo = UI.el("div", { "class": "flex-1 py-2" });
    const p = UI.el("p");
    p.appendChild(UI.el("strong", null, "Listo."));
    p.appendChild(document.createTextNode(" "));
    partes.forEach((parte) => {
      p.appendChild(typeof parte === "string" ? document.createTextNode(parte) : parte);
    });
    cuerpo.appendChild(p);
    if (lista) cuerpo.appendChild(lista);
    caja.appendChild(cuerpo);
    const cerrar = UI.el("button", { "class": "icon-btn", type: "button", "aria-label": "Cerrar aviso" }, "×");
    cerrar.addEventListener("click", ocultarExito);
    caja.appendChild(cerrar);
    caja.hidden = false;
  }

  const num = (t) => UI.el("span", { "class": "num" }, t);

  // ---------------------------------------------------------------- catalogo (activos + dados de baja)

  // Carga activos e inactivos en paralelo y actualiza la tabla; devuelve el error (o null).
  function cargarCatalogo() {
    return Promise.all([Api.get("/api/inventario"), Api.get("/api/productos/inactivos")]).then(
      (r) => { inactivos = r[1]; aplicarProductos(r[0]); return null; },
      (err) => err
    );
  }

  function cargarInactivos() {
    return Api.get("/api/productos/inactivos").then(
      (lista) => { inactivos = lista; },
      () => { /* el aviso de dado de baja es opcional */ }
    );
  }

  // ---------------------------------------------------------------- nuevo ingreso

  function avisoCodigoDeBaja() {
    const codigo = $("nu-codigo").value.trim().toUpperCase();
    const baja = codigo !== "" && inactivos.some((p) => p.codigo === codigo);
    $("nu-aviso").hidden = !baja;
    const campo = $("nu-codigo");
    if (campo.getAttribute("aria-invalid") !== "true") {
      campo.setAttribute("aria-describedby", baja ? "nu-codigo-h nu-aviso" : "nu-codigo-h");
    }
  }

  function abrirNuevo() {
    ocultarExito();
    const form = $("form-nuevo");
    form.reset();
    $("nu-categoria").value = "";
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("nu-alerta"));
    $("nu-aviso").hidden = true;
    UI.abrir($("modal-nuevo"));
    cargarInactivos().then(avisoCodigoDeBaja);
  }

  function validarNuevo(form) {
    UI.limpiarErrores(form);
    const codigo = $("nu-codigo"), nombre = $("nu-nombre"), stock = $("nu-stock");
    const errores = [
      [codigo, Validacion.requerido(codigo.value, "El código") || Validacion.largo(codigo.value, 50, "El código")],
      [nombre, Validacion.requerido(nombre.value, "El nombre") || Validacion.largo(nombre.value, 120, "El nombre")],
      [stock, Validacion.requerido(stock.value, "El stock") || Validacion.stock(stock.value)]
    ].filter((e) => e[1]);
    errores.forEach((e) => UI.errorBajoCampo(e[0], e[1]));
    if (errores.length) errores[0][0].focus();
    return errores.length === 0;
  }

  function enviarNuevo(e) {
    e.preventDefault();
    const form = $("form-nuevo"), boton = $("nu-enviar"), alerta = $("nu-alerta");
    if (boton.disabled) return;
    UI.ocultarAlerta(alerta);
    if (!validarNuevo(form)) return;
    const cuerpo = {
      codigo: $("nu-codigo").value.trim(),
      nombre: $("nu-nombre").value.trim(),
      stock: Number($("nu-stock").value.trim()),
      categoria: $("nu-categoria").value === "" ? null : $("nu-categoria").value
    };
    const restaurar = UI.ocupado(boton, "Creando…");
    Api.post("/api/productos", cuerpo).then(
      (r) => {
        restaurar();
        UI.cerrar();
        mostrarExito([
          r.reactivado ? "Producto reactivado: " : "Producto creado: ",
          num(r.codigo), " · " + r.nombre + " (stock " + r.stock + ")."
        ]);
        cargar(false);
      },
      (err) => {
        restaurar();
        UI.alerta(alerta, err.detail, "error");
        let campo = null;
        if (err.status === 409) campo = $("nu-codigo");
        else if (err.status === 422 && /nombre/i.test(err.detail)) campo = $("nu-nombre");
        else if (err.status === 422 && /stock/i.test(err.detail)) campo = $("nu-stock");
        else if (err.status === 422 && /categor/i.test(err.detail)) campo = $("nu-categoria");
        else if (err.status === 422 && /c[oó]digo/i.test(err.detail)) campo = $("nu-codigo");
        if (campo) {
          UI.invalido(campo, "nu-alerta");
          campo.focus();
        }
      }
    );
  }

  // ---------------------------------------------------------------- modificar stock

  const NO_EXISTE = "Este producto ya no existe: elegí otro o quitá la línea.";
  const ES_ENTERO = /^\d+$/;

  function lineasMod() {
    return Array.from(document.querySelectorAll("#mod-lineas > li"));
  }

  // { p, baja } del producto (activo o dado de baja) o null.
  function buscarProducto(codigo) {
    let p = productos.find((x) => x.codigo === codigo);
    if (p) return { p: p, baja: false };
    p = inactivos.find((x) => x.codigo === codigo);
    return p ? { p: p, baja: true } : null;
  }

  function modoDe(li) {
    return li.querySelector('input[type="radio"]:checked').value;
  }

  function llenarSelectMod(select, ocupados, conservar, categoria) {
    const previo = select.value;
    UI.vaciar(select);
    select.appendChild(UI.el("option", { value: "" }, "Elegí un producto…"));
    [["Activos", Busqueda.porCategoria(productos, categoria)],
      ["Dados de baja", Busqueda.porCategoria(inactivos, categoria)]].forEach((g) => {
      if (g[1].length === 0) return;
      const grupo = UI.el("optgroup", { label: g[0] });
      g[1].forEach((p) => {
        const op = UI.el("option", { value: p.codigo }, etiquetaProducto(p));
        if (ocupados.has(p.codigo) && p.codigo !== previo) {
          op.disabled = true;
          op.textContent += " — ya está en otra línea";
        }
        grupo.appendChild(op);
      });
      select.appendChild(grupo);
    });
    if (previo && buscarProducto(previo)) {
      // Existe pero quedo fuera del filtro: la opcion no esta y el selector vuelve a "Elegí un producto…".
      if (Busqueda.productoSigueVisible(previo, productos.concat(inactivos), categoria)) select.value = previo;
    } else if (previo && conservar) {
      select.appendChild(UI.el("option", { value: previo }, previo + " · (ya no existe)"));
      select.value = previo;
    }
  }

  // Rellena todos los selectores: cada uno deshabilita los productos elegidos en las demás líneas.
  function refrescarSelectsMod(conservar) {
    const filas = lineasMod();
    const valores = filas.map((li) => li.querySelector("select[data-producto]").value);
    filas.forEach((li, i) => {
      const ocupados = new Set(valores.filter((v, j) => j !== i && v !== ""));
      llenarSelectMod(li.querySelector("select[data-producto]"), ocupados, conservar, li.querySelector("select[data-filtro]").value);
    });
    filas.forEach(actualizarAyudaMod);
    filas.forEach(actualizarLineaMod);
  }

  // Ayuda de lista vacía cuando el filtro de la línea no deja activos ni dados de baja.
  function actualizarAyudaMod(li) {
    const categoria = li.querySelector("select[data-filtro]").value;
    const vacia = categoria !== "" && Busqueda.porCategoria(productos, categoria).length === 0
      && Busqueda.porCategoria(inactivos, categoria).length === 0;
    const id = "mod-" + li.getAttribute("data-k") + "-vacio";
    const select = li.querySelector("select[data-producto]");
    const previa = document.getElementById(id);
    if (previa) previa.remove();
    if (select.getAttribute("aria-describedby") === id) select.removeAttribute("aria-describedby");
    if (!vacia) return;
    const cuerpo = li.querySelector(".mline-body");
    cuerpo.insertBefore(UI.el("p", { "class": "help", id: id }, AYUDA_SIN_PRODUCTOS), cuerpo.firstChild);
    if (!select.hasAttribute("aria-invalid")) select.setAttribute("aria-describedby", id);
  }

  function renumerarMod() {
    const filas = lineasMod();
    filas.forEach((li, i) => {
      const n = i + 1, k = li.getAttribute("data-k");
      li.querySelector(".line-n").textContent = String(n);
      const fil = li.querySelector("select[data-filtro]");
      fil.setAttribute("aria-label", "Filtrar por categoría, línea " + n);
      fil.id = "mod-" + k + "-fil";
      li.querySelector("[data-filtro-etiqueta]").setAttribute("for", fil.id);
      const prod = li.querySelector("select[data-producto]");
      prod.setAttribute("aria-label", "Producto de la línea " + n);
      prod.id = "mod-" + k + "-prod";
      li.querySelector("[data-producto-etiqueta]").setAttribute("for", prod.id);
      const cat = li.querySelector("select[data-categoria]");
      cat.setAttribute("aria-label", "Categoría de la línea " + n);
      cat.id = "mod-" + k + "-cat";
      li.querySelector("[data-categoria-etiqueta]").setAttribute("for", cat.id);
      li.querySelector("[data-modo]").setAttribute("aria-label", "Modo de la línea " + n);
      const nombre = li.querySelector("[data-nombre]");
      nombre.setAttribute("aria-label", "Nuevo nombre (opcional) de la línea " + n);
      nombre.id = "mod-" + k + "-nom";
      li.querySelector("[data-nombre-etiqueta]").setAttribute("for", nombre.id);
      const quitar = li.querySelector("[data-quitar]");
      quitar.setAttribute("aria-label", "Quitar producto de la línea " + n);
      quitar.disabled = filas.length === 1;
    });
    const lleno = filas.length >= MAX_LINEAS;
    $("mod-agregar").disabled = lleno;
    $("mod-max").hidden = !lleno;
    $("mod-contador").textContent = filas.length + " de " + MAX_LINEAS + " productos" + (lleno ? " (máximo)" : "");
  }

  function nuevaLineaMod() {
    const li = $("tpl-mline").content.firstElementChild.cloneNode(true);
    secuenciaLinea += 1;
    li.setAttribute("data-k", String(secuenciaLinea));
    li.querySelectorAll('input[type="radio"]').forEach((r) => { r.name = "mod-" + secuenciaLinea + "-modo"; });
    llenarSelectCategoria(li.querySelector("select[data-categoria]"), "Sin categoría", false);
    llenarSelectCategoria(li.querySelector("select[data-filtro]"), "Todas las categorías", true);
    return li;
  }

  function agregarLineaMod() {
    if (lineasMod().length >= MAX_LINEAS) return;
    const li = nuevaLineaMod();
    $("mod-lineas").appendChild(li);
    renumerarMod();
    refrescarSelectsMod(false);
    li.querySelector("select[data-producto]").focus();
  }

  function quitarLineaMod(li) {
    const filas = lineasMod();
    if (filas.length <= 1) return;
    const i = filas.indexOf(li);
    li.remove();
    renumerarMod();
    refrescarSelectsMod(false);
    lineasMod()[Math.min(i, filas.length - 2)].querySelector("select[data-producto]").focus();
  }

  // Valor propuesto y categoría precargada según el producto elegido (o vacíos si no hay ninguno).
  function aplicarProductoMod(li) {
    const info = buscarProducto(li.querySelector("select[data-producto]").value);
    if (modoDe(li) === "fijar") li.querySelector("[data-valor]").value = info ? String(info.p.stock) : "";
    // La categoría se precarga con la del producto elegido (activo o dado de baja).
    elegirCategoria(li.querySelector("select[data-categoria]"), info ? info.p.categoria : "");
  }

  // Pone el valor propuesto (stock actual) al elegir un producto en "Fijar en" o al cambiar de modo.
  function alCambiarLineaMod(e) {
    const li = e.target.closest("li");
    if (!li) return;
    const campoValor = li.querySelector("[data-valor]");
    const info = buscarProducto(li.querySelector("select[data-producto]").value);
    if (e.target.matches("select[data-producto]")) {
      refrescarSelectsMod(false);
      aplicarProductoMod(li);
    } else if (e.target.matches("select[data-filtro]")) {
      // Solo presentación: conserva el producto si pertenece al filtro; si no, lo deselecciona
      // (antes de refrescar, porque refrescarSelectsMod calcula los ocupados con los valores previos).
      const select = li.querySelector("select[data-producto]");
      if (select.value !== "" && !Busqueda.productoSigueVisible(select.value, productos.concat(inactivos), e.target.value)) {
        select.value = "";
        aplicarProductoMod(li);
      }
      refrescarSelectsMod(false);
    } else if (e.target.matches("select[data-categoria]")) {
      // solo cambia la categoria: no toca el stock propuesto
    } else if (e.target.matches('input[type="radio"]')) {
      campoValor.value = modoDe(li) === "fijar" && info ? String(info.p.stock) : "";
    }
    actualizarLineaMod(li);
  }

  // Resultado "Stock actual A → B", aviso de dado de baja y rótulos según el modo.
  function actualizarLineaMod(li) {
    const n = lineasMod().indexOf(li) + 1;
    const modo = modoDe(li);
    const campoValor = li.querySelector("[data-valor]");
    campoValor.setAttribute("aria-label",
      (modo === "fijar" ? "Stock nuevo de la línea " : "Cantidad a sumar de la línea ") + n);
    const info = buscarProducto(li.querySelector("select[data-producto]").value);
    const delta = UI.vaciar(li.querySelector("[data-delta]"));
    const aviso = li.querySelector("[data-aviso]");
    const nombre = li.querySelector("[data-nombre]");
    nombre.placeholder = info ? "Sin cambios (" + info.p.nombre + ")" : "";
    if (!info) {
      aviso.hidden = true;
      return;
    }
    const actual = info.p.stock;
    const texto = campoValor.value.trim();
    const valido = ES_ENTERO.test(texto) && (modo === "fijar" ? Number(texto) <= 10000 : Number(texto) >= 1 && Number(texto) <= 10000);
    let nuevo = actual;
    if (valido) nuevo = modo === "fijar" ? Number(texto) : actual + Number(texto);
    delta.appendChild(document.createTextNode("Stock actual "));
    delta.appendChild(UI.el("strong", { "class": "num" }, String(actual)));
    if (valido && nuevo !== actual) {
      delta.appendChild(document.createTextNode(" → "));
      delta.appendChild(UI.el("strong", { "class": "num" }, String(nuevo)));
    } else if (valido) {
      delta.appendChild(document.createTextNode(" · sin cambios"));
    }
    if (!info.baja) {
      aviso.hidden = true;
      return;
    }
    // Un dado de baja solo se reactiva si el stock cambia y queda > 0 (decisión 9).
    let mensaje = "Dado de baja: sigue dado de baja (sin cambio de stock).";
    if (nuevo !== actual) {
      mensaje = nuevo > 0
        ? "Dado de baja: se va a reactivar al guardar."
        : "Dado de baja: sigue dado de baja (stock 0).";
    }
    aviso.textContent = mensaje;
    aviso.hidden = false;
  }

  function limpiarMarcaMod(li) {
    li.removeAttribute("data-invalid");
    li.querySelectorAll("[data-error]").forEach((x) => x.remove());
    li.querySelectorAll("[aria-invalid]").forEach((c) => { c.removeAttribute("aria-invalid"); c.removeAttribute("aria-describedby"); });
  }

  function marcarLineaMod(li, campo, mensaje) {
    li.setAttribute("data-invalid", "");
    const clave = campo.matches("select[data-producto]") ? "p" : campo.matches("select[data-categoria]") ? "c"
      : campo.matches("[data-valor]") ? "v" : "n";
    const id = "mod-" + li.getAttribute("data-k") + "-" + clave + "-e";
    const previo = document.getElementById(id);
    if (previo) previo.remove();
    li.querySelector(".mline-body").appendChild(UI.el("p", { "class": "err", id: id, role: "alert", "data-error": true }, mensaje));
    UI.invalido(campo, id);
  }

  function leerLineasMod() {
    return lineasMod().map((li) => ({
      codigo: li.querySelector("select[data-producto]").value,
      modo: modoDe(li),
      valor: li.querySelector("[data-valor]").value,
      nombre: li.querySelector("[data-nombre]").value,
      categoria: li.querySelector("select[data-categoria]").value
    }));
  }

  function ocultarGeneralMod() {
    const p = $("mod-general-e");
    p.textContent = "";
    p.hidden = true;
  }

  function abrirModificar() {
    ocultarExito();
    const form = $("form-modificar");
    form.reset();
    UI.limpiarErrores(form);
    UI.ocultarAlerta($("mod-alerta"));
    $("mod-nota").hidden = true;
    ocultarGeneralMod();
    UI.vaciar($("mod-lineas")).appendChild(nuevaLineaMod());
    renumerarMod();
    refrescarSelectsMod(false);
    UI.abrir($("modal-modificar"));
    cargarCatalogo().then((err) => {
      if (err) UI.alerta($("mod-alerta"), err.detail, "error");
      else refrescarSelectsMod(false);
    });
  }

  function validarModificar(form) {
    UI.limpiarErrores(form);
    lineasMod().forEach(limpiarMarcaMod);
    ocultarGeneralMod();
    const r = Validacion.lineasModificacion(leerLineasMod());
    if (r.general) {
      const p = $("mod-general-e");
      p.textContent = r.general;
      p.hidden = false;
    }
    let primero = null;
    lineasMod().forEach((li, i) => {
      const e = r.porLinea[i];
      if (!e) return;
      [[e.producto, li.querySelector("select[data-producto]")], [e.valor, li.querySelector("[data-valor]")],
        [e.nombre, li.querySelector("[data-nombre]")]].forEach((par) => {
        if (!par[0]) return;
        marcarLineaMod(li, par[1], par[0]);
        primero = primero || par[1];
      });
    });
    if (primero) primero.focus();
    return primero === null && !r.general;
  }

  function mapearErrorModificar(err, alerta) {
    UI.alerta(alerta, err.detail, "error");
    const filas = lineasMod();
    let foco = null;
    if (err.status === 404 && err.codigos) {
      cargarCatalogo().then(() => {
        refrescarSelectsMod(true);
        filas.forEach((li) => {
          const select = li.querySelector("select[data-producto]");
          if (err.codigos.indexOf(select.value) === -1) return;
          marcarLineaMod(li, select, NO_EXISTE);
          foco = foco || select;
        });
        const nota = $("mod-nota");
        nota.textContent = "La lista de productos se actualizó.";
        nota.hidden = false;
        if (foco) foco.focus();
      });
      return;
    }
    if (err.status === 422) {
      const m = /^Línea (\d+):\s*(.*)$/.exec(err.detail);
      const li = m ? filas[Number(m[1]) - 1] : null;
      if (li) {
        const texto = m[2];
        let campo = li.querySelector("[data-valor]");
        if (/categor/i.test(texto)) campo = li.querySelector("select[data-categoria]");
        else if (/producto|c[oó]digo/i.test(texto)) campo = li.querySelector("select[data-producto]");
        else if (/nombre/i.test(texto)) campo = li.querySelector("[data-nombre]");
        marcarLineaMod(li, campo, texto);
        foco = campo;
      }
    }
    if (foco) foco.focus();
  }

  function resumenModificacion(lineas) {
    const lista = UI.el("ul", { "class": "sum-list" });
    lineas.forEach((l) => {
      const li = UI.el("li");
      li.appendChild(num(l.codigo));
      li.appendChild(document.createTextNode(" · " + l.nombre + ": "));
      if (l.stock === l.stock_anterior) {
        li.appendChild(document.createTextNode("stock "));
        li.appendChild(num(String(l.stock)));
        li.appendChild(document.createTextNode(" sin cambios"));
      } else {
        li.appendChild(num(l.stock_anterior + " → " + l.stock));
        if (l.modo === "sumar") li.appendChild(document.createTextNode(" (+" + (l.stock - l.stock_anterior) + ")"));
      }
      if (l.nombre !== l.nombre_anterior) {
        li.appendChild(document.createTextNode(" · nombre antes: " + l.nombre_anterior));
      }
      if (l.categoria !== l.categoria_anterior) {
        li.appendChild(document.createTextNode(
          " · categoría: " + nombreCategoriaDe(l.categoria_anterior) + " → " + nombreCategoriaDe(l.categoria)
        ));
      }
      if (l.reactivado) {
        li.appendChild(document.createTextNode(" · "));
        li.appendChild(UI.el("span", { "class": "tag-react" }, "reactivado"));
      }
      lista.appendChild(li);
    });
    return lista;
  }

  function enviarModificar(e) {
    e.preventDefault();
    const form = $("form-modificar"), boton = $("mod-enviar"), alerta = $("mod-alerta");
    if (boton.disabled) return;
    UI.ocultarAlerta(alerta);
    $("mod-nota").hidden = true;
    if (!validarModificar(form)) return;
    const cuerpo = {
      lineas: leerLineasMod().map((l) => {
        const linea = { codigo: l.codigo, modo: l.modo };
        linea[l.modo === "fijar" ? "stock" : "cantidad"] = Number(l.valor.trim());
        const nombre = l.nombre.trim();
        if (nombre !== "") linea.nombre = nombre;
        linea.categoria = l.categoria === "" ? null : l.categoria;
        return linea;
      })
    };
    const restaurar = UI.ocupado(boton, "Guardando…");
    Api.post("/api/stock/modificaciones", cuerpo).then(
      (r) => {
        restaurar();
        UI.cerrar();
        const n = r.lineas.length;
        mostrarExito(["Stock modificado (" + n + (n === 1 ? " producto" : " productos") + "):"], resumenModificacion(r.lineas));
        cargar(false);
      },
      (err) => {
        restaurar();
        mapearErrorModificar(err, alerta);
      }
    );
  }

  // ---------------------------------------------------------------- nueva orden (formulario compartido: orden-form.js)

  function abrirOrden() {
    ocultarExito();
    ordenForm.abrir();
  }

  function ordenCreada(orden) {
    const enlace = UI.el("a", { "class": "font-semibold underline", href: "/ordenes" }, "Ver órdenes");
    mostrarExito(["Orden ", num(orden.numero), " creada. ", enlace]);
    cargar(false);
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
    ordenForm = OrdenForm.montar({
      modo: "nueva",
      formId: "form-orden",
      modalId: "modal-orden",
      recargarProductos: () => cargar(false),
      alExito: ordenCreada
    });
    $("btn-nuevo").addEventListener("click", abrirNuevo);
    $("btn-modificar").addEventListener("click", abrirModificar);
    $("btn-orden").addEventListener("click", abrirOrden);
    $("inv-reintentar").addEventListener("click", () => { ocultarExito(); cargar(true); });
    $("inv-buscar").addEventListener("input", aplicarBusqueda);
    $("inv-buscar").addEventListener("keydown", (e) => {
      if (e.key === "Escape" && $("inv-buscar").value !== "") { e.preventDefault(); limpiarBusqueda(); }
    });
    $("inv-categoria").addEventListener("change", aplicarBusqueda);
    $("inv-limpiar").addEventListener("click", limpiarFiltros);
    $("btn-exportar-inv").addEventListener("click", exportarInventario);

    $("inv-cuerpo").addEventListener("click", (e) => {
      const boton = e.target.closest("[data-baja]");
      if (boton) abrirBaja(boton.getAttribute("data-baja"));
    });

    $("nu-codigo").addEventListener("input", avisoCodigoDeBaja);
    $("form-nuevo").addEventListener("submit", enviarNuevo);

    $("mod-agregar").addEventListener("click", agregarLineaMod);
    $("mod-lineas").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar]");
      if (q) quitarLineaMod(q.closest("li"));
    });
    $("mod-lineas").addEventListener("change", alCambiarLineaMod);
    $("mod-lineas").addEventListener("input", (e) => {
      const li = e.target.closest("li");
      if (li) actualizarLineaMod(li);
    });
    $("form-modificar").addEventListener("submit", enviarModificar);

    $("baja-confirmar").addEventListener("click", confirmarBaja);

    llenarSelectoresCategoria();
    cargarCategorias();
    ordenForm.cargarCatalogos();
    cargar(true);
  });
})();
