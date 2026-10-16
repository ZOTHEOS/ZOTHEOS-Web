
(function () {
  'use strict';
  /* The herald of names (DESIGN_NATIONS 4 to 7). Strings live in TEXT. Every card is set with textContent. */
  var TEXT = {
    also: 'Also known as', say: 'Say it', lands: 'Lands', source: 'Source: ', asOf: 'As of ', checked: 'Checked ',
    person: 'Checked by a person on ', grace: 'The tool could not reach the page on ', open: 'Open this nation',
    own: "Nation's own site", newTab: ' (opens in a new tab)', pron: 'Pronunciation: ', pause: 'Pause', resume: 'Resume',
    ringPos: ' of 15 in today\'s ring', nations: ' nations', lastCheck: 'Last check ', compiled: 'Compiled ',
    pressNext: 'Press Next for the next nation.', loadFail: 'More nations could not load. Every nation still has its own page under By region.',
    live: 'Nation: ', liveLands: '. Lands: ', loading: 'Loading the name list', many: ' nations match', one: '1 nation matches',
    none: 'No nation matches yet. Try another spelling, a place, or browse by region.', showAll: 'Show all',
    searchFail: 'The name list could not load. The region lists below hold every nation.',
    overdue: 'Verification is overdue. The last published check ran on ', overdue2: '. Facts stay shown with their last checked date.'
  };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  /*@FOLD@*/
  function imul(a, b) { return Math.imul(a, b) >>> 0; }
  function fnv1a32(s) {
    var h = 0x811c9dc5, b = new TextEncoder().encode(s);
    for (var i = 0; i < b.length; i++) { h = (h ^ b[i]) >>> 0; h = imul(h, 0x01000193); }
    return h;
  }
  function mix32(x) {
    x = x >>> 0; x = (x ^ (x >>> 16)) >>> 0; x = imul(x, 0x7feb352d); x = (x ^ (x >>> 15)) >>> 0;
    x = imul(x, 0x846ca68b); return (x ^ (x >>> 16)) >>> 0;
  }
  function ringPick(seed, ri, n) { return mix32((seed ^ imul(ri + 1, 0x9e3779b1)) >>> 0) % n; }
  function dayNumber(iso) { var p = iso.split('-'); return Math.floor(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000); }
  function pickFact(id, facts, day) {
    var pref = [], i;
    for (i = 0; i < facts.length; i++) if (facts[i].k === 'today' || facts[i].k === 'achievement') pref.push(i);
    if (!pref.length) for (i = 0; i < facts.length; i++) pref.push(i);
    return pref[(day + fnv1a32(id)) % pref.length];
  }
  function feistel4(x, n, key) {
    if (n <= 1) return 0;
    var bits = Math.max(2, Math.ceil(Math.log2(n))); if ((1 << bits) < n) bits++;
    if (bits % 2) bits++;
    var half = bits / 2, mask = (1 << half) - 1, l, r, f, t, k;
    do {
      l = x >>> half; r = x & mask;
      for (k = 0; k < 4; k++) { f = mix32((r ^ key ^ imul(k + 1, 0x85ebca6b)) >>> 0) & mask; t = r; r = (l ^ f) >>> 0; l = t; }
      x = ((l << half) | r) >>> 0;
    } while (x >= n);
    return x;
  }
  function tokens(s) { var f = fold(s); return f ? f.split(' ') : []; }
  function fieldHas(field, qt) {
    for (var i = 0; i < qt.length; i++) {
      var ok = false;
      for (var j = 0; j < field.length; j++) if (field[j].indexOf(qt[i]) === 0) { ok = true; break; }
      if (!ok) return false;
    }
    return true;
  }
  function exact(field, qt) {
    for (var i = 0; i < qt.length; i++) if (field.indexOf(qt[i]) >= 0) return true;
    return false;
  }
  /* rank: 0 name, 1 also (shown) or also_search (never shown), 2 lands, 3 country or region, 4 spread across fields */
  function rank(e, qt) {
    if (fieldHas(e.tn, qt)) return { r: 0, x: exact(e.tn, qt) ? 0 : 1 };
    for (var i = 0; i < e.ta.length; i++) if (fieldHas(e.ta[i], qt)) return { r: 1, x: 1, also: e.a[i] };
    for (i = 0; i < e.tq.length; i++) if (fieldHas(e.tq[i], qt)) return { r: 1, x: 1 };
    if (fieldHas(e.tl, qt)) return { r: 2, x: 1 };
    if (fieldHas(e.tp, qt)) return { r: 3, x: 1 };
    if (fieldHas(e.all, qt)) return { r: 4, x: 1 };
    return null;
  }
  function prep(row, regions, countries) {
    var e = { id: row[0], n: row[1], a: row[2], q: row[3], l: row[4], r: row[5], c: row[6], f: row[7], s: row[8] };
    e.tn = tokens(e.n); e.ta = e.a.map(tokens); e.tq = e.q.map(tokens); e.tl = tokens(e.l);
    e.tp = tokens(e.c.map(function (c) { return countries[c] || ''; }).join(' ') + ' ' + (regions[e.r] || ''));
    e.all = [].concat(e.tn, [].concat.apply([], e.ta), [].concat.apply([], e.tq), e.tl, e.tp);
    e.key = fold(e.n);
    return e;
  }
  function search(entries, q) {
    var qt = tokens(q), out = [];
    if (!qt.length) return out;
    for (var i = 0; i < entries.length; i++) { var m = rank(entries[i], qt); if (m) out.push({ e: entries[i], m: m }); }
    out.sort(function (a, b) { return a.m.r - b.m.r || a.m.x - b.m.x || (a.e.key < b.e.key ? -1 : a.e.key > b.e.key ? 1 : 0); });
    return out;
  }
  var ZN = { fold: fold, fnv1a32: fnv1a32, mix32: mix32, ringPick: ringPick, dayNumber: dayNumber, pickFact: pickFact,
             feistel4: feistel4, prep: prep, search: search };
  if (typeof document === 'undefined') { if (typeof globalThis !== 'undefined') globalThis.ZN_TEST = ZN; return; }

  /* ---------------------------------------------------------------------------------------------- the page */
  var $ = function (id) { return document.getElementById(id); };
  var d = document.documentElement, herald = $('today'), stage = $('heraldStage'), live = $('heraldLive');
  var btnPrev = $('hrPrev'), btnPause = $('hrPause'), btnNext = $('hrNext'), ringEl = $('hrRing'), status = $('hrStatus');
  var IDX;
  try { IDX = JSON.parse($('heraldIndex').textContent); } catch (e) { return; }
  if (!IDX || !IDX.regions || !herald || !stage) return;
  function fmt(iso) { var p = iso.split('-'); return (+p[2]) + ' ' + MONTHS[+p[1] - 1] + ' ' + p[0]; }
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  var now = new Date(), today = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
  var day = dayNumber(today);
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } return null; }
  var regs = IDX.regions.filter(function (r) { return r.ab > 0; });
  var seed = fnv1a32(today + '|' + IDX.v);
  var ring = regs.map(function (r, j) { return { r: r, i: ringPick(seed, IDX.regions.indexOf(r), r.ab), j: j }; });
  var SEEN = 'zth_nations_ring_' + today, seen = parseInt(store(SEEN) || '0', 10) || 0;
  try { for (var si = localStorage.length - 1; si >= 0; si--) { var sk = localStorage.key(si); if (sk && sk.indexOf('zth_nations_ring_') === 0 && sk !== SEEN) localStorage.removeItem(sk); } } catch (e) {}
  var key = parseInt(store('zth_nations_key') || '', 10);
  if (!(key >= 0)) {
    var buf = new Uint32Array(1); (window.crypto || window.msCrypto).getRandomValues(buf); key = buf[0];
    store('zth_nations_key', String(key));
  }
  var cursor = parseInt(store('zth_nations_cursor') || '', 10);
  if (!(cursor >= 0)) { cursor = store('zth_nations_key') === String(key) ? 0 : (key % 997); }
  var planC = cursor;
  var RD = {}; IDX.regions.forEach(function (r) { RD[r.k] = r.d; });
  var order = regs.slice().sort(function (a, b) { return mix32((key ^ fnv1a32(a.k)) >>> 0) - mix32((key ^ fnv1a32(b.k)) >>> 0); });
  var lastLine = IDX.lastCheck ? TEXT.lastCheck + fmt(IDX.lastCheck) : TEXT.compiled + fmt(IDX.compiled);

  /* ---------------------------------------------------------------------------------------------- shards */
  var shards = {}, queue = [], busy = false, failed = false;
  var ID_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/, URL_RE = /^https:\/\/[^\s"<>]+$/, DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  function str(s, max) { return typeof s === 'string' && s.length > 0 && s.length <= max; }
  function clean(s) { return s.replace(/[\u2013\u2014]/g, ', '); }
  function validCard(c) {
    if (!c || !ID_RE.test(c.id) || !str(c.n, 120) || !str(c.l, 300) || !Array.isArray(c.f) || !c.f.length) return false;
    if (c.o && !URL_RE.test(c.o)) return false;
    if (c.s && !(str(c.s.t, 160) && URL_RE.test(c.s.u) && str(c.s.p, 160))) return false;
    c.f = c.f.filter(function (f) { return str(f.t, 200) && str(f.p, 200) && URL_RE.test(f.u) && DATE_RE.test(f.d) && f.d <= today; });
    return c.f.length > 0;
  }
  function pump() {
    if (busy || !queue.length) return;
    busy = true;
    var job = queue.shift(), ctl = window.AbortController ? new AbortController() : null;
    var t = setTimeout(function () { if (ctl) ctl.abort(); }, 4000);
    fetch(job.url, { credentials: 'omit', signal: ctl ? ctl.signal : undefined }).then(function (r) {
      if (!r.ok) throw new Error('http ' + r.status); return r.json();
    }).then(function (j) { clearTimeout(t); busy = false; job.ok(j); pump(); }, function (e) { clearTimeout(t); busy = false; job.fail(e); pump(); });
  }
  function get(url, first) {
    return new Promise(function (ok, fail) { var job = { url: url, ok: ok, fail: fail }; if (first) queue.unshift(job); else queue.push(job); pump(); });
  }
  function shard(r) {
    if (!shards[r.k]) {
      shards[r.k] = get('/static/nations/' + r.s[0]).then(function (j) {
        if (!j || j.r !== r.k || !Array.isArray(j.n)) throw new Error('bad shard');
        return j.n.map(function (c) { return validCard(c) ? c : null; });
      });
      shards[r.k].catch(function () { delete shards[r.k]; });
    }
    return shards[r.k];
  }

  /* ---------------------------------------------------------------------------------------------- the card */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = clean(String(text)); return e; }
  function ext(href, text) {
    var a = el('a', null, text); a.href = href; a.rel = 'noopener noreferrer'; a.target = '_blank';
    a.appendChild(el('span', 'sr-only', TEXT.newTab)); return a;
  }
  function timeEl(iso) { var t = el('time', null, fmt(iso)); t.setAttribute('datetime', iso); return t; }
  function dot() { var s = el('span', 'hr-dot', '·'); s.setAttribute('aria-hidden', 'true'); return s; }
  function line(cls, k, text, face) {
    var p = el('p', cls); if (face === 'names') p.setAttribute('data-face', 'names');
    p.appendChild(el('span', 'hr-k', k)); p.appendChild(document.createTextNode(' ' + clean(text))); return p;
  }
  function build(c, fi, region) {
    var f = c.f[fi % c.f.length], art = el('article', 'hr-card'), a = (c.a || []).slice(0, 2);
    art.id = 'heraldCard';
    if (!a.length) art.classList.add('no-also');
    if (!c.s) art.classList.add('no-say');
    var head = el('div', 'hr-head'); head.appendChild(el('p', 'hr-region', region.d));
    var h = el('h2', 'hr-name', c.n); h.dir = 'auto';
    h.setAttribute('data-size', c.sz); h.setAttribute('data-face', c.fc); h.setAttribute('data-script', c.sc);
    head.appendChild(h); var ln = el('span', 'hr-line'); ln.setAttribute('aria-hidden', 'true'); head.appendChild(ln);
    art.appendChild(head);
    if (a.length) art.appendChild(line('hr-also', TEXT.also, a.join(', '), c.af));
    if (c.s) { var say = line('hr-say', TEXT.say, c.s.t, c.sf); say.appendChild(ext(c.s.u, TEXT.pron + c.s.p)); art.appendChild(say); }
    art.appendChild(line('hr-lands', TEXT.lands, c.l, c.lf));
    var fact = el('p', 'hr-fact', f.t); if (f.fc === 'names') fact.setAttribute('data-face', 'names'); art.appendChild(fact);
    var rc = el('p', 'hr-receipt'); rc.appendChild(ext(f.u, TEXT.source + f.p));
    if (f.y) { rc.appendChild(dot()); rc.appendChild(document.createTextNode(TEXT.asOf + f.y)); }
    rc.appendChild(dot()); rc.appendChild(document.createTextNode(f.h ? TEXT.person : TEXT.checked)); rc.appendChild(timeEl(f.d));
    if (f.g && f.c) { rc.appendChild(dot()); rc.appendChild(document.createTextNode(TEXT.grace)); rc.appendChild(timeEl(f.c)); }
    art.appendChild(rc);
    var more = el('p', 'hr-more'), op = el('a', null, TEXT.open); op.href = '/nations/' + c.id; more.appendChild(op);
    if (c.o) more.appendChild(ext(c.o, TEXT.own));
    art.appendChild(more);
    return { art: art, name: c.n, lands: c.l, fact: f.t, len: f.t.length, face: c.sc !== 'latn' ? c.sc : c.fc, factFace: f.fc };
  }
  var FACES = { brand: 'Instrument Serif', names: 'ZN Serif', cher: 'ZN Cherokee', cans: 'ZN Syllabics', tfng: 'ZN Tifinagh' };
  function fontsReady(v) {
    if (!document.fonts || !document.fonts.load) return Promise.resolve();
    var ps = [document.fonts.load('400 64px "' + (FACES[v.face] || FACES.brand) + '"', v.name)];
    if (v.factFace === 'names') ps.push(document.fonts.load('400 20px "ZN Sans"', v.fact));
    return Promise.race([Promise.all(ps), new Promise(function (r) { setTimeout(r, 600); })]).catch(function () {});
  }

  /* ---------------------------------------------------------------------------------------------- the clock */
  var motion = function () { return d.getAttribute('data-motion') || 'living'; };
  var hist = [], pos = -1, phase = 'in', remaining = 0, timer = 0, started = 0, pressed = false;
  var hover = false, focusIn = false, visible = true, busyNav = false;
  function paused() { return pressed || hover || focusIn || document.hidden || !visible; }
  function dwellFor(v) { return Math.min(14000, Math.max(7000, 4500 + 55 * v.len)); }
  function stopClock() { if (timer) { clearTimeout(timer); timer = 0; remaining = Math.max(0, remaining - (Date.now() - started)); } }
  function clock() {
    stopClock();
    if (phase !== 'dwell' || motion() === 'still' || paused()) return;
    started = Date.now(); timer = setTimeout(function () { timer = 0; remaining = 0; advance(false); }, remaining);
  }
  function onBuilt(v) {
    phase = 'dwell'; remaining = dwellFor(v);
    stage.setAttribute('data-state', 'shown');
    if (hist[pos] && hist[pos].ring >= 0) { seen |= 1 << hist[pos].ring; store(SEEN, String(seen)); }
    if (hist[pos] && hist[pos].walk && hist[pos].c >= cursor) { cursor = hist[pos].c + 1; store('zth_nations_cursor', String(cursor)); }
    prefetch(); clock();
  }
  function whenBuilt(v) {
    var rc = stage.querySelector('.hr-more') || stage.querySelector('.hr-receipt');
    var anims = rc && rc.getAnimations ? rc.getAnimations() : [];
    if (!anims.length || motion() === 'still') { onBuilt(v); return; }
    Promise.all(anims.map(function (a) { return a.finished; })).then(function () { if (cur === v) onBuilt(v); }, function () { if (cur === v) onBuilt(v); });
  }
  var cur = null;
  function show(at, announce) {
    var entry = hist[at];
    return entry.view().then(function (v) {
      return fontsReady(v).then(function () {
        var old = $('heraldCard'); stage.setAttribute('data-state', 'in');
        if (old) stage.replaceChild(v.art, old); else stage.appendChild(v.art);
        pos = at; cur = v; phase = 'in'; marks(entry); line2(entry);
        if (announce) live.textContent = clean(TEXT.live + v.name + TEXT.liveLands + v.lands + '. ' + v.fact);
        whenBuilt(v);
      });
    });
  }
  function fadeOut() {
    return new Promise(function (ok) {
      if (motion() === 'still') { ok(true); return; }
      stage.setAttribute('data-state', 'out'); phase = 'out';
      var c = $('heraldCard'), an = c && c.getAnimations ? c.getAnimations() : [];
      var black = motion() === 'calm' ? 300 : 400;
      var done = function () { if (phase !== 'out') { ok(false); return; } setTimeout(function () { ok(phase === 'out'); }, black); };
      if (!an.length) { done(); return; }
      an[0].finished.then(done, done);
    });
  }
  function nextEntry() {
    for (var j = 0; j < ring.length; j++) if (!(seen & (1 << j)) && !inHist(ring[j])) return ringEntry(ring[j]);
    var c0 = planC++, r = order[c0 % order.length], k = Math.floor(c0 / order.length), n = r.ab;
    var i = feistel4(k % n, n, (key ^ fnv1a32(r.k) ^ IDX.major) >>> 0);
    return cardEntry(r, i, function (c) { return (Math.floor(k / n) + fnv1a32(c.id)) % c.f.length; }, -1, { walk: true, c: c0 });
  }
  function inHist(rg) { for (var h = 0; h < hist.length; h++) if (hist[h].ring === rg.j && hist[h].day === today) return true; return false; }
  function ringEntry(rg) { return cardEntry(rg.r, rg.i, function (c) { return pickFact(c.id, c.f, day); }, rg.j, {}); }
  function cardEntry(r, i, factOf, j, extra) {
    var e = { ring: j, day: today, view: function () {
      return shard(r).then(function (cards) { var c = cards[i]; if (!c) throw new Error('card'); return build(c, factOf(c), r); });
    } };
    for (var x in extra) e[x] = extra[x];
    return e;
  }
  function advance(user, back) {
    if (busyNav) return; busyNav = true; stopClock();
    var target, pushed = false;
    if (back) { if (pos <= 0) { busyNav = false; clock(); return; } target = pos - 1; }
    else if (pos < hist.length - 1) target = pos + 1;
    else { hist.push(nextEntry()); target = hist.length - 1; pushed = true; }
    (user ? Promise.resolve(true) : fadeOut()).then(function (go) {
      if (!go) { if (pushed) hist.pop(); busyNav = false; clock(); return null; }
      return show(target, user).then(function () { failed = false; busyNav = false; });
    }).catch(function () {
      failed = true; busyNav = false; if (pushed) hist.pop();
      stage.setAttribute('data-state', 'shown'); phase = 'dwell'; remaining = 4000; line2(hist[pos]); clock();
    });
  }
  function prefetch() {
    if (failed) return;
    var peek = [];
    for (var j = 0; j < ring.length && peek.length < 2; j++) if (!(seen & (1 << j)) && !inHist(ring[j])) peek.push(ring[j].r);
    if (peek.length < 2) peek.push(order[cursor % order.length]);
    peek.slice(0, 2).forEach(function (r) { shard(r).catch(function () {}); });
  }

  /* ---------------------------------------------------------------------------------------------- status, marks */
  function marks(entry) {
    var dots = ringEl.querySelectorAll('i');
    for (var i = 0; i < dots.length; i++) dots[i].className = entry && entry.ring === i ? 'on' : '';
  }
  function line2(entry) {
    var parts = [];
    if (entry && entry.ring >= 0) parts.push((entry.ring + 1) + TEXT.ringPos);
    parts.push(IDX.nations.toLocaleString('en-US') + TEXT.nations, lastLine);
    var t = failed ? TEXT.loadFail : parts.join(' · ');
    if (!failed && motion() === 'still') t += ' · ' + TEXT.pressNext;
    status.textContent = t;
    btnPrev.setAttribute('aria-disabled', pos <= 0 ? 'true' : 'false');
  }
  ringEl.textContent = '';
  for (var g = 0; g < 3; g++) { var grp = el('span', 'g'); for (var gi = 0; gi < 5; gi++) grp.appendChild(el('i')); ringEl.appendChild(grp); }

  /* ---------------------------------------------------------------------------------------------- the static first card */
  var F = IDX.first, staticArt = $('heraldCard'), firstRing = -1;
  if (F && ring[0] && ring[0].r.k === F.k && ring[0].i === F.i && F.date === today) firstRing = 0;
  else if (F && ring.length) { for (var fr = 0; fr < ring.length; fr++) if (ring[fr].r.k === F.k && ring[fr].i === F.i && F.date === today) firstRing = fr; }
  var staticView = { art: staticArt, name: F ? F.n : '', lands: F ? F.l : '', fact: F ? F.t : '', len: F ? F.t.length : 60 };
  hist.push({ ring: firstRing, day: today, view: function () { var a = staticArt.cloneNode(true); var v = {}; for (var x in staticView) v[x] = staticView[x]; v.art = a; v.face = F.face; return Promise.resolve(v); } });
  pos = 0; cur = staticView; marks(hist[0]); line2(hist[0]);
  if (herald.contains(document.activeElement)) live.textContent = clean(TEXT.live + staticView.name + TEXT.liveLands + staticView.lands + '. ' + staticView.fact);
  whenBuilt(staticView);

  /* ---------------------------------------------------------------------------------------------- controls */
  btnNext.addEventListener('click', function () { advance(true, false); });
  btnPrev.addEventListener('click', function () { if (btnPrev.getAttribute('aria-disabled') !== 'true') advance(true, true); });
  btnPause.addEventListener('click', function () {
    pressed = !pressed; btnPause.setAttribute('aria-pressed', pressed ? 'true' : 'false');
    btnPause.textContent = pressed ? TEXT.resume : TEXT.pause; pressed ? stopClock() : clock();
  });
  $('hrControls').addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); advance(true, false); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); if (pos > 0) advance(true, true); }
  });
  function cancelFade() { if (phase === 'out') { stage.setAttribute('data-state', 'shown'); phase = 'dwell'; remaining = 2500; } }
  herald.addEventListener('pointerenter', function () { hover = true; cancelFade(); stopClock(); });
  herald.addEventListener('pointerleave', function () { hover = false; clock(); });
  herald.addEventListener('focusin', function () { focusIn = true; cancelFade(); stopClock(); });
  herald.addEventListener('focusout', function (e) { if (!herald.contains(e.relatedTarget)) { focusIn = false; clock(); } });
  document.addEventListener('visibilitychange', function () { document.hidden ? stopClock() : clock(); });
  if (window.IntersectionObserver) {
    new IntersectionObserver(function (es) { visible = es[0].intersectionRatio >= 0.6; visible ? clock() : stopClock(); },
      { threshold: [0, 0.6, 1] }).observe(stage);
  }
  new MutationObserver(function () { line2(hist[pos]); clock(); }).observe(d, { attributes: true, attributeFilter: ['data-motion'] });

  /* ---------------------------------------------------------------------------------------------- today's ring list */
  var ringList = $('ringList'), ringNote = $('ringNote');
  if (F && F.date === today && ringNote) ringNote.hidden = true;
  else if (ringList && window.IntersectionObserver) {
    var io = new IntersectionObserver(function (es) {
      if (!es[0].isIntersecting) return; io.disconnect();
      var rows = [], chain = Promise.resolve();
      ring.forEach(function (rg) { chain = chain.then(function () { return shard(rg.r).then(function (cards) { rows.push([rg, cards[rg.i]]); }); }); });
      chain.then(function () {
        var frag = document.createDocumentFragment();
        rows.forEach(function (x) {
          var c = x[1]; if (!c) return;
          var li = el('li'), a = el('a', 'row'); a.href = '/nations/' + c.id;
          var n = el('span', 'nm', c.n); n.dir = 'auto'; n.setAttribute('data-face', c.fc); n.setAttribute('data-script', c.sc);
          a.appendChild(n); a.appendChild(el('span', 'row-m', x[0].r.d));
          var w = c.l.split(/\s+/); var l = el('span', 'row-l', w.slice(0, 8).join(' ') + (w.length > 8 ? '\u00a0...' : ''));
          if (c.lf === 'names') l.setAttribute('data-face', 'names'); a.appendChild(l); li.appendChild(a); frag.appendChild(li);
        });
        ringList.textContent = ''; ringList.appendChild(frag); if (ringNote) ringNote.hidden = true;
      }, function () {});
    }, { rootMargin: '400px 0px' });
    io.observe(ringList);
  }

  /* ---------------------------------------------------------------------------------------------- search */
  var box = $('findBox'), input = $('findInput'), out = $('findResults'), fstat = $('findStatus'), entries = null, loadingS = false, deb = 0;
  if (box && input) {
    box.hidden = false;
    var say = function (t) { clearTimeout(deb); deb = setTimeout(function () { fstat.textContent = t; }, 300); };
    var render = function (all) {
      var q = input.value, res = entries ? search(entries, q) : [];
      out.textContent = '';
      if (!q.trim()) { clearTimeout(deb); fstat.textContent = ''; return; }
      if (!entries) return;
      var lim = all ? res.length : Math.min(24, res.length);
      for (var i = 0; i < lim; i++) {
        var e = res[i].e, li = el('li'), a = el('a'); a.href = '/nations/' + e.id;
        var n = el('span', 'nm', e.n); n.dir = 'auto'; n.setAttribute('data-face', e.f); n.setAttribute('data-script', e.s); a.appendChild(n);
        if (res[i].m.also) a.appendChild(el('span', 'sr-also', TEXT.also + ' ' + res[i].m.also));
        var ls = e.l.length > 90 ? e.l.slice(0, 90).replace(/\s+\S*$/, '') + '\u00a0...' : e.l;
        a.appendChild(el('span', 'row-m', (RD[e.r] || '') + ' · ' + ls));
        li.appendChild(a); out.appendChild(li);
      }
      if (res.length > lim) {
        var li2 = el('li'), b = el('button', 'pill', TEXT.showAll); b.type = 'button';
        b.addEventListener('click', function () { render(true); var as = out.querySelectorAll('a'); if (as[lim]) as[lim].focus(); });
        li2.appendChild(b); out.appendChild(li2);
      }
      say(res.length === 1 ? TEXT.one : res.length ? res.length.toLocaleString('en-US') + TEXT.many : TEXT.none);
    };
    input.addEventListener('focus', function () {
      if (entries || loadingS) return; loadingS = true; fstat.textContent = TEXT.loading;
      get('/static/nations/search.json', true).then(function (j) {
        entries = j.n.map(function (row) { return prep(row, j.regions, j.countries); }); fstat.textContent = ''; render(false);
      }, function () { loadingS = false; fstat.textContent = TEXT.searchFail; });
    });
    input.addEventListener('input', function () { render(false); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { var a = out.querySelector('a'); if (a) { e.preventDefault(); a.focus(); } }
      else if (e.key === 'Escape') { input.value = ''; render(false); }
    });
    out.addEventListener('keydown', function (e) {
      var as = Array.prototype.slice.call(out.querySelectorAll('a, button')), i = as.indexOf(document.activeElement);
      if (i < 0) return;
      if (e.key === 'ArrowDown' && i < as.length - 1) { e.preventDefault(); as[i + 1].focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); (i === 0 ? input : as[i - 1]).focus(); }
      else if (e.key === 'Escape') { input.value = ''; render(false); input.focus(); }
    });
  }

  /* ---------------------------------------------------------------------------------------------- overdue */
  setTimeout(function () {
    get('/static/nations/status.json').then(function (s) {
      var o = $('vpOverdue');
      if (!o || !s || !s.last_full_check) return;
      if (dayNumber(today) - dayNumber(s.last_full_check) > 14) { o.textContent = TEXT.overdue + fmt(s.last_full_check) + TEXT.overdue2; o.hidden = false; }
    }, function () {});
  }, 9000);
})();
