# local/060-underline-red-text

Benchmark task for translating OSWorld LibreOffice Impress example `986fc832-6af2-417c-8845-9272b3a1528b` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: Underline the body of the slide only (without title and table) in dark red 2, and change the font color of the whole slide (title, body and table) to dark red 2.
- Main output path: `/app/154_3.pptx`
- Verifier behavior: the exact OSWorld `compare_pptx_files` metric

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_pptx_files` metric.
- The explicit local output contract at `/app/154_3.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/154_3.pptx`.

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
