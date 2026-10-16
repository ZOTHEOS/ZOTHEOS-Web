/* Independent prebuild contract against the real enhancement script.
   Fictional DOM only; no playback, browser, licensing or source certification. */
const assert = require('node:assert/strict');
const {fixture} = require('./theater-story-access-fixture.cjs');
const results = [];
function test(name, fn, options={}) {
  try { const f=fixture(options); f.init(); fn(f); assert.deepEqual(f.blocked,[]); results.push({name,pass:true}); }
  catch(error) { results.push({name,pass:false,error:error.message}); }
}
const id = card => card.dataset.theaterFilm;
const visible = f => f.visible().map(id);
function selected(f, wanted) {
  const card=f.cards.find(c=>id(c)===wanted); assert(card,'Fixture record exists');
  assert.equal(f.ids.theaterTitle.textContent,card.dataset.title);
  assert.deepEqual(f.selects.filter(b=>b.getAttribute('aria-pressed')==='true').map(b=>b.dataset.theaterSelect),[wanted]);
  return card;
}
function oneReady(f) {
  assert.equal(f.currentFrames().length,1);
  const frame=f.currentFrames()[0], u=new URL(frame.src);
  assert.equal(u.searchParams.get('autoplay'),'0');
  assert(!String(frame.allow).split(';').some(x=>/^\s*autoplay\b/.test(x)));
  return frame;
}
function storyLink(f,wanted) {
  const u=new URL(f.permalink.href,'https://zotheos.org');
  assert.equal(u.origin,'https://zotheos.org'); assert.equal(u.pathname,'/theater');
  assert.equal(u.search,''); assert.equal(u.hash,'#film-'+wanted);
}
function noStartupDisturbance(f) {
  assert.equal(f.location.hash,f.initialHash,'Startup must preserve the exact incoming fragment');
  assert.equal(f.location.search,f.initialSearch,'Startup must preserve unrelated query parameters');
  assert.equal(f.location.href,f.initialHref,'Startup must preserve the full URL');
  assert.deepEqual(f.historyWrites,[],'Reading an incoming link must never replace or push browser history');
  assert.deepEqual(f.focuses,[],'Initial selection must not steal keyboard focus');
  assert.deepEqual(f.scrolls,[],'Initial selection must not trigger scripted scrolling');
}

test('A direct story link selects the exact source-backed record on startup', f=>{
  selected(f,'fixture-vimeo'); const frame=oneReady(f);
  assert.equal(new URL(frame.src).hostname,'player.vimeo.com');
  assert.equal(f.requests.length,1,'Do not contact a featured provider before resolving the incoming story');
  noStartupDisturbance(f); storyLink(f,'fixture-vimeo');
},{hash:'#film-fixture-vimeo'});
test('Direct stories preserve unrelated query parameters and do not serialize viewer filters',f=>{
  selected(f,'fixture-vimeo');noStartupDisturbance(f);const href=f.location.href;
  f.search.value='coast voice';f.search.event('input');assert.equal(f.location.href,href);
  f.selects[3].event('click');assert.equal(f.location.href,href);assert.deepEqual(f.historyWrites,[]);
},{hash:'#film-fixture-vimeo',search:'?ref=official-source&mode=reading'});
test('Deep links beyond page one reveal the cited card while preserving normal page batches',f=>{
  selected(f,'fixture-extra-199'); assert.equal(f.cards[199].hidden,false);
  assert.equal(f.visible().length,200); oneReady(f); noStartupDisturbance(f);
},{hash:'#film-fixture-extra-199',total:200});
test('A direct source-only story has honest fallback and no substituted provider',f=>{
  selected(f,'fixture-language'); assert.equal(f.currentFrames().length,0); assert.equal(f.requests.length,0);
  assert.equal(f.ids.theaterWatch.href,'https://publisher.example.test/words');
  assert(f.playerStatus.textContent.includes(f.cards[1].dataset.availability));
  storyLink(f,'fixture-language'); noStartupDisturbance(f);
},{hash:'#film-fixture-language'});
for(const hash of ['', '#collection','#screening','#film-no-such-record','#film-__proto__','#film-constructor',
  '#film-','##film-fixture-vimeo','#film-fixture-vimeo/extra','#film-fixture-vimeo?autoplay=1',
  '#film-fixture-vimeo%00','#film-%3Cscript%3E','#film-%E0%A4%A','#film-%252E%252E',
  '#film-javascript:alert(1)']) test('Unknown or hostile fragment safely keeps the feature: '+JSON.stringify(hash),f=>{
    selected(f,'fixture-river'); oneReady(f); noStartupDisturbance(f);
  },{hash});
