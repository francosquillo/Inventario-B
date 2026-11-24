/* Maquetas paso-5c-buscador-pdf: selector de estados por #ancla + filtrado real de la tabla. No es el JS de la app.
   Sin innerHTML: solo DOM. ?captura oculta la barra de la maqueta.
   - <option value="ID" data-q="texto" data-desc="...">: estado; data-q = búsqueda precargada.
   - [data-show="A B"] / [data-hide="A B"]: visibilidad por estado. */
(function () {
  var root = document.documentElement;
  var captura = new URLSearchParams(location.search).has('captura');
  root.classList.add(captura ? 'mk-captura' : 'mk-bar-on');
  var sel = document.getElementById('mk-state');
  var desc = document.getElementById('mk-desc');
  var opts = [].slice.call(sel.options);
  var cur = opts[0];

  var BASE = [
    ['A-01', 'Tornillo M8', 7], ['B-02', 'Tuerca M8', 0], ['B-10', 'Tuerca M6', 22], ['C-03', 'Arandela plana 8 mm', 120],
    ['C-99', 'Junta tórica', 2], ['CAJA/10', 'Caja de arandelas ×10', 4], ['D-05', 'Disco de corte 115 mm', 0],
    ['E-07', 'Llave ajustable 10"', 3], ['F-11', 'Lija grano 80', 45], ['G-02', 'Cinta aisladora', 16],
    ['H-04', 'Guantes de trabajo', 9], ['JUN-12', 'Junta industrial 12"', 30]
  ];
  var BIG = BASE.slice();
  for (var i = 13; i <= 64; i++) { var n = ('00' + i).slice(-3); BIG.push(['R-' + n, 'Repuesto de muestra ' + n, (i * 7) % 41 + 1]); }

  function words(e, a) { return (e.getAttribute(a) || '').split(/\s+/).filter(Boolean); }
  function norm(t) { return String(t == null ? '' : t).trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function filtrar(list, q) { var n = norm(q); return n ? list.filter(function (p) { return norm(p[0]).indexOf(n) !== -1 || norm(p[1]).indexOf(n) !== -1; }) : list; }
  function conteo(v, t, hay) { return hay ? v + ' de ' + t + ' productos' : t + (t === 1 ? ' producto' : ' productos'); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(id) { return document.getElementById(id); }

  function stockCell(s, sheet) {
    var td = el('td', 'num r');
    if (s === 0) {
      if (sheet) { td.appendChild(el('span', 'sin-stock', '0 (sin stock)')); }
      else { var b = el('span', 'badge bg-warning-subtle text-warning-fg', '0'); b.appendChild(el('span', 'sr-only', ', sin stock')); td.appendChild(b); }
    } else td.textContent = String(s);
    return td;
  }

  /* Pantalla: tabla de inventario con el filtro actual */
  function renderInv(q, loading) {
    var body = document.querySelector('[data-inv-body]'); if (!body) return;
    var vis = filtrar(BASE, q);
    clear(body);
    vis.forEach(function (p) {
      var tr = el('tr');
      tr.appendChild(el('td', 'num', p[0])); tr.appendChild(el('td', null, p[1])); tr.appendChild(stockCell(p[2], false));
      var a = el('td', 'r'); var bt = el('button', 'btn btn-secondary btn-sm', 'Eliminar'); bt.type = 'button'; bt.setAttribute('aria-label', 'Eliminar ' + p[0]); a.appendChild(bt); tr.appendChild(a);
      body.appendChild(tr);
    });
    $('inv-conteo').textContent = loading ? '' : conteo(vis.length, BASE.length, !!norm(q));
    $('inv-tabla').hidden = loading || vis.length === 0;
    $('inv-cargando').hidden = !loading;
    $('inv-nomatch').hidden = loading || vis.length !== 0;
    $('inv-nomatch-q').textContent = String(q).trim();
    $('btn-exportar-inv').disabled = loading || vis.length === 0;
  }

  /* Hoja de impresión del inventario (P1 filtrada por q, P2 completa) */
  function renderSheet(q, big) {
    var body = document.querySelector('[data-sheet-body]'); if (!body) return;
    var all = big ? BIG : BASE, vis = filtrar(all, q), hay = !!norm(q);
    clear(body);
    vis.forEach(function (p) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', p[0])); tr.appendChild(el('td', null, p[1])); tr.appendChild(stockCell(p[2], true)); body.appendChild(tr);
    });
    $('sheet-cantidad').textContent = conteo(vis.length, vis.length, false);
  }

  function apply() {
    cur = opts.filter(function (o) { return o.value === decodeURIComponent(location.hash.slice(1)); })[0] || opts[0];
    document.querySelectorAll('[data-show],[data-hide]').forEach(function (e) {
      var show = !e.hasAttribute('data-show') || words(e, 'data-show').indexOf(cur.value) !== -1;
      if (words(e, 'data-hide').indexOf(cur.value) !== -1) show = false;
      e.hidden = !show;
    });
    var q = cur.getAttribute('data-q') || '';
    var inp = $('inv-buscar'); if (inp) inp.value = q;
    if (document.querySelector('[data-inv-body]')) renderInv(q, cur.value === 'B3');
    if (document.querySelector('[data-sheet-body]')) renderSheet(q, cur.value === 'P2');
    sel.value = cur.value;
    desc.textContent = cur.value + ' — ' + cur.getAttribute('data-desc');
    document.title = cur.value + ' · ' + document.body.getAttribute('data-screen');
    window.scrollTo(0, 0);
  }
  function go(id) { if (location.hash === '#' + id) apply(); else location.hash = id; }
  sel.addEventListener('change', function () { go(sel.value); });
  $('mk-prev').addEventListener('click', function () { go(opts[Math.max(0, cur.index - 1)].value); });
  $('mk-next').addEventListener('click', function () { go(opts[Math.min(opts.length - 1, cur.index + 1)].value); });
  window.addEventListener('hashchange', apply);

  var inp = $('inv-buscar');
  if (inp) {
    inp.addEventListener('input', function () { renderInv(inp.value, false); });
    inp.addEventListener('keydown', function (e) { if (e.key === 'Escape') { inp.value = ''; renderInv('', false); } });
    $('inv-limpiar').addEventListener('click', function () { inp.value = ''; renderInv('', false); inp.focus(); });
  }
  apply();
})();
