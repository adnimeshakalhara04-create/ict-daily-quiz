from pathlib import Path
import tempfile
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / 'daily-quiz-cropped-images-under-25MB.zip'

bad = []
count = 0
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    with zipfile.ZipFile(ZIP) as z:
        broken_member = z.testzip()
        if broken_member:
            raise SystemExit(f'ZIP CRC ERROR: {broken_member}')
        z.extractall(out)
    for path in out.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in {'.webp','.png','.jpg','.jpeg'}:
            continue
        count += 1
        try:
            with Image.open(path) as im:
                im.verify()
        except Exception as exc:
            data = path.read_bytes()
            bad.append((str(path.relative_to(out)), str(exc), len(data), data[:64].hex(), data[-64:].hex(), data.find(b'RIFF'), data.find(b'WEBP'), sum(1 for b in data if b)))

print(f'Baseline image scan: {count} image files')
if bad:
    print(f'CORRUPT_IMAGE_COUNT={len(bad)}')
    for name, error, size, head, tail, riff, webp, nonzero in bad:
        print(f'CORRUPT: {name} :: {error}')
        print(f'  SIZE={size} NONZERO={nonzero} RIFF_AT={riff} WEBP_AT={webp}')
        print(f'  HEAD64={head}')
        print(f'  TAIL64={tail}')
    raise SystemExit(2)
print('BASELINE_IMAGES_OK')
