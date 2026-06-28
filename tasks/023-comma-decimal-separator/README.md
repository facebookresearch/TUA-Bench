# local/023-comma-decimal-separator

Benchmark task for translating OSWorld LibreOffice Calc example `a01fbce3-2793-461f-ab86-43680ccbae25` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Calc`
- Local task description: I need to set the decimal separator as a comma (,) for localized data representation and clarity in visualization. Can you help me to update all the numbers in the sheet? Also please keep the decimal numbers as-is.
- Main output path: `/app/Set_Decimal_Separator_Dot.xlsx`
- Verifier behavior: the exact OSWorld `compare_table` metric with rules: `sheet_print`

## What Was Preserved

- The original LibreOffice Calc user intent and application constraint.
- The exact OSWorld `compare_table` metric with rules: `sheet_print`.
- The local output contract at `/app/Set_Decimal_Separator_Dot.xlsx`.

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

- The workbook must be saved in place at `/app/Set_Decimal_Separator_Dot.xlsx`.
- The verifier also reads the exported sheet artifact `/app/Set_Decimal_Separator_Dot-Sheet1.csv`, which is generated from the saved workbook during verification.

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
