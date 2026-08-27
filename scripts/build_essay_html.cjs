const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const converterPkg = require('sinhala-unicode-coverter');

const fmAbayaToUnicode = converterPkg.fmAbayaToUnicode || (converterPkg.default && converterPkg.default.fmAbayaToUnicode);
if (typeof fmAbayaToUnicode !== 'function') {
  throw new Error('fmAbayaToUnicode is unavailable from sinhala-unicode-coverter');
}

const ROOT = path.resolve(__dirname, '..');
const PAYLOAD = path.join(ROOT, 'essay_html_payload');
const SITE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'site-build');
const OUT = path.join(SITE, 'essay_html');
fs.mkdirSync(OUT, { recursive: true });

function decodeEntities(s) {
  return String(s)
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#([0-9]+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&nbsp;/g, '\u00a0')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function convertLegacySpans(fragment) {
  let converted = 0;
  const html = fragment.replace(/(<span\b[^>]*style="[^"]*font-family:4u[^\"]*"[^>]*>)([\s\S]*?)(<\/span>)/gi, (all, open, body, close) => {
    converted++;
    const legacy = decodeEntities(body);
    const unicode = fmAbayaToUnicode(legacy);
    const fixedOpen = open.replace(/font-family:4u[^;\"]*/i, 'font-family:Noto Sans Sinhala,Iskoola Pota,Segoe UI,sans-serif');
    return fixedOpen + escapeHtml(unicode) + close;
  });
  return { html, converted };
}

function wrapPage(fragment, title) {
  return `<!doctype html><html lang="si"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes"><title>${title}</title><style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#e8edf4;width:100%;min-height:100%;overflow-x:hidden}body{font-family:Arial,sans-serif}.page-stage{position:relative;width:100vw;margin:0 auto;background:#e8edf4}.pdf-page{position:absolute;left:0;top:0;transform-origin:top left;background:#fff;overflow:hidden;box-shadow:0 2px 12px rgba(13,35,64,.12)}.pdf-page p{position:absolute;margin:0;padding:0;white-space:nowrap;z-index:2}.pdf-page img{position:absolute;z-index:1}.pdf-page .source-vectors{position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}.pdf-page span{font-synthesis:none}.pdf-page b{font-weight:700}.pdf-page i{font-style:italic}
</style></head><body><div class="page-stage" id="stage"><div class="pdf-page" id="pdfPage">${fragment}</div></div><script>
(function(){var host=document.getElementById('pdfPage'),stage=document.getElementById('stage'),inner=host.firstElementChild;if(!inner)return;var m=(inner.getAttribute('style')||'').match(/width:([0-9.]+)pt;height:([0-9.]+)pt/);var w=(m?parseFloat(m[1]):595.3)*96/72,h=(m?parseFloat(m[2]):841.9)*96/72;host.style.width=w+'px';host.style.height=h+'px';inner.style.width=(m?m[1]:'595.3')+'pt';inner.style.height=(m?m[2]:'841.9')+'pt';function fit(){var avail=Math.max(280,document.documentElement.clientWidth);var s=Math.min(1.65,avail/w);host.style.transform='scale('+s+')';stage.style.height=(h*s)+'px';stage.style.width=(w*s)+'px'}fit();addEventListener('resize',fit,{passive:true})})();
</script></body></html>`;
}

const files = fs.readdirSync(PAYLOAD).filter(f => f.endsWith('.b64')).sort();
if (!files.length) throw new Error('No essay HTML payload files found');
const manifest = { sourceMode: 'bundled-html-unicode', files: [], pages: 0, convertedSpans: 0 };
for (const file of files) {
  const encoded = fs.readFileSync(path.join(PAYLOAD, file), 'utf8').trim();
  const compressed = Buffer.from(encoded, 'base64url');
  const obj = JSON.parse(zlib.gunzipSync(compressed).toString('utf8'));
  const dir = path.join(OUT, obj.driveId);
  fs.mkdirSync(dir, { recursive: true });
  obj.pages.forEach((fragment, idx) => {
    const page = obj.start + idx;
    const result = convertLegacySpans(fragment);
    if (!result.converted) throw new Error(`No legacy Sinhala spans found in ${file} page ${page}`);
    if (/font-family:4u/i.test(result.html)) throw new Error(`Legacy 4u font reference remains in ${file} page ${page}`);
    const unicodeCount = (result.html.match(/[\u0D80-\u0DFF]/g) || []).length;
    if (unicodeCount < 5) throw new Error(`Unicode Sinhala conversion failed in ${file} page ${page}`);
    const finalHtml = wrapPage(result.html, `Lesson ${obj.lesson} Essay Source - Page ${page}`);
    fs.writeFileSync(path.join(dir, `page-${page}.html`), finalHtml, 'utf8');
    manifest.pages++;
    manifest.convertedSpans += result.converted;
    console.log(`Essay HTML ready: lesson ${obj.lesson} page ${page}; ${result.converted} Sinhala spans, ${unicodeCount} Sinhala chars`);
  });
  manifest.files.push({ file, lesson: obj.lesson, start: obj.start, count: obj.pages.length, driveId: obj.driveId });
}
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
if (manifest.pages !== 28) throw new Error(`Expected 28 essay pages, built ${manifest.pages}`);
console.log(`Built ${manifest.pages} self-contained Essay pages with ${manifest.convertedSpans} converted Sinhala spans`);
