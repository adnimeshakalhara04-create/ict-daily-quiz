# ICT Daily Quiz 2028 — Telegram + Drive Automation

This repository contains an automated pipeline for `@ictfromabc28`:

1. On the first activated run, Google Drive is checked first for any complete sequential Quiz + Marking PDF pairs missing from the repository. This safely backfills existing historical quizzes such as Quiz 21+ from the authoritative raw Drive folders.
2. Puppeteer inspects the public Telegram channel preview and logs matching quiz/PDF posts as a lightweight discovery/verification layer.
3. Telethon/MTProto downloads complete new Quiz + Marking PDF pairs from Telegram. A quiz is never published with only one half of the pair.
4. The existing PyMuPDF/Pillow processor crops questions and markings to `q-01.webp` … `q-05.webp` and extracts the five answer values from the marking PDF.
5. The original PDFs are synchronized to the existing Google Drive `Daily Quiz/Quiz NN` folder.
6. Crops are synchronized to the existing Drive crop structure: `Quiz NN/Questions` and `Quiz NN/Markings`.
7. New source PDFs are committed to `main`. Vercel's Git integration then rebuilds and deploys the latest complete quiz automatically.

The scheduled workflow runs hourly, is sequential and idempotent, and makes no commit/deployment when there is nothing new. Duplicate or visually identical Drive folders are avoided by whitespace-normalized folder matching.

## Required GitHub Actions secrets

Configure these directly in **Repository Settings → Secrets and variables → Actions**. Never commit them or paste them into issues/chat.

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

### Telegram one-time authorization

Create an API application in Telegram's official developer portal to obtain the API ID and API hash. Then run locally:

```bash
python -m pip install telethon
python scripts/create_telegram_session.py
```

Telegram will ask for the account phone/login code (and 2-step-verification password if enabled). Put the printed StringSession directly into the `TELEGRAM_SESSION` GitHub secret. Do not share the StringSession, OTP, password, API hash, or other account secrets.

### Google Drive one-time authorization

Enable the Google Drive API for a Google Cloud project, create a service account and JSON key, and save the complete JSON as `GOOGLE_SERVICE_ACCOUNT_JSON`.

Share these two existing Drive folders with the service-account email as **Editor**:

- Raw parent: `Daily Quiz`
- Crop parent: `Daily Quiz Crop Images - Quiz 01-23`

The scripts use the existing parent folder IDs by default. Existing quiz folders are reused, including historical folder names that contain accidental leading/trailing spaces. New Quiz NN folders are created only when necessary.

## First activation

After the secrets are configured, open **Actions → ICT Daily Quiz Telegram Sync → Run workflow**.

The first successful run will:

- backfill complete sequential source PDFs already present in Drive but missing from GitHub;
- process/crop them and verify marking answers;
- continue immediately with the next complete Telegram quiz pair if one is available;
- synchronize the crops to Drive;
- commit only the source PDFs;
- let Vercel build generated assets and publish the new site version.

After that, the hourly schedule handles future channel posts automatically.
