(function () {
  'use strict';
  var root = document.documentElement, layer = null, field = null, raf = null, listening = false, px = 0, py = 0;
  var reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var fine = window.matchMedia ? window.matchMedia('(hover: hover) and (pointer: fine)') : null;
  function read(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function living() { return root.getAttribute('data-theme') === 'calavera' && root.getAttribute('data-motion') === 'living' && !(reduce && reduce.matches) && !document.hidden && !document.getElementById('zg'); }
  function paint() {
    raf = null;
    if (!living() || !field) return;
    field.style.setProperty('--cn-x', px.toFixed(2) + 'px');
    field.style.setProperty('--cn-y', py.toFixed(2) + 'px');
  }
  function pointer(event) {
    if (event.pointerType && event.pointerType !== 'mouse' || !living()) return;
    px = (event.clientX / Math.max(1, window.innerWidth) - .5) * 28;
    py = (event.clientY / Math.max(1, window.innerHeight) - .5) * 20;
    if (raf === null) raf = window.requestAnimationFrame(paint);
  }
  function stop() {
    if (listening) { document.removeEventListener('pointermove', pointer); listening = false; }
    if (raf !== null) { window.cancelAnimationFrame(raf); raf = null; }
    if (field) { field.style.removeProperty('--cn-x'); field.style.removeProperty('--cn-y'); }
  }
  function sync() {
    var selected = root.getAttribute('data-theme') === 'calavera' && !document.getElementById('zg');
    root.classList.toggle('cn-living', living());
    if (selected && !layer) {
      layer = document.createElement('div'); layer.className = 'calavera-atmosphere'; layer.setAttribute('aria-hidden', 'true');
      field = document.createElement('div'); field.className = 'cn-field'; layer.appendChild(field);
      ['cn-light','cn-light cn-light-b','cn-skull cn-skull-a','cn-skull cn-skull-b'].forEach(function (name) { var item = document.createElement('i'); item.className = name; (name.indexOf('cn-skull') === 0 ? layer : field).appendChild(item); });
      document.body.appendChild(layer);
    }
    if (layer) {
      layer.hidden = !selected;
      var amount = read('zotheos_rain');
      layer.style.setProperty('--cn-strength', amount === 'light' ? '.35' : amount === 'heavy' ? '.8' : '.56');
      layer.classList.toggle('is-living', living());
    }
    if (living() && fine && fine.matches) { if (!listening) { document.addEventListener('pointermove', pointer, {passive: true}); listening = true; } }
    else stop();
  }
  new MutationObserver(sync).observe(root, {attributes: true, attributeFilter: ['data-theme','data-motion']});
  new MutationObserver(sync).observe(document.body, {childList: true});
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('pagehide', function () { stop(); root.classList.remove('cn-living'); if (layer) layer.classList.remove('is-living'); });
  window.addEventListener('pageshow', sync);
  window.addEventListener('storage', sync);
  function intensityChanged(event) { if (event.target.closest && event.target.closest('#fxAmount')) sync(); }
  document.addEventListener('click', intensityChanged);
  document.addEventListener('keydown', intensityChanged);
  [reduce, fine].forEach(function (query) { if (!query) return; if (query.addEventListener) query.addEventListener('change', sync); else if (query.addListener) query.addListener(sync); });
  sync();
})();
