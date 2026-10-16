'use strict';
// Council Route controller acceptance checks: autoplay on view (Living and Calm only), an explicit Pause respected,
// 0 animations in Still, pause and resume rules, step order, timing, CC, the hidden Audio slot and guarded haptics.
// Run: node test_council_route.cjs [path/to/council_route.fragment.html or index.html]
// Dependency-free: the real markup block is parsed into a small fake DOM and the real script block runs in a vm, with
// fake timers, a fake Web Animations clock, a fake IntersectionObserver (the stage starts out of view, ratio 0, as a
// browser reports it far below the fold) and a fake navigator. No browser, network or file mutation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const fragPath = path.resolve(process.argv[2] && !process.argv[2].startsWith('-') ? process.argv[2]
  : path.join(__dirname, '..', 'route', 'council_route.fragment.html'));
const fragment = fs.readFileSync(fragPath, 'utf8').replace(/\r\n?/g, '\n');
function block(a, b) {
  const i = fragment.indexOf(a), j = fragment.indexOf(b);
  assert(i >= 0 && j > i, 'marker pair ' + a);
  assert.equal(fragment.indexOf(a, i + 1), -1, 'marker appears once: ' + a);
  return fragment.slice(i + a.length, j);
}
const MARKUP = block('<!-- council-route:markup -->', '<!-- /council-route:markup -->');
const SCRIPT = block('/* council-route:js */', '/* /council-route:js */');

const VOID = new Set(['br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr']);

