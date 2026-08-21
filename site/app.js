(async () => {
  const root = document.getElementById('app');
  const modal = document.getElementById('modal');

  const REPO = 'adnimeshakalhara04-create/ict-daily-quiz';
  const MANIFEST_URL = `https://raw.githubusercontent.com/${REPO}/main/quiz-data.json`;
  const ASSET_BASE = `https://raw.githubusercontent.com/${REPO}/main/daily_assets`;

  const fallbackAnswers = [
    [3,5,2,3,4],[3,2,2,4,3],[1,1,1,1,1],[3,2,4,1,4],[3,5,3,3,3],
    [2,1,3,2,1],[2,1,2,2,2],[3,3,3,5,3],[3,2,2,2,3],[4,2,3,3,4],
    [1,2,1,1,2],[2,5,2,1,1],[1,3,1,3,1],[5,3,2,3,3],[3,2,2,1,2],
    [2,2,3,2,3],[3,1,3,2,2]
  ];

  let answers = fallbackAnswers;
  try {
    const response = await fetch(`${MANIFEST_URL}?v=${Date.now()}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`manifest HTTP ${response.status}`);
    const manifest = await response.json();
    if (!Array.isArray(manifest.answers) || !manifest.answers.length) throw new Error('manifest answers missing');
    const valid = manifest.answers.every(row => Array.isArray(row) && row.length === 5 && row.every(v => Number.isInteger(v) && v >= 1 && v <= 5));
    if (!valid) throw new Error('manifest answer format invalid');
    answers = manifest.answers;
  } catch (error) {
    console.warn('Daily Quiz manifest fallback:', error);
  }

  const latestQuiz = answers.length;
  const totalQuestions = latestQuiz * 5;
  const data = Array.from({length: latestQuiz}, (_, i) => ({
    number: i + 1,
    title: `QUIZ ${String(i + 1).padStart(2, '0')}`,
    questions: Array.from({length: 5}, (_, j) => ({
      number: j + 1,
      answer: answers[i][j],
      question: `${ASSET_BASE}/questions/quiz-${String(i + 1).padStart(2, '0')}/q-${String(j + 1).padStart(2, '0')}.webp`,
      marking: `${ASSET_BASE}/markings/quiz-${String(i + 1).padStart(2, '0')}/q-${String(j + 1).padStart(2, '0')}.webp`
    }))
  }));

  const KEY = 'ict-daily-quiz-2028-v1';
  let state = {screen:'home', mode:'all', paper:null, index:0, answers:{}, saved:[], zoom:''};
  try { const savedState = JSON.parse(localStorage.getItem(KEY) || 'null'); if (savedState) state = {...state, ...savedState, screen:'home', zoom:''}; } catch {}
  const save = () => localStorage.setItem(KEY, JSON.stringify(state));
  const qkey = (p, q) => `p${p}q${q}`;
  const flat = () => state.mode === 'all' ? data.flatMap(p => p.questions.map(q => ({...q, paper:p.number, title:p.title}))) : state.paper.questions.map(q => ({...q, paper:state.paper.number, title:state.paper.title}));
  const answeredIn = p => p.questions.filter(q => state.answers[qkey(p.number, q.number)] !== undefined).length;

  function startAll() { state.mode='all'; state.paper=null; const questions=data.flatMap(p=>p.questions.map(q=>({...q,paper:p.number}))); const next=questions.findIndex(q=>state.answers[qkey(q.paper,q.number)]===undefined); state.index=next<0?0:next; state.screen='quiz'; save(); render(); scrollTo(0,0); }
  function startPaper(number) { state.mode='paper'; state.paper=data.find(p=>p.number===number); const next=state.paper.questions.findIndex(q=>state.answers[qkey(number,q.number)]===undefined); state.index=next<0?0:next; state.screen='quiz'; save(); render(); scrollTo(0,0); }
  function home() { state.screen='home'; save(); render(); scrollTo(0,0); }
  function choose(number) { const q=flat()[state.index], key=qkey(q.paper,q.number); if(state.answers[key]!==undefined)return; state.answers[key]=number; save(); render(); }
  function nav(delta) { const questions=flat(); state.index=Math.max(0,Math.min(questions.length-1,state.index+delta)); save(); render(); scrollTo(0,0); }
  function toggleSave() { const q=flat()[state.index], key=qkey(q.paper,q.number); state.saved=state.saved.includes(key)?state.saved.filter(x=>x!==key):[...state.saved,key]; save(); render(); }
  function showResults() { state.screen='results'; save(); render(); scrollTo(0,0); }
  function zoom(src) { state.zoom=src; modal.innerHTML=`<div class="modal open"><button data-close>×</button><img src="${src}" alt="Expanded image"></div>`; modal.querySelector('[data-close]').onclick=closeZoom; modal.querySelector('.modal').onclick=e=>{if(e.target===e.currentTarget)closeZoom();}; }
  function closeZoom() { state.zoom=''; modal.innerHTML=''; }
  function attachImageErrors() { root.querySelectorAll('img').forEach(img=>{ img.onerror=()=>{ const box=document.createElement('div'); box.style.cssText='padding:22px;border:1px solid #efabb8;background:#fff0f3;color:#b34459;border-radius:14px;font-weight:700'; box.textContent='Image is still being generated. Refresh in a moment.'; img.replaceWith(box); }; }); }

  function renderHome() {
    root.innerHTML=`<main class="home"><div class="wrap"><header class="header"><div class="brand"><span class="brand-badge">IT</span><span><strong>ICT Daily Quiz</strong><small>2028 QUIZ STUDIO</small></span></div><div class="pill">QUIZ 01–${String(latestQuiz).padStart(2,'0')} · AUTO UPDATED</div></header>
      <section class="hero"><div><p class="eyebrow">Information & Communication Technology</p><h1>Turn every daily quiz<span>into exam-ready practice.</span></h1><p class="lead">Daily Quiz ${latestQuiz}ක ප්‍රශ්න ${totalQuestions}ම original question crop එකෙන් practice කරන්න. පිළිතුර තෝරාගත් පසු එම ප්‍රශ්නයටම අදාළ official marking crop එක බලන්න.</p><div class="actions"><button class="btn primary" data-all>Start all ${totalQuestions} questions →</button></div><div class="stats"><div><strong>${totalQuestions}</strong><span>QUESTIONS</span></div><div><strong>${latestQuiz}</strong><span>DAILY QUIZZES</span></div><div><strong>5</strong><span>CHOICES EACH</span></div></div></div>
      <div class="demo-wrap"><div class="orbit"></div><div class="orbit b"></div><div class="demo"><div class="demo-top"><span>LIVE PRACTICE</span><span>QUIZ 01</span></div><div class="track"><i></i></div><div class="mini">QUESTION 3 OF 5</div><h2>Choose your answer</h2><div class="answers-preview"><span>1</span><span>2</span><span class="on">3</span><span>4</span><span>5</span></div><div class="demo-ok"><b>✓</b><div><strong>Official marking review</strong><small>Exact crop from source</small></div></div></div></div></section>
      <section class="papers"><div class="section-head"><div><p class="eyebrow">DAILY QUIZ MODE</p><h2>QUIZ 01 සිට QUIZ ${String(latestQuiz).padStart(2,'0')} දක්වා</h2></div><p>Quiz එකක් තෝරලා ප්‍රශ්න 5ම එකින් එක practice කරන්න. Progress device එකේම save වෙනවා.</p></div><div class="paper-grid">${data.map(p=>{const a=answeredIn(p),pc=a/5*100;return`<button class="paper-card" data-paper="${p.number}"><div class="paper-top"><span class="paper-number">${String(p.number).padStart(2,'0')}</span><span class="paper-count">5 questions</span></div><h3>${p.title}</h3><div class="paper-progress"><i style="width:${pc}%"></i></div><div class="paper-foot"><span>${a?`${a}/5 completed`:'Not started'}</span><span>↗</span></div></button>`;}).join('')}</div></section>
      <footer class="footer"><span>Source: 2028 ICT Daily Quiz series · Original crops.</span><span>Quiz list updates from the verified GitHub manifest.</span></footer></div></main>`;
    root.querySelector('[data-all]').onclick=startAll;
    root.querySelectorAll('[data-paper]').forEach(button=>button.onclick=()=>startPaper(Number(button.dataset.paper)));
  }

  function renderQuiz() {
    const questions=flat(), q=questions[state.index], key=qkey(q.paper,q.number), picked=state.answers[key], done=picked!==undefined, correct=q.answer, saved=state.saved.includes(key), pct=(state.index+1)/questions.length*100;
    root.innerHTML=`<main class="quiz"><header class="quiz-header"><button class="icon" data-home>←</button><div class="qtitle"><small>${state.mode==='all'?'ALL QUIZZES':'QUIZ MODE'}</small><strong>${q.title}</strong></div><div class="counter">${state.index+1}/${questions.length}</div></header><div class="top-progress"><i style="width:${pct}%"></i></div><section class="stage"><div class="qmeta"><div><span class="qkicker">${q.title} · QUESTION ${q.number}</span><h1>Choose the correct answer</h1></div><button class="save ${saved?'on':''}" data-save>${saved?'★ Saved':'☆ Save'}</button></div>
      <div class="crop-card"><img src="${q.question}" alt="${q.title} Question ${q.number}" data-zoom="${q.question}"></div>
      <div class="answer-box"><div class="answer-head"><strong>Your answer</strong><span>Select 1–5</span></div><div class="choices">${[1,2,3,4,5].map(n=>{let cls='';if(done)cls=n===correct?'correct':n===picked?'wrong':'dim';return`<button class="choice ${cls}" data-choice="${n}" ${done?'disabled':''}>${n}${cls==='correct'?'<i>✓</i>':cls==='wrong'?'<i>×</i>':''}</button>`;}).join('')}</div>${done?`<div class="feedback ${picked===correct?'good':'bad'}"><div class="mark">${picked===correct?'✓':'!'}</div><div><strong>${picked===correct?'Correct!':'Not quite — review the marking.'}</strong><p>The official marking answer is ${correct}.</p></div></div><section class="marking"><small>OFFICIAL MARKING REVIEW</small><h2>Why this answer is right or wrong</h2><img src="${q.marking}" alt="${q.title} Question ${q.number} marking" data-zoom="${q.marking}"></section>`:''}</div>
      <div class="nav"><button data-prev ${state.index===0?'disabled':''}>← Previous</button><span>${q.title} · ${q.number}/5</span>${state.index===questions.length-1?'<button class="next" data-results>View results →</button>':'<button class="next" data-next>Next →</button>'}</div></section></main>`;
    root.querySelector('[data-home]').onclick=home; root.querySelector('[data-save]').onclick=toggleSave;
    root.querySelectorAll('[data-choice]').forEach(button=>button.onclick=()=>choose(Number(button.dataset.choice)));
    root.querySelector('[data-prev]').onclick=()=>nav(-1); root.querySelector('[data-next]')?.addEventListener('click',()=>nav(1)); root.querySelector('[data-results]')?.addEventListener('click',showResults);
    root.querySelectorAll('[data-zoom]').forEach(img=>img.onclick=()=>zoom(img.dataset.zoom)); attachImageErrors();
  }

  function renderResults() {
    const questions=flat(); let attempted=0,correct=0; questions.forEach(q=>{const value=state.answers[qkey(q.paper,q.number)];if(value!==undefined){attempted++;if(value===q.answer)correct++;}});
    const wrong=attempted-correct,unanswered=questions.length-attempted,pct=questions.length?Math.round(correct/questions.length*100):0;
    root.innerHTML=`<main class="results"><section class="result-card"><p class="eyebrow">SESSION COMPLETE</p><div class="score" style="--score:${pct*3.6}deg"><div><strong>${pct}%</strong><span>SCORE</span></div></div><h1>${pct>=80?'Excellent!':pct>=60?'Good progress.':'Keep practicing.'}</h1><p>${state.mode==='all'?`QUIZ 01–${String(latestQuiz).padStart(2,'0')}`:state.paper.title} · ${correct}/${questions.length} correct</p><div class="result-stats"><div><span>CORRECT</span><strong>${correct}</strong></div><div><span>WRONG</span><strong>${wrong}</strong></div><div><span>UNANSWERED</span><strong>${unanswered}</strong></div></div><div class="actions" style="justify-content:center"><button class="btn primary" data-review>Review questions →</button><button class="btn secondary dark" data-home>Quiz list</button></div></section></main>`;
    root.querySelector('[data-review]').onclick=()=>{state.screen='quiz';state.index=0;save();render();}; root.querySelector('[data-home]').onclick=home;
  }

  function render(){if(state.screen==='home')renderHome();else if(state.screen==='quiz')renderQuiz();else renderResults();}
  render();
})();
