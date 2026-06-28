# local/116-bottom-left-page-numbers

Benchmark task for translating OSWorld LibreOffice Writer example `0e47de2a-32e0-456c-a366-8c607ef7a9d2` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Writer`
- Local task description: Use LibreOffice Writer to add page numbers at the bottom left of every page.
- Main output path: `/app/LibreOffice_Open_Source_Word_Processing.docx`
- Verifier behavior: the exact OSWorld `has_page_numbers_in_footers` metric

## What Was Preserved

- The original LibreOffice Writer user intent and application constraint.
- The exact OSWorld `has_page_numbers_in_footers` metric.
- The in-place local document or artifact contract at `/app/LibreOffice_Open_Source_Word_Processing.docx`.

## What Was Simplified

- The original Desktop path is translated to the local Harbor workspace path `/app/LibreOffice_Open_Source_Word_Processing.docx`.
- The OSWorld GUI launch and save-hotkey postconfig are simplified to an explicit terminal-side file contract.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-writer`
- `tmux` and `asciinema` for terminal session support
- `dbus-x11`, `xvfb`, and `xauth` so Writer can still be launched from the terminal
- `python-docx` as the only verifier Python dependency

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The document must be saved in place at `/app/LibreOffice_Open_Source_Word_Processing.docx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing artifact with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld `has_page_numbers_in_footers` metric with only local path and remote-fetch adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
