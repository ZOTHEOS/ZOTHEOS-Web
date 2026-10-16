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
  const cards = [], selects = [], officialLinks = [];
  for (const item of inputs) {
    const attrs = {'data-theater-film':item.id, 'data-featured':String(item.id === (options.featured || 'fixture-river')), 'data-id':item.id, 'data-search':item.search, 'data-topic':item.topic,
      'data-title':item.title, 'data-watch-url':item.watch, 'data-kind':'trailer',
      'data-availability':'Official source; access and regional availability may change.',
      'data-summary':'Fictional test description.', 'data-content-note':'Fictional content note.', 'data-credits':'Fictional filmmaker'};
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
  return {root,ids,document,media,motion,search,topic,clear,tools,status,empty,player,load,close,playerStatus,consent,cards,selects,officialLinks,requests,frames,blocked,focuses,
    init(){ vm.runInNewContext(source,context,{filename:sourcePath,timeout:1000}); },
    visible(){ return cards.filter(card=>!card.hidden); },
    currentFrames(){ return player.querySelectorAll('iframe'); },
    reduce(value){ media.matches=value; for(const fn of mediaEvents) fn({matches:value}); },
    globalStill(value){ document.documentElement.setAttribute('data-motion',value?'still':'ambient'); for(const fn of mutationObservers) fn([{attributeName:'data-motion',target:document.documentElement}]); },
    key(key){ for(const fn of winEvents.keydown||[]) fn({key,preventDefault(){}}); root.event('keydown',{key}); }};
}


const results=[];
function test(name,fn,options={}) {
  try { const f=fixture(options); f.init(); fn(f); assert.deepEqual(f.blocked,[]); results.push({name,result:'PASS'}); }
  catch(error) { results.push({name,result:'FAIL',error:error.message}); }
}
function current(f,provider='youtube',id='abcdefghijk',route='stationplayer') {
  assert.equal(f.currentFrames().length,1,'Exactly one ready player is present');
  const frame=f.currentFrames()[0], url=new URL(frame.src);
  const origins={youtube:'https://www.youtube-nocookie.com',pbs:'https://player.pbs.org',vimeo:'https://player.vimeo.com',nfb:'https://www.nfb.ca'};
  assert.equal(url.origin,origins[provider]);
  const expected=provider==='pbs'?'/'+route+'/'+id+'/':provider==='vimeo'?'/video/'+id:provider==='nfb'?'/film/'+id+'/embed/player/':'/embed/'+id;
  assert.equal(url.pathname,expected);
  if(provider!=='nfb') assert.equal(url.searchParams.get('autoplay'),'0','A ready player never starts the recording');
  assert(!url.searchParams.has('autoplay') || url.searchParams.get('autoplay')==='0');
  if(provider==='pbs') assert.equal(url.searchParams.get('autoPlay'),'false');
  assert(frame.title && frame.title.trim());
  assert.equal(frame.referrerPolicy,'strict-origin-when-cross-origin');
  assert(!/(^|;)s*autoplay/.test(frame.allow));
  return frame;
}
function still(f) { return f.document.documentElement.dataset.theaterMotion==='still' || f.document.body.dataset.theaterMotion==='still'; }

