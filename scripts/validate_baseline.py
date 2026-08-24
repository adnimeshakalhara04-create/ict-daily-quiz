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
            bad.append((str(path.relative_to(out)), str(exc)))

print(f'Baseline image scan: {count} image files')
if bad:
    print(f'CORRUPT_IMAGE_COUNT={len(bad)}')
    for name, error in bad:
        print(f'CORRUPT: {name} :: {error}')
    raise SystemExit(2)
print('BASELINE_IMAGES_OK')
