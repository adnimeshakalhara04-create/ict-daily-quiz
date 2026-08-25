from __future__ import annotations

import base64
import io
import json
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "incoming"
ASSETS = ROOT / "daily_assets"
MANIFEST = ROOT / "quiz-data.json"
BASELINE_ZIP = ROOT / "daily-quiz-cropped-images-under-25MB.zip"
REPAIRS = ROOT / "repairs"
PREBUILT = ROOT / "prebuilt" / "quiz21-23"

SIDE_MARGIN_PT = 38
CONTINUATION_TOP_PT = 42
BOTTOM_MARGIN_PT = 30
BOUNDARY_PAD_PT = 6
RENDER_SCALE = 2.3
STITCH_GAP_PX = 14

QUIZ_RE = re.compile(r"(?i)\bquiz[\s_-]*0*(\d{1,3})\b")
START_RE = re.compile(r"^\s*([1-5])\.\s+\S")
ANSWER_RE = re.compile(r"(?im)\bAnswer\s*:\s*([1-5])\s*\)")

PREBUILT_ANSWERS = {
    21: [3, 2, 2, 2, 2],
    22: [5, 2, 3, 5, 4],
    23: [5, 3, 2, 3, 3],
}


@dataclass(frozen=True)
class Start:
    number: int
    page: int
    y0: float


def load_manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    answers = data.get("answers")
    if not isinstance(answers, list) or not answers:
        raise RuntimeError("quiz-data.json has no answers array")
    for idx, row in enumerate(answers, 1):
        if not isinstance(row, list) or len(row) != 5 or any(v not in [1, 2, 3, 4, 5] for v in row):
            raise RuntimeError(f"Invalid answer row for Quiz {idx:02d}")
    return data


def save_manifest(data: dict) -> None:
    data["quizCount"] = len(data["answers"])
    data["questionCount"] = len(data["answers"]) * 5
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_kind(path: Path) -> str | None:
    text = str(path).lower().replace("\\", "/")
    if "marking" in text:
        return "markings"
    if "question" in text:
        return "questions"
    return None


def extract_qnum_from_name(path: Path) -> int | None:
    stem = path.stem.lower()
    match = re.search(r"(?:^|[^a-z])q[\s_-]*0*(\d{1,2})(?:[^0-9]|$)", stem)
    if match:
        return int(match.group(1))
    nums = re.findall(r"\d+", stem)
    if nums:
        number = int(nums[-1])
        if 1 <= number <= 5:
            return number
    return None


def save_as_webp(image: Image.Image, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dst, "WEBP", quality=88, method=6)


def convert_to_webp(src: Path, dst: Path) -> None:
    with Image.open(src) as image:
        save_as_webp(image, dst)


def repair_q14_bytes() -> bytes:
    parts = sorted(REPAIRS.glob("q14-marking-q02.part*.b64"))
    if not parts:
        raise RuntimeError("Quiz 14 marking repair parts are missing")
    payload = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    data = base64.b64decode(payload, validate=True)
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    return data


def bootstrap_assets() -> None:
    expected = [
        ASSETS / kind / f"quiz-{quiz:02d}" / f"q-{number:02d}.webp"
        for quiz in range(1, 18)
        for kind in ("questions", "markings")
        for number in range(1, 6)
    ]
    if all(path.exists() and path.stat().st_size > 1000 for path in expected):
        return
    if not BASELINE_ZIP.exists():
        raise RuntimeError(f"Baseline archive missing: {BASELINE_ZIP.name}")

    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    ASSETS.mkdir(parents=True)
    repair = repair_q14_bytes()
    copied = set()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(BASELINE_ZIP) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Baseline archive CRC failed at: {bad}")
            archive.extractall(temp_path)

        for src in temp_path.rglob("*"):
            if not src.is_file() or src.suffix.lower() not in {".webp", ".png", ".jpg", ".jpeg"}:
                continue
            relative = str(src.relative_to(temp_path)).replace("\\", "/")
            quiz_match = QUIZ_RE.search(relative)
            kind = normalize_kind(src)
            number = extract_qnum_from_name(src)
            if not quiz_match or not kind or number is None:
                continue
            quiz = int(quiz_match.group(1))
            if not (1 <= quiz <= 17 and 1 <= number <= 5):
                continue
            dst = ASSETS / kind / f"quiz-{quiz:02d}" / f"q-{number:02d}.webp"
            if quiz == 14 and kind == "markings" and number == 2 and src.stat().st_size == 0:
                with Image.open(io.BytesIO(repair)) as image:
                    save_as_webp(image, dst)
                print("Quiz 14 marking q-02: repaired verified zero-byte baseline asset")
            else:
                convert_to_webp(src, dst)
            copied.add((quiz, kind, number))

    if len(copied) != 170:
        missing = [
            f"{quiz:02d}/{kind}/q-{number:02d}"
            for quiz in range(1, 18)
            for kind in ("questions", "markings")
            for number in range(1, 6)
            if (quiz, kind, number) not in copied
        ]
        raise RuntimeError(f"Baseline normalization found {len(copied)}/170 assets; missing {missing[:12]}")


