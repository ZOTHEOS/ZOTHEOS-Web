'use strict';
// Headless acceptance of the real engine; visual and pointer tests remain for the browser.
// Usage from the repository: node tools/tests/echo-acceptance.js [game/index.src.html]
// No packages or browser installation required. Use readable source with development hooks.
var fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
var sourcePath = path.resolve(process.argv[2] || path.join(process.cwd(), 'game/index.src.html'));
var source = fs.readFileSync(sourcePath, 'utf8');
assert(source.indexOf('<script>') >= 0 && source.indexOf('</script>') > source.indexOf('<script>'), 'Expected the readable standalone game source');
var js = source.slice(source.indexOf('<script>') + 8, source.indexOf('</script>'));
var sandbox = { window: {}, document: { getElementById: function () { return null; } },
  localStorage: { getItem: function () { return null; }, setItem: function () {} },
  setTimeout: function (f) { f(); return 0; }, clearTimeout: function () {}, console: console };
vm.createContext(sandbox); vm.runInContext(js, sandbox, { filename: sourcePath });
assert(sandbox.window.ZTH_GAME && typeof sandbox.window.ZTH_GAME._ev === 'function', 'Use index.src.html with development hooks, not the production build');
var api = sandbox.window.ZTH_GAME, T = api._ev('TEXT'), count = 0;
console.log('Source: ' + sourcePath);
function test(name, f) { f(); count++; console.log('PASS ' + name); }
function close(a, b) { assert(Math.abs(a - b) < 1e-8, String(a) + ' != ' + String(b)); }
function fresh(L) { return api._sim('echo', 123456, L || 0); }
function ui() { return api._ev("E = {Lv:{},Sc:{},Tm:{},Obj:{},Ball:{},cap:{style:{}},capS:{},live:{}}; E"); }
function ringPosition(g) {
  var q = g.rings.filter(function (r) { return !r.gr; })[0], c = q.off + .35 + q.w / 2;
  g.b.x = q.hz ? q.a0 - 1.2 : q.lc + q.s * (1.5 - c);
  g.b.y = q.hz ? q.lc + q.s * (1.5 - c) : q.a0 - 1.2;
  g.p.x = g.b.x - (q.hz ? .5 : 0); g.p.y = g.b.y - (q.hz ? 0 : .5);
  g.p.fx = q.hz ? 1 : .12; g.p.fy = q.hz ? .12 : 1;
  g.p.cd = 0; g.b.held = 0; g.f.st = 0;
  return q;
}
test('Visible ring tally excludes Great Rings and tracks finale silence', function () {
  var g = fresh(3), f = api._ev('E_tm'), rings = g.rings.filter(function (q) { return !q.gr; });
  assert(f(g).indexOf('>0/' + rings.length + '</b>') >= 0);
  rings[0].h = 1; assert(f(g).indexOf('>0/') >= 0);
  rings[0].c = 1; assert(f(g).indexOf('>1/') >= 0);
  g.fin = 1; assert(f(g).indexOf(T.silence) >= 0);
  rings[0].sil = 1; assert(f(g).indexOf('>0/') >= 0);
});
test('Persistent ball state refreshes without score changes', function () {
  var g = fresh(), e = ui(), hud = api._ev('hud'); hud();
  assert.strictEqual(e.Obj.innerHTML, T.echoGoal); assert.strictEqual(e.Ball.innerHTML, T.ballReady);
  g.b.held = 1; hud(); assert.strictEqual(e.Ball.innerHTML, T.ballHeld);
  g.b.held = 0; g.b.x = g.p.x + 4; hud(); assert.strictEqual(e.Ball.innerHTML, T.ballFar);
  g.b.x = g.p.x; g.b.y = g.p.y; hud(); assert.strictEqual(e.Ball.innerHTML, T.ballReady);
  g.fin = 1; hud(); assert.strictEqual(e.Obj.innerHTML, T.echoFinal);
});
test('Ring preview and actual strike resolve to the same assisted direction', function () {
  var g = fresh(), q = ringPosition(g), direction = api._ev('E_direction'), strike = api._ev('E_strike');
  var a = Array.from(direction(g, g.p.fx, g.p.fy));
  close(a[0], q.hz ? 1 : 0); close(a[1], q.hz ? 0 : 1);
  api._ev('TT=40;OX=0;OY=0;DPR=1;VS=G.vs;NN=G.n;VIS.fill(G.vs);G.al=new Float64Array(7);inp.ph=0;coarse=false;');
  assert.strictEqual(api._ev('E_aim')(g), 1);
  var px = (g.al[2] - g.al[0]) / 40, py = (g.al[3] - g.al[1]) / 40;
  close(px * a[1] - py * a[0], 0);
  assert(Math.abs(px) + Math.abs(py) > .1);
  strike(g, g.p.fx, g.p.fy); close(g.b.vx / g.strk, a[0]); close(g.b.vy / g.strk, a[1]);
});
test('Mouse preview and actual strike share the Stone Face snap', function () {
  var g = fresh(), q = ringPosition(g), direction = api._ev('E_direction');
  g.f.x = g.b.x + (q.hz ? 1.7 : .25); g.f.y = g.b.y + (q.hz ? .25 : 1.7); g.f.st = 1;
  var a = Array.from(direction(g, g.p.fx, g.p.fy));
  var dx = g.f.x - g.b.x, dy = g.f.y - g.b.y, distance = Math.sqrt(dx * dx + dy * dy);
  close(a[0], dx / distance); close(a[1], dy / distance);
  assert(q.hz ? a[1] > .1 : a[0] > .1, 'Stone Face correction must differ from ring direction');
  api._ev('TT=40;OX=0;OY=0;DPR=1;VS=G.vs;NN=G.n;VIS.fill(G.vs);G.al=new Float64Array(7);inp.ph=1;coarse=false;inp.px=(G.p.x+G.p.fx)*40;inp.py=(G.p.y+G.p.fy)*40;');
  assert.strictEqual(api._ev('E_aim')(g), 1);
  close(((g.al[2] - g.al[0]) / 40) * a[1] - ((g.al[3] - g.al[1]) / 40) * a[0], 0);
  api._ev('E_strike')(g, g.p.fx, g.p.fy); close(g.b.vx / g.strk, a[0]); close(g.b.vy / g.strk, a[1]);
});
test('Space with a visible mouse aim follows the preview instead of a stale facing direction', function () {
  var g = fresh(), q = ringPosition(g), a, step = api._ev('P_step'); api._ev('inp0()');
  g.f.x = g.b.x + (q.hz ? 1.7 : .25); g.f.y = g.b.y + (q.hz ? .25 : 1.7); g.f.st = 1;
  g.T = 40; g.ox = g.oy = 0;
  api._ev('DPR=1;coarse=false;inp.ph=1;inp.sa=0;inp.sb=1;inp.px=(G.f.x+.1)*40;inp.py=(G.f.y+.1)*40;');
  a = Array.from(api._ev('E_direction')(g, g.f.x + .1 - g.p.x, g.f.y + .1 - g.p.y));
  g.p.fx = -g.p.fx; g.p.fy = -g.p.fy; step(g, .001);
  assert(g.b.vx * a[0] + g.b.vy * a[1] > 0); close(g.b.vx * a[1] - g.b.vy * a[0], 0);
});
test('Out-of-reach and held balls cannot preview or be struck', function () {
  var g = fresh(), strike = api._ev('E_strike'), aim = api._ev('E_aim');
  g.b.held = 1; g.b.vx = g.b.vy = 0; strike(g, 1, 0); assert.strictEqual(g.b.vx, 0); assert.strictEqual(aim(g), 0);
  g.b.held = 0; g.b.x = g.p.x + 2; strike(g, 1, 0); assert.strictEqual(g.b.vx, 0); assert.strictEqual(aim(g), 0);
});
test('A fast ball hitting the Stone Face triggers the explained catch', function () {
  var g = fresh(), e = ui(); api._ev('inp0()');
  g.f.st = 1; g.f.pcd = 0; g.b.x = g.f.x - .35; g.b.y = g.f.y; g.b.vx = 5; g.b.vy = 0;
  api._ev('P_step')(g, .001); assert.strictEqual(g.b.held, 1); assert.strictEqual(g.f.st, 6);
  assert.strictEqual(e.capS.textContent, T.ballHeld);
});
test('A two-pass ring explains the first pass and becomes safe on the second', function () {
  var g = fresh(3), q = ringPosition(g), e = ui(), stepPlayer = api._ev('P_step'); api._ev('inp0()');
  var c = q.off + .35 + q.w / 2;
  function cross() {
    g.b.x = q.hz ? q.a0 - .03 : q.lc + q.s * (1.5 - c);
    g.b.y = q.hz ? q.lc + q.s * (1.5 - c) : q.a0 - .03;
    g.b.vx = q.hz ? 8 : 0; g.b.vy = q.hz ? 0 : 8;
    g.p.x = g.b.x - (q.hz ? 1.4 : 0); g.p.y = g.b.y - (q.hz ? 0 : 1.4);
    stepPlayer(g, .012);
  }
  cross(); assert.strictEqual(q.h, 1); assert.strictEqual(q.c, 0); assert.strictEqual(e.capS.textContent, T.half);
  cross(); assert.strictEqual(q.c, 1); assert.strictEqual(api._x().SF[q.z], 1); assert.strictEqual(e.capS.textContent, T.claimed);
});
test('Every catch gives the next action; return releases the ball before recovery', function () {
  var g = fresh(), e = ui(), catchBall = api._ev('E_play'), stepFace = api._ev('F_step');
  catchBall(g, g.f); assert.strictEqual(g.b.held, 1); assert.strictEqual(e.capS.textContent, T.ballHeld);
  e.capS.textContent = ''; catchBall(g, g.f); assert.strictEqual(e.capS.textContent, T.ballHeld);
  var x = g.f.x, y = g.f.y; stepFace(g, .1); close(g.f.x, x); close(g.f.y, y); assert.strictEqual(g.b.held, 1);
  g.f.s = .001; stepFace(g, .01); assert.strictEqual(g.b.held, 0); assert.strictEqual(g.f.st, 7);
  close(Math.sqrt(g.b.vx * g.b.vx + g.b.vy * g.b.vy), 5.5); assert.strictEqual(e.capS.textContent, T.ballBack);
});
test('Echo playfield begins below persistent goal on phone and landscape sizes', function () {
  var g = fresh(), lay = api._ev('E_lay');
  [[320,568],[390,844],[844,390],[1600,993]].forEach(function (size) {
    api._ev('W=' + size[0] + ';H=' + size[1] + ';DPR=1;'); lay(g);
    assert(g.vy >= 128); assert(g.vh > 0); assert(g.vy + g.vh <= size[1]);
  });
});
test('Echo logic remains deterministic and the replay identifier is distinct', function () {
  js.match(/\/\*L\*\/[\s\S]*?\/\*L\*\//g).forEach(function (s) { assert(!/Math\.(?:sin|cos|tan|atan2?|pow|exp|log|random)\b/.test(s)); });
  assert(source.indexOf("row(btn('Rr', T.replay)") >= 0); assert(source.indexOf("result: 'Rr'") >= 0);
  assert(source.indexOf("btn('Rc', T.replay)") < 0); assert.strictEqual(source.match(/btn\('Rr',/g).length, 1);
  var a = fresh(2), initial = [a.p.x,a.p.y,a.f.x,a.f.y,JSON.stringify(a.rooms)];
  var b = fresh(2); assert.deepStrictEqual([b.p.x,b.p.y,b.f.x,b.f.y,JSON.stringify(b.rooms)], initial);
});
test('Keyboard focus trap includes the native help summary', function () {
  var focused = false, prevented = false, first = { offsetParent: {}, focus: function () { focused = true; } };
  var summary = { offsetParent: {}, focus: function () {} }, root = api._ev('root = {}');
  root.querySelectorAll = function (selector) { assert(selector.indexOf('summary') >= 0); return [first, summary]; };
  sandbox.document.activeElement = summary;
  api._ev('trap')({ shiftKey: false, preventDefault: function () { prevented = true; } });
  assert(focused && prevented);
});
console.log(count + ' acceptance checks passed. Browser layout, keyboard and touch interaction still require integration testing.');
