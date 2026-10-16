/* ZOTHEOS stepped frame (revision 3): the code-drawn light, drawn on whole device pixels.
   Original ZOTHEOS geometry: nested brackets after the mark; the light descends a stepped aisle from above to the
   screen; the aisle is a stepped notch with no traditional or ceremonial meaning.

   One inline SVG per frame, measured in device pixels: width and height are the CSS box, the viewBox is the device
   pixel box (ResizeObserver devicePixelContentBoxSize, with a rounded fallback). Every rectangle sits on integer
   device pixels and every line is round(devicePixelRatio) device pixels wide (1 at 1 and 1.25, 2 at 1.5 and 2, 3 at
   3), so at any scaling each tier crossing is exactly that many pixels of the exact token, with no in-between colour.
   It redraws on resize and when the device pixel ratio changes. No dependencies, network or storage. Timers drive the 1.0 s arrival hand-off and optional 0.5 s light ticker.

   Usage:
     var f = new ZtFrame(stageEl, screenEl, { geometry: 'auto', ticker: true });   // 'wide', 'phone', 'auto' or {ox, oy, a}
     f.set('walk' | 'rest' | 'paused' | 'playing');
     f.arrive(function () { player.play(); });                       // last four segments, then house lights
     f.motionOk(true);                                               // the visitor chose Keep Motion
     f.destroy();
   The stage must be positioned (relative) and contain the screen; a box with the SVG fills the stage under the
   screen (the screen needs position: relative and a z-index of 1 or more). */
