'use strict';
// Portable, dependency-free acceptance checks for the actual landing-page controller.
// Run: node test_intro_lifecycle.cjs /path/to/ZOTHEOS-Web/index.html
// No browser, media decoding, network, application startup, or file mutation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const htmlPath = path.resolve(process.argv[2] || 'index.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const marker = html.indexOf('/* Intro overlay:');
assert(marker >= 0, 'Intro controller marker must exist');
const start = html.indexOf('(function () {', marker);
const end = html.indexOf('/* Header scroll state', start);
assert(start >= 0 && end > start, 'Intro controller must be extracted intact');
const controller = html.slice(start, end);

function deferred() {
  let handlers = [], state = null;
  function settle(ok) {
    assert.equal(state, null, 'Fake play promise can settle only once');
    state = ok;
    for (const pair of handlers) if (pair[ok ? 0 : 1]) pair[ok ? 0 : 1]();
  }
  return { then(ok, bad) { handlers.push([ok, bad]); },
    resolve() { settle(true); }, reject() { settle(false); } };
}

function harness({ seen = false, sound = 'off', policy = 'allowed', readyState = 1 } = {}) {
  let now = 10000, serial = 0;
  const timers = new Map();
  function schedule(fn, delay, interval) {
    const id = ++serial;
    timers.set(id, { fn, at: now + delay, interval });
    return id;
  }
  function tick(ms) {
    const until = now + ms;
    let steps = 0;
    while (true) {
      const due = [...timers].filter(([, t]) => t.at <= until)
        .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!due) break;
      assert(++steps < 10000, 'Timer loop must stay bounded');
      const [id, timer] = due;
      now = timer.at;
      if (timer.interval) timer.at += timer.interval;
      else timers.delete(id);
      timer.fn();
    }
    now = until;
  }
  class Target {
    constructor(tag = 'DIV') {
      this.tagName = tag;
      this.listeners = new Map();
      this.children = [];
      this.attributes = new Map();
      this.hidden = false;
      this.inert = false;
      this.offsetParent = {};
      const classes = new Set();
      this.classList = {
        add(...v) { v.forEach(x => classes.add(x)); },
        remove(...v) { v.forEach(x => classes.delete(x)); },
        contains(v) { return classes.has(v); },
        toggle(v, force) { const on = force === undefined ? !classes.has(v) : !!force; if (on) classes.add(v); else classes.delete(v); return on; }
      };
      this.style = { setProperty(k, v) { this[k] = v; } };
    }
    addEventListener(name, fn) { if (!this.listeners.has(name)) this.listeners.set(name, new Set()); this.listeners.get(name).add(fn); }
    removeEventListener(name, fn) { this.listeners.get(name)?.delete(fn); }
    dispatch(name, extra = {}) { const e = { target: this, preventDefault() {}, stopPropagation() {}, ...extra }; for (const fn of [...(this.listeners.get(name) || [])]) fn(e); }
    click() { this.dispatch('click'); }
    setAttribute(k, v) { this.attributes.set(k, String(v)); }
    getAttribute(k) { return this.attributes.get(k) ?? null; }
    removeAttribute(k) { this.attributes.delete(k); }
    appendChild(el) { this.children.push(el); el.parentNode = this; return el; }
    contains(el) { return this === el || this.children.some(x => x.contains(el)); }
    querySelector(selector) { return selector.startsWith('source') ? this.children.find(x => x.tagName === 'SOURCE') || null : null; }
    focus() { document.activeElement = this; }
    matches() { return false; }
  }
  const document = new Target();
  document.body = new Target('BODY');
  document.documentElement = new Target('HTML');
  document.activeElement = document.body;
  const ids = Object.fromEntries(['introOverlay', 'introStage', 'skipIntro', 'introSound', 'introAudio', 'introGate', 'gateSound', 'gateQuiet', 'replayIntro', 'apReplayRow', 'appearanceBtn', 'appearancePop'].map(id => [id, new Target()]));
  document.getElementById = id => ids[id] || null;
  document.createElement = tag => new Target(tag.toUpperCase());
  document.body.appendChild(ids.introOverlay);
  document.body.appendChild(ids.appearanceBtn);
  for (const id of ['introStage', 'skipIntro', 'introSound', 'introAudio', 'introGate']) ids.introOverlay.appendChild(ids[id]);
  ids.introGate.appendChild(ids.gateSound);
  ids.introGate.appendChild(ids.gateQuiet);
  ids.introGate.hidden = true;
  const audio = ids.introAudio;
  audio.setAttribute('data-src', '/static/zotheos_intro.mp3');
  audio.readyState = readyState;
  audio.paused = true;
  audio.volume = 1;
  audio.muted = false;
  audio.networkState = 1;
  audio.plays = [];
  audio.pauses = 0;
  audio.seeks = [];
  let position = 0;
  Object.defineProperty(audio, 'currentTime', { get() { return position; }, set(v) { position = v; audio.seeks.push(v); } });
  audio.pause = () => { audio.paused = true; audio.pauses++; };
  audio.play = () => { audio.paused = false; const p = deferred(); audio.plays.push(p); return p; };
  audio.load = () => {};
  const storage = values => ({ getItem(k) { return values[k] ?? null; }, setItem(k, v) { values[k] = String(v); } });
  const window = new Target();
  window.localStorage = storage({ zotheos_intro_sound: sound });
  window.sessionStorage = storage(seen ? { zotheos_intro_seen: '1' } : {});
  window.zMotionAllowed = () => true;
  const mounts = [];
  window.ZTH_INTRO = { mount(stage, options) {
    const handlers = {};
    let began = null;
    stage.classList.add('zi-root');
    const instance = {
      options, destroyed: 0,
      on(name, fn) { (handlers[name] ||= []).push(fn); return this; },
      // Explicitly deliver callbacks even after destruction to exercise controller isolation.
      emit(name) { if (name === 'parts') began = now; for (const fn of handlers[name] || []) fn(); },
      elapsed() { return began === null ? 0 : now - began; },
      destroy() { this.destroyed++; stage.classList.remove('zi-root', 'zi-done', 'zi-release'); }
    };
    mounts.push(instance);
    return instance;
  } };
  const navigator = { getAutoplayPolicy() { return policy; }, userActivation: { hasBeenActive: false } };
  const context = vm.createContext({ document, window, navigator,
    Date: class extends Date { static now() { return now; } },
    setTimeout: (fn, ms) => schedule(fn, ms || 0, 0), clearTimeout: id => timers.delete(id),
    setInterval: (fn, ms) => schedule(fn, ms, ms), clearInterval: id => timers.delete(id) });
  vm.runInContext(controller, context, { filename: htmlPath });
  return { ids, audio, mounts, tick, setPolicy(v) { policy = v; },
    dismissed() { return ids.introOverlay.classList.contains('dismissed'); },
    gating() { return ids.introOverlay.classList.contains('intro-gating'); },
    skip() { ids.skipIntro.click(); }, replay() { ids.replayIntro.click(); },
    soundOn() { return ids.introSound.getAttribute('aria-pressed') === 'true'; } };
}

