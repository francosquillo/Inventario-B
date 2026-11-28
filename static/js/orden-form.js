/* orden-form.js: formulario de orden compartido por "Nueva orden" (/inventario) y "Editar orden" (/ordenes)
   (specs interfaz-web: Nueva orden, Servicio general, Servicios adicionales, Datos del cliente, Chequeo final,
   Modal de edicion, Errores por linea). `window.OrdenForm.montar(opciones)` conecta el formulario ya presente en
   la pagina (ids `ord-*`) y devuelve el controlador. No toca el DOM al cargar el archivo. Datos solo con
   textContent / createElement (design D4). */
(function () {
  "use strict";

  const UI = window.UI;
  const Api = window.Api;
  const MAX_LINEAS = 100;
  const ACTUAL = "__actual__";   // opcion "Servicio (actual)": conserva el servicio guardado en la orden
  const PERSONALIZADO = Procesos.PERSONALIZADO;
  const MSG_ADICIONALES_CAIDOS = "No se pudo cargar la lista de servicios adicionales.";
  const MSG_SERVICIOS_CAIDOS = "No se pudo cargar la lista de servicios generales.";
  const AYUDA_SIN_PRODUCTOS = "No hay productos en esta categoría.";

  const $ = (id) => document.getElementById(id);

  // Importe de la API (centavos) -> texto de la caja, sin el "$ " (que pone el CSS): "45.000,00" o "".
  function importeTexto(centavos) {
    return centavos == null ? "" : Precios.formatear(centavos).replace(/^\$ /, "");
  }

  // opciones: {
  //   modo: "nueva" | "editar", formId, modalId,
  //   recargarProductos(): Promise  (vuelve a pedir el inventario y llama a setProductos),
  //   alCrear / alEditar(resultado): tras el exito (la pagina cierra el modal y avisa),
  //   alOrdenInexistente(): solo editar, la orden ya no existe
  // }
  function montar(opciones) {
    const editar = opciones.modo === "editar";
    let productos = [];
    let categorias = [];        // catalogo [{clave, nombre}] (solo "nueva": filtro por linea)
    let catalogoProcesos = [];  // [{clave, nombre}] (vacio si fallo la carga)
    let procesosFallo = false;
    let catalogoServicios = []; // [{clave, nombre, chequeos}] (vacio si fallo la carga)
    let serviciosFallo = false;
    let secuenciaLinea = 0;
    let orden = null;           // solo editar: la orden de la lista que se esta editando
    let enOrden = {};           // solo editar: codigo -> cantidad que la orden ya descontaba

    // ---------------------------------------------------------------- lineas de componentes

    function etiquetaProducto(p) {
      const enEsta = enOrden[p.codigo] ? " + " + enOrden[p.codigo] + " en esta orden" : "";
      return p.codigo + " · " + p.nombre + " (stock " + p.stock + enEsta + ")";
    }

    // Llena un <select> de categoria. `primera`: texto de la opcion vacia; `conSin` agrega "Sin categoria".
    function llenarSelectCategoria(select, primera, conSin) {
      const previo = select.value;
      UI.vaciar(select);
      select.appendChild(UI.el("option", { value: "" }, primera));
      categorias.forEach((c) => select.appendChild(UI.el("option", { value: c.clave }, c.nombre)));
      if (conSin) select.appendChild(UI.el("option", { value: Busqueda.SIN_CATEGORIA }, "Sin categoría"));
      const existe = Array.from(select.options).some((o) => o.value === previo);
      select.value = existe ? previo : "";
    }

    // Llena un <select> con los productos activos. `conservar`: si el valor previo ya no esta, se deja visible.
    // `categoria` filtra la lista ("" = todas; "__sin__" = sin categoria); si el producto elegido no pertenece, se resetea.
    // Una linea de la orden con un producto dado de baja (data-baja) lo conserva solo en su propia linea.
    function llenarSelect(select, conservar, categoria) {
      const previo = select.value;
      const lista = Busqueda.porCategoria(productos, categoria);
      UI.vaciar(select);
      select.appendChild(UI.el("option", { value: "" }, "Elegí un producto…"));
      lista.forEach((p) => select.appendChild(UI.el("option", { value: p.codigo }, etiquetaProducto(p))));
      const baja = select.getAttribute("data-baja");
      if (baja) {
        select.appendChild(UI.el("option", { value: baja }, baja + " · " + (nombreEnOrden(baja) || "") + " (dado de baja)"));
        if (previo === baja) { select.value = previo; return; }
      }
      if (previo && Busqueda.productoSigueVisible(previo, productos, categoria)) {
        select.value = previo;
      } else if (previo && conservar) {
        select.appendChild(UI.el("option", { value: previo }, previo + " · (ya no está activo)"));
        select.value = previo;
      }
    }

    function nombreEnOrden(codigo) {
      const c = orden ? orden.componentes.find((x) => x.codigo === codigo) : null;
      return c ? c.nombre : null;
    }

    function selectProducto(li) { return li.querySelector("select[data-opts]"); }
    function selectCategoria(li) { return li.querySelector("select[data-cat]"); }
    function inputCantidad(li) { return li.querySelector("input[data-cant]"); }
    function inputImporte(li) { return li.querySelector("input[data-imp]"); }

    function categoriaDe(li) {
      const s = selectCategoria(li);
      return s ? s.value : "";
    }

    // Nueva orden: ayuda bajo la linea cuando el filtro de categoria no deja ningun producto.
    // Editar orden: cuanto se puede pedir (stock + lo ya descontado) o aviso de producto dado de baja.
    function actualizarAyudaLinea(li) {
      const id = "ord-" + li.getAttribute("data-k") + "-vacio";
      const previa = document.getElementById(id);
      if (previa) previa.remove();
      selectProducto(li).removeAttribute("aria-describedby");
      const texto = editar ? ayudaEdicion(li) : ayudaCategoria(li);
      if (!texto) return;
      const p = UI.el("p", { "class": "help line-help", id: id });
      if (texto.baja) p.appendChild(UI.el("span", { "class": "tag-baja" }, "Dado de baja"));
      p.appendChild(document.createTextNode((texto.baja ? " " : "") + texto.mensaje));
      li.appendChild(p);
      selectProducto(li).setAttribute("aria-describedby", id);
    }

    function ayudaCategoria(li) {
      const categoria = categoriaDe(li);
      const vacia = Busqueda.porCategoria(productos, categoria).length === 0;
      return vacia && categoria !== "" ? { mensaje: AYUDA_SIN_PRODUCTOS } : null;
    }

    function ayudaEdicion(li) {
      const codigo = selectProducto(li).value;
      if (!codigo) return null;
      if (selectProducto(li).getAttribute("data-baja") === codigo) {
        return {
          baja: true,
          mensaje: "Podés dejarlo o bajar la cantidad; quitarlo devuelve el stock y lo reactiva."
        };
      }
      const previo = enOrden[codigo];
      const producto = productos.find((p) => p.codigo === codigo);
      if (!previo || !producto) return null;
      return {
        mensaje: "Hasta " + (producto.stock + previo) + ": " + producto.stock + " en stock + " + previo +
          " ya descontados por esta orden."
      };
    }

    function refrescarLinea(li, conservar) {
      llenarSelect(selectProducto(li), conservar, categoriaDe(li));
      actualizarAyudaLinea(li);
    }

    function refrescarSelects(conservar) {
      lineas().forEach((li) => refrescarLinea(li, conservar));
    }

    function refrescarCategorias() {
      document.querySelectorAll("#ord-lineas select[data-cat]").forEach((s) => llenarSelectCategoria(s, "Todas", true));
    }

    // ---------------------------------------------------------------- procesos (servicios adicionales)

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

    // "Proceso N: ..." (lista del catalogo) o "Proceso personalizado N: ..." -> {li, mensaje, importe}
    // con la linea de la orden que corresponde; `importe` si el error es del precio.
    function procesoDeError(detail) {
      const m = /^Proceso (personalizado )?(\d+):\s*(.*)$/.exec(detail);
      if (!m) return null;
      const delTipo = lineasProc().filter((li) => (selectProceso(li).value === PERSONALIZADO) === Boolean(m[1]));
      const li = delTipo[Number(m[2]) - 1];
      return li ? { li: li, mensaje: m[3], importe: /precio/i.test(m[3]) } : null;
    }

    // Editar: un proceso guardado se precarga como el del catalogo con el mismo nombre; si el catalogo ya no
    // lo tiene (o era personalizado) se precarga como personalizado con su nombre (design D5).
    function precargarProcesos(procesos) {
      procesos.forEach((p) => {
        const li = nuevaLineaProceso();
        $("ord-procesos").appendChild(li);
        const delCatalogo = p.personalizado ? null
          : catalogoProcesos.find((c) => c.nombre.toLowerCase() === p.nombre.toLowerCase());
        if (delCatalogo) {
          selectProceso(li).value = delCatalogo.clave;
        } else {
          selectProceso(li).value = PERSONALIZADO;
          textoProceso(li).value = p.nombre;
        }
        importeProceso(li).value = importeTexto(p.precio);
      });
    }

    // ---------------------------------------------------------------- servicio general

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

    // Servicio elegido en el selector -> {servicio: clave|null, conservar: bool, error}.
    function servicioElegido() {
      const valor = $("ord-servicio").value;
      if (valor === ACTUAL) return { servicio: null, conservar: true, error: null };
      const r = Servicios.armar(valor, catalogoServicios);
      return { servicio: r.servicio, conservar: false, error: r.error };
    }

    function mostrarChequeos() {
      const clave = $("ord-servicio").value;
      const lista = UI.vaciar($("ord-servicio-chequeos"));
      const actual = clave === ACTUAL && orden && orden.servicio;
      const chequeos = actual ? orden.servicio.chequeos : Servicios.chequeosDe(clave, catalogoServicios);
      chequeos.forEach((c) => lista.appendChild(UI.el("li", { "class": "chip" }, c)));
      const servicio = catalogoServicios.find((s) => s.clave === clave);
      const nombre = actual ? orden.servicio.nombre : servicio ? servicio.nombre : null;
      lista.setAttribute("aria-label", nombre ? "Chequeos de " + nombre : "Chequeos");
      $("ord-servicio-inc").querySelector(".lbl").textContent = actual ? "Incluye (guardado en la orden):" : "Incluye:";
      $("ord-servicio-inc").hidden = chequeos.length === 0;
      const precio = $("ord-servicio-precio");
      precio.disabled = clave === "";
      if (precio.disabled) precio.value = "";
      actualizarResumen();
    }

    function llenarSelectServicio() {
      const select = UI.vaciar($("ord-servicio"));
      const conActual = Boolean(orden && orden.servicio);
      if (conActual) select.appendChild(UI.el("option", { value: ACTUAL }, orden.servicio.nombre + " (actual)"));
      select.appendChild(UI.el("option", { value: "" }, "Sin servicio general"));
      catalogoServicios.forEach((s) => select.appendChild(UI.el("option", { value: s.clave }, s.nombre)));
      select.value = conActual ? ACTUAL : "";
      mostrarChequeos();
    }

    function recargarServicios() {
      return cargarServicios().then(llenarSelectServicio);
    }

    // ---------------------------------------------------------------- chequeo final (solo editar)

    function filasChequeo() {
      return Array.from(document.querySelectorAll("#ord-chequeo > li"));
    }

    function construirChequeo(marcados) {
      const lista = UI.vaciar($("ord-chequeo"));
      const porClave = {};
      (marcados || []).forEach((c) => { porClave[c.clave] = c; });
      ChequeoFinal.ITEMS.forEach((item) => {
        const hecho = porClave[item.clave];
        const li = UI.el("li", { "class": "chk-row", "data-clave": item.clave });
        const etiqueta = UI.el("label", { "class": "chk-lbl" });
        const casilla = UI.el("input", { "class": "check", type: "checkbox", "data-chk": item.clave });
        casilla.checked = Boolean(hecho);
        etiqueta.appendChild(casilla);
        etiqueta.appendChild(document.createTextNode(" " + item.nombre));
        li.appendChild(etiqueta);
        const caja = UI.el("div", { "class": "money" });
        const importe = UI.el("input", {
          "class": "field", id: "ord-chk-imp-" + item.clave, inputmode: "decimal", autocomplete: "off",
          placeholder: "0,00", "data-chk-imp": item.clave, "aria-label": "Importe de " + item.nombre
        });
        importe.disabled = !hecho;
        importe.value = hecho ? importeTexto(hecho.precio) : "";
        caja.appendChild(importe);
        li.appendChild(caja);
        lista.appendChild(li);
      });
    }

    function importeChequeo(li) { return li.querySelector("input[data-chk-imp]"); }
    function casillaChequeo(li) { return li.querySelector("input[data-chk]"); }

    function estadoChequeo() {
      return filasChequeo().map((li) => ({
        clave: casillaChequeo(li).getAttribute("data-chk"),
        marcado: casillaChequeo(li).checked,
        importe: importeChequeo(li).value
      }));
    }

    function alCambiarChequeo(e) {
      if (!e.target.matches("input[data-chk]")) return;
      const li = e.target.closest("li");
      const importe = importeChequeo(li);
      importe.disabled = !e.target.checked;
      if (!e.target.checked) {
        importe.value = "";
        UI.limpiarErrores(li);
      } else {
        importe.focus();
      }
      actualizarResumen();
    }

    // ---------------------------------------------------------------- resumen

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
        items: lineas().map((li) => centavosDe(inputImporte(li))),
        chequeo_final: filasChequeo().filter((li) => casillaChequeo(li).checked).map((li) => centavosDe(importeChequeo(li)))
      });
      $("ord-sub-servicios").textContent = Precios.formatear(r.subtotal_servicios);
      $("ord-sub-items").textContent = Precios.formatear(r.subtotal_items);
      $("ord-total").textContent = Precios.formatear(r.total);
    }

    // ---------------------------------------------------------------- datos del cliente

    const CAMPOS_DATOS = {
      cliente: "ord-cliente", celular: "ord-celular", casco: "ord-casco", motor: "ord-motor",
      trailer: "ord-trailer", fecha_ingreso: "ord-ingreso", fecha_egreso: "ord-egreso"
    };

    function leerDatosCliente() {
      const campos = {};
      Object.keys(CAMPOS_DATOS).forEach((c) => { campos[c] = $(CAMPOS_DATOS[c]).value; });
      return DatosOrden.validar(campos);
    }

    // ---------------------------------------------------------------- lineas de componentes (DOM)

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
        selectProducto(li).setAttribute("aria-label", editar ? "Producto de la línea " + n : "Producto del componente " + n);
        const cat = selectCategoria(li);
        if (cat) cat.setAttribute("aria-label", "Categoría de la línea " + n);
        inputCantidad(li).setAttribute("aria-label", editar ? "Cantidad de la línea " + n : "Cantidad del componente " + n);
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

    function nuevaLinea(codigo, cantidad, importe) {
      secuenciaLinea += 1;
      const li = UI.el("li", { "data-row": true, "data-k": String(secuenciaLinea) });
      const fila = UI.el("div", { "class": "line line-p" + (editar ? " line-sc" : "") });
      fila.appendChild(UI.el("span", { "class": "line-n", "aria-hidden": "true" }, "0"));
      if (!editar) fila.appendChild(UI.el("select", { "class": "field", "data-cat": true }));
      const select = UI.el("select", { "class": "field", "data-opts": true });
      if (editar && codigo && !productos.some((p) => p.codigo === codigo)) select.setAttribute("data-baja", codigo);
      fila.appendChild(select);
      fila.appendChild(UI.el("input", {
        "class": "field num", inputmode: "numeric", autocomplete: "off", "data-cant": true, value: cantidad || ""
      }));
      const caja = UI.el("div", { "class": "money" });
      caja.appendChild(UI.el("input", {
        "class": "field", inputmode: "decimal", autocomplete: "off", placeholder: "0,00", "data-imp": true,
        value: importe || ""
      }));
      fila.appendChild(caja);
      fila.appendChild(UI.el("button", { "class": "btn btn-secondary", type: "button", "data-quitar": true }, "Quitar"));
      li.appendChild(fila);
      if (!editar) llenarSelectCategoria(selectCategoria(li), "Todas", true);
      llenarSelect(select, false, "");
      if (codigo) select.value = codigo;
      if (editar) actualizarAyudaLinea(li);
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

    function ocultarErrorGeneral() {
      const p = $("ord-general-e");
      p.textContent = "";
      p.hidden = true;
    }

    // Nueva orden: formulario vacio con la fecha de hoy. Editar: precargado con `existente` (objeto de GET /api/ordenes).
    function abrir(existente) {
      orden = editar ? existente : null;
      enOrden = {};
      if (orden) orden.componentes.forEach((c) => { enOrden[c.codigo] = c.cantidad; });
      const form = $(opciones.formId);
      form.reset();
      UI.limpiarErrores(form);
      UI.ocultarAlerta($("ord-alerta"));
      ocultarErrorGeneral();
      UI.vaciar($("ord-lineas"));
      UI.vaciar($("ord-procesos"));
      if (orden) {
        $("ord-titulo-num").textContent = orden.numero;
        $("ord-numero-fijo").textContent = orden.numero + " (no se puede cambiar)";
        $("ord-fecha").value = orden.fecha;
        Object.keys(CAMPOS_DATOS).forEach((c) => { $(CAMPOS_DATOS[c]).value = orden[c] || ""; });
        orden.componentes.forEach((c) => {
          $("ord-lineas").appendChild(nuevaLinea(c.codigo, String(c.cantidad), importeTexto(c.precio)));
        });
        precargarProcesos(orden.procesos || []);
        construirChequeo(orden.chequeo_final);
      } else {
        $("ord-fecha").value = Validacion.hoy();
        $("ord-lineas").appendChild(nuevaLinea());
      }
      renumerar();
      mostrarAvisoProcesos(procesosFallo ? MSG_ADICIONALES_CAIDOS : "");
      renumerarProcesos();
      llenarSelectServicio();
      if (orden && orden.servicio) $("ord-servicio-precio").value = importeTexto(orden.servicio.precio);
      mostrarAvisoServicio(serviciosFallo ? MSG_SERVICIOS_CAIDOS : "");
      actualizarResumen();
      UI.abrir($(opciones.modalId));
    }

    function leerLineas() {
      return lineas().map((li) => ({
        codigo: selectProducto(li).value,
        cantidad: inputCantidad(li).value
      }));
    }

    // ---------------------------------------------------------------- validacion y envio

    function validarOrden(form) {
      UI.limpiarErrores(form);
      lineas().forEach(limpiarMarcaLinea);
      ocultarErrorGeneral();
      const numero = $("ord-numero"), fecha = $("ord-fecha");
      let primero = null;
      if (numero) {
        const eNumero = Validacion.requerido(numero.value, "El número de orden") || Validacion.largo(numero.value, 30, "El número de orden");
        if (eNumero) { UI.errorBajoCampo(numero, eNumero); primero = numero; }
      }
      const eFecha = Validacion.fecha(fecha.value);
      if (eFecha) { UI.errorBajoCampo(fecha, eFecha, fecha); primero = primero || fecha; }
      const datos = leerDatosCliente();
      Object.keys(CAMPOS_DATOS).forEach((c) => {
        if (!datos.errores[c]) return;
        const campo = $(CAMPOS_DATOS[c]);
        UI.errorBajoCampo(campo, datos.errores[c]);
        primero = primero || campo;
      });
      const rs = servicioElegido();
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
      if (editar) {
        const rc = ChequeoFinal.leer(estadoChequeo());
        filasChequeo().forEach((li, i) => {
          if (!rc.errores[i]) return;
          const campo = importeChequeo(li);
          UI.errorBajoCampo(campo, rc.errores[i], campo.parentElement);
          primero = primero || campo;
        });
      }
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

    // Codigos citados por un 404 de productos: `codigos` de la API (edicion) o los entrecomillados del mensaje (alta).
    function codigosCitados(err) {
      return err.codigos || (err.detail.match(/'([^']*)'/g) || []).map((s) => s.slice(1, -1));
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
      } else if (err.status === 404 && editar && /^No existe una orden /.test(err.detail)) {
        // La orden se borro desde otra parte: el modal queda con el mensaje y la lista se recarga al cerrarlo.
        $("ord-enviar").disabled = true;
        opciones.alOrdenInexistente();
        return;
      } else if (err.status === 404) {
        const citados = codigosCitados(err);
        opciones.recargarProductos().then(() => {
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
          err.detail === "El campo servicio debe ser texto." ||
          err.detail === "La orden no tiene un servicio general para conservar.")) {
        // Un servicio borrado desde otra parte: se recarga el catalogo (el selector vuelve a su opcion inicial)
        // y el modal sigue abierto con el resto de los datos.
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
      } else if (err.status === 422 && editar && /^Chequeo final (\d+):/.test(err.detail)) {
        const n = Number(/^Chequeo final (\d+):/.exec(err.detail)[1]);
        const li = filasChequeo().filter((f) => casillaChequeo(f).checked)[n - 1];
        if (li) {
          foco = importeChequeo(li);
          UI.errorBajoCampo(foco, err.detail.replace(/^Chequeo final \d+:\s*/, ""), foco.parentElement);
        }
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

    function armarCuerpo() {
      const importes = lineas().map((li) => centavosDe(inputImporte(li)));
      const cuerpo = {};
      if (!editar) cuerpo.numero = $("ord-numero").value.trim();
      cuerpo.fecha = $("ord-fecha").value.trim();
      cuerpo.componentes = leerLineas().map((l, i) => ({
        codigo: l.codigo, cantidad: Number(l.cantidad.trim()), precio: importes[i]
      }));
      const datos = leerDatosCliente().valores;
      Object.keys(CAMPOS_DATOS).forEach((c) => { cuerpo[c] = datos[c]; });
      const rp = leerProcesos();
      cuerpo.procesos = rp.procesos;
      cuerpo.procesos_personalizados = rp.procesos_personalizados;
      const rsv = servicioElegido();
      cuerpo.servicio = rsv.servicio;
      cuerpo.precio_servicio = rsv.servicio === null && !rsv.conservar ? null : centavosDe($("ord-servicio-precio"));
      if (editar) {
        cuerpo.conservar_servicio = rsv.conservar;
        cuerpo.chequeo_final = ChequeoFinal.leer(estadoChequeo()).valores;
      }
      return cuerpo;
    }

    function enviarOrden(e) {
      e.preventDefault();
      const form = $(opciones.formId), boton = $("ord-enviar"), alerta = $("ord-alerta");
      if (boton.disabled) return;
      UI.ocultarAlerta(alerta);
      if (!validarOrden(form)) return;
      const cuerpo = armarCuerpo();
      const restaurar = UI.ocupado(boton, editar ? "Guardando…" : "Creando orden…");
      const pedido = editar
        ? Api.put("/api/ordenes/" + encodeURIComponent(orden.numero), cuerpo)
        : Api.post("/api/ordenes", cuerpo);
      pedido.then(
        (resultado) => {
          restaurar();
          UI.cerrar();
          opciones.alExito(resultado);
        },
        (err) => {
          restaurar();
          mapearErrorOrden(err, alerta);
        }
      );
    }

    // ---------------------------------------------------------------- conexion con el formulario

    const form = $(opciones.formId);
    form.addEventListener("input", (e) => {
      if (e.target.matches(".money input")) actualizarResumen();
    });
    $("ord-agregar").addEventListener("click", agregarLinea);
    $("ord-lineas").addEventListener("click", (e) => {
      const q = e.target.closest("[data-quitar]");
      if (q) quitarLinea(q.closest("li"));
    });
    $("ord-lineas").addEventListener("change", (e) => {
      const li = e.target.closest("li");
      if (e.target.matches("select[data-cat]")) refrescarLinea(li, false);
      else if (editar && e.target.matches("select[data-opts]")) actualizarAyudaLinea(li);
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
    if (editar) $("ord-chequeo").addEventListener("change", alCambiarChequeo);
    form.addEventListener("submit", enviarOrden);

    return {
      setProductos: (lista) => { productos = lista; },
      setCategorias: (lista) => { categorias = lista; },
      cargarCatalogos: () => Promise.all([cargarProcesos(), cargarServicios()]),
      refrescarSelects: refrescarSelects,
      refrescarCategorias: refrescarCategorias,
      abrir: abrir
    };
  }

  window.OrdenForm = { montar: montar, ACTUAL: ACTUAL, AYUDA_SIN_PRODUCTOS: AYUDA_SIN_PRODUCTOS };
})();