function harness({ motion = 'living', reduce = false, width = 1214, script = SCRIPT, ratio = 0, vibrate = true,
  activated = false, storage = {}, overlay = null } = {}) {
  let now = 0, serial = 0;
  const timers = new Map(), anims = [], counters = { raf: 0, interval: 0, scrolls: 0, scrollLog: [] };
  const vib = [], audios = [];
  class Anim {
    constructor(target, frames, opts) {
      this.effect = { target, frames }; this.duration = opts.duration; this.fill = opts.fill;
      this.currentTime = 0; this.playState = 'running'; anims.push(this);
    }
    play() { if (this.playState !== 'idle') this.playState = this.currentTime >= this.duration ? 'finished' : 'running'; }
    pause() { if (this.playState !== 'idle') this.playState = 'paused'; }
    cancel() { this.playState = 'idle'; }
  }
  function advance(to) {
    const dt = to - now;
    for (const a of anims) if (a.playState === 'running') {
      a.currentTime = Math.min(a.duration, a.currentTime + dt);
      if (a.currentTime >= a.duration) a.playState = 'finished';
    }
    now = to;
  }
  function tick(ms) {
    const until = now + ms;
    let guard = 0;
    while (true) {
      const due = [...timers].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!due) break;
      assert(++guard < 100000, 'timer loop must stay bounded');
      const [id, t] = due;
      timers.delete(id);
      advance(Math.max(now, t.at));
      t.fn();
    }
    advance(until);
  }
  const userActivation = { hasBeenActive: !!activated };
  class Node {
    constructor(tag) {
      this.tagName = tag ? tag.toUpperCase() : '#text'; this.nodeName = this.tagName; this.childNodes = [];
      this.attrs = new Map(); this.listeners = new Map(); this.parentNode = null; this.data = '';
      this.style = { setProperty(k, v) { this[k] = String(v); } };
      const self = this;
      this.classList = {
        contains(c) { return (self.getAttribute('class') || '').split(/\s+/).includes(c); },
        toggle(c, on) {
          const set = new Set((self.getAttribute('class') || '').split(/\s+/).filter(Boolean));
          on = on === undefined ? !set.has(c) : !!on;
          if (on) set.add(c); else set.delete(c);
          self.setAttribute('class', [...set].join(' '));
          return on;
        },
        add(c) { this.toggle(c, true); }, remove(c) { this.toggle(c, false); }
      };
      if (this.tagName === 'AUDIO') {
        this.currentTime = 0; this.paused = true; this.plays = 0;
        this.play = () => { this.paused = false; this.plays++; return { catch() {} }; };
        this.pause = () => { this.paused = true; };
        audios.push(this);
      }
    }
    get children() { return this.childNodes.filter(n => n.tagName !== '#text'); }
    get firstChild() { return this.childNodes[0] || null; }
    get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
    get id() { return this.getAttribute('id'); }
    get hidden() { return this.attrs.has('hidden'); }
    set hidden(v) { if (v) this.attrs.set('hidden', ''); else this.attrs.delete('hidden'); }
    get dataset() {
      const self = this, key = k => 'data-' + k.replace(/[A-Z]/g, c => '-' + c.toLowerCase());
      return new Proxy({}, { get: (_, k) => self.getAttribute(key(k)) ?? undefined, set: (_, k, v) => { self.setAttribute(key(k), v); return true; } });
    }
    get className() { return this.getAttribute('class') || ''; }
    set className(v) { this.setAttribute('class', v); }
    get textContent() { return this.tagName === '#text' ? this.data : this.childNodes.map(n => n.textContent).join(''); }
    set textContent(v) { this.childNodes.forEach(n => { n.parentNode = null; }); this.childNodes = []; if (v !== '') { const t = new Node(); t.data = String(v); this.appendChild(t); } }
    getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
    setAttribute(k, v) { this.attrs.set(k, String(v)); }
    removeAttribute(k) { this.attrs.delete(k); }
    appendChild(n) { if (n.tagName === '#fragment') { [...n.childNodes].forEach(c => this.appendChild(c)); return n; } if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.push(n); return n; }
    removeChild(n) { const i = this.childNodes.indexOf(n); assert(i >= 0, 'removeChild of a non-child'); this.childNodes.splice(i, 1); n.parentNode = null; return n; }
    replaceChild(n, old) { const i = this.childNodes.indexOf(old); assert(i >= 0); if (n.parentNode) n.parentNode.removeChild(n); this.childNodes[i] = n; n.parentNode = this; old.parentNode = null; return old; }
    cloneNode() { const c = new Node(this.tagName.toLowerCase()); this.attrs.forEach((v, k) => c.attrs.set(k, v)); return c; }
    contains(n) { while (n) { if (n === this) return true; n = n.parentNode; } return false; }
    *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
    matches(sel) {
      let m = /^\[([\w-]+)(?:=([\w-]+))?\]$/.exec(sel);
      if (m) return this.attrs.has(m[1]) && (m[2] === undefined || this.attrs.get(m[1]) === m[2]);
      m = /^([a-z]+)$/.exec(sel);
      if (m) return this.tagName === m[1].toUpperCase();
      throw new Error('fake DOM selector not supported: ' + sel);
    }
    querySelectorAll(sel) { return [...this.walk()].filter(n => n.matches(sel)); }
    querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
    addEventListener(t, fn) { if (!this.listeners.has(t)) this.listeners.set(t, []); this.listeners.get(t).push(fn); }
    removeEventListener(t, fn) { const l = this.listeners.get(t) || []; const i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); }
    dispatch(t, extra = {}) { let prevented = false; const e = Object.assign({ type: t, target: this, preventDefault() { prevented = true; } }, extra); for (const fn of [...(this.listeners.get(t) || [])]) fn(e); return prevented; }
    dispatchEvent(e) { this.dispatch(e.type, e); return true; }
    animate(frames, opts) { return new Anim(this, frames, opts); }
    getBoundingClientRect() { return { top: 120, bottom: 600, left: 0, right: width, width, height: 480 }; }
    scrollIntoView(o) { counters.scrolls++; counters.scrollLog.push([this.id, JSON.stringify(o === undefined ? null : o)]); }
    get clientWidth() { return this.id === 'crStage' ? (width < 720 ? Math.min(width, 331) : width) : width; }
    // A press is a user activation, as in a browser (sticky: it stays true for the page's life).
    click() { userActivation.hasBeenActive = true; this.dispatch('click'); }
  }
  // Minimal parser for the fragment markup (well-formed, double-quoted attributes).
  function parse(html) {
    const root = new Node('#fragment'); root.tagName = '#fragment';
    const stack = [root];
    const re = /<!--[\s\S]*?-->|<\/([a-zA-Z0-9-]+)\s*>|<([a-zA-Z0-9-]+)((?:\s+[a-zA-Z_:][\w:.-]*(?:="[^"]*")?)*)\s*(\/?)>|([^<]+)/g;
    let m;
    while ((m = re.exec(html))) {
      const top = stack[stack.length - 1];
      const host = top.tagName === 'TEMPLATE' ? top.content : top;
      if (m[0].startsWith('<!--')) continue;
      if (m[1]) { const t = stack.pop(); assert.equal(t.tagName, m[1].toUpperCase(), 'balanced markup'); continue; }
      if (m[2]) {
        const n = new Node(m[2]);
        const ar = /([a-zA-Z_:][\w:.-]*)(?:="([^"]*)")?/g;
        let a;
        while ((a = ar.exec(m[3]))) n.attrs.set(a[1], (a[2] || '').replace(/&amp;/g, '&'));
        if (n.tagName === 'TEMPLATE') { n.content = new Node('#fragment'); n.content.tagName = '#fragment'; }
        host.appendChild(n);
        if (!VOID.has(m[2].toLowerCase()) && !m[4]) stack.push(n);
        continue;
      }
      const t = new Node(); t.data = m[5].replace(/&amp;/g, '&'); host.appendChild(t);
    }
    assert.equal(stack.length, 1, 'all elements closed');
    return root;
  }
  const document = new Node('#document');
  document.documentElement = new Node('html');
  document.documentElement.setAttribute('data-motion', reduce ? 'still' : motion);
  document.body = new Node('body');
  document.documentElement.appendChild(document.body);
  document.hidden = false;
  let intro = null;
  if (overlay) {
    intro = new Node('div');
    intro.setAttribute('id', 'introOverlay');
    intro.setAttribute('class', overlay);
    document.body.appendChild(intro);
  }
  const frag = parse(MARKUP);
  document.body.appendChild(frag);
  document.getElementById = id => document.documentElement.querySelectorAll('[id=' + id + ']')[0] || null;
  document.createElementNS = (ns, tag) => new Node(tag);
  document.createElement = tag => new Node(tag);
  const mqListeners = [];
  const mq = { matches: reduce, addEventListener(t, fn) { mqListeners.push(fn); } };
  const observers = { io: [], ro: [], mo: [] };
  class IO {
    constructor(cb, opts) { this.cb = cb; this.opts = opts; this.targets = new Set(); observers.io.push(this); }
    // A browser reports the target's state once on observe: the stage's actual ratio (0 while far below the fold).
    observe(t) { this.targets.add(t); this.cb([{ target: t, intersectionRatio: ratio, isIntersecting: ratio > 0 }]); }
    unobserve(t) { this.targets.delete(t); }
    disconnect() { this.targets.clear(); }
    fire(r) { for (const t of [...this.targets]) this.cb([{ target: t, intersectionRatio: r, isIntersecting: r > 0 }]); }
  }
  class RO { constructor(cb) { this.cb = cb; observers.ro.push(this); } observe(t) { this.t = t; } }
  class MO { constructor(cb) { this.cb = cb; observers.mo.push(this); } observe(t, o) { this.t = t; this.o = o; } }
  const window = new Node('#window');
  const store = Object.assign({}, storage === 'throw' ? {} : storage);
  const navigator = { userActivation };
  if (vibrate === 'throw') navigator.vibrate = () => { throw new Error('vibrate blocked'); };
  else if (vibrate) navigator.vibrate = ms => { vib.push([now, ms]); return true; };
  Object.assign(window, {
    matchMedia: q => { assert.equal(q, '(prefers-reduced-motion: reduce)'); return mq; },
    IntersectionObserver: IO, ResizeObserver: RO, MutationObserver: MO, innerHeight: 1000, navigator,
    requestAnimationFrame() { counters.raf++; return 0; }
  });
  if (storage === 'throw') Object.defineProperty(window, 'localStorage', { get() { throw new Error('storage denied'); } });
  else window.localStorage = { getItem: k => (k in store ? store[k] : null) };
  const context = vm.createContext({ document, window, Math, String, Number, Array, Object, JSON, IntersectionObserver: IO, ResizeObserver: RO, MutationObserver: MO,
    setTimeout: (fn, ms) => { const id = ++serial; timers.set(id, { fn, at: now + (ms || 0) }); return id; },
    clearTimeout: id => timers.delete(id),
    setInterval: () => { counters.interval++; return 0; }, clearInterval() {},
    requestAnimationFrame: () => { counters.raf++; return 0; } });
  vm.runInContext(script, context, { filename: fragPath });
  const $ = id => document.getElementById(id);
  const R = $('councilRoute'), cap = $('crCap');
  const announcements = [];
  // Record what a screen reader would be offered: caption text changes while the region is polite.
  const desc = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
  Object.defineProperty(cap, 'textContent', { get() { return desc.get.call(this); },
    set(v) { desc.set.call(this, v); if (this.getAttribute('aria-live') === 'polite') announcements.push([now, v]); } });
  const mutate = (target, attributeName) => { for (const o of observers.mo) if (o.t === target) o.cb([{ attributeName }]); };
  const h = {
    R, cap, anims, timers, counters, observers, announcements, document, window, $, vib, audios, store, userActivation,
    tick, now: () => now,
    live: () => anims.filter(a => a.playState !== 'idle'),
    running: () => anims.filter(a => a.playState === 'running'),
    beat: () => R.getAttribute('data-b'), p: () => R.getAttribute('data-p'),
    caption: () => cap.textContent, playHidden: () => $('crPlay').hidden,
    play: () => $('crPlay').click(), next: () => $('crNext').click(), prev: () => $('crPrev').click(), cc: () => $('crCc').click(),
    key: (k, mods = {}) => { userActivation.hasBeenActive = true; return $('crCtl').dispatch('keydown', Object.assign({ key: k, altKey: false, ctrlKey: false, metaKey: false, shiftKey: false }, mods)); },
    setMotion(m) {
      document.documentElement.setAttribute('data-motion', m);
      mutate(document.documentElement, 'data-motion');
      window.dispatch('zotheos:effectschange');
    },
    setReduce(v) { mq.matches = v; for (const fn of mqListeners) fn({ matches: v }); },
    hide(v) { document.hidden = v; document.dispatch('visibilitychange'); },
    inView(r) { for (const o of observers.io) o.fire(r); },
    resize(wd) { width = wd; for (const o of observers.ro) o.cb([{ target: R }]); },
    seek(t) { R.dispatch('cr:seek', { detail: t }); },
    intro(cls) { intro.setAttribute('class', cls); mutate(intro, 'class'); },
    transcriptOpen: () => !!$('crText').open,
    captions: () => $('crList').children.map(li => li.textContent.replace(/\s+/g, ' ').trim())
  };
  return h;
}