test('full intro holds 8400 ms from the first frame after delayed images', () => {
  const h = harness();
  h.tick(4000);
  assert.equal(h.dismissed(), false);
  h.mounts[0].emit('parts');
  assert.equal(h.ids.introOverlay.style['--intro-ms'], '8400ms');
  h.tick(4650); h.mounts[0].emit('done');
  h.tick(3749);
  assert.equal(h.dismissed(), false, 'assembly completion must not shorten the score');
  h.tick(1);
  assert.equal(h.dismissed(), true);
});

test('return intro is silent and holds 950 ms from its delayed first frame', () => {
  const h = harness({ seen: true, sound: 'on' });
  assert.equal(h.mounts[0].options.quick, true);
  h.tick(1000); h.mounts[0].emit('parts');
  h.tick(949); assert.equal(h.dismissed(), false);
  h.tick(1); assert.equal(h.dismissed(), true);
  assert.equal(h.audio.plays.length, 0);
  assert.equal(h.audio.children.length, 0, 'short return must not request the MP3');
});

test('missing image callbacks have a bounded full and quick escape', () => {
  const full = harness();
  full.tick(13399); assert.equal(full.dismissed(), false);
  full.tick(1); assert.equal(full.dismissed(), true);
  const quick = harness({ seen: true });
  quick.tick(2499); assert.equal(quick.dismissed(), false);
  quick.tick(1); assert.equal(quick.dismissed(), true);
});

