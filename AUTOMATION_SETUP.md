# ICT Daily Quiz 2028 — Telegram Automation

This repository contains an automated pipeline for `@ictfromabc28`:

1. Puppeteer inspects the public Telegram channel preview and logs matching quiz/PDF posts.
2. Telethon downloads complete Quiz + Marking PDF pairs from Telegram.
3. The existing PyMuPDF/Pillow processor crops questions and markings to `q-01.webp` … `q-05.webp` and extracts the five answer values from the marking PDF.
4. The original PDFs are synchronized to the existing Google Drive `Daily Quiz/Quiz NN` folder.
5. Crops are synchronized to the existing Drive crop structure: `Quiz NN/Questions` and `Quiz NN/Markings`.
6. The new source PDFs are committed to `main`. Vercel's Git integration builds and deploys the new quiz automatically.

The workflow runs hourly and is idempotent. It only publishes complete sequential Quiz + Marking pairs.

## Required GitHub Actions secrets

Configure these in **Repository Settings → Secrets and variables → Actions**. Never commit them.

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

Telegram will ask for the account phone/login code (and 2-step-verification password if enabled). Put the printed StringSession directly into the `TELEGRAM_SESSION` GitHub secret. Do not paste it into issues, commits, or chat messages.

### Google Drive one-time authorization

Enable the Google Drive API for a Google Cloud project, create a service account and JSON key, and save the complete JSON as `GOOGLE_SERVICE_ACCOUNT_JSON`.

Share these two existing Drive folders with the service-account email as **Editor**:

- Raw parent: `Daily Quiz`
- Crop parent: `Daily Quiz Crop Images - Quiz 01-23`

The script uses the existing folder IDs by default and continues the same structure for Quiz 24+.

## Manual test

After the secrets are configured, open **Actions → ICT Daily Quiz Telegram Sync → Run workflow**. A successful first run can backfill all complete sequential quizzes after Quiz 23 that are still in the configured Telegram history window.
