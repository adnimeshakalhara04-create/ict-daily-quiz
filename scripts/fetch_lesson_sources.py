from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import gdown

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


def valid_pdf(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 1000 and path.read_bytes()[:5] == b"%PDF-"


def download_pdf(file_id: str) -> dict:
    target = OUT / f"{file_id}.pdf"
    if valid_pdf(target):
        return {"id": file_id, "bytes": target.stat().st_size, "cached": True}

    target.unlink(missing_ok=True)
    last_error = None

    try:
        result = gdown.download(id=file_id, output=str(target), quiet=True)
        if result and valid_pdf(target):
            return {"id": file_id, "bytes": target.stat().st_size, "cached": False}
        if target.exists():
            last_error = RuntimeError(
                f"gdown returned non-PDF content ({target.stat().st_size} bytes)"
            )
            target.unlink(missing_ok=True)
    except Exception as exc:
        last_error = exc
        target.unlink(missing_ok=True)

    urls = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
    ]
    for attempt in range(2):
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as response:
                    data = response.read()
                if data.startswith(b"%PDF-") and len(data) > 1000:
                    target.write_bytes(data)
                    return {"id": file_id, "bytes": len(data), "cached": False}
                last_error = RuntimeError(
                    f"Drive source returned non-PDF content ({len(data)} bytes)"
                )
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_error = exc
        time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(str(last_error or "unknown Drive download error"))


results = []
failures = []
with ThreadPoolExecutor(max_workers=min(4, len(ids))) as pool:
    futures = {pool.submit(download_pdf, file_id): file_id for file_id in ids}
    for future in as_completed(futures):
        file_id = futures[future]
        try:
            result = future.result()
            results.append(result)
            print(f"Local source ready: {result['id']} ({result['bytes']} bytes)")
        except Exception as exc:
            failures.append({"id": file_id, "error": str(exc)})
            print(f"LOCAL SOURCE MISSING: {file_id} :: {exc}")

manifest = {
    "source": "Lesson 1 + 2 quiz-data Drive file IDs",
    "requested": len(ids),
    "count": len(results),
    "missingCount": len(failures),
    "files": sorted(results, key=lambda item: item["id"]),
    "missing": sorted(failures, key=lambda item: item["id"]),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Mirrored {len(results)}/{len(ids)} Lesson 1/2 source PDFs into {OUT}")
if failures:
    print("Protected/unavailable source IDs: " + ", ".join(item["id"] for item in sorted(failures, key=lambda item: item["id"])))