const REST = 'Press Play to follow the route, or step through it at your own pace.';
const REST_STILL = 'Step through the route at your own pace.';
const STARTS = [0, 6, 11, 17.5, 23.5, 30.5, 35];
const withSound = s => s.replace("const SOUND_FILE = '';", "const SOUND_FILE = '/static/route_test.mp3';");

test('loads at rest out of view: stage revealed, rest caption, nothing animates or waits', () => {
  const h = harness();
  assert.equal(h.R.hidden, false);
  assert.equal(h.beat(), '0');
  assert.equal(h.caption(), REST);
  assert.equal(h.cap.getAttribute('aria-live'), 'off', 'the rest caption is not announced');
  assert.equal(h.p(), 'play');
  assert.equal(h.playHidden(), false);
  assert.equal(h.anims.length, 0, 'no animation exists before the stage is in view or a press');
  assert.equal(h.timers.size, 0, 'no timer before the stage is in view or a press');
  h.tick(120000);
  assert.equal(h.anims.length, 0);
  assert.equal(h.beat(), '0');
  assert.equal(h.counters.raf, 0);
  assert.equal(h.counters.interval, 0);
  assert.equal(h.announcements.length, 0);
  assert.deepEqual(Array.from(h.observers.io[0].opts.threshold), [0, 0.25, 0.6], 'the observer reports the 25% and 60% lines');
});

