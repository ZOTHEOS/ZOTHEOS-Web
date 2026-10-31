/* Filter clarity and recovery contract against the real Theater script (UI-THEATER-FILTERS-002).
   Fictional records and a fictional DOM only. Not browser, assistive-technology or playback certification. */
const assert = require('node:assert/strict');
const {fixture} = require('./theater-story-access-fixture.cjs');
const results = [];
const id = card => card.dataset.theaterFilm;
const visible = f => f.visible().map(id);

/* Adds the markup this change renders (theater_build.py) to the shared fictional fixture before the script runs. */
function setup(options = {}) {
  const f = fixture(options);
  const make = (tag, key, attrs = {}, text = '') => {
    const el = f.document.createElement(tag); el.setAttribute('id', key);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    el.textContent = text; f.root.add(el); return el;
  };
  f.topic.options = [{value:'all', textContent:'All Subjects'}, {value:'land', textContent:'Land And Water'}, {value:'language', textContent:'Language'}];
  f.region.options = [{value:'all', textContent:'Worldwide'}, {value:'north-america', textContent:'North America'}, {value:'oceania', textContent:'Oceania'}];
  f.kind.options = [{value:'all', textContent:'Films, Shorts And More'}, {value:'full-film', textContent:'Full Films'}, {value:'official-page', textContent:'Official Pages'}];
  f.toggle = make('button', 'theaterFiltersToggle', {type:'button', 'aria-expanded':'false'}, 'Filters');
  f.count = make('span', 'theaterFilterCount'); f.count.hidden = true;
  f.activeBox = make('div', 'theaterActive'); f.activeBox.hidden = true;
  f.activeList = make('ul', 'theaterActiveList');
  f.emptyText = make('p', 'theaterEmptyText');
  f.clearSearch = make('button', 'theaterClearSearch', {type:'button'}, 'Clear Search'); f.clearSearch.hidden = true;
  f.clearFacets = make('button', 'theaterClearFacets', {type:'button'}, 'Clear Selected Filters'); f.clearFacets.hidden = true;
  f.reset = make('button', 'theaterReset', {type:'button'}, 'Reset Search And Filters'); f.reset.hidden = true;
  /* Fictional accented records; search folding must still match them while choices are removed. */
  f.cards[0].setAttribute('data-search', 'river voices water sovereignty Kanienʼkéha Diné');
  f.cards[6].setAttribute('data-search', 'vimeo recorded conversation Māori whenua');
  if (options.collapsed) for (const el of [f.topic, f.region, f.kind, f.access]) el.getClientRects = () => [];
  return f;
}
function test(name, fn, options = {}) {
  try { const f = setup(options); f.init(); fn(f); assert.deepEqual(f.blocked, []); assert.deepEqual(f.historyWrites, []); results.push({name, pass:true}); }
  catch (error) { results.push({name, pass:false, error:error.stack}); }
}
const text = el => el.children.length ? el.children.map(text).join('') : String(el.textContent || '');
const chips = f => f.activeList.querySelectorAll('[data-facet]');
const chipNames = f => chips(f).map(text);
function choose(f, select, value) { select.value = value; select.event('change'); }
function type(f, value) { f.search.value = value; f.search.event('input'); }
function player(f) {
  assert.equal(f.currentFrames().length, 1, 'Exactly one selected player remains');
  return {frame: f.currentFrames()[0], src: f.currentFrames()[0].src, requests: f.requests.length, title: f.ids.theaterTitle.textContent};
}
function samePlayer(f, before) {
  const now = player(f);
  assert.equal(now.frame, before.frame, 'Filtering and recovery never replace the player frame');
  assert.equal(now.src, before.src); assert.equal(now.requests, before.requests, 'No new provider request');
  assert.equal(now.title, before.title, 'The selected story stays on screen');
}

