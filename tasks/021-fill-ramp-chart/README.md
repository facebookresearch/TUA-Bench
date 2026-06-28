# local/021-fill-ramp-chart

Benchmark task for translating OSWorld LibreOffice Calc example `4de54231-e4b5-49e3-b2ba-61a0bec721c0` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: I have computed the acceleration in row 2, and I want you to fill out the remaining rows for columns B and D. Next, concatenate the values from columns A to D, including their headers (the pattern is "Header: cell value, ..., Header: cell value"), into a new column named "Combined Data" for all rows. In the new column, keep only 2 decimal digits.
- Main output path: `/app/RampUpAndDown.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `sheet_data`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `sheet_data`.
- The local output contract at `/app/RampUpAndDown.xlsx`.

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

- The workbook must be saved in place at `/app/RampUpAndDown.xlsx`.

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