def group_incoming() -> dict[int, dict[str, Path]]:
    groups: dict[int, dict[str, Path]] = {}
    if not INCOMING.exists():
        return groups
    for path in sorted(INCOMING.glob("*.pdf")):
        match = QUIZ_RE.search(path.name)
        if not match:
            continue
        quiz = int(match.group(1))
        kind = "marking" if "marking" in path.name.lower() else "question"
        slot = groups.setdefault(quiz, {})
        if kind in slot:
            raise RuntimeError(f"More than one {kind} PDF found for Quiz {quiz:02d}")
        slot[kind] = path
    return groups


def line_text(line: dict) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", []))


META_PATTERNS = (
    "2028 quiz series",
    "#ictfromabc",
    "all rights reserved",
    "information and communication technology",
    "ravindu bandaranayake",
)


def is_metadata_line(text: str) -> bool:
    clean = " ".join(text.lower().split())
    if not clean:
        return True
    if any(token in clean for token in META_PATTERNS):
        return True
    return bool(re.fullmatch(r"-?\s*\d+\s*-?", clean))


def meaningful_content_bottom(page: fitz.Page, top: float, hard_bottom: float) -> float:
    max_y = top
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                text = line_text(line).strip()
                if is_metadata_line(text):
                    continue
                bbox = line.get("bbox") or (0, 0, 0, 0)
                y0, y1 = float(bbox[1]), float(bbox[3])
                if y1 <= top + 1 or y0 >= hard_bottom - 1:
                    continue
                max_y = max(max_y, min(y1, hard_bottom))
        elif block.get("type") == 1:
            bbox = block.get("bbox") or (0, 0, 0, 0)
            y0, y1 = float(bbox[1]), float(bbox[3])
            if y1 <= top + 1 or y0 >= hard_bottom - 1:
                continue
            max_y = max(max_y, min(y1, hard_bottom))
    return min(hard_bottom, max_y + 12)


def find_question_starts(doc: fitz.Document) -> list[Start]:
    found: dict[int, Start] = {}
    for page_number, page in enumerate(doc):
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                text = line_text(line).strip()
                match = START_RE.match(text)
                if match:
                    number = int(match.group(1))
                    if number not in found:
                        bbox = line.get("bbox") or (0, 0, 0, 0)
                        found[number] = Start(number, page_number, float(bbox[1]))
    if sorted(found) != [1, 2, 3, 4, 5]:
        raise RuntimeError(f"Could not uniquely locate question starts 1–5; found {sorted(found)}")
    starts = [found[number] for number in range(1, 6)]
    if any((b.page, b.y0) <= (a.page, a.y0) for a, b in zip(starts, starts[1:])):
        raise RuntimeError("Question starts are not in ascending document order")
    return starts


def page_clip(page: fitz.Page, top: float, bottom: float) -> fitz.Rect:
    left = min(SIDE_MARGIN_PT, page.rect.width * 0.12)
    right = page.rect.width - left
    top = max(0, min(top, page.rect.height - 2))
    bottom = max(top + 2, min(bottom, page.rect.height))
    return fitz.Rect(left, top, right, bottom)


