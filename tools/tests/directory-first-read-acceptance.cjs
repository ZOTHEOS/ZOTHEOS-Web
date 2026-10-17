/* Prebuild reader-behavior contract. Neutral DOM hooks, actual production filter code. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const actual=fs.readFileSync(process.argv[2],'utf8');
const marker="(function () {\n  var input = document.getElementById('directoryQuery')";
assert(actual.includes(marker),'Actual directory enhancement must be available.');
const source=actual.slice(actual.indexOf(marker));

function fixture({readControls='both',enhanced=true,hash='#directoryNames'}={}){
  const ids={},listeners={},focus=[],scroll=[];
  class El{
    constructor(id,attrs={},className=''){this.id=id;this.attrs=attrs;this.className=className;this.children=[];this.hidden=false;this.disabled=false;this.events={};this.textContent='';this.value='';this.checked=false;if(id)ids[id]=this;}
    add(child){child.parent=this;this.children.push(child);return child;}
    getAttribute(key){return key==='href'?this.href:this.attrs[key]??null;}
    setAttribute(key,value){this.attrs[key]=String(value);}
    removeAttribute(key){delete this.attrs[key];}
    is(selector){if(selector==='[data-directory-name]:not([hidden])')return 'data-directory-name' in this.attrs&&!this.hidden;if(selector.startsWith('['))return selector.slice(1,-1) in this.attrs;if(selector.startsWith('.'))return this.className.split(' ').includes(selector.slice(1));return false;}
    querySelectorAll(selector){const out=[];function walk(el){for(const child of el.children){if(child.is(selector))out.push(child);walk(child);}}walk(this);return out;}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    closest(selector){for(let el=this;el;el=el.parent)if(el.is(selector))return el;return null;}
    contains(target){for(let el=target;el;el=el.parent)if(el===this)return true;return false;}
    addEventListener(type,fn){(this.events[type]??=[]).push(fn);}
    event(type,props={}){for(const fn of this.events[type]||[])fn.call(this,{button:0,preventDefault(){},...props});}
    focus(){focus.push(this.id);}
    scrollIntoView(){scroll.push(this.id);}
  }
  const doc=new El('document'),input=doc.add(new El('directoryQuery'));
  const status=doc.add(new El('directoryResult')),clear=doc.add(new El('directoryClear'));
  const list=doc.add(new El('directoryNames')),nav=doc.add(new El('nav',{},'directory-inventory-nav'));
  const intro=list.add(new El('directoryResultsIntro'));intro.hidden=true;
  const summary=intro.add(new El('directoryResultsSummary')),empty=intro.add(new El('directoryResultsEmpty'));empty.hidden=true;
  const actions=intro.add(new El('directoryResultsActions'));
  const a=list.add(new El('us-directory',{'data-directory-inventory':'us-directory'},'directory-group'));
  const b=list.add(new El('other-directory',{'data-directory-inventory':'other-directory'},'directory-group'));
  const child=a.add(new El('a-child',{},'directory-group'));
  const records=[];
  for(let i=0;i<103;i++){
    const name=i===0?'Southern Ute Indian Tribe':i===1?'Ute Mountain Ute Tribe':i===2?'San Juan Southern Paiute Tribe':i===51?'Ute Source Record':i===101?'Ute Pending Record':'Fictional Source Record '+i;
    const row=(i<50?child:b).add(new El('entry-'+i,{'data-directory-name':name,'data-directory-profile':i!==2&&i<92?'ready':'pending'}));
    row.add(new El('name-'+i,{},'directory-name')).textContent=name;records.push(row);
  }
  // A nonpublic lookalike outside the reader results must never become a target.
  const held=doc.add(new El('held-record',{'data-directory-name':'Ute Hidden Sentinel'}));held.hidden=true;
  held.add(new El('held-name',{},'directory-name')).textContent='Ute Hidden Sentinel';
  const jumps=[nav.add(new El('jump-a')),nav.add(new El('jump-b'))];jumps[0].href='#us-directory';jumps[1].href='#other-directory';
  let tools,inventory,more,profiles,hint,limit,readFirst,resultsFirst;
  if(enhanced){
    tools=doc.add(new El('directoryTools'));tools.hidden=true;
    inventory=tools.add(new El('directoryInventory'));inventory.value='all';inventory.options=[{value:'all',textContent:'All source inventories'},{value:'us-directory',textContent:'US federal snapshot'},{value:'other-directory',textContent:'Other source category'}];
    Object.defineProperty(inventory,'selectedIndex',{get(){return this.options.findIndex(x=>x.value===this.value);}});
    profiles=tools.add(new El('directoryProfilesOnly'));hint=tools.add(new El('directoryProfileHint'));hint.hidden=true;
    more=doc.add(new El('directoryMore'));more.hidden=true;limit=tools.add(new El('directoryLimit'));
  }
  if(['both','toolbar'].includes(readControls)){readFirst=(tools||doc).add(new El('directoryReadFirst'));readFirst.hidden=true;}
  if(['both','results'].includes(readControls)){resultsFirst=actions.add(new El('directoryResultsReadFirst'));resultsFirst.hidden=true;}
  const document={getElementById(id){return ids[id]||null;},querySelectorAll(selector){return selector==='.directory-inventory-nav a'?jumps:doc.querySelectorAll(selector);}};
  const window={location:{hash},requestAnimationFrame(fn){fn();},addEventListener(type,fn){(listeners[type]??=[]).push(fn);}};
  return {input,status,clear,list,intro,summary,empty,inventory,more,profiles,records,focus,scroll,window,readFirst,resultsFirst,
    init(){vm.runInNewContext(source,{document,window});},shown(){return records.filter(x=>!x.hidden);},
    hashChange(value){window.location.hash=value;for(const fn of listeners.hashchange||[])fn();}};
}
const outcomes=[];
function check(name,action){try{action();outcomes.push({name,passed:true});}catch(error){outcomes.push({name,passed:false,error:error.message});}}
function snapshot(f){return JSON.stringify({query:f.input.value,inventory:f.inventory?.value,ready:f.profiles?.checked,shown:f.shown().map(r=>r.id),status:f.status.textContent,summary:f.summary.textContent,hash:f.window.location.hash,moreHidden:f.more?.hidden,moreText:f.more?.textContent});}
function reading(f,button,expected){
  assert(button,'Reader action must exist.');assert.equal(button.hidden,false,'A nonempty enhanced result offers direct reading.');assert.equal(button.disabled,false);
  const before=snapshot(f);button.event('click');assert.equal(snapshot(f),before,'Reading must preserve filters, visible batch, URL and result truth.');
  assert.equal(f.focus.at(-1),expected);const row=f.records.find(r=>r.children.some(c=>c.id===expected));assert(row&&!row.hidden,'Target is a currently visible public row.');
  const heading=row.querySelector('.directory-name');assert.equal(heading.getAttribute('tabindex'),'-1');assert.equal(f.scroll.at(-1),expected,'The actual name heading is scrolled into view.');
}
for(const action of ['readFirst','resultsFirst']){
  check(action+': initial enhancement reads actual first visible name',()=>{const f=fixture();assert.equal(f[action].hidden,true);f.init();reading(f,f[action],'name-0');});
  check(action+': combined query, source and ready filter determine the target',()=>{const f=fixture();f.init();f.profiles.checked=true;f.profiles.event('change');f.inventory.value='other-directory';f.inventory.event('change');f.input.value='ute';f.input.event('input');reading(f,f[action],'name-51');assert.deepEqual(f.shown().map(r=>r.id),['entry-51']);});
  check(action+': each new query replaces the old reading target',()=>{const f=fixture();f.init();f.input.value='mountain';f.input.event('input');reading(f,f[action],'name-1');f.input.value='ute source';f.input.event('input');reading(f,f[action],'name-51');});
  check(action+': empty results remove the action and cannot focus stale content',()=>{const f=fixture();f.init();reading(f,f[action],'name-0');f.input.value='unmatched';f.input.event('input');assert.equal(f[action].hidden,true);const before=f.focus.length;f[action].event('click');assert.equal(f.focus.length,before);assert.equal(f.shown().length,0);});
  check(action+': pending names stay pending and cannot bypass ready-only selection',()=>{const f=fixture();f.init();f.input.value='pending';f.input.event('input');reading(f,f[action],'name-101');assert.equal(f.records[101].getAttribute('data-directory-profile'),'pending');f.profiles.checked=true;f.profiles.event('change');assert.equal(f[action].hidden,true);const before=f.focus.length;f[action].event('click');assert.equal(f.focus.length,before);assert.equal(f.shown().length,0);});
  check(action+': reading retains an expanded batch; Show More owns progression',()=>{const f=fixture();f.init();f.more.event('click');assert.equal(f.shown().length,80);assert.equal(f.focus.at(-1),'name-40');reading(f,f[action],'name-0');assert.equal(f.shown().length,80);f.more.event('click');assert.equal(f.shown().length,103);assert.equal(f.focus.at(-1),'name-80');});
  check(action+': Clear recovery keeps selected source and ready state',()=>{const f=fixture();f.init();f.profiles.checked=true;f.profiles.event('change');f.inventory.value='other-directory';f.inventory.event('change');f.input.value='unmatched';f.input.event('input');f.clear.event('click');assert.equal(f.input.value,'');assert.equal(f.profiles.checked,true);assert.equal(f.inventory.value,'other-directory');reading(f,f[action],'name-50');});
  check(action+': explicit deep links still reveal their record and reading preserves that state',()=>{const f=fixture();f.init();f.hashChange('#entry-101');assert.equal(f.records[101].hidden,false);reading(f,f[action],'name-50');assert.equal(f.window.location.hash,'#entry-101');});
}
check('Either optional reading position can be absent without disabling the other',()=>{for(const [present,key]of [['toolbar','readFirst'],['results','resultsFirst']]){const f=fixture({readControls:present});f.init();reading(f,f[key],'name-0');}});
check('Legacy markup without reading actions preserves current filtering',()=>{const f=fixture({readControls:'none'});f.init();f.input.value='ute';f.input.event('input');assert.deepEqual(f.shown().map(r=>r.id),['entry-0','entry-1','entry-51','entry-101']);});
check('Incomplete enhancement keeps all static names and hidden reading actions',()=>{const f=fixture({enhanced:false});f.init();assert.equal(f.shown().length,103);assert.equal(f.readFirst.hidden,true);assert.equal(f.resultsFirst.hidden,true);});
console.log(JSON.stringify({checks:outcomes,passed:outcomes.filter(x=>x.passed).length,failed:outcomes.filter(x=>!x.passed).length},null,2));
if(outcomes.some(x=>!x.passed))process.exitCode=1;
