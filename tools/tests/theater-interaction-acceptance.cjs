/* Independent prebuild interaction contract. Fictional DOM hooks supply no
   search, selection, consent or player algorithm. Not browser certification. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = process.argv[2] || path.resolve(__dirname, '../../static/theater/theater.js');
assert(fs.existsSync(sourcePath), 'The actual optional Theater enhancement script must exist');
const source = fs.readFileSync(sourcePath, 'utf8');

function fixture() {
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
  ];
  const cards = [], selects = [], officialLinks = [];
  for (const item of inputs) {
    const attrs = {'data-theater-film':item.id, 'data-id':item.id, 'data-search':item.search, 'data-topic':item.topic,
      'data-title':item.title, 'data-watch-url':item.watch, 'data-kind':'trailer',
      'data-availability':'Official source; access and regional availability may change.',
      'data-summary':'Fictional test description.', 'data-content-note':'Fictional content note.', 'data-credits':'Fictional filmmaker'};
    attrs['data-provider'] = item.provider || '';
    if (item.videoId) attrs['data-video-id'] = item.videoId;
    const card = add('article',item.id,attrs,item.title); cards.push(card);
    selects.push(card.add(new El('button','select-'+item.id,{'data-theater-select':item.id,type:'button'},'Details')));
    officialLinks.push(card.add(new El('a','watch-'+item.id,{href:item.watch,target:'_blank',rel:'noopener noreferrer'},'Official Source')));
  }
  document = {readyState:'complete', documentElement:new El('html'), activeElement:null,
    getElementById: id => ids[id] || null, querySelector: s => root.querySelector(s), querySelectorAll: s => root.querySelectorAll(s),
    createElement: tag => new El(tag), addEventListener: (type,fn) => root.addEventListener(type,fn)};
  const deny = name => (...args) => { blocked.push(name); throw new Error('Forbidden outside API: '+name); };
  const window = {location:{hash:'',href:'https://zotheos.org/theater'},
    addEventListener(type,fn) { (winEvents[type] ||= []).push(fn); },
    requestAnimationFrame: fn => fn(), matchMedia: () => ({matches:true,addEventListener(){}})};
  for (const name of ['localStorage','sessionStorage']) Object.defineProperty(window,name,{get(){ blocked.push(name); throw new Error('Theater may not store viewer choices'); }});
  Object.defineProperty(document,'cookie',{get: deny('cookie read'),set: deny('cookie write')});
  const context = {document,window,console,URL,URLSearchParams,Map,Set,
    fetch:deny('fetch'), XMLHttpRequest:deny('XMLHttpRequest'), WebSocket:deny('WebSocket'), EventSource:deny('EventSource'),
    Image:deny('Image'), navigator:{sendBeacon:deny('sendBeacon')},
    requestAnimationFrame:fn=>fn(), setTimeout:fn=>{ fn(); return 1; }, clearTimeout(){}};
  // Accessing the fixture's own localStorage getter would itself be a request to
  // forbidden state; expose a trapped binding without reading it during setup.
  delete context.localStorage;
  Object.defineProperty(context,'localStorage',{get(){ return window.localStorage; }});
  Object.defineProperty(context,'sessionStorage',{get(){ return window.sessionStorage; }});
  return {root,ids,search,topic,clear,tools,status,empty,player,load,close,playerStatus,consent,cards,selects,officialLinks,requests,frames,blocked,focuses,
    init(){ vm.runInNewContext(source,context,{filename:sourcePath,timeout:1000}); },
    visible(){ return cards.filter(card=>!card.hidden); },
    currentFrames(){ return player.querySelectorAll('iframe'); },
    key(key){ for(const fn of winEvents.keydown||[]) fn({key,preventDefault(){}}); root.event('keydown',{key}); }};
}

let passed = 0;
function test(name,fn) { const f=fixture(); f.init(); fn(f); assert.deepEqual(f.blocked,[]); passed++; console.log('PASS '+name); }
function loadSelected(f, provider='youtube', id='abcdefghijk') {
  f.load.event('click');
  assert.equal(f.currentFrames().length,1,'Consent creates exactly one frame');
  const frame=f.currentFrames()[0], u=new URL(frame.src);
  assert.equal(u.origin,provider==='pbs'?'https://player.pbs.org':'https://www.youtube-nocookie.com');
  assert.equal(u.pathname,provider==='pbs'?'/stationplayer/'+id+'/':'/embed/'+id);
  assert(!u.searchParams.has('autoplay') || u.searchParams.get('autoplay')==='0','Autoplay is forbidden');
  assert(frame.title.trim().length>0,'Player needs an accessible title');
  assert.equal(frame.referrerPolicy,'strict-origin-when-cross-origin');
  assert(!/(^|;)\s*autoplay\b/.test(frame.allow),'Do not grant autoplay permission');
}

test('Initial enhancement makes no outside request, embeds nothing and keeps static watch links',f=>{
  assert.equal(f.requests.length,0); assert.equal(f.frames.length,0); assert.equal(f.currentFrames().length,0);
  assert.equal(f.visible().length,6); assert.equal(f.tools.hidden,false);
  for(const link of f.officialLinks) assert(link.href.startsWith('https://publisher.example.test/'));
});
test('Search and topic combine, report zero results and recover through Clear Filters',f=>{
  f.search.value='  RIVER  '; f.search.event('input'); assert.deepEqual(f.visible().map(x=>x.id),['fixture-river']);
  f.topic.value='language'; f.topic.event('change'); assert.equal(f.visible().length,0); assert.equal(f.empty.hidden,false);
  assert.match(f.status.textContent,/0/);
  f.clear.event('click'); assert.equal(f.search.value,''); assert.equal(f.topic.value,'all'); assert.equal(f.visible().length,6); assert.equal(f.empty.hidden,true);
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
});
test('Selecting a film is separate from explicit player consent',f=>{
  f.selects[0].event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
  loadSelected(f); assert.equal(f.requests.length,1);
  f.load.event('click'); assert.equal(f.currentFrames().length,1,'Repeated consent may not stack players');
});
test('Closing removes the player and reopening requires a fresh consent action',f=>{
  f.selects[0].event('click'); loadSelected(f); f.close.event('click'); assert.equal(f.currentFrames().length,0);
  const count=f.requests.length; f.selects[0].event('click'); assert.equal(f.requests.length,count); assert.equal(f.currentFrames().length,0);
  loadSelected(f);
});
test('Changing to a film without an embed stops the prior player and retains the official fallback',f=>{
  f.selects[0].event('click'); loadSelected(f); const count=f.requests.length;
  f.selects[1].event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
  f.load.event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
  assert.equal(f.officialLinks[1].href,'https://publisher.example.test/words');
});
test('Changing back to an embeddable film requires consent again',f=>{
  f.selects[0].event('click'); loadSelected(f); f.selects[1].event('click'); f.selects[0].event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,1); loadSelected(f);
});
test('Invalid video IDs cannot create iframe markup or an outside request',f=>{
  f.selects[2].event('click'); f.load.event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
  assert.equal(f.officialLinks[2].href,'https://publisher.example.test/broken');
});
test('Publisher-provided PBS player has the same explicit consent and close boundary',f=>{
  f.selects[3].event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
  loadSelected(f,'pbs','3067357496'); f.close.event('click'); assert.equal(f.currentFrames().length,0);
});
test('Malformed PBS identifiers never become embed URLs',f=>{
  f.selects[4].event('click'); f.load.event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
});
test('Unapproved provider cannot inherit the YouTube or PBS frame permission',f=>{
  f.selects[5].event('click'); f.load.event('click'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
});
console.log(JSON.stringify({passed,total:10,scope:'Isolated actual-script behavior, not a browser or accessibility certification'}));
