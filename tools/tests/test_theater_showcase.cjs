'use strict';
// Homepage Theater chapter ("Where ZOTHEOS listens.") controller checks, against the owner's decision (film previews
// start muted when in view) and the Theater's player semantics: nothing reaches a provider before the section nears
// the screen (images at 1250px, the player at 400px) and stays there for half a second while the page is not flying
// past (a jump across it contacts nobody); the muted preview once 60% of the screen and its whole
// control row are in view (Living and Calm; never in Still, under the OS reduced-motion floor, with Save-Data, behind
// the intro, or while visibility is unknown); mute before every page start; a start the visitor leaves before it lands
// paused unseen; a slow start still the page's own however long the player takes (its limits hold, and the status
// keeps saying it is starting), and a start that never begins called off for good; Play, Sound and the player's own controls
// taking control, a caption choice only restarting the limit; the visitor's own playback never resumed by itself
// (so an earlier Sound choice never unmutes a new preview); stale sound reports ignored and opposite requests reset;
// the visitor's Pause respected; the 45 s and phone 15 s limits stopping the stream and Play resuming at the spot;
// strict postMessage origins; the controls straight under the screen and one Before Watching note after them (Play
// described by it until the first start, spoken once at the first automatic start); a status that asks for Play where
// the window is too short for the start rule, following a resize; the hero door landing low enough to show the
// control row where it would end below the window, never past the start rule; the controls counted as seen once clear of the header (the phone dock steps aside); a press on the covering poster
// as Play; the keyboard ring on the player; the mirror's Theater row; the Haptics preference (visible even without the
// section) and haptics only inside a real press; the floating page buttons stepping aside; and PREVIEW_AUTOPLAY = false
// meeting the no-autoplay contract (native controls, no autoplay permission, no message interface, no command sent).
// Run: node --test tools/tests/test_theater_showcase.cjs [path/to/index.html]
// Dependency-free: the real markup block from index.html is parsed into a small fake DOM and the real script block runs
// in a vm with fake timers, a fake clock, fake IntersectionObservers driven by the test, and a fake YouTube player that
// answers the documented postMessage protocol. No browser, network or file mutation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const arg = process.argv.slice(2).find(a => !a.startsWith('-') && /\.html?$/.test(a));
const pagePath = path.resolve(arg || path.join(__dirname, '..', '..', 'index.html'));
const page = fs.readFileSync(pagePath, 'utf8').replace(/\r\n?/g, '\n');
function between(a, b) {
  const i = page.indexOf(a), j = page.indexOf(b);
  assert(i >= 0 && j > i, 'marker pair ' + a);
  assert.equal(page.indexOf(a, i + 1), -1, 'marker appears once: ' + a);
  return page.slice(i + a.length, j);
}
const MARKUP = between('<!-- theater-showcase:markup -->', '<!-- /theater-showcase:markup -->');
const SCRIPT = between('/* theater-showcase:js */', '/* /theater-showcase:js */');
const HAPTICS_ROW = (/<div class="ap-row" id="apHapticsRow" hidden>[\s\S]*?<\/div>\s*<\/div>/.exec(page) || [''])[0];
const MIRROR_ROW = (/<div class="mirror-row"><span>Theater section<\/span><span class="mr-val" id="mrTheater">[^<]*<\/span><\/div>/.exec(page) || [''])[0];
const INTRO = '<div id="introOverlay" class="intro-overlay"></div>';
const YT = 'https://www.youtube-nocookie.com';
const SWITCH_ON = 'var PREVIEW_AUTOPLAY = true;';
const switchOff = s => { assert.equal(s.split(SWITCH_ON).length, 2, 'the switch appears once, on'); return s.replace(SWITCH_ON, 'var PREVIEW_AUTOPLAY = false;'); };
const VOID = new Set(['br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr', 'path', 'rect']);

