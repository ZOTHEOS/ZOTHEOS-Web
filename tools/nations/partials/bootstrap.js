
    /* Theme before first paint: a saved named theme is applied here, so those visitors never see the mono default
       flash first. Fluid motion (registered custom properties) is switched on only where @property exists.
       W2-03: the visitor's Motion choice (Living / Calm / Still) is set here too, so Still never shows a moving
       first frame. The OS reduced-motion setting is a floor: it always reads as Still. */
    (function () {
      var d = document.documentElement;
      var m = 'living';
      try {
        var t = localStorage.getItem('zotheos_landing_theme');
        if (t === 'maya' || t === 'codex' || t === 'skeleton') d.setAttribute('data-theme', t);
        var s = localStorage.getItem('zotheos_motion');
        if (s === 'living' || s === 'calm' || s === 'still') m = s;
        else if (localStorage.getItem('zotheos_fx') === 'off') m = 'still';
      } catch (e) {}
      try { if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) m = 'still'; } catch (e) {}
      d.setAttribute('data-motion', m);
      if (window.CSS && CSS.registerProperty) d.classList.add('zm-fluid');
    })();
  