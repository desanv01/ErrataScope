import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'compositions');
fs.mkdirSync(out, {recursive:true});
const esc = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const scenes = [
 {id:'intro', duration:8, type:'title'},
 {id:'workspace',duration:18,file:'01-workspace.mp4',in:12,title:'From manufacturer errata to a reviewable draft',caption:'Two selected ES0620 entries. Source evidence stays beside the interpretation.'},
 {id:'provenance',duration:8,file:'01-workspace.mp4',in:30,type:'focus',crop:[1165,195,405,220],title:'An actual NVIDIA model result',headline:'Nemotron, via Token Factory.',body:'nvidia/Nemotron-3.5-Super-VL',detail:'Interprets selected source excerpts through the Nebius API.',caption:'This demo replays the recorded response. It does not make a new inference call.'},
 {id:'citations',duration:28,file:'02-citations.mp4',in:4,title:'Follow a claim back to its source',caption:'Click a citation: the corresponding entry and source excerpt come into view.'},
 {id:'unknowns',duration:8,file:'03-unknowns.mp4',in:4,type:'focus',crop:[1165,350,405,260],title:'Preserve what the source does not establish',headline:'Unknown stays unknown.',body:'Affected device. Exception.',detail:'Missing information remains explicitly unresolved.',caption:'Null or unknown is not false. Human review cannot manufacture missing evidence.'},
 {id:'coverage',duration:14,file:'03-unknowns.mp4',in:12,title:'Keep the limits visible',caption:'2 supported of 53 detected entries. The inventory is incomplete; unselected entries are not assessed.'},
 {id:'review',duration:13,file:'04-review.mp4',in:4,title:'Record a human source review',caption:'A required note records the reviewer’s observations and remaining uncertainty.'},
 {id:'history',duration:7,file:'04-review.mp4',in:17,type:'focus',crop:[1165,425,405,325],title:'The decision is retained',headline:'Review. Record. Revisit.',body:'An append-only review history.',detail:'The submitted note remains attached to this interpretation.',caption:'A reviewed interpretation is not an accepted executable rule or an applicability assessment.'},
 {id:'saved-note',duration:5,file:'05-export.mp4',in:10,type:'focus',crop:[1165,585,405,175],title:'The saved note stays in the record',headline:'Your observation is saved.',body:'Review history · revision 2',detail:'The earlier review remains visible alongside the new note.',caption:'A persistent record of observations—not an applicability decision.'},
 {id:'export',duration:14,file:'05-export.mp4',in:4,title:'Take the evidence with you',caption:'Download actual JSON and Markdown summaries: citations, coverage, unknowns and review history.'},
 {id:'synthetic',duration:22,file:'06-synthetic.mp4',in:7,title:'A deliberately incomplete example',badge:'SYNTHETIC / OFFLINE',caption:'Synthetic fixture—not manufacturer evidence. Document identity and revision remain unknown.'},
 {id:'close',duration:7,type:'title'},
];
let t = 0; for (const s of scenes) {s.start=t;t+=s.duration;}
const fonts = `@font-face{font-family:'ES Sans';src:url('assets/fonts/Inter-400.woff2');font-weight:400;}@font-face{font-family:'ES Sans';src:url('assets/fonts/Inter-700.woff2');font-weight:700;}`;
const css = `${fonts}*{box-sizing:border-box}#root{position:absolute;inset:0;width:100%;height:100%;overflow:hidden;background:#0d151c;color:#f8f5ee;font-family:'ES Sans',sans-serif} .top{position:absolute;left:96px;top:40px;width:1180px;font-size:32px;font-weight:700;margin:0;line-height:1.25}.badge{position:absolute;right:96px;top:43px;font-size:28px;color:#65d2f4;letter-spacing:1px}.caption{position:absolute;left:96px;top:1000px;width:1728px;font-size:28px;line-height:1.25;color:#e6e9ed;margin:0}.footage{position:absolute;left:96px;top:114px;width:1728px;height:864px;overflow:hidden;background:#0d151c;border:1px solid #344956}.footage video{position:absolute;width:100%;height:100%;object-fit:contain}.side{position:absolute;left:192px;top:285px;width:700px}.side h2{font-size:64px;line-height:1.1;letter-spacing:-2px;margin:0 0 45px}.side p{font-size:32px;line-height:1.5;margin:0 0 30px;color:#65d2f4}.side .detail{font-size:30px;color:#ced7df}.crop{position:absolute;left:1000px;top:235px;width:824px;height:660px;overflow:hidden;border:1px solid #344956;background:#101920}.crop video{position:absolute;object-fit:fill;max-width:none}.overline{position:absolute;left:192px;top:150px;font-size:28px;letter-spacing:3px;color:#65d2f4}.hero{position:absolute;left:192px;top:260px;width:1500px;margin:0;font-size:148px;font-weight:700;letter-spacing:-7px;line-height:1.1}.hero span{display:inline-block}.subtitle{position:absolute;left:198px;top:460px;font-size:44px;line-height:1.4;width:1400px;color:#f8f5ee;margin:0}.name{position:absolute;left:198px;top:670px;font-size:38px;color:#65d2f4;margin:0}.minor{position:absolute;left:198px;top:740px;font-size:29px;color:#bdc9d2;margin:0;width:1450px}.rule{position:absolute;left:198px;top:605px;width:1350px;height:2px;background:#3c5a6a}.close-title{font-size:112px;letter-spacing:-4px}.close-sub{font-size:40px}.close-link{font-size:39px;color:#65d2f4}.clip{position:absolute;inset:0}`;
for(const s of scenes){
 let html='', anim='';
 if(s.id==='intro'){
  html=`<p class="overline">NVIDIA × NEBIUS · HACKATHON DEMONSTRATION</p><h1 class="hero" id="intro-hero"><span>ErrataScope</span></h1><p class="subtitle" id="intro-sub">Understand the errata.<br />Keep the evidence.</p><div class="rule"></div><p class="name">Desan Vasu</p><p class="minor">A cited interpretation workspace for manufacturer errata.</p>`;
  anim=`tl.fromTo('#intro-hero span',{y:24},{y:0,duration:.55,ease:'power2.out'},0);tl.fromTo('#intro-sub',{opacity:0,y:16},{opacity:1,y:0,duration:.5,ease:'power2.out'},.6);`;
 }else if(s.id==='close'){
  html=`<p class="overline">ERRATASCOPE · LOCAL WORKING DEMO</p><h1 class="hero close-title" id="close-hero">Trace the claim.<br />Keep the unknowns.</h1><p class="subtitle close-sub" style="top:550px">Source citations → human review → portable evidence</p><p class="name close-link" style="top:710px">github.com/desanv01/ErrataScope</p><p class="minor" style="top:790px">Desan Vasu · NVIDIA Nemotron through Nebius Token Factory</p>`;
  anim=`tl.fromTo('#close-hero',{y:18},{y:0,duration:.5,ease:'power2.out'},0);`;
 }else{
  const video=`<video id="${s.id}-video" class="clip" data-start="0" data-duration="${s.duration}" data-media-start="${s.in}" data-track-index="1" src="assets/capture/${s.file}" muted playsinline preload="auto"></video>`;
  if(s.type==='focus'){
   const [x,y,w,h]=s.crop;const k=Math.min(824/w,660/h);const ox=(824-w*k)/2,oy=(660-h*k)/2;
   html=`<div class="side"><h2>${esc(s.headline)}</h2><p>${esc(s.body)}</p><p class="detail">${esc(s.detail)}</p></div><div class="crop" style="height:${h*k}px;top:${235+oy}px">${video.replace('muted',`style="width:${1600*k}px;height:${800*k}px;left:${-x*k+ox}px;top:${-y*k}px" muted`)}</div>`;
  }else html=`<div class="footage">${video}</div>`;
  html+=`<p class="top">${esc(s.title)}</p><span class="badge"${s.badge?' style="color:#edbf65"':''}>${s.badge??'RECORDED LIVE OUTPUT'}</span><p class="caption">${esc(s.caption)}</p>`;
 }
 const doc=`<template><div id="root" data-composition-id="${s.id}" data-duration="${s.duration}" data-width="1920" data-height="1080"><style>${css}</style>${html}<script>const tl=gsap.timeline({paused:true});${anim}window.__timelines['${s.id}']=tl;</script></div></template>`;
 fs.writeFileSync(path.join(out,`${s.id}.html`),doc);
}
const hosts=scenes.map(s=>`<div id="${s.id}" class="clip" data-composition-id="${s.id}" data-composition-src="compositions/${s.id}.html" data-start="${s.start}" data-duration="${s.duration}" data-width="1920" data-height="1080" data-track-index="1" data-track-kind="graphics"></div>`).join('\n');
fs.writeFileSync(path.join(root,'index.html'),`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ErrataScope · Desan Vasu</title><script src="assets/vendor/gsap-3.14.2.min.js"></script><style>html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0d151c}#root{position:absolute;inset:0;width:100%;height:100%}.clip{position:absolute;inset:0}</style></head><body><div id="root" data-composition-id="main" data-duration="${t}" data-width="1920" data-height="1080" data-fps="30">${hosts}</div><script>window.__timelines['main']=gsap.timeline({paused:true});</script></body></html>`);
fs.writeFileSync(path.join(root,'EDIT.json'),JSON.stringify({duration:t,fps:30,scenes},null,2));
console.log(`Built ${scenes.length} scenes, ${t} seconds, ${t*30} frames`);
