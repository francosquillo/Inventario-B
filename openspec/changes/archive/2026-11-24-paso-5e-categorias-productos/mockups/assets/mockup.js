/* Maqueta paso-5e-categorias-productos / inventario.html: selector de estados por #ancla + datos de muestra. No es el JS de la app.
   Sin innerHTML: solo DOM. ?captura oculta la barra de la maqueta.
   - <option value="ID" data-base="ID_BASE" data-q data-cat data-ds data-desc>: data-q = texto de búsqueda, data-cat = '' | clave | __sin__,
     data-ds = conjunto de datos ('base' | 'm2' | 'nomotor').
   - [data-show="A B"] / [data-hide="A B"]: visibilidad por estado (o por el estado base si es un modal).
   - select[data-catsel]: se llena con las categorías (data-first = texto de la primera opción, data-sin = agrega "Sin categoría" al final, data-value).
   - select[data-prodsel]: productos activos (+ "Dados de baja" con data-baja), filtrados por data-cat; data-value elige. */
(function () {
  var root = document.documentElement;
  var captura = new URLSearchParams(location.search).has('captura');
  root.classList.add(captura ? 'mk-captura' : 'mk-bar-on');
  var sel = document.getElementById('mk-state');
  var desc = document.getElementById('mk-desc');
  var bar = document.querySelector('.mk-bar');
  var opts = [].slice.call(sel.options);
  var FOCUS = 'input:not([disabled]),select:not([disabled]),textarea,button:not([disabled]),[href],[tabindex="0"]';
  var cur = opts[0];

  var CATS = [['aceite', 'Aceite'], ['filtro', 'Filtro'], ['motor', 'Motor']]; /* alfabético por nombre */
  var NOMBRE = { aceite: 'Aceite', filtro: 'Filtro', motor: 'Motor' };
  /* [codigo, nombre, stock, categoria|null] — orden de la API (por código) */
  var BASE = [
    ['A-01', 'Tornillo M8', 120, null], ['ACE-01', 'Aceite 10W-40 1 L', 18, 'aceite'], ['ACE-02', 'Aceite 5W-30 sintético 4 L', 7, 'aceite'],
    ['ACE-03', 'Aceite de transmisión 80W-90', 0, 'aceite'], ['B-10', 'Tuerca M6', 85, null], ['C-03', 'Arandela plana 8 mm', 240, null],
    ['CAJA/10', 'Caja de arandelas ×10', 4, null], ['FIL-01', 'Filtro de aceite Ford', 9, 'filtro'], ['FIL-02', 'Filtro de aire universal', 5, 'filtro'],
    ['FIL-03', 'Filtro de combustible', 3, 'filtro'], ['MOT-01', 'Junta de culata', 4, 'motor'], ['MOT-02', 'Correa de distribución', 6, 'motor']
  ];
  var BAJA = [['C-99', 'Junta tórica', 2, 'motor'], ['D-05', 'Disco de corte 115 mm', 0, null]];

  function words(e, a) { return (e.getAttribute(a) || '').split(/\s+/).filter(Boolean); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(id) { return document.getElementById(id); }
  function norm(s) { return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); }
  function plural(n) { return n + (n === 1 ? ' producto' : ' productos'); }
  function nombreCat(c) { return c ? NOMBRE[c] : 'Sin categoría'; }

  function dataset(ds) {
    var d = BASE.map(function (r) { return r.slice(); });
    if (ds === 'm2') d.forEach(function (r) { if (r[0] === 'FIL-01') r[3] = 'aceite'; });
    if (ds === 'nomotor') d = d.filter(function (r) { return r[3] !== 'motor'; });
    return d;
  }
  function filtrar(d, q, cat) {
    var n = norm(q);
    return d.filter(function (r) {
      var okQ = !n || norm(r[0]).indexOf(n) !== -1 || norm(r[1]).indexOf(n) !== -1;
      var okC = !cat || (cat === '__sin__' ? r[3] === null : r[3] === cat);
      return okQ && okC;
    });
  }
  function conteo(v, t, hay) { return (hay && v < t) ? v + ' de ' + t + ' productos' : plural(t); }
  function mensaje(q, cat) {
    var n = (q || '').trim();
    var c = cat ? (cat === '__sin__' ? 'Sin categoría' : NOMBRE[cat]) : '';
    if (n && c) return 'Ningún producto coincide con «' + n + '» en la categoría «' + c + '»';
    if (c) return 'Ningún producto en la categoría «' + c + '»';
    return 'Ningún producto coincide con «' + n + '»';
  }

  /* ---------- Selectores ---------- */
  function fillCat(s) {
    clear(s);
    var first = s.getAttribute('data-first');
    var o0 = el('option', null, first); o0.value = ''; s.appendChild(o0);
    CATS.forEach(function (c) { var o = el('option', null, c[1]); o.value = c[0]; s.appendChild(o); });
    if (s.hasAttribute('data-sin')) { var o = el('option', null, 'Sin categoría'); o.value = '__sin__'; s.appendChild(o); }
    s.value = s.getAttribute('data-value') || '';
  }
  function fillProd(s, ds) {
    clear(s);
    var cat = s.getAttribute('data-cat-filter') || '';
    var o0 = el('option', null, 'Elegí un producto…'); o0.value = ''; s.appendChild(o0);
    var act = filtrar(dataset(ds), '', cat);
    function opt(r) { var o = el('option', null, r[0] + ' · ' + r[1] + ' (stock ' + r[2] + ')'); o.value = r[0]; return o; }
    if (s.hasAttribute('data-baja')) {
      var g1 = document.createElement('optgroup'); g1.label = 'Activos'; act.forEach(function (r) { g1.appendChild(opt(r)); }); s.appendChild(g1);
      var g2 = document.createElement('optgroup'); g2.label = 'Dados de baja'; BAJA.forEach(function (r) { g2.appendChild(opt(r)); }); s.appendChild(g2);
    } else act.forEach(function (r) { s.appendChild(opt(r)); });
    s.value = s.getAttribute('data-value') || '';
  }

  /* ---------- Inventario ---------- */
  function renderTable(d, vis) {
    var body = document.querySelector('[data-inv-body]'); clear(body);
    vis.forEach(function (r) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', r[0]));
      var nom = el('td', null, r[1]);
      nom.appendChild(el('span', 'cat-inline' + (r[3] ? '' : ' cat-none'), nombreCat(r[3])));
      tr.appendChild(nom);
      tr.appendChild(el('td', 'cat-col' + (r[3] ? '' : ' cat-none'), nombreCat(r[3])));
      var td = el('td', 'num r');
      if (r[2] === 0) { var b = el('span', 'badge bg-warning-subtle text-warning-fg', '0'); b.appendChild(el('span', 'sr-only', ', sin stock')); td.appendChild(b); }
      else td.textContent = String(r[2]);
      tr.appendChild(td);
      var ac = el('td', 'r'); var bt = el('button', 'btn btn-secondary btn-sm', 'Eliminar'); bt.type = 'button'; bt.setAttribute('aria-label', 'Eliminar ' + r[0]); ac.appendChild(bt); tr.appendChild(ac);
      body.appendChild(tr);
    });
  }
  function renderSheet(vis, cat) {
    var body = document.querySelector('[data-sheet-body]'); clear(body);
    vis.forEach(function (r) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', r[0])); tr.appendChild(el('td', null, r[1])); tr.appendChild(el('td', 'cat', nombreCat(r[3])));
      var td = el('td', 'num r');
      if (r[2] === 0) td.appendChild(el('span', 'sin-stock', '0 (sin stock)')); else td.textContent = String(r[2]);
      tr.appendChild(td); body.appendChild(tr);
    });
    var meta = $('sheet-meta'); clear(meta);
    if (cat) meta.appendChild(el('span', null, cat === '__sin__' ? 'Sin categoría' : NOMBRE[cat]));
    meta.appendChild(el('span', null, plural(vis.length)));
    meta.appendChild(el('span', null, '2026-11-24'));
  }

  function apply() {
    cur = opts.filter(function (o) { return o.value === decodeURIComponent(location.hash.slice(1)); })[0] || opts[0];
    var active = [cur.value, cur.getAttribute('data-base') || cur.value];
    document.querySelectorAll('[data-show],[data-hide]').forEach(function (e) {
      var show = !e.hasAttribute('data-show') || words(e, 'data-show').some(function (s) { return active.indexOf(s) !== -1; });
      if (words(e, 'data-hide').some(function (s) { return active.indexOf(s) !== -1; })) show = false;
      e.hidden = !show;
    });

    var base = opts.filter(function (o) { return o.value === (cur.getAttribute('data-base') || cur.value); })[0];
    var q = base.getAttribute('data-q') || '', cat = base.getAttribute('data-cat') || '', ds = base.getAttribute('data-ds') || 'base';
    var d = dataset(ds), vis = filtrar(d, q, cat), hay = !!norm(q) || !!cat;
    $('inv-buscar').value = q;
    $('inv-categoria').value = cat;
    $('inv-conteo').textContent = conteo(vis.length, d.length, hay);
    renderTable(d, vis);
    var vacio = vis.length === 0;
    $('inv-nomatch').hidden = !vacio; $('inv-tabla').hidden = vacio;
    $('inv-nomatch-msg').textContent = mensaje(q, cat);
    $('btn-exportar-inv').disabled = vacio;
    if (cur.value === 'P1') renderSheet(vis, cat);

    document.querySelectorAll('select[data-catsel]').forEach(fillCat);
    document.querySelectorAll('select[data-prodsel]').forEach(function (s) { fillProd(s, cur.getAttribute('data-ds') || 'base'); });
    $('inv-categoria').value = cat;

    sel.value = cur.value;
    desc.textContent = cur.value + ' — ' + (cur.getAttribute('data-desc') || cur.textContent);
    document.title = cur.value + ' · ' + document.body.getAttribute('data-screen');
    root.style.setProperty('--mk-bar', captura ? '0px' : bar.offsetHeight + 'px');
    var dlg = dialog();
    document.body.style.overflow = dlg ? 'hidden' : '';
    window.scrollTo(0, 0);
    var scope = dlg || document;
    var f = [].slice.call(scope.querySelectorAll('[data-autofocus]')).filter(visible)[0];
    if (f) f.focus({ preventScroll: true });
    else if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
  }
  function visible(n) { return n.offsetParent !== null; }
  function dialog() {
    var o = [].slice.call(document.querySelectorAll('.overlay')).filter(function (x) { return !x.hidden; })[0];
    return o ? o.querySelector('[role=dialog],[role=alertdialog]') : null;
  }
  function go(id) { if (location.hash === '#' + id) apply(); else location.hash = id; }
  function closeDialog() { go(cur.getAttribute('data-base') || opts[0].value); }

  sel.addEventListener('change', function () { go(sel.value); });
  $('mk-prev').addEventListener('click', function () { go(opts[Math.max(0, cur.index - 1)].value); });
  $('mk-next').addEventListener('click', function () { go(opts[Math.min(opts.length - 1, cur.index + 1)].value); });
  window.addEventListener('hashchange', apply);
  window.addEventListener('resize', function () { root.style.setProperty('--mk-bar', captura ? '0px' : bar.offsetHeight + 'px'); });

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('[data-close]') || (t.classList && t.classList.contains('overlay'))) { closeDialog(); return; }
    var g = t.closest('[data-goto]');
    if (g) { var to = g.getAttribute('data-goto'); if (to.charAt(0) === '#') go(to.slice(1)); else location.href = to; }
  });
  /* El buscador y el filtro de la maqueta filtran de verdad (sobre el estado base actual) */
  function vivo() {
    var d = dataset((cur.getAttribute('data-base') ? opts.filter(function (o) { return o.value === cur.getAttribute('data-base'); })[0] : cur).getAttribute('data-ds') || 'base');
    var q = $('inv-buscar').value, cat = $('inv-categoria').value, vis = filtrar(d, q, cat);
    $('inv-conteo').textContent = conteo(vis.length, d.length, !!norm(q) || !!cat);
    renderTable(d, vis);
    $('inv-nomatch').hidden = vis.length !== 0; $('inv-tabla').hidden = vis.length === 0;
    $('inv-nomatch-msg').textContent = mensaje(q, cat);
    $('btn-exportar-inv').disabled = vis.length === 0;
  }
  $('inv-buscar').addEventListener('input', vivo);
  $('inv-categoria').addEventListener('change', vivo);
  $('inv-limpiar').addEventListener('click', function () { $('inv-buscar').value = ''; $('inv-categoria').value = ''; vivo(); $('inv-buscar').focus(); });
  document.addEventListener('keydown', function (e) {
    var dlg = dialog(); if (!dlg) return;
    if (e.key === 'Escape') { closeDialog(); return; }
    if (e.key === 'Tab') {
      var items = [].slice.call(dlg.querySelectorAll(FOCUS)).filter(visible);
      if (!items.length) return;
      var a = items[0], z = items[items.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    }
  });
  /* Nueva orden: cambiar la categoría de una línea vuelve a llenar su selector de producto (conserva el producto si pertenece) */
  document.addEventListener('change', function (e) {
    var c = e.target.closest && e.target.closest('select[data-cat]'); if (!c) return;
    var row = c.closest('[data-row]'), p = row.querySelector('select[data-prodsel]');
    var prev = p.value; p.setAttribute('data-cat-filter', c.value === '__sin__' ? '__sin__' : c.value);
    p.setAttribute('data-value', prev); fillProd(p, cur.getAttribute('data-ds') || 'base');
    var ayuda = row.querySelector('[data-vacio]'); if (ayuda) ayuda.hidden = p.options.length > 1;
  });
  apply();
})();
