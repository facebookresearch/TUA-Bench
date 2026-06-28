# local/068-strike-first-two-lines

Benchmark task for translating OSWorld LibreOffice Impress example `550ce7e7-747b-495f-b122-acdc4d0b8e54` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: I am checking our soccer club's to-do list for the last semester and adding strike-through sign on the line we have already accomplished. Could you help me add a strike-through on the first and second line?
- Main output path: `/app/New_Club_Spring_2018_Training.pptx`
- Verifier behavior: the exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination.
- The explicit local output contract at `/app/New_Club_Spring_2018_Training.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/New_Club_Spring_2018_Training.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- The reward is the exact combined OSWorld metric value in `[0, 1]`.
