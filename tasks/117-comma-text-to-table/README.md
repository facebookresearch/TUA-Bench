# local/117-comma-text-to-table

Benchmark task for translating OSWorld LibreOffice Writer example `936321ce-5236-426a-9a20-e0e3c5dc536f` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Writer`
- Local task description: Use LibreOffice Writer to convert comma-separated text into a table.
- Main output path: `/app/Graphemes_Sound_Letter_Patterns.docx`
- Verifier behavior: the exact OSWorld metric list `compare_docx_tables`, `compare_docx_tables` with `or` semantics

## What Was Preserved

- The original LibreOffice Writer user intent and application constraint.
- The exact OSWorld metric list `compare_docx_tables`, `compare_docx_tables` with `or` semantics.
- The in-place local document or artifact contract at `/app/Graphemes_Sound_Letter_Patterns.docx`.

## What Was Simplified

- The original Desktop path is translated to the local Harbor workspace path `/app/Graphemes_Sound_Letter_Patterns.docx`.
- The OSWorld GUI launch and save-hotkey postconfig are simplified to an explicit terminal-side file contract.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-writer`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages so Writer can still be launched from the terminal
- only the Python dependencies needed by the verifier

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The document must be saved in place at `/app/Graphemes_Sound_Letter_Patterns.docx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing artifact with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld metric list `compare_docx_tables`, `compare_docx_tables` with `or` semantics with only local path and remote-fetch adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
