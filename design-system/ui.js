/* Modales y utilidades de la maqueta (vanilla JS). */
(function () {
  var last = null, current = null;
  var FOCUS = 'input,select,textarea,button:not([disabled]),[href]';
  function open(id) {
    var el = document.getElementById(id); if (!el) return;
    last = document.activeElement; current = el; el.hidden = false;
    var f = el.querySelector('input:not([type=radio]),select,textarea') || el.querySelector(FOCUS);
    if (f) f.focus();
  }
  function close() {
    if (!current) return;
    current.hidden = true; current = null;
    if (last && last.focus) last.focus();
  }
  document.addEventListener('click', function (e) {
    var o = e.target.closest('[data-open]');
    if (o) {
      if (o.dataset.target) { var s = document.getElementById(o.dataset.target); if (s) s.textContent = o.dataset.name || ''; }
      open(o.dataset.open); return;
    }
    if (e.target.closest('[data-close]') || e.target.classList.contains('overlay')) close();
    var rm = e.target.closest('[data-remove-row]');
    if (rm) { var row = rm.closest('[data-row]'); if (row.parentNode.children.length > 1) row.remove(); }
    var add = e.target.closest('[data-add-row]');
    if (add) {
      var list = document.getElementById(add.dataset.addRow);
      var c = list.firstElementChild.cloneNode(true);
      c.querySelectorAll('input').forEach(function (i) { i.value = ''; });
      c.querySelector('select').value = '';
      list.appendChild(c); c.querySelector('select').focus();
    }
    var tg = e.target.closest('[data-toggle]');
    if (tg) {
      var inp = document.getElementById(tg.dataset.toggle), show = inp.type === 'password';
      inp.type = show ? 'text' : 'password';
      tg.textContent = show ? 'Ocultar' : 'Mostrar';
      tg.setAttribute('aria-pressed', String(show));
    }
  });
  document.addEventListener('keydown', function (e) {
    if (!current) return;
    if (e.key === 'Escape') { close(); return; }
    if (e.key === 'Tab') {
      var items = [].slice.call(current.querySelectorAll(FOCUS)).filter(function (n) { return n.offsetParent !== null; });
      if (!items.length) return;
      var a = items[0], z = items[items.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    }
  });
})();
