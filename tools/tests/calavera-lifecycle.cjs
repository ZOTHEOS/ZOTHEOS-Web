'use strict';
// Independent behavior probe. This simulates the documented DOM/event boundary; it is not browser QA.
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');
const source = process.argv[2];
const code = fs.readFileSync(source, 'utf8');
const checks = [];
function check(name, pass, detail) { checks.push({name, pass: !!pass, detail: detail === undefined ? null : detail}); }
function fixture(options = {}) {
  const observers = [], mutations = [], rafs = new Map(), store = new Map([['zotheos_rain','medium']]);
  let nextRaf = 0, peak = 0, requested = 0, canceled = 0, game = null, external = 0;
  class Target {
    constructor() { this.listeners = new Map(); }
    addEventListener(t, fn, opts) { if (!this.listeners.has(t)) this.listeners.set(t,new Set()); this.listeners.get(t).add(fn); }
    removeEventListener(t, fn) { this.listeners.get(t)?.delete(fn); }
    send(t, props={}) { for (const fn of [...(this.listeners.get(t)||[])]) fn({type:t,target:this,...props}); }
    count(t) { return (this.listeners.get(t)||new Set()).size; }
  }
  function change(target, type, attributeName) {
    for (const o of observers) if (o.target === target && (type === 'childList' ? o.options.childList : o.options.attributes && (!o.options.attributeFilter || o.options.attributeFilter.includes(attributeName)))) mutations.push(o.callback);
  }
  class Element extends Target {
    constructor(tag) {
      super(); this.tagName=tag; this.children=[]; this.attributes=new Map(); this.parentNode=null; this.hidden=false;
      this.style={values:new Map(),setProperty(k,v){this.values.set(k,String(v));},removeProperty(k){this.values.delete(k);},getPropertyValue(k){return this.values.get(k)||'';}};
      const self=this;
      this.classList={
        contains(k){return (self.className||'').split(/\s+/).includes(k);},
        add(k){this.toggle(k,true);},remove(k){this.toggle(k,false);},
        toggle(k,force){let s=new Set((self.className||'').split(/\s+/).filter(Boolean));const on=force===undefined?!s.has(k):!!force;if(on)s.add(k);else s.delete(k);self.className=[...s].join(' ');return on;}
      };
    }
    get className(){return this.attributes.get('class')||'';}
    set className(v){this.setAttribute('class',v);}
    setAttribute(k,v){const old=this.attributes.get(k);this.attributes.set(k,String(v));if(old!==String(v))change(this,'attributes',k);}
    getAttribute(k){return this.attributes.has(k)?this.attributes.get(k):null;}
    removeAttribute(k){if(this.attributes.delete(k))change(this,'attributes',k);}
    appendChild(el){this.children.push(el);el.parentNode=this;change(this,'childList');return el;}
    closest(selector){return selector==='#fxAmount'&&this.id==='fxAmount'?this:null;}
  }
  const root=new Element('html'), body=new Element('body'), doc=new Target(), win=new Target();
  root.setAttribute('data-motion', options.motion||'living'); if(options.theme)root.setAttribute('data-theme',options.theme);
  doc.documentElement=root;doc.body=body;doc.hidden=!!options.hidden;doc.createElement=t=>new Element(t);doc.getElementById=id=>id==='zg'?game:null;
  const reduce=new Target(),fine=new Target();reduce.matches=!!options.reduce;fine.matches=options.fine!==false;
  win.innerWidth=1000;win.innerHeight=800;
  win.matchMedia=q=>q.includes('prefers-reduced-motion')?reduce:fine;
  win.requestAnimationFrame=fn=>{rafs.set(++nextRaf,fn);requested++;peak=Math.max(peak,rafs.size);return nextRaf;};
  win.cancelAnimationFrame=id=>{if(rafs.delete(id))canceled++;};
  const forbidden=()=>{external++;throw new Error('Unexpected external I/O');};
  win.fetch=forbidden;
  const localStorage={getItem(k){if(options.storageThrows)throw new Error('Storage unavailable');return store.get(k)||null;}};
  class Observer { constructor(callback){this.callback=callback;} observe(target,opts){this.target=target;this.options=opts;observers.push(this);} }
  vm.runInNewContext(code,{window:win,document:doc,localStorage,MutationObserver:Observer,fetch:forbidden,XMLHttpRequest:forbidden,Image:forbidden},{filename:source,timeout:1000});
  function flushMutations(){let count=0;while(mutations.length){if(++count>100)throw new Error('Observer sync loop');mutations.shift()();}}
  flushMutations();
  return {root,body,doc,win,reduce,fine,store,rafs,
    attr(k,v){v===null?root.removeAttribute(k):root.setAttribute(k,v);flushMutations();},
    flush(){for(const [id,fn] of [...rafs]){rafs.delete(id);fn();}flushMutations();},
    mouse(x=1000,y=800){doc.send('pointermove',{pointerType:'mouse',clientX:x,clientY:y});},
    touch(){doc.send('pointermove',{pointerType:'touch',clientX:0,clientY:0});},
    pen(){doc.send('pointermove',{pointerType:'pen',clientX:0,clientY:0});},
    visibility(hidden){doc.hidden=hidden;doc.send('visibilitychange');flushMutations();},
    media(which,value){const q=which==='reduce'?reduce:fine;q.matches=value;q.send('change');flushMutations();},
    game(value){game=value?new Element('div'):null;change(body,'childList');flushMutations();},
    get layer(){return body.children.find(x=>x.classList.contains('calavera-atmosphere'));},
    get field(){return this.layer?.children.find(x=>x.classList.contains('cn-field'));},
    stats(){return {pending:rafs.size,peak,requested,canceled,external};}
  };
}
const f=fixture();
check('No default-theme atmosphere allocation',f.body.children.length===0);
check('No default-theme pointer listener or animation frame',f.doc.count('pointermove')===0&&f.stats().pending===0);
f.attr('data-theme','calavera');
check('Calavera creates one decorative layer',f.body.children.length===1&&f.layer.getAttribute('aria-hidden')==='true');
check('Living root lifecycle marker is present',f.root.classList.contains('cn-living'));
check('Skulls remain outside overscanned parallax field',f.layer.children.filter(x=>x.classList.contains('cn-skull')).length===2&&f.field.children.every(x=>x.classList.contains('cn-light')));
check('Fine pointer attaches exactly one passive-path listener',f.doc.count('pointermove')===1);
for(let i=0;i<100;i++)f.mouse(i*10,i*8);
check('One hundred pointer events coalesce to one pending rAF',f.stats().pending===1&&f.stats().requested===1&&f.stats().peak===1,f.stats());
f.flush();
check('Paint flushes without self-scheduling a loop',f.stats().pending===0);
check('Parallax stays within intended small bounds',Math.abs(parseFloat(f.field.style.getPropertyValue('--cn-x')))<=14&&Math.abs(parseFloat(f.field.style.getPropertyValue('--cn-y')))<=10);
const requests=f.stats().requested;f.touch();f.pen();
check('Touch and pen do not request animation frames',f.stats().requested===requests);
f.mouse();f.attr('data-motion','still');
check('Still removes listener and cancels pending frame',f.doc.count('pointermove')===0&&f.stats().pending===0&&f.stats().canceled===1);
check('Still clears parallax and ambient motion class',!f.field.style.getPropertyValue('--cn-x')&&!f.field.style.getPropertyValue('--cn-y')&&!f.layer.classList.contains('is-living'));
check('Still removes heading-animation root marker',!f.root.classList.contains('cn-living'));
f.attr('data-motion','living');f.mouse();f.media('reduce',true);
check('Reduced-motion change cancels pointer and ambient work',f.doc.count('pointermove')===0&&f.stats().pending===0&&!f.layer.classList.contains('is-living'));
check('Reduced motion removes heading-animation root marker',!f.root.classList.contains('cn-living'));
f.media('reduce',false);f.mouse();f.visibility(true);
check('Hidden document cancels pending work and ambient class',f.doc.count('pointermove')===0&&f.stats().pending===0&&!f.layer.classList.contains('is-living'));
check('Hidden document removes heading-animation root marker',!f.root.classList.contains('cn-living'));
f.visibility(false);
check('Visible document resumes once',f.doc.count('pointermove')===1&&f.layer.classList.contains('is-living'));
f.mouse();f.media('fine',false);
check('Coarse-pointer change cancels pending pointer work',f.doc.count('pointermove')===0&&f.stats().pending===0);
f.media('fine',true);f.mouse();f.attr('data-theme','maya');
check('Leaving theme hides the layer and cancels work',f.layer.hidden&&f.doc.count('pointermove')===0&&f.stats().pending===0);
for(let i=0;i<100;i++){f.attr('data-theme','calavera');f.attr('data-theme','maya');}
f.attr('data-theme','calavera');
check('Theme churn does not duplicate layers or pointer listeners',f.body.children.length===1&&f.doc.count('pointermove')===1);
f.mouse();f.win.send('pagehide');
check('pagehide cancels frame/listener and ambient class',f.stats().pending===0&&f.doc.count('pointermove')===0&&!f.layer.classList.contains('is-living'));
check('pagehide removes heading-animation root marker',!f.root.classList.contains('cn-living'));
f.win.send('pageshow');
check('pageshow restores one listener',f.doc.count('pointermove')===1);
f.store.set('zotheos_rain','heavy');f.win.send('storage');
check('Storage intensity update affects existing layer',f.layer.style.getPropertyValue('--cn-strength')==='.8');
const clicked=new (f.root.constructor)('button');clicked.id='fxAmount';f.store.set('zotheos_rain','light');f.doc.send('click',{target:clicked});
check('Existing intensity control click updates strength',f.layer.style.getPropertyValue('--cn-strength')==='.35');
f.mouse();f.game(true);
check('Active game suppresses atmospheric layer and pointer work',f.layer.hidden&&f.doc.count('pointermove')===0&&f.stats().pending===0);
check('Active game removes heading-animation root marker',!f.root.classList.contains('cn-living'));
f.game(false);
check('Removing game restores one layer and one listener',f.body.children.length===1&&f.doc.count('pointermove')===1);
check('Runtime performs no external I/O',f.stats().external===0);
const locked=fixture({theme:'calavera',storageThrows:true});
check('Unavailable localStorage leaves a usable default strength',locked.layer.style.getPropertyValue('--cn-strength')==='.56');
const calm=fixture({theme:'calavera',motion:'calm'});
check('Calm starts with static atmosphere and no pointer work',!calm.layer.hidden&&!calm.layer.classList.contains('is-living')&&calm.doc.count('pointermove')===0&&calm.stats().pending===0);
const game=fixture();game.game(true);game.attr('data-theme','calavera');
check('Game-first route does not allocate an atmospheric layer',game.body.children.length===0&&game.doc.count('pointermove')===0);
const keyed=fixture({theme:'calavera'}),keyControl=new (keyed.root.constructor)('button');keyControl.id='fxAmount';
keyed.store.set('zotheos_rain','heavy');keyed.doc.send('keydown',{target:keyControl,key:'ArrowRight'});
check('Existing intensity radio keyboard selection updates current decorative strength',keyed.layer.style.getPropertyValue('--cn-strength')==='.8');
const report={checked_at:new Date().toISOString(),source,source_sha256:crypto.createHash('sha256').update(code).digest('hex'),probe_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),checks,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length,stats:f.stats(),limits:['Simulated DOM/event boundary, not browser, native accessibility, visual or performance measurement.','Stylesheet hidden-heading, forced-colors and print behavior require separate review/browser verification.']};
const out=process.argv[3];fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,failed:report.failed,source_sha256:report.source_sha256,stats:report.stats}));process.exitCode=report.failed?1:0;