function harness({ script = SCRIPT, storage = {}, reduce = false, coarse = false, phone = false, vibrate = true,
  saveData = false, floaters = false, haptics = false, player = 'answers', origin = 'https://zotheos.org',
  startDelay = 0, soundDelay = 0, intro = false, mirror = false, section = true, observers = true, htmlMotion = null, aim = null } = {}) {
  let now = 1000000, serial = 0, scrollY = 0, sectionTop = 6000;   // the section starts far below the window
  let viewH = 900;
  const geo = {};   // laid-out boxes by id, set by a test; unset boxes measure 0 (no layout)
  const timers = new Map(), sent = [], vib = [], posted = [], mos = [];
  const VIEW_H = 900, SECTION_H = 1900;
  const activation = { isActive: false, hasBeenActive: false };
  function tick(ms) {
    const until = now + ms;
    for (let guard = 0; ; guard++) {
      assert(guard < 100000, 'timers stay bounded');
      const due = [...timers].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!due) break;
      timers.delete(due[0]);
      now = Math.max(now, due[1].at);
      due[1].fn();
    }
    now = until;
  }
  class Node {
    constructor(tag) {
      this.tagName = tag ? tag.toUpperCase() : '#text'; this.childNodes = []; this.attrs = new Map();
      this.listeners = new Map(); this.parentNode = null; this.data = ''; this.style = {}; this.offsetHeight = 0;
    }
    get children() { return this.childNodes.filter(n => n.tagName !== '#text'); }
    get firstChild() { return this.childNodes[0] || null; }
    get id() { return this.getAttribute('id'); }
    get hidden() { return this.attrs.has('hidden'); }
    set hidden(v) { if (v) this.attrs.set('hidden', ''); else this.attrs.delete('hidden'); }
    get className() { return this.getAttribute('class') || ''; }
    set className(v) { this.setAttribute('class', v); }
    set tabIndex(v) { this.setAttribute('tabindex', String(v)); }
    get textContent() { return this.tagName === '#text' ? this.data : this.childNodes.map(n => n.textContent).join(''); }
    set textContent(v) { this.childNodes.forEach(n => { n.parentNode = null; }); this.childNodes = []; if (v !== '') { const t = new Node(); t.data = String(v); this.appendChild(t); } }
    set innerHTML(v) { this.textContent = ''; this.html = String(v); }
    getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
    hasAttribute(k) { return this.attrs.has(k); }
    setAttribute(k, v) { this.attrs.set(k, String(v)); for (const mo of mos) if (mo.target === this && mo.filter.includes(k)) later(0, () => mo.cb([])); }
    getBoundingClientRect() { return this === document.getElementById('theater') ? { top: sectionTop, bottom: sectionTop + SECTION_H } : (geo[this.getAttribute('id')] || { top: 0, bottom: 0 }); }
    removeAttribute(k) { this.attrs.delete(k); }
    appendChild(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.push(n); if (n.tagName === 'IFRAME') onFrame(n); return n; }
    insertBefore(n, ref) { if (n.parentNode) n.parentNode.removeChild(n); const i = ref ? this.childNodes.indexOf(ref) : -1; n.parentNode = this; if (i < 0) this.childNodes.push(n); else this.childNodes.splice(i, 0, n); return n; }
    removeChild(n) { const i = this.childNodes.indexOf(n); assert(i >= 0); this.childNodes.splice(i, 1); n.parentNode = null; return n; }
    *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
    matchesOne(c) {
      if (c.tag && this.tagName !== c.tag.toUpperCase()) return false;
      if (c.id && this.getAttribute('id') !== c.id) return false;
      for (const k of c.cls) if (!this.className.split(/\s+/).includes(k)) return false;
      for (const [k, v] of c.attrs) if (!this.attrs.has(k) || (v !== undefined && this.attrs.get(k) !== v)) return false;
      return true;
    }
    matches(sel) {
      const parts = sel.trim().split(/\s+/).map(compile);
      if (!this.matchesOne(parts[parts.length - 1])) return false;
      let n = this.parentNode;
      for (let i = parts.length - 2; i >= 0; i--) { while (n && !(n.matchesOne && n.matchesOne(parts[i]))) n = n.parentNode; if (!n) return false; n = n.parentNode; }
      return true;
    }
    closest(sel) { let n = this; while (n && n.matchesOne) { if (n.matches(sel)) return n; n = n.parentNode; } return null; }
    querySelectorAll(sel) { return [...this.walk()].filter(n => n.matches(sel)); }
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
    addEventListener(t, fn) { if (!this.listeners.has(t)) this.listeners.set(t, []); this.listeners.get(t).push(fn); }
    removeEventListener(t, fn) { const l = this.listeners.get(t) || []; const i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); }
    dispatch(t, extra = {}) {
      const e = Object.assign({ type: t, target: this, defaultPrevented: false, preventDefault() { e.defaultPrevented = true; } }, extra);
      for (let n = this; n; n = t === 'click' ? n.parentNode : null) for (const fn of [...(n.listeners.get(t) || [])]) fn(e);
      return e;
    }
    focus() { document.activeElement = this; }
    // A visitor's press is a user activation; a click from a page script is not.
    click(extra) { activation.isActive = true; activation.hasBeenActive = true; try { return this.dispatch('click', extra); } finally { activation.isActive = false; } }
    scriptedClick() { this.dispatch('click'); }
  }
  function compile(s) {
    const c = { tag: null, id: null, cls: [], attrs: [] };
    const re = /^([a-z][a-z0-9]*)|#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
    let m, seen = 0;
    while ((m = re.exec(s))) { seen += m[0].length; if (m[1]) c.tag = m[1]; else if (m[2]) c.id = m[2]; else if (m[3]) c.cls.push(m[3]); else c.attrs.push([m[4], m[5]]); }
    assert.equal(seen, s.length, 'fake DOM selector not supported: ' + s);
    return c;
  }
  function parse(html, host) {
    const stack = [host];
    const re = /<!--[\s\S]*?-->|<\/([a-zA-Z0-9-]+)\s*>|<([a-zA-Z0-9-]+)((?:\s+[a-zA-Z_:][\w:.-]*(?:="[^"]*")?)*)\s*(\/?)>|([^<]+)/g;
    let m;
    while ((m = re.exec(html))) {
      const top = stack[stack.length - 1];
      if (m[0].startsWith('<!--')) continue;
      if (m[1]) { const t = stack.pop(); assert.equal(t.tagName, m[1].toUpperCase(), 'balanced markup'); continue; }
      if (m[2]) {
        const n = new Node(m[2]);
        const ar = /([a-zA-Z_:][\w:.-]*)(?:="([^"]*)")?/g;
        let a;
        while ((a = ar.exec(m[3]))) n.attrs.set(a[1], (a[2] || '').replace(/&amp;/g, '&').replace(/&#x27;/g, "'"));
        top.appendChild(n);
        if (!VOID.has(m[2].toLowerCase()) && !m[4]) stack.push(n);
        continue;
      }
      const t = new Node(); t.data = m[5]; top.appendChild(t);
    }
    assert.equal(stack.length, 1, 'all elements closed');
  }
  const document = new Node('#document');
  document.documentElement = new Node('html');
  document.appendChild(document.documentElement);
  document.body = new Node('body');
  document.documentElement.appendChild(document.body);
  document.hidden = false;
  document.activeElement = document.body;
  if (htmlMotion) document.documentElement.setAttribute('data-motion', htmlMotion);
  if (section) parse(MARKUP, document.body);
  if (haptics) parse(HAPTICS_ROW, document.body);
  if (mirror) { assert(MIRROR_ROW, 'the mirror has a Theater row'); parse(MIRROR_ROW, document.body); }
  if (intro) parse(INTRO, document.body);
  if (floaters) for (const id of ['mobileCta', 'scrollTop', 'mirrorBtn']) { const n = new Node('div'); n.setAttribute('id', id); document.body.appendChild(n); }
  document.getElementById = id => document.documentElement.querySelectorAll('#' + id)[0] || null;
  document.createElement = tag => new Node(tag);
  document.createElementNS = (ns, tag) => new Node(tag);
  document.createTextNode = t => { const n = new Node(); n.data = String(t); return n; };
  document.querySelector = sel => document.documentElement.querySelector(sel);

  // The fake player: answers the documented YouTube message protocol, a few milliseconds later, from its own origin.
  let frame = null;
  const yt = { muted: null, state: -1, t: 0 };
  function deliver(data, from = YT, source) {
    const win = source || (frame && frame.contentWindow);
    later(5, () => window.dispatch('message', { origin: from, source: win, data: typeof data === 'string' ? data : JSON.stringify(data) }));
  }
  function later(ms, fn) { const id = ++serial; timers.set(id, { fn, at: now + ms }); return id; }
  function onFrame(f) {
    frame = f;
    f.contentWindow = {
      postMessage(msg, target) {
        posted.push(target);
        const d = typeof msg === 'string' ? JSON.parse(msg) : msg;
        sent.push(d);
        if (player !== 'answers' && player !== 'ignores-play') return;
        if (d.event === 'listening' && yt.state === -1) { yt.state = 5; deliver({ event: 'onReady' }); }
        if (d.event !== 'command') return;
        if (d.func === 'playVideo' && player === 'ignores-play') return;   // a start the browser or provider refused
        if (d.func === 'seekTo') yt.t = d.args[0];
        if (d.func === 'loadVideoById') { yt.t = d.args[0].startSeconds; yt.state = 1; deliver({ event: 'infoDelivery', info: { playerState: 1 } }); }
        if (d.func === 'playVideo' && startDelay) {   // a slow connection: buffering at once, playing much later
          yt.state = 3; deliver({ event: 'infoDelivery', info: { playerState: 3 } });
          yt.pending = later(startDelay, () => { yt.state = 1; deliver({ event: 'infoDelivery', info: { playerState: 1 } }); });
        } else if (d.func === 'playVideo') { yt.state = 1; deliver({ event: 'infoDelivery', info: { playerState: 1 } }); }
        if (d.func === 'pauseVideo') { timers.delete(yt.pending); yt.state = 2; deliver({ event: 'infoDelivery', info: { playerState: 2 } }); }
        if (d.func === 'stopVideo') { timers.delete(yt.pending); yt.state = 5; deliver({ event: 'infoDelivery', info: { playerState: 5 } }); }
        if (d.func === 'mute' || d.func === 'unMute') { yt.muted = d.func === 'mute'; const m = yt.muted; later(soundDelay, () => deliver({ event: 'infoDelivery', info: { muted: m } })); }
      }
    };
  }
  const mqs = { '(prefers-reduced-motion: reduce)': { matches: reduce }, '(pointer: coarse)': { matches: coarse }, '(max-width: 719px)': { matches: phone } };
  for (const q of Object.values(mqs)) q.addEventListener = (t, fn) => { q.change = fn; };
  const ios = [];
  class IO {
    constructor(cb, opts) { this.cb = cb; this.opts = opts || {}; this.targets = []; ios.push(this); }
    observe(t) { this.targets.push(t); }
    disconnect() { this.targets = []; }
    fire(r) { for (const t of [...this.targets]) this.cb([{ target: t, intersectionRatio: r, isIntersecting: r > 0 }], this); }
  }
  const store = Object.assign({}, storage);
  const navigator = { userActivation: activation };
  if (vibrate) navigator.vibrate = ms => { vib.push([now, ms, activation.isActive]); return true; };
  if (saveData) navigator.connection = { saveData: true, effectiveType: '4g' };
  class MO {
    constructor(cb) { this.cb = cb; this.target = null; this.filter = []; mos.push(this); }
    observe(t, o) { this.target = t; this.filter = (o && o.attributeFilter) || []; }
    disconnect() { this.target = null; }
  }
  const window = new Node('#window');
  Object.defineProperty(window, 'scrollY', { get: () => scrollY });
  Object.assign(window, {
    document, navigator, location: { origin }, devicePixelRatio: 1, IntersectionObserver: IO, MutationObserver: MO,
    localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    matchMedia: q => mqs[q] || { matches: false },
    getComputedStyle: () => ({ display: 'block', getPropertyValue: () => '' }),
    setTimeout: (fn, ms) => later(ms || 0, fn), clearTimeout: id => timers.delete(id),
    Date: { now: () => now }, Math, JSON, Array, Object, String, Number, encodeURIComponent, parseFloat
  });
  if (haptics) {
    window.zRadios = (group, onPick) => { group.onPick = onPick; };
    window.zRadioSet = (group, pick) => { for (const b of group.querySelectorAll('[data-haptics]')) b.setAttribute('aria-checked', String(b === pick)); };
  }
  Object.defineProperty(window, 'innerHeight', { get: () => viewH });
  if (aim) window.zAnchorAim = aim;   // an earlier owner of the page's anchor hook (the council story)
  window.window = window;
  if (!observers) delete window.IntersectionObserver;
  vm.runInContext(script, vm.createContext(window), { filename: pagePath });
  const $ = id => document.getElementById(id);
  const root = $('theater');
  const io = which => {
    const t = { screen: $('tscScreen'), bar: $('tscBar') }[which];
    const found = ios.filter(o => o.targets.length && (t ? o.targets[0] === t : o.targets[0] === root && (
      which === 'images' ? o.opts.rootMargin === '1250px 0px' : which === 'near' ? o.opts.rootMargin === '400px 0px' : !o.opts.rootMargin)));
    assert.equal(found.length, 1, 'one observer for ' + which);
    return found[0];
  };
  const h = {
    $, root, document, window, store, sent, posted, vib, timers, tick, frame: () => frame,
    now: () => now, io,
    commands: f => sent.filter(d => d.event === 'command' && d.func === f).length,
    order: () => sent.filter(d => d.event === 'command' && ['mute', 'unMute', 'playVideo', 'pauseVideo', 'stopVideo', 'seekTo', 'loadVideoById'].includes(d.func)).map(d => d.func),
    status: () => $('tscStatus').textContent,
    said: () => $('tscAnnounce').textContent,
    yt,
    reduceTo(v) { mqs['(prefers-reduced-motion: reduce)'].matches = v; mqs['(prefers-reduced-motion: reduce)'].change(); tick(10); },
    motion(m) { store.zotheos_motion = m; window.dispatch('zotheos:effectschange'); tick(10); },
    attr: k => root.getAttribute(k),
    imgsWithSrc: () => root.querySelectorAll('img').filter(i => i.getAttribute('src')),
    // where the section is: its top edge relative to the window (the page scroll moves with it)
    place(top) { scrollY += sectionTop - top; sectionTop = top; },
    // the page scrolls by px over ms, in 50 ms steps, carrying the section with it
    fly(ms, px) { const steps = Math.max(1, Math.round(ms / 50)); for (let i = 0; i < steps; i++) { h.place(sectionTop - px / steps); tick(50); } },
    near() { h.place(300); io('images').fire(1); io('near').fire(1); tick(600); },
    dismissIntro() { $('introOverlay').setAttribute('class', 'intro-overlay dismissed'); tick(10); },
    replayIntro() { $('introOverlay').setAttribute('class', 'intro-overlay'); tick(10); },
    load() { frame.dispatch('load'); tick(300); },
    view(screen = 0.8, bar = 1) { io('bar').fire(bar); io('screen').fire(screen); tick(10); },
    approach() { h.near(); h.load(); h.view(); tick(1500); },
    playing: () => yt.state === 1,
    at(t) { yt.t = t; deliver({ event: 'infoDelivery', info: { currentTime: t } }); tick(10); },
    hide(v) { document.hidden = v; document.dispatch('visibilitychange'); tick(50); },
    // lay out boxes (top and height in px) and resize the window, as the browser would report them
    layout(boxes, height) { for (const [id, [top, h]] of Object.entries(boxes)) geo[id] = { top, bottom: top + h, height: h }; if (height) viewH = height; window.dispatch('resize'); tick(200); },
    deliver
  };
  return h;
}

test('the markup holds no provider request: images are data-src only, no iframe, no src to another host', () => {
  assert(!/<iframe/i.test(MARKUP), 'no player in the markup');
  assert(!/\ssrc="https?:/i.test(MARKUP), 'no remote src attribute in the markup');
  assert.equal((MARKUP.match(/<img data-src="https:\/\/(i\.ytimg\.com|assets\.nfbcdn\.ca)\//g) || []).length, 7);
  assert.equal((MARKUP.match(/<img /g) || []).length, 7);
});

test('at load nothing is requested from a provider: no image source, no player, no message', () => {
  const h = harness();
  h.tick(60000);
  assert.equal(h.imgsWithSrc().length, 0);
  assert.equal(h.frame(), null);
  assert.equal(h.sent.length, 0);
  assert.equal(h.attr('data-script'), '');
  // the floating page buttons, the screen and the bar observers exist but report nothing yet
  h.io('screen').fire(0);
  assert.equal(h.frame(), null);
});

test('images fill at 1250px, the player connects at 400px, and only then', () => {
  const h = harness();
  h.place(1500);   // inside 1250px of the window's foot (900 + 1250), outside 400px
  h.io('images').fire(1);
  h.tick(450);
  assert.equal(h.imgsWithSrc().length, 0, 'the gate holds for half a second');
  h.tick(100);
  const imgs = h.imgsWithSrc();
  assert.equal(imgs.length, 7);
  for (const i of imgs) assert.equal(i.getAttribute('src'), i.getAttribute('data-src'));
  assert.equal(h.frame(), null, 'the player waits for the 400px line');
  h.place(1000);
  h.io('near').fire(1);
  h.tick(450);
  assert.equal(h.frame(), null, 'the player gate holds for half a second too');
  h.tick(100);
  const f = h.frame();
  assert(f, 'player created');
  assert(f.src.startsWith(YT + '/embed/AWCB1Abxktk?'), f.src);
  assert(/[?&]enablejsapi=1&origin=https%3A%2F%2Fzotheos\.org&/.test(f.src));
  assert(/[?&]mute=1(&|$)/.test(f.src) && /cc_load_policy=1&cc_lang_pref=en/.test(f.src));
  assert.equal(f.allow, 'autoplay; encrypted-media; picture-in-picture; fullscreen');
  assert.equal(f.referrerPolicy, 'strict-origin-when-cross-origin');
});

for (const motion of ['living', 'calm']) {
  test('the preview starts without sound once 60% of the screen and the whole control row are in view (' + motion + ')', () => {
    const h = harness({ storage: { zotheos_motion: motion } });
    h.near(); h.load();
    assert.equal(h.status(), 'Ready. The preview starts without sound when the screen and its controls are in view.');
    h.view(0.5, 1); h.tick(3000);
    assert.equal(h.commands('playVideo'), 0, 'under 60% nothing starts');
    h.view(0.6, 0.5); h.tick(3000);
    assert.equal(h.commands('playVideo'), 0, 'the control row must be wholly in view');
    h.view(0.6, 1); h.tick(1500);
    assert.equal(h.commands('playVideo'), 1);
    assert(h.playing());
    const order = h.order();
    assert.equal(order[order.indexOf('playVideo') - 1], 'mute', 'muted right before it plays');
    assert.equal(h.attr('data-primary'), 'sound', 'Sound leads while it plays without sound');
    assert.equal(h.status(), 'Preview playing without sound. Captions on where the provider offers them.');
    h.tick(700);
    assert(/Before watching: Contains discussion of barriers/.test(h.said()), 'the first start is spoken with the note: ' + h.said());
    assert.equal(h.attr('data-light'), 'rest');
    assert(h.posted.every(o => o === YT), 'every command goes to the exact player origin');
  });
}

test('one Before Watching note: after the controls, which sit straight under the screen; never repeated in the status, spoken once', () => {
  assert.equal((MARKUP.match(/<strong>Before watching:<\/strong>/g) || []).length, 1, 'one visible note');
  assert(/<div class="tsc-tiers"[^>]*>(?:\s*<span [^>]*><\/span>)+\s*<\/div>\s*<\/div>\s*(?:<!--[\s\S]*?-->\s*)?<div class="tsc-bar"[\s\S]*?<p class="tsc-status"[^>]*><\/p>\s*<p class="tsc-sr" id="tscAnnounce"[^>]*><\/p>\s*<p class="tsc-before" id="tscBefore"><strong>Before watching:<\/strong>[^<]*<\/p>\s*<div class="tsc-comfort"/.test(MARKUP),
    'the controls follow the frame directly (nothing lengthens the reach from the screen to them), then the status line, then the note');
  assert(!/<div class="tsc-program">[\s\S]*Before watching/.test(MARKUP), 'the programme column does not repeat it');
  const h = harness();
  h.approach(); h.tick(700);
  assert(/Before watching:/.test(h.said()), h.said());
  h.$('tscAnnounce').textContent = '';
  for (let i = 0; i < 40; i++) { h.tick(500); assert(!/Before watching/.test(h.status()), h.status()); }
  h.view(0, 0); h.tick(500); h.view(1, 1); h.tick(3000);
  assert(h.playing());
  assert(!/Before watching/.test(h.said()), 'spoken once per visit');
});

test('Play carries the Before Watching note as its description until the preview first plays', () => {
  const h = harness();
  assert.equal(h.$('tscPlay').getAttribute('aria-describedby'), 'tscBefore', 'heard before any start');
  h.approach(); h.tick(700);
  assert(h.playing());
  assert(/Before watching:/.test(h.said()), 'the first automatic start speaks it');
  assert.equal(h.$('tscPlay').getAttribute('aria-describedby'), null, 'then Pause is not described by it again');
  const s = harness({ storage: { zotheos_motion: 'still' } });
  s.approach(); s.tick(3000);
  assert(!s.playing());
  assert.equal(s.$('tscPlay').getAttribute('aria-describedby'), 'tscBefore', 'focusing Play in Still reads the note first');
  s.$('tscPlay').click(); s.tick(100);
  assert(s.playing());
  assert.equal(s.$('tscPlay').getAttribute('aria-describedby'), null, 'the visitor\'s own playback ends it');
  // a page start the visitor leaves before it lands keeps the description, as it keeps the announcement
  const q = harness({ storage: { zotheos_motion: 'calm' }, startDelay: 400 });
  q.near(); q.load(); q.view(0.8, 1); q.tick(60); q.view(0, 0); q.tick(20);
  q.deliver({ event: 'infoDelivery', info: { playerState: 1 } });   // the provider starts anyway, out of view
  q.tick(2000);
  assert(!q.playing(), 'paused unseen');
  assert.equal(q.$('tscPlay').getAttribute('aria-describedby'), 'tscBefore');
});

test('a window too short for 60% of the screen and the whole control row: the status asks for Play, and follows a resize', () => {
  // a 1440-wide layout: the screen 486px tall, the control row 14px under it and 44px tall
  const boxes = { tscScreen: [100, 486], tscBar: [600, 44] };   // 0.6 x 486 + 58 + 72 header = 421.6px needed
  const h = harness({ storage: { zotheos_motion: 'calm' } });
  h.layout(boxes, 421);
  h.near(); h.load();
  assert.equal(h.status(), 'Ready. Press Play to watch.', 'no start is promised where none can happen');
  h.view(0.55, 1); h.tick(3000);
  assert.equal(h.commands('playVideo'), 0);
  h.layout(boxes, 422);
  assert.equal(h.status(), 'Ready. The preview starts without sound when the screen and its controls are in view.', 'a taller window: the promise returns');
  // scrolled to where both rules hold in the 422px window: 60.1% of the screen under the header, the row's foot at 422
  h.layout({ tscScreen: [-122, 486], tscBar: [378, 44] }, 422);
  h.view(0.6, 1); h.tick(1500);
  assert(h.playing());
  h.view(0, 0); h.tick(500);
  assert.equal(h.status(), 'Paused while out of view. It continues without sound when you return.');
  h.layout(boxes, 400);   // the phone turns, or the window is made shorter
  assert.equal(h.status(), 'Paused while out of view. Press Play to continue.');
  // unmeasured boxes (no layout yet) keep the usual line
  const u = harness({ storage: { zotheos_motion: 'calm' } });
  u.near(); u.load();
  assert.equal(u.status(), 'Ready. The preview starts without sound when the screen and its controls are in view.');
});

test('one frame crossing both thresholds never starts on the control row\'s stale flag: the start rule is measured live', () => {
  // a short window (1440x420): at rest the whole row is in view but only 23% of the screen; one wheel tick up
  // brings 72% of the screen into view and carries the row below the window. The screen's observer reports first.
  for (const motion of ['calm', 'living']) {
    const h = harness({ storage: { zotheos_motion: motion } });
    h.layout({ tscScreen: [-300, 486], tscBar: [200, 44] }, 420);
    h.near(); h.load();
    h.view(0.23, 1); h.tick(3000);
    assert.equal(h.commands('playVideo'), 0, 'under 60% of the screen nothing starts');
    h.layout({ tscScreen: [72, 486], tscBar: [572, 44] }, 420);
    h.io('screen').fire(0.72); h.tick(1500);   // the row's flag still says in view
    assert.equal(h.commands('playVideo'), 0, motion + ': the row is below the window, so nothing starts');
    h.io('bar').fire(0); h.tick(3000);
    assert.equal(h.commands('playVideo'), 0);
    assert(!h.playing());
  }
});

test('the hero door lands lower only where the control row would end below the window, never past the start rule', () => {
  const prior = t => (t && t.id === 'seat-analyst' ? 1234 : null);
  const h = harness({ aim: prior });
  h.near(); h.load();
  const aimAt = t => h.window.zAnchorAim(t), door = h.$('theater-screen');
  assert.equal(aimAt({ id: 'seat-analyst' }), 1234, 'the council story keeps its own targets');
  assert.equal(aimAt({ id: 'faq' }), null, 'any other target keeps the page default');
  // laid out as at 1366 wide: the door's anchor at 300, the screen 85px under it and 407px tall, the row's foot 97px under the screen
  h.layout({ 'theater-screen': [300, 1], tscScreen: [385, 407], tscBar: [845, 44] }, 900);
  const base = h.window.scrollY + 300 - 72;
  assert.equal(aimAt(door), base, 'a tall window: the screen right under the header, as before');
  h.layout({}, 657);   // the row's foot would end 4px below the window
  assert.equal(aimAt(door), base + 12, 'just enough to show the row, with 8px of air');
  h.layout({}, 420);   // room to start (0.6 x 407 + 97 + 72 = 413.2): the row shows, 60% of the screen stays clear
  assert(Math.abs(aimAt(door) - (base + 85 + 0.4 * 407)) < 1e-9, String(aimAt(door) - base));
  h.layout({}, 400);   // too short to start: the whole screen under the header, and no further
  assert.equal(aimAt(door), base + 85);
  // with the switch off there are no page controls to show: the door keeps its landing
  const off = harness({ script: switchOff(SCRIPT) });
  off.layout({ 'theater-screen': [300, 1], tscScreen: [385, 407], tscBar: [845, 44] }, 657);
  assert.equal(off.window.zAnchorAim(off.$('theater-screen')), off.window.scrollY + 228);
});

test('Still never starts anything on its own; the light rests; the visitor\'s Play plays with sound', () => {
  const h = harness({ storage: { zotheos_motion: 'still' } });
  h.approach();
  assert(!/[?&]mute=1/.test(h.frame().src), 'loaded with sound where no preview may start by itself, as on the Theater');
  h.view(1, 1); h.tick(60000);
  assert.equal(h.commands('playVideo'), 0);
  assert.equal(h.attr('data-light'), 'rest');
  assert.equal(h.status(), 'Still: nothing moves. Press Play when you want to watch.');
  h.$('tscPlay').click(); h.tick(500);
  assert.equal(h.commands('playVideo'), 1);
  assert.equal(h.commands('mute'), 0, 'no mute before the visitor\'s own Play');
  assert.equal(h.status(), 'Preview playing with sound. Captions on where the provider offers them.');
  h.tick(60000);
  assert.equal(h.commands('stopVideo') + h.commands('pauseVideo'), 0, 'the visitor\'s own playback has no limit');
});

test('the page\'s Motion comes from html data-motion first, and a change to Still holds a page-started preview', () => {
  const h = harness({ htmlMotion: 'still', storage: { zotheos_motion: 'living' } });
  h.approach(); h.tick(5000);
  assert.equal(h.commands('playVideo'), 0, 'the page says Still');
  const g = harness();
  g.approach();
  assert(g.playing());
  g.motion('still'); g.tick(500);
  assert(!g.playing(), 'Still holds the page-started preview');
  assert.equal(g.status(), 'Still: nothing moves. Press Play when you want to watch.');
});

test('OS reduced motion is an unconditional floor: no question, nothing starts, the light rests, Play still works', () => {
  assert(!/tscAsk|data-answer|Keep Motion|Use Calm|Change Motion/.test(MARKUP), 'no motion question in the markup');
  assert(!/askOpen|data-answer|'ask'|Keep Motion/.test(SCRIPT), 'no motion question in the script');
  for (const stored of [null, 'living', 'calm']) {
    const h = harness({ reduce: true, storage: stored ? { zotheos_motion: stored } : {}, htmlMotion: stored });
    h.approach(); h.view(1, 1); h.tick(60000);
    assert.equal(h.commands('playVideo'), 0, 'nothing starts under the floor, whatever was saved: ' + stored);
    assert.equal(h.attr('data-motion'), 'still');
    assert.equal(h.attr('data-light'), 'rest');
    assert.equal(h.status(), 'Your device asks for reduced motion, so nothing starts on its own. Press Play when you want to watch.');
    h.$('tscPlay').click(); h.tick(500);
    assert(h.playing(), 'the visitor\'s Play plays');
  }
  const live = harness();
  live.approach();
  assert(live.playing());
  live.reduceTo(true); live.tick(500);
  assert(!live.playing(), 'turning the OS setting on holds a page-started preview');
});

test('a visitor who turned Sound off keeps it off when they press Play', () => {
  const h = harness();
  h.approach();
  h.$('tscSound').click(); h.tick(300);   // on
  h.$('tscSound').click(); h.tick(300);   // off again, by choice
  h.$('tscPlay').click(); h.tick(300);    // pause
  h.$('tscPlay').click(); h.tick(300);    // play
  assert.equal(h.commands('unMute'), 1, 'only the visitor\'s own Sound press unmuted it');
  assert(h.status().startsWith('Preview playing without sound.'), h.status());
});

test('the visitor\'s Pause holds through leaving and returning', () => {
  const h = harness();
  h.approach();
  assert(h.playing());
  h.$('tscPlay').click(); h.tick(500);
  assert.equal(h.commands('pauseVideo'), 1);
  assert.equal(h.status(), 'Paused. It stays paused until you press Play.');
  h.view(0, 0); h.tick(2000); h.view(1, 1); h.tick(10000);
  assert.equal(h.commands('playVideo'), 1, 'no restart after the visitor paused');
  h.$('tscPlay').click(); h.tick(500);
  assert.equal(h.commands('playVideo'), 2);
});

test('out of view or a hidden tab pauses a page-started preview; it continues without sound on return', () => {
  const h = harness();
  h.approach();
  h.view(0.1, 0); h.tick(500);
  assert(h.commands('pauseVideo') >= 1);
  assert(!h.playing());
  assert.equal(h.status(), 'Paused while out of view. It continues without sound when you return.');
  h.view(0.8, 1); h.tick(1500);
  assert.equal(h.commands('playVideo'), 2);
  const order = h.order();
  assert.equal(order[order.lastIndexOf('playVideo') - 1], 'mute', 'muted again before it continues');
  assert(h.playing());
  h.hide(true); h.tick(500);
  assert(!h.playing(), 'a hidden tab pauses it');
});

test('the visitor\'s own playback, paused out of view, never resumes by itself: an earlier Sound choice cannot unmute a new start', () => {
  const h = harness();
  h.approach();
  h.$('tscSound').click(); h.tick(500);           // Sound On: the visitor's playback now, with sound
  assert.equal(h.yt.muted, false);
  h.view(0, 0); h.tick(500);
  assert(!h.playing(), 'out of view it pauses (no hidden sound)');
  assert.equal(h.status(), 'Paused while out of view. Press Play to continue.');
  h.view(1, 1); h.tick(30000);
  assert(!h.playing(), 'it waits for Play on return');
  assert.equal(h.commands('playVideo'), 1);
  h.$('tscPlay').click(); h.tick(500);
  assert(h.playing() && h.yt.muted === false, 'Play continues it, with the sound the visitor chose');
});

for (const [label, phone, limit] of [['desktop', false, 45000], ['phone', true, 15000]]) {
  test('a page-started preview stops itself after ' + limit / 1000 + ' s (' + label + ') and Play resumes at the spot', () => {
    const h = harness({ phone });
    h.approach();
    h.at(12.5);
    h.tick(limit - 1500 - 200 - 10);
    assert.equal(h.commands('stopVideo'), 0);
    assert(h.playing());
    h.tick(400);
    assert.equal(h.commands('stopVideo'), 1, 'it stops loading too');
    assert.equal(h.status(), 'Preview paused. Press Play to keep watching.');
    h.view(0, 0); h.view(1, 1); h.tick(5000);
    assert.equal(h.commands('playVideo'), 1, 'a capped preview waits for Play');
    h.$('tscPlay').click(); h.tick(500);
    const order = h.order();
    assert.deepEqual(order.slice(-2), ['unMute', 'loadVideoById'], 'after a stop the preview is loaded again at its spot');
    assert.equal(h.yt.t, 12.5, 'Play resumes where it stopped');
    assert(h.playing());
  });
}

test('time out of view is not counted toward the limit', () => {
  const h = harness({ phone: true });
  h.approach();                                    // 1.5 s playing
  h.tick(8000);                                    // 9.5 s
  h.view(0, 0); h.tick(60000);                     // a minute out of view
  h.view(1, 1); h.tick(1500);                      // 11 s
  assert(h.playing());
  h.tick(3000);                                    // 14 s
  assert.equal(h.commands('stopVideo'), 0, 'only time in view counts');
  h.tick(1500);                                    // 15.5 s
  assert.equal(h.commands('stopVideo'), 1, 'stopped after 15 s in view');
});

test('Play, Sound and the player\'s own controls take control (no limit); a caption choice only restarts the limit', () => {
  for (const take of ['sound', 'native-play', 'native-unmute']) {
    const h = harness({ phone: true });
    h.approach();
    if (take === 'sound') { h.$('tscSound').click(); h.tick(500); assert.equal(h.commands('unMute'), 1); }
    if (take === 'native-play') {   // the visitor pauses and plays inside the player itself
      h.deliver({ event: 'infoDelivery', info: { playerState: 2 } }); h.tick(20);
      h.tick(10000);
      h.deliver({ event: 'infoDelivery', info: { playerState: 1 } }); h.tick(20);
    }
    if (take === 'native-unmute') { h.tick(6000); h.deliver({ event: 'infoDelivery', info: { muted: false } }); h.tick(20); }
    h.tick(60000);
    assert.equal(h.commands('stopVideo') + h.commands('pauseVideo'), 0, take + ': no limit once the visitor takes control');
  }
  const c = harness({ phone: true });
  c.approach();
  c.tick(10000);
  c.$('tscCaptions').click(); c.tick(20);
  assert.equal(c.attr('data-primary'), 'sound', 'still the page-started preview without sound');
  c.tick(14000);
  assert.equal(c.commands('stopVideo'), 0, 'the limit started again at the caption choice');
  c.tick(1500);
  assert.equal(c.commands('stopVideo'), 1);
});

test('sound reports: a stale unmute report after the page\'s mute is ignored; a sound request resets the opposite one', () => {
  // Still first: the player loads with sound; then Motion becomes Living and the page starts the preview, muting first
  const h = harness({ phone: true, storage: { zotheos_motion: 'still' }, soundDelay: 400 });
  h.approach(); h.tick(1000);
  assert.equal(h.yt.muted, null, 'loaded with sound, nothing sent yet');
  h.deliver({ event: 'initialDelivery', info: { muted: false } }); h.tick(20);
  h.motion('living'); h.tick(20);
  assert.deepEqual(h.order().slice(-2), ['mute', 'playVideo'], 'mute before play');
  // a report the player sent before the page's mute arrived (the confirmation comes 400 ms later)
  h.deliver({ event: 'infoDelivery', info: { muted: false } }); h.tick(20);
  assert.equal(h.$('tscSound').querySelector('.tsc-state').textContent, 'Checking', 'the state waits for the player\'s answer');
  h.tick(1000);
  assert.equal(h.$('tscSound').querySelector('.tsc-state').textContent, 'Off');
  assert.equal(h.attr('data-primary'), 'sound', 'still the page-started preview: the stale report was not read as the visitor\'s unmute');
  h.tick(20000);
  assert.equal(h.commands('stopVideo'), 1, 'the limit still holds');
  const r = harness();
  r.approach();
  r.$('tscSound').click(); r.$('tscSound').click(); r.tick(1000);
  assert.deepEqual(r.order().filter(f => f === 'mute' || f === 'unMute').slice(-2), ['unMute', 'mute']);
  assert.equal(r.$('tscSound').querySelector('.tsc-state').textContent, 'Off', 'the last request wins once confirmed');
});

test('a page start the player never begins is called off at 6 s: the status says so and nothing starts again by itself', () => {
  const h = harness({ phone: true, player: 'ignores-play' });
  h.near(); h.load(); h.view();                 // the page asks the player to start at once (no frame light here)
  h.tick(5000);
  assert.equal(h.commands('playVideo'), 1);
  assert.equal(h.status(), 'Starting the preview without sound.');
  h.tick(2000);
  assert.equal(h.commands('pauseVideo'), 1, 'the queued start is cancelled, so it cannot begin later unattended');
  assert.equal(h.status(), 'Ready. Press Play to watch.', 'the start was refused');
  h.view(0, 0); h.tick(500); h.view(1, 1); h.tick(10000);
  assert.equal(h.commands('playVideo'), 1, 'it waits for Play for the rest of the visit');
  // the player's own big Play, pressed inside the player (measured in Chrome: the window blurs with the frame active)
  h.document.activeElement = h.frame(); h.window.dispatch('blur');
  const pauses = h.commands('pauseVideo');
  h.deliver({ event: 'infoDelivery', info: { playerState: 1 } }); h.tick(20);
  h.tick(60000);
  assert.equal(h.commands('stopVideo') + h.commands('pauseVideo'), pauses, 'no limit on the visitor\'s own start');
  // and the visitor's own Play under the screen plays at once
  const p = harness({ phone: true, player: 'ignores-play' });
  p.approach(); p.tick(7000);
  p.$('tscPlay').click(); p.tick(20);
  assert.equal(p.commands('playVideo'), 2);
});

test('a start the page called off that begins anyway, with no press inside the player, is paused again at once', () => {
  const h = harness({ phone: true, player: 'ignores-play' });
  h.approach(); h.tick(7000);
  assert.equal(h.commands('pauseVideo'), 1);
  h.deliver({ event: 'infoDelivery', info: { playerState: 2 } }); h.tick(20);    // a repeated report of the confirmed cancel
  h.tick(13000);
  h.deliver({ event: 'infoDelivery', info: { playerState: 1 } }); h.tick(20);    // the provider starts it anyway
  assert.equal(h.commands('pauseVideo'), 2, 'still the page\'s own start, so it is paused again');
  h.deliver({ event: 'infoDelivery', info: { playerState: 2 } }); h.tick(50);
  assert.equal(h.status(), 'Ready. Press Play to watch.');
  assert(!/Before watching/.test(h.said()), 'no first-start announcement for a start that was called off');
});

test('Save-Data: no preview starts on its own', () => {
  const h = harness({ saveData: true });
  h.approach(); h.tick(10000);
  assert.equal(h.commands('playVideo'), 0);
  assert.equal(h.status(), 'Ready. Press Play to watch. Previews do not start on their own while your browser asks to save data.');
});

test('unknown visibility stays manual: without an IntersectionObserver nothing connects or starts; Play does', () => {
  const h = harness({ observers: false });
  h.tick(60000);
  assert.equal(h.frame(), null);
  assert.equal(h.imgsWithSrc().length, 0);
  assert.equal(h.$('tscPlay').getAttribute('aria-disabled'), 'false');
  h.$('tscPlay').click(); h.tick(10);
  assert(h.frame(), 'Play connects the player');
  h.load(); h.tick(500);
  assert(h.playing(), 'and plays it');
  assert.equal(h.commands('mute'), 0);
});

test('messages are read only from the player\'s exact origin and window', () => {
  const h = harness({ player: 'silent' });
  h.near(); h.load(); h.view(1, 1);
  h.deliver({ event: 'onReady' }, 'https://www.youtube.com'); h.tick(50);
  h.deliver({ event: 'onReady' }, YT, { postMessage() {} }); h.tick(50);
  h.deliver('not json', YT); h.tick(50);
  assert.equal(h.status(), 'Connecting to YouTube.');
  h.deliver({ event: 'onReady' }); h.tick(1500);
  assert.notEqual(h.status(), 'Connecting to YouTube.');
  assert(h.commands('playVideo') >= 1);
});

test('haptics: a visible Appearance preference, only inside a real press, never in Still or under the floor, off with zotheos_haptics=off', () => {
  const on = harness({ coarse: true, haptics: true });
  assert.equal(on.$('apHapticsRow').hidden, false, 'the Appearance row shows on a touch device that can vibrate');
  on.approach();
  on.tick(7000);
  assert.equal(on.vib.length, 0, 'no pulse without a press');
  on.$('tscCaptions').scriptedClick(); on.tick(100);
  assert.equal(on.vib.length, 0, 'a click from a page script is no press');
  on.$('tscSound').click();
  assert.deepEqual(on.vib.map(v => [v[1], v[2]]), [[10, true]]);
  const group = on.$('hapticsGroup');
  group.onPick(group.querySelector('[data-haptics="off"]'));
  assert.equal(on.store.zotheos_haptics, 'off', 'the row saves the choice the Council Route reads too');
  on.$('tscCaptions').click();
  assert.equal(on.vib.length, 1, 'off means off');
  const off = harness({ coarse: true, storage: { zotheos_haptics: 'off' } });
  off.approach(); off.$('tscSound').click();
  assert.equal(off.vib.length, 0);
  for (const opts of [{ storage: { zotheos_motion: 'still' } }, { reduce: true }]) {
    const still = harness(Object.assign({ coarse: true }, opts));
    still.approach(); still.$('tscPlay').click();
    assert.equal(still.vib.length, 0, JSON.stringify(opts));
  }
  const desk = harness({ coarse: false, haptics: true });
  assert.equal(desk.$('apHapticsRow').hidden, true, 'no Haptics row without a touch screen');
  const bare = harness({ coarse: true, haptics: true, section: false });
  assert.equal(bare.$('apHapticsRow').hidden, false, 'the preference stays visible even when the section is missing');
});

test('the floating page buttons step aside while the section is on screen', () => {
  const h = harness({ floaters: true });
  const ids = ['mobileCta', 'scrollTop', 'mirrorBtn'];
  h.io('floaters').fire(0.01);
  assert.deepEqual(ids.map(id => h.$(id).style.visibility), ['hidden', 'hidden', 'hidden']);
  h.io('floaters').fire(0);
  assert.deepEqual(ids.map(id => h.$(id).style.visibility), ['', '', '']);
});

test('PREVIEW_AUTOPLAY = false meets the no-autoplay contract: native controls, no autoplay, no message interface', () => {
  for (const reduce of [false, true]) {
    const h = harness({ script: switchOff(SCRIPT), reduce });
    h.near();
    const f = h.frame();
    assert(f);
    assert(!/enablejsapi/.test(f.src) && !/[?&]mute=1/.test(f.src) && !/autoplay=1/.test(f.src), f.src);
    assert(!/autoplay/.test(f.allow), f.allow);
    h.load(); h.view(1, 1); h.tick(60000);
    assert.equal(h.sent.length, 0, 'no command is ever sent');
    assert.equal(h.$('tscBar').hidden, true, 'no Play, Sound or Captions bar');
    assert.equal(h.$('tscProviderNote').hidden, false);
    assert.equal(h.status(), 'Ready. This player has its own Play, sound and caption controls and does not start on its own.');
    if (reduce) assert.equal(h.attr('data-motion'), 'still', 'the OS setting reads as Still');
  }
});

test('the switch defaults to the owner\'s preview, and story links stay the Theater\'s native #film- links', () => {
  assert.equal(SCRIPT.split(SWITCH_ON).length, 2);
  assert.equal(SCRIPT.split('var STORY_WATCH_LINKS = false;').length, 2);
  const h = harness();
  const links = h.root.querySelectorAll('a[data-story]');
  assert.equal(links.length, 7);
  for (const a of links) assert.equal(a.getAttribute('href'), '/theater#film-' + a.getAttribute('data-story'));
});

// ---- the contact gate (a jump across the section contacts nobody) ---------------------------------------------------

test('a jump that carries the page across the section contacts nobody', () => {
  const h = harness({ mirror: true });
  // the page's smooth anchor scroll: the section crosses the window in about 150 ms and the page rests far past it
  h.place(1200); h.io('images').fire(1); h.io('near').fire(1);
  h.fly(150, 3600);
  h.io('near').fire(0); h.io('images').fire(0);
  h.place(-9000);
  h.tick(60000);
  assert.equal(h.imgsWithSrc().length, 0, 'no thumbnail');
  assert.equal(h.frame(), null, 'no player');
  assert.equal(h.$('mrTheater').textContent, 'YouTube and NFB, as the section nears', 'the mirror says nothing was contacted');
});

test('a fling that is still flying past when the half second ends waits until it slows inside the distance', () => {
  const h = harness();
  h.place(1100); h.io('images').fire(1); h.io('near').fire(1);
  h.fly(500, 1500);   // 3 px per ms, still inside both distances
  h.fly(300, 900);
  assert.equal(h.imgsWithSrc().length, 0, 'nothing while it flies');
  assert.equal(h.frame(), null);
  h.tick(200);         // it comes to rest inside the distance
  assert.equal(h.imgsWithSrc().length, 7);
  assert(h.frame(), 'the player connects once the page settles near the section');
});

test('a reader who scrolls here at reading speed is served without stopping', () => {
  const h = harness({ mirror: true });
  h.place(2000); h.io('images').fire(1);
  h.fly(600, 600);    // 1 px per ms, a steady wheel
  assert.equal(h.imgsWithSrc().length, 7);
  assert.equal(h.$('mrTheater').textContent, 'YouTube and NFB, contacted', 'the mirror row changes once a provider is contacted');
});

// ---- starts that race the visitor ------------------------------------------------------------------------------------

test('Calm: a start still in flight when the visitor scrolls away is called off, and pauses unseen if it lands late', () => {
  for (const lateAnyway of [false, true]) {
    const h = harness({ storage: { zotheos_motion: 'calm' }, startDelay: 400 });
    h.near(); h.load();
    h.view(0.8, 1); h.tick(60);                // Calm: no arrival, the page asks the player to start at once
    assert.equal(h.commands('playVideo'), 1);
    h.view(0, 0); h.tick(20);                  // gone before the player answers
    assert.equal(h.commands('pauseVideo'), 1, 'the pending start is called off');
    if (lateAnyway) h.deliver({ event: 'infoDelivery', info: { playerState: 1 } });   // the provider starts anyway
    h.tick(2000);
    if (lateAnyway) {
      assert.equal(h.commands('pauseVideo'), 2, 'a late start out of view is paused at once');
      h.deliver({ event: 'infoDelivery', info: { playerState: 2 } }); h.tick(50);
    }
    assert.equal(h.status(), 'Paused while out of view. It continues without sound when you return.');
    assert(!/Before watching/.test(h.said()), 'the first-start announcement was not spent out of view');
    h.view(0.8, 1); h.tick(1500);
    assert.equal(h.commands('playVideo'), 2, 'it starts when the visitor returns');
    h.tick(700);
    assert(/Before watching:/.test(h.said()), 'the first-start announcement is kept for the start they see: ' + h.said());
  }
});

for (const [label, delay] of [['3 s', 3000], ['7 s, after the 6 s wait', 7000], ['10.5 s, a slow phone connection', 10500], ['19 s', 19000]]) {
  test('a page start that takes ' + label + ' to begin is still the page own start: cover, announcement and the phone limit hold', () => {
    const h = harness({ phone: true, startDelay: delay });
    h.near(); h.load(); h.view(0.8, 1);
    h.tick(50);                               // the page has asked the player to start (no frame light here)
    assert.equal(h.commands('playVideo'), 1);
    for (let waited = 0; waited + 500 < delay; waited += 500) {
      assert.equal(h.status(), 'Starting the preview without sound.', 'while the player loads, at ' + waited + ' ms');
      h.tick(500);
    }
    h.tick(delay - Math.ceil((delay - 500) / 500) * 500 + 100);
    assert(h.playing(), 'it began');
    assert.equal(h.commands('pauseVideo'), 0, 'a start that is loading is not called off');
    assert.equal(h.attr('data-primary'), 'sound', 'still a page-started preview without sound');
    h.tick(700);
    assert(/Before watching:/.test(h.said()), h.said());
    h.tick(15000);
    assert.equal(h.commands('stopVideo'), 1, 'the 15 s phone limit stopped it');
    assert.equal(h.status(), 'Preview paused. Press Play to keep watching.');
  });
}

test('a start still loading after 20 s is called off: nothing begins later on its own, and the status says so', () => {
  const h = harness({ phone: true, startDelay: 25000 });
  h.near(); h.load(); h.view(0.8, 1);
  h.tick(50 + 19000);
  assert.equal(h.status(), 'Starting the preview without sound.');
  h.tick(1500);
  assert.equal(h.commands('pauseVideo'), 1, 'called off after 20 s');
  h.tick(60000);
  assert(!h.playing(), 'the cancel stopped the queued start');
  assert.equal(h.status(), 'Ready. Press Play to watch.');
  assert.equal(h.commands('playVideo'), 1);
});

test('the controls count as seen once clear of the header: no band is kept for the phone dock, which steps aside', () => {
  const h = harness({ floaters: true, phone: true });
  h.$('mobileCta').offsetHeight = 71;
  assert.equal(h.io('bar').opts.rootMargin, '-72px 0px 0px 0px');
  h.near(); h.load();
  h.io('floaters').fire(0.4);                   // the section is on screen: the dock and both round buttons step aside
  assert.equal(h.$('mobileCta').style.visibility, 'hidden');
  h.view(1, 1); h.tick(1500);
  assert(h.playing(), 'with the whole screen and control row in view it starts, wherever the dock would sit');
});

test('nothing starts behind the intro; it starts once the intro closes; a replayed intro pauses it', () => {
  const h = harness({ intro: true });
  h.approach(); h.view(1, 1); h.tick(10000);
  assert.equal(h.commands('playVideo'), 0, 'not behind the intro');
  h.dismissIntro(); h.tick(1500);
  assert.equal(h.commands('playVideo'), 1);
  assert(h.playing());
  h.replayIntro(); h.tick(100);
  assert.equal(h.commands('pauseVideo'), 1);
  assert(!h.playing());
  h.dismissIntro(); h.tick(1500);
  assert.equal(h.commands('playVideo'), 2, 'it continues when the intro closes again');
});

// ---- the screen, the ring and the names ----------------------------------------------------------------------------

test('a press on the covering poster is Play, not a trip to youtube.com; a modified click and a failed player keep the link', () => {
  const h = harness({ phone: true });
  const poster = h.$('tscPoster');
  assert.equal(poster.getAttribute('aria-hidden'), 'true', 'Play under the screen is the keyboard path');
  assert.equal(poster.getAttribute('tabindex'), '-1');
  h.approach();
  h.tick(1000);                                    // inside the first 4 s: the poster still covers the running preview
  assert(h.$('tscPlayer').hasAttribute('data-cover'));
  let e = poster.click();
  assert.equal(e.defaultPrevented, true);
  assert.equal(h.commands('unMute'), 1, 'it reveals the preview with sound, as Play would');
  assert(!h.$('tscPlayer').hasAttribute('data-cover'));
  const c = harness({ phone: true });
  c.approach(); c.tick(16000);
  assert.equal(c.status(), 'Preview paused. Press Play to keep watching.');
  e = c.$('tscPoster').click();
  assert.equal(e.defaultPrevented, true);
  c.tick(500);
  assert(c.playing(), 'a press on the capped screen plays');
  assert.equal(c.commands('unMute'), 1);
  e = c.$('tscPoster').click({ ctrlKey: true });
  assert.equal(e.defaultPrevented, false, 'a new-tab click still follows the official source');
  const f = harness({ player: 'silent' });
  f.near(); f.load(); f.tick(21000);               // the player never answers: failed
  assert.equal(f.status(), 'This preview cannot play here right now. The official source link stays available.');
  assert.equal(f.root.hasAttribute('data-failed'), true, 'the poster label shows again');
  assert.equal(f.$('tscPoster').getAttribute('aria-hidden'), null);
  assert.equal(f.$('tscPoster').click().defaultPrevented, false, 'the poster is the source link again');
});

test('Tab into the player draws the screen ring; a press inside it does not', () => {
  const h = harness();
  h.approach();
  const f = h.frame(), slot = h.$('tscPlayer');
  // as measured in Chrome: Tab into a cross-origin frame fires only the window's blur, with the frame active
  const into = () => { h.document.activeElement = f; h.window.dispatch('blur'); };
  h.document.dispatch('keydown', { key: 'Tab' }); h.tick(20);
  into();
  assert.equal(slot.hasAttribute('data-ring'), true);
  h.document.activeElement = h.document.body; h.window.dispatch('focus');
  assert.equal(slot.hasAttribute('data-ring'), false, 'the ring goes when focus comes back to the page');
  h.tick(2000);
  into();
  assert.equal(slot.hasAttribute('data-ring'), false, 'focus from a press inside the player brings no Tab');
});

test('the visible Sound and CC words are in the accessible names', () => {
  const sound = /<button class="tsc-btn tsc-sound"[^>]*>[\s\S]*?<\/button>/.exec(MARKUP)[0];
  assert(/<span class="tsc-pre">Turn <\/span>Sound<span class="tsc-post"> On<\/span>/.test(sound), sound);
  const cc = /<button class="tsc-btn tsc-cc-btn"[^>]*>[\s\S]*?<\/button>/.exec(MARKUP)[0];
  assert(/<span class="tsc-cc">CC<\/span><span class="tsc-lbl tsc-cc-word">Captions<\/span>/.test(cc), cc);
});
