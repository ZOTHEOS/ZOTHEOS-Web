/* Execute actual early script with no body available: no network, storage writes or provider APIs. */
const fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync(process.argv[2],'utf8'),theme=process.argv[3]||'calavera',reduced=process.argv[4]==='reduce';
const attrs={},reads=[];
const root={setAttribute(k,v){attrs[k]=String(v)},removeAttribute(k){delete attrs[k]},classList:{add(){},remove(){},contains(){return false}}};
const localStorage={getItem(k){reads.push(k);return k==='zotheos_landing_theme'?theme:k==='zotheos_motion'?'living':null},setItem(){throw Error('Prepaint must not persist settings')}};
const CSS={registerProperty(){}};const window={CSS,matchMedia:()=>({matches:reduced})};
const blocked=name=>()=>{throw Error('Unexpected prepaint API '+name)};
try{vm.runInNewContext(code,{document:{documentElement:root,getElementById:()=>null},window,CSS,localStorage,console,fetch:blocked('fetch'),XMLHttpRequest:blocked('XHR'),WebSocket:blocked('socket'),navigator:{sendBeacon:blocked('beacon')}},{timeout:1000});console.log(JSON.stringify({attrs,reads}));}catch(e){console.error(e.stack);process.exitCode=1}
