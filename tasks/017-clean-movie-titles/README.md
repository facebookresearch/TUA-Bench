# local/017-clean-movie-titles

Benchmark task for translating OSWorld LibreOffice Calc example `a9f325aa-8c05-4e4f-8341-9e4358565f4f` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: I want to copy the movie titles from the 'Garbage Movie Titles' column to the 'Clean Movie Titles' column. Please remove redundant whitespace and canonicalize letter casing by capitalizing the first letter of each word and leaving the other letters lowercase. Finish the work and don't touch irrelevant regions, even if they are blank.
- Main output path: `/app/Movie_title_garbage_clean.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `sheet_data`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `sheet_data`.
- The local output contract at `/app/Movie_title_garbage_clean.xlsx`.

## What Was Simplified

- The original `/home/user/...` paths are translated to the local Harbor workspace under `/app`.
- OSWorld launch automation and save-hotkey postconfig are simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-calc`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages so Calc can still be launched from the terminal
- only the Python dependencies needed by the verifier

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The workbook must be saved in place at `/app/Movie_title_garbage_clean.xlsx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing artifact with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Calc evaluator helpers with only local path and remote-fetch adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
