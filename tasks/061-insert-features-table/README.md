# local/061-insert-features-table

Benchmark task for translating OSWorld LibreOffice Impress example `39be0d19-634d-4475-8768-09c130f5425d` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: In the "Features" slide, insert a table with 5 rows and 2 columns.
- Main output path: `/app/41_3.pptx`
- Verifier behavior: the exact OSWorld `compare_pptx_files` metric

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_pptx_files` metric.
- The explicit local output contract at `/app/41_3.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/41_3.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