def render_clip(page: fitz.Page, rect: fitz.Rect) -> Image.Image:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), clip=rect, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def build_crop(doc: fitz.Document, start: Start, next_start: Start | None) -> Image.Image:
    end_page = next_start.page if next_start else len(doc) - 1
    pieces: list[Image.Image] = []
    for page_number in range(start.page, end_page + 1):
        page = doc[page_number]
        top = max(0, start.y0 - BOUNDARY_PAD_PT) if page_number == start.page else CONTINUATION_TOP_PT
        hard_bottom = next_start.y0 - BOUNDARY_PAD_PT if next_start and page_number == next_start.page else page.rect.height - BOTTOM_MARGIN_PT
        bottom = meaningful_content_bottom(page, top, hard_bottom)
        if bottom <= top + 3:
            continue
        pieces.append(render_clip(page, page_clip(page, top, bottom)))
        if next_start and page_number == next_start.page:
            break
    if not pieces:
        raise RuntimeError(f"No crop content produced for question {start.number}")
    if len(pieces) == 1:
        return pieces[0]
    width = max(image.width for image in pieces)
    height = sum(image.height for image in pieces) + STITCH_GAP_PX * (len(pieces) - 1)
    merged = Image.new("RGB", (width, height), "white")
    y = 0
    for image in pieces:
        merged.paste(image, ((width - image.width) // 2, y))
        y += image.height + STITCH_GAP_PX
    return merged


def extract_answers(marking_doc: fitz.Document, starts: list[Start]) -> list[int]:
    answers: list[int] = []
    for index, start in enumerate(starts):
        next_start = starts[index + 1] if index < 4 else None
        chunks: list[str] = []
        end_page = next_start.page if next_start else len(marking_doc) - 1
        for page_number in range(start.page, end_page + 1):
            page = marking_doc[page_number]
            top = start.y0 if page_number == start.page else CONTINUATION_TOP_PT
            bottom = next_start.y0 if next_start and page_number == next_start.page else page.rect.height
            if bottom > top + 2:
                chunks.append(page.get_text("text", clip=page_clip(page, top, bottom)))
            if next_start and page_number == next_start.page:
                break
        matches = ANSWER_RE.findall("\n".join(chunks))
        if len(matches) != 1:
            raise RuntimeError(f"Marking PDF question {start.number}: expected one Answer line, found {matches}")
        answers.append(int(matches[0]))
    return answers


def process_quiz(quiz: int, question_pdf: Path, marking_pdf: Path) -> list[int]:
    with fitz.open(question_pdf) as question_doc, fitz.open(marking_pdf) as marking_doc:
        question_starts = find_question_starts(question_doc)
        marking_starts = find_question_starts(marking_doc)
        answers = extract_answers(marking_doc, marking_starts)
        for kind, doc, starts in (("questions", question_doc, question_starts), ("markings", marking_doc, marking_starts)):
            target = ASSETS / kind / f"quiz-{quiz:02d}"
            if target.exists():
                shutil.rmtree(target)
            for index, start in enumerate(starts):
                next_start = starts[index + 1] if index < 4 else None
                save_as_webp(build_crop(doc, start, next_start), target / f"q-{index + 1:02d}.webp")
    return answers


def install_prebuilt_21_23(manifest: dict) -> None:
    current = len(manifest["answers"])
    if current >= 23:
        return
    if current != 20:
        raise RuntimeError(f"Prebuilt Quiz 21–23 expects site to end at Quiz 20, currently {current}")
    parts = sorted(PREBUILT.glob("part*"))
    if not parts:
        raise RuntimeError("Verified Quiz 21–23 prebuilt bundle is missing")
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    payload = base64.b64decode(encoded, validate=True)
    with tempfile.TemporaryDirectory() as td:
        archive_path = Path(td) / "bundle.zip"
        archive_path.write_bytes(payload)
        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Quiz 21–23 prebuilt ZIP failed at {bad}")
            archive.extractall(td)
        copied = set()
        for src in Path(td).rglob("*.png"):
            rel = str(src.relative_to(td)).replace("\\", "/")
            quiz_match = QUIZ_RE.search(rel)
            kind = normalize_kind(src)
            number = extract_qnum_from_name(src)
            if not quiz_match or not kind or number is None:
                continue
            quiz = int(quiz_match.group(1))
            if quiz not in PREBUILT_ANSWERS:
                continue
            dst = ASSETS / kind / f"quiz-{quiz:02d}" / f"q-{number:02d}.webp"
            convert_to_webp(src, dst)
            copied.add((quiz, kind, number))
        if len(copied) != 30:
            raise RuntimeError(f"Quiz 21–23 bundle produced {len(copied)}/30 assets")
    for quiz in (21, 22, 23):
        manifest["answers"].append(PREBUILT_ANSWERS[quiz])
        print(f"Quiz {quiz:02d}: installed verified crops, answers={PREBUILT_ANSWERS[quiz]}")


def verify_all_assets(quiz_count: int) -> None:
    bad = []
    for quiz in range(1, quiz_count + 1):
        for kind in ("questions", "markings"):
            for number in range(1, 6):
                path = ASSETS / kind / f"quiz-{quiz:02d}" / f"q-{number:02d}.webp"
                if not path.exists() or path.stat().st_size <= 1000:
                    bad.append(str(path.relative_to(ROOT)))
                    continue
                try:
                    with Image.open(path) as image:
                        image.verify()
                except Exception as exc:
                    bad.append(f"{path.relative_to(ROOT)} ({exc})")
    if bad:
        raise RuntimeError(f"Missing/corrupt generated assets: {bad[:12]}")


def main() -> None:
    bootstrap_assets()
    manifest = load_manifest()
    groups = group_incoming()
    current = len(manifest["answers"])

    for quiz in [number for number in sorted(groups) if number > current]:
        if quiz != current + 1:
            raise RuntimeError(f"Quiz sequence gap: site ends at {current:02d}, next upload is {quiz:02d}")
        pair = groups[quiz]
        if set(pair) != {"question", "marking"}:
            raise RuntimeError(f"Quiz {quiz:02d} needs question + MARKING PDFs; found {sorted(pair)}")
        answers = process_quiz(quiz, pair["question"], pair["marking"])
        manifest["answers"].append(answers)
        current += 1
        print(f"Quiz {quiz:02d}: answers={answers}")

    if len(manifest["answers"]) == 20:
        install_prebuilt_21_23(manifest)

    save_manifest(manifest)
    verify_all_assets(len(manifest["answers"]))
    print(f"Daily Quiz build verified: {len(manifest['answers'])} quizzes, {len(manifest['answers']) * 10} WEBP assets")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