(function (global) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var GEOMETRY = {
    wide:  { ox: [6, 14, 22, 30, 38], oy: [12, 30, 48, 66, 84], a: [36, 80, 124, 168, 212] },
    phone: { ox: [5, 11, 17], oy: [10, 22, 34], a: [18, 44, 70] }
  };
  var STATES = { walk: 1, arrive: 1, playing: 1, rest: 1, paused: 1 };

  function zone(k) { return k === 0 ? 'zC' : (k >= 3 ? 'zA' : 'zB'); }

  function ZtFrame(stage, screen, options) {
    if (!(this instanceof ZtFrame)) return new ZtFrame(stage, screen, options);
    options = options || {};
    this.stage = stage;
    this.screen = screen;
    this.geometry = options.geometry || 'auto';
    this.phone = global.matchMedia ? global.matchMedia(options.phoneQuery || '(max-width: 640px)') : null;
    this.state = STATES[options.state] ? options.state : 'rest';
    this.timer = 0;
    /* Ticker mode advances the light with one 0.5 s timer and changes the active segment twice a second.
       No performance benchmark is claimed by this implementation. */
    this.ticker = !!options.ticker;
    this.tickTimer = 0;
    this.step = 0;
    this.segs = [];
    this.reduce = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : null;
    this.forced = global.matchMedia ? global.matchMedia('(forced-colors: active)') : null;
    this.dev = null;
    this.info = null;
    /* The box is an HTML element: ResizeObserver reports device pixels for a CSS box, not for an svg element
       (Chrome reports an outer svg's size in CSS pixels even for device-pixel-content-box). */
    var box = document.createElement('div');
    box.className = 'zt-frame-box';
    box.setAttribute('aria-hidden', 'true');
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'zt-frame-svg');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('data-zt-light', this.state);
    box.appendChild(svg);
    stage.insertBefore(box, stage.firstChild);
    this.box = box;
    this.svg = svg;
    var self = this;
    this._draw = function () { self.draw(); };
    if (global.ResizeObserver) {
      this.ro = new ResizeObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].target !== box) continue;
          var d = entries[i].devicePixelContentBoxSize && entries[i].devicePixelContentBoxSize[0];
          self.dev = d ? [d.inlineSize, d.blockSize] : null;
        }
        self.draw();
      });
      try { this.ro.observe(box, { box: 'device-pixel-content-box' }); } catch (err) { this.ro.observe(box); }
      this.ro.observe(screen);
    } else {
      global.addEventListener('resize', this._draw);
    }
    if (this.phone) this._listen(this.phone, this._draw);
    this._watchDpr();
    if (global.IntersectionObserver) {
      this.io = new IntersectionObserver(function (entries) {
        self.inView = entries[entries.length - 1].isIntersecting;
        self._hold();
      });
      this.io.observe(stage);
    }
    this._vis = function () { self._hold(); };
    document.addEventListener('visibilitychange', this._vis);
    this.draw();
  }

  ZtFrame.GEOMETRY = GEOMETRY;

  ZtFrame.prototype._listen = function (mq, fn) {
    if (mq.addEventListener) mq.addEventListener('change', fn); else if (mq.addListener) mq.addListener(fn);
  };
  ZtFrame.prototype._unlisten = function (mq, fn) {
    if (mq.removeEventListener) mq.removeEventListener('change', fn); else if (mq.removeListener) mq.removeListener(fn);
  };

  /* The device pixel ratio changes with browser zoom or a move to another display: redraw, then watch the new one. */
  ZtFrame.prototype._watchDpr = function () {
    var self = this;
    if (this.dprMq) this._unlisten(this.dprMq, this._dprChange);
    if (!global.matchMedia) return;
    this.dprMq = global.matchMedia('(resolution: ' + (global.devicePixelRatio || 1) + 'dppx)');
    this._dprChange = function () { self.dev = null; self.draw(); self._watchDpr(); };
    this._listen(this.dprMq, this._dprChange);
  };

  ZtFrame.prototype._hold = function () {
    var hold = document.hidden || this.inView === false;
    if (hold) this.svg.setAttribute('data-zt-hold', ''); else this.svg.removeAttribute('data-zt-hold');
    if (this.ticker) this._tickRun();
  };

  /* The ticker's schedule, segment by segment (d = steps since the segment's turn in the 8 s loop): zA l1 for one
     step; zB l2 then l1; the last step lands: its riser l3, l2, then its rest level; its tread l3, then its rest level
     (the rest levels come from zt-frame.css, so an empty inline fill shows them). */
  function tickFill(seg, d) {
    var z = seg.__z, r = seg.__r;
    if (z === 'zA') return d === 0 ? 'var(--zt-frame-l1)' : 'transparent';
    if (z === 'zB') return d === 0 ? 'var(--zt-frame-l2)' : d === 1 ? 'var(--zt-frame-l1)' : 'transparent';
    if (r) return d === 0 ? 'var(--zt-frame-l3)' : d === 1 ? 'var(--zt-frame-l2)' : '';
    return d === 0 ? 'var(--zt-frame-l3)' : '';
  }
  ZtFrame.prototype._tickPaint = function () {
    for (var i = 0; i < this.segs.length; i++) {
      var seg = this.segs[i], f = tickFill(seg, (this.step - seg.__j + 16) % 16);
      if (seg.style.fill !== f) seg.style.fill = f;
    }
  };
  ZtFrame.prototype._tickClear = function () {
    for (var i = 0; i < this.segs.length; i++) if (this.segs[i].style.fill) this.segs[i].style.fill = '';
  };
  /* Ticks only while walking, in view, with the tab shown, outside forced colours, and (if the device asks for less
     motion) only after the visitor chose Keep Motion: the same floors as zt-frame.css. */
  ZtFrame.prototype._tickRun = function () {
    var self = this;
    var floor = (this.forced && this.forced.matches) || (this.reduce && this.reduce.matches && !this.svg.hasAttribute('data-zt-motion-ok'));
    var go = this.state === 'walk' && !floor && !document.hidden && this.inView !== false;
    if (this.state === 'walk' && !floor) this.svg.setAttribute('data-zt-tick', ''); else this.svg.removeAttribute('data-zt-tick');
    if (this.state !== 'walk' || floor) this._tickClear();
    if (go && !this.tickTimer) {
      var loop = function () {
        self.tickTimer = setTimeout(loop, 500);
        self._tickPaint();
        self.step = (self.step + 1) % 16;
      };
      loop();
    } else if (!go && this.tickTimer) { clearTimeout(this.tickTimer); this.tickTimer = 0; }
  };

  ZtFrame.prototype.motionOk = function (ok) {
    if (ok) this.svg.setAttribute('data-zt-motion-ok', ''); else this.svg.removeAttribute('data-zt-motion-ok');
    if (this.ticker) this._tickRun();
  };

  ZtFrame.prototype.set = function (state) {
    if (!STATES[state]) return;
    if (this.timer) { clearTimeout(this.timer); this.timer = 0; }
    var was = this.state;
    this.state = state;
    /* Setting the same state again restarts nothing; a new state restarts the CSS animations from their start. */
    this.svg.setAttribute('data-zt-light', state);
    if (this.ticker) { if (state === 'walk' && was !== 'walk') this.step = 0; this._tickRun(); }
  };

  /* Only when the page itself is about to start a preview. The callback runs when the light lands (1.0 s). */
  ZtFrame.prototype.arrive = function (done) {
    var self = this;
    this.set('arrive');
    this.timer = setTimeout(function () { self.timer = 0; self.set('playing'); if (done) done(); }, 1000);
  };

  ZtFrame.prototype.pick = function () {
    var g = this.geometry;
    if (typeof g === 'object' && g) return g;
    if (g === 'wide' || g === 'phone') return GEOMETRY[g];
    return this.phone && this.phone.matches ? GEOMETRY.phone : GEOMETRY.wide;
  };

  ZtFrame.prototype.draw = function () {
    var svg = this.svg, screen = this.screen;
    var vr = this.box.getBoundingClientRect(), sr = screen.getBoundingClientRect();
    if (!vr.width || !vr.height || !sr.width) return;
    var dpr = global.devicePixelRatio || 1;
    /* The browser's device pixel box is exact on real hardware. Under device emulation (as in automated checks)
       Chrome reports the CSS size there, so a box more than a pixel away from the CSS size times the ratio is not
       trusted and the rounded size is used instead. */
    var dev = this.dev && Math.abs(this.dev[0] - vr.width * dpr) <= 1 && Math.abs(this.dev[1] - vr.height * dpr) <= 1 ? this.dev : null;
    var W = dev ? dev[0] : Math.round(vr.width * dpr);
    var H = dev ? dev[1] : Math.round(vr.height * dpr);
    var kx = W / vr.width, ky = H / vr.height;
    var sx0 = Math.round((sr.left - vr.left) * kx), sx1 = Math.round((sr.right - vr.left) * kx);
    var sy0 = Math.round((sr.top - vr.top) * ky), sy1 = Math.round((sr.bottom - vr.top) * ky);
    var lw = Math.max(1, Math.round(dpr));
    var g = this.pick();
    var key = [W, H, sx0, sy0, sx1, sy1, lw, g.ox.join()].join(',');
    if (key === this.key) return;
    this.key = key;
    var R = function (v) { return Math.round(v * dpr); };
    var OX = g.ox.map(R), OY = g.oy.map(R), A = g.a.map(R);
    var n = g.ox.length;
    /* Drop outer tiers that would not fit inside the stage (a narrow stage keeps the inner tiers). Each offset is
       rounded on its own, so at a ratio such as 1.25 the outermost line can land one device pixel past the box (a
       46px offset is 57.5 device pixels); that line is kept and clamped to the box edge instead of dropped. */
    while (n > 2 && (sx0 - OX[n - 1] < -1 || sy0 - OY[n - 1] < -1 || sx1 + OX[n - 1] > W + 1 || sy1 + OY[n - 1] > H + 1)) n--;
    var half = Math.floor((sx1 - sx0) / 2);
    var XL = A.map(function (a) { return sx0 + half - a; });   /* left top arm ends here (exclusive) */
    var XR = A.map(function (a) { return sx1 - half + a; });   /* right top arm starts here */
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    var tiersG = document.createElementNS(NS, 'g'), segsG = document.createElementNS(NS, 'g');
    tiersG.setAttribute('class', 'zt-tiers');
    segsG.setAttribute('class', 'zt-segs');
    svg.appendChild(tiersG);
    svg.appendChild(segsG);
    function rect(parent, x0, y0, x1, y1, cls) {
      if (x1 <= x0 || y1 <= y0) return null;
      var r = document.createElementNS(NS, 'rect');
      r.setAttribute('x', x0); r.setAttribute('y', y0); r.setAttribute('width', x1 - x0); r.setAttribute('height', y1 - y0);
      r.setAttribute('class', cls);
      parent.appendChild(r);
      return r;
    }
    for (var k = n - 1; k >= 0; k--) {
      var xl = Math.max(0, sx0 - OX[k]), xr = Math.min(W - lw, sx1 + OX[k] - lw), yt = Math.max(0, sy0 - OY[k]), yb = Math.min(H - lw, sy1 + OY[k] - lw), c = 'zt-tier k' + k;
      rect(tiersG, xl, yt, XL[k], yt + lw, c);               /* left top arm */
      rect(tiersG, xl, yt + lw, xl + lw, yb, c);             /* left side */
      rect(tiersG, xl, yb, xr + lw, yb + lw, c);             /* the unbroken bottom */
      rect(tiersG, xr, yt + lw, xr + lw, yb, c);             /* right side */
      rect(tiersG, XR[k], yt, xr + lw, yt + lw, c);          /* right top arm */
    }
    var per = 2 * (n - 1);
    for (var side = 0; side < 2; side++) {
      for (k = n - 2; k >= 0; k--) {
        var j = (n - 2 - k) * 2, z = zone(k), yk = Math.max(0, sy0 - OY[k]), yk1 = Math.max(0, sy0 - OY[k + 1]);
        var riser = side === 0 ? [XL[k + 1] - lw, yk1, XL[k + 1], yk + lw] : [XR[k + 1], yk1, XR[k + 1] + lw, yk + lw];
        var tread = side === 0 ? [XL[k + 1], yk, XL[k], yk + lw] : [XR[k], yk, XR[k + 1], yk + lw];
        var parts = [['r', riser, j], ['t', tread, j + 1]];
        for (var p = 0; p < 2; p++) {
          var r = rect(segsG, parts[p][1][0], parts[p][1][1], parts[p][1][2], parts[p][1][3],
                       'zt-seg ' + parts[p][0] + ' k' + k + ' ' + z);
          if (!r) continue;
          r.style.setProperty('--zt-j', String(parts[p][2]));
          var a = parts[p][2] - (per - 4);
          if (a >= 0) { r.setAttribute('data-zt-a', ''); r.style.setProperty('--zt-a', String(a)); }
        }
      }
    }
    this.segs = Array.prototype.slice.call(segsG.childNodes);
    for (var q = 0; q < this.segs.length; q++) {
      var cl = this.segs[q].getAttribute('class');
      this.segs[q].__j = +this.segs[q].style.getPropertyValue('--zt-j') || 0;
      this.segs[q].__z = / zA/.test(cl) ? 'zA' : / zB/.test(cl) ? 'zB' : 'zC';
      this.segs[q].__r = / r /.test(cl);
    }
    if (this.ticker && this.tickTimer) this._tickPaint();
    this.info = { dpr: dpr, devicePixels: [W, H], fromDevicePixelBox: !!dev, reportedDevicePixelBox: this.dev, line: lw, tiers: n,
                  screen: [sx0, sy0, sx1, sy1], segmentsPerStair: per };
    /* Redrawing replaces the elements, so a walking frame restarts its walk from the outermost step. */
  };

  ZtFrame.prototype.destroy = function () {
    if (this.timer) clearTimeout(this.timer);
    if (this.tickTimer) clearTimeout(this.tickTimer);
    if (this.ro) this.ro.disconnect();
    if (this.io) this.io.disconnect();
    if (this.phone) this._unlisten(this.phone, this._draw);
    if (this.dprMq) this._unlisten(this.dprMq, this._dprChange);
    global.removeEventListener('resize', this._draw);
    document.removeEventListener('visibilitychange', this._vis);
    if (this.box.parentNode) this.box.parentNode.removeChild(this.box);
  };

  global.ZtFrame = ZtFrame;
})(window);
