# local/018-calculate-total-earnings

Benchmark task for translating OSWorld LibreOffice Calc example `357ef137-7eeb-4c80-a3bb-0951f26a8aff` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: I have calculated the total work hours from the daily hours, and I have an hourly rate. Now I want to multiply the total hours by the hourly rate to get a total earned amount. However, I can't get the correct answer by directly multiplying the two cells. Here the "total hours" value is formatted as time and "hourly rate" is just a number. How can I get the correct product? Help me fill in the cell with the correct answer. Don't touch irrelevant blank regions.
- Main output path: `/app/Multiply_Time_Number.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `check_cell`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `check_cell`.
- The local output contract at `/app/Multiply_Time_Number.xlsx`.

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

- The workbook must be saved in place at `/app/Multiply_Time_Number.xlsx`.

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
