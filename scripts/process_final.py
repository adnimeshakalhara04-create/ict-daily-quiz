from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "process_incoming.py"
REPAIR = ROOT / "repairs" / "q14-marking-q02.png"

spec = importlib.util.spec_from_file_location("daily_source_builder", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load Daily Quiz source builder")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def verified_q14_bytes() -> bytes:
    data = REPAIR.read_bytes()
    if len(data) < 1000 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Verified Quiz 14 marking PNG is missing or invalid")
    return data


module.repair_q14_bytes = verified_q14_bytes
module.main()
