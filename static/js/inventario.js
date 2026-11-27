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
  let categorias = [];      // catalogo [{clave, nombre}] ordenado por nombre (vacio si fallo la carga)
  let mapaCategorias = {};  // clave -> nombre
  let catalogoProcesos = []; // [{clave, nombre}] ordenado por nombre (vacio si fallo la carga)
  let procesosFallo = false;
  let catalogoServicios = []; // [{clave, nombre, chequeos}] ordenado por nombre (vacio si fallo la carga)
  let serviciosFallo = false;

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
    document.querySelectorAll("#ord-lineas select[data-cat]").forEach((s) => llenarSelectCategoria(s, "Todas", true));
  }

  // Catalogo de categorias; si falla, la tabla muestra la clave cruda y los filtros solo ofrecen "Todas".
  function cargarCategorias() {
    return Api.get("/api/categorias").then(
      (lista) => { categorias = lista; },
      () => { categorias = []; }
    ).then(() => {
      mapaCategorias = {};
      categorias.forEach((c) => { mapaCategorias[c.clave] = c.nombre; });
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

  // Llena un <select> con los productos activos. `conservar`: si el valor previo ya no esta, se deja visible.
  // `categoria` filtra la lista ("" = todas; "__sin__" = sin categoria); si el producto elegido no pertenece, se resetea.
  function llenarSelect(select, conservar, categoria) {
    const previo = select.value;
    const lista = Busqueda.porCategoria(productos, categoria);
    UI.vaciar(select);
    select.appendChild(UI.el("option", { value: "" }, "Elegí un producto…"));
    lista.forEach((p) => select.appendChild(UI.el("option", { value: p.codigo }, etiquetaProducto(p))));
    if (previo && Busqueda.productoSigueVisible(previo, productos, categoria)) {
      select.value = previo;
    } else if (previo && conservar) {
      select.appendChild(UI.el("option", { value: previo }, previo + " · (ya no está activo)"));
      select.value = previo;
    }
  }

  function selectProducto(li) { return li.querySelector("select[data-opts]"); }
  function selectCategoria(li) { return li.querySelector("select[data-cat]"); }
  function inputCantidad(li) { return li.querySelector("input[data-cant]"); }
  function inputImporte(li) { return li.querySelector("input[data-imp]"); }

  // Ayuda bajo la linea cuando el filtro de categoria no deja ningun producto (Nueva orden y Modificar stock).
  const AYUDA_SIN_PRODUCTOS = "No hay productos en esta categoría.";

  function actualizarAyudaLinea(li) {
    const categoria = selectCategoria(li).value;
    const vacia = Busqueda.porCategoria(productos, categoria).length === 0;
    const id = "ord-" + li.getAttribute("data-k") + "-vacio";
    const previa = document.getElementById(id);
    if (previa) previa.remove();
    selectProducto(li).removeAttribute("aria-describedby");
    if (!vacia || categoria === "") return;
    li.appendChild(UI.el("p", { "class": "help line-help", id: id }, AYUDA_SIN_PRODUCTOS));
    selectProducto(li).setAttribute("aria-describedby", id);
  }

  function refrescarLinea(li, conservar) {
    llenarSelect(selectProducto(li), conservar, selectCategoria(li).value);
    actualizarAyudaLinea(li);
  }

  function refrescarSelects(conservar) {
    lineas().forEach((li) => refrescarLinea(li, conservar));
  }

  function aplicarProductos(lista) {
    productos = lista;
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

  // "Proceso N: ..." (lista del catalogo) o "Proceso personalizado N: ..." -> {li, mensaje, importe}
  // con la linea de la orden que corresponde; `importe` si el error es del precio.
  function procesoDeError(detail) {
    const m = /^Proceso (personalizado )?(\d+):\s*(.*)$/.exec(detail);
    if (!m) return null;
    const delTipo = lineasProc().filter((li) => (selectProceso(li).value === PERSONALIZADO) === Boolean(m[1]));
    const li = delTipo[Number(m[2]) - 1];
    return li ? { li: li, mensaje: m[3], importe: /precio/i.test(m[3]) } : null;
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

  // ---------------------------------------------------------------- nueva orden

  // Procesos de la orden (C-06f): lineas con un select (catalogo + "Personalizado") y, en
  // "Personalizado", una caja de texto. Cero lineas es valido.
  const PERSONALIZADO = Procesos.PERSONALIZADO;
  const MSG_ADICIONALES_CAIDOS = "No se pudo cargar la lista de servicios adicionales.";

  function lineasProc() {
    return Array.from(document.querySelectorAll("#ord-procesos > li"));
  }

  function selectProceso(li) { return li.querySelector("select[data-proc]"); }
  function textoProceso(li) { return li.querySelector("input[data-proc-texto]"); }
  function importeProceso(li) { return li.querySelector("input[data-proc-imp]"); }

  function mostrarAvisoProcesos(mensaje) {
    const p = $("ord-proc-aviso");
    p.textContent = mensaje || "";
    p.hidden = !mensaje;
  }

  function cargarProcesos() {
    return Api.get("/api/procesos").then(
      (lista) => { catalogoProcesos = lista; procesosFallo = false; },
      () => { catalogoProcesos = []; procesosFallo = true; }
    );
  }

  function llenarSelectProceso(select, conservar) {
    const previo = conservar ? select.value : null;
    UI.vaciar(select);
    catalogoProcesos.forEach((p) => select.appendChild(UI.el("option", { value: p.clave }, p.nombre)));
    select.appendChild(UI.el("option", { value: PERSONALIZADO }, "Personalizado"));
    if (previo === null) {
      select.value = catalogoProcesos.length ? catalogoProcesos[0].clave : PERSONALIZADO;
    } else if (previo === PERSONALIZADO || catalogoProcesos.some((p) => p.clave === previo)) {
      select.value = previo;
    } else {
      // El proceso elegido ya no existe: la linea queda sin seleccion hasta que se elija otro.
      select.insertBefore(UI.el("option", { value: "", disabled: true }, "Elegí un servicio adicional"), select.firstChild);
      select.value = "";
    }
  }

  function personalizadosActuales() {
    return lineasProc().filter((li) => selectProceso(li).value === PERSONALIZADO).length;
  }

  function renumerarProcesos() {
    const filas = lineasProc();
    const usados = personalizadosActuales();
    const lleno = usados >= Procesos.PERSONALIZADOS_MAX;
    filas.forEach((li, i) => {
      const select = selectProceso(li);
      select.setAttribute("aria-label", "Servicio adicional de la línea " + (i + 1));
      importeProceso(li).setAttribute("aria-label", "Precio del servicio adicional " + (i + 1));
      li.querySelector("[data-quitar-proc]").setAttribute("aria-label", "Quitar servicio adicional " + (i + 1));
      const opcion = Array.from(select.options).find((o) => o.value === PERSONALIZADO);
      if (opcion) opcion.disabled = lleno && select.value !== PERSONALIZADO;
      const caja = li.querySelector(".pline-txt");
      caja.hidden = select.value !== PERSONALIZADO;
      textoProceso(li).setAttribute("aria-label", "Servicio adicional personalizado de la línea " + (i + 1));
    });
    $("ord-proc-max").hidden = !lleno;
    $("ord-proc-contador").textContent =
      usados + (usados === 1 ? " personalizado" : " personalizados") + " de " + Procesos.PERSONALIZADOS_MAX;
  }

  function nuevaLineaProceso() {
    secuenciaLinea += 1;
    const k = String(secuenciaLinea);
    const li = UI.el("li", { "data-k": k });
    const fila = UI.el("div", { "class": "pline pline-p" });
    const select = UI.el("select", { "class": "field", "data-proc": true });
    fila.appendChild(select);
    const importe = UI.el("div", { "class": "money" });
    importe.appendChild(UI.el("input", {
      "class": "field", inputmode: "decimal", autocomplete: "off", placeholder: "0,00", "data-proc-imp": true
    }));
    fila.appendChild(importe);
    fila.appendChild(UI.el("button", { "class": "btn btn-secondary", type: "button", "data-quitar-proc": true }, "Quitar"));
    const caja = UI.el("div", { "class": "pline-txt" });
    caja.appendChild(UI.el("label", { "class": "sr-only", "for": "ord-pt-" + k }, "Servicio adicional personalizado"));
    caja.appendChild(UI.el("input", {
      "class": "field", id: "ord-pt-" + k, "data-proc-texto": true, maxlength: String(Procesos.NOMBRE_MAX),
      autocomplete: "off", placeholder: "Servicio adicional personalizado"
    }));
    fila.appendChild(caja);
    li.appendChild(fila);
    llenarSelectProceso(select, false);
    return li;
  }

  function agregarProceso() {
    const li = nuevaLineaProceso();
    $("ord-procesos").appendChild(li);
    renumerarProcesos();
    actualizarResumen();
    selectProceso(li).focus();
  }

  function quitarProceso(li) {
    const filas = lineasProc();
    const i = filas.indexOf(li);
    li.remove();
    renumerarProcesos();
    actualizarResumen();
    const resto = lineasProc();
    (resto.length ? selectProceso(resto[Math.min(i, resto.length - 1)]) : $("ord-proc-agregar")).focus();
  }

  function marcarProceso(li, mensaje) {
    const campo = selectProceso(li).value === PERSONALIZADO ? textoProceso(li) : selectProceso(li);
    const id = "ord-pe-" + li.getAttribute("data-k");
    const previo = document.getElementById(id);
    if (previo) previo.remove();
    campo.insertAdjacentElement("afterend", UI.el("p", { "class": "err", id: id, role: "alert", "data-error": true }, mensaje));
    UI.invalido(campo, id);
    return campo;
  }

  function marcarImporteProceso(li, mensaje) {
    const campo = importeProceso(li);
    const id = "ord-pi-" + li.getAttribute("data-k");
    const previo = document.getElementById(id);
    if (previo) previo.remove();
    campo.parentElement.insertAdjacentElement("afterend", UI.el("p", { "class": "err", id: id, role: "alert", "data-error": true }, mensaje));
    UI.invalido(campo, id);
    return campo;
  }

  function leerProcesos() {
    return Procesos.armar(
      lineasProc().map((li) => ({
        valor: selectProceso(li).value,
        texto: textoProceso(li).value,
        precio: Precios.parsear(importeProceso(li).value).centavos
      })),
      catalogoProcesos
    );
  }

  function recargarProcesos() {
    return cargarProcesos().then(() => {
      lineasProc().forEach((li) => llenarSelectProceso(selectProceso(li), true));
      renumerarProcesos();
    });
  }

  // Servicio general de la orden (C-06g): un select (catalogo + "Sin servicio general") y, debajo, la
  // lista de solo lectura "Incluye:" con los chequeos del servicio elegido. Cero o un servicio.
  const MSG_SERVICIOS_CAIDOS = "No se pudo cargar la lista de servicios generales.";

  function mostrarAvisoServicio(mensaje) {
    const p = $("ord-servicio-aviso");
    p.textContent = mensaje || "";
    p.hidden = !mensaje;
  }

  function marcarServicio(mensaje) {
    mostrarAvisoServicio(mensaje);
    const select = $("ord-servicio");
    select.setAttribute("aria-invalid", "true");
    select.setAttribute("aria-describedby", "ord-servicio-aviso ord-servicio-inc");
    return select;
  }

  function cargarServicios() {
    return Api.get("/api/servicios-generales").then(
      (lista) => { catalogoServicios = lista; serviciosFallo = false; },
      () => { catalogoServicios = []; serviciosFallo = true; }
    );
  }

  function mostrarChequeos() {
    const clave = $("ord-servicio").value;
    const lista = UI.vaciar($("ord-servicio-chequeos"));
    const chequeos = Servicios.chequeosDe(clave, catalogoServicios);
    chequeos.forEach((c) => lista.appendChild(UI.el("li", { "class": "chip" }, c)));
    const servicio = catalogoServicios.find((s) => s.clave === clave);
    lista.setAttribute("aria-label", servicio ? "Chequeos de " + servicio.nombre : "Chequeos");
    $("ord-servicio-inc").hidden = chequeos.length === 0;
    const precio = $("ord-servicio-precio");
    precio.disabled = clave === "";
    if (precio.disabled) precio.value = "";
    actualizarResumen();
  }

  function llenarSelectServicio() {
    const select = UI.vaciar($("ord-servicio"));
    select.appendChild(UI.el("option", { value: "" }, "Sin servicio general"));
    catalogoServicios.forEach((s) => select.appendChild(UI.el("option", { value: s.clave }, s.nombre)));
    select.value = "";
    mostrarChequeos();
  }

  function recargarServicios() {
    return cargarServicios().then(llenarSelectServicio);
  }

  function lineas() {
    return Array.from(document.querySelectorAll("#ord-lineas > li"));
  }

  // Vista previa de subtotales y total (solo en pantalla, nunca se envia). Importes vacios o
  // todavia invalidos cuentan 0 (Precios.parsear devuelve centavos null).
  function centavosDe(campo) {
    return Precios.parsear(campo.value).centavos;
  }

  function actualizarResumen() {
    const r = Precios.resumen({
      servicio: centavosDe($("ord-servicio-precio")),
      adicionales: lineasProc().map((li) => centavosDe(importeProceso(li))),
      items: lineas().map((li) => centavosDe(inputImporte(li)))
    });
    $("ord-sub-servicios").textContent = Precios.formatear(r.subtotal_servicios);
    $("ord-sub-items").textContent = Precios.formatear(r.subtotal_items);
    $("ord-total").textContent = Precios.formatear(r.total);
  }

  const CAMPOS_DATOS = {
    cliente: "ord-cliente", celular: "ord-celular", casco: "ord-casco", motor: "ord-motor",
    trailer: "ord-trailer", fecha_ingreso: "ord-ingreso", fecha_egreso: "ord-egreso"
  };

  function leerDatosCliente() {
    const campos = {};
    Object.keys(CAMPOS_DATOS).forEach((c) => { campos[c] = $(CAMPOS_DATOS[c]).value; });
    return DatosOrden.validar(campos);
  }

  function limpiarMarcaLinea(li) {
    li.removeAttribute("data-invalid");
    li.querySelectorAll("[data-error]").forEach((n) => n.remove());
    li.querySelectorAll("[aria-invalid]").forEach((c) => { c.removeAttribute("aria-invalid"); c.removeAttribute("aria-describedby"); });
  }

  function marcarLinea(li, campo, mensaje, comoAlerta) {
    li.setAttribute("data-invalid", "");
    const idx = lineas().indexOf(li) + 1;
    const id = "ord-l" + idx + (campo.tagName === "SELECT" ? "-p" : campo.hasAttribute("data-imp") ? "-i" : "-c") + "-e";
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
      selectProducto(li).setAttribute("aria-label", "Producto del componente " + n);
      selectCategoria(li).setAttribute("aria-label", "Categoría de la línea " + n);
      inputCantidad(li).setAttribute("aria-label", "Cantidad del componente " + n);
      inputImporte(li).setAttribute("aria-label", "Importe de la línea " + n);
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
    secuenciaLinea += 1;
    const li = UI.el("li", { "data-row": true, "data-k": String(secuenciaLinea) });
    const fila = UI.el("div", { "class": "line line-p" });
    fila.appendChild(UI.el("span", { "class": "line-n", "aria-hidden": "true" }, "0"));
    fila.appendChild(UI.el("select", { "class": "field", "data-cat": true }));
    const select = UI.el("select", { "class": "field", "data-opts": true });
    fila.appendChild(select);
    fila.appendChild(UI.el("input", {
      "class": "field num", inputmode: "numeric", autocomplete: "off", "data-cant": true, value: cantidad || ""
    }));
    const importe = UI.el("div", { "class": "money" });
    importe.appendChild(UI.el("input", {
      "class": "field", inputmode: "decimal", autocomplete: "off", placeholder: "0,00", "data-imp": true
    }));
    fila.appendChild(importe);
    fila.appendChild(UI.el("button", { "class": "btn btn-secondary", type: "button", "data-quitar": true }, "Quitar"));
    li.appendChild(fila);
    llenarSelectCategoria(selectCategoria(li), "Todas", true);
    llenarSelect(select, false, "");
    if (codigo) select.value = codigo;
    return li;
  }

  function agregarLinea() {
    if (lineas().length >= MAX_LINEAS) return;
    const li = nuevaLinea();
    $("ord-lineas").appendChild(li);
    renumerar();
    actualizarResumen();
    selectProducto(li).focus();
  }

  function quitarLinea(li) {
    const filas = lineas();
    if (filas.length <= 1) return;
    const i = filas.indexOf(li);
    li.remove();
    renumerar();
    actualizarResumen();
    const resto = lineas();
    selectProducto(resto[Math.min(i, resto.length - 1)]).focus();
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
    UI.vaciar($("ord-procesos"));
    mostrarAvisoProcesos(procesosFallo ? MSG_ADICIONALES_CAIDOS : "");
    renumerarProcesos();
    llenarSelectServicio();
    mostrarAvisoServicio(serviciosFallo ? MSG_SERVICIOS_CAIDOS : "");
    actualizarResumen();
    UI.abrir($("modal-orden"));
  }

  function ocultarErrorGeneral() {
    const p = $("ord-general-e");
    p.textContent = "";
    p.hidden = true;
  }

  function leerLineas() {
    return lineas().map((li) => ({
      codigo: selectProducto(li).value,
      cantidad: inputCantidad(li).value
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
    const datos = leerDatosCliente();
    Object.keys(CAMPOS_DATOS).forEach((c) => {
      if (!datos.errores[c]) return;
      const campo = $(CAMPOS_DATOS[c]);
      UI.errorBajoCampo(campo, datos.errores[c]);
      primero = primero || campo;
    });
    const rs = Servicios.armar($("ord-servicio").value, catalogoServicios);
    mostrarAvisoServicio(serviciosFallo ? MSG_SERVICIOS_CAIDOS : "");
    if (rs.error) {
      const select = marcarServicio(rs.error);
      primero = primero || select;
    }
    const precioServicio = Precios.parsear($("ord-servicio-precio").value);
    if (precioServicio.error) {
      const campo = $("ord-servicio-precio");
      UI.errorBajoCampo(campo, precioServicio.error, campo.parentElement);
      primero = primero || campo;
    }
    const r = Validacion.componentes(leerLineas());
    const rp = leerProcesos();
    lineasProc().forEach((li, i) => {
      const e = selectProceso(li).value === "" ? "Elegí un servicio adicional o quitá la línea." : rp.errores[i];
      if (e) {
        const campo = marcarProceso(li, e);
        primero = primero || campo;
      }
      const importe = Precios.parsear(importeProceso(li).value);
      if (importe.error) {
        const campo = marcarImporteProceso(li, importe.error);
        primero = primero || campo;
      }
    });
    if (r.general) {
      const p = $("ord-general-e");
      p.textContent = r.general;
      p.hidden = false;
    }
    lineas().forEach((li, i) => {
      const e = r.porLinea[i];
      if (!e) return;
      if (e.producto) {
        marcarLinea(li, selectProducto(li), e.producto, true);
        primero = primero || selectProducto(li);
      }
      if (e.cantidad) {
        marcarLinea(li, inputCantidad(li), e.cantidad, true);
        primero = primero || inputCantidad(li);
      }
      const importe = Precios.parsear(inputImporte(li).value);
      if (importe.error) {
        marcarLinea(li, inputImporte(li), importe.error, true);
        primero = primero || inputImporte(li);
      }
    });
    if (primero) primero.focus();
    return primero === null && !r.general;
  }

  // Campo de "Cliente y embarcacion" al que apunta un 422 del backend (o null).
  function campoDeDatos(detalle) {
    if (/^La fecha de ingreso/.test(detalle)) return $("ord-ingreso");
    if (/^La fecha de egreso/.test(detalle)) return $("ord-egreso");
    if (/^El cliente /.test(detalle) || /^El campo cliente /.test(detalle)) return $("ord-cliente");
    if (/^El celular /.test(detalle) || /^El campo celular /.test(detalle)) return $("ord-celular");
    const m = /^El campo (casco|motor|trailer) /.exec(detalle);
    return m ? $("ord-" + m[1]) : null;
  }

  function mapearErrorOrden(err, alerta) {
    UI.alerta(alerta, err.detail, "error");
    alerta.id = "ord-alerta";
    const filas = lineas();
    let foco = null;
    if (err.status === 409 && err.faltantes) {
      err.faltantes.forEach((f) => {
        filas.forEach((li) => {
          if (selectProducto(li).value !== f.codigo) return;
          const campo = inputCantidad(li);
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
          const select = selectProducto(li);
          if (citados.indexOf(select.value) === -1) return;
          marcarLinea(li, select, "Este producto ya no está activo: elegí otro o quitá la línea.", false);
          foco = foco || select;
        });
        if (foco) foco.focus();
      });
      return;
    } else if (err.status === 422 && (/^El servicio general '.*' no existe\.$/.test(err.detail) ||
        err.detail === "El campo servicio debe ser texto.")) {
      // Un servicio borrado desde otra parte: se recarga el catalogo (el selector vuelve a "Sin servicio
      // general") y el modal sigue abierto con el resto de los datos.
      const select = marcarServicio(err.detail);
      recargarServicios().then(() => select.scrollIntoView && select.scrollIntoView({ block: "nearest" }));
      select.focus();
      return;
    } else if (err.status === 422 && /^El proceso '.*' no existe\.$/.test(err.detail)) {
      // Un proceso borrado desde otra parte: se recarga el catalogo y el modal sigue abierto con los datos.
      mostrarAvisoProcesos(err.detail);
      recargarProcesos().then(() => $("ord-proc-aviso").scrollIntoView && $("ord-proc-aviso").scrollIntoView({ block: "nearest" }));
      return;
    } else if (err.status === 422 && procesoDeError(err.detail)) {
      const p = procesoDeError(err.detail);
      foco = p.importe ? marcarImporteProceso(p.li, p.mensaje) : marcarProceso(p.li, p.mensaje);
    } else if (err.status === 422 && campoDeDatos(err.detail)) {
      foco = campoDeDatos(err.detail);
      UI.errorBajoCampo(foco, err.detail);
    } else if (err.status === 422 && err.detail.indexOf("precio del servicio general") !== -1) {
      foco = $("ord-servicio-precio");
      UI.errorBajoCampo(foco, err.detail, foco.parentElement);
    } else if (err.status === 422) {
      const m = /^Componente (\d+):\s*(.*)$/.exec(err.detail);
      if (m && filas[Number(m[1]) - 1]) {
        const li = filas[Number(m[1]) - 1];
        const campo = /producto|código/i.test(m[2]) ? selectProducto(li)
          : /precio/i.test(m[2]) ? inputImporte(li) : inputCantidad(li);
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
    const importes = lineas().map((li) => centavosDe(inputImporte(li)));
    const cuerpo = {
      numero: $("ord-numero").value.trim(),
      fecha: $("ord-fecha").value.trim(),
      componentes: leerLineas().map((l, i) => ({
        codigo: l.codigo, cantidad: Number(l.cantidad.trim()), precio: importes[i]
      }))
    };
    const datos = leerDatosCliente().valores;
    Object.keys(CAMPOS_DATOS).forEach((c) => { cuerpo[c] = datos[c]; });
    const rp = leerProcesos();
    cuerpo.procesos = rp.procesos;
    cuerpo.procesos_personalizados = rp.procesos_personalizados;
    const rsv = Servicios.armar($("ord-servicio").value, catalogoServicios);
    cuerpo.servicio = rsv.servicio;
    cuerpo.precio_servicio = rsv.servicio === null ? null : centavosDe($("ord-servicio-precio"));
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

    $("form-orden").addEventListener("input", (e) => {
      if (e.target.matches(".money input")) actualizarResumen();
    });
    $("ord-agregar").addEventListener("click", agregarLinea);
    $("ord-lineas").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar]");
      if (q) quitarLinea(q.closest("li"));
    });
    $("ord-lineas").addEventListener("change", (e) => {
      if (!e.target.matches("select[data-cat]")) return;
      const li = e.target.closest("li");
      refrescarLinea(li, false);
    });
    $("ord-proc-agregar").addEventListener("click", agregarProceso);
    $("ord-procesos").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar-proc]");
      if (q) quitarProceso(q.closest("li"));
    });
    $("ord-procesos").addEventListener("change", (e) => {
      if (!e.target.matches("select[data-proc]")) return;
      renumerarProcesos();
      if (e.target.value === PERSONALIZADO) textoProceso(e.target.closest("li")).focus();
    });
    $("ord-servicio").addEventListener("change", mostrarChequeos);
    $("form-orden").addEventListener("submit", enviarOrden);

    $("baja-confirmar").addEventListener("click", confirmarBaja);

    llenarSelectoresCategoria();
    cargarCategorias();
    cargarProcesos();
    cargarServicios();
    cargar(true);
  });
})();
