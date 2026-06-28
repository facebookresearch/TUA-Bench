# local/012-hide-na-budget-values

Benchmark task for translating OSWorld LibreOffice Calc example `6054afcb-5bab-4702-90a0-b259b5d3217c` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: Some data are missed by now and are filled by 'N/A' temporarily. Please hide them in the table for now. Do not delete any cells and filter is not needed.
- Main output path: `/app/Date_Budget_Variance_HideNA.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `row_props`, `sheet_data`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `row_props`, `sheet_data`.
- The local output contract at `/app/Date_Budget_Variance_HideNA.xlsx`.

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

- The workbook must be saved in place at `/app/Date_Budget_Variance_HideNA.xlsx`.

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
