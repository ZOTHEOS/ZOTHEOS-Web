'use strict';
// Exercise the actual loader and UI metadata with a controlled browser/XHR surface.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const segment = source.slice(source.indexOf('var HIST ='), source.indexOf('// the card between levels:'));
const nfile = 'n-' + 'a'.repeat(32) + '.json';
const nfile2 = 'n-' + 'b'.repeat(32) + '.json';
const hfile = 'h-' + 'c'.repeat(32) + '.json';
const hfile2 = 'h-' + 'd'.repeat(32) + '.json';
const date = '2026-10-12';
function fact(id) { return {id, text:'A public sourced fact.', kind:'history', as_of:'1881', source:{url:'https://example.org/source', publisher:'Nation source', title:'History', accessed:'2020-01-01'}, checked:'2020-01-02', state:'ok'}; }
function nation(id) { return {id, name:'Nation ' + id, lands:'Public description', countries:['US'], region:'region-a', facts:[fact('fact-' + id)], also:[]}; }
function quick(rows) { return {updated:date, count:rows.length, nations:rows}; }
function history(rows) { return {updated:date, count:Object.keys(rows).length, nations:rows}; }
function setup() {
  const requests = [];
  class Element {
    constructor(tag='div') { this.tagName=tag; this.children=[]; this.hidden=false; this.attrs={}; this._text=''; this.detached=false; }
    get childNodes() { return this.children; }
    set textContent(v) { this._text=v; this.children=[]; }
    get textContent() { return this._text + this.children.map(x=>x.textContent || '').join(''); }
    appendChild(x) { this.children.push(x); return x; }
    removeChild(x) { this.children.splice(this.children.indexOf(x),1); }
    setAttribute(k,v) { this.attrs[k]=v; }
    set href(v) { this.url=new URL(v,'https://zotheos.org/game/'); }
    get href() { return this.url.href; }
    get protocol() { return this.url.protocol; }
    get host() { return this.url.host; }
    get hostname() { return this.url.hostname; }
  }
  class XHR {
    constructor() { requests.push(this); this.status=0; this.responseText=''; this.responseURL=''; this.aborted=false; }
    open(method,url) { this.method=method; this.url=url; }
    send() { this.sent=true; }
    abort() { this.aborted=true; this.status=0; if(this.onloadend) this.onloadend(); }
    respond(body,status=200) { this.status=status; this.responseText=typeof body==='string'?body:JSON.stringify(body); this.responseURL=this.url; this.onloadend(); }
  }
  const ctx = vm.createContext({document:{createElement:tag=>new Element(tag),createTextNode:t=>({textContent:t})},
    location:{protocol:'https:',host:'zotheos.org'}, XMLHttpRequest:XHR,
    root:{contains:box=>!box.detached}, opts:{nationsUrl:'/game/nations.json',historyUrl:'/game/history.json',nationsPage:'https://zotheos.org/nations'},
    RND:Math.round, FLR:Math.floor, ABS:Math.abs, rng:()=>()=>0.3, hashStr:()=>1,
    p2:n=>String(n).padStart(2,'0'), setTimeout, clearTimeout, localStorage:{getItem:()=>null,setItem:()=>{}},
    TEXT:{updated:'List updated',nations:'nations',natFail:'The nations list could not load.',checked:'Checked',source:'Source',asOf:'As of',stale:'Old check'},
    E:Object.fromEntries(['An','Al','Ac','Ab3','Am','Ap2'].map(k=>[k,new Element()])), console});
  vm.runInContext(segment,ctx);
  vm.runInContext('herald=function(){}; natDay=function(){return 0;}; devNat=0;',ctx);
  const evalIn=s=>vm.runInContext(s,ctx);
  return {ctx, requests, evalIn, box:()=>new Element(), close:()=>{if(ctx.xhr)ctx.xhr.abort();if(ctx.hx)ctx.hx.abort();ctx.xhr=ctx.hx=null;ctx.root=null;},
    reopen:()=>{ctx.root={contains:box=>!box.detached};evalIn('HIST=HM=null;HST=0;hw=[];');}};
}
let passed=0;
function test(name,run) { try {run();console.log('PASS '+name);passed++;} catch(e){console.error('FAIL '+name);throw e;} }

