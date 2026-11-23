/* Maquetas paso-5b-fixes-menores: selector de estados por #ancla + interacciones mínimas.
   Basado en el mockup.js de paso-5-web-local (C-06). No es el JS de la app.
   Sin innerHTML: solo DOM (cloneNode, textContent, setAttribute).
   - <option value="ID" data-base="ID_BASE" data-desc="..."> en #mk-state define cada estado.
   - [data-show="A B"]: visible si el estado actual o su base está en la lista.
   - [data-hide="A B"]: oculto si el estado actual está en la lista.
   - [data-mkfocus="A"]: anillo de foco estático en ese estado.
   - [data-autofocus]: recibe el foco real al mostrar el estado.
   - <select data-opts="VALOR" data-opts-disable="X Y">: se llena con <template id="tpl-opts">.
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

  /* Opciones de producto compartidas (activos + grupo "Dados de baja") */
  var tpl = document.getElementById('tpl-opts');
  function fill(s) {
    var dis = words(s, 'data-opts-disable');
    var skip = words(s, 'data-opts-exclude');
    [].slice.call(tpl.content.children).forEach(function (n) {
      var c = n.cloneNode(true);
      var all = c.tagName === 'OPTGROUP' ? [].slice.call(c.children) : [c];
      all.forEach(function (o) {
        if (skip.indexOf(o.value) !== -1) o.remove();
        else if (dis.indexOf(o.value) !== -1) { o.disabled = true; o.textContent += ' — ya está en otra línea'; }
      });
      s.appendChild(c);
    });
    s.value = s.getAttribute('data-opts');
  }
  if (tpl) document.querySelectorAll('select[data-opts]').forEach(fill);

  function renumber(list) {
    var rows = list.children, max = 100;
    [].slice.call(rows).forEach(function (r, i) {
      var n = String(i + 1);
      r.querySelector('.line-n').textContent = n;
      r.querySelector('select').setAttribute('aria-label', 'Producto de la línea ' + n);
      var fs = r.querySelector('.seg'); if (fs) fs.setAttribute('aria-label', 'Modo de la línea ' + n);
      var q = r.querySelector('[data-remove-row]');
      q.setAttribute('aria-label', 'Quitar línea ' + n);
      q.disabled = rows.length === 1;
    });
    var form = list.closest('form');
    var add = form.querySelector('[data-add-row]');
    var cnt = form.querySelector('[data-count]');
    if (add) add.disabled = rows.length >= max;
    if (cnt) cnt.textContent = rows.length + ' de ' + max + ' líneas';
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
    if (!f && dlg) f = [].slice.call(dlg.querySelectorAll('input:not([type=radio]),select,textarea')).filter(visible)[0] || dlg.querySelector(FOCUS);
    if (f) f.focus({ preventScroll: true });
    else if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
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
    var rm = t.closest('[data-remove-row]');
    if (rm) { var row = rm.closest('[data-row]'), list = row.parentNode; if (list.children.length > 1) { row.remove(); renumber(list); } return; }
    var add = t.closest('[data-add-row]');
    if (add) {
      var l = document.getElementById(add.getAttribute('data-add-row'));
      var c = l.lastElementChild.cloneNode(true);
      var uid = 'r' + Date.now();
      c.removeAttribute('data-invalid');
      c.querySelectorAll('.err,.hint').forEach(function (x) { x.remove(); });
      c.querySelectorAll('[aria-invalid]').forEach(function (x) { x.removeAttribute('aria-invalid'); x.removeAttribute('aria-describedby'); });
      c.querySelectorAll('input[type=radio]').forEach(function (x) { x.name = uid; x.checked = x.value === 'fijar'; });
      c.querySelector('select').value = '';
      c.querySelectorAll('input:not([type=radio])').forEach(function (x) { x.value = ''; });
      var d = c.querySelector('.delta'); if (d) d.textContent = '';
      l.appendChild(c); renumber(l); c.querySelector('select').focus();
    }
  });

  /* Cambio de modo: actualiza la etiqueta del valor ("Stock nuevo" / "Cantidad a sumar") */
  document.addEventListener('change', function (e) {
    var r = e.target;
    if (r.type !== 'radio' || !r.closest('.seg')) return;
    var row = r.closest('[data-row]');
    var lab = row.querySelector('[data-val-label]');
    if (lab) lab.textContent = r.value === 'sumar' ? 'Cantidad a sumar' : 'Stock nuevo';
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
