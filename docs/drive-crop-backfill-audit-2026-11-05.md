# ICT Daily Quiz 2028 — Google Drive Crop Backfill Audit

Verified: 2026-11-05

## Scope and results

- Original quiz set: **Quiz 01–95**, with **95 questions PDFs** and **95 marking PDFs** in the original-PDF Google Drive root.
- Previous Drive cropped-image audit found **248 missing expected WEBP filenames**:
  - Quiz 27 Markings q-05
  - Quiz 28 Markings q-05
  - Quiz 33 Markings q-02 and q-04
  - Quiz 38 Markings q-05
  - Quiz 45 Markings q-01
  - Quiz 71 Markings q-04 and q-05
  - Quiz 72–95 all ten images per quiz (240 images)
- **248 WEBP files generated from original PDF pages and uploaded** to their existing `Quiz NN/Questions` or `Quiz NN/Markings` Drive folders; all failed/blocked initial move requests were retried until files were in the destination folders.
- All **248 locally generated crops** passed WEBP-decoding, nonempty-size and SHA-256 manifest validation. Four representative uploaded Drive crops (Quiz 27 marking q-05, Quiz 33 marking q-02, Quiz 72 question q-01 and Quiz 95 marking q-03) were downloaded back and checked against local source SHA-256 hashes; all matched.
- Post-upload, all **95 Quiz folders**, both category subfolders (**190 folders total**), and the expected five filenames per category were individually listed. **950/950 expected WEBP images** are now present: 475 Questions + 475 Markings, with no unexpected files or duplicate filenames remaining inside the 190 target category folders.
- **19 pre-existing duplicate/legacy split files** were safely moved into a separate backup folder without permanent deletion. Existing expected files were otherwise preserved.

## Locations

- [Original PDF root](https://drive.google.com/drive/folders/1I9fU_ojRQBS-U3_5slnkWGN_SIsgRjmN)
- [Cropped-image root](https://drive.google.com/drive/folders/1mYROVvho24eDc3ys_OA2C2dmDq5cZ9NL)
- [Archived duplicates and split crops](https://drive.google.com/drive/folders/1R16UbxUvCMQfxcoXgxc6f7NxKfqgapE9)
- [Production site](https://ict-daily-quiz-2028-nimesha.vercel.app/)

## Production checks

The Vercel production quiz-data endpoint returned HTTP 200 with 95 quizzes, 475 questions and 95 marking-answer rows. Sample image assets returned HTTP 200. The repository generates assets during its production build from the incoming source PDFs; this report is an audit record, not a change to quiz answers or to original PDF content.

The previously removed failing GitHub Actions workflows remain removed. No service-account credentials, secrets, original PDFs or generated binary images are included in this report.

## Future validation

For a new quiz, verify that both original PDFs exist, five question and five marking WEBP files have the exact `q-01.webp` to `q-05.webp` names, all images decode correctly, marking answers agree with the source PDF, and the site deployment becomes READY.
