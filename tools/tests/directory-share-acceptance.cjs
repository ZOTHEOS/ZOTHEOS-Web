/* Link To This Search acceptance. Fictional records and DOM hooks only; the filter, URL reading and link
   writing come from the actual directory script. This is not a browser, device or assistive-technology test. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const allSource = fs.readFileSync(process.argv[2] || require('node:path').resolve(__dirname, '../nations/partials/appearance.js'), 'utf8');
const marker = "(function () {\n  var input = document.getElementById('directoryQuery')";
assert(allSource.includes(marker), 'Actual directory script must be available');
const source = allSource.slice(allSource.indexOf(marker));
function fixture({search = '', hash = '', shareHref = '/nations/directory#directoryNames', shareControl = true, deferTimers = false} = {}) {
  const ids = {}, winListeners = {}, focus = [], scroll = [], timers = [], historyCalls = [];
  class El {
    constructor(id, attrs = {}, className = '') { this.id = id; this.attrs = attrs; this.className = className; this.children = []; this.hidden = false; this.events = {}; this.textContent = ''; this.value = ''; this.checked = false; if (id) ids[id] = this; }
    add(child) { child.parent = this; this.children.push(child); return child; }
    getAttribute(key) { return key === 'href' ? this.href : this.attrs[key] || null; }
    setAttribute(key, value) { if (key === 'href') this.href = String(value); else this.attrs[key] = value; }
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
  const doc = new El('document');
  const tools = doc.add(new El('directoryTools')); tools.hidden = true;
  const input = tools.add(new El('directoryQuery')), clear = tools.add(new El('directoryClear'));
  const inventory = tools.add(new El('directoryInventory'));
  inventory.options = [{value: 'all', textContent: 'All source inventories'}, {value: 'us-directory', textContent: 'US federal snapshot'}, {value: 'other-directory', textContent: 'Other source category'}]; inventory.value = 'all';
  Object.defineProperty(inventory, 'selectedIndex', {get() { return this.options.findIndex(x => x.value === this.value); }});
  const profiles = tools.add(new El('directoryProfilesOnly')), hint = tools.add(new El('directoryProfileHint')); hint.hidden = true;
  const status = tools.add(new El('directoryResult'));
  let share;
  if (shareControl) { share = tools.add(new El('directoryShareLink')); share.href = shareHref; }
  const more = doc.add(new El('directoryMore')); more.hidden = true; const limitNote = doc.add(new El('directoryLimit'));
  const list = doc.add(new El('directoryNames')), nav = doc.add(new El('nav', {}, 'directory-inventory-nav'));
  const intro = list.add(new El('directoryResultsIntro')); intro.hidden = true;
  const summary = intro.add(new El('directoryResultsSummary')), empty = intro.add(new El('directoryResultsEmpty')); empty.hidden = true;
  const a = list.add(new El('us-directory', {'data-directory-inventory': 'us-directory'}, 'directory-group'));
  const b = list.add(new El('other-directory', {'data-directory-inventory': 'other-directory'}, 'directory-group'));
  const records = [];
  for (let j = 0; j < 103; j++) {
    const name = j === 0 ? 'Southern Ute Indian Tribe' : j === 1 ? 'Ute Mountain Ute Tribe' : j === 2 ? 'San Juan Southern Paiute Tribe' : j === 51 ? 'Ute Source Record' : j === 101 ? 'Ute Pending Record' : 'Fictional Source Record ' + j;
    const row = (j < 50 ? a : b).add(new El('entry-' + j, {'data-directory-name': name, 'data-directory-profile': (j !== 2 && j < 92) ? 'ready' : 'pending'}));
    row.add(new El('name-' + j, {}, 'directory-name'));
    records.push(row);
  }
  const jumps = [nav.add(new El('jump-a')), nav.add(new El('jump-b'))]; jumps[0].href = '#us-directory'; jumps[1].href = '#other-directory';
  const docListeners = {};
  const document = {addEventListener(type, fn) { (docListeners[type] ||= []).push(fn); }, getElementById(id) { return ids[id] || null; }, querySelectorAll(selector) { return selector === '.directory-inventory-nav a' ? jumps : doc.querySelectorAll(selector); }};
  const location = {hash, search};
  const window = {location, addEventListener(type, fn) { (winListeners[type] ||= []).push(fn); }, requestAnimationFrame(fn) { fn(); },
    setTimeout(fn) { if (deferTimers) timers.push(fn); else fn(); },
    history: {pushState() { historyCalls.push('push'); }, replaceState() { historyCalls.push('replace'); }}};
  return {input, clear, inventory, profiles, hint, status, share, more, list, intro, summary, empty, tools, records, jumps, focus, scroll, timers, historyCalls, location,
    init() { vm.runInNewContext(source, {document, window}); },
    shown() { return records.filter(x => !x.hidden).map(x => x.id); },
    type(value) { this.input.value = value; this.input.event('input'); },
    hashChange(value) { location.hash = value; for (const fn of winListeners.hashchange || []) fn(); },
    // Back/Forward inside one document: the fragment changes with no link activation.
    traverse(value) { this.hashChange(value); },
    // In-page link activation: click is dispatched before the fragment navigation, as in a browser.
    activateOnly(value, props = {}, attrs = {}) { const link = {getAttribute(name) { return name === 'href' ? value : Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null; }, closest() { return this; }}; for (const fn of docListeners.click || []) fn({button: 0, target: link, ...props}); },
    followLink(value) { this.activateOnly(value); if (location.hash !== value) this.hashChange(value); },
    pageshow(persisted) { for (const fn of winListeners.pageshow || []) fn({persisted}); }};
}
function query(href) {
  assert(href.startsWith('/nations/directory'), 'Link stays on the directory path: ' + href);
  assert(href.endsWith('#directoryNames'), 'Generated links use the neutral results fragment: ' + href);
  const q = href.indexOf('?');
  return q < 0 ? '' : href.slice(q + 1, href.indexOf('#'));
}
function reopen(href, options = {}) {
  const at = href.indexOf('?'), hashAt = href.indexOf('#');
  return fixture({...options, search: at < 0 ? '' : href.slice(at, hashAt), hash: href.slice(hashAt)});
}

const outcomes = [];
function check(name, action) {
  try { action(); outcomes.push({name, passed: true}); }
  catch (error) { outcomes.push({name, passed: false, error: error.message}); }
}

check('Without the script the link stays inside hidden tools and every record stays visible', () => {
  const f = fixture({search: '?q=ute'});
  assert.equal(f.tools.hidden, true); assert.equal(f.shown().length, 103); assert.equal(f.share.getAttribute('href'), '/nations/directory#directoryNames');
});
check('Link follows query, inventory and ready filters without touching history', () => {
  const f = fixture(); f.init();
  assert.equal(f.share.getAttribute('href'), '/nations/directory#directoryNames');
  for (const value of ['U', 'Ut', 'Ute', 'Ute ', 'Ute M']) f.type(value);
  assert.equal(query(f.share.getAttribute('href')), 'q=Ute%20M');
  f.inventory.value = 'other-directory'; f.inventory.event('change');
  f.profiles.checked = true; f.profiles.event('change');
  assert.equal(query(f.share.getAttribute('href')), 'q=Ute%20M&inventory=other-directory&ready=1');
  f.clear.event('click');
  assert.equal(query(f.share.getAttribute('href')), 'inventory=other-directory&ready=1');
  f.profiles.checked = false; f.profiles.event('change'); f.inventory.value = 'all'; f.inventory.event('change');
  assert.equal(f.share.getAttribute('href'), '/nations/directory#directoryNames');
  assert.deepEqual(f.historyCalls, []); assert.equal(f.location.search, ''); assert.equal(f.location.hash, '');
});
check('Entered text is percent-encoded so it cannot change the link structure', () => {
  const f = fixture(); f.init(); f.type('  <b>&ready=1#x "Ute"  ');
  const href = f.share.getAttribute('href');
  assert.equal(query(href), 'q=%3Cb%3E%26ready%3D1%23x%20%22Ute%22');
  assert.doesNotMatch(href, /[<>" ]/);
});
check('A shared link restores all filters, counts and the reading position', () => {
  const origin = fixture(); origin.init(); origin.type('ute'); origin.inventory.value = 'other-directory'; origin.inventory.event('change');
  origin.profiles.checked = true; origin.profiles.event('change');
  const f = reopen(origin.share.getAttribute('href')); f.init();
  assert.equal(f.input.value, 'ute'); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.profiles.checked, true);
  assert.deepEqual(f.shown(), ['entry-51']); assert.equal(f.hint.hidden, false); assert.equal(f.tools.hidden, false);
  assert.match(f.status.textContent, /^Search restored from this link\. 1 of 1 matching name records with reviewed profile links shown in Other source category\.$/);
  assert.equal(f.summary.textContent, f.status.textContent); assert.equal(f.share.getAttribute('href'), origin.share.getAttribute('href'));
  assert.equal(f.scroll.at(-1), 'directoryNames'); assert.deepEqual(f.focus, []);
});
check('Restored filters keep Show More batches', () => {
  const f = fixture({search: '?ready=1'}); f.init();
  assert.equal(f.shown().length, 40); assert.match(f.status.textContent, /40 of 91/); assert.equal(f.more.hidden, false);
  f.more.event('click'); assert.equal(f.shown().length, 80); assert.equal(f.profiles.checked, true);
});
check('A zero-result shared query is restored and announced with recovery guidance', () => {
  const f = fixture({search: '?q=Nonexistent%20fictional', hash: '#directoryNames'}); f.init();
  assert.equal(f.input.value, 'Nonexistent fictional'); assert.deepEqual(f.shown(), []);
  assert.match(f.status.textContent, /^Search restored from this link\. 0 of 0 matching name records/);
  assert.match(f.status.textContent, /Try another spelling/); assert.equal(f.empty.hidden, false); assert.equal(f.more.hidden, true);
});
check('The restored message is a later live-region change and yields to newer input', () => {
  const f = fixture({search: '?q=ute', deferTimers: true}); f.init();
  assert.equal(f.timers.length, 1); assert.doesNotMatch(f.status.textContent, /restored/);
  f.timers[0](); assert.match(f.status.textContent, /^Search restored from this link\. 4 of 4/);
  const g = fixture({search: '?q=ute', deferTimers: true}); g.init(); g.type('southern'); g.timers[0]();
  assert.doesNotMatch(g.status.textContent, /restored/); assert.match(g.status.textContent, /^2 of 2/);
});
check('Legacy record and inventory fragments keep precedence over search parameters', () => {
  const f = fixture({search: '?q=apache&inventory=us-directory&ready=1', hash: '#entry-101'}); f.init();
  assert.equal(f.input.value, ''); assert.equal(f.profiles.checked, false); assert.equal(f.inventory.value, 'other-directory');
  assert.equal(f.records[101].hidden, false); assert.equal(f.scroll.at(-1), 'entry-101'); assert.doesNotMatch(f.status.textContent, /restored/);
  assert.equal(query(f.share.getAttribute('href')), 'inventory=other-directory');
  const g = fixture({search: '?q=ute&ready=1', hash: '#us-directory'}); g.init();
  assert.equal(g.input.value, ''); assert.equal(g.profiles.checked, false); assert.equal(g.inventory.value, 'us-directory'); assert.equal(g.shown().length, 40);
  const legacy = fixture({hash: '#entry-101'}); legacy.init(); assert.equal(legacy.records[101].hidden, false); assert.equal(legacy.inventory.value, 'other-directory');
});
check('Inventory jumps after a restored search still reset filters and refresh the link', () => {
  const f = fixture({search: '?q=ute&ready=1', hash: '#directoryNames'}); f.init();
  f.jumps[0].event('click'); f.hashChange('#us-directory');
  assert.equal(f.input.value, ''); assert.equal(f.profiles.checked, false); assert.equal(query(f.share.getAttribute('href')), 'inventory=us-directory');
});
check('Unknown, malformed, duplicate and oversized parameters are handled safely', () => {
  const unknown = fixture({search: '?utm_source=x&page=2'}); unknown.init();
  assert.equal(unknown.shown().length, 40); assert.doesNotMatch(unknown.status.textContent, /restored|recognized/);
  const bad = fixture({search: '?q=%E0%A4%A&inventory=constructor&ready=yes'}); bad.init();
  assert.equal(bad.input.value, ''); assert.equal(bad.inventory.value, 'all'); assert.equal(bad.profiles.checked, false);
  assert.match(bad.status.textContent, /^Search restored from this link\. Some link settings were not recognized and were left out\. 40 of 103/);
  const partly = fixture({search: '?q=ute+mountain&q=apache&inventory=nowhere'}); partly.init();
  assert.equal(partly.input.value, 'ute mountain'); assert.equal(partly.inventory.value, 'all'); assert.deepEqual(partly.shown(), ['entry-1']);
  assert.match(partly.status.textContent, /not recognized/);
  const long = fixture({search: '?q=' + 'a'.repeat(201)}); long.init(); assert.equal(long.input.value, ''); assert.match(long.status.textContent, /not recognized/);
  const max = fixture({search: '?q=' + 'a'.repeat(200)}); max.init(); assert.equal(max.input.value.length, 200); assert.doesNotMatch(max.status.textContent, /not recognized/);
  const huge = fixture({search: '?q=ute&pad=' + 'x'.repeat(3000)}); huge.init(); assert.equal(huge.input.value, ''); assert.equal(huge.shown().length, 40);
  assert.match(huge.status.textContent, /not recognized/);
  const markup = fixture({search: '?q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E'}); markup.init();
  assert.equal(markup.input.value, '<img src=x onerror=alert(1)>'); assert.doesNotMatch(markup.status.textContent, /<img/);
});
check('An unsafe generated base path disables link rewriting instead of pointing off-site', () => {
  for (const shareHref of ['//elsewhere.example/x#directoryNames', 'https://elsewhere.example/#directoryNames', '/\\elsewhere.example#directoryNames']) {
    const f = fixture({shareHref}); f.init(); f.type('ute'); assert.equal(f.share.getAttribute('href'), shareHref); assert.deepEqual(f.shown(), ['entry-0', 'entry-1', 'entry-51', 'entry-101']);
  }
});
check('Older markup without the link still restores and filters', () => {
  const f = fixture({shareControl: false, search: '?q=ute'}); f.init(); assert.equal(f.input.value, 'ute'); assert.equal(f.shown().length, 4);
});
function state(f) { return {q: f.input.value, inventory: f.inventory.value, ready: f.profiles.checked, shown: f.shown(), href: f.share.getAttribute('href')}; }
check('History: Back to a shared URL after an inventory jump restores its q and ready and the default inventory; Forward reapplies the jump', () => {
  const f = fixture({search: '?q=ute&ready=1', hash: '#directoryNames'}); f.init();
  const shared = state(f); assert.deepEqual(shared.shown, ['entry-0', 'entry-1', 'entry-51']);
  f.jumps[0].event('click'); f.hashChange('#us-directory');
  assert.equal(f.input.value, ''); assert.equal(f.profiles.checked, false); assert.equal(f.inventory.value, 'us-directory');
  f.traverse('#directoryNames'); assert.deepEqual(state(f), shared);
  assert.equal(query(f.share.getAttribute('href')), 'q=ute&ready=1');
  f.traverse('#us-directory'); assert.equal(f.inventory.value, 'us-directory'); assert.equal(f.input.value, ''); assert.equal(f.profiles.checked, false);
});
check('History: Back to the default no-parameter URL restores every default, including inventory', () => {
  const f = fixture(); f.init();
  f.jumps[1].event('click'); f.hashChange('#other-directory'); assert.equal(f.inventory.value, 'other-directory');
  f.traverse(''); assert.equal(f.inventory.value, 'all'); assert.equal(f.input.value, ''); assert.equal(f.profiles.checked, false);
  assert.equal(f.shown().length, 40); assert.equal(f.share.getAttribute('href'), '/nations/directory#directoryNames');
  const g = fixture({hash: '#directoryNames'}); g.init(); g.type('ute'); g.profiles.checked = true; g.profiles.event('change');
  g.inventory.value = 'other-directory'; g.inventory.event('change'); g.followLink('#directoryQuery');
  g.traverse('#directoryNames'); assert.deepEqual([g.input.value, g.inventory.value, g.profiles.checked], ['', 'all', false]);
});
check('History: a later-page legacy record entry still wins, and Back returns to the URL search', () => {
  const f = fixture({search: '?q=ute&inventory=us-directory', hash: '#directoryNames'}); f.init();
  f.traverse('#entry-101');
  assert.equal(f.records[101].hidden, false); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.input.value, ''); assert.equal(f.shown().length, 53);
  f.traverse('#directoryNames'); assert.deepEqual(f.shown(), ['entry-0', 'entry-1']); assert.equal(f.inventory.value, 'us-directory');
  const g = fixture({search: '?q=ute', hash: '#entry-101'}); g.init(); assert.equal(g.records[101].hidden, false); assert.equal(g.input.value, '');
  g.traverse(''); assert.equal(g.input.value, 'ute'); assert.equal(g.inventory.value, 'all');
});
check('In-page results, adjustment and skip links keep edited filters; Show More and Clear are unchanged', () => {
  const f = fixture({search: '?q=ute', hash: '#directoryNames'}); f.init();
  f.inventory.value = 'other-directory'; f.inventory.event('change'); f.type('ute source'); f.profiles.checked = true; f.profiles.event('change');
  const edited = state(f); assert.deepEqual(edited.shown, ['entry-51']);
  for (const hash of ['#directoryQuery', '#main', '#directoryNames']) { f.followLink(hash); assert.deepEqual(state(f), edited, hash); }
  assert.equal(query(f.share.getAttribute('href')), 'q=ute%20source&inventory=other-directory&ready=1');
  f.clear.event('click'); assert.equal(f.input.value, ''); assert.equal(f.inventory.value, 'other-directory'); assert.equal(f.profiles.checked, true);
  f.followLink('#directoryQuery'); assert.equal(f.profiles.checked, true); assert.equal(f.inventory.value, 'other-directory');
  f.profiles.checked = false; f.profiles.event('change'); f.more.event('click'); assert.equal(f.shown().length, 53); f.followLink('#directoryNames'); assert.equal(f.shown().length, 53);
  assert.deepEqual(f.historyCalls, []);
});
check('Restoration from the back-forward cache, and malformed fragments, follow the URL safely', () => {
  const f = fixture({search: '?inventory=us-directory'}); f.init(); f.type('ute'); f.inventory.value = 'other-directory'; f.inventory.event('change');
  assert.equal(f.inventory.getAttribute('autocomplete'), 'off'); assert.equal(f.profiles.getAttribute('autocomplete'), 'off');
  f.pageshow(false); assert.equal(f.inventory.value, 'other-directory');
  f.pageshow(true); assert.equal(f.inventory.value, 'us-directory'); assert.equal(f.input.value, '');
  f.type('ute'); f.traverse('#%'); assert.equal(f.input.value, 'ute');
});
check('Modified, canceled and new-context activations cannot poison a later Back restoration', () => {
  const activations = [
    {name: 'Ctrl', props: {ctrlKey: true}}, {name: 'Meta', props: {metaKey: true}},
    {name: 'Shift', props: {shiftKey: true}}, {name: 'Alt', props: {altKey: true}},
    {name: 'non-primary synthetic click', props: {button: 1}},
    {name: 'canceled click', props: {defaultPrevented: true}},
    {name: 'new tab target', attrs: {target: '_blank'}},
    {name: 'download', attrs: {download: ''}}
  ];
  for (const activation of activations) {
    const f = fixture({search: '?q=ute&ready=1', hash: '#directoryNames'}); f.init();
    const shared = state(f);
    f.jumps[0].event('click'); f.hashChange('#us-directory');
    // These clicks do not navigate the current document. The next event models a genuine Back traversal.
    f.activateOnly('#directoryNames', activation.props, activation.attrs);
    f.traverse('#directoryNames');
    assert.deepEqual(state(f), shared, activation.name);
  }
});
console.log(JSON.stringify({fixtureOnly: true, browserOrDeviceCertification: false, outcomes}, null, 2));
if (outcomes.some(x => !x.passed)) process.exitCode = 1;
