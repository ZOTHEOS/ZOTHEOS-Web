/* Isolated interaction acceptance. The fixture supplies DOM hooks, not the filter algorithm. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const allSource = fs.readFileSync(process.argv[2] || require('node:path').resolve(__dirname, '../nations/partials/appearance.js'), 'utf8');
const marker = "(function () {\n  var input = document.getElementById('directoryQuery')";
assert(allSource.includes(marker), 'Actual directory script must be available');
const source = allSource.slice(allSource.indexOf(marker));
function fixture({enhanced = true, hash = '', profileControl = true} = {}) {
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
  const api = {input, status, clear, list, a, b, childA, tools, inventory, more, limit, profiles, hint, records, jumps, focus, scroll, window, init() { vm.runInNewContext(source, {document, window}); }, shown() { return records.filter(x => !x.hidden); }, hashChange(value) { window.location.hash = value; for (const fn of winListeners.hashchange || []) fn(); }};
  return api;
}

const outcomes = [];
function check(name, action) {
  try { action(); outcomes.push({name, passed: true}); }
  catch (error) { outcomes.push({name, passed: false, error: error.message}); }
}
function ready(f) { f.profiles.checked = true; f.profiles.event('change'); }
function allReady(f) { return f.shown().every(row => row.getAttribute('data-directory-profile') === 'ready'); }
check('Static source names remain available before JS', () => {
  const f = fixture(); assert.equal(f.shown().length,103); assert.equal(f.tools.hidden,true); assert.equal(f.hint.hidden,true);
});
check('Native change filters ready links and discloses count scope', () => {
  const f = fixture();f.init();ready(f);
  assert.equal(f.shown().length,40);assert(allReady(f),'A pending record remains visible in Profiles Ready mode');
  assert.match(f.status.textContent,/40 of 91/);assert.match(f.status.textContent,/with reviewed profile links/i);
  assert.match(f.status.textContent,/\b(?:source|name) records\b/i);assert.doesNotMatch(f.status.textContent,/\bNations\b|canonical profiles/i);
  assert.equal(f.hint.hidden,false);f.profiles.checked=false;f.profiles.event('change');assert.equal(f.hint.hidden,true);
});
check('Query, inventory and ready state combine with AND', () => {
  const f=fixture();f.init();ready(f);f.input.value='ute';f.input.event('input');
  assert.deepEqual(f.shown().map(r=>r.id),['entry-0','entry-1','entry-51']);
  f.inventory.value='other-directory';f.inventory.event('change');
  assert.deepEqual(f.shown().map(r=>r.id),['entry-51']);assert.equal(f.profiles.checked,true);assert.equal(f.a.hidden,true);
});
check('Show More batches and focuses the first newly revealed ready name', () => {
  const f=fixture();f.init();ready(f);f.more.event('click');
  assert.equal(f.shown().length,80);assert(allReady(f));assert.equal(f.focus.at(-1),'name-41');assert.match(f.more.textContent,/11/);
  f.profiles.checked=false;f.profiles.event('change');assert.equal(f.shown().length,40);
  ready(f);assert.equal(f.shown().length,40);assert(allReady(f));
});
check('Clear keeps ready mode and selected source while clearing query', () => {
  const f=fixture();f.init();ready(f);f.inventory.value='other-directory';f.inventory.event('change');f.input.value='ute';f.input.event('input');
  f.clear.event('click');assert.equal(f.input.value,'');assert.equal(f.inventory.value,'other-directory');assert.equal(f.profiles.checked,true);
  assert.equal(f.shown().length,40);assert(allReady(f));assert.match(f.status.textContent,/40 of 42/);assert.equal(f.focus.at(-1),'directoryQuery');
});
check('Explicit source anchor resets ready and query', () => {
  const f=fixture();f.init();ready(f);f.input.value='ute';f.input.event('input');
  f.jumps[0].event('click');f.hashChange('#us-directory');
  assert.equal(f.profiles.checked,false);assert.equal(f.input.value,'');assert.equal(f.inventory.value,'us-directory');
  assert.equal(f.hint.hidden,true);assert.equal(f.records[2].hidden,false);assert.equal(f.focus.at(-1),'directoryInventory');
});
check('Deep row link resets ready and reveals pending target; malformed hash is harmless', () => {
  const f=fixture();f.init();ready(f);f.input.value='ute';f.input.event('input');
  f.hashChange('#%');assert.equal(f.profiles.checked,true);assert.equal(f.input.value,'ute');
  f.hashChange('#entry-101');assert.equal(f.profiles.checked,false);assert.equal(f.input.value,'');assert.equal(f.inventory.value,'other-directory');
  assert.equal(f.records[101].hidden,false);assert.equal(f.scroll.at(-1),'entry-101');assert.equal(f.hint.hidden,true);
  const initial=fixture({hash:'#entry-101'});initial.init();assert.equal(initial.records[101].hidden,false);assert.equal(initial.profiles.checked,false);
});
check('Older markup without checkbox keeps existing browsing', () => {
  const f=fixture({profileControl:false});f.init();assert.equal(f.shown().length,40);f.more.event('click');assert.equal(f.shown().length,80);
  f.input.value='ute';f.input.event('input');assert.deepEqual(f.shown().map(r=>r.id),['entry-0','entry-1','entry-51','entry-101']);
});
check('Legacy unenhanced markup keeps all static names and literal search', () => {
  const f=fixture({enhanced:false,profileControl:false});f.init();assert.equal(f.shown().length,103);
  f.input.value='ute';f.input.event('input');assert.equal(f.shown().length,4);
});
console.log(JSON.stringify({fixtureOnly:true,browserOrDeviceCertification:false,outcomes},null,2));
if (outcomes.some(x=>!x.passed)) process.exitCode=1;
