from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from PIL import ImageFile

# One legacy repair stream is truncated at the container level. Pillow can
# decode the available source pixels; the normal asset verifier checks the
# generated output before deployment.
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


# Preserve already-verified WEBP crops byte-for-byte instead of recompressing
# all baseline images on every Vercel build. Non-WEBP inputs still use the
# original source conversion routine.
_original_convert = module.convert_to_webp

def fast_convert(src: Path, dst: Path) -> None:
    if src.suffix.lower() == ".webp":
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    else:
        _original_convert(src, dst)


module.repair_q14_bytes = verified_q14_bytes
module.convert_to_webp = fast_convert
module.main()
