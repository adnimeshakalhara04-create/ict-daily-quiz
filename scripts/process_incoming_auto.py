from __future__ import annotations

import sys

import process_incoming as base


def main() -> None:
    base.bootstrap_assets()
    manifest = base.load_manifest()
    groups = base.group_incoming()

    while True:
        current = len(manifest["answers"])
        next_quiz = current + 1

        pair = groups.get(next_quiz)
        if pair is not None:
            if set(pair) != {"question", "marking"}:
                print(
                    f"Quiz {next_quiz:02d}: waiting for question + MARKING PDFs; "
                    f"found {sorted(pair)}"
                )
                break
            answers = base.process_quiz(next_quiz, pair["question"], pair["marking"])
            manifest["answers"].append(answers)
            print(f"Quiz {next_quiz:02d}: answers={answers}")
            continue

        # The repository already contains a verified prebuilt bridge for 21-23.
        # Install it exactly when the sequential build reaches Quiz 20, then keep
        # processing any incoming Quiz 24+ PDFs in the same run.
        if current == 20:
            base.install_prebuilt_21_23(manifest)
            continue

        break

    base.save_manifest(manifest)
    base.verify_all_assets(len(manifest["answers"]))

    deferred = sorted(number for number in groups if number > len(manifest["answers"]))
    if deferred:
        print(
            "Deferred out-of-sequence/incomplete incoming quizzes: "
            + ", ".join(f"{number:02d}" for number in deferred)
        )

    print(
        f"Daily Quiz build verified: {len(manifest['answers'])} quizzes, "
        f"{len(manifest['answers']) * 10} WEBP assets"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
