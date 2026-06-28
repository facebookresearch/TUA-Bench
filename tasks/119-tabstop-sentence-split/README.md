# local/119-tabstop-sentence-split

Benchmark task for translating OSWorld LibreOffice Writer example `0a0faba3-5580-44df-965d-f562a99b291c` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Writer`
- Local task description: Use LibreOffice Writer tabstops to keep the first three words left and the rest right-aligned.
- Main output path: `/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx`
- Verifier behavior: the exact OSWorld `check_tabstops` metric

## What Was Preserved

- The original LibreOffice Writer user intent and application constraint.
- The exact OSWorld `check_tabstops` metric.
- The in-place local document or artifact contract at `/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx`.

## What Was Simplified

- The original Desktop path is translated to the local Harbor workspace path `/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx`.
- The OSWorld GUI launch and save-hotkey postconfig are simplified to an explicit terminal-side file contract.
- The oracle normalizes the upstream gold text so each line has exactly three words before the tab while preserving the exact OSWorld tabstop positions.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-writer`
- `tmux` and `asciinema` for terminal session support
- `dbus-x11`, `xvfb`, and `xauth` so Writer can still be launched from the terminal
- `python-docx` as the only verifier Python dependency

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The document must be saved in place at `/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing artifact with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact into `/logs/artifacts/`
- `tests/test_outputs.py` ports the OSWorld `check_tabstops` metric with local path and remote-fetch adaptations, plus local bounds checks so malformed tab-stop output still scores in `[0, 1]`

## Reward Logic

- The reward follows the OSWorld tabstop metric, clamped into `[0, 1]`.
