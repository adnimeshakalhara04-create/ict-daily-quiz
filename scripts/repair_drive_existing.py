#!/usr/bin/env python3
"""Repair missing Drive quiz PDF/crop files using already-verified incoming PDFs.

This never removes existing files or duplicate folders. It chooses the most complete
existing folder whenever legacy folders share the same visible name.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

import sync_google_drive as existing

FOLDER_MIME = "application/vnd.google-apps.folder"
FROM = int(os.getenv("REPAIR_FROM", "27"))
TO = int(os.getenv("REPAIR_TO", "95"))
if FROM < 1 or TO > 999 or FROM > TO:
    raise SystemExit("Invalid REPAIR_FROM/REPAIR_TO range")

def children(service, parent):
    result = []
    page = None
    while True:
        response = service.files().list(
            q=f"'{parent}' in parents and trashed = false",
            fields="nextPageToken,files(id,name,mimeType,size)",
            pageSize=1000,
            pageToken=page,
        ).execute()
        result.extend(response.get("files", []))
        page = response.get("nextPageToken")
        if not page:
            break
    return result

def named_folder(rows, name):
    matches = [r for r in rows if r.get("mimeType") == FOLDER_MIME and
               r.get("name", "").strip().casefold() == name.strip().casefold()]
    return matches

def ensure(service, parent, name, *, crop_quiz=False):
    matches = named_folder(children(service, parent), name)
    if not matches:
        return existing.ensure_folder(service, parent, name)
    if len(matches) == 1:
        return matches[0]["id"]

    def completeness(row):
        if not crop_quiz:
            return 0
        subfolders = children(service, row["id"])
        score = 0
        for kind in ("Questions", "Markings"):
            for sub in named_folder(subfolders, kind):
                score += sum(
                    1 for f in children(service, sub["id"])
                    if f.get("name") in {f"q-{n:02d}.webp" for n in range(1, 6)}
                    and int(f.get("size") or 0) > 0
                )
        return score

    selected = sorted(matches, key=lambda r: (-completeness(r), r["id"]))[0]
    print(f"WARNING: {len(matches)} duplicate folders named {name!r}; "
          f"using {selected['id']}, leaving others untouched")
    return selected["id"]

def ensure_present(service, folder, path):
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"Missing local generated asset: {path}")
    current = next((item for item in children(service, folder)
                    if item["name"] == path.name and int(item.get("size") or 0) > 0), None)
    if current:
        return False
    existing.upload_or_replace(service, folder, path)
    return True

def main():
    credential_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if credential_json:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credential_json), scopes=existing.SCOPES
        )
        print("Drive auth: service account")
    else:
        import google.auth
        try:
            credentials, _ = google.auth.default(scopes=existing.SCOPES)
        except google.auth.exceptions.DefaultCredentialsError as exc:
            raise SystemExit(
                "No Drive credentials. In Colab call google.colab.auth.authenticate_user() first."
            ) from exc
        print("Drive auth: user OAuth / Google ADC")
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    added = 0
    verified = 0
    for quiz in range(FROM, TO + 1):
        label = f"Quiz {quiz:02d}"
        raw_folder = ensure(service, existing.RAW_PARENT_ID, label)
        for suffix in (".pdf", " MARKING.pdf"):
            filename = f"2028 QUIZ {quiz}{suffix}"
            added += ensure_present(service, raw_folder, existing.INCOMING / filename)

        crop_folder = ensure(service, existing.CROP_PARENT_ID, label, crop_quiz=True)
        for display, key in (("Questions", "questions"), ("Markings", "markings")):
            folder = ensure(service, crop_folder, display)
            for n in range(1, 6):
                crop = existing.ASSETS / key / f"quiz-{quiz:02d}" / f"q-{n:02d}.webp"
                added += ensure_present(service, folder, crop)
            stored = {f["name"] for f in children(service, folder)
                      if int(f.get("size") or 0) > 0}
            expected = {f"q-{n:02d}.webp" for n in range(1, 6)}
            missing = expected - stored
            if missing:
                raise RuntimeError(f"{label} {display}: still missing {sorted(missing)}")
        verified += 1
        print(f"Verified {label}: PDF pair + 10 crop images")

    print(f"COMPLETE: {verified} Drive quiz folders verified, "
          f"{added} missing files restored. No existing files deleted.")

if __name__ == "__main__":
    main()
