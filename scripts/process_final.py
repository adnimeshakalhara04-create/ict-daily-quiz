from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "process_incoming.py"
REPAIR = ROOT / "repairs" / "q14-marking-q02.png"

name = "daily_source_builder"
spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load Daily Quiz source builder")
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)


def verified_q14_bytes() -> bytes:
    data = REPAIR.read_bytes()
    if len(data) < 1000 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Quiz 14 marking repair PNG is missing or invalid")
    return data


_original_convert = module.convert_to_webp

def fast_convert(src: Path, dst: Path) -> None:
    if src.suffix.lower() == ".webp":
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    else:
        _original_convert(src, dst)


module.repair_q14_bytes = verified_q14_bytes
module.convert_to_webp = fast_convert

# Build the locally hosted source crops only through Quiz 20.
module.bootstrap_assets()
manifest = module.load_manifest()
groups = module.group_incoming()
current = len(manifest["answers"])
for quiz in [number for number in sorted(groups) if number > current and number <= 20]:
    if quiz != current + 1:
        raise RuntimeError(f"Quiz sequence gap: site ends at {current:02d}, next upload is {quiz:02d}")
    pair = groups[quiz]
    if set(pair) != {"question", "marking"}:
        raise RuntimeError(f"Quiz {quiz:02d} needs question + MARKING PDFs; found {sorted(pair)}")
    answers = module.process_quiz(quiz, pair["question"], pair["marking"])
    manifest["answers"].append(answers)
    current += 1
    print(f"Quiz {quiz:02d}: answers={answers}")

if len(manifest["answers"]) != 20:
    raise RuntimeError(f"Expected verified local source set through Quiz 20, got {len(manifest['answers'])}")

# Quiz 21–23 use the exact Google Drive crops in the browser. Keep their
# verified official answer rows in the same manifest so the bank totals 115.
for quiz in (21, 22, 23):
    manifest["answers"].append(module.PREBUILT_ANSWERS[quiz])
    print(f"Quiz {quiz:02d}: Drive crop mode, answers={module.PREBUILT_ANSWERS[quiz]}")

module.save_manifest(manifest)
module.verify_all_assets(20)
print("Daily Quiz source build verified: 23 quizzes / 115 questions; local crops 01-20, Drive crops 21-23")
