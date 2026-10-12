'use strict';
// Run with readable source. Built-in Node modules only, no browser or network.
var fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
var sourcePath = path.resolve(process.argv[2] || path.join(process.cwd(), 'game/index.src.html'));
var source = fs.readFileSync(sourcePath, 'utf8'), passed = 0;
function engine(html) {
  var box = { window: {}, document: { getElementById: function () { return null; } },
    localStorage: { getItem: function () { return null; }, setItem: function () {} },
    setTimeout: function (f) { f(); return 0; }, clearTimeout: function () {} };
  vm.createContext(box); vm.runInContext(html.slice(html.indexOf('<script>') + 8, html.indexOf('</script>')), box);
  return box.window.ZTH_GAME;
}
var api = engine(source), T = api._ev('TEXT');
function test(name, f) { f(); passed++; console.log('PASS ' + name); }
function fresh(L, seed) { return api._sim('echo', seed || 123456, L || 0); }
function near(a, b) { assert(Math.abs(a - b) < 1e-8, a + ' != ' + b); }
function canvas() {
  var ctx = { arcs: [], labels: [], boxes: [],
    beginPath: function () {}, moveTo: function () {}, lineTo: function () {}, stroke: function () {}, fill: function () {},
    save: function () {}, restore: function () {}, setLineDash: function () {}, strokeRect: function () {},
    arc: function (x, y, r) { this.arcs.push([x,y,r]); },
    fillRect: function (x, y, w, h) { this.boxes.push([x,y,w,h]); },
    measureText: function (s) { return { width: s.length * 7 }; }, fillText: function (s, x, y) { this.labels.push([s,x,y]); } };
  var get = api._ev('(function (v) { ctx=v;TT=40;OX=10;OY=20;DPR=1;LW=2;VS=-1;NN=1000000000; })'); get(ctx);
  return ctx;
}
test('The first objective is a reachable side ring and stays selected until claimed', function () {
  var target = api._ev('E_target');
  [123456,543210,20261012,77].forEach(function (seed) {
    for (var L=0; L<5; L++) {
      var g = fresh(L, seed), q = target(g); assert(q && !q.gr && !q.c);
      assert.strictEqual(target(g), q); q.c=1; assert.notStrictEqual(target(g), q);
    }
  });
});
test('Hoop centre exactly matches the real crossing plane and aperture', function () {
  for (var L=0; L<5; L++) {
    var g=fresh(L), point=api._ev('E_point'), along=api._ev('ral'), across=api._ev('rq');
    g.rings.forEach(function (q) {
      q.off=.17; q.ao=.3; point(q); near(along(q,q.gx,q.gy),0); near(across(q,q.gx,q.gy),q.off+.35+q.w/2);
    });
  }
});
test('The active hoop is visible before exploration and has RING and PASS BALL labels', function () {
  var g=fresh(), q=api._ev('E_target')(g), ctx=canvas(); q.sn=0;
  api._ev('E_ring')(g,q);
  assert(ctx.arcs.some(function (a) { return Math.abs(a[0]-(10+q.gx*40))<1e-8 && Math.abs(a[1]-(20+q.gy*40))<1e-8 && a[2]>=12; }));
  assert(ctx.labels.some(function (a) { return a[0]===T.ringLabel; }));
  assert(ctx.labels.some(function (a) { return a[0]===T.passLabel; }));
  q.c=1; ctx.labels=[]; api._ev('E_ring')(g,q); assert(ctx.labels.some(function (a) { return a[0]===T.safeLabel; }));
});
test('The route arrow follows connected floor and avoids ring bodies', function () {
  [123456,543210,20261012,77].forEach(function (seed) {
    for (var L=0; L<5; L++) {
      var g=fresh(L,seed), x=api._x(), ctx=canvas(); g.DS=[4,4];g.D0=[];g.vx=16;g.vy=128;g.vw=360;g.vh=500;api._ev('E_guide')(g);
      assert(g.guideNext>=0, 'No first route step for '+L+'/'+seed);
      assert(ctx.labels.some(function(a){return a[0]===T.routeLabel;}));
      var tile=g.pt, budget=x.EN;
      assert(g.gd[tile]<9999, 'Court approach must be reachable');
      while(g.gd[tile]>0 && budget--) {
        var next=-1, best=g.gd[tile];
        for(var d=1;d<=4;d++) { var n=api._ev('nbr')(tile,d); if(n>=0 && g.gd[n]<best) {best=g.gd[n];next=n;} }
        assert(next>=0 && (x.GR[next]&1) && !x.FB[next]);tile=next;
      }
      assert(budget>0 && g.gd[tile]===0);
    }
  });
});
test('Walking onto a hoop does not count and the objective tells you to pass the ball', function () {
  var g=fresh(), q=api._ev('E_target')(g); canvas();
  g.p.x=q.gx;g.p.y=q.gy;g.b.x=g.p.x+5;g.b.y=g.p.y+5;g.b.vx=g.b.vy=0;
  api._ev('inp0()');api._ev('P_step')(g,.001);api._ev('E_ptile')(g);
  assert.strictEqual(q.c,0);assert.strictEqual(q.h,0);assert.strictEqual(api._ev('E_goal')(g),T.passBall);
});
test('Finale guidance selects an active Great Ring and explains a closed gate', function () {
  var g=fresh(3);g.rings.forEach(function(q){if(!q.gr)q.c=1;});g.fin=1;
  g.rings.forEach(function(q){if(q.gr)q.live=q.pair?1:0;});
  var q=api._ev('E_target')(g);assert(q.gr && q.live && q.pair);q.open=0;assert.strictEqual(api._ev('E_goal')(g),T.ringWait);
  q.open=1;assert.strictEqual(api._ev('E_goal')(g),T.echoFinal);
});
test('Offscreen ring and ball pointers use labeled circular markers', function () {
  var g=fresh(), ctx=canvas();g.ms=8;g.vx=16;g.vy=128;g.vw=360;g.vh=500;
  api._ev('E_mark')(g,100,100,0);assert(ctx.labels.some(function(a){return a[0]===T.ringLabel;}));assert(ctx.arcs.length>=2);
  ctx.labels=[];api._ev('E_mark')(g,100,100,2);assert(ctx.labels.some(function(a){return a[0]===T.ballLabel;}));
});
// Optional baseline provides the content-preservation and game-logic comparison after integration.
if(process.argv[3]) {
  var base=fs.readFileSync(path.resolve(process.argv[3]),'utf8'), old=engine(base);
  test('All About prose, source paragraphs and marked dictionary forms survive in the offline template', function () {
    var expected=old._ev("(function(){var a=TEXT.aboutLines.slice();a.push(TEXT.termsHead);for(var k in TERMS)a.push(up1(plain(TERMS[k][0]))+', '+TERMS[k][1]+'. '+TEXT.source+' '+TERMS[k][2]+'.');return a;})()"),
      template=source.match(/<template id="zgAboutCopy">([\s\S]*?)<\/template>/)[1],
      actual=template.match(/<p\b[^>]*>[\s\S]*?<\/p>/g).map(function(p){return p.replace(/^<p\b[^>]*>|<\/p>$/g,'').replace(/&quot;/g,'"').replace(/&gt;/g,'>').replace(/&lt;/g,'<').replace(/&amp;/g,'&');});
    assert.deepStrictEqual(actual,Array.from(expected));
    var terms=old._ev('TERMS');Object.keys(terms).forEach(function(k){assert(template.indexOf('data-term="'+terms[k][0]+'"')>=0);});
    assert(source.indexOf('Background and word sources are unavailable on this host.')>=0);
  });
  test('Guidance drawing leaves seeded movement, ball physics and hunter behavior unchanged', function () {
    function state(g) {return JSON.stringify({p:g.p,b:g.b,f:g.f,score:g.score,lives:g.lives,n:g.n,rings:g.rings.map(function(q){return[q.c,q.h,q.off,q.open,q.live,q.sil,q.ao];})});}
    function bot(g,i){var n=g.n%480;i.u=n<120?1:0;i.r=n>=120&&n<240?1:0;i.d=n>=240&&n<360?1:0;i.l=n>=360?1:0;i.ph=0;i.sa=0;i.sb=g.n%84===0?1:0;}
    for(var L=0;L<5;L++) {
      var a=old._sim('echo',123456,L,{assist:true}), b=api._sim('echo',123456,L,{assist:true});canvas();b.DS=[4,4];b.D0=[];
      for(var n=0;n<1200;n++) {old._tick(1,bot);api._tick(1,bot);if(n%60===0)api._ev('E_guide')(api._echo());}
      assert.strictEqual(state(api._echo()),state(old._echo()),'Logic differs on level '+L);
    }
  });
}
console.log(passed+' discovery acceptance checks passed. Browser appearance and play-through remain required.');
