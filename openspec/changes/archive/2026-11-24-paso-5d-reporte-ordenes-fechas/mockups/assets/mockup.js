/* Maquetas paso-5d-reporte-ordenes-fechas: selector de estados por #ancla + datos de muestra. No es el JS de la app.
   Sin innerHTML: solo DOM. ?captura oculta la barra de la maqueta.
   - <option value="ID" data-k="inicial|datos|vacio|cargando|error|print|nav" data-desde data-hasta data-prod data-set data-res data-err data-open>
   - [data-show="A B"] / [data-hide="A B"]: visibilidad por estado (o por clase de estado: datos-ok). */
(function () {
  var root = document.documentElement;
  var captura = new URLSearchParams(location.search).has('captura');
  root.classList.add(captura ? 'mk-captura' : 'mk-bar-on');
  var sel = document.getElementById('mk-state');
  var desc = document.getElementById('mk-desc');
  var opts = [].slice.call(sel.options);
  var cur = opts[0];

  /* Productos usados en alguna orden (de cualquier fecha); C-99 está dado de baja. */
  var USADOS = [
    ['A-01', 'Tornillo M8', true], ['B-10', 'Tuerca M6', true], ['C-03', 'Arandela plana 8 mm', true],
    ['C-99', 'Junta tórica', false], ['JUN-12', 'Junta industrial 12"', true]
  ];
  /* Reporte del mes: cantidad desc., desempate por código. [codigo, nombre, activo, cantidad, ordenes] */
  var MES = [
    ['C-03', 'Arandela plana 8 mm', true, 48, 6], ['A-01', 'Tornillo M8', true, 34, 8], ['B-10', 'Tuerca M6', true, 15, 4],
    ['C-99', 'Junta tórica', false, 12, 3], ['JUN-12', 'Junta industrial 12"', true, 6, 2]
  ];
  var LARGO = MES.slice();
  for (var i = 1; i <= 55; i++) {
    var n = ('00' + i).slice(-3);
    LARGO.push(['R-' + n, 'Repuesto de muestra ' + n, i % 9 !== 0, Math.max(1, 5 - Math.floor(i / 12)), (i % 4) + 1]);
  }

  function words(e, a) { return (e.getAttribute(a) || '').split(/\s+/).filter(Boolean); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function $(id) { return document.getElementById(id); }
  function plural(n) { return n + (n === 1 ? ' producto' : ' productos'); }

  function opcion(u) { var o = el('option', null, u[0] + ' · ' + u[1]); o.value = u[0]; return o; }
  function fillSelect(s, valor) {
    clear(s);
    var todos = el('option', null, 'Todos los productos'); todos.value = ''; s.appendChild(todos);
    [[true, 'Activos'], [false, 'Dados de baja']].forEach(function (g) {
      var lista = USADOS.filter(function (u) { return u[2] === g[0]; });
      if (!lista.length) return;
      var og = document.createElement('optgroup'); og.label = g[1];
      lista.forEach(function (u) { og.appendChild(opcion(u)); });
      s.appendChild(og);
    });
    if (valor != null) s.value = valor;
  }

  function filas(set) {
    if (set === 'TODOS') return MES;
    return MES.filter(function (f) { return f[0] === set; });
  }

  function renderScreen(set) {
    var body = document.querySelector('[data-rep-body]'); clear(body);
    filas(set).forEach(function (f) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', f[0]));
      var nom = el('td', null, f[1]);
      if (!f[2]) nom.appendChild(el('span', 'badge badge-baja bg-warning-subtle text-warning-fg', 'dado de baja'));
      tr.appendChild(nom);
      tr.appendChild(el('td', 'num r', String(f[3]))); tr.appendChild(el('td', 'num r', String(f[4])));
      body.appendChild(tr);
    });
  }

  function renderSheet(big) {
    var body = document.querySelector('[data-sheet-body]'); clear(body);
    var data = big ? LARGO : MES;
    data.forEach(function (f) {
      var tr = el('tr'); tr.appendChild(el('td', 'num', f[0]));
      var nom = el('td', null, f[1]);
      if (!f[2]) { nom.appendChild(document.createTextNode(' ')); nom.appendChild(el('strong', null, 'dado de baja')); }
      tr.appendChild(nom);
      tr.appendChild(el('td', 'num r', String(f[3]))); tr.appendChild(el('td', 'num r', String(f[4])));
      body.appendChild(tr);
    });
    $('sheet-meta').textContent = (big ? '2026-01-01' : '2026-11-01') + ' a 2026-11-24 · ' + plural(data.length);
  }

  function apply() {
    cur = opts.filter(function (o) { return o.value === decodeURIComponent(location.hash.slice(1)); })[0] || opts[0];
    var k = cur.getAttribute('data-k');
    var ok = k === 'datos';
    document.querySelectorAll('[data-show],[data-hide]').forEach(function (e) {
      var list = words(e, 'data-show');
      var show = !e.hasAttribute('data-show') || list.indexOf(cur.value) !== -1 || (ok && list.indexOf('datos-ok') !== -1);
      if (words(e, 'data-hide').indexOf(cur.value) !== -1) show = false;
      e.hidden = !show;
    });

    var s = $('r-producto');
    fillSelect(s, cur.getAttribute('data-prod') || '');
    fillSelect($('r-producto-abierto'), '');
    var d = $('r-desde'), h = $('r-hasta');
    d.value = cur.getAttribute('data-desde') || ''; h.value = cur.getAttribute('data-hasta') || '';
    var err = cur.getAttribute('data-err');
    d.removeAttribute('aria-invalid'); h.removeAttribute('aria-invalid');
    if (err === 'desde') d.setAttribute('aria-invalid', 'true');
    if (err === 'hasta') h.setAttribute('aria-invalid', 'true');

    $('btn-exportar-rep').disabled = !ok;
    $('btn-generar').disabled = k === 'cargando';
    if (ok) { renderScreen(cur.getAttribute('data-set')); $('rep-resumen').textContent = cur.getAttribute('data-res'); }
    if (k === 'print') renderSheet(cur.value === 'P5');

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
  $('form-reporte').addEventListener('submit', function (e) { e.preventDefault(); });
  apply();
})();
