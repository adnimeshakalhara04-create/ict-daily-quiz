from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "incoming"
MANIFEST = ROOT / "quiz-data.json"
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "ictfromabc28").lstrip("@")
REPORT_PATH = Path(os.environ.get("TELEGRAM_INGEST_REPORT", "/tmp/telegram-ingest.json"))
HISTORY_LIMIT = int(os.environ.get("TELEGRAM_HISTORY_LIMIT", "600"))

QUIZ_RE = re.compile(r"(?i)\b(?:2028\s*)?quiz[\s_-]*0*(\d{1,3})\b")


def current_quiz_floor() -> int:
    current = 0
    if MANIFEST.exists():
        try:
            current = int(json.loads(MANIFEST.read_text(encoding="utf-8")).get("quizCount", 0))
        except Exception:
            pass
    for path in INCOMING.glob("*.pdf") if INCOMING.exists() else []:
        match = QUIZ_RE.search(path.name)
        if match:
            current = max(current, int(match.group(1)))
    return current


def classify_message(message) -> tuple[int, str, str] | None:
    if not getattr(message, "document", None):
        return None

    file_obj = getattr(message, "file", None)
    filename = (getattr(file_obj, "name", None) or "").strip()
    mime_type = (getattr(file_obj, "mime_type", None) or "").lower()
    text = (getattr(message, "raw_text", None) or "").strip()

    if mime_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        return None

    combined = f"{filename}\n{text}"
    match = QUIZ_RE.search(combined)
    if not match:
        return None

    quiz = int(match.group(1))
    kind = "marking" if re.search(r"(?i)\bmarking\b", combined) else "question"
    return quiz, kind, filename


def validate_pdf(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"Downloaded PDF is missing/too small: {path}")
    if path.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"Downloaded file is not a PDF: {path}")


async def run() -> None:
    api_id_raw = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    session_string = os.environ.get("TELEGRAM_SESSION", "").strip()

    if not api_id_raw or not api_hash or not session_string:
        raise RuntimeError(
            "Missing TELEGRAM_API_ID, TELEGRAM_API_HASH or TELEGRAM_SESSION. "
            "Create them once and store them as GitHub Actions secrets; never commit them."
        )

    try:
        api_id = int(api_id_raw)
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_API_ID must be numeric") from exc

    INCOMING.mkdir(parents=True, exist_ok=True)
    current = current_quiz_floor()
    print(f"Telegram sync channel=@{CHANNEL}; repository floor=Quiz {current:02d}")

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("TELEGRAM_SESSION is not authorized")

        candidates: dict[int, dict[str, object]] = {}
        async for message in client.iter_messages(CHANNEL, limit=HISTORY_LIMIT):
            classified = classify_message(message)
            if not classified:
                continue
            quiz, kind, filename = classified
            if quiz <= current:
                continue
            slot = candidates.setdefault(quiz, {})
            # iter_messages is newest-first, so preserve the newest matching document.
            if kind not in slot:
                slot[kind] = message
                slot[f"{kind}_filename"] = filename

        downloaded: list[dict[str, object]] = []
        expected = current + 1
        while True:
            pair = candidates.get(expected)
            if not pair or "question" not in pair or "marking" not in pair:
                break

            question_dst = INCOMING / f"2028 QUIZ {expected}.pdf"
            marking_dst = INCOMING / f"2028 QUIZ {expected} MARKING.pdf"

            with tempfile.TemporaryDirectory(prefix=f"quiz-{expected:02d}-") as td:
                q_tmp = Path(td) / question_dst.name
                m_tmp = Path(td) / marking_dst.name
                await client.download_media(pair["question"], file=str(q_tmp))
                await client.download_media(pair["marking"], file=str(m_tmp))
                validate_pdf(q_tmp)
                validate_pdf(m_tmp)
                question_dst.write_bytes(q_tmp.read_bytes())
                marking_dst.write_bytes(m_tmp.read_bytes())

            downloaded.append(
                {
                    "quiz": expected,
                    "questionMessageId": int(pair["question"].id),
                    "markingMessageId": int(pair["marking"].id),
                    "question": question_dst.name,
                    "marking": marking_dst.name,
                }
            )
            print(f"Quiz {expected:02d}: downloaded question + marking PDFs")
            expected += 1

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(
                {
                    "channel": CHANNEL,
                    "repositoryFloor": current,
                    "quizzes": downloaded,
                    "nextExpected": expected,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        if not downloaded:
            print(f"No new complete sequential quiz pair found. Next expected: Quiz {expected:02d}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run())
