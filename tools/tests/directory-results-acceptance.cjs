/* Isolated interaction acceptance. The fixture supplies DOM hooks, not the filter algorithm. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const allSource = fs.readFileSync(process.argv[2] || require('node:path').resolve(__dirname, '../nations/partials/appearance.js'), 'utf8');
const marker = "(function () {\n  var input = document.getElementById('directoryQuery')";
assert(allSource.includes(marker), 'Actual directory script must be available');
const source = allSource.slice(allSource.indexOf(marker));
function fixture({enhanced = true, hash = '', profileControl = true, resultsControl = true} = {}) {
  const ids = {}, winListeners = {}, focus = [], scroll = [];
  class El {
    constructor(id, attrs = {}, className = '') { this.id = id; this.attrs = attrs; this.className = className; this.children = []; this.hidden = false; this.events = {}; this.textContent = ''; this.value = ''; this.checked = false; if (id) ids[id] = this; }
    add(child) { child.parent = this; this.children.push(child); return child; }
    getAttribute(key) { return key === 'href' ? this.href : this.attrs[key] || null; }
    setAttribute(key, value) { this.attrs[key] = value; }
    is(selector) { if (selector === '[data-directory-name]:not([hidden])') return this.attrs['data-directory-name'] && !this.hidden; if (selector.startsWith('[')) return !!this.attrs[selector.slice(1, -1)]; if (selector.startsWith('.')) return this.className.split(' ').includes(selector.slice(1)); return false; }
    querySelectorAll(selector) { const out = []; function walk(el) { for (const child of el.children) { if (child.is(selector)) out.push(child); walk(child); } } walk(this); return out; }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { for (let el = this; el; el = el.parent) if (el.is(selector)) return el; return null; }
    contains(target) { for (let el = target; el; el = el.parent) if (el === this) return true; return false; }
    addEventListener(type, fn) { (this.events[type] ||= []).push(fn); }
    event(type, props = {}) { for (const fn of this.events[type] || []) fn.call(this, {button: 0, preventDefault() {}, ...props}); }
    focus() { focus.push(this.id); }
    scrollIntoView() { scroll.push(this.id); }
  }
  const doc = new El('document'), input = doc.add(new El('directoryQuery'));
  const status = doc.add(new El('directoryResult')), clear = doc.add(new El('directoryClear'));
  const list = doc.add(new El('directoryNames')), nav = doc.add(new El('nav', {}, 'directory-inventory-nav'));
  let intro, summary, empty;
  if (resultsControl) {intro=list.add(new El('directoryResultsIntro'));intro.hidden=true;summary=intro.add(new El('directoryResultsSummary'));empty=intro.add(new El('directoryResultsEmpty'));empty.hidden=true;}
  const a = list.add(new El('us-directory', {'data-directory-inventory': 'us-directory'}, 'directory-group'));
  const b = list.add(new El('other-directory', {'data-directory-inventory': 'other-directory'}, 'directory-group'));
  const childA = a.add(new El('a-child', {}, 'directory-group'));
  const records = [];
  for (let j = 0; j < 103; j++) {
    const name = j === 0 ? 'Southern Ute Indian Tribe' : j === 1 ? 'Ute Mountain Ute Tribe' : j === 2 ? 'San Juan Southern Paiute Tribe' : j === 51 ? 'Ute Source Record' : j === 101 ? 'Ute Pending Record' : 'Fictional Source Record ' + j;
    const row = (j < 50 ? childA : b).add(new El('entry-' + j, {'data-directory-name': name, 'data-directory-profile': (j !== 2 && j < 92) ? 'ready' : 'pending'}));
    row.add(new El('name-' + j, {}, 'directory-name'));
    records.push(row);
  }
  const jumps = [nav.add(new El('jump-a')), nav.add(new El('jump-b'))]; jumps[0].href = '#us-directory'; jumps[1].href = '#other-directory';
  let tools, inventory, more, limit, profiles, hint;
  if (enhanced) {
    tools = doc.add(new El('directoryTools')); tools.hidden = true;
    inventory = doc.add(new El('directoryInventory')); inventory.options = [{value: 'all', textContent: 'All source inventories'}, {value: 'us-directory', textContent: 'US federal snapshot'}, {value: 'other-directory', textContent: 'Other source category'}]; inventory.value = 'all';
    if (profileControl) { profiles = doc.add(new El('directoryProfilesOnly')); hint = doc.add(new El('directoryProfileHint')); hint.hidden = true; }
    Object.defineProperty(inventory, 'selectedIndex', {get() { return this.options.findIndex(x => x.value === this.value); }});
    more = doc.add(new El('directoryMore')); more.hidden = true; limit = doc.add(new El('directoryLimit'));
  }
  const document = {getElementById(id) { return ids[id] || null; }, querySelectorAll(selector) { return selector === '.directory-inventory-nav a' ? jumps : doc.querySelectorAll(selector); }};
  const window = {location: {hash}, addEventListener(type, fn) { (winListeners[type] ||= []).push(fn); }, requestAnimationFrame(fn) { fn(); }};
  const api = {intro, summary, empty, input, status, clear, list, a, b, childA, tools, inventory, more, limit, profiles, hint, records, jumps, focus, scroll, window, init() { vm.runInNewContext(source, {document, window}); }, shown() { return records.filter(x => !x.hidden); }, hashChange(value) { window.location.hash = value; for (const fn of winListeners.hashchange || []) fn(); }};
  return api;
}


const outcomes=[];
function check(name,action){try{action();outcomes.push({name,passed:true});}catch(e){outcomes.push({name,passed:false,error:e.message});}}
function mirrored(f){assert.equal(f.intro.hidden,false,'Results heading must be revealed only after enhancement');assert.equal(f.summary.textContent,f.status.textContent,'Readable results summary must mirror the one original live status');}
function ready(f){f.profiles.checked=true;f.profiles.event('change');}
check('Static names remain visible; results enhancement starts hidden',()=>{let f=fixture();assert.equal(f.shown().length,103);assert.equal(f.intro.hidden,true);assert.equal(f.empty.hidden,true);});
check('Initial bounded results have an adjacent heading and synchronized summary',()=>{let f=fixture();f.init();assert.equal(f.shown().length,40);mirrored(f);assert.equal(f.empty.hidden,true);});
check('Query updates summary; no matches shows guidance and recovery hides it',()=>{let f=fixture();f.init();f.input.value='no such fixture';f.input.event('input');mirrored(f);assert.equal(f.shown().length,0);assert.equal(f.empty.hidden,false);f.input.value='ute';f.input.event('input');mirrored(f);assert.equal(f.shown().length,4);assert.equal(f.empty.hidden,true);});
check('Ready, inventory, query combine; summary mirrors every action',()=>{let f=fixture();f.init();ready(f);mirrored(f);f.inventory.value='other-directory';f.inventory.event('change');mirrored(f);f.input.value='ute';f.input.event('input');mirrored(f);assert.deepEqual(f.shown().map(r=>r.id),['entry-51']);});
check('Clear preserves ready and inventory while updating readable summary',()=>{let f=fixture();f.init();ready(f);f.inventory.value='other-directory';f.inventory.event('change');f.input.value='unmatched';f.input.event('input');f.clear.event('click');mirrored(f);assert.equal(f.profiles.checked,true);assert.equal(f.inventory.value,'other-directory');assert.equal(f.input.value,'');assert.equal(f.empty.hidden,true);assert.match(f.summary.textContent,/40 of 42/);});
check('Show More summary and focus follow newly revealed results',()=>{let f=fixture();f.init();f.more.event('click');mirrored(f);assert.equal(f.shown().length,80);assert.equal(f.focus.at(-1),'name-40');assert.match(f.summary.textContent,/80 of 103/);});
check('Results jump preserves query, source and ready mode',()=>{let f=fixture();f.init();ready(f);f.inventory.value='other-directory';f.inventory.event('change');f.input.value='ute';f.input.event('input');f.hashChange('#directoryNames');mirrored(f);assert.equal(f.profiles.checked,true);assert.equal(f.inventory.value,'other-directory');assert.equal(f.input.value,'ute');assert.deepEqual(f.shown().map(r=>r.id),['entry-51']);});
check('Explicit source and deep-row links update summary and recover hidden records',()=>{let f=fixture();f.init();ready(f);f.input.value='unmatched';f.input.event('input');f.hashChange('#entry-101');mirrored(f);assert.equal(f.empty.hidden,true);assert.equal(f.records[101].hidden,false);f.jumps[0].event('click');f.hashChange('#us-directory');mirrored(f);assert.match(f.summary.textContent,/US federal snapshot/);});
check('Legacy markup without optional results header keeps existing filtering',()=>{let f=fixture({resultsControl:false});f.init();ready(f);f.input.value='ute';f.input.event('input');assert.deepEqual(f.shown().map(r=>r.id),['entry-0','entry-1','entry-51']);assert.match(f.status.textContent,/3 of 3/);});
check('Incomplete toolbar never exposes results enhancement or falsely batches rows',()=>{let f=fixture({enhanced:false});f.init();assert.equal(f.intro.hidden,true);assert.equal(f.shown().length,103);f.input.value='ute';f.input.event('input');assert.equal(f.intro.hidden,true);assert.equal(f.shown().length,4);});
console.log(JSON.stringify({checks:outcomes,passed:outcomes.filter(x=>x.passed).length,failed:outcomes.filter(x=>!x.passed).length},null,2));
if(outcomes.some(x=>!x.passed))process.exitCode=1;
