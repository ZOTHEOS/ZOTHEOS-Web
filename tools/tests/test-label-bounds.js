'use strict';
// Portable: node tools/tests/test-label-bounds.js [game/index.src.html] [baseline-source]
// Captures the real canvas label backplates; this is layout geometry, not a browser-play claim.
var fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
var file=path.resolve(process.argv[2]||'game/index.src.html'),source=fs.readFileSync(file,'utf8');
function engine(s){var b={window:{},document:{getElementById:function(){return null;}},localStorage:{getItem:function(){return null;},setItem:function(){}},setTimeout:function(f){f();},clearTimeout:function(){}};vm.createContext(b);vm.runInContext(s.slice(s.indexOf('<script>')+8,s.indexOf('</script>', s.indexOf('<script>') + 8)),b);return b.window.ZTH_GAME;}
var api=engine(source),T=api._ev('TEXT'),cases=0;
function overlaps(a,b){return a[0]<b[0]+b[2]&&a[0]+a[2]>b[0]&&a[1]<b[1]+b[3]&&a[1]+a[3]>b[1];}
function measure(a,width,height,dpr,hz,side,edge){
  var g,q,seed=110;
  for(;seed<250;seed++){g=a._sim('echo',seed,0);q=g.rings.filter(function(q){return!q.gr&&!!q.hz===hz;})[0];if(q)break;}
  assert(q,'Missing orientation fixture');a._ev('E_point')(q);g.gq=q;
  g.p.x=q.hz?q.gx+side*2:Math.round(q.gx);g.p.y=q.hz?Math.round(q.gy):q.gy+side*2;a._ev('E_ptile')(g);
  a._ev('(function(w,h,d){W=w;H=h;DPR=d;E_lay(G);TT=G.T;VS=-1;NN=1e9;})')(width,height,dpr);
  var radius=Math.max(12*dpr,.36*g.T),targetY=edge==='bottom'?g.vy+g.vh-radius-22*dpr:edge==='top'?g.vy+radius+22*dpr:g.vy+g.vh/2;
  a._ev('(function(x,y){OX=x;OY=y;LW=2*DPR;})')(width*dpr/2-q.gx*g.T,targetY-q.gy*g.T);
  var c={labels:{},lastBox:null,save:function(){},restore:function(){},beginPath:function(){},moveTo:function(){},lineTo:function(){},arc:function(){},stroke:function(){},fill:function(){},strokeRect:function(){},setLineDash:function(){},
    measureText:function(s){return{width:s.length*parseFloat(this.font)*.6};},fillRect:function(x,y,w,h){this.lastBox=[x,y,w,h];},fillText:function(s){this.labels[s]=this.lastBox.slice();}};
  a._ev('(function(c){ctx=c;})')(c);a._ev('E_ring')(g,q);a._ev('E_guide')(g);
  var route=c.labels[T.routeLabel],pass=c.labels[T.passLabel],ring=c.labels[T.ringLabel];
  assert(route&&pass&&ring,'Labels must all be drawn');
  return{route:route,pass:pass,ring:ring,g:g};
}
[[390,844,2],[320,568,1],[844,390,1],[1600,993,1.25]].forEach(function(size){
  [false,true].forEach(function(hz){[-1,1].forEach(function(side){['middle','top','bottom'].forEach(function(edge){
    var f=measure(api,size[0],size[1],size[2],hz,side,edge);cases++;
    assert(!overlaps(f.route,f.pass),'TO RING intersects PASS BALL: '+[size,hz,side,edge]);
    assert(!overlaps(f.route,f.ring),'TO RING intersects RING: '+[size,hz,side,edge]);
    assert(f.route[0]>=f.g.vx&&f.route[0]+f.route[2]<=f.g.vx+f.g.vw);
    assert(f.route[1]>=f.g.vy&&f.route[1]+f.route[3]<=f.g.vy+f.g.vh);
  });});});
});
console.log('PASS '+cases+' actual canvas label rectangles: phone, landscape, desktop, both ring orientations and viewport edges');
if(process.argv[3]){
  var base=fs.readFileSync(path.resolve(process.argv[3]),'utf8'),old=engine(base),f=measure(old,390,844,2,false,1,'middle');
  assert(overlaps(f.route,f.pass),'Baseline must reproduce the reported phone overlap');
  assert.deepStrictEqual(source.match(/\/\*L\*\/[\s\S]*?\/\*L\*\//g),base.match(/\/\*L\*\/[\s\S]*?\/\*L\*\//g));
  assert.strictEqual(source.match(/<template id="zgAboutCopy">[\s\S]*?<\/template>/)[0],base.match(/<template id="zgAboutCopy">[\s\S]*?<\/template>/)[0]);
  var marker='// ---------- NATIONS OF TODAY ----------';assert.strictEqual(source.slice(source.indexOf(marker)),base.slice(base.indexOf(marker)));
  console.log('PASS baseline phone collision reproduced; physics, hunter, full About and nation loading remain byte-identical');
}
