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
function choosePreview(opts={}){
  const f=setup(opts);f.selects[12].event('click');f.ready();f.visible();f.reportPlaying();return f;
}
function commandsForCurrent(f,name){return f.packets.filter(p=>p.frame===f.current()&&(p.data.func===name||p.data.method===name));}
switch(scenario){
case 'poster-desktop-cap':case 'poster-phone-cap':
  f=choosePreview({phone:scenario==='poster-phone-cap'});f.advance((scenario==='poster-phone-cap'?15:45)*1000);
  assert(commandsForCurrent(f,'stopVideo').length>=1,'Choosing a story is still a bounded automatic preview until Play or Sound takeover');break;
case 'poster-offview-pause':
  f=choosePreview();f.view('theaterScreen',0);
  assert(commandsForCurrent(f,'pauseVideo').length>=1,'A chosen preview pauses when its screen leaves view');break;
case 'poster-hidden-tab-pause':
  f=choosePreview();f.document.hidden=true;f.root.event('visibilitychange');
  assert(commandsForCurrent(f,'pauseVideo').length>=1,'A chosen preview pauses in a hidden tab');break;
case 'next-story-remains-capped':
  f=setup();f.selects[12].event('click');f.ready();f.next.event('click');f.ready();f.visible();f.reportPlaying();f.advance(45000);
  assert(commandsForCurrent(f,'stopVideo').length>=1,'Next Story selects a bounded preview; it is not Play');break;
case 'new-poster-preview-is-muted-after-earlier-sound':
  f=preview();f.reportPlaying();f.environment.context.navigator.userActivation.isActive=true;f.ids.theaterSound.event('click');
  f.packet({event:'infoDelivery',info:{muted:false}},'https://www.youtube-nocookie.com',f.current().contentWindow);
  f.selects[12].event('click');f.ready();f.visible();
  assert.equal(commandsForCurrent(f,'unMute').length,0,'Earlier Sound choice must not unmute a newly selected automatic preview');
  assert(commandsForCurrent(f,'mute').length>=1);break;
case 'actual-play-takeover-is-deliberate':
  f=setup({hold:'hold-note'});f.ready();f.ids.theaterPlay.event('click');f.reportPlaying();f.visible();f.advance(45000);
  assert.equal(commandsForCurrent(f,'stopVideo').length,0,'Actual Play takes control from preview cap');
  f.view('theaterScreen',0);assert.equal(commandsForCurrent(f,'pauseVideo').length,0);break;
case 'actual-sound-takeover-is-deliberate':
  f=preview();f.reportPlaying();f.environment.context.navigator.userActivation.isActive=true;f.ids.theaterSound.event('click');
  f.packet({event:'infoDelivery',info:{muted:false}},'https://www.youtube-nocookie.com',f.current().contentWindow);
  f.advance(45000);assert.equal(commandsForCurrent(f,'stopVideo').length,0,'Actual Sound takes control from preview cap');break;
case 'native-play-takeover-is-deliberate':
  f=setup({hold:'hold-note'});f.ready();f.reportPlaying();f.visible();f.advance(45000);
  assert.equal(commandsForCurrent(f,'stopVideo').length,0,'Native provider Play takes control from preview cap');break;
default:throw Error('Unknown story/preview boundary '+scenario);
}
f.assertQuiet();console.log('PASS '+scenario);
