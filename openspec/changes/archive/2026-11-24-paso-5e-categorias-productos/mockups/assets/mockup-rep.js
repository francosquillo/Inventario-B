/* Maqueta paso-5e-categorias-productos / reportes.html: selector de estados (R10, P2) + datos de muestra. No es el JS de la app.
   Sin innerHTML: solo DOM. ?captura oculta la barra de la maqueta. */
(function () {
  var root = document.documentElement;
  var captura = new URLSearchParams(location.search).has('captura');
  root.classList.add(captura ? 'mk-captura' : 'mk-bar-on');
  var sel = document.getElementById('mk-state');
  var desc = document.getElementById('mk-desc');
  var bar = document.querySelector('.mk-bar');
  var opts = [].slice.call(sel.options);
  var cur = opts[0];
  /* Reporte del mes, cantidad desc. [codigo, nombre, categoria|null, activo, cantidad, ordenes] */
  var MES = [
    ['ACE-01', 'Aceite 10W-40 1 L', 'Aceite', true, 48, 6], ['FIL-01', 'Filtro de aceite Ford', 'Filtro', true, 34, 8],
    ['A-01', 'Tornillo M8', null, true, 22, 4], ['C-99', 'Junta tórica', 'Motor', false, 9, 3], ['B-10', 'Tuerca M6', null, true, 6, 2]
  ];
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(id) { return document.getElementById(id); }
  function cat(r) { return r[2] || 'Sin categoría'; }
  function fillRows(body, sheet) {
    clear(body);
    MES.forEach(function (r) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', r[0]));
      var nom = el('td', null, r[1]);
      if (!r[3]) {
        if (sheet) { nom.appendChild(document.createTextNode(' ')); nom.appendChild(el('strong', null, 'dado de baja')); }
        else nom.appendChild(el('span', 'badge badge-baja bg-warning-subtle text-warning-fg', 'dado de baja'));
      }
      if (!sheet) nom.appendChild(el('span', 'cat-inline' + (r[2] ? '' : ' cat-none'), cat(r)));
      tr.appendChild(nom);
      tr.appendChild(el('td', sheet ? 'cat' : 'cat-col' + (r[2] ? '' : ' cat-none'), cat(r)));
      tr.appendChild(el('td', 'num r', String(r[4]))); tr.appendChild(el('td', 'num r', String(r[5])));
      body.appendChild(tr);
    });
  }
  function words(e, a) { return (e.getAttribute(a) || '').split(/\s+/).filter(Boolean); }
  function apply() {
    cur = opts.filter(function (o) { return o.value === decodeURIComponent(location.hash.slice(1)); })[0] || opts[0];
    document.querySelectorAll('[data-show],[data-hide]').forEach(function (e) {
      var show = !e.hasAttribute('data-show') || words(e, 'data-show').indexOf(cur.value) !== -1;
      if (words(e, 'data-hide').indexOf(cur.value) !== -1) show = false;
      e.hidden = !show;
    });
    fillRows(document.querySelector('[data-rep-body]'), false);
    fillRows(document.querySelector('[data-sheet-body]'), true);
    $('rep-resumen').textContent = '5 productos · 2026-11-01 a 2026-11-24';
    $('sheet-meta').textContent = '2026-11-01 a 2026-11-24 · 5 productos';
    sel.value = cur.value;
    desc.textContent = cur.value + ' — ' + cur.getAttribute('data-desc');
    document.title = cur.value + ' · ' + document.body.getAttribute('data-screen');
    root.style.setProperty('--mk-bar', captura ? '0px' : bar.offsetHeight + 'px');
    window.scrollTo(0, 0);
  }
  function go(id) { if (location.hash === '#' + id) apply(); else location.hash = id; }
  sel.addEventListener('change', function () { go(sel.value); });
  $('mk-prev').addEventListener('click', function () { go(opts[Math.max(0, cur.index - 1)].value); });
  $('mk-next').addEventListener('click', function () { go(opts[Math.min(opts.length - 1, cur.index + 1)].value); });
  window.addEventListener('hashchange', apply);
  $('form-reporte').addEventListener('submit', function (e) { e.preventDefault(); });
  document.addEventListener('click', function (e) { var g = e.target.closest('[data-goto]'); if (g) go(g.getAttribute('data-goto').slice(1)); });
  apply();
})();