test('A later native hash navigation updates the one selected frame without history recursion',f=>{
  const initial=oneReady(f); f.hash('#film-fixture-vimeo'); selected(f,'fixture-vimeo');
  assert.equal(initial.parentElement,null); oneReady(f); storyLink(f,'fixture-vimeo');
  assert.deepEqual(f.historyWrites,[]);
  assert(f.focuses.length>0,'An intentional native story link moves focus into the selected story');
});
test('Native non-story and unknown fragment navigation leaves a later chosen story intact',f=>{
  f.selects[6].event('click');const frame=oneReady(f);const count=f.requests.length;
  for(const hash of ['#collection','#screening','#film-no-such-record','#film-%E0%A4%A']) {
    f.hash(hash); selected(f,'fixture-vimeo');assert.equal(oneReady(f),frame);
    assert.equal(f.requests.length,count);assert.deepEqual(f.historyWrites,[]);
  }
});
test('Malformed hash changes keep the current story rather than losing viewer context',f=>{
  const initial=oneReady(f); f.hash('#film-%E0%A4%A'); selected(f,'fixture-river');
  assert.equal(oneReady(f),initial); assert.deepEqual(f.historyWrites,[]);
});
test('Explicit story selection updates a native shareable story link',f=>{
  const initial=oneReady(f); f.selects[6].event('click'); selected(f,'fixture-vimeo');
  assert.equal(initial.parentElement,null); oneReady(f); storyLink(f,'fixture-vimeo');
  assert.deepEqual(f.historyWrites,[],'Normal poster selection must not write browser history');
  assert.equal(f.location.hash,'','Normal poster selection must not rewrite the URL');
});
for(const modifier of ['ctrlKey','metaKey','shiftKey','altKey']) test('Modified native poster '+modifier+' remains a normal official source link',f=>{
  f.selects[6].tagName='A'; const initial=oneReady(f), count=f.requests.length;
  f.selects[6].event('click',{[modifier]:true}); selected(f,'fixture-river');
  assert.equal(oneReady(f),initial); assert.equal(f.requests.length,count); assert.deepEqual(f.historyWrites,[]);
});
test('Ordinary selection preserves an existing incoming fragment and only updates its story link',f=>{
  f.selects[6].event('click'); selected(f,'fixture-vimeo'); storyLink(f,'fixture-vimeo');
  assert.equal(f.location.hash,'#film-fixture-river'); assert.deepEqual(f.historyWrites,[]);
},{hash:'#film-fixture-river'});
test('Watch Here is based on valid provider URLs rather than truthy or hostile metadata',f=>{
  f.access.value='watch-here'; f.access.event('change');
  assert.deepEqual(visible(f),['fixture-river','fixture-pbs','fixture-vimeo','fixture-nfb','fixture-pbs-viral']);
  assert.equal(f.next.disabled,false);
});
test('Official Site includes unset, unknown and malformed players without implying free access',f=>{
  f.access.value='official-site'; f.access.event('change');
  assert.deepEqual(visible(f),['fixture-language','fixture-invalid','fixture-pbs-invalid','fixture-provider-invalid','fixture-vimeo-invalid','fixture-nfb-invalid']);
  for(const c of f.visible()) assert.equal(c.dataset.availability,'Official source; access and regional availability may change.');
});
test('Availability joins topic, region, viewing type and all search words with AND',f=>{
  f.access.value='watch-here'; f.topic.value='land'; f.region.value='oceania';
  f.kind.value='full-film'; f.search.value='coast voice'; f.access.event('change');
  assert.deepEqual(visible(f),['fixture-pbs']); assert.equal(f.next.disabled,true);
});
test('Availability filtering alone preserves the current screening selection and focus',f=>{
  const initial=oneReady(f), focusCount=f.focuses.length;
  f.access.value='official-site'; f.access.event('change');
  assert.equal(oneReady(f),initial); selected(f,'fixture-river'); assert.equal(f.focuses.length,focusCount);
});
test('Availability filter uses 24-card pagination without preloading matches',f=>{
  const count=f.requests.length; f.access.value='watch-here'; f.access.event('change');
  assert.equal(f.visible().length,24); assert.equal(f.more.hidden,false); assert.equal(f.requests.length,count);
  f.more.event('click'); assert.equal(f.visible().length,48); assert.equal(f.requests.length,count);
},{total:200});
test('Next Story traverses only Watch Here matches and starts at the first when filtered out',f=>{
  f.access.value='watch-here'; f.access.event('change'); const order=visible(f);
  for(let i=1;i<=order.length;i++){ f.next.event('click'); selected(f,order[i%order.length]); oneReady(f); }
});
test('Next Story on Official Site destroys the old player and preserves the selected source',f=>{
  const initial=oneReady(f); f.access.value='official-site'; f.access.event('change'); f.next.event('click');
  selected(f,'fixture-language'); assert.equal(initial.parentElement,null); assert.equal(f.currentFrames().length,0);
  storyLink(f,'fixture-language');
});
test('Zero access matches disable Next without changing the screening room',f=>{
  const initial=oneReady(f); f.access.value='official-site'; f.search.value='not-present'; f.search.event('input');
  assert.deepEqual(visible(f),[]); assert.equal(f.next.disabled,true); assert.equal(f.empty.hidden,false); assert.equal(oneReady(f),initial);
});
test('Clear Filters resets access and all existing facets without changing selection',f=>{
  const initial=oneReady(f); f.access.value='official-site'; f.topic.value='language';f.region.value='oceania'; f.kind.value='official-page';
  f.search.value='words'; f.access.event('change'); f.clear.event('click');
  for(const input of [f.access,f.topic,f.region,f.kind]) assert.equal(input.value,'all');
  assert.equal(f.search.value,''); assert.equal(f.visible().length,11); assert.equal(oneReady(f),initial);
  assert.equal(f.document.activeElement,f.search);
});
test('Next Story beyond the first access page reveals the correct card without autoplay',f=>{
  f.access.value='watch-here';f.access.event('change');
  const eligible=f.cards.filter(c=>!['fixture-language','fixture-invalid','fixture-pbs-invalid','fixture-provider-invalid','fixture-vimeo-invalid','fixture-nfb-invalid'].includes(id(c)));
  for(let i=0;i<24;i++)f.next.event('click'); selected(f,id(eligible[24]));
  assert.equal(eligible[24].hidden,false); assert.equal(f.visible().length,48); oneReady(f);
},{total:200});
test('Automatic completion events still cannot navigate to another story',f=>{
  const initial=oneReady(f), count=f.requests.length; initial.event('ended'); f.player.event('ended');
  f.message({event:'finish'},'https://player.vimeo.com'); selected(f,'fixture-river');
  assert.equal(oneReady(f),initial); assert.equal(f.requests.length,count); assert.deepEqual(f.historyWrites,[]);
});
console.log(JSON.stringify({scope:'Independent real-script prebuild checks. No browser or playback certification.',passed:results.filter(r=>r.pass).length,total:results.length,results},null,2));
if(results.some(r=>!r.pass))process.exitCode=1;
