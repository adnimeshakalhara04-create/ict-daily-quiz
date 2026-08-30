from __future__ import annotations

import base64
import io
import struct
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "prebuilt" / "quiz21-26-sprite"

parts = sorted(PARTS.glob("part*"))
print(f"SPRITE_DIAG parts={[(p.name, p.stat().st_size) for p in parts]}")
encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
print(f"SPRITE_DIAG encoded_chars={len(encoded)} mod4={len(encoded) % 4} tail={encoded[-24:]!r}")
payload = base64.b64decode(encoded, validate=True)
print(f"SPRITE_DIAG zip_bytes={len(payload)} prefix={payload[:8]!r} tail={payload[-24:]!r}")

# Recover complete ZIP local-file records even when the central directory / final
# EOCD record was never uploaded. Python-created ZIPs have sizes in the local
# header, so complete entries before the truncation point are still testable.
pos = 0
entry = 0
recovered = []
while pos + 30 <= len(payload):
    sig = payload[pos:pos+4]
    if sig != b"PK\x03\x04":
        print(f"SPRITE_SCAN_STOP offset={pos} sig={sig!r} remaining={len(payload)-pos}")
        break
    fields = struct.unpack_from("<IHHHHHIIIHH", payload, pos)
    _, version, flags, method, mtime, mdate, crc, csize, usize, nlen, xlen = fields
    name_start = pos + 30
    data_start = name_start + nlen + xlen
    name = payload[name_start:name_start+nlen].decode("utf-8", "replace")
    print(f"SPRITE_LOCAL entry={entry} offset={pos} name={name!r} flags={flags} method={method} csize={csize} usize={usize} data_start={data_start}")
    if flags & 0x08:
        print("SPRITE_SCAN_ABORT data-descriptor flag set; cannot size truncated entry deterministically")
        break
    data_end = data_start + csize
    if data_end > len(payload):
        print(f"SPRITE_TRUNCATED_ENTRY name={name!r} need_end={data_end} have={len(payload)} missing={data_end-len(payload)}")
        break
    comp = payload[data_start:data_end]
    try:
        if method == 0:
            raw = comp
        elif method == 8:
            raw = zlib.decompress(comp, -15)
        else:
            raise RuntimeError(f"unsupported compression method {method}")
        if len(raw) != usize:
            raise RuntimeError(f"size mismatch {len(raw)} != {usize}")
        if (zlib.crc32(raw) & 0xffffffff) != crc:
            raise RuntimeError("CRC mismatch")
        low = name.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".webp")):
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                dims = image.size
                fmt = image.format
                mode = image.mode
            print(f"SPRITE_RECOVERED_IMAGE name={name!r} bytes={len(raw)} format={fmt} size={dims} mode={mode}")
        else:
            print(f"SPRITE_RECOVERED_FILE name={name!r} bytes={len(raw)}")
        recovered.append(name)
    except Exception as exc:
        print(f"SPRITE_RECOVERY_ERROR name={name!r} error={exc}")
        break
    pos = data_end
    entry += 1

print(f"SPRITE_RECOVERY_SUMMARY complete_entries={len(recovered)} names={recovered}")
raise RuntimeError("Intentional diagnostic stop after sprite recovery scan")
