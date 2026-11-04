"""Temporary lossless transfer of the PDF-generated missing WEBP files.

Encode a ZIP as pixel bytes in PNG frames. The receiving side checks SHA-256
for every original WEBP; no image resampling or OCR is involved.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/"daily_assets"
TARGET=ROOT/"site-build"/"_repair_transfer"
TARGET.mkdir(parents=True,exist_ok=True)
missing=[(27,"markings",5),(28,"markings",5),(33,"markings",2),(33,"markings",4),(38,"markings",5),(45,"markings",1),(71,"markings",4),(71,"markings",5)]
missing += [(n,k,q) for n in range(72,96) for k in ("questions","markings") for q in range(1,6)]
assert len(missing)==248
out=io.BytesIO()
manifest={}
with zipfile.ZipFile(out,"w",zipfile.ZIP_STORED) as bundle:
    for n,k,q in missing:
        file=ASSETS/k/f"quiz-{n:02d}"/f"q-{q:02d}.webp"
        contents=file.read_bytes()
        assert contents[:4]==b"RIFF" and contents[8:12]==b"WEBP" and len(contents)>1000
        key=f"{n:02d}/{k}/q-{q:02d}.webp"
        bundle.writestr(key,contents)
        manifest[key]={"sha256":hashlib.sha256(contents).hexdigest(),"size":len(contents)}
    bundle.writestr("manifest.json",json.dumps(manifest,sort_keys=True))
blob=out.getvalue()
stream=len(blob).to_bytes(8,"big")+blob
capacity=1024*1024*3
total=math.ceil(len(stream)/capacity)
for i in range(total):
    chunk=stream[i*capacity:(i+1)*capacity].ljust(capacity,bytes([0]))
    frame=Image.frombytes("RGB",(1024,1024),chunk)
    dest=io.BytesIO()
    frame.save(dest,"PNG",compress_level=1)
    (TARGET/f"part-{i:02d}.txt").write_text(base64.b64encode(dest.getvalue()).decode("ascii"),encoding="ascii")
(TARGET/"info.json").write_text(json.dumps({"parts":total,"zip_bytes":len(blob),"entries":len(missing),"zip_sha256":hashlib.sha256(blob).hexdigest()}))
print(f"REPAIR_TRANSFER: {total} frames / {len(blob)} bytes / {len(missing)} files")
