from pathlib import Path
import base64, io, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]
PARTS=ROOT/'.past_payload'
OUT=ROOT/'past_assets'
parts=sorted(PARTS.glob('part*.b64'))
if not parts: raise SystemExit('Past-paper payload parts missing')
payload=''.join(p.read_text(encoding='utf-8').strip() for p in parts)
raw=base64.b64decode(payload,validate=True)
if OUT.exists(): shutil.rmtree(OUT)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    bad=z.testzip()
    if bad: raise SystemExit(f'Past-paper payload CRC failed: {bad}')
    z.extractall(ROOT)
expected=[OUT/f'L{lesson}'/f'Q{q:02d}'/f'{kind}.png' for lesson,count in ((1,44),(2,56)) for q in range(1,count+1) for kind in ('question','marking')]
missing=[str(p.relative_to(ROOT)) for p in expected if not p.exists() or p.stat().st_size<100]
if missing: raise SystemExit(f'Past-paper assets incomplete: {missing[:10]}')
print(f'Past-paper assets ready: {len(expected)} files')