for (const motion of ['living', 'calm']) {
  test('autoplays like a video preview once 60% of the stage is in view (' + motion + '), without scrolling', () => {
    const h = harness({ motion });
    h.inView(0.3);
    h.inView(0.59);
    assert.equal(h.anims.length, 0, 'under 60% in view nothing starts');
    h.inView(0.6);
    assert.equal(h.p(), 'pause');
    assert.equal(h.beat(), '1');
    assert(h.running().length > 0);
    assert.equal(h.counters.scrolls, 0, 'autoplay never moves the page');
    h.tick(6100);
    assert.equal(h.beat(), '2');
  });
}

test('a stage already in view at load starts on its own in Living', () => {
  const h = harness({ ratio: 1 });
  assert.equal(h.p(), 'pause');
  assert(h.running().length > 0);
});

for (const [name, opts] of [['Still chosen', { motion: 'still' }], ['OS reduced motion over Living', { motion: 'living', reduce: true }]]) {
  test('never autoplays in Still (' + name + '): stepper only, transcript open, 0 animations', () => {
    const h = harness(Object.assign({ ratio: 1 }, opts));
    h.inView(0.2); h.inView(1); h.hide(true); h.hide(false);
    h.tick(60000);
    assert.equal(h.anims.length, 0, 'Still creates no animation at all');
    assert.equal(h.timers.size, 0);
    assert.equal(h.playHidden(), true);
    assert.equal(h.transcriptOpen(), true);
    assert.equal(h.caption(), REST_STILL);
    h.play();
    h.seek(20);
    h.next(); h.next();
    assert.equal(h.beat(), '2');
    h.inView(1);
    h.tick(50000);
    assert.equal(h.anims.length, 0);
    assert.equal(h.timers.size, 0);
  });
}

