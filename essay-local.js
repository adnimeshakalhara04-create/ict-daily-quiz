(()=>{'use strict';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const driveId=v=>{const m=String(v||'').match(/(?:\/d\/|id=)([A-Za-z0-9_-]{20,})/);return m?m[1]:''};
let items=[],shown=[],activeType='all';
function idOf(r){return String(r&&r.driveId||driveId(r&&r.previewUrl)||driveId(r&&r.sourceUrl)||driveId(r&&r.url)||'')}
function lessonOf(r){const n=Number(r&&r.lesson);if(n===1||n===2)return n;const m=String(r&&r.title||'').match(/lesson\s*([12])/i);return m?Number(m[1]):0}
function makeItems(){
  const src=window.SOURCE_QUIZ_DATA||{};
  const essays=Array.isArray(src.essayPages)?src.essayPages:(Array.isArray(src.essays)?src.essays:[]);
  const notes=Array.isArray(src.notes)?src.notes:(Array.isArray(src.theory)?src.theory:[]);
  const essayItems=essays.map((r,i)=>{const lesson=lessonOf(r),page=Number(r.page)||i+1,title=r.title||`Lesson ${lesson} Essay Marking`;return{...r,_type:'essay',_id:`essay-${lesson}-${page}-${i}`,_lesson:lesson,_drive:idOf(r),_label:`${title} — Page ${page}`}});
  const theoryItems=notes.map((r,i)=>{const lesson=lessonOf(r),title=r.title||`Lesson ${lesson} Theory Source ${i+1}`;return{...r,_type:'theory',_id:`theory-${i}`,_lesson:lesson,_drive:idOf(r),_label:title}});
  return [...essayItems,...theoryItems].filter(r=>r._drive&&r._lesson);
}
function essayUrl(r){return`essay_html/${encodeURIComponent(r._drive)}/page-${Number(r.page)||1}.html`}
function theoryUrl(r){return`sources/${encodeURIComponent(r._drive)}.pdf${r.page?`#page=${encodeURIComponent(r.page)}&view=FitH`:''}`}
function goHome(){if(location.hash)history.replaceState(null,'',location.pathname+location.search);location.reload()}
function setHash(v){try{history.pushState({ictSource:v},'',v?`#${v}`:location.pathname+location.search)}catch(_){}}
function openResources(push=true){
  items=makeItems();shown=[...items];activeType='all';
  if(push)setHash('sources');
  const essayCount=items.filter(x=>x._type==='essay').length,theoryCount=items.filter(x=>x._type==='theory').length;
  const app=$('#app');
  app.innerHTML=`<main class="local-res"><div class="lr-wrap"><header class="lr-head"><button class="lr-back" id="lrHome" aria-label="Back home">←</button><div><h1>Essay + Theory Sources</h1><p>Lesson 1 & 2 original sources • local Vercel reader</p></div><span class="lr-badge">${essayCount} ESSAY • ${theoryCount} THEORY</span></header><section class="lr-summary"><div><strong>${essayCount}</strong><span>Essay pages</span></div><div><strong>${theoryCount}</strong><span>Theory documents</span></div><div><strong>${items.length}</strong><span>Total local sources</span></div></section><div class="lr-tools"><input id="lrSearch" inputmode="search" placeholder="Search title, lesson or page…"><select id="lrLesson"><option value="0">All lessons</option><option value="1">Lesson 1</option><option value="2">Lesson 2</option></select><div class="lr-tabs" role="group" aria-label="Source type"><button class="lr-tab on" data-type="all">All</button><button class="lr-tab" data-type="essay">Essay</button><button class="lr-tab" data-type="theory">Theory</button></div></div><div class="lr-count" id="lrCount"></div><section class="lr-grid" id="lrGrid"></section></div></main>`;
  $('#lrHome').onclick=goHome;
  const apply=()=>{const q=$('#lrSearch').value.trim().toLowerCase(),l=Number($('#lrLesson').value);shown=items.filter(r=>(activeType==='all'||r._type===activeType)&&(!l||r._lesson===l)&&(!q||`${r._label} ${r._type} lesson ${r._lesson} page ${r.page||''}`.toLowerCase().includes(q)));renderGrid()};
  $('#lrSearch').oninput=apply;$('#lrLesson').onchange=apply;
  document.querySelectorAll('.lr-tab').forEach(b=>b.onclick=()=>{activeType=b.dataset.type;document.querySelectorAll('.lr-tab').forEach(x=>x.classList.toggle('on',x===b));apply()});
  renderGrid();
}
function renderGrid(){
  const g=$('#lrGrid'),count=$('#lrCount');if(!g||!count)return;
  const essayVisible=shown.filter(x=>x._type==='essay').length,theoryVisible=shown.filter(x=>x._type==='theory').length;
  count.textContent=`Showing ${shown.length} sources • ${essayVisible} essay • ${theoryVisible} theory`;
  g.innerHTML=shown.length?shown.map((r,i)=>`<button class="lr-card" data-ri="${i}"><div class="lr-card-top"><small>${r._type==='essay'?'ESSAY':'THEORY'} • LESSON ${r._lesson}</small><span>${r._type==='essay'?`PAGE ${esc(r.page)}`:'PDF'}</span></div><h3>${esc(r._label)}</h3><p>${r._type==='essay'?'Original essay marking/source page':'Original theory source document'}</p><b>View inside app →</b></button>`).join(''):`<div class="lr-empty"><strong>No matching source found.</strong><span>Change the lesson, type or search filter.</span></div>`;
  g.querySelectorAll('[data-ri]').forEach(b=>b.onclick=()=>viewSource(shown[Number(b.dataset.ri)]));
}
function peers(r){return items.filter(x=>x._type==='essay'&&x._drive===r._drive).sort((a,b)=>Number(a.page)-Number(b.page))}
function viewSource(r){
  if(!r)return openResources(false);
  setHash(r._type==='essay'?`essay-l${r._lesson}-p${Number(r.page)||1}`:`theory-${r._id}`);
  const app=$('#app');let src,prev=null,next=null;
  if(r._type==='essay'){const ps=peers(r),i=ps.findIndex(x=>x._id===r._id);prev=i>0?ps[i-1]:null;next=i>=0&&i<ps.length-1?ps[i+1]:null;src=essayUrl(r)}else src=theoryUrl(r);
  const note=r._type==='essay'?'Original Essay source page • bundled into this deployment • no Google Drive viewer':'Original Theory PDF • served from this deployment • no Google Drive viewer';
  app.innerHTML=`<main class="local-res reader-mode"><div class="lr-reader"><div class="lr-reader-top"><button id="lrBackList">← Sources</button><div><h2>${esc(r._label)}</h2><p>${r._type==='essay'?`Essay • Lesson ${r._lesson} • Page ${esc(r.page)}`:`Theory • Lesson ${r._lesson}`}</p></div><button id="lrHome2">Home</button></div><div class="lr-source-note">✓ ${esc(note)}</div><div class="lr-frame-shell"><div class="lr-loading" id="lrLoading">Loading source…</div><iframe class="lr-frame" id="lrFrame" loading="eager" src="${esc(src)}" title="${esc(r._label)}"></iframe></div>${r._type==='essay'?`<div class="lr-page-nav"><button id="lrPrev" ${prev?'':'disabled'}>← Previous page</button><span>Page ${esc(r.page)}</span><button id="lrNext" ${next?'':'disabled'}>Next page →</button></div>`:''}</div></main>`;
  $('#lrBackList').onclick=()=>openResources(false);$('#lrHome2').onclick=goHome;
  const frame=$('#lrFrame'),loading=$('#lrLoading');if(frame)frame.addEventListener('load',()=>{if(loading)loading.remove()},{once:true});
  if(prev)$('#lrPrev').onclick=()=>viewSource(prev);if(next)$('#lrNext').onclick=()=>viewSource(next);
}
function bindEssayButton(){const b=$('#res');if(!b||b.dataset.localEssayBound==='1')return;b.dataset.localEssayBound='1';b.onclick=e=>{e.preventDefault();e.stopPropagation();openResources(true)}}
new MutationObserver(bindEssayButton).observe(document.documentElement,{subtree:true,childList:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bindEssayButton);else bindEssayButton();
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('#res');if(!b)return;e.preventDefault();e.stopImmediatePropagation();openResources(true)},true);
window.addEventListener('popstate',()=>{if(location.hash==='#sources')openResources(false);else if(!location.hash)goHome()});
})();