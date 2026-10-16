/* Independent DOM-event contract, not browser geometry certification. No network. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const repo=process.argv[2]||process.env.ZOTHEOS_TEST_REPO||path.resolve(__dirname,'../..');
const shared=fs.readFileSync(path.join(repo,'tools/nations/partials/appearance.js'),'utf8');
const scopedPath=process.argv[3]||path.join(repo,'static/theater/appearance.js');
const scoped=fs.existsSync(scopedPath)?fs.readFileSync(scopedPath,'utf8'):'';
const actual=JSON.parse(fs.readFileSync(process.argv[4]||path.join(__dirname,'actual-output-dom.json'),'utf8'));


function fixture(options={}){
 const ids={},reads=[],writes=[],blocked=[],observers=[],queue=[],events={},scrolls=[];
 let document,media={matches:!!options.reduced,events:[],addEventListener(t,f){this.events.push(f)},addListener(f){this.events.push(f)}};
 function flush(){let n=0;while(queue.length){assert(++n<300,'No unbounded UI loop');queue.shift()()}}
 class El{
  constructor(tag='div',id='',attrs={},text=''){this.tagName=tag.toUpperCase();this.attrs={...attrs};this.children=[];this.parentElement=null;this.events={};this.style={setProperty(k,v){this[k]=v},removeProperty(k){delete this[k]}};this._text=text;this.hidden=false;this.value='';this.disabled=false;this._open=false;if(id){this.attrs.id=id;ids[id]=this}this.rect={left:0,top:0,width:80,height:44};this.dataset=new Proxy({},{get:(_,k)=>this.getAttribute('data-'+String(k).replace(/[A-Z]/g,c=>'-'+c.toLowerCase())),set:(_,k,v)=>{this.setAttribute('data-'+String(k).replace(/[A-Z]/g,c=>'-'+c.toLowerCase()),v);return true}});this.classList={contains:k=>(this.attrs.class||'').split(/\s+/).includes(k),add:k=>{this.attrs.class=((this.attrs.class||'')+' '+k).trim()},remove:k=>{this.attrs.class=(this.attrs.class||'').split(/\s+/).filter(v=>v!==k).join(' ')},toggle:(k,on)=>{on=on===undefined?!this.classList.contains(k):on;on?this.classList.add(k):this.classList.remove(k);return on}};}
  get id(){return this.attrs.id||''}set id(v){this.attrs.id=v;ids[v]=this}get className(){return this.attrs.class||''}set className(v){this.attrs.class=v}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}set textContent(v){this._text=String(v);this.children=[]}get innerText(){return this.textContent}
  getAttribute(k){return Object.hasOwn(this.attrs,k)?this.attrs[k]:null}setAttribute(k,v){const old=this.attrs[k];this.attrs[k]=String(v);if(old!==String(v))for(const o of observers)if(o.target===this&&(!o.opts.attributeFilter||o.opts.attributeFilter.includes(k)))queue.push(()=>o.fn([{target:this,attributeName:k}]))}removeAttribute(k){delete this.attrs[k]}
  get tabIndex(){return Number(this.attrs.tabindex||0)}set tabIndex(v){this.attrs.tabindex=String(v)}get href(){return new URL(this.attrs.href||'', 'https://zotheos.org/theater').href}set href(v){this.attrs.href=String(v)}get src(){return this.attrs.src||''}set src(v){this.attrs.src=String(v)}
  get options(){return this.children}get selectedIndex(){return this.children.findIndex(x=>x.value===this.value)}get firstChild(){return this.children[0]||null}get parentNode(){return this.parentElement}
  appendChild(c){c.remove();c.parentElement=this;this.children.push(c);return c}append(...cs){cs.forEach(c=>this.appendChild(c))}add(c){return this.appendChild(c)}removeChild(c){this.children=this.children.filter(x=>x!==c);c.parentElement=null;return c}replaceChildren(...cs){this.children=[];this._text='';this.append(...cs)}remove(){this.parentElement?.removeChild(this)}contains(e){for(;e;e=e.parentElement)if(e===this)return true;return false}
  matches(s){if(s.includes(','))return s.split(',').some(v=>this.matches(v.trim()));if(s===':popover-open')return this._open;const simple=s.replace(/\[[^\]]*\]/g,'');let m=simple.match(/^[\w-]+/);if(m&&this.tagName!==m[0].toUpperCase())return false;m=simple.match(/#([\w-]+)/);if(m&&this.id!==m[1])return false;for(const c of simple.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(c[1]))return false;for(const a of s.matchAll(/\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\]/g)){const v=this.getAttribute(a[1]);if(v===null||(a[2]!==undefined&&v!==a[2]))return false}if(s.includes(':not')&&s.includes('[hidden]')&&this.hidden)return false;return true}
  querySelectorAll(s){if(s.includes(','))return [...new Set(s.split(',').flatMap(v=>this.querySelectorAll(v.trim())))];if(s.includes(' ')){const parts=s.trim().split(/\s+/);return this.querySelectorAll(parts.pop()).filter(e=>e.parentElement?.closest(parts.join(' ')))}let found=[];for(const c of this.children){if(c.matches(s))found.push(c);found.push(...c.querySelectorAll(s))}return found}querySelector(s){return this.querySelectorAll(s)[0]||null}closest(s){for(let e=this;e;e=e.parentElement)if(e.matches(s))return e;return null}
  addEventListener(t,f){(this.events[t]||=[]).push(f)}dispatchEvent(e){e.target||=this;e.preventDefault||=function(){this.defaultPrevented=true};e.stopPropagation||=function(){this.cancelBubble=true};for(let el=this;el;el=el.parentElement){for(const fn of el.events[e.type]||[])fn.call(el,e);if(e.cancelBubble)break}flush();return !e.defaultPrevented}event(t,extra={}){return this.dispatchEvent({type:t,key:'',button:0,...extra})}
  click(){const accepted=this.event('click');const target=ids[this.getAttribute('popovertarget')];if(accepted&&options.native&&target)target.togglePopover();flush()}
  focus(){const prior=document.activeElement;document.activeElement=this;if(prior&&prior!==this)prior.event('focusout',{relatedTarget:this})}scrollIntoView(){scrolls.push(this.id)}
  getBoundingClientRect(){if(this.hidden)return {left:0,top:0,right:0,bottom:0,width:0,height:0};const r={...this.rect};if(this.id==='appearancePop'){r.width=Math.min(340,Number.parseFloat(this.style.maxWidth)||340);r.height=Math.min(480,Number.parseFloat(this.style.maxHeight)||480);r.left=Number.parseFloat(this.style.left)||0;r.top=Number.parseFloat(this.style.top)||0}return {...r,right:r.left+r.width,bottom:r.top+r.height}}
  get offsetWidth(){return this.getBoundingClientRect().width}get offsetHeight(){return this.getBoundingClientRect().height}get clientWidth(){return this.id==='html'?options.width||1440:this.offsetWidth}get offsetParent(){return this.hidden?null:this.parentElement}getClientRects(){return this.hidden?[]:[this.getBoundingClientRect()]}
  cloneNode(deep){const n=new El(this.tagName,'',{...this.attrs},this._text);n.value=this.value;n.hidden=this.hidden;if(deep)this.children.forEach(c=>n.appendChild(c.cloneNode(true)));return n}
 }
 const html=new El('html','html'),body=html.add(new El('body','body')),main=body.add(new El('main','main',{class:'th-page th-cinema'}));
 document={documentElement:html,body,activeElement:body,hidden:false,readyState:'complete',getElementById:k=>ids[k]||null,querySelector:s=>html.querySelector(s),querySelectorAll:s=>html.querySelectorAll(s),createElement:t=>new El(t),createTextNode:text=>new El('#text','',{},String(text)),addEventListener:(t,f)=>html.addEventListener(t,f)};
 const header=body.add(new El('header','header')),trigger=header.add(new El('button','appearanceBtn',{popovertarget:'appearancePop',type:'button'},'Appearance'));
 trigger.rect={left:options.triggerLeft??700,top:20,width:126,height:44};
 const menu=header.add(new El('button','navMenuBtn',{type:'button',popovertarget:'navSheet'},'Menu'));menu.rect={left:16,top:16,width:96,height:44};
 const sheet=body.add(new El('nav','navSheet')),secondary=sheet.add(new El('button','sheetAppearance',{popovertarget:'appearancePop',type:'button',class:'ns-appearance'},'Appearance'));secondary.rect={left:20,top:650,width:150,height:44};
 const pop=body.add(new El('div','appearancePop',{popover:'',class:'appearance-pop',role:'group'}));
 if(options.native){for(const surface of [pop,sheet]){surface.showPopover=()=>{surface.event('beforetoggle',{newState:'open'});surface._open=true;surface.event('toggle',{newState:'open'})};surface.hidePopover=()=>{surface.event('beforetoggle',{newState:'closed'});surface._open=false;surface.event('toggle',{newState:'closed'})};surface.togglePopover=()=>surface._open?surface.hidePopover():surface.showPopover()}}
 const themeRow=pop.add(new El('div','themeRow')),themes=themeRow.add(new El('div','themeGroup',{class:'theme-picker',role:'radiogroup'}));
 const themeValues=['','maya','codex','skeleton'];const themeButtons=themeValues.map((v,i)=>themes.add(new El('button','theme'+i,{'data-set':v,role:'radio',tabindex:i?' -1':'0','aria-checked':String(!i)})));
 pop.add(new El('span','apThemeName'));pop.add(new El('p','apThemeDescription'));header.add(new El('meta','themeColorMeta'));
 const motionRow=pop.add(new El('div','apMotionRow')),motion=motionRow.add(new El('div','motionGroup',{role:'radiogroup'}));
 const motionButtons=['living','calm','still'].map((v,i)=>motion.add(new El('button','motion'+i,{'data-mode':v,role:'radio',tabindex:i?'-1':'0','aria-checked':String(!i)},v)));
 motionRow.add(new El('p','apMotionNote',{},'Your system asks for reduced motion'));
 const fxRow=pop.add(new El('div','fxAmountRow')),fx=fxRow.add(new El('div','fxAmount',{role:'radiogroup'}));
 const fxButtons=['Light','Medium','Heavy'].map((v,i)=>fx.add(new El('button','fx'+i,{'data-level':String(i),role:'radio',tabindex:i===1?'0':'-1','aria-checked':String(i===1)},v)));
 fxRow.add(new El('p','apFxNote',{},'Applies while Motion is Living'));
 const language=pop.add(new El('a','languageLink',{href:'#site-translation'},'Language And Translation'));pop.add(new El('button','apReturnToFilm',{type:'button'},'Back To The Film'));
 const heading=main.add(new El('header','intro'));heading.add(new El('h1','theater-heading',{},'PUBLIC INTRODUCTION.'));
 const now=main.add(new El('section','screening',{class:'th-screening-layout'}));const title=now.add(new El('h2','theaterTitle',{tabindex:'-1'},'PUBLIC STORY TITLE'));now.add(new El('p','theaterDescription',{},'PUBLIC STORY SUMMARY'));
 now.add(new El('textarea','privateTextarea',{},'PRIVATE_TEXTAREA_SENTINEL'));
 now.add(new El('p','privateHidden',{hidden:''},'PRIVATE_HIDDEN_SENTINEL'));
 now.add(new El('span','privateAria',{'aria-hidden':'true'},'PRIVATE_ARIA_SENTINEL'));
 now.add(new El('iframe','privateProvider',{src:'https://provider.example/'},'PRIVATE_PROVIDER_SENTINEL'));
 now.add(new El('button','privateButton',{},'PRIVATE_BUTTON_SENTINEL'));
 const player=main.add(new El('div','theaterPlayer'));const frame=player.add(new El('iframe','frame',{src:'https://www.youtube-nocookie.com/embed/abcdefghijk?autoplay=0'}));Object.defineProperty(frame,'contentDocument',{get(){throw Error('Do not inspect provider content')}});
 const search=main.add(new El('input','theaterSearch'));search.value='PRIVATE_SEARCH_SENTINEL';
 main.add(new El('section','curation',{},'PUBLIC CURATION. '+('Long public reading. '.repeat(options.longText?600:1))));
 const translation=main.add(new El('details','site-translation'));translation.open=false;translation.add(new El('summary','translationSummary',{tabindex:'-1'},'Language And Translation'));const select=translation.add(new El('select','translateSection'));const textLink=translation.add(new El('a','translateText',{href:'https://translate.google.com/?sl=en&tl=es&op=translate',target:'_blank',rel:'noopener noreferrer'}));translation.add(new El('p','translationNote',{},'Names and meaning can change. Video captions use provider controls.'));
 const external=body.add(new El('button','outside',{},'Outside'));
 const allowed=new Set(['zotheos_landing_theme','zotheos_motion','zotheos_fx','zotheos_rain']);const stored={...options.storage};const storage={getItem(k){assert(allowed.has(k),'No unrelated state read');reads.push(k);if(options.storageBlocked)throw Error('Storage unavailable');return stored[k]??null},setItem(k,v){assert(allowed.has(k),'Only shared appearance preferences may persist');writes.push([k,String(v)]);if(options.storageBlocked)throw Error('Storage unavailable');stored[k]=String(v)}};
 const no=name=>(...args)=>{blocked.push(name);throw Error('No external API '+name)};
 const vv={width:options.width||1440,height:options.height||900,offsetLeft:options.offsetLeft||0,offsetTop:options.offsetTop||0,addEventListener(t,f){(events['vv-'+t]||=[]).push(f)}};
 const window={innerWidth:vv.width,innerHeight:vv.height,visualViewport:vv,matchMedia:()=>media,localStorage:storage,addEventListener(t,f){(events[t]||=[]).push(f)},dispatchEvent(e){for(const f of events[e.type]||[])f(e);flush()},requestAnimationFrame:f=>{queue.push(f);return 1},getComputedStyle:e=>({display:e.hidden?'none':'block',visibility:'visible'})};
 class MutationObserver{constructor(fn){this.fn=fn}observe(target,opts){observers.push({fn:this.fn,target,opts})}disconnect(){}}
 const context={document,window,localStorage:storage,MutationObserver,URL,URLSearchParams,Event:class{constructor(type){this.type=type}},console,
  getComputedStyle:window.getComputedStyle,requestAnimationFrame:window.requestAnimationFrame,setTimeout:f=>{queue.push(f);return 1},clearTimeout(){},
  fetch:no('fetch'),XMLHttpRequest:no('XHR'),WebSocket:no('socket'),Image:no('Image'),navigator:{sendBeacon:no('beacon')},location:{hash:'',href:'https://zotheos.org/theater'},history:{pushState:no('history'),replaceState:no('history')}};

 // Parse-neutral adapter: ONLY data nodes from actual generated HTML are inserted.
 // The fixture blocks network APIs; no provider, inline, or vendor script executes.
 main.replaceChildren();
 function actualNode(raw){
   if(typeof raw==='string')return new El('#text','',{},raw);
   const attrs=Object.fromEntries(Object.entries(raw.attrs).map(([k,v])=>[k,v===null?'':v]));
   const node=new El(raw.tag,attrs.id||'',attrs);
   node.hidden=Object.hasOwn(attrs,'hidden');node.value=attrs.value||'';
   for(const child of raw.children)node.appendChild(actualNode(child));
   return node;
 }
 for(const raw of actual.fragments)main.appendChild(actualNode(raw));
 const actualScreen=ids.screening;
 actualScreen.appendChild(new El('textarea','actualPrivateInput',{},'PRIVATE_INPUT_SENTINEL'));
 actualScreen.appendChild(new El('p','actualPrivateHidden',{hidden:''},'PRIVATE_HIDDEN_SENTINEL'));
 actualScreen.appendChild(new El('p','actualPrivateAria',{'aria-hidden':'true'},'PRIVATE_ARIA_SENTINEL'));
 actualScreen.appendChild(new El('p','actualPrivateEditable',{contenteditable:'true'},'PRIVATE_EDITABLE_SENTINEL'));
 actualScreen.appendChild(new El('button','actualPrivateControl',{},'PRIVATE_CONTROL_SENTINEL'));
 actualScreen.appendChild(new El('script','actualScript',{},'PRIVATE_SCRIPT_SENTINEL'));
 actualScreen.appendChild(new El('style','actualStyle',{},'PRIVATE_STYLE_SENTINEL'));
 const stage=actualScreen.querySelector('.th-stage-col');
 stage.appendChild(new El('p','stageLeakProbe',{},'PLAYER_ONLY_SENTINEL'));
 const actions=actualScreen.querySelector('.th-now-actions');
 actions.appendChild(new El('a','actionsLeakProbe',{href:'#collection'},'ACTION_ONLY_SENTINEL'));
 // A provider subtree must not be read, even accidentally via clone text.
 const provider=ids.theaterPlayer.querySelector('iframe');
 if(provider)Object.defineProperty(provider,'contentDocument',{get(){throw Error('Provider content inspected')}});
 vm.runInNewContext(shared,context,{filename:'shared-appearance.js',timeout:1000});vm.runInNewContext(scoped,context,{filename:scopedPath,timeout:1000});flush();
 return {ids,document,html,pop,trigger,menu,secondary,fxButtons,motionButtons,themeButtons,stored,writes,blocked,player,frame,search,title,translation,select,textLink,language,external,scrolls,window,
  reduced(v){media.matches=v;media.events.forEach(f=>f({matches:v}));flush()},key(el,key){el.focus();el.event('keydown',{key})},click(el){el.click()},event(name){window.dispatchEvent({type:name})},open(){trigger.click()}};
}


const cases=[];function test(name,fn){cases.push([name,fn])}
function f(){return fixture()}
function selected(f,value){const s=f.ids.translateSection;s.value=value;s.event('change');return new URL(f.ids.translateText.href).searchParams.get('text')||''}
function normalized(value){return value.replace(/\s+/g,' ').trim()}
test('actual generated layout has nested masthead and separate stage/action columns',()=>{const x=f();assert(x.ids['theater-heading'].closest('.th-cinema-heading'));assert.equal(x.ids['theater-heading'].parentElement.className,'th-masthead-title');assert(x.ids.screening.querySelector('.th-stage-col'));assert(x.ids.screening.querySelector('.th-now-actions'))});
test('introduction includes actual heading, lede and library scope',()=>{const x=f(),t=selected(x,'introduction-0');let previous=-1;assert(actual.introBlocks.length>=4);for(const block of actual.introBlocks){const at=t.indexOf(block);assert(at>previous,'Actual intro block survives in order: '+block);previous=at}});
test('selected story retains exact visible maker, perspective and Before Watching text',()=>{const x=f(),t=selected(x,'story-0');for(const key of ['theaterTitle','theaterDescription','theaterCredits','theaterPerspective','theaterContentNote'])assert(t.includes(actual.expected[key]),key+' remains exact')});
test('selected story keeps Publisher, Year and Runtime legible with term/value separators',()=>{const x=f(),t=selected(x,'story-0');for(const [label,key]of [['Publisher','theaterPublisher'],['Year','theaterYear'],['Runtime','theaterRuntime']])assert(t.includes(label+' '+actual.expected[key]),label+' needs a separating space')});
test('selected story retains source titles, check dates and thumbnail credit',()=>{const x=f(),t=selected(x,'story-0');assert(actual.sourceTitles.length>0);for(const title of actual.sourceTitles)assert(t.includes(title.replace(' (opens a new tab)','')),'Source title remains exact');for(const date of actual.sourceDates)assert(t.includes('Checked '+date),'Source-check date remains exact');assert(t.includes('Thumbnail Source'));assert(t.includes(actual.expected.theaterThumbCredit.replace('Thumbnail Source (opens a new tab)','').trim()))});
test('selected story excludes all stage, status, Up Next, privacy and story-action text',()=>{const x=f(),t=selected(x,'story-0');for(const bad of ['PLAYER_ONLY_SENTINEL','ACTION_ONLY_SENTINEL','Watch At Your Pace.','Use Play in the player, or open the official source.','Next In This Selection','They receive your IP address and request information.','Back To Collection','Link To This Story'])assert(!t.includes(bad),bad+' is player/UI context, not selected story')});
test('existing private-input, hidden, controls, editable, script and provider boundaries survive',()=>{const x=f(),t=selected(x,'story-0');assert(!t.includes('PRIVATE_'));assert.deepEqual(x.blocked,[]);assert.equal(x.ids.actualPrivateInput.textContent,'PRIVATE_INPUT_SENTINEL');assert.equal(x.search.value,'PRIVATE_SEARCH_SENTINEL')});
test('explicit link activation refreshes current public story without restoring excluded UI',()=>{const x=f();x.ids.theaterTitle.textContent='CHANGED CURRENT STORY';x.ids.translateSection.value='story-0';x.ids.translateText.click();const t=new URL(x.ids.translateText.href).searchParams.get('text');assert(t.includes('CHANGED CURRENT STORY'));assert(!t.includes('PLAYER_ONLY_SENTINEL'));assert(!t.includes('ACTION_ONLY_SENTINEL'));assert(!t.includes('PRIVATE_'))});
test('all actual output translation parts are bounded, explicit, public and inert',()=>{const x=f();assert(x.ids.translateSection.options.length>=3);for(const option of x.ids.translateSection.options){const t=selected(x,option.value),u=new URL(x.ids.translateText.href);assert.equal(u.origin,'https://translate.google.com');assert(t.length>0&&t.length<=4500);assert(!t.includes('PRIVATE_'));}assert.deepEqual(x.blocked,[])});
const results=[];for(const[name,fn]of cases){try{fn();results.push({name,pass:true})}catch(e){results.push({name,pass:false,error:e.message})}}
console.log(JSON.stringify({scope:'Actual generated theater.html fragments; neutral DOM event fixture; no browser geometry or provider playback certification.',html:actual.htmlPin,cases:results,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length},null,2));if(results.some(r=>!r.pass))process.exitCode=1;