test('the run: 7 beats in order on the timing rule, 42.0 s, then rests with Replay and never restarts on its own', () => {
  const h = harness();
  h.inView(1);
  assert.equal(h.p(), 'pause');
  const seen = [];
  for (let t = 0; t <= 44000; t += 250) {
    const b = h.beat();
    if (!seen.length || seen[seen.length - 1][0] !== b) seen.push([b, h.now()]);
    h.tick(250);
  }
  const beats = seen.map(s => s[0]);
  assert.deepEqual(beats, ['1', '2', '3', '4', '5', '6', '7', '0']);
  const caps = h.captions();
  assert.deepEqual(h.announcements.map(a => a[1]), caps, '7 announcements per run, in caption order');
  STARTS.forEach((s, i) => assert(Math.abs(seen[i][1] / 1000 - s) <= 0.3, 'beat ' + (i + 1) + ' starts near ' + s + ' s, saw ' + seen[i][1]));
  assert(Math.abs(seen[7][1] / 1000 - 42) <= 0.3, 'run ends near 42.0 s, saw ' + seen[7][1]);
  assert.equal(h.p(), 'replay');
  assert.equal(h.caption(), REST);
  assert.equal(h.live().length, 0, 'every animation is cancelled at the end');
  assert.equal(h.timers.size, 0, 'no timer at rest');
  h.inView(0); h.inView(1); h.hide(true); h.hide(false);
  assert.equal(h.p(), 'replay', 'back in view after the end: it stays at rest');
  assert.equal(h.live().length, 0);
  h.tick(60000);
  assert.equal(h.beat(), '0', 'never loops and never restarts after the end');
  assert.equal(h.announcements.length, 7, 'no second run');
  assert.equal(h.live().length, 0);
  assert.equal(h.counters.raf, 0);
  assert.equal(h.counters.interval, 0);
  h.play();
  assert.equal(h.p(), 'pause', 'Replay plays again');
  assert.equal(h.beat(), '1');
});

test('every animation spans the whole run on one clock and touches only stroke-dashoffset, opacity or transform', () => {
  const h = harness();
  h.play();
  const durs = new Set(h.anims.map(a => a.duration));
  assert.deepEqual([...durs], [42000]);
  for (const a of h.anims) {
    for (const f of a.effect.frames) {
      const props = Object.keys(f).filter(k => k !== 'offset' && k !== 'easing');
      assert(props.length === 1 && ['strokeDashoffset', 'opacity', 'transform'].includes(props[0]), JSON.stringify(f));
      assert(f.offset >= 0 && f.offset <= 1);
    }
    for (let i = 1; i < a.effect.frames.length; i++) assert(a.effect.frames[i].offset >= a.effect.frames[i - 1].offset);
  }
});

test('under 25% in view pauses; back at 60% it resumes where it stopped', () => {
  const h = harness();
  h.inView(1);
  h.tick(8000);
  assert.equal(h.beat(), '2');
  h.inView(0.3);
  assert.equal(h.p(), 'pause', '30% in view keeps playing');
  h.inView(0.2);
  assert.equal(h.p(), 'play');
  assert.equal(h.running().length, 0);
  assert.equal(h.timers.size, 0);
  const t = h.anims[0].currentTime;
  h.tick(10000);
  h.inView(0.5);
  assert.equal(h.running().length, 0, 'not yet: under 60%');
  assert.equal(h.anims[0].currentTime, t);
  h.inView(0.6);
  assert.equal(h.p(), 'pause', 'resumes on its own');
  assert.equal(h.anims[0].currentTime, t, 'from the same moment');
  h.tick(3500);
  assert.equal(h.beat(), '3');
  assert.equal(h.counters.scrolls, 0);
});

test('a hidden tab pauses; the tab shown again resumes when the stage is in view', () => {
  const h = harness();
  h.inView(1);
  h.tick(8000);
  h.hide(true);
  assert.equal(h.p(), 'play');
  assert.equal(h.running().length, 0);
  assert.equal(h.timers.size, 0);
  h.inView(0.9);
  assert.equal(h.running().length, 0, 'no start while the tab is hidden');
  const t = h.anims[0].currentTime;
  h.hide(false);
  assert.equal(h.p(), 'pause');
  assert.equal(h.anims[0].currentTime, t);
  h.inView(0.1);
  h.hide(true); h.hide(false);
  assert.equal(h.p(), 'play', 'out of view: the tab coming back does not start it');
});

test('an explicit Pause is respected until Play: no resume on view, scroll or tab return', () => {
  const h = harness();
  h.inView(1);
  h.tick(7000);
  h.play();
  assert.equal(h.p(), 'play');
  const t = h.anims[0].currentTime;
  h.inView(0); h.inView(0.7); h.inView(1);
  h.hide(true); h.hide(false);
  h.setMotion('calm');
  h.resize(1300);
  h.tick(30000);
  assert.equal(h.running().length, 0, 'held');
  assert.equal(h.anims[0].currentTime, t);
  assert.equal(h.beat(), '2');
  h.play();
  assert.equal(h.p(), 'pause', 'Play releases the hold');
  h.tick(4500);
  assert.equal(h.beat(), '3', 'and resumes from where it paused');
  h.inView(0.1);
  h.inView(1);
  assert.equal(h.p(), 'pause', 'after Play the view rules apply again');
});

test('stepping is an explicit choice too: Previous or Next pause and hold until Play', () => {
  const h = harness();
  h.inView(1);
  h.tick(12000);
  assert.equal(h.beat(), '3');
  h.next();
  assert.equal(h.beat(), '4');
  assert.equal(h.live().length, 0);
  h.inView(0); h.inView(1);
  assert.equal(h.live().length, 0, 'no autoplay after a step');
  h.play();
  assert.equal(h.beat(), '4');
  assert(Math.abs(h.live()[0].currentTime - 17500) < 1, 'Play from a stepped beat starts at the start of that beat');
});

