# Daily Quiz Upload Inbox

Upload exactly two PDFs for each new quiz into this folder.

Example for Quiz 18:

- `2028 QUIZ 18.pdf`
- `2028 QUIZ 18 MARKING.pdf`

The GitHub Action detects the quiz number from the filename, extracts the five official answers from the MARKING PDF, creates five question crops and five marking crops, converts them to WEBP, verifies all ten files, and updates `quiz-data.json`.

Rules:

- Keep the word `QUIZ` and the quiz number in both filenames.
- The marking file must contain the word `MARKING`.
- Upload quizzes in order without skipping a number.
- If five question starts or five `Answer: N)` lines cannot be verified, the build fails instead of guessing.