test('dismissed run permission timeout and completion cannot alter a replay', () => {
  const h = harness({ sound: 'on', policy: '' });
  const probe = h.audio.plays[0];
  h.skip(); h.tick(700); h.setPolicy('allowed'); h.replay();
  h.mounts[0].emit('parts');
  const pauses = h.audio.pauses;
  const seeks = h.audio.seeks.length;
  probe.resolve();
  h.tick(800); // the first permission probe timeout would fire here
  assert.equal(h.mounts.length, 1);
  assert.equal(h.gating(), false);
  assert.equal(h.audio.pauses, pauses);
  assert.equal(h.audio.seeks.length, seeks);
  assert.equal(h.soundOn(), true);
});

test('late image callback from the dismissed run cannot reset replay timing', () => {
  const h = harness();
  const old = h.mounts[0];
  h.skip(); h.tick(200); h.replay(); h.mounts[1].emit('parts');
  h.tick(500); old.emit('parts');
  h.tick(7899); assert.equal(h.dismissed(), false);
  h.tick(1); assert.equal(h.dismissed(), true);
});

test('late play rejection cannot mute the replay sound control', () => {
  const h = harness({ sound: 'on' });
  h.mounts[0].emit('parts'); const old = h.audio.plays[0];
  h.skip(); h.tick(700); h.replay(); h.mounts[1].emit('parts');
  old.reject();
  assert.equal(h.soundOn(), true);
});

test('late play success cannot seek audio belonging to a replay', () => {
  const h = harness({ sound: 'on' });
  h.mounts[0].emit('parts'); const old = h.audio.plays[0];
  h.skip(); h.tick(700); h.replay(); h.mounts[1].emit('parts');
  const seeks = h.audio.seeks.length;
  old.resolve(); h.tick(250);
  assert.equal(h.audio.seeks.length, seeks);
  assert.equal(h.soundOn(), true);
});

test('late explicit-sound gate completion cannot rewind or remount a replay', () => {
  const h = harness({ sound: 'on', policy: 'disallowed' });
  assert.equal(h.gating(), true);
  h.ids.gateSound.click(); const old = h.audio.plays[0];
  h.skip(); h.tick(700); h.setPolicy('allowed'); h.replay(); h.mounts[0].emit('parts');
  const pauses = h.audio.pauses;
  const seeks = h.audio.seeks.length;
  old.resolve();
  assert.equal(h.mounts.length, 1, 'the new replay must not be replaced');
  assert.equal(h.audio.pauses, pauses, 'old choice must not pause current sound');
  assert.equal(h.audio.seeks.length, seeks, 'old choice must not rewind current sound');
});

test('delayed old-instance cleanup must not remove the replay stage classes', () => {
  const h = harness();
  h.mounts[0].emit('parts'); h.skip(); h.tick(200); h.replay(); h.mounts[1].emit('parts');
  assert.equal(h.mounts[0].destroyed, 1, 'replay replaces the previous instance');
  h.tick(1000);
  assert.equal(h.mounts[0].destroyed, 1, 'old instance must not be destroyed twice');
  assert.equal(h.ids.introStage.classList.contains('zi-root'), true);
});
