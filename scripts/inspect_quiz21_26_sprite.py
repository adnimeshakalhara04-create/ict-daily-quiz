from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "prebuilt" / "quiz21-26-sprite"

parts = sorted(PARTS.glob("part*"))
print(f"SPRITE_DIAG parts={[(p.name, p.stat().st_size) for p in parts]}")
encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
print(f"SPRITE_DIAG encoded_chars={len(encoded)} mod4={len(encoded) % 4}")
payload = base64.b64decode(encoded, validate=True)
print(f"SPRITE_DIAG zip_bytes={len(payload)} prefix={payload[:8]!r}")
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
    bad = archive.testzip()
    print(f"SPRITE_DIAG testzip={bad!r} entries={len(archive.infolist())}")
    for info in archive.infolist():
        print(f"SPRITE_ENTRY name={info.filename!r} size={info.file_size} compressed={info.compress_size}")
        low = info.filename.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".webp")):
            data = archive.read(info.filename)
            with Image.open(io.BytesIO(data)) as image:
                print(f"SPRITE_IMAGE name={info.filename!r} format={image.format} size={image.size} mode={image.mode}")
        elif low.endswith((".json", ".txt", ".csv")) and info.file_size <= 20000:
            try:
                text = archive.read(info.filename).decode("utf-8")
                print(f"SPRITE_TEXT name={info.filename!r} content={text!r}")
            except Exception as exc:
                print(f"SPRITE_TEXT_ERROR name={info.filename!r} error={exc}")
