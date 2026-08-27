from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site-build"
SOURCES = SITE / "sources"
OUT = SITE / "essay_pages"

ESSAY_IDS = {
    "1aNyguRdOMTNcYYAIqc_C1Ytf9N4CUQt3",
    "1xkXsZuUxmbSE29P_KILTezuRnR9GEYYx",
}

OUT.mkdir(parents=True, exist_ok=True)

for file_id in sorted(ESSAY_IDS):
    pdf_path = SOURCES / f"{file_id}.pdf"
    if not pdf_path.exists() or pdf_path.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"Bundled essay PDF missing or invalid: {file_id}")

    target_dir = OUT / file_id
    target_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        target = target_dir / f"page-{index}.webp"
        image.save(target, "WEBP", quality=88, method=6)
        print(f"Essay local page ready: {file_id} page {index} ({target.stat().st_size} bytes)")
    doc.close()
