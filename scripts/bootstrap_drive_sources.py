from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "incoming"
MANIFEST = ROOT / "quiz-data.json"
REPORT_PATH = Path(os.environ.get("DRIVE_BOOTSTRAP_REPORT", "/tmp/drive-bootstrap.json"))
RAW_PARENT_ID = os.environ.get("DRIVE_RAW_PARENT_ID", "1I9fU_ojRQBS-U3_5slnkWGN_SIsgRjmN")
FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive"]
QUIZ_RE = re.compile(r"(?i)\bquiz[\s_-]*0*(\d{1,3})\b")


def validate_pdf(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"Drive PDF is missing/too small: {path}")
    if path.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"Drive file is not a valid PDF: {path}")


def highest_source_quiz() -> int:
    highest = 0
    if INCOMING.exists():
        for path in INCOMING.glob("*.pdf"):
            match = QUIZ_RE.search(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    if highest:
        return highest
    if MANIFEST.exists():
        try:
            return int(json.loads(MANIFEST.read_text(encoding="utf-8")).get("quizCount", 0))
        except Exception:
            return 0
    return 0


def list_quiz_folders(service) -> dict[int, str]:
    folders: dict[int, str] = {}
    page_token = None
    while True:
        response = service.files().list(
            q=(
                f"'{RAW_PARENT_ID}' in parents and "
                f"mimeType = '{FOLDER_MIME}' and trashed = false"
            ),
            fields="nextPageToken,files(id,name)",
            pageSize=1000,
            pageToken=page_token,
            spaces="drive",
        ).execute()
        for row in response.get("files", []):
            match = re.fullmatch(r"(?i)quiz\s+0*(\d{1,3})", row.get("name", "").strip())
            if match:
                folders[int(match.group(1))] = row["id"]
        page_token = response.get("nextPageToken")
        if not page_token:
            return folders


def list_pdf_pair(service, folder_id: str, quiz: int) -> dict[str, dict]:
    response = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id,name,mimeType,size)",
        pageSize=100,
        spaces="drive",
    ).execute()
    pair: dict[str, dict] = {}
    for row in response.get("files", []):
        name = row.get("name", "")
        match = QUIZ_RE.search(name)
        if not match or int(match.group(1)) != quiz:
            continue
        if row.get("mimeType") != "application/pdf" and not name.lower().endswith(".pdf"):
            continue
        kind = "marking" if "marking" in name.lower() else "question"
        pair[kind] = row
    return pair


def download_file(service, file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    destination.write_bytes(buffer.getvalue())
    validate_pdf(destination)


def write_report(quizzes: list[int], start: int) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps({"start": start, "quizzes": [{"quiz": q} for q in quizzes]}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    start = highest_source_quiz()
    raw_credentials = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw_credentials:
        write_report([], start)
        print("Drive source bootstrap skipped: GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
        return

    info = json.loads(raw_credentials)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    folders = list_quiz_folders(service)

    downloaded: list[int] = []
    expected = start + 1
    while expected in folders:
        pair = list_pdf_pair(service, folders[expected], expected)
        if set(pair) != {"question", "marking"}:
            print(f"Drive Quiz {expected:02d}: incomplete pair; stopping sequential backfill.")
            break

        question_dst = INCOMING / f"2028 QUIZ {expected}.pdf"
        marking_dst = INCOMING / f"2028 QUIZ {expected} MARKING.pdf"
        download_file(service, pair["question"]["id"], question_dst)
        download_file(service, pair["marking"]["id"], marking_dst)
        downloaded.append(expected)
        print(f"Drive Quiz {expected:02d}: downloaded source question + marking PDFs")
        expected += 1

    write_report(downloaded, start)
    if downloaded:
        print("Drive source bootstrap complete: " + ", ".join(f"Quiz {q:02d}" for q in downloaded))
    else:
        print(f"Drive source bootstrap: no sequential quiz after Quiz {start:02d}.")


if __name__ == "__main__":
    main()
