# local/062-add-baseball-audio

Benchmark task for translating OSWorld LibreOffice Impress example `c59742c0-4323-4b9d-8a02-723c251deaa0` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: I am making PPT about the history of baseball. I want to add an introduction audio named "Baseball.mp3" in `/app` into my PPT, but I do not know how. Could you help me add audio into my presentation file?
- Main output path: `/app/Mady_and_Mia_Baseball.pptx`
- Verifier behavior: the exact OSWorld `compare_audios` metric

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_audios` metric.
- The explicit local output contract at `/app/Mady_and_Mia_Baseball.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/Mady_and_Mia_Baseball.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- The reward is the exact OSWorld metric value in `[0, 1]`.
