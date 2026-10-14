/* Isolated interaction acceptance. The fixture supplies DOM hooks, not the filter algorithm. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const allSource = fs.readFileSync(process.argv[2] || require('node:path').resolve(__dirname, '../nations/partials/appearance.js'), 'utf8');
const marker = "(function () {\n  var input = document.getElementById('directoryQuery')";
assert(allSource.includes(marker), 'Actual directory script must be available');
const source = allSource.slice(allSource.indexOf(marker));
function fixture({enhanced = true, hash = ''} = {}) {
  const ids = {}, winListeners = {}, focus = [], scroll = [];
  class El {
    constructor(id, attrs = {}, className = '') { this.id = id; this.attrs = attrs; this.className = className; this.children = []; this.hidden = false; this.events = {}; this.textContent = ''; this.value = ''; if (id) ids[id] = this; }
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
    const name = j === 0 ? 'Southern Ute Indian Tribe' : j === 1 ? 'Ute Mountain Ute Tribe' : j === 2 ? 'San Juan Southern Paiute Tribe' : j === 51 ? 'Ute Source Record' : 'Fictional Source Record ' + j;
    const row = (j < 50 ? childA : b).add(new El('entry-' + j, {'data-directory-name': name}));
    row.add(new El('name-' + j, {}, 'directory-name'));
    records.push(row);
  }
  const jumps = [nav.add(new El('jump-a')), nav.add(new El('jump-b'))]; jumps[0].href = '#us-directory'; jumps[1].href = '#other-directory';
  let tools, inventory, more, limit;
  if (enhanced) {
    tools = doc.add(new El('directoryTools')); tools.hidden = true;
    inventory = doc.add(new El('directoryInventory')); inventory.options = [{value: 'all', textContent: 'All source inventories'}, {value: 'us-directory', textContent: 'US federal snapshot'}, {value: 'other-directory', textContent: 'Other source category'}]; inventory.value = 'all';
    Object.defineProperty(inventory, 'selectedIndex', {get() { return this.options.findIndex(x => x.value === this.value); }});
    more = doc.add(new El('directoryMore')); more.hidden = true; limit = doc.add(new El('directoryLimit'));
  }
  const document = {getElementById(id) { return ids[id] || null; }, querySelectorAll(selector) { return selector === '.directory-inventory-nav a' ? jumps : doc.querySelectorAll(selector); }};
  const window = {location: {hash}, addEventListener(type, fn) { (winListeners[type] ||= []).push(fn); }, requestAnimationFrame(fn) { fn(); }};
  const api = {input, status, clear, list, a, b, childA, tools, inventory, more, limit, records, jumps, focus, scroll, window, init() { vm.runInNewContext(source, {document, window}); }, shown() { return records.filter(x => !x.hidden); }, hashChange(value) { window.location.hash = value; for (const fn of winListeners.hashchange || []) fn(); }};
  return api;
}
let f = fixture();
assert.equal(f.shown().length, 103, 'Before JS every source row is available');
f.init();
assert.equal(f.tools.hidden, false); assert.equal(f.shown().length, 40); assert.match(f.status.textContent, /40 of 103 matching name records/); assert.equal(f.more.textContent, 'Show 40 More'); assert.equal(f.b.hidden, true);
f.input.value = 'ute'; f.input.event('input'); assert.deepEqual(f.shown().map(x => x.id), ['entry-0', 'entry-1', 'entry-51']); assert.equal(f.more.hidden, true); assert.equal(f.a.hidden, false); assert.equal(f.b.hidden, false);
f.input.value = ''; f.inventory.value = 'other-directory'; f.inventory.event('change'); assert.equal(f.shown().length, 40); assert.equal(f.a.hidden, true); assert.equal(f.more.textContent, 'Show 13 More');
f.more.event('click'); assert.equal(f.shown().length, 53); assert.equal(f.focus.at(-1), 'name-90'); assert.equal(f.more.hidden, true);
f.clear.event('click'); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.shown().length, 40); assert.equal(f.focus.at(-1), 'directoryQuery');
f.input.value = 'no such fixture'; f.input.event('input'); assert.equal(f.shown().length, 0); assert.match(f.status.textContent, /0 of 0 matching name records/); assert.equal(f.more.hidden, true);
f.jumps[0].event('click'); f.hashChange('#us-directory'); assert.equal(f.inventory.value, 'us-directory'); assert.equal(f.input.value, ''); assert.equal(f.shown().length, 40); assert.equal(f.focus.at(-1), 'directoryInventory');
f.hashChange('#entry-101'); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.records[101].hidden, false); assert.equal(f.scroll.at(-1), 'entry-101');
f.hashChange('#%'); assert.equal(f.inventory.value, 'other-directory');
f = fixture({hash: '#entry-101'}); f.init(); assert.equal(f.records[101].hidden, false); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.scroll.at(-1), 'entry-101'); assert.equal(f.focus.length, 0);
f = fixture({enhanced: false}); f.init(); assert.equal(f.shown().length, 103); f.input.value = 'ute'; f.input.event('input'); assert.equal(f.shown().length, 3); assert.match(f.status.textContent, /3 of 103 name records/);
console.log('Directory interaction acceptance passed: no-JS source availability, bounded batches, typed scope, Ute/Paiute separation, no results, Show More focus, preserved scope, deep links, chooser focus, malformed hash, legacy fallback.');