test('The featured recording is ready on entry without autoplay or initial focus theft',f=>{
  current(f); assert.equal(f.requests.length,1); assert.equal(f.focuses.length,0);
  for(const link of f.officialLinks) assert(link.href.startsWith('https://publisher.example.test/'));
});
test('Native featured state chooses the actual selected item rather than first card',f=>{
  current(f,'pbs','3067357496');
},{featured:'fixture-pbs'});
test('A featured item without an allowed embed retains native fallback and no fake player',f=>{
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
  assert.equal(f.ids.theaterWatch.href,'https://publisher.example.test/words');
},{featured:'fixture-language'});
test('Search and topic combine, zero results recover, and filters do not restart the recording',f=>{
  const frame=current(f), count=f.requests.length;
  f.search.value=' RIVER '; f.search.event('input'); assert.deepEqual(f.visible().map(x=>x.id),['fixture-river']);
  f.topic.value='language'; f.topic.event('change'); assert.equal(f.visible().length,0); assert.equal(f.empty.hidden,false);
  f.clear.event('click'); assert.equal(f.visible().length,11); assert.equal(f.empty.hidden,true);
  assert.equal(f.requests.length,count); assert.equal(f.currentFrames()[0],frame);
});
test('Selecting another playable card directly replaces the ready player without stacking',f=>{
  const previous=current(f); f.selects[3].event('click'); current(f,'pbs','3067357496');
  assert.equal(previous.parentElement,null); assert.equal(f.requests.length,2);
});
test('Close destroys the player and the reload control restores exactly one paused player',f=>{
  current(f); f.close.event('click'); assert.equal(f.currentFrames().length,0);
  f.load.event('click'); current(f); f.load.event('click'); assert.equal(f.currentFrames().length,1);
});
test('A nonembedded selection destroys the previous player and exposes its official destination',f=>{
  current(f); const count=f.requests.length; f.selects[1].event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
  f.load.event('click'); assert.equal(f.currentFrames().length,0);
  assert.equal(f.ids.theaterWatch.href,'https://publisher.example.test/words');
});
test('Returning to an embeddable card prepares it directly, with autoplay disabled',f=>{
  f.selects[1].event('click'); f.selects[0].event('click'); current(f);
});
test('Malformed YouTube IDs fail closed without new provider requests',f=>{
  const count=f.requests.length; f.selects[2].event('click'); f.load.event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
});
test('Malformed PBS IDs fail closed without new provider requests',f=>{
  const count=f.requests.length; f.selects[4].event('click'); f.load.event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
});
test('Unapproved player providers never inherit approved CSP capabilities',f=>{
  const count=f.requests.length; f.selects[5].event('click'); f.load.event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
});
test('Still is reversible without viewer storage or restarting the ready player',f=>{
  const frame=current(f), count=f.requests.length;
  f.motion.event('click'); assert(still(f),'Still state disables ambient framing');
  assert.equal(f.motion.getAttribute('aria-pressed'),'true');
  f.motion.event('click'); assert(!still(f),'Viewer may restore ambient motion when OS permits it');
  assert.equal(f.motion.getAttribute('aria-pressed'),'false');
  assert.equal(f.currentFrames()[0],frame); assert.equal(f.requests.length,count);
});
test('OS reduced motion starts Still and cannot be overridden into ambient animation',f=>{
  assert(still(f)); assert.equal(f.motion.getAttribute('aria-pressed'),'true');
  f.motion.event('click'); assert(still(f));
},{reduced:true});
test('A runtime OS reduced-motion change immediately stops ambient motion',f=>{
  f.reduce(true); assert(still(f)); assert.equal(f.motion.getAttribute('aria-pressed'),'true');
});
test('A reviewed Vimeo ID uses only the approved player origin without autoplay',f=>{
  f.selects[6].event('click'); current(f,'vimeo','141218300');
});
test('A malformed Vimeo identifier never becomes a player URL',f=>{
  const count=f.requests.length; f.selects[7].event('click'); f.load.event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
});
test('A reviewed NFB slug uses the exact publisher embed route',f=>{
  f.selects[8].event('click'); current(f,'nfb','birth_of_a_family');
});
test('NFB path traversal cannot escape into an arbitrary frame destination',f=>{
  const count=f.requests.length; f.selects[9].event('click'); f.load.event('click');
  assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,count);
});
test('Publisher-provided PBS viralplayer route disables both known autoplay switches',f=>{
  f.selects[10].event('click'); current(f,'pbs','3109669877','viralplayer');
});
test('Sitewide Still is honored on entry and cannot be overridden locally',f=>{
  assert(still(f)); f.motion.event('click'); assert(still(f));
},{globalStill:true});
test('A runtime sitewide Still change immediately stops the frame animation',f=>{
  f.globalStill(true); assert(still(f)); assert.equal(f.motion.getAttribute('aria-pressed'),'true');
});
test('Sitewide Calm keeps the geometric frame static without locally enabling it',f=>{
  assert(still(f)); f.motion.event('click'); assert(still(f));
},{calm:true});
const passed=results.filter(row=>row.result==='PASS').length;
console.log(JSON.stringify({version:2,passed,total:results.length,results,scope:'Actual enhancement script in an independent fictional DOM. Not a real browser, network playback, layout or accessibility certification.'},null,2));
if(passed!==results.length) process.exitCode=1;
