(() => {
  const root = document.getElementById('app');
  const modal = document.getElementById('modal');
  const answers = [
    [3,5,2,3,4],[3,2,2,4,3],[1,1,1,1,1],[3,2,4,1,4],[3,5,3,3,3],
    [2,1,3,2,1],[2,1,2,2,2],[3,3,3,5,3],[3,2,2,2,3],[4,2,3,3,4],
    [1,2,1,1,2],[2,5,2,1,1],[1,3,1,3,1],[5,3,2,3,3],[3,2,2,1,2],
    [2,2,3,2,3],[3,1,3,2,2]
  ];
  const data = Array.from({length:17},(_,i)=>({
    number:i+1,
    title:`QUIZ ${String(i+1).padStart(2,'0')}`,
    questions:Array.from({length:5},(_,j)=>({
      number:j+1,
      answer:answers[i][j],
      question:`daily_assets/questions/quiz-${String(i+1).padStart(2,'0')}/q-${String(j+1).padStart(2,'0')}.png`,
      marking:`daily_assets/markings/quiz-${String(i+1).padStart(2,'0')}/q-${String(j+1).padStart(2,'0')}.png`
    }))
  }));

  const KEY='ict-daily-quiz-2028-v1';
  let state={screen:'home',mode:'all',paper:null,index:0,answers:{},saved:[],zoom:''};
  try{const s=JSON.parse(localStorage.getItem(KEY)||'null');if(s)state={...state,...s,screen:'home',zoom:''};}catch{}
  const save=()=>localStorage.setItem(KEY,JSON.stringify(state));
  const qkey=(p,q)=>`p${p}q${q}`;
  const flat=()=>state.mode==='all'?data.flatMap(p=>p.questions.map(q=>({...q,paper:p.number,title:p.title}))):state.paper.questions.map(q=>({...q,paper:state.paper.number,title:state.paper.title}));
  const answeredIn=p=>p.questions.filter(q=>state.answers[qkey(p.number,q.number)]!==undefined).length;
  function startAll(){state.mode='all';state.paper=null;const qs=data.flatMap(p=>p.questions.map(q=>({...q,paper:p.number})));const n=qs.findIndex(q=>state.answers[qkey(q.paper,q.number)]===undefined);state.index=n<0?0:n;state.screen='quiz';save();render();scrollTo(0,0)}
  function startPaper(n){state.mode='paper';state.paper=data.find(p=>p.number===n);const i=state.paper.questions.findIndex(q=>state.answers[qkey(n,q.number)]===undefined);state.index=i<0?0:i;state.screen='quiz';save();render();scrollTo(0,0)}
  function home(){state.screen='home';save();render();scrollTo(0,0)}
  function choose(n){const q=flat()[state.index],k=qkey(q.paper,q.number);if(state.answers[k]!==undefined)return;state.answers[k]=n;save();render()}
  function nav(d){const qs=flat();state.index=Math.max(0,Math.min(qs.length-1,state.index+d));save();render();scrollTo(0,0)}
  function toggleSave(){const q=flat()[state.index],k=qkey(q.paper,q.number);state.saved=state.saved.includes(k)?state.saved.filter(x=>x!==k):[...state.saved,k];save();render()}
  function showResults(){state.screen='results';save();render();scrollTo(0,0)}
  function zoom(src){state.zoom=src;modal.innerHTML=`<div class="modal open"><button data-close>×</button><img src="${src}" alt="Expanded image"></div>`;modal.querySelector('[data-close]').onclick=closeZoom;modal.querySelector('.modal').onclick=e=>{if(e.target===e.currentTarget)closeZoom()}}
  function closeZoom(){state.zoom='';modal.innerHTML=''}

  function renderHome(){
    root.innerHTML=`<main class="home"><div class="wrap"><header class="header"><div class="brand"><span class="brand-badge">IT</span><span><strong>ICT Daily Quiz</strong><small>2028 QUIZ STUDIO</small></span></div><div class="pill">AUG 01–17 · DAILY QUIZ</div></header>
      <section class="hero"><div><p class="eyebrow">Information & Communication Technology</p><h1>Turn every daily quiz<span>into exam-ready practice.</span></h1><p class="lead">අගෝස්තු 01 සිට 17 දක්වා Daily Quiz 17ක ප්‍රශ්න 85ම original question crop එකෙන් practice කරන්න. පිළිතුර තෝරාගත් පසු එම ප්‍රශ්නයටම අදාළ official marking crop එක බලන්න.</p><div class="actions"><button class="btn primary" data-all>Start all 85 questions →</button></div><div class="stats"><div><strong>85</strong><span>QUESTIONS</span></div><div><strong>17</strong><span>DAILY QUIZZES</span></div><div><strong>5</strong><span>CHOICES EACH</span></div></div></div>
      <div class="demo-wrap"><div class="orbit"></div><div class="orbit b"></div><div class="demo"><div class="demo-top"><span>LIVE PRACTICE</span><span>QUIZ 01</span></div><div class="track"><i></i></div><div class="mini">QUESTION 3 OF 5</div><h2>Choose your answer</h2><div class="answers-preview"><span>1</span><span>2</span><span class="on">3</span><span>4</span><span>5</span></div><div class="demo-ok"><b>✓</b><div><strong>Official marking review</strong><small>Exact crop from source</small></div></div></div></div></section>
      <section class="papers"><div class="section-head"><div><p class="eyebrow">DAILY QUIZ MODE</p><h2>QUIZ 01 සිට QUIZ 17 දක්වා</h2></div><p>Quiz එකක් තෝරලා ප්‍රශ්න 5ම එකින් එක practice කරන්න. Progress device එකේම save වෙනවා.</p></div><div class="paper-grid">${data.map(p=>{const a=answeredIn(p),pc=a/5*100;return`<button class="paper-card" data-paper="${p.number}"><div class="paper-top"><span class="paper-number">${String(p.number).padStart(2,'0')}</span><span class="paper-count">5 questions</span></div><h3>${p.title}</h3><div class="paper-progress"><i style="width:${pc}%"></i></div><div class="paper-foot"><span>${a?`${a}/5 completed`:'Not started'}</span><span>↗</span></div></button>`}).join('')}</div></section>
      <footer class="footer"><span>Source: 2028 ICT Daily Quiz series · Original crops.</span><span>Progress is stored only on your device.</span></footer></div></main>`;
    root.querySelector('[data-all]').onclick=startAll;
    root.querySelectorAll('[data-paper]').forEach(b=>b.onclick=()=>startPaper(Number(b.dataset.paper)));
  }

  function renderQuiz(){
    const qs=flat(),q=qs[state.index],k=qkey(q.paper,q.number),picked=state.answers[k],done=picked!==undefined,correct=q.answer,saved=state.saved.includes(k),pct=(state.index+1)/qs.length*100;
    root.innerHTML=`<main class="quiz"><header class="quiz-header"><button class="icon" data-home>←</button><div class="qtitle"><small>${state.mode==='all'?'ALL QUIZZES':'QUIZ MODE'}</small><strong>${q.title}</strong></div><div class="counter">${state.index+1}/${qs.length}</div></header><div class="top-progress"><i style="width:${pct}%"></i></div><section class="stage"><div class="qmeta"><div><span class="qkicker">${q.title} · QUESTION ${q.number}</span><h1>Choose the correct answer</h1></div><button class="save ${saved?'on':''}" data-save>${saved?'★ Saved':'☆ Save'}</button></div>
      <div class="crop-card"><img src="${q.question}" alt="${q.title} Question ${q.number}" data-zoom="${q.question}"></div>
      <div class="answer-box"><div class="answer-head"><strong>Your answer</strong><span>Select 1–5</span></div><div class="choices">${[1,2,3,4,5].map(n=>{let cls='';if(done)cls=n===correct?'correct':n===picked?'wrong':'dim';return`<button class="choice ${cls}" data-choice="${n}" ${done?'disabled':''}>${n}${cls==='correct'?'<i>✓</i>':cls==='wrong'?'<i>×</i>':''}</button>`}).join('')}</div>${done?`<div class="feedback ${picked===correct?'good':'bad'}"><div class="mark">${picked===correct?'✓':'!'}</div><div><strong>${picked===correct?'Correct!':'Not quite — review the marking.'}</strong><p>The official marking answer is ${correct}.</p></div></div><section class="marking"><small>OFFICIAL MARKING REVIEW</small><h2>Why this answer is right or wrong</h2><img src="${q.marking}" alt="${q.title} Question ${q.number} marking" data-zoom="${q.marking}"></section>`:''}</div>
      <div class="nav"><button data-prev ${state.index===0?'disabled':''}>← Previous</button><span>${q.title} · ${q.number}/5</span>${state.index===qs.length-1?'<button class="next" data-results>View results →</button>':'<button class="next" data-next>Next →</button>'}</div></section></main>`;
    root.querySelector('[data-home]').onclick=home;root.querySelector('[data-save]').onclick=toggleSave;
    root.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>choose(Number(b.dataset.choice)));
    root.querySelector('[data-prev]').onclick=()=>nav(-1);root.querySelector('[data-next]')?.addEventListener('click',()=>nav(1));root.querySelector('[data-results]')?.addEventListener('click',showResults);
    root.querySelectorAll('[data-zoom]').forEach(img=>img.onclick=()=>zoom(img.dataset.zoom));
  }

  function renderResults(){const qs=flat();let attempted=0,correct=0;qs.forEach(q=>{const v=state.answers[qkey(q.paper,q.number)];if(v!==undefined){attempted++;if(v===q.answer)correct++}});const wrong=attempted-correct,unanswered=qs.length-attempted,pct=qs.length?Math.round(correct/qs.length*100):0;root.innerHTML=`<main class="results"><section class="result-card"><p class="eyebrow">SESSION COMPLETE</p><div class="score" style="--score:${pct*3.6}deg"><div><strong>${pct}%</strong><span>SCORE</span></div></div><h1>${pct>=80?'Excellent!':pct>=60?'Good progress.':'Keep practicing.'}</h1><p>${state.mode==='all'?'QUIZ 01–17':state.paper.title} · ${correct}/${qs.length} correct</p><div class="result-stats"><div><span>CORRECT</span><strong>${correct}</strong></div><div><span>WRONG</span><strong>${wrong}</strong></div><div><span>UNANSWERED</span><strong>${unanswered}</strong></div></div><div class="actions" style="justify-content:center"><button class="btn primary" data-review>Review questions →</button><button class="btn secondary dark" data-home>Quiz list</button></div></section></main>`;root.querySelector('[data-review]').onclick=()=>{state.screen='quiz';state.index=0;save();render()};root.querySelector('[data-home]').onclick=home}
  function render(){if(state.screen==='home')renderHome();else if(state.screen==='quiz')renderQuiz();else renderResults()}
  render();
})();
