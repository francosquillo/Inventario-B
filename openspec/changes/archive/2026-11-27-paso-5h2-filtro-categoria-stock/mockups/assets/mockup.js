/* Selector de estados por #ancla (maqueta; no es el JS de la app). ?captura oculta la barra. [data-show="A B"]: visible solo en esos estados. */
(function () {
  var root = document.documentElement;
  var qs = new URLSearchParams(location.search);
  root.classList.add(qs.has('captura') ? 'mk-captura' : 'mk-bar-on');
  if (qs.has('largo')) root.classList.add('mk-largo');
  var sel = document.getElementById('mk-state'), desc = document.getElementById('mk-desc'), opts = [].slice.call(sel.options), cur = opts[0];
  function apply() {
    cur = opts.filter(function (o) { return o.value === decodeURIComponent(location.hash.slice(1)); })[0] || opts[0];
    document.querySelectorAll('[data-show]').forEach(function (e) { e.hidden = (e.getAttribute('data-show') || '').split(/\s+/).indexOf(cur.value) === -1; });
    sel.value = cur.value; desc.textContent = cur.value + ' — ' + cur.getAttribute('data-desc');
    document.title = cur.value + ' · ' + document.body.getAttribute('data-screen');
  }
  function go(id) { if (location.hash === '#' + id) apply(); else location.hash = id; }
  sel.addEventListener('change', function () { go(sel.value); });
  window.addEventListener('hashchange', apply);
  apply();
})();
