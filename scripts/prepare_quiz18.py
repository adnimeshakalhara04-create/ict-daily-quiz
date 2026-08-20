from pathlib import Path
import base64, gzip, io, re, shutil, zipfile

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".quiz_sources" / "quiz18"
TMP = ROOT / ".quiz_build" / "quiz18"
ASSETS = ROOT / "daily_assets"


def rebuild_pdf(parts_dir: Path, out_pdf: Path):
    parts = sorted(parts_dir.glob("part*"))
    if not parts:
        raise RuntimeError(f"No source parts found in {parts_dir}")
    encoded = "".join(p.read_text().strip() for p in parts)
    raw = gzip.decompress(base64.b64decode(encoded))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.write_bytes(raw)


def render_pdf(pdf_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(200 / 72, 200 / 72)
    rendered = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        p = out_dir / f"page-{i+1}.png"
        pix.save(p)
        rendered.append(p)
    return rendered


def crop_page(path: Path, box):
    return Image.open(path).convert("RGB").crop(box)


def save_png(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def main():
    TMP.mkdir(parents=True, exist_ok=True)

    question_pdf = TMP / "quiz18.pdf"
    marking_pdf = TMP / "quiz18_marking.pdf"
    rebuild_pdf(SRC / "question", question_pdf)
    rebuild_pdf(SRC / "marking", marking_pdf)

    q_pages = render_pdf(question_pdf, TMP / "question_pages")
    m_pages = render_pdf(marking_pdf, TMP / "marking_pages")
    if len(q_pages) != 3 or len(m_pages) != 8:
        raise RuntimeError(f"Unexpected page count: question={len(q_pages)}, marking={len(m_pages)}")

    # Coordinates were visually verified against the source PDFs rendered at 200 dpi.
    q_specs = {
        1: (1, (115, 455, 1535, 995)),
        2: (1, (115, 985, 1535, 2075)),
        3: (2, (115, 125, 1535, 905)),
        4: (2, (115, 895, 1535, 1605)),
        5: (3, (115, 125, 1535, 1065)),
    }
    m_specs = {
        1: [(1, (115, 255, 1535, 2260)), (2, (115, 120, 1535, 1210))],
        2: [(3, (115, 125, 1535, 2260)), (4, (115, 115, 1535, 875))],
        3: [(4, (115, 865, 1535, 2260)), (5, (115, 115, 1535, 1160))],
        4: [(6, (115, 115, 1535, 2260)), (7, (115, 115, 1535, 525))],
        5: [(7, (115, 505, 1535, 2260)), (8, (115, 115, 1535, 2040))],
    }

    q_dir = ASSETS / "questions" / "quiz-18"
    m_dir = ASSETS / "markings" / "quiz-18"
    q_dir.mkdir(parents=True, exist_ok=True)
    m_dir.mkdir(parents=True, exist_ok=True)

    for q, (page_no, box) in q_specs.items():
        save_png(crop_page(q_pages[page_no - 1], box), q_dir / f"q-{q:02d}.png")

    for q, pieces in m_specs.items():
        imgs = [crop_page(m_pages[p - 1], box) for p, box in pieces]
        width = max(im.width for im in imgs)
        gap = 16
        height = sum(im.height for im in imgs) + gap * (len(imgs) - 1)
        merged = Image.new("RGB", (width, height), "white")
        y = 0
        for im in imgs:
            merged.paste(im, (0, y))
            y += im.height + gap
        save_png(merged, m_dir / f"q-{q:02d}.png")

    expected = [q_dir / f"q-{i:02d}.png" for i in range(1, 6)] + [m_dir / f"q-{i:02d}.png" for i in range(1, 6)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        raise RuntimeError("Quiz 18 crop generation failed")

    app = ROOT / "app.js"
    text = app.read_text()
    if "[2,1,2,2,1]" not in text:
        text = text.replace("    [2,2,3,2,3],[3,1,3,2,2]\n", "    [2,2,3,2,3],[3,1,3,2,2],[2,1,2,2,1]\n")
    text = text.replace("Array.from({length:17}", "Array.from({length:18}")
    text = text.replace("AUG 01–17 · DAILY QUIZ", "AUG 01–18 · DAILY QUIZ")
    text = text.replace("අගෝස්තු 01 සිට 17 දක්වා Daily Quiz 17ක ප්‍රශ්න 85ම", "අගෝස්තු 01 සිට 18 දක්වා Daily Quiz 18ක ප්‍රශ්න 90ම")
    text = text.replace("Start all 85 questions", "Start all 90 questions")
    text = text.replace("<strong>85</strong><span>QUESTIONS</span>", "<strong>90</strong><span>QUESTIONS</span>")
    text = text.replace("<strong>17</strong><span>DAILY QUIZZES</span>", "<strong>18</strong><span>DAILY QUIZZES</span>")
    text = text.replace("QUIZ 01 සිට QUIZ 17 දක්වා", "QUIZ 01 සිට QUIZ 18 දක්වා")
    text = text.replace("'QUIZ 01–17'", "'QUIZ 01–18'")
    app.write_text(text)

    # Final invariant: 18 quizzes x (5 question + 5 marking) = 180 image files.
    files = [p for p in ASSETS.rglob("*.png") if p.is_file()]
    if len(files) != 180:
        raise RuntimeError(f"Expected 180 PNG assets after Quiz 18, found {len(files)}")


if __name__ == "__main__":
    main()
