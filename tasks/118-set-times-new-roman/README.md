# local/118-set-times-new-roman

Benchmark task for translating OSWorld LibreOffice Writer example `0e763496-b6bb-4508-a427-fad0b6c3e195` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Writer`
- Local task description: Use LibreOffice Writer to change the whole document font to Times New Roman.
- Main output path: `/app/Dublin_Zoo_Intro.docx`
- Verifier behavior: the exact OSWorld `compare_font_names` metric

## What Was Preserved

- The original LibreOffice Writer user intent and application constraint.
- The exact OSWorld `compare_font_names` metric.
- The in-place local document or artifact contract at `/app/Dublin_Zoo_Intro.docx`.

## What Was Simplified

- The original Desktop path is translated to the local Harbor workspace path `/app/Dublin_Zoo_Intro.docx`.
- The OSWorld GUI launch and save-hotkey postconfig are simplified to an explicit terminal-side file contract.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-writer`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages so Writer can still be launched from the terminal
- only `python-docx`, which is the single Python dependency needed by the verifier

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The document must be saved in place at `/app/Dublin_Zoo_Intro.docx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing artifact with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact into `/logs/artifacts/`
- `tests/test_outputs.py` keeps only the exact OSWorld `compare_font_names` metric path used by this task

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
