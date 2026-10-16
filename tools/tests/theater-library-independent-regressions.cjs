/* Independent v2 prebuild interaction contract. User authorized ready players and remote thumbnails. Fictional DOM hooks supply no
   search, selection, consent or player algorithm. Not browser certification. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = process.argv[2] || path.resolve(__dirname, '../../static/theater/theater.js');
assert(fs.existsSync(sourcePath), 'The actual optional Theater enhancement script must exist');
const source = fs.readFileSync(sourcePath, 'utf8');

function fixture(options = {}) {
  const ids = {}, requests = [], frames = [], blocked = [], focuses = [], winEvents = {};
  let document;
  class El {
    constructor(tag = 'div', id = '', attrs = {}, text = '') {
      this.tagName = tag.toUpperCase(); this.id = id; this.attrs = {...attrs};
      this.children = []; this.parentElement = null; this.events = {}; this.hidden = false;
      this.textContent = text; this.value = ''; this.disabled = false; this.style = {};
      this.className = attrs.class || ''; this.type = attrs.type || '';
      if (id) { ids[id] = this; this.attrs.id = id; }
      this.classList = {contains: key => this.className.split(/\s+/).includes(key),
        add: key => { this.className += ' ' + key; },
        remove: key => { this.className = this.className.split(/\s+/).filter(x => x !== key).join(' '); },
        toggle: (key, force) => { const on = force ?? !this.classList.contains(key); on ? this.classList.add(key) : this.classList.remove(key); return on; }};
      this.dataset = new Proxy({}, {get: (_, key) => this.getAttribute('data-' + String(key).replace(/[A-Z]/g, x => '-' + x.toLowerCase())),
        set: (_, key, value) => { this.setAttribute('data-' + String(key).replace(/[A-Z]/g, x => '-' + x.toLowerCase()), value); return true; }});
    }
    getAttribute(key) { return Object.hasOwn(this.attrs, key) ? this.attrs[key] : null; }
    setAttribute(key, value) { this.attrs[key] = String(value); if (key === 'id') { this.id = String(value); ids[this.id] = this; } }
    removeAttribute(key) { delete this.attrs[key]; }
    get src() { return this.attrs.src || ''; } set src(value) { this.setAttribute('src', value); }
    get href() { return this.attrs.href || ''; } set href(value) { this.setAttribute('href', value); }
    get title() { return this.attrs.title || ''; } set title(value) { this.setAttribute('title', value); }
    get referrerPolicy() { return this.attrs.referrerpolicy || ''; } set referrerPolicy(value) { this.setAttribute('referrerpolicy', value); }
    get allow() { return this.attrs.allow || ''; } set allow(value) { this.setAttribute('allow', value); }
    get firstChild() { return this.children[0] || null; }
    get childElementCount() { return this.children.length; }
    get innerHTML() { return ''; }
    set innerHTML(value) { assert.equal(value, '', 'Player markup must be constructed with DOM methods'); this.replaceChildren(); }
    add(el) { return this.appendChild(el); }
    appendChild(el) { el.parentElement = this; this.children.push(el); if (el.tagName === 'IFRAME') { frames.push(el); requests.push(el.src); } return el; }
    append(...els) { for (const el of els) this.appendChild(el); }
    replaceChildren(...els) { for (const el of this.children) el.parentElement = null; this.children = []; this.append(...els); }
    removeChild(el) { this.children = this.children.filter(x => x !== el); el.parentElement = null; return el; }
    remove() { this.parentElement?.removeChild(this); }
    contains(el) { for (; el; el = el.parentElement) if (el === this) return true; return false; }
    matches(selector) {
      if (selector.includes(',')) return selector.split(',').some(s => this.matches(s.trim()));
      const tag = selector.match(/^[a-z]+/i)?.[0];
      if (tag && this.tagName !== tag.toUpperCase()) return false;
      const id = selector.match(/#([\w-]+)/)?.[1]; if (id && this.id !== id) return false;
      const cls = selector.match(/\.([\w-]+)/)?.[1]; if (cls && !this.classList.contains(cls)) return false;
      for (const match of selector.matchAll(/\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\]/g)) {
        const value = this.getAttribute(match[1]); if (value === null || (match[2] !== undefined && value !== match[2])) return false;
      }
      return true;
    }
    querySelectorAll(selector) { const found = []; for (const child of this.children) { if (child.matches(selector)) found.push(child); found.push(...child.querySelectorAll(selector)); } return found; }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { for (let el = this; el; el = el.parentElement) if (el.matches(selector)) return el; return null; }
    addEventListener(type, fn) { (this.events[type] ||= []).push(fn); }
    event(type, extra = {}) {
      const ev = {type, target: this, key: '', button: 0, defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; }, ...extra};
      for (let el = this; el; el = el.parentElement) for (const fn of el.events[type] || []) fn.call(el, ev);
    }
    focus() { document.activeElement = this; focuses.push(this.id); }
    scrollIntoView() {}
  }
  const root = new El('document');
  function add(tag, id, attrs, text) { return root.add(new El(tag, id, attrs, text)); }
  const search = add('input', 'theaterSearch', {type: 'search'});
  const topic = add('select', 'theaterTopic'); topic.value = 'all';
  topic.options = [{value:'all', textContent:'All Topics'}, {value:'land', textContent:'Land'}, {value:'language', textContent:'Language'}];
  const clear = add('button', 'theaterClear', {type:'button'}, 'Clear Filters');
  const motion = add('button', 'theaterMotion', {type:'button','aria-pressed':'false'}, 'Still');
  const tools = add('div', 'theaterTools'); tools.hidden = true;
  const status = add('p', 'theaterStatus', {role:'status'});
  const empty = add('div', 'theaterEmpty', {}, 'No matching films. Clear filters to explore the collection.'); empty.hidden = true;
  const player = add('div', 'theaterPlayer');
  const load = add('button', 'theaterLoad', {type:'button'}, 'Load YouTube Player');
  const close = add('button', 'theaterClose', {type:'button'}, 'Close Player'); close.hidden = true;
  const playerStatus = add('p', 'theaterPlayerStatus', {role:'status'});
  const consent = add('p', 'theaterConsent', {}, 'Loading connects to the selected video provider, which receives information about your device and request. Its own policies apply.');
  for (const id of ['theaterTitle','theaterDescription','theaterAvailability','theaterKind','theaterContentNote','theaterCredits']) add('p',id);
  const watch = add('a','theaterWatch',{href:'https://publisher.example.test/river',rel:'noopener noreferrer',target:'_blank'},'Open Official Page');
  const inputs = [
    {id:'fixture-river', title:'River Voices', search:'river voices water sovereignty', topic:'land', provider:'youtube', videoId:'abcdefghijk', watch:'https://publisher.example.test/river'},
    {id:'fixture-language', title:'Living Words', search:'living words language renewal', topic:'language', videoId:null, watch:'https://publisher.example.test/words'},
    {id:'fixture-invalid', title:'Broken Clip Fixture', search:'broken clip fixture land', topic:'land', provider:'youtube', videoId:'bad-id<script>', watch:'https://publisher.example.test/broken'},
    {id:'fixture-pbs', title:'Coast Voice', search:'coast voice excerpt', topic:'land', provider:'pbs', videoId:'3067357496', watch:'https://publisher.example.test/coast'},
    {id:'fixture-pbs-invalid', title:'Invalid PBS Fixture', search:'invalid pbs fixture', topic:'land', provider:'pbs', videoId:'3067357496/evil', watch:'https://publisher.example.test/pbs-invalid'},
    {id:'fixture-provider-invalid', title:'Unknown Provider Fixture', search:'unknown provider fixture', topic:'land', provider:'other', videoId:'abcdefghijk', watch:'https://publisher.example.test/provider-invalid'},
    {id:'fixture-vimeo',title:'Vimeo Record',search:'vimeo recorded conversation',topic:'land',provider:'vimeo',videoId:'141218300',watch:'https://publisher.example.test/vimeo'},
    {id:'fixture-vimeo-invalid',title:'Invalid Vimeo',search:'invalid vimeo',topic:'land',provider:'vimeo',videoId:'141218300?autoplay=1',watch:'https://publisher.example.test/vimeo-invalid'},
    {id:'fixture-nfb',title:'NFB Record',search:'nfb film',topic:'land',provider:'nfb',videoId:'birth_of_a_family',watch:'https://publisher.example.test/nfb'},
    {id:'fixture-nfb-invalid',title:'Invalid NFB',search:'invalid nfb',topic:'land',provider:'nfb',videoId:'../birth_of_a_family',watch:'https://publisher.example.test/nfb-invalid'},
    {id:'fixture-pbs-viral',title:'PBS Viral Record',search:'pbs film',topic:'land',provider:'pbs',videoId:'3109669877',pbsRoute:'viralplayer',watch:'https://publisher.example.test/pbs-viral'},
  ];
  if(options.total) while(inputs.length<options.total) {
    const i=inputs.length; inputs.push({id:'fixture-extra-'+i,title:'Story '+i,search:'story water '+i,
      topic:'land',provider:'youtube',videoId:'abcdefghijk',watch:'https://publisher.example.test/story/'+i});
  }
  const region=add('select','theaterRegion'); region.value='all';
  const kind=add('select','theaterViewing'); kind.value='all';
  const more=add('button','theaterMore',{},'Show More Stories');
  const next=add('button','theaterNext',{},'Next Story');
  const cards = [], selects = [], officialLinks = [];
  for (const item of inputs) {
    const attrs = {'data-theater-film':item.id, 'data-featured':String(item.id === (options.featured || 'fixture-river')), 'data-id':item.id, 'data-search':item.search, 'data-topic':item.topic,
      'data-title':item.title, 'data-watch-url':item.watch, 'data-kind':'trailer',
      'data-availability':'Official source; access and regional availability may change.',
      'data-region':inputs.indexOf(item)%2?'oceania':'north-america', 'data-viewing':item.id==='fixture-language'?'official-page':'full-film', 'data-summary':'Fictional test description.', 'data-content-note':'Fictional content note.', 'data-credits':'Fictional filmmaker'};
    attrs['data-provider'] = item.provider || '';
    attrs['data-pbs-route']=item.pbsRoute || 'stationplayer';
    if (item.videoId) attrs['data-video-id'] = item.videoId;
    const card = add('article',item.id,attrs,item.title); cards.push(card);
    selects.push(card.add(new El('button','select-'+item.id,{'data-theater-select':item.id,type:'button'},'Details')));
    officialLinks.push(card.add(new El('a','watch-'+item.id,{href:item.watch,target:'_blank',rel:'noopener noreferrer'},'Official Source')));
  }
  document = {readyState:'complete', documentElement:new El('html'), activeElement:null,
    getElementById: id => ids[id] || null, querySelector: s => root.querySelector(s), querySelectorAll: s => root.querySelectorAll(s),
    createElement: tag => new El(tag), addEventListener: (type,fn) => root.addEventListener(type,fn)};
  const deny = name => (...args) => { blocked.push(name); throw new Error('Forbidden outside API: '+name); };
  const mediaEvents = [];
  const media = {matches: Boolean(options.reduced), addEventListener(type,fn){if(type==='change') mediaEvents.push(fn);}, addListener(fn){mediaEvents.push(fn);}};
  const window = {location:{hash:'',href:'https://zotheos.org/theater'},
    addEventListener(type,fn) { (winEvents[type] ||= []).push(fn); },
    requestAnimationFrame: fn => fn(), matchMedia: () => media};
  for (const name of ['localStorage','sessionStorage']) Object.defineProperty(window,name,{get(){ blocked.push(name); throw new Error('Theater may not store viewer choices'); }});
  Object.defineProperty(document,'cookie',{get: deny('cookie read'),set: deny('cookie write')});
  document.body = root;
  const mutationObservers=[];
  class MutationObserver { constructor(fn){mutationObservers.push(fn);} observe(){} disconnect(){} }
  if(options.globalStill) document.documentElement.setAttribute('data-motion','still');
  if(options.calm) document.documentElement.setAttribute('data-motion','calm');
  const context = {document,window,console,URL,URLSearchParams,Map,Set,MutationObserver,matchMedia:()=>media,
    fetch:deny('fetch'), XMLHttpRequest:deny('XMLHttpRequest'), WebSocket:deny('WebSocket'), EventSource:deny('EventSource'),
    Image:deny('Image'), navigator:{sendBeacon:deny('sendBeacon')},
    requestAnimationFrame:fn=>fn(), setTimeout:fn=>{ fn(); return 1; }, clearTimeout(){}};
  // Accessing the fixture's own localStorage getter would itself be a request to
  // forbidden state; expose a trapped binding without reading it during setup.
  delete context.localStorage;
  Object.defineProperty(context,'localStorage',{get(){ return window.localStorage; }});
  Object.defineProperty(context,'sessionStorage',{get(){ return window.sessionStorage; }});
  return {root,ids,document,media,motion,search,topic,region,kind,more,next,clear,tools,status,empty,player,load,close,playerStatus,consent,cards,selects,officialLinks,requests,frames,blocked,focuses,
    init(){ delete ids.theaterLoad; delete ids.theaterClose; vm.runInNewContext(source,context,{filename:sourcePath,timeout:1000}); },
    visible(){ return cards.filter(card=>!card.hidden); },
    currentFrames(){ return player.querySelectorAll('iframe'); },
    reduce(value){ media.matches=value; for(const fn of mediaEvents) fn({matches:value}); },
    globalStill(value){ document.documentElement.setAttribute('data-motion',value?'still':'ambient'); for(const fn of mutationObservers) fn([{attributeName:'data-motion',target:document.documentElement}]); },
    message(data, origin='https://www.youtube-nocookie.com'){ for(const fn of winEvents.message||[]) fn({data,origin,source:null}); },
    key(key){ for(const fn of winEvents.keydown||[]) fn({key,preventDefault(){}}); root.event('keydown',{key}); }};
}




const results=[];
function test(name,fn,options={}) { try { const f=fixture(options); f.init(); fn(f); assert.deepEqual(f.blocked,[]); results.push({name,pass:true}); } catch(error) { results.push({name,pass:false,error:error.message}); } }
function ready(f) {
  assert.equal(f.currentFrames().length,1,'One selected ready frame required');
  const frame=f.currentFrames()[0], u=new URL(frame.src);
  assert.equal(u.searchParams.get('autoplay'),'0');
  assert(!String(frame.allow).split(';').some(part=>part.trim().startsWith('autoplay')),'No autoplay permission');
  return frame;
}
test('Next Story cycles only through the current region and viewing matches', f=>{
  f.region.value='oceania'; f.kind.value='full-film'; f.region.event('change');
  const ids=f.visible().map(c=>c.id); assert(ids.length>1);
  for(let i=0;i<=ids.length;i++) { f.next.event('click'); assert.equal(f.ids.theaterTitle.textContent, f.ids[ids[i%ids.length]].dataset.title); }
});
test('Next Story reveals a selected result beyond the first24 cards', f=>{
  for(let i=0;i<24;i++)f.next.event('click');
  assert.equal(f.ids.theaterTitle.textContent,f.cards[24].dataset.title);
  assert.equal(f.cards[24].hidden,false); assert.equal(f.visible().length,48); ready(f);
},{total:200});
test('Next Story begins at the first match when selection was excluded by a filter', f=>{
  const initial=ready(f); f.search.value='story water'; f.search.event('input');
  assert.equal(ready(f),initial); const first=f.visible()[0]; f.next.event('click');
  assert.equal(f.ids.theaterTitle.textContent,first.dataset.title); assert.equal(initial.parentElement,null); ready(f);
},{total:200});
test('Zero or one match disables Next Story without changing selection', f=>{
  const initial=ready(f); f.search.value='no such match'; f.search.event('input'); assert.equal(f.next.disabled,true);
  assert.equal(ready(f),initial); f.search.value='living words'; f.search.event('input'); assert.equal(f.next.disabled,true);
  assert.equal(ready(f),initial);
});
test('Native provider completion events never advance or request another story', f=>{
  const initial=ready(f), count=f.requests.length, title=f.ids.theaterTitle.textContent;
  initial.event('ended'); f.player.event('ended');
  f.message(JSON.stringify({event:'onStateChange',info:0}));
  f.message({event:'finish'},'https://player.vimeo.com');
  assert.equal(f.ids.theaterTitle.textContent,title); assert.equal(ready(f),initial); assert.equal(f.requests.length,count);
});
test('Selection replaces prior play state and selects exactly one pressed card', f=>{
  const initial=ready(f); f.selects[6].event('click');
  assert.equal(initial.parentElement,null); const frame=ready(f);
  assert.equal(new URL(frame.src).hostname,'player.vimeo.com');
  assert.deepEqual(f.selects.filter(b=>b.getAttribute('aria-pressed')==='true').map(b=>b.dataset.theaterSelect),['fixture-vimeo']);
});
test('Unavailable title keeps truthful availability and native official fallback', f=>{
  const initial=ready(f); f.selects[1].event('click'); assert.equal(initial.parentElement,null);
  assert.equal(f.currentFrames().length,0); assert.equal(f.ids.theaterWatch.href,'https://publisher.example.test/words');
  assert(f.playerStatus.textContent.includes(f.cards[1].dataset.availability));
});
for(const index of [2,4,5,7,9]) test('Invalid provider fixture '+index+' stays source-only',f=>{
  ready(f); f.selects[index].event('click'); assert.equal(f.currentFrames().length,0);
  assert.equal(f.ids.theaterWatch.href,f.cards[index].dataset.watchUrl);
});
for(const bad of ['../film','film?autoplay=1','film/embed/player/','film%2Fother','film\\other']) test('NFB path rejects '+JSON.stringify(bad),f=>{
  f.cards[8].dataset.videoId=bad; f.selects[8].event('click'); assert.equal(f.currentFrames().length,0);
});
for(const slug of ['bill-reid-remembers','Waaydanaa','some_film-title']) test('NFB bounded published slug '+slug+' preserves fixed origin',f=>{
  f.cards[8].dataset.videoId=slug; f.selects[8].event('click');
  const u=new URL(ready(f).src); assert.equal(u.origin,'https://www.nfb.ca'); assert.equal(u.pathname,'/film/'+slug+'/embed/player/');
});
for(const bad of ['javascript:alert(1)','http://publisher.example.test/','https://user:pass@publisher.example.test/','https://publisher.example.test:0/','https://publisher.example.test:/']) test('Selected source rejects '+bad,f=>{
  f.cards[3].dataset.watchUrl=bad; f.selects[3].event('click'); assert.equal(f.ids.theaterWatch.href,'/theater'); ready(f);
});
for(const modifier of ['ctrlKey','metaKey','shiftKey','altKey']) test('Native poster '+modifier+' click preserves normal external link behavior',f=>{
  const initial=ready(f), count=f.requests.length; f.selects[3].tagName='A'; f.selects[3].event('click',{[modifier]:true});
  assert.equal(ready(f),initial); assert.equal(f.requests.length,count);
});
test('ASCII search finds accented names while retaining original displayed spelling', f=>{
  f.cards[0].dataset.title='Uýra'; f.cards[0].dataset.search='Uýra João forest';
  f.search.value='uyra joao'; f.search.event('input'); assert.deepEqual(f.visible().map(c=>c.id),['fixture-river']);
  assert.equal(f.cards[0].dataset.title,'Uýra');
});
test('Changing OS reduced-motion preference keeps manual pause meaningful', f=>{
  f.motion.event('click'); f.reduce(true); f.reduce(false);
  assert.equal(f.document.documentElement.dataset.theaterMotion,'still');
  f.motion.event('click'); assert.equal(f.document.documentElement.dataset.theaterMotion,'ambient');
});
test('Global Still locks ambient motion until explicitly released', f=>{
  f.globalStill(true); assert.equal(f.document.documentElement.dataset.theaterMotion,'still');
  f.motion.event('click'); assert.equal(f.document.documentElement.dataset.theaterMotion,'still');
  f.globalStill(false); assert.equal(f.document.documentElement.dataset.theaterMotion,'ambient');
});
console.log(JSON.stringify({scope:'Supplemental adversarial contract against actual optional script; no real player/network/browser certification.',passed:results.filter(r=>r.pass).length,total:results.length,results},null,2));
if(results.some(r=>!r.pass))process.exitCode=1;
