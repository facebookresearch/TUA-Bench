# local/022-monthly-sales-line-chart

Benchmark task for translating OSWorld LibreOffice Calc example `0a2e43bf-b26c-4631-a966-af9dfa12c9e5` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: Work out the monthly total sales in a new row called "Total" and then create a line chart to show the results with the months on the x-axis.
- Main output path: `/app/SalesRep.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `chart`, `sheet_data`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `chart`, `sheet_data`.
- The local output contract at `/app/SalesRep.xlsx`.

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

- The workbook must be saved in place at `/app/SalesRep.xlsx`.

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
