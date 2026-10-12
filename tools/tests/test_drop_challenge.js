/* Headless acceptance checks. Node built-ins only; no network, browser, or source writes.
 * Usage: node tools/tests/test_drop_challenge.js [game/index.src.html]
 * Keep this beside the pytest wrapper in tools/tests so the default path resolves.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const crypto = require('crypto');
const sourcePath = process.argv[2] || path.resolve(__dirname, '../../game/index.src.html');
const sourceBytes = fs.readFileSync(sourcePath);
const html = sourceBytes.toString('utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert(script, 'Readable game source must contain its inline script');
const dt = 1 / 120;
const report = {
  sourceSHA256: crypto.createHash('sha256').update(sourceBytes).digest('hex'),
  layouts: 0,
  spikePlacements: 0,
  guardians: 0,
  variants: [],
  spikeWarningSeconds: [],
  guardianWarningSeconds: [],
  tallerGeometryNormal: [],
  tallerGeometryCalm: []
};

function instance() {
  const stats = { calls: 0, rotations: [] };
  const draw = new Proxy({}, {
    get(target, key) {
      if (key in target) return target[key];
      target[key] = (...args) => {
        stats.calls++;
        args.forEach(value => {
          if (typeof value === 'number') assert(Number.isFinite(value), 'Finite canvas coordinate: ' + key);
        });
        if (key === 'rotate') stats.rotations.push(args[0]);
        if (key === 'createRadialGradient') return { addColorStop() {} };
      };
      return target[key];
    }
  });
  const context = {
    window: { drawCtx: draw },
    document: {
      getElementById: () => null,
      body: { getAttribute: () => null },
      createElement: () => ({ getContext: () => draw })
    },
    setTimeout() {},
    clearTimeout() {}
  };
  vm.createContext(context);
  vm.runInContext(script[1], context, { timeout: 5000 });
  const api = context.window.ZTH_GAME;
  assert(api && api._sim && api._tick && api._ev, 'Use index.src.html with development hooks');
  api._ev('ctx=window.drawCtx;cv={width:480,height:800};W=480;H=800;DPR=1;LW=1;');
  return { api, stats };
}

function sim(api, seed, level, calm = false, assist = false) {
  api._ev('RM=false');
  api._beat(null);
  const g = api._sim('drop', seed, level, { calm, assist });
  Object.keys(api._inp).forEach(key => { api._inp[key] = 0; });
  return g;
}

function snapshot(g) {
  return JSON.stringify({ time: g.hzTime, grace: g.hzGrace, spikes: g.spikes, guardian: g.guard, failure: g.hzFail });
}

function trapCourt(api, calm = false, assist = false) {
  for (let seed = 0; seed < 128; seed++) {
    const g = sim(api, seed, 3, calm, assist);
    if (g.spikes.length) return g;
  }
  assert.fail('No generated spike trap in 128 courts');
}

const { api, stats } = instance();
const kinds = new Set();

// Safety and seeded repeatability across all levels. Small phone and wide desktop
// canvas stubs also reject non-finite drawing coordinates, including cached bands.
for (let seed = 0; seed < 128; seed++) {
  for (let level = 0; level < 5; level++) {
    const g = sim(api, seed, level);
    assert(g.pitch > 72 && g.pitch <= 104, 'Taller but bounded row clearance');
    assert(g.floor - g.last >= 480, 'Taller ring arena');
    for (const h of g.spikes) {
      const ri = Math.round((h.y - 150) / g.pitch);
      const row = g.rows[ri];
      assert(ri >= 2 && ri < g.rows.length - 1 && ri % 4 !== 3, 'Intro and central landing rows stay clear');
      assert(row.segs.some(s => s[1] === h.y && s[3] === h.y && Math.abs((s[0] + s[2]) / 2 - h.x) < 1e-8 && Math.abs(s[2] - s[0]) >= 56), 'Trap fits a horizontal ledge');
      row.gs.forEach(gap => assert(Math.abs(gap - h.x) > ((2.6 - 0.15 * level) * 18) / 2 + 15 + 9, 'Circle-ball clearance at each gap'));
      if (row.mk) assert(Math.abs(row.mk.x - h.x) > 42, 'Marker is not covered by a trap');
      assert(h.tn >= 0.9 && h.on > 0 && h.rest > 0, 'Positive windows and at least 0.9 seconds notice');
      report.spikePlacements++;
    }
    if (g.guard) {
      assert(g.guard.tn >= 0.9, 'Guardian must warn before contact');
      kinds.add(g.guard.id);
      report.guardians++;
    }
    const before = snapshot(g);
    api._ev('cv.width=W=320;cv.height=H=640;coarse=true');
    g.draw();
    assert.strictEqual(snapshot(g), before, 'Phone drawing never advances hazard clocks');
    api._ev('cv.width=W=1280;cv.height=H=800;coarse=false');
    g.draw();
    assert.strictEqual(snapshot(g), before, 'Desktop drawing never advances hazard clocks');
    const repeat = sim(api, seed, level);
    assert.strictEqual(JSON.stringify(repeat.rows), JSON.stringify(g.rows), 'Court layout repeats by seed');
    assert.strictEqual(snapshot(repeat), before, 'Hazards repeat by seed');
    report.layouts++;
  }
}
assert(kinds.size >= 3, 'Multiple original guardian profiles must occur');
assert(report.spikePlacements > 100, 'Spikes must appear in generated play');
report.variants = [...kinds].sort();

// Holding the initial ball and pausing gameplay both freeze the hazard clocks.
let g = sim(api, 2026, 3);
const held = snapshot(g);
api._tick(480);
assert.strictEqual(snapshot(g), held, 'Held-ball safety');
g.b.held = false;
api._ev("scr='pause'");
api._tick(480);
assert.strictEqual(snapshot(g), held, 'Pause safety');
api._ev("scr='play'");

// Actual collision steps: no early damage, one lost attempt, no repeated loss,
// and a fresh protected retry. Calm's longer warning must be measurable.
for (const calm of [false, true]) {
  g = trapCourt(api, calm);
  const h = g.spikes[0];
  g.spikes = [h]; g.guard = null; g.hzGrace = 0;
  g.b.held = false; g.b.x = h.x; g.b.y = h.y - 9; g.b.vx = g.b.vy = 0;
  let steps = 0;
  while (!g.hzFail && steps < 300) {
    api._tick(1); steps++;
    if (steps * dt < h.tn - 1e-8) assert.strictEqual(g.lives, 3, 'No spike injury during warning');
  }
  assert(g.hzFail, 'Remaining on solid spikes must cost an attempt');
  const elapsed = steps * dt;
  assert(elapsed + 1e-8 >= h.tn && elapsed < h.tn + 2 * dt, 'Damage follows full warning');
  report.spikeWarningSeconds.push(elapsed);
  assert.strictEqual(g.lives, 2);
  for (let i = 0; i < 200; i++) g.step(dt);
  assert.strictEqual(g.lives, 2, 'One contact cannot remove several lives');
  api._tick(100);
  assert.strictEqual(g.hzFail, 0);
  assert.strictEqual(g.hzGrace, 1);
  assert(g.b.held);
  assert.strictEqual(h.state, 0);
}
assert(report.spikeWarningSeconds[1] > report.spikeWarningSeconds[0], 'Calm provides more notice');

// A previously active trap disarms outside proximity. Returning requires a new
// full warning, so a dangerous phase cannot await the player unseen offscreen.
g = trapCourt(api);
let h = g.spikes[0];
g.spikes = [h]; g.guard = null; g.hzGrace = 0; g.b.x = h.x; g.b.y = h.y - 60;
for (let i = 0; i < Math.ceil(h.tn / dt) + 2; i++) api._ev('D_hazardStep(G,1/120)');
assert.strictEqual(h.state, 2);
g.b.x = h.x + 180;
api._ev('D_hazardStep(G,1/120)');
assert.strictEqual(h.state, 0); assert.strictEqual(h.t, 0);
g.b.x = h.x;
api._ev('D_hazardStep(G,1/120)');
for (let i = 0; i < Math.floor(0.9 / dt) - 2; i++) api._ev('D_hazardStep(G,1/120)');
assert.strictEqual(h.state, 1, 'Fresh proximity receives a full new warning');

// Concurrent contacts retain the existing Assist behavior and still trigger
// only one failure. Collision queries may not grant footing or deflect a ball.
g = trapCourt(api, false, true);
h = g.spikes[0];
g.spikes = [h, { ...h }]; g.guard = null; g.hzGrace = 0;
g.b.held = false; g.b.x = h.x; g.b.y = h.y - 9;
for (let i = 0; i < 130 && !g.hzFail; i++) api._tick(1);
assert.strictEqual(g.lives, 3); assert.strictEqual(g.clean, 0);
assert(g.hzFail && api._beat());
for (let i = 0; i < 200; i++) g.step(dt);
assert.strictEqual(g.lives, 3);
const ballBefore = JSON.stringify(g.b);
api._ev('D_near(G.b,G.b.x-5,G.b.y,G.b.x+5,G.b.y)');
assert.strictEqual(JSON.stringify(g.b), ballBefore, 'Trap overlap query is not a footing collision');

// Guardian notice precedes contact; the patrol stays central; explicit rest
// windows allow crossings. Safe ornaments outside the body are non-damaging.
for (const calm of [false, true]) {
  g = sim(api, 19, 4, calm); g.spikes = []; g.hzGrace = 0; g.inCourt = true; g.rt = 1000; g.b.held = false;
  const q = g.guard;
  g.b.y = q.y;
  let steps = 0;
  while (!g.hzFail && steps < 300) {
    g.b.x = q.x; g.b.y = q.y; g.b.vx = g.b.vy = 0;
    api._tick(1); steps++;
    assert(q.x >= 138 && q.x <= 222, 'Wall ring approaches remain open');
    if (steps * dt < q.tn - 1e-8) assert.strictEqual(g.lives, 3);
  }
  assert(g.hzFail);
  assert(steps * dt + 1e-8 >= q.tn && steps * dt < q.tn + 2 * dt);
  report.guardianWarningSeconds.push(steps * dt);
  assert.strictEqual(g.lives, 2);
  g.hzFail = 0; g.lives = 3; g.b.x = 90; g.b.y = q.y;
  for (let i = 0; i < Math.ceil(q.on / dt) + 4; i++) api._ev('D_hazardStep(G,1/120)');
  assert.strictEqual(q.state, 3); assert.strictEqual(g.lives, 3);
}
assert(report.guardianWarningSeconds[1] > report.guardianWarningSeconds[0]);

// Nonessential rotation obeys reduced motion without changing the patrol.
g = sim(api, 19, 4); g.guard.angle = 1;
api._ev('MS=1;MX=0;MY=0;RM=true');
stats.rotations.length = 0;
api._ev('D_hazardDraw(G,1,G.floor+100)');
assert.deepStrictEqual(stats.rotations, [0]);
api._ev('RM=false');
stats.rotations.length = 0;
api._ev('D_hazardDraw(G,1,G.floor+100)');
assert.deepStrictEqual(stats.rotations, [1]);

// One physical input sequence gives the same result at different render rates.
const a = instance().api, b = instance().api;
const ga = sim(a, 43210, 4), gb = sim(b, 43210, 4);
for (let i = 0; i < 1400; i++) {
  for (const target of [a, b]) {
    target._inp.l = i % 360 > 180 ? 1 : 0;
    target._inp.r = i % 360 <= 180 ? 1 : 0;
    if (i % 80 === 0) target._inp.sb = 0.12;
    target._tick(1);
  }
  if (i % 3 === 0) ga.draw();
  if (i % 19 === 0) gb.draw();
  assert.strictEqual(snapshot(ga), snapshot(gb));
  assert.strictEqual(JSON.stringify(ga.b), JSON.stringify(gb.b));
}

// Reachability uses real physics and inputs. Traps are disabled only here to
// isolate the geometry question from intentional challenge and bot mistakes.
function descendGeometry(calm) {
  const reached = [0, 0, 0, 0, 0];
  for (let seed = 0; seed < 32; seed++) {
    for (let level = 0; level < 5; level++) {
      const g = sim(api, seed, level, calm), input = api._inp;
      g.spikes = []; g.guard = null;
      let ticks = 0;
      while (ticks < 120 * 80 && !g.inCourt && g.lives > 0) {
        const ball = g.b;
        const row = g.rows.find(r => r.y + 22 > ball.y) || g.rows[g.rows.length - 1];
        const x = row.gs.reduce((a, x) => Math.abs(x - ball.x) < Math.abs(a - ball.x) ? x : a, row.gs[0]);
        const desired = Math.max(-g.vxm, Math.min(g.vxm, (x - ball.x) * 4));
        input.pt = Math.max(-1, Math.min(1, (desired - ball.vx) / 100));
        input.sb = ball.held ? 0.12 : 0;
        api._tick(1); ticks++;
      }
      assert(g.inCourt, 'Taller geometry blocks descent: seed ' + seed + ', level ' + level + ', Calm ' + calm);
      reached[level]++;
    }
  }
  return reached;
}
report.tallerGeometryNormal = descendGeometry(false);
report.tallerGeometryCalm = descendGeometry(true);

// The world grows, but the grounded strike must retain its existing reach.
g = sim(api, 20, 1); g.guard = null; g.spikes = []; g.inCourt = true; g.rt = 1000;
g.b.held = false; g.b.x = 180; g.b.y = g.floor - 9; g.b.vx = g.b.vy = 0;
g.b.ct = 0; g.b.lg = 1; g.b.cd = 0;
api._inp.sb = 0.12;
const origin = g.b.y;
let top = origin;
for (let i = 0; i < 120; i++) { api._tick(1); top = Math.min(top, g.b.y); }
assert(origin - top > 63 && origin - top < 68, 'Grounded strike reach changed');
report.groundedStrikeRise = origin - top;
report.canvasCalls = stats.calls;
report.pass = true;
console.log(JSON.stringify(report));
