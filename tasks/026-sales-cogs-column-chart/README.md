# local/026-sales-cogs-column-chart

Benchmark task for translating OSWorld LibreOffice Calc example `12382c62-0cd1-4bf2-bdc8-1d20bf9b2371` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: Create a clustered column chart showing the Sales and COGS data for each week in a new sheet named "Sheet2". Set the chart title as "Sales & COGS".
- Main output path: `/app/WeeklySales.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `chart`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `chart`.
- The local output contract at `/app/WeeklySales.xlsx`.

## What Was Simplified

- The original `/home/user/...` paths are translated to the local Harbor workspace under `/app`.
- OSWorld launch automation and save-hotkey postconfig are simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs:

- `libreoffice-calc`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages so Calc can still be launched from the terminal
- only `openpyxl` for the active chart-verifier path

Broader generic Calc-verifier helpers stay in `tests/test_outputs.py`, but their optional imports are branch-gated so this task image does not carry unused spreadsheet, XML, PDF, or fuzzy-match packages.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The workbook must be saved in place at `/app/WeeklySales.xlsx`.

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