test('step order: Next walks 1 to 7 and stops, Previous returns to rest, arrows step only inside the group', () => {
  const h = harness();
  const caps = h.captions();
  assert.equal(h.$('crPrev').getAttribute('aria-disabled'), 'true');
  for (let k = 1; k <= 7; k++) {
    h.next();
    assert.equal(h.beat(), String(k));
    assert.equal(h.caption(), caps[k - 1]);
    assert.equal(h.live().length, 0, 'stepping creates no animation');
    assert.equal(h.timers.size, 0, 'stepping arms no timer');
  }
  assert.equal(h.$('crNext').getAttribute('aria-disabled'), 'true');
  h.next();
  assert.equal(h.beat(), '7');
  h.key('ArrowLeft');
  assert.equal(h.beat(), '6');
  h.key('ArrowRight');
  assert.equal(h.beat(), '7');
  h.key('ArrowUp');
  assert.equal(h.beat(), '7', 'only Left and Right step');
  for (let k = 6; k >= 0; k--) { h.prev(); assert.equal(h.beat(), String(k)); }
  h.prev();
  assert.equal(h.beat(), '0');
  assert.equal(h.caption(), REST);
  assert.equal(h.announcements.length, 7 + 2 + 6, 'one announcement per visitor step, none for the rest caption');
});

test('switching Motion to Still mid-run cancels every animation and holds the beat; Calm in view plays on', () => {
  const h = harness();
  h.inView(1);
  h.tick(19000);
  assert.equal(h.beat(), '4');
  h.setMotion('still');
  assert.equal(h.live().length, 0);
  assert.equal(h.timers.size, 0);
  assert.equal(h.beat(), '4');
  assert.equal(h.playHidden(), true);
  assert.equal(h.transcriptOpen(), false, 'the transcript opens by default only at load, never on a live switch');
  h.inView(0.2); h.inView(1);
  assert.equal(h.live().length, 0, 'nothing starts in Still');
  h.setMotion('calm');
  assert.equal(h.playHidden(), false, 'Calm allows Play again');
  assert.equal(h.p(), 'pause', 'in view and not held: it plays on in Calm');
  assert(Math.abs(h.live()[0].currentTime - 17500) < 1, 'from the start of the held beat');
  h.inView(0);
  h.setMotion('still');
  h.setMotion('living');
  assert.equal(h.live().length, 0, 'out of view: nothing starts on the switch back');
});

test('reduced motion switched on mid-run also stops everything and blocks autoplay', () => {
  const h = harness();
  h.inView(1);
  h.tick(3000);
  h.setReduce(true);
  assert.equal(h.live().length, 0);
  assert.equal(h.playHidden(), true);
  assert.equal(h.transcriptOpen(), false, 'an OS switch mid-visit does not open the transcript (no layout shift without input)');
  h.inView(0); h.inView(1);
  h.tick(20000);
  assert.equal(h.live().length, 0);
});

test('a layout change mid-run restarts the current beat in view, and stays at rest out of view', () => {
  const h = harness();
  h.inView(1);
  h.tick(12000);
  h.resize(300);
  assert.equal(h.$('crStage').className, 'cr-stage p');
  assert.equal(h.beat(), '3');
  assert.equal(h.p(), 'pause');
  assert(Math.abs(h.live()[0].currentTime - 11000) < 1);
  h.inView(0.1);
  h.resize(1300);
  assert.equal(h.live().length, 0);
  assert.equal(h.beat(), '3');
});

test('Play brings the whole controls-to-caption block into view with one nearest scroll; nothing else scrolls', () => {
  const h = harness();
  const run = h.$('crRun');
  for (const id of ['crCtl', 'crPlay', 'crCc', 'crStage', 'crCb', 'crCap']) assert(run.contains(h.$(id)), id + ' is inside the scroll block');
  assert(!run.contains(h.$('crText')), 'the transcript stays outside the scroll block');
  h.next(); h.prev(); h.cc(); h.cc();
  assert.equal(h.counters.scrolls, 0, 'stepping and CC never scroll');
  h.play();
  assert.deepEqual(h.counters.scrollLog, [['crRun', JSON.stringify({ block: 'nearest' })]]);
  h.play();
  assert.equal(h.counters.scrolls, 1, 'Pause does not scroll');
  h.play();
  assert.equal(h.counters.scrolls, 2, 'each press of Play asks once');
  h.seek(12);
  h.inView(0.1); h.inView(1);
  assert.equal(h.counters.scrolls, 2, 'a seek or an autoplay never scrolls');
});

