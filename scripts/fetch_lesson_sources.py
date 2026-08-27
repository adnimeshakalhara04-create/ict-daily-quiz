from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site-build" / "sources"
OUT.mkdir(parents=True, exist_ok=True)

DATA_FILES = [ROOT / "quiz-data-1.js", ROOT / "quiz-data-2.js", ROOT / "quiz-data-3.js"]
FILE_URL_RE = re.compile(r"drive\.google\.com/file/d/([A-Za-z0-9_-]+)")
DRIVE_ID_RE = re.compile(r'"driveId"\s*:\s*"([A-Za-z0-9_-]+)"')

text = "\n".join(path.read_text(encoding="utf-8") for path in DATA_FILES)
ids = sorted(set(FILE_URL_RE.findall(text)) | set(DRIVE_ID_RE.findall(text)))
if not ids:
    raise RuntimeError("No Lesson 1/2 Google Drive source IDs were found in quiz-data files")

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; ICT-Source-Quiz-Build/1.0)",
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
}


def download_pdf(file_id: str) -> dict:
    target = OUT / f"{file_id}.pdf"
    if target.exists() and target.stat().st_size > 1000:
        head = target.read_bytes()[:5]
        if head == b"%PDF-":
            return {"id": file_id, "bytes": target.stat().st_size, "cached": True}

    urls = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
    ]
    last_error = None
    for attempt in range(3):
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as response:
                    data = response.read()
                if data.startswith(b"%PDF-") and len(data) > 1000:
                    target.write_bytes(data)
                    return {"id": file_id, "bytes": len(data), "cached": False}
                last_error = RuntimeError(
                    f"Drive source {file_id} did not return a PDF (received {len(data)} bytes)"
                )
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_error = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not mirror source {file_id}: {last_error}")


results = []
with ThreadPoolExecutor(max_workers=min(4, len(ids))) as pool:
    futures = {pool.submit(download_pdf, file_id): file_id for file_id in ids}
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        print(f"Local source ready: {result['id']} ({result['bytes']} bytes)")

manifest = {
    "source": "Lesson 1 + 2 quiz-data Drive file IDs",
    "count": len(results),
    "files": sorted(results, key=lambda item: item["id"]),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Mirrored {len(results)} Lesson 1/2 source PDFs into {OUT}")