test('No choices: the selected-filter row and every recovery control start hidden', f => {
  assert.equal(f.activeBox.hidden, true); assert.equal(chips(f).length, 0);
  for (const b of [f.clearSearch, f.clearFacets, f.reset]) assert.equal(b.hidden, true);
});
test('Combined choices are named in order with readable labels and the badge still counts them', f => {
  choose(f, f.topic, 'land'); choose(f, f.region, 'oceania'); choose(f, f.kind, 'full-film'); choose(f, f.access, 'watch-here');
  assert.equal(f.activeBox.hidden, false);
  assert.deepEqual(chipNames(f), ['Remove Subject: Land And Water', 'Remove Region: Oceania', 'Remove Viewing Type: Full Films', 'Remove Where To Watch: Watch Here']);
  for (const b of chips(f)) { assert.equal(b.tagName, 'BUTTON'); assert.equal(b.type, 'button'); }
  assert.equal(f.count.textContent, '4'); assert.equal(f.toggle.getAttribute('aria-label'), 'Filters, 4 set');
  assert.equal(f.toggle.getAttribute('aria-expanded'), 'false', 'Choices never open the folded panel');
});
test('Removing one choice keeps the search and the other choices, recounts and resets paging', f => {
  type(f, 'story'); choose(f, f.topic, 'land'); choose(f, f.region, 'north-america');
  const narrowed = f.status.textContent; assert.match(narrowed, /^Showing 24 of \d+ stories\.$/);
  f.more.event('click'); assert.equal(f.visible().length, 48);
  const before = player(f);
  chips(f)[1].event('click');
  assert.equal(f.search.value, 'story'); assert.equal(f.topic.value, 'land'); assert.equal(f.region.value, 'all');
  assert.deepEqual(chipNames(f), ['Remove Subject: Land And Water']);
  assert.equal(f.visible().length, 24, 'Paging returns to the first page through the shared filter path');
  assert.match(f.status.textContent, /^Removed Region: North America\. Showing 24 of \d+ stories\.$/);
  assert.equal(f.count.textContent, '1');
  samePlayer(f, before);
}, {total: 200});
test('Focus moves to the next remaining choice, then to the visible select, without scrolling', f => {
  choose(f, f.topic, 'land'); choose(f, f.region, 'oceania'); choose(f, f.access, 'watch-here');
  const scrolls = f.scrolls.length;
  chips(f)[0].focus(); chips(f)[0].event('click');
  assert.equal(f.document.activeElement, chips(f)[0]); assert.equal(f.document.activeElement.getAttribute('data-facet'), 'theaterRegion');
  chips(f)[1].event('click');
  assert.equal(f.document.activeElement.getAttribute('data-facet'), 'theaterRegion', 'The last removal falls back to the remaining choice');
  chips(f)[0].event('click');
  assert.equal(chips(f).length, 0); assert.equal(f.activeBox.hidden, true);
  assert.equal(f.document.activeElement, f.region, 'With no choices left, focus lands on the removed choice\'s own visible select');
  assert.equal(f.scrolls.length, scrolls, 'Removal never scrolls the page');
});
test('With the phone panel folded, the last removal focuses the Filters button and the panel stays folded', f => {
  choose(f, f.kind, 'official-page'); chips(f)[0].event('click');
  assert.equal(f.document.activeElement, f.toggle); assert.equal(f.toggle.getAttribute('aria-expanded'), 'false');
}, {collapsed: true});
test('Zero results offer only the relevant recovery: search only, filters only, or both', f => {
  type(f, 'zzzz-not-present');
  assert.deepEqual(visible(f), []); assert.equal(f.empty.hidden, false);
  assert.deepEqual([f.clearSearch.hidden, f.clearFacets.hidden, f.reset.hidden], [false, true, true]);
  assert.match(f.emptyText.textContent, /search/i);
  type(f, ''); choose(f, f.topic, 'language'); choose(f, f.access, 'watch-here');
  assert.deepEqual(visible(f), []);
  assert.deepEqual([f.clearSearch.hidden, f.clearFacets.hidden, f.reset.hidden], [true, false, true]);
  type(f, 'words');
  assert.deepEqual([f.clearSearch.hidden, f.clearFacets.hidden, f.reset.hidden], [false, false, false]);
  assert.equal(f.reset.textContent, 'Reset Search And Filters');
});
test('Clear Search keeps every selected choice and focuses the search box', f => {
  choose(f, f.topic, 'language'); type(f, 'river');
  assert.deepEqual(visible(f), []); const before = player(f);
  f.clearSearch.event('click');
  assert.equal(f.search.value, ''); assert.equal(f.topic.value, 'language');
  assert.deepEqual(visible(f), ['fixture-language']); assert.equal(f.empty.hidden, true);
  assert.deepEqual(chipNames(f), ['Remove Subject: Language']);
  assert.match(f.status.textContent, /^Search cleared\. Selected filters kept\. 1 title in this selection\.$/);
  assert.equal(f.document.activeElement, f.search); samePlayer(f, before);
});
test('Clear Selected Filters keeps an accented search and focuses a visible collection control', f => {
  choose(f, f.access, 'official-site'); type(f, 'MAORI');
  assert.deepEqual(visible(f), []); const before = player(f);
  f.clearFacets.event('click');
  assert.equal(f.search.value, 'MAORI', 'The entered search is never cleared by filter recovery');
  assert.equal(f.access.value, 'all'); assert.deepEqual(visible(f), ['fixture-vimeo']);
  assert.equal(f.activeBox.hidden, true);
  assert.equal(f.document.activeElement, f.topic);
  samePlayer(f, before);
});
test('Clear Selected Filters on a folded phone panel focuses the Filters button', f => {
  choose(f, f.region, 'oceania'); type(f, 'zzzz'); f.clearFacets.event('click');
  assert.equal(f.document.activeElement, f.toggle); assert.equal(f.toggle.getAttribute('aria-expanded'), 'false');
}, {collapsed: true});
test('Accented and unaccented queries match while choices are removed', f => {
  type(f, 'dine'); choose(f, f.region, 'oceania'); assert.deepEqual(visible(f), []);
  chips(f)[0].event('click'); assert.deepEqual(visible(f), ['fixture-river']); assert.equal(f.search.value, 'dine');
  type(f, 'KANIENʼKÉHA'); assert.deepEqual(visible(f), ['fixture-river']);
  type(f, 'Diné'); assert.deepEqual(visible(f), ['fixture-river']);
});
test('Explicit full resets clear both kinds of input from the empty state and the toolbar', f => {
  choose(f, f.topic, 'language'); type(f, 'river'); const before = player(f);
  f.reset.event('click');
  assert.equal(f.search.value, ''); assert.equal(f.topic.value, 'all'); assert.equal(f.visible().length, 11);
  assert.equal(f.document.activeElement, f.search); assert.match(f.status.textContent, /^Search and filters reset\. /);
  choose(f, f.region, 'oceania'); type(f, 'x'); f.clear.event('click');
  assert.equal(f.region.value, 'all'); assert.equal(f.search.value, '');
  samePlayer(f, before);
});
test('Typing never adds a removal note, never writes history and never opens storage', f => {
  choose(f, f.topic, 'land'); chips(f)[0].event('click');
  type(f, 'r'); type(f, 'ri'); type(f, 'riv');
  assert.doesNotMatch(f.status.textContent, /Removed|cleared|reset/);
});
test('Removing a choice never rebuilds chips needlessly or touches the selected story', f => {
  choose(f, f.topic, 'land'); choose(f, f.region, 'oceania');
  const first = chips(f)[0]; type(f, 'story'); assert.equal(chips(f)[0], first, 'Search input leaves the choice buttons in place');
  const before = player(f); chips(f)[1].event('click'); samePlayer(f, before);
});

console.log(JSON.stringify({scope: 'Real-script fictional-DOM checks for filter clarity and recovery. No browser or playback certification.',
  passed: results.filter(r => r.pass).length, total: results.length, results}, null, 2));
if (results.some(r => !r.pass)) process.exitCode = 1;