test('CC: on by default, toggles the caption line with aria-pressed; captions keep following and the transcript stays', () => {
  const h = harness();
  const b = h.$('crCc');
  assert.equal(b.getAttribute('aria-pressed'), 'true');
  assert.equal(b.hidden, false);
  assert.equal(h.R.getAttribute('data-cc'), null, 'captions shown (no off flag)');
  h.cc();
  assert.equal(b.getAttribute('aria-pressed'), 'false');
  assert.equal(h.R.getAttribute('data-cc'), 'off');
  h.inView(1);
  h.tick(6500);
  assert.equal(h.beat(), '2');
  assert.equal(h.caption(), h.captions()[1], 'the caption line keeps the current beat while hidden');
  assert.equal(h.$('crText').hidden, false, 'the transcript stays available');
  assert.equal(h.$('crList').children.length, 7);
  h.cc();
  assert.equal(b.getAttribute('aria-pressed'), 'true');
  assert.equal(h.R.getAttribute('data-cc'), 'on');
  assert.equal(h.p(), 'pause', 'CC never pauses');
  const s = harness({ motion: 'still' });
  assert.equal(s.$('crCc').hidden, false, 'CC also serves the Still stepper');
  s.cc();
  assert.equal(s.$('crCc').getAttribute('aria-pressed'), 'false');
});

test('Audio: the slot stays hidden and loads nothing while no sound file is configured', () => {
  assert.match(SCRIPT, /const SOUND_FILE = '';/);
  for (const opts of [{}, { motion: 'calm' }, { motion: 'still' }]) {
    const h = harness(opts);
    const s = h.$('crSnd');
    assert.equal(s.hidden, true);
    h.inView(1); h.tick(9000); h.next(); h.play(); h.tick(3000); h.setMotion('living'); h.cc();
    s.click();
    assert.equal(s.hidden, true, 'still hidden after play, steps, motion and CC');
    assert.equal(s.getAttribute('aria-pressed'), 'false');
    assert.equal(h.audios.length, 0, 'no audio element is ever created');
  }
});

test('Audio: once configured, the button shows outside Still and the owner\'s sound follows the run', () => {
  const h = harness({ script: withSound(SCRIPT) });
  const s = h.$('crSnd');
  assert.equal(s.hidden, false);
  assert.equal(h.audios.length, 0, 'nothing loads before a press');
  h.inView(1);
  h.tick(7000);
  s.click();
  assert.equal(s.getAttribute('aria-pressed'), 'true');
  assert.equal(h.audios.length, 1);
  const au = h.audios[0];
  assert.equal(au.getAttribute('src') || au.src, '/static/route_test.mp3');
  assert.equal(au.paused, false, 'plays with the run');
  assert(Math.abs(au.currentTime - 7) < 0.31, 'lined up with the run clock');
  h.play();
  assert.equal(au.paused, true, 'Pause pauses the sound');
  h.play();
  assert.equal(au.paused, false);
  s.click();
  assert.equal(au.paused, true, 'Audio off');
  const still = harness({ script: withSound(SCRIPT), motion: 'still' });
  assert.equal(still.$('crSnd').hidden, true, 'no sound control in Still');
});

test('haptics: one 8 to 12 ms pulse per beat change and per Play or Pause, only after the visitor has interacted', () => {
  const h = harness();
  h.inView(1);
  h.tick(13000);
  assert.equal(h.beat(), '3');
  assert.equal(h.vib.length, 0, 'autoplay before any interaction never vibrates');
  h.play();
  assert.equal(h.vib.length, 1, 'Pause pulses once');
  h.play();
  assert.equal(h.vib.length, 2, 'Play pulses once');
  h.tick(5000);
  assert.equal(h.beat(), '4');
  assert.equal(h.vib.length, 3, 'a beat change pulses once');
  h.next();
  assert.equal(h.vib.length, 4, 'a step pulses once');
  h.play();
  assert.equal(h.vib.length, 5, 'Play from a step pulses once (not twice)');
  for (const [, ms] of h.vib) assert(ms >= 8 && ms <= 12, 'pulse length ' + ms);
  const r = harness();
  r.next();
  assert.equal(r.vib.length, 1);
  r.prev();
  r.play();
  assert.equal(r.vib.length, 3, 'Play from rest pulses once, for the move to beat 1');
});

