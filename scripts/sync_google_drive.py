from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "incoming"
ASSETS = ROOT / "daily_assets"
TELEGRAM_REPORT = Path(os.environ.get("TELEGRAM_INGEST_REPORT", "/tmp/telegram-ingest.json"))
DRIVE_BOOTSTRAP_REPORT = Path(os.environ.get("DRIVE_BOOTSTRAP_REPORT", "/tmp/drive-bootstrap.json"))

# These are folder identifiers, not credentials. They match the existing Drive
# structure used by ICT Daily Quiz 2028 and may be overridden with env vars.
RAW_PARENT_ID = os.environ.get("DRIVE_RAW_PARENT_ID", "1I9fU_ojRQBS-U3_5slnkWGN_SIsgRjmN")
CROP_PARENT_ID = os.environ.get("DRIVE_CROP_PARENT_ID", "1mYROVvho24eDc3ys_OA2C2dmDq5cZ9NL")
FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def find_child(service, parent_id: str, name: str, mime_type: str | None = None) -> dict | None:
    clauses = [
        f"'{parent_id}' in parents",
        f"name = '{escape_query(name)}'",
        "trashed = false",
    ]
    if mime_type:
        clauses.append(f"mimeType = '{mime_type}'")
    result = service.files().list(
        q=" and ".join(clauses),
        fields="files(id,name,mimeType)",
        pageSize=10,
        spaces="drive",
    ).execute()
    files = result.get("files", [])
    if files:
        return files[0]

    # Some historical quiz folders contain accidental trailing spaces. Reuse
    # them rather than creating duplicate folders with visually identical names.
    if mime_type == FOLDER_MIME:
        result = service.files().list(
            q=(
                f"'{parent_id}' in parents and mimeType = '{FOLDER_MIME}' "
                "and trashed = false"
            ),
            fields="files(id,name,mimeType)",
            pageSize=1000,
            spaces="drive",
        ).execute()
        wanted = name.strip().casefold()
        for row in result.get("files", []):
            if row.get("name", "").strip().casefold() == wanted:
                return row
    return None


def ensure_folder(service, parent_id: str, name: str) -> str:
    existing = find_child(service, parent_id, name, FOLDER_MIME)
    if existing:
        return existing["id"]
    created = service.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id",
    ).execute()
    print(f"Drive: created folder {name}")
    return created["id"]


def upload_or_replace(service, parent_id: str, local_path: Path) -> None:
    if not local_path.exists() or local_path.stat().st_size == 0:
        raise RuntimeError(f"Drive upload source missing: {local_path}")
    mime_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=False)
    existing = find_child(service, parent_id, local_path.name)
    if existing:
        service.files().update(
            fileId=existing["id"],
            body={"name": local_path.name},
            media_body=media,
            fields="id",
        ).execute()
        print(f"Drive: updated {local_path.name}")
    else:
        service.files().create(
            body={"name": local_path.name, "parents": [parent_id]},
            media_body=media,
            fields="id",
        ).execute()
        print(f"Drive: uploaded {local_path.name}")


def sync_quiz(service, quiz: int) -> None:
    quiz_name = f"Quiz {quiz:02d}"

    raw_quiz = ensure_folder(service, RAW_PARENT_ID, quiz_name)
    upload_or_replace(service, raw_quiz, INCOMING / f"2028 QUIZ {quiz}.pdf")
    upload_or_replace(service, raw_quiz, INCOMING / f"2028 QUIZ {quiz} MARKING.pdf")

    crop_quiz = ensure_folder(service, CROP_PARENT_ID, quiz_name)
    questions_folder = ensure_folder(service, crop_quiz, "Questions")
    markings_folder = ensure_folder(service, crop_quiz, "Markings")

    for number in range(1, 6):
        filename = f"q-{number:02d}.webp"
        upload_or_replace(
            service,
            questions_folder,
            ASSETS / "questions" / f"quiz-{quiz:02d}" / filename,
        )
        upload_or_replace(
            service,
            markings_folder,
            ASSETS / "markings" / f"quiz-{quiz:02d}" / filename,
        )


def report_quizzes() -> list[int]:
    quizzes: set[int] = set()
    for path in (DRIVE_BOOTSTRAP_REPORT, TELEGRAM_REPORT):
        if not path.exists():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        for row in report.get("quizzes", []):
            quizzes.add(int(row["quiz"]))
    return sorted(quizzes)


def main() -> None:
    raw_credentials = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw_credentials:
        print("Drive sync skipped: GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
        return

    quizzes = report_quizzes()
    if not quizzes:
        print("Drive sync: no new or backfilled quiz pair to upload.")
        return

    info = json.loads(raw_credentials)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    for quiz in quizzes:
        sync_quiz(service, quiz)

    print("Drive sync complete for: " + ", ".join(f"Quiz {quiz:02d}" for quiz in quizzes))


if __name__ == "__main__":
    main()
