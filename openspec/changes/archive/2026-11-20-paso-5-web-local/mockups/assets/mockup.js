/* Maquetas paso-5-web-local: selector de estados por #ancla + interacciones mínimas.
   No es el JS de la app. Sin innerHTML: solo DOM (cloneNode, textContent, setAttribute).
   - <option value="ID" data-base="ID_BASE" data-desc="..."> en #mk-state define cada estado.
   - [data-show="A B"]: visible si el estado actual o su base está en la lista.
   - [data-hide="A B"]: oculto si el estado actual está en la lista.
   - [data-mkfocus="A"]: anillo de foco estático en ese estado.
   - [data-autofocus]: recibe el foco real al mostrar el estado.
   - ?captura en la URL oculta la barra de la maqueta (capturas limpias). */
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

  function words(el, attr) { return (el.getAttribute(attr) || '').split(/\s+/).filter(Boolean); }
  function find(id) { for (var i = 0; i < opts.length; i++) if (opts[i].value === id) return opts[i]; return opts[0]; }
  function go(id) { if (location.hash === '#' + id) apply(); else location.hash = id; }

  /* Opciones de producto compartidas: <template id="tpl-opts"> -> <select data-opts="VALOR" data-opts-exclude="X"> */
  var tpl = document.getElementById('tpl-opts');
  if (tpl) {
    document.querySelectorAll('select[data-opts]').forEach(function (s) {
      var skip = words(s, 'data-opts-exclude');
      [].slice.call(tpl.content.children).forEach(function (o) {
        if (skip.indexOf(o.value) === -1) s.appendChild(o.cloneNode(true));
      });
      s.value = s.getAttribute('data-opts');
    });
  }

  /* Relleno hasta N líneas (estado MO7b) */
  document.querySelectorAll('[data-fill-rows]').forEach(function (list) {
    var n = parseInt(list.getAttribute('data-fill-rows'), 10);
    var codes = ['A-01', 'CAJA/10', 'JUN-12'];
    while (list.children.length < n) {
      var c = list.lastElementChild.cloneNode(true);
      list.appendChild(c);
      c.querySelector('select').value = codes[list.children.length % codes.length];
      c.querySelector('input').value = '1';
    }
    renumber(list);
  });

  function renumber(list) {
    var rows = list.children, max = parseInt(list.getAttribute('data-max') || '100', 10);
    [].slice.call(rows).forEach(function (r, i) {
      var n = String(i + 1);
      r.querySelector('.line-n').textContent = n;
      r.querySelector('select').setAttribute('aria-label', 'Producto del componente ' + n);
      r.querySelector('input').setAttribute('aria-label', 'Cantidad del componente ' + n);
      var q = r.querySelector('[data-remove-row]');
      q.setAttribute('aria-label', 'Quitar componente ' + n);
      q.disabled = rows.length === 1;
    });
    var form = list.closest('form');
    var add = form.querySelector('[data-add-row]');
    var cnt = form.querySelector('[data-count]');
    if (add && !add.hasAttribute('data-keep')) add.disabled = rows.length >= max;
    if (cnt) cnt.textContent = rows.length + ' de ' + max + ' componentes' + (rows.length >= max ? ' (máximo)' : '');
  }

  function apply() {
    cur = find(decodeURIComponent(location.hash.slice(1)));
    var active = [cur.value, cur.getAttribute('data-base') || cur.value];
    document.querySelectorAll('[data-show],[data-hide]').forEach(function (el) {
      var show = !el.hasAttribute('data-show') || words(el, 'data-show').some(function (s) { return active.indexOf(s) !== -1; });
      if (words(el, 'data-hide').indexOf(cur.value) !== -1) show = false;
      el.hidden = !show;
    });
    document.querySelectorAll('[data-mkfocus]').forEach(function (el) {
      el.classList.toggle('mk-focus', words(el, 'data-mkfocus').indexOf(cur.value) !== -1);
    });
    sel.value = cur.value;
    desc.textContent = cur.value + ' — ' + (cur.getAttribute('data-desc') || cur.textContent);
    document.title = cur.value + ' · ' + document.body.getAttribute('data-screen');
    root.style.setProperty('--mk-bar', captura ? '0px' : bar.offsetHeight + 'px');
    var dlg = dialog();
    document.body.style.overflow = dlg ? 'hidden' : '';
    window.scrollTo(0, 0);
    var scope = dlg || document;
    var f = [].slice.call(scope.querySelectorAll('[data-autofocus]')).filter(visible)[0];
    if (!f && dlg) f = [].slice.call(dlg.querySelectorAll('input,select,textarea')).filter(visible)[0] || dlg.querySelector(FOCUS);
    if (f) f.focus({ preventScroll: true });
    else if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
    if (dlg) {
      var end = dlg.querySelector('[data-scroll-end]');
      if (end) end.scrollTop = end.scrollHeight;
    }
  }
  function visible(n) { return n.offsetParent !== null; }
  function dialog() {
    var o = [].slice.call(document.querySelectorAll('.overlay')).filter(function (x) { return !x.hidden; })[0];
    return o ? o.querySelector('[role=dialog],[role=alertdialog]') : null;
  }
  function closeDialog() { go(cur.getAttribute('data-base') || opts[0].value); }

  sel.addEventListener('change', function () { go(sel.value); });
  document.getElementById('mk-prev').addEventListener('click', function () { go(opts[Math.max(0, cur.index - 1)].value); });
  document.getElementById('mk-next').addEventListener('click', function () { go(opts[Math.min(opts.length - 1, cur.index + 1)].value); });
  window.addEventListener('hashchange', apply);
  window.addEventListener('resize', function () { root.style.setProperty('--mk-bar', captura ? '0px' : bar.offsetHeight + 'px'); });

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('[data-close]') || (t.classList && t.classList.contains('overlay'))) { closeDialog(); return; }
    var g = t.closest('[data-goto]');
    if (g) { var to = g.getAttribute('data-goto'); if (to.charAt(0) === '#') go(to.slice(1)); else location.href = to; return; }
    var tg = t.closest('[data-toggle]');
    if (tg) {
      var inp = document.getElementById(tg.getAttribute('data-toggle')), show = inp.type === 'password';
      inp.type = show ? 'text' : 'password';
      tg.textContent = show ? 'Ocultar' : 'Mostrar';
      tg.setAttribute('aria-pressed', String(show));
      return;
    }
    var rm = t.closest('[data-remove-row]');
    if (rm) { var row = rm.closest('[data-row]'), list = row.parentNode; if (list.children.length > 1) { row.remove(); renumber(list); } return; }
    var add = t.closest('[data-add-row]');
    if (add) {
      var l = document.getElementById(add.getAttribute('data-add-row'));
      var c = l.lastElementChild.cloneNode(true);
      c.removeAttribute('data-invalid');
      c.querySelectorAll('.err').forEach(function (x) { x.remove(); });
      c.querySelectorAll('[aria-invalid]').forEach(function (x) { x.removeAttribute('aria-invalid'); x.removeAttribute('aria-describedby'); });
      c.querySelector('select').value = ''; c.querySelector('input').value = '';
      l.appendChild(c); renumber(l); c.querySelector('select').focus();
    }
  });

  /* Casilla "Devolver stock": cambia el texto del botón y la ayuda */
  document.addEventListener('change', function (e) {
    var cb = e.target.closest('[data-devolver]');
    if (!cb) return;
    var k = cb.checked ? 'data-on' : 'data-off';
    [cb.getAttribute('data-devolver'), cb.getAttribute('aria-describedby')].forEach(function (id) {
      var el = id && document.getElementById(id); if (el) el.textContent = el.getAttribute(k);
    });
  });

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

  document.querySelectorAll('[data-add-row]').forEach(function (b) { var l = document.getElementById(b.getAttribute('data-add-row')); if (l) renumber(l); });
  apply();
})();