test('haptics are guarded: never in Still, off by preference, silent without support or storage', () => {
  const s = harness({ motion: 'still', activated: true });
  s.next(); s.next(); s.prev(); s.play();
  assert.equal(s.vib.length, 0, 'never in Still');
  const os = harness({ reduce: true, activated: true });
  os.next(); os.next();
  assert.equal(os.vib.length, 0, 'never under OS reduced motion');
  const off = harness({ storage: { zotheos_haptics: 'off' }, activated: true });
  off.inView(1); off.tick(20000); off.play(); off.next();
  assert.equal(off.vib.length, 0, 'localStorage zotheos_haptics = "off" switches them off');
  const on = harness({ storage: { zotheos_haptics: 'on' }, activated: true });
  on.next();
  assert.equal(on.vib.length, 1, 'any other value keeps the default (on)');
  for (const opts of [{ vibrate: false }, { vibrate: 'throw' }, { storage: 'throw' }]) {
    const h = harness(Object.assign({ activated: true }, opts));
    h.inView(1); h.tick(13000); h.play(); h.play(); h.next();
    assert.equal(h.beat(), '4', 'the route works the same: ' + JSON.stringify(opts));
  }
  const noUa = harness();
  delete noUa.window.navigator.userActivation;
  noUa.next(); noUa.play();
  assert.equal(noUa.vib.length, 0, 'without the user-activation signal there is no pulse');
  const t = harness({ storage: 'throw', activated: true });
  t.next();
  assert.equal(t.vib.length, 1, 'storage that throws keeps the default (on)');
});

test('the intro: no autoplay while the intro overlay shows; starts when it is dismissed; a replayed intro pauses', () => {
  const h = harness({ overlay: 'intro-overlay', ratio: 1 });
  h.tick(9000);
  assert.equal(h.anims.length, 0, 'never under the intro');
  h.intro('intro-overlay dismissed');
  assert.equal(h.p(), 'pause');
  h.tick(3000);
  h.intro('intro-overlay');
  assert.equal(h.p(), 'play', 'a replayed intro pauses the route');
  assert.equal(h.running().length, 0);
  h.intro('intro-overlay dismissed');
  assert.equal(h.p(), 'pause', 'and it resumes afterwards');
  const d = harness({ overlay: 'intro-overlay dismissed', ratio: 1 });
  assert.equal(d.p(), 'pause', 'an intro already gone does not block it');
});

test('modified arrow keys pass through to the browser (Alt or Cmd plus arrow is Back or Forward)', () => {
  const h = harness();
  h.next(); h.next();
  for (const mods of [{ altKey: true }, { ctrlKey: true }, { metaKey: true }, { shiftKey: true }]) {
    for (const k of ['ArrowLeft', 'ArrowRight']) {
      const prevented = h.key(k, mods);
      assert.equal(prevented, false, k + ' with ' + Object.keys(mods)[0] + ' is not cancelled');
      assert.equal(h.beat(), '2', k + ' with ' + Object.keys(mods)[0] + ' does not step');
    }
  }
  assert.equal(h.key('ArrowRight'), true, 'a plain arrow is handled');
  assert.equal(h.beat(), '3');
});

test('flags: the confirmed variant restores the disagreements caption and runs 43.5 s', () => {
  const h = harness({ script: SCRIPT.replace('const CONFIRMED = false;', 'const CONFIRMED = true;') });
  assert(h.captions()[5].startsWith('Inspect the sources, disagreements and limits.'));
  h.play();
  assert.equal(h.anims[0].duration, 43500);
});

test('flags: without the tie the synthesis caption keeps one sentence and beat 5 shortens', () => {
  const h = harness({ script: SCRIPT.replace('const TIE = true;', 'const TIE = false;') });
  assert.equal(h.captions()[4], 'One synthesized draft combines the perspectives.');
  assert.equal(h.$('crStage').querySelectorAll('[data-k]').some(n => n.getAttribute('data-k') === 'tie'), false);
  h.play();
  assert.equal(h.anims[0].duration, 38500);
});

test('flags: Play in Still (owner switch) still never autoplays and never vibrates in Still', () => {
  const h = harness({ motion: 'still', ratio: 1, activated: true, script: SCRIPT.replace('const PLAY_IN_STILL = false;', 'const PLAY_IN_STILL = true;') });
  assert.equal(h.playHidden(), false);
  h.inView(1);
  assert.equal(h.anims.length, 0, 'no autoplay in Still');
  h.play();
  assert.equal(h.p(), 'pause', 'a press plays');
  h.tick(13000);
  assert.equal(h.vib.length, 0);
});

test('defaults: fallback beat 6, tie on, glyphs never animate, no Play in Still, no sound file', () => {
  assert.match(SCRIPT, /const CONFIRMED = false;/);
  assert.match(SCRIPT, /const TIE = true;/);
  assert.match(SCRIPT, /const GLYPH_ACTIVE = false;/);
  assert.match(SCRIPT, /const PLAY_IN_STILL = false;/);
  assert.match(SCRIPT, /const SOUND_FILE = '';/);
  const h = harness();
  h.play();
  for (const a of h.anims) assert.notEqual(a.effect.target.tagName, 'USE', 'role glyphs are never animated');
});
