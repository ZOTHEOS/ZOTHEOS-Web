/* Independent user-authorized muted-preview contract. The DOM fixture supplies
   browser primitives, deterministic time, provider packets and visibility only;
   all preview, mute, caption, selection and safety logic is the real script. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const repo=process.argv[2], scenario=process.argv[3];
const html=fs.readFileSync(path.join(repo,'theater.html'),'utf8');
const opening=/<html\b([^>]*)>/i.exec(html)?.[1] || '';
const actualDefault=/data-preview-autoplay=["']([^"']+)/i.exec(opening)?.[1] || 'off';
assert.equal(actualDefault,'on','User selected muted previews; read the real generated production default');
process.argv[2]=path.join(repo,'static/theater/theater.js');
const {fixture}=require('./theater-muted-preview-fixture.cjs');

function setup(opts={}) {
  let clock=100000,serial=1;
  const timers=new Map(), observers=[],packets=[],vibrations=[];
  const timer=(fn,ms,repeat)=>{const id=serial++;timers.set(id,{fn,at:clock+(Number(ms)||0),ms:Number(ms)||0,repeat});return id;};
  const advance=ms=>{const end=clock+ms;let count=0;while(true){let item=null;for(const [id,t] of timers)if(t.at<=end&&(!item||t.at<item[1].at))item=[id,t];if(!item)break;if(++count>10000)throw Error('Unbounded timer loop');clock=item[1].at;timers.delete(item[0]);if(item[1].repeat)timers.set(item[0],{...item[1],at:clock+Math.max(1,item[1].ms)});item[1].fn();}clock=end;};
  const f=fixture({total:70,hash:opts.hash||'',search:opts.search||'',beforeInit({context,window,document,root,El,ids}){
    const proto=El.prototype,append=proto.appendChild;
    proto.appendChild=function(el){if(el.tagName==='IFRAME')el.contentWindow={postMessage(data,origin){let decoded=data;try{if(typeof data==='string')decoded=JSON.parse(data);}catch{}packets.push({data:decoded,origin,frame:el});}};return append.call(this,el);};
    Object.defineProperty(proto,'parentNode',{get(){return this.parentElement;}});
    Object.defineProperty(proto,'childNodes',{get(){return this.children;}});
    Object.defineProperty(proto,'lastElementChild',{get(){return this.children.at(-1)||null;}});
    proto.cloneNode=function(deep){const n=new El(this.tagName,'',{...this.attrs},this.textContent);if(deep)this.children.forEach(c=>n.appendChild(c.cloneNode(true)));return n;};
    proto.insertBefore=function(el,before){if(el.parentElement)el.remove();el.parentElement=this;const i=this.children.indexOf(before);this.children.splice(i<0?this.children.length:i,0,el);return el;};
    proto.getBoundingClientRect=function(){return {top:100,bottom:400,left:10,right:710,width:700,height:300};};
    proto.getClientRects=function(){return [this.getBoundingClientRect()];};
    proto.setAttributeNS=function(_ns,k,v){this.setAttribute(k,v);};
    for(const node of [root,...root.querySelectorAll('*'),document.documentElement]){node.style.setProperty=function(k,v){this[k]=v;};node.style.removeProperty=function(k){delete this[k];};}
    const add=(tag,id,attrs={},text='')=>root.add(new El(tag,id,attrs,text));
    for(const [id,tag] of Object.entries({screening:'section',theaterTransport:'div',theaterStage:'div',theaterScreen:'div',theaterPlay:'button',theaterSound:'button',theaterCC:'button',theaterAnnounce:'p',theaterBack:'a',theaterPublisher:'p',theaterPerspective:'p',theaterPerspectiveRow:'p',theaterYear:'p',theaterYearRow:'div',theaterRuntime:'p',theaterRuntimeRow:'div',theaterLocation:'p',theaterPlaceRow:'div',theaterForm:'p',theaterSources:'ul',theaterThumbCredit:'div','collection-heading':'h2'}))if(!ids[id])add(tag,id,id==='theaterBack'?{href:'#collection'}:{});
    for(const id of ['theaterPlay','theaterSound','theaterCC']){root.removeChild(ids[id]);ids.theaterTransport.appendChild(ids[id]);}
    ids.theaterPlay.setAttribute('data-next','play');ids.theaterBack.textContent='Back To Collection';
    for(const id of ['theaterPlay','theaterSound','theaterCC']){
      ids[id].add(new El('span','',{class:'th-tlabel'},id==='theaterPlay'?'Play':id==='theaterSound'?'Sound':'Captions'));
      ids[id].add(new El('span','',{class:'th-tstate'},''));
    }
    ids['collection-heading'].setAttribute('tabindex','-1');
    root.querySelectorAll('[data-theater-film]').forEach((card,i)=>{
      card.setAttribute('data-preview',opts.hold || 'ok');
      card.setAttribute('data-captions','supplied'); card.setAttribute('data-cap-lang','en');
      card.setAttribute('data-runtime',opts.short?'30s':'10m 0s');
      card.setAttribute('data-publisher','Fictional Publisher '+i);
      // Perspective is public card text in the package, not a manufactured claim.
      const p=card.add(new El('p','', {class:'th-film-perspective'}));p.add(new El('span','',{},'Fictional perspective '+i));
    });
    document.documentElement.setAttribute('data-preview-autoplay',actualDefault);
    document.documentElement.setAttribute('data-motion',opts.motion||'living');
    document.documentElement.setAttribute('data-haptics','off');
    document.hidden=false;document.createTextNode=text=>new El('text','',{},text);
    document.createElementNS=(_ns,tag)=>new El(tag);
    document.hasFocus=()=>true;
    window.innerWidth=opts.phone?390:1440;window.innerHeight=900;
    window.location.origin='https://zotheos.org';
    window.matchMedia=q=>({matches:q.includes('min-width')?!opts.phone:q.includes('reduced-motion')?!!opts.reduced:false,addEventListener(){},addListener(){}});
    class IO{constructor(fn,options){this.fn=fn;this.options=options;this.nodes=[];observers.push(this);}observe(node){this.nodes.push(node);}disconnect(){this.nodes=[];}unobserve(node){this.nodes=this.nodes.filter(n=>n!==node);}}
    if(!opts.noIO)context.IntersectionObserver=window.IntersectionObserver=IO;
    context.setTimeout=(fn,ms)=>timer(fn,ms,false);context.clearTimeout=id=>timers.delete(id);
    context.setInterval=(fn,ms)=>timer(fn,ms,true);context.clearInterval=id=>timers.delete(id);
    context.Date=class extends Date{static now(){return clock;}};
    context.performance={now:()=>clock};
    context.requestAnimationFrame=fn=>{fn(clock);return 1;};context.cancelAnimationFrame=()=>{};
    context.navigator={sendBeacon(){throw Error('No beacon');},vibrate(v){vibrations.push(v);},userActivation:{isActive:false},connection:{saveData:!!opts.saveData,effectiveType:'4g'}};
    context.matchMedia=window.matchMedia;
  }});
  f.init();
  function packet(data,origin,source){for(const fn of f.environment.winEvents.message||[])fn({data,origin,source});}
  function current(){return f.currentFrames()[0];}
  function provider(){return current()?.src.startsWith('https://player.vimeo.com')?'vimeo':'youtube';}
  function ready(){const frame=current();assert(frame);if(provider()==='vimeo'){packet({event:'ready'},'https://player.vimeo.com',frame.contentWindow);packet({method:'getTextTracks',value:[{kind:'captions',language:'en'}]},'https://player.vimeo.com',frame.contentWindow);}else packet({event:'onReady'},'https://www.youtube-nocookie.com',frame.contentWindow);advance(5);}
  function view(id,ratio){let found=false;for(const ob of observers)for(const node of ob.nodes)if(node.id===id || (id==='theaterPlay' && node.id==='theaterTransport')){found=true;ob.fn([{target:node,isIntersecting:ratio>0,intersectionRatio:ratio}]);}assert(found,'Real runtime must observe '+id);advance(1100);}
  function visible(){view('theaterPlay',1);view('theaterScreen',0.6);}
  function reportPlaying(){const frame=current();if(provider()==='vimeo')packet({event:'playing'},'https://player.vimeo.com',frame.contentWindow);else packet({event:'onStateChange',info:1},'https://www.youtube-nocookie.com',frame.contentWindow);advance(5);}
  function count(command){return packets.filter(p=>p.data.func===command||p.data.method===command).length;}
  function assertQuiet(){assert.deepEqual(f.blocked,[]);assert.deepEqual(f.historyWrites,[]);assert.deepEqual(vibrations,[]);assert(f.currentFrames().length<=1);assert(packets.every(p=>['https://www.youtube-nocookie.com','https://player.vimeo.com'].includes(p.origin)));}
  return Object.assign(f,{advance,packets,observers,ready,view,visible,reportPlaying,current,packet,count,assertQuiet,provider});
}

function preview(opts={}){const f=setup(opts);f.ready();f.visible();return f;}
let f;
switch(scenario){
case 'initial-muted':
  f=setup();assert.equal(f.count('playVideo'),0);assert.equal(f.focuses.length,0);assert.equal(new URL(f.current().src).searchParams.get('mute'),'1');f.ready();assert.equal(f.count('playVideo'),0);f.visible();assert.equal(f.count('playVideo'),1);assert(f.count('mute')>=1);assert.equal(f.count('unMute'),0);assert(/(?:^|;)\s*autoplay\b/.test(f.current().allow));break;
case 'viewport-gate':
  f=setup();f.ready();f.view('theaterPlay',1);f.view('theaterScreen',0.599);assert.equal(f.count('playVideo'),0,'Less than 60% does not count');f.view('theaterScreen',0.6);assert.equal(f.count('playVideo'),1);break;
case 'controls-gate':
  f=setup();f.ready();f.view('theaterScreen',0.8);f.view('theaterPlay',0.59);assert.equal(f.count('playVideo'),0);f.view('theaterPlay',1);assert.equal(f.count('playVideo'),1);break;
case 'still':
case 'os-reduced':
  f=preview(scenario==='still'?{motion:'still'}:{reduced:true});assert.equal(f.count('playVideo'),0);break;
case 'no-intersection-observer':
  f=setup({noIO:true});f.ready();f.advance(2000);assert.equal(f.count('playVideo'),0,'Missing visibility support is manual Play, never permission to autoplay');break;
case 'calm':
  f=preview({motion:'calm'});assert.equal(f.count('playVideo'),1,'Calm permits silent preview while frame rests');break;
case 'held-note':case 'held-audio':case 'held-captions':
  f=preview({hold:{'held-note':'hold-note','held-audio':'hold-audio','held-captions':'hold-captions'}[scenario]});assert.equal(f.count('playVideo'),0);break;
case 'source-only':
  f=setup({hash:'#film-fixture-language'});assert.equal(f.currentFrames().length,0);assert.equal(f.requests.length,0);assert.equal(f.packets.length,0);break;
case 'nfb-native':
  f=setup({hash:'#film-fixture-nfb'});assert(f.current().src.startsWith('https://www.nfb.ca/film/'));assert(!/(?:^|;)\s*autoplay\b/.test(f.current().allow),'NFB has no scripted autoplay');assert.equal(f.packets.length,0);for(const id of ['theaterPlay','theaterSound','theaterCC'])assert(f.ids[id].hidden||f.ids[id].disabled||f.ids[id].getAttribute('aria-disabled')==='true',id+' cannot pretend to control native NFB');break;
case 'vimeo-muted':
  f=preview({hash:'#film-fixture-vimeo'});assert.equal(new URL(f.current().src).searchParams.get('muted'),'1');assert.equal(f.count('play'),1);assert(f.packets.some(p=>p.data.method==='setMuted'&&p.data.value===true));assert(!f.packets.some(p=>p.data.method==='setMuted'&&p.data.value===false));break;
case 'manual-pause':
  f=preview();f.reportPlaying();f.ids.theaterPlay.event('click');f.packet({event:'onStateChange',info:2},'https://www.youtube-nocookie.com',f.current().contentWindow);const before=f.count('playVideo');assert(f.count('pauseVideo')>=1);f.view('theaterScreen',0);f.view('theaterScreen',0.9);assert.equal(f.count('playVideo'),before,'Manual Pause persists after return');f.ids.theaterPlay.event('click');assert(f.count('playVideo')>before);break;
case 'out-of-view':
  f=preview();f.reportPlaying();f.view('theaterScreen',0);assert(f.count('pauseVideo')>=1);break;
case 'hidden-tab':
  f=preview();f.reportPlaying();f.document.hidden=true;f.root.event('visibilitychange');assert(f.count('pauseVideo')>=1);break;
case 'phone-cap':case 'desktop-cap':case 'short-desktop-cap':
  f=preview({phone:scenario==='phone-cap',short:scenario==='short-desktop-cap'});f.reportPlaying();f.advance((scenario==='phone-cap'?15:45)*1000);assert(f.count('stopVideo')>=1,'Every untouched automatic preview must stop loading at its cap');break;
case 'origin-reject':case 'source-reject':
  f=setup();f.packet({event:'onReady'},scenario==='origin-reject'?'https://www.youtube-nocookie.com.evil.test':'https://www.youtube-nocookie.com',scenario==='source-reject'?{}:f.current().contentWindow);f.visible();assert.equal(f.count('playVideo'),0,'Forged provider messages cannot make a player ready');break;
case 'sound-gesture':
  f=preview();f.reportPlaying();assert.equal(f.count('unMute'),0);f.environment.context.navigator.userActivation.isActive=true;f.ids.theaterSound.event('click');assert(f.count('unMute')>=1,'Sound must respond to the user control');break;
case 'sound-report-truth':
  f=preview();f.reportPlaying();f.environment.context.navigator.userActivation.isActive=true;f.ids.theaterSound.event('click');assert.notEqual(f.ids.theaterSound.getAttribute('aria-pressed'),'true','Sending unmute is not proof of audible sound');assert.notEqual(f.ids.theaterSound.querySelector('.th-tstate').textContent,'On');f.packet({event:'infoDelivery',info:{muted:false}},'https://www.youtube-nocookie.com',f.current().contentWindow);assert.equal(f.ids.theaterSound.getAttribute('aria-pressed'),'true');break;
case 'caption-off-truth':
  f=preview();f.packet({event:'infoDelivery',info:{captions:{tracklist:[{languageCode:'en'}],track:{languageCode:'en'}}}},'https://www.youtube-nocookie.com',f.current().contentWindow);f.ids.theaterCC.event('click');f.advance(3000);assert.notEqual(f.ids.theaterCC.querySelector('.th-tstate').textContent,'Off','A timer cannot contradict the last active-track report');f.packet({event:'infoDelivery',info:{captions:{track:{}}}},'https://www.youtube-nocookie.com',f.current().contentWindow);assert.equal(f.ids.theaterCC.querySelector('.th-tstate').textContent,'Off');break;
case 'review-query-cannot-override':
  f=setup({motion:'still',hold:'hold-note',search:'?state=trailer&motion=living&theme=maya&ambient=1&story=fixture-vimeo'});f.ready();f.visible();assert.equal(f.count('playVideo'),0);assert.equal(f.cards[0].getAttribute('data-preview'),'hold-note');assert(f.current().src.includes('/abcdefghijk?'));break;
case 'return-focus':
  f=setup();f.more.event('click');f.selects[35].event('click');f.ids.theaterBack.event('click');assert.equal(f.document.activeElement,f.selects[35]);f.search.value='zzqv no results';f.search.event('input');f.ids.theaterBack.event('click');assert.equal(f.document.activeElement,f.ids['collection-heading']);break;
case 'deep-link':
  f=setup({hash:'#film-fixture-vimeo'});assert.equal(f.requests.length,1);assert(f.requests[0].startsWith('https://player.vimeo.com'));assert.equal(f.focuses.length,0);break;
case 'caption-state':
  f=preview();assert(!/\b(?:On|Auto)\b/.test(f.ids.theaterCC.textContent),'Do not claim successful captions before provider report');f.packet({event:'infoDelivery',info:{captions:{tracklist:[{languageCode:'en'}],track:{languageCode:'en'}}}},'https://www.youtube-nocookie.com',f.current().contentWindow);assert(f.ids.theaterCC.getAttribute('aria-pressed')==='true'||/\bOn\b/.test(f.ids.theaterCC.textContent));break;
default:throw Error('Unknown independent scenario '+scenario);
}
f.assertQuiet();
console.log('PASS '+scenario);
