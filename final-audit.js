(()=>{'use strict';
const app=document.getElementById('app');
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const driveId=v=>{const m=String(v||'').match(/(?:\/d\/|id=)([A-Za-z0-9_-]{20,})/);return m?m[1]:''};
const BROKEN_LOCAL_PAST=new Set(['1f3DpT3-qcBpEjIRf8CqXK1j4pRd3ObwL','1vHe0dGIHf-wfx2pFZfnLtz4J-qnuREAS']);
let sourceItems=[],shown=[],activeType='all',lastHome=null,lastQuestionKey='';

function lessonOf(r){const n=Number(r&&r.lesson);if(n===1||n===2)return n;const m=String(r&&r.title||'').match(/lesson\s*([12])/i);return m?Number(m[1]):0}
function idOf(r){return String(r&&r.driveId||driveId(r&&r.previewUrl)||driveId(r&&r.sourceUrl)||driveId(r&&r.url)||'')}
function makeSourceItems(){
  const src=window.SOURCE_QUIZ_DATA||{};
  const essays=Array.isArray(src.essayPages)?src.essayPages:(Array.isArray(src.essays)?src.essays:[]);
  const notes=Array.isArray(src.notes)?src.notes:(Array.isArray(src.theory)?src.theory:[]);
  const essayItems=essays.map((r,i)=>{const lesson=lessonOf(r),page=Number(r.page)||i+1,title=r.title||`Lesson ${lesson} Essay Marking`;return{...r,_type:'essay',_lesson:lesson,_drive:idOf(r),_id:`essay-${lesson}-${page}-${i}`,_label:`${title} — Page ${page}`}});
  const theoryItems=notes.map((r,i)=>{const lesson=lessonOf(r),title=r.title||`Lesson ${lesson} Theory Source ${i+1}`;return{...r,_type:'theory',_lesson:lesson,_drive:idOf(r),_id:`theory-${i}`,_label:title}});
  return [...essayItems,...theoryItems].filter(r=>r._drive&&r._lesson);
}
function essayUrl(r){return`essay_html/${encodeURIComponent(r._drive)}/page-${Number(r.page)||1}.html`}
function theoryUrl(r){return`sources/${encodeURIComponent(r._drive)}.pdf${r.page?`#page=${encodeURIComponent(r.page)}&view=FitH`:''}`}
function originalUrl(r){const raw=String(r.previewUrl||r.sourceUrl||r.url||'');return raw||`https://drive.google.com/file/d/${r._drive}/view`}
function setHash(v,replace=false){try{const u=v?`#${v}`:location.pathname+location.search;(replace?history.replaceState:history.pushState).call(history,{ictSource:v},'',u)}catch(_){}}
function goHome(){setHash('',true);location.reload()}

function openSources(push=true){
  sourceItems=makeSourceItems(); shown=[...sourceItems]; activeType='all'; if(push)setHash('sources');
  const e1=sourceItems.filter(x=>x._type==='essay'&&x._lesson===1).length;
  const e2=sourceItems.filter(x=>x._type==='essay'&&x._lesson===2).length;
  const essayCount=e1+e2, theoryCount=sourceItems.filter(x=>x._type==='theory').length;
  app.innerHTML=`<main class="local-res"><div class="lr-wrap"><header class="lr-head"><button class="lr-back" id="faHome" aria-label="Back home">←</button><div><h1>Essay + Theory Sources</h1><p>Lesson 1 & 2 • original source material • in-app reader</p></div><span class="lr-badge">${essayCount} ESSAY • ${theoryCount} THEORY</span></header><section class="lr-summary fa-summary"><button data-quick="essay-1"><strong>${e1}</strong><span>Lesson 1 Essay pages</span></button><button data-quick="essay-2"><strong>${e2}</strong><span>Lesson 2 Essay pages</span></button><button data-quick="theory"><strong>${theoryCount}</strong><span>Theory documents</span></button></section><div class="lr-tools"><input id="faSearch" inputmode="search" autocomplete="off" placeholder="Search title, lesson or page…"><select id="faLesson" aria-label="Filter lesson"><option value="0">All lessons</option><option value="1">Lesson 1</option><option value="2">Lesson 2</option></select><div class="lr-tabs" role="group" aria-label="Source type"><button class="lr-tab on" data-type="all">All</button><button class="lr-tab" data-type="essay">Essay</button><button class="lr-tab" data-type="theory">Theory</button></div></div><div class="lr-count" id="faCount"></div><section class="lr-grid" id="faGrid"></section></div></main>`;
  $('#faHome').onclick=goHome;
  const apply=()=>{const q=$('#faSearch').value.trim().toLowerCase(),l=Number($('#faLesson').value);shown=sourceItems.filter(r=>(activeType==='all'||r._type===activeType)&&(!l||r._lesson===l)&&(!q||`${r._label} ${r._type} lesson ${r._lesson} page ${r.page||''}`.toLowerCase().includes(q)));renderSources()};
  $('#faSearch').oninput=apply; $('#faLesson').onchange=apply;
  $$('.lr-tab').forEach(b=>b.onclick=()=>{activeType=b.dataset.type;$$('.lr-tab').forEach(x=>x.classList.toggle('on',x===b));apply()});
  $$('[data-quick]').forEach(b=>b.onclick=()=>{const v=b.dataset.quick;if(v==='theory'){activeType='theory';$('#faLesson').value='0'}else{activeType='essay';$('#faLesson').value=v.endsWith('1')?'1':'2'};$$('.lr-tab').forEach(x=>x.classList.toggle('on',x.dataset.type===activeType));apply();$('#faGrid').scrollIntoView({behavior:'smooth',block:'start'})});
  renderSources(); window.scrollTo(0,0);
}
function renderSources(){
  const g=$('#faGrid'),count=$('#faCount'); if(!g||!count)return;
  const ev=shown.filter(x=>x._type==='essay').length,tv=shown.filter(x=>x._type==='theory').length;
  count.textContent=`Showing ${shown.length} sources • ${ev} essay • ${tv} theory`;
  g.innerHTML=shown.length?shown.map((r,i)=>`<button class="lr-card" data-src-index="${i}"><div class="lr-card-top"><small>${r._type==='essay'?'ESSAY':'THEORY'} • LESSON ${r._lesson}</small><span>${r._type==='essay'?`PAGE ${esc(r.page)}`:'PDF'}</span></div><h3>${esc(r._label)}</h3><p>${r._type==='essay'?'Original essay question / marking source page':'Original theory source document'}</p><b>View inside app →</b></button>`).join(''):`<div class="lr-empty"><strong>No matching source found.</strong><span>Change the lesson, type or search filter.</span></div>`;
  $$('[data-src-index]',g).forEach(b=>b.onclick=()=>viewSource(shown[Number(b.dataset.srcIndex)]));
}
function peers(r){return sourceItems.filter(x=>x._type==='essay'&&x._drive===r._drive).sort((a,b)=>Number(a.page)-Number(b.page))}
function viewSource(r){
  if(!r)return openSources(false); const src=r._type==='essay'?essayUrl(r):theoryUrl(r); const ps=r._type==='essay'?peers(r):[],i=ps.findIndex(x=>x._id===r._id),prev=i>0?ps[i-1]:null,next=i>=0&&i<ps.length-1?ps[i+1]:null;
  setHash(r._type==='essay'?`essay-l${r._lesson}-p${Number(r.page)||1}`:`theory-${r._id}`);
  app.innerHTML=`<main class="local-res reader-mode"><div class="lr-reader"><div class="lr-reader-top"><button id="faBack">← Sources</button><div><h2>${esc(r._label)}</h2><p>${r._type==='essay'?`Essay • Lesson ${r._lesson} • Page ${esc(r.page)}`:`Theory • Lesson ${r._lesson}`}</p></div><button id="faHome2">Home</button></div><div class="lr-source-note">✓ ${r._type==='essay'?'Original Essay source page • bundled in this deployment':'Original Theory PDF • served from this deployment'}</div><div class="lr-frame-shell"><div class="lr-loading" id="faLoading">Loading source…</div><iframe class="lr-frame" id="faFrame" loading="eager" src="${esc(src)}" title="${esc(r._label)}"></iframe><div class="fa-source-error" id="faError" hidden><strong>Local source failed to open.</strong><a target="_blank" rel="noopener" href="${esc(originalUrl(r))}">Open original source ↗</a></div></div>${r._type==='essay'?`<div class="lr-page-nav"><button id="faPrev" ${prev?'':'disabled'}>← Previous page</button><span>Page ${esc(r.page)} of ${ps.length}</span><button id="faNext" ${next?'':'disabled'}>Next page →</button></div>`:''}</div></main>`;
  $('#faBack').onclick=()=>openSources(false); $('#faHome2').onclick=goHome;
  if(prev)$('#faPrev').onclick=()=>viewSource(prev); if(next)$('#faNext').onclick=()=>viewSource(next);
  const frame=$('#faFrame'),loading=$('#faLoading'); if(frame)frame.addEventListener('load',()=>loading&&loading.remove(),{once:true});
  fetch(src.split('#')[0],{method:'HEAD',cache:'no-store'}).then(res=>{if(!res.ok)throw new Error(String(res.status))}).catch(()=>{const e=$('#faError');if(e)e.hidden=false});
  window.scrollTo(0,0);
}

function patchHome(){
  const home=$('.home'); if(!home)return;
  if(home!==lastHome){lastHome=home;window.scrollTo(0,0)}
  if(home.dataset.finalAuditHome==='1')return;
  home.dataset.finalAuditHome='1';
  const stats=$$('.stats>div',home);
  if(stats.length>=4){
    const rows=[['347','TOTAL MCQ','all question instances'],['22','DAY PAPERS','132 questions'],['23','DAILY QUIZZES','115 questions'],['100','PAST PAPER MCQ','Lesson 1 + 2']];
    stats.slice(0,4).forEach((el,i)=>{el.innerHTML=`<strong>${rows[i][0]}</strong><span>${rows[i][1]}</span><em>${rows[i][2]}</em>`});
  }
  const res=$('#res',home);
  if(res){if(res.textContent!=='Essay + Theory')res.textContent='Essay + Theory';res.setAttribute('aria-label','Open 28 Essay pages and 8 Theory documents')}
  $$('.paper-card',home).forEach(card=>{const h=$('h3',card),c=$('.paper-count',card);if(!h||!c)return;const t=h.textContent.trim();let wanted='';if(t==='Day Papers')wanted='22 papers • 132 Q';else if(t==='Daily Quiz')wanted='23 quizzes • 115 Q';else if(t==='Lesson 1 Past Papers')wanted='44 MCQ';else if(t==='Lesson 2 Past Papers')wanted='56 MCQ';if(wanted&&c.textContent!==wanted)c.textContent=wanted});
}
function patchQuestionScroll(){
  const quiz=$('.quiz'); if(!quiz)return; const key=($('.counter',quiz)?.textContent||'')+'|'+($('.qtitle strong',quiz)?.textContent||'');
  if(key&&key!==lastQuestionKey){const oldCounter=lastQuestionKey.split('|')[0],newCounter=key.split('|')[0];lastQuestionKey=key;if(oldCounter!==newCounter)window.scrollTo(0,0)}
}
function patchProtectedPastPaperFrames(){
  $$('.source-frame').forEach(frame=>{if(frame.dataset.sourceFallback)return;const raw=frame.getAttribute('src')||'';const m=raw.match(/sources\/([A-Za-z0-9_-]+)\.pdf(?:#page=(\d+))?/);if(!m||!BROKEN_LOCAL_PAST.has(m[1]))return;const id=m[1],page=m[2]||'1';frame.dataset.sourceFallback='drive';frame.src=`https://drive.google.com/file/d/${id}/preview#page=${page}`;const card=frame.closest('.pdf-card');const link=card&&$('.source-link',card);if(link)link.href=`https://drive.google.com/file/d/${id}/view`;if(card&&!$('.fa-fallback-note',card)){const n=document.createElement('p');n.className='fa-fallback-note';n.textContent='Protected original PDF • direct source fallback is being used.';card.appendChild(n)}})
}
function audit(){patchHome();patchQuestionScroll();patchProtectedPastPaperFrames()}
let auditScheduled=false;
function scheduleAudit(){if(auditScheduled)return;auditScheduled=true;requestAnimationFrame(()=>{auditScheduled=false;audit()})}
const obs=new MutationObserver(scheduleAudit);obs.observe(app||document.body,{subtree:true,childList:true});scheduleAudit();

document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('#res');if(!b)return;e.preventDefault();e.stopImmediatePropagation();openSources(true)},true);
window.addEventListener('popstate',()=>{if(location.hash==='#sources')openSources(false);else if(location.hash.startsWith('#essay-')||location.hash.startsWith('#theory-'))openSources(false);else if(!location.hash)location.reload()});
})();