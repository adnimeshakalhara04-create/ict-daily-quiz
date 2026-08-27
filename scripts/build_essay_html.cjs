const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const vm = require('vm');
const converterPkg = require('sinhala-unicode-coverter');

const fmAbayaToUnicode = converterPkg.fmAbayaToUnicode || (converterPkg.default && converterPkg.default.fmAbayaToUnicode);
if (typeof fmAbayaToUnicode !== 'function') throw new Error('fmAbayaToUnicode is unavailable');

const ROOT = path.resolve(__dirname, '..');
const PAYLOAD = path.join(ROOT, 'essay_html_payload');
const TEXT = path.join(ROOT, 'essay_text');
const SITE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'site-build');
const OUT = path.join(SITE, 'essay_html');
fs.mkdirSync(OUT, { recursive: true });

function decodeEntities(s) {
  return String(s).replace(/&#x([0-9a-f]+);/gi, (_,h)=>String.fromCodePoint(parseInt(h,16)))
    .replace(/&#([0-9]+);/g, (_,d)=>String.fromCodePoint(parseInt(d,10)))
    .replace(/&apos;/g,"'").replace(/&quot;/g,'"').replace(/&nbsp;/g,'\u00a0')
    .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
}
function escapeHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function convertLegacySpans(fragment){
  let converted=0;
  const html=fragment.replace(/(<span\b[^>]*style="[^"]*font-family:4u[^\"]*"[^>]*>)([\s\S]*?)(<\/span>)/gi,(all,open,body,close)=>{
    converted++;
    const unicode=fmAbayaToUnicode(decodeEntities(body));
    const fixedOpen=open.replace(/font-family:4u[^;\"]*/i,'font-family:Noto Sans Sinhala,Iskoola Pota,Segoe UI,sans-serif');
    return fixedOpen+escapeHtml(unicode)+close;
  });
  return {html,converted};
}
function wrapPdfPage(fragment,title){return `<!doctype html><html lang="si"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes"><title>${escapeHtml(title)}</title><style>*{box-sizing:border-box}html,body{margin:0;padding:0;background:#e8edf4;width:100%;min-height:100%;overflow-x:hidden}body{font-family:Arial,'Noto Sans Sinhala','Iskoola Pota',sans-serif}.page-stage{position:relative;width:100vw;margin:0 auto;background:#e8edf4}.pdf-page{position:absolute;left:0;top:0;transform-origin:top left;background:#fff;overflow:hidden;box-shadow:0 2px 12px rgba(13,35,64,.12)}.pdf-page p{position:absolute;margin:0;padding:0;white-space:nowrap;z-index:2}.pdf-page img{position:absolute;z-index:1}.pdf-page .source-vectors{position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}.pdf-page span{font-synthesis:none}</style></head><body><div class="page-stage" id="stage"><div class="pdf-page" id="pdfPage">${fragment}</div></div><script>(function(){var host=document.getElementById('pdfPage'),stage=document.getElementById('stage'),inner=host.firstElementChild;if(!inner)return;var m=(inner.getAttribute('style')||'').match(/width:([0-9.]+)pt;height:([0-9.]+)pt/);var w=(m?parseFloat(m[1]):595.3)*96/72,h=(m?parseFloat(m[2]):841.9)*96/72;host.style.width=w+'px';host.style.height=h+'px';function fit(){var avail=Math.max(280,document.documentElement.clientWidth);var s=Math.min(1.65,avail/w);host.style.transform='scale('+s+')';stage.style.height=(h*s)+'px';stage.style.width=(w*s)+'px'}fit();addEventListener('resize',fit,{passive:true})})();</script></body></html>`;}

function looksLegacy(line){
  if (!line || /[\u0D80-\u0DFF]/.test(line)) return false;
  if (/[%^;`~|{}<>\\]/.test(line)) return true;
  if (/[a-z][A-Z]{1,3}[a-z]/.test(line)) return true;
  if (/\b(?:WodyrK|Ndú|lsÍ|fõ|wjYH|mß|f;dr|uDÿ|wdodk|moaO|fiajd|wxl|frðia|l%shd|m%Odk|mrïmrdj)\b/.test(line)) return true;
  return false;
}
function convertText(raw){
  let convertedLines=0;
  const lines=String(raw||'').split(/\r?\n/).map(line=>{
    if(!looksLegacy(line)) return line;
    const u=fmAbayaToUnicode(line);
    const count=(u.match(/[\u0D80-\u0DFF]/g)||[]).length;
    if(count>=2){convertedLines++;return u;}
    return line;
  });
  return {text:lines.join('\n'),convertedLines};
}
function wrapTextPage(raw,title){
  const c=convertText(raw);
  const html=`<!doctype html><html lang="si"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><style>*{box-sizing:border-box}html,body{margin:0;background:#eef3f8;color:#132741}body{font-family:Inter,'Noto Sans Sinhala','Iskoola Pota','Segoe UI',Arial,sans-serif}.sheet{max-width:920px;margin:0 auto;background:#fff;min-height:100vh;padding:28px 34px;box-shadow:0 6px 24px rgba(16,42,75,.08)}.tag{display:inline-block;padding:6px 10px;border-radius:999px;background:#e9f7f0;color:#166848;font-size:11px;font-weight:800;margin-bottom:14px}.source{white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px;line-height:1.65;margin:0}@media(max-width:600px){.sheet{padding:18px 16px}.source{font-size:14px;line-height:1.58}}</style></head><body><main class="sheet"><div class="tag">LOCAL SOURCE • UNICODE SINHALA</div><pre class="source">${escapeHtml(c.text)}</pre></main></body></html>`;
  return {html,convertedLines:c.convertedLines};
}

const built=new Set();
const manifest={sourceMode:'bundled-local',files:[],pages:0,pdfLayoutPages:0,textFallbackPages:0,convertedSpans:0,convertedTextLines:0};
const files=fs.existsSync(PAYLOAD)?fs.readdirSync(PAYLOAD).filter(f=>f.endsWith('.b64')).sort():[];
for(const file of files){
  const encoded=fs.readFileSync(path.join(PAYLOAD,file),'utf8').trim();
  const obj=JSON.parse(zlib.gunzipSync(Buffer.from(encoded,'base64url')).toString('utf8'));
  const dir=path.join(OUT,obj.driveId);fs.mkdirSync(dir,{recursive:true});
  obj.pages.forEach((fragment,idx)=>{
    const page=obj.start+idx,key=`${obj.driveId}:${page}`;
    const result=convertLegacySpans(fragment);
    const unicodeCount=(result.html.match(/[\u0D80-\u0DFF]/g)||[]).length;
    if(!result.converted||unicodeCount<5) throw new Error(`Unicode conversion failed in ${file} page ${page}`);
    fs.writeFileSync(path.join(dir,`page-${page}.html`),wrapPdfPage(result.html,`Lesson ${obj.lesson} Essay Source - Page ${page}`),'utf8');
    built.add(key);manifest.pages++;manifest.pdfLayoutPages++;manifest.convertedSpans+=result.converted;
  });
  manifest.files.push({file,lesson:obj.lesson,start:obj.start,count:obj.pages.length,driveId:obj.driveId,mode:'pdf-layout'});
}

const sandbox={window:{LOCAL_ESSAY_TEXT:{}}};
for(const file of fs.readdirSync(TEXT).filter(f=>f.endsWith('.js')).sort()) vm.runInNewContext(fs.readFileSync(path.join(TEXT,file),'utf8'),sandbox,{filename:file});
for(const [driveId,pages] of Object.entries(sandbox.window.LOCAL_ESSAY_TEXT||{})){
  const lesson=driveId==='1aNyguRdOMTNcYYAIqc_C1Ytf9N4CUQt3'?1:driveId==='1xkXsZuUxmbSE29P_KILTezuRnR9GEYYx'?2:0;
  if(!lesson) continue;
  const dir=path.join(OUT,driveId);fs.mkdirSync(dir,{recursive:true});
  for(const row of pages){
    const page=Number(row.page),key=`${driveId}:${page}`;if(!page||built.has(key))continue;
    const out=wrapTextPage(row.text,`Lesson ${lesson} Essay Source - Page ${page}`);
    fs.writeFileSync(path.join(dir,`page-${page}.html`),out.html,'utf8');
    built.add(key);manifest.pages++;manifest.textFallbackPages++;manifest.convertedTextLines+=out.convertedLines;
  }
}

const expected=[['1aNyguRdOMTNcYYAIqc_C1Ytf9N4CUQt3',18],['1xkXsZuUxmbSE29P_KILTezuRnR9GEYYx',10]];
for(const [id,count] of expected)for(let p=1;p<=count;p++)if(!built.has(`${id}:${p}`))throw new Error(`Missing local Essay page ${id} page ${p}`);
if(manifest.pages!==28)throw new Error(`Expected 28 essay pages, built ${manifest.pages}`);
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2),'utf8');
console.log(`Built ${manifest.pages} local Essay pages: ${manifest.pdfLayoutPages} PDF-layout + ${manifest.textFallbackPages} Unicode-text fallback; ${manifest.convertedTextLines} converted legacy lines`);