test('legacy cards and full count remain available',()=>{
  const s=setup();s.ctx.natLoad();assert.equal(s.requests.length,1);
  s.requests[0].respond(quick([nation('nation-a'),nation('nation-b')]));
  assert.equal(s.ctx.NAT.length,2);assert.match(s.ctx.E.Am.textContent,/2 nations/);assert.equal(s.ctx.E.Ap2.hidden,false);
});
test('day and visit choose different pools with truthful pool and total text',()=>{
  const s=setup();s.ctx.natV=1;s.ctx.natLoad();
  s.requests[0].respond({updated:date,count:3,shards:[[nfile,2],[nfile2,1]]});
  assert.equal(s.requests[1].url,'https://zotheos.org/game/data/'+nfile2);
  s.requests[1].respond(quick([nation('nation-c')]));
  assert.equal(s.ctx.NAT.length,1);assert.match(s.ctx.E.Am.textContent,/1 in this visit pool \/ 3 published records/);
});
test('all pools are reached over successive visits',()=>{
  for(let v=0;v<2;v++){const s=setup();s.ctx.natV=v;s.ctx.natLoad();s.requests[0].respond({updated:date,count:2,shards:[[nfile,1],[nfile2,1]]});assert.equal(s.requests[1].url,'https://zotheos.org/game/data/'+[nfile,nfile2][v]);}
});
test('external, traversal, encoded and wrong-kind shard names make no second request',()=>{
  for(const name of ['https://evil.example/'+nfile,'../'+nfile,'%2e%2e/'+nfile,'data/'+nfile,'\\'+nfile,nfile+'?x=1',hfile]){
    const s=setup();s.ctx.natLoad();s.requests[0].respond({updated:date,count:1,shards:[[name,1]]});
    assert.equal(s.requests.length,1,name);assert.equal(s.ctx.NATst,3,name);assert.equal(s.ctx.E.Ap2.hidden,false);
  }
});
test('invalid counts and duplicated shard references fail closed',()=>{
  for(const j of [{updated:date,count:2,shards:[[nfile,1]]},{updated:date,count:2,shards:[[nfile,1],[nfile,1]]},{updated:date,count:601,shards:[[nfile,601]]}]){
    const s=setup();s.ctx.natLoad();s.requests[0].respond(j);assert.equal(s.requests.length,1);assert.equal(s.ctx.NATst,3);
  }
});
test('missing pool and nested manifest stop without fallback or recursion',()=>{
  for(const fail of [null,{updated:date,count:1,shards:[[nfile2,1]]}]){
    const s=setup();s.ctx.natLoad();s.requests[0].respond({updated:date,count:1,shards:[[nfile,1]]});
    s.requests[1].respond(fail,fail?200:404);assert.equal(s.requests.length,2);assert.equal(s.ctx.NATst,3);assert.equal(s.ctx.E.Ap2.hidden,false);
  }
});
test('bad IDs, duplicate IDs, wrong versions and declared counts are rejected',()=>{
  for(const j of [quick([nation('../bad')]),quick([nation('nation-a'),nation('nation-a')]),{...quick([nation('nation-a')]),updated:'2020-01-01'},{...quick([nation('nation-a')]),count:2}]){
    const s=setup();s.ctx.natLoad();s.requests[0].respond({updated:date,count:j.nations.length,shards:[[nfile,j.nations.length]]});
    s.requests[1].respond(j);assert.equal(s.ctx.NATst,3);
  }
});
test('timeouts fail finitely and progress aborts oversized transfers',()=>{
  const s=setup();s.ctx.natLoad();const x=s.requests[0];assert.equal(x.timeout,5000);x.onloadend();assert.equal(s.ctx.NATst,3);
  const t=setup();t.ctx.natLoad();t.requests[0].onprogress({loaded:524289});assert.equal(t.requests[0].aborted,true);assert.equal(t.ctx.NATst,3);
});
test('UTF-8 byte limit rejects multibyte content even without progress events',()=>{
  const s=setup();s.ctx.natLoad();s.requests[0].respond(JSON.stringify({padding:'é'.repeat(270000),...quick([nation('nation-a')])}));assert.equal(s.ctx.NATst,3);
});
test('stale completion after close/reopen cannot replace new cards or start old shard',()=>{
  const s=setup();s.ctx.natLoad();const old=s.requests[0];s.close();s.reopen();s.ctx.natLoad();
  s.requests[1].respond(quick([nation('new-nation')]));old.respond({updated:date,count:1,shards:[[nfile,1]]});
  assert.equal(s.requests.length,2);assert.equal(s.ctx.NAT[0].id,'new-nation');
});
test('history loads on expansion, caches manifest and shard, and never resurrects failed content',()=>{
  const s=setup(),a=s.box(),b=s.box();s.ctx.histLoad(a,{id:'nation-a'});assert.equal(s.requests.length,1);
  s.requests[0].respond({updated:date,count:2,shards:[[hfile,1,'nation-a'],[hfile2,1,'nation-z']]});
  assert.equal(s.requests.length,2);assert.equal(s.requests[1].url,'https://zotheos.org/game/data/'+hfile);
  s.requests[1].respond(history({'nation-a':{history:[fact('ha')],context:[]}}));assert.match(a.textContent,/public sourced fact/);
  s.ctx.histLoad(s.box(),{id:'nation-a'});assert.equal(s.requests.length,2);
  s.ctx.histLoad(b,{id:'nation-z'});assert.equal(s.requests.length,3);assert.equal(s.requests[2].url,'https://zotheos.org/game/data/'+hfile2);
  s.requests[2].respond(null,404);assert.match(b.textContent,/History unavailable/);assert.equal(s.ctx.HST,3);
  s.ctx.histLoad(s.box(),{id:'nation-z'});assert.equal(s.requests.length,3);
});
test('missing history after last range is remembered without requests',()=>{
  const s=setup(),a=s.box();s.ctx.histLoad(a,{id:'zz-last'});
  s.requests[0].respond({updated:date,count:1,shards:[[hfile,1,'nation-a']]});
  assert.equal(s.requests.length,1);assert.match(a.textContent,/not yet published/);
  s.ctx.histLoad(s.box(),{id:'zz-last'});assert.equal(s.requests.length,1);
});
test('detached history panels and stale history callbacks do not affect reopened session',()=>{
  const s=setup(),a=s.box();a.detached=true;s.ctx.histLoad(a,{id:'nation-a'});assert.equal(s.requests.length,0);
  const b=s.box();s.ctx.histLoad(b,{id:'nation-a'});const old=s.requests[0];s.close();s.reopen();
  old.respond({updated:date,count:1,shards:[[hfile,1,'nation-a']]});assert.equal(s.requests.length,1);assert.equal(s.ctx.HM,null);
});
test('root data URL validation rejects off-origin and traversal paths before sending',()=>{
  for(const u of ['https://evil.example/nations.json','../nations.json','/game/%2e%2e/nations.json','//evil.example/nations.json','javascript:alert(1)']){
    const s=setup();s.ctx.opts.nationsUrl=u;s.ctx.natLoad();assert.equal(s.requests.length,0);assert.equal(s.ctx.NATst,3);
  }
});
test('numeric bundle query busts legacy roots and leaves child shard paths clean',()=>{
  const s=setup();s.ctx.opts.nationsUrl='/game/nations.json?v=2.4';s.ctx.natLoad();
  assert.equal(s.requests[0].url,'https://zotheos.org/game/nations.json?v=2.4');
  s.requests[0].respond({updated:date,count:1,shards:[[nfile,1]]});
  assert.equal(s.requests[1].url,'https://zotheos.org/game/data/'+nfile);
  s.requests[1].respond(quick([nation('nation-a')]));assert.equal(s.ctx.NAT.length,1);
  const h=setup();h.ctx.opts.historyUrl='/game/history.json?v=2.4';const b=h.box();h.ctx.histLoad(b,{id:'nation-a'});
  assert.equal(h.requests[0].url,'https://zotheos.org/game/history.json?v=2.4');
  h.requests[0].respond({updated:date,count:1,shards:[[hfile,1,'nation-a']]});
  assert.equal(h.requests[1].url,'https://zotheos.org/game/data/'+hfile);
  h.requests[1].respond(history({'nation-a':{history:[fact('ha')],context:[]}}));assert.match(b.textContent,/public sourced fact/);
});
test('arbitrary query strings remain rejected before any network request',()=>{
  for(const suffix of ['?x=1','?v=2.4&x=1','?v=2.4#anchor','?v=2.4?v=2.4','?v=2.4%20','?v=abc']){
    const s=setup();s.ctx.opts.nationsUrl='/game/nations.json'+suffix;s.ctx.natLoad();
    assert.equal(s.requests.length,0,suffix);assert.equal(s.ctx.NATst,3,suffix);
  }
});
console.log(passed+' loader acceptance checks passed');
