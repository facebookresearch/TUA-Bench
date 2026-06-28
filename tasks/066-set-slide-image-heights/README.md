# local/066-set-slide-image-heights

Benchmark task for translating OSWorld LibreOffice Impress example `7ae48c60-f143-4119-b659-15b8f485eb9a` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: Change picture's height to 20, 30, 25cm on slide 3, 4, 6 respectively.
- Main output path: `/app/30_1.pptx`
- Verifier behavior: the exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination.
- The explicit local output contract at `/app/30_1.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/30_1.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- The reward is the exact combined OSWorld metric value in `[0, 1]`.
